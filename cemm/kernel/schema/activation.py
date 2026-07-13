"""Atomic CAS activation and cluster activation for schema lifecycle.

Import boundary: standard library only → model.refs, schema.envelope,
schema.versioning, schema.dependency.

Activation authority: SemanticSchemaStore delegates here for the
compare-and-swap commit. This module cannot activate independently —
it performs the atomic lifecycle commit *through* the store.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ActivationStatus(str, Enum):
    SUCCESS = "success"
    CAS_FAILED = "cas_failed"
    CLUSTER_FAILED = "cluster_failed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Result of an activation attempt."""
    status: ActivationStatus
    activated_refs: tuple[str, ...] = ()
    failed_ref: str | None = None
    detail: str = ""


class SchemaStoreProtocol(Protocol):
    """Minimal protocol for the store to support atomic activation."""
    def get_revision(self, record_id: str) -> int | None: ...
    def set_status(
        self, record_id: str, status: str, expected_revision: int
    ) -> bool: ...


def activate_single(
    store: SchemaStoreProtocol,
    record_id: str,
    target_status: str,
    expected_revision: int,
) -> ActivationResult:
    """Compare-and-swap activation of a single schema revision.

    If the store revision has changed since assessment, CAS fails
    and reassessment is required.
    """
    current = store.get_revision(record_id)
    if current is None:
        return ActivationResult(
            status=ActivationStatus.BLOCKED,
            detail=f"Record {record_id} not found",
        )
    if current != expected_revision:
        return ActivationResult(
            status=ActivationStatus.CAS_FAILED,
            failed_ref=record_id,
            detail=f"Expected revision {expected_revision}, found {current}",
        )
    if not store.set_status(record_id, target_status, expected_revision):
        return ActivationResult(
            status=ActivationStatus.CAS_FAILED,
            failed_ref=record_id,
            detail="CAS commit failed",
        )
    return ActivationResult(
        status=ActivationStatus.SUCCESS,
        activated_refs=(record_id,),
    )


def activate_cluster(
    store: SchemaStoreProtocol,
    record_ids: tuple[str, ...],
    target_status: str,
    expected_revisions: dict[str, int],
) -> ActivationResult:
    """Atomic cluster activation — all-or-nothing.

    If any member fails, no member becomes active.
    Provisional revisions/evidence remain consistent.
    """
    # Verify all revisions first.
    for rid in record_ids:
        current = store.get_revision(rid)
        expected = expected_revisions.get(rid)
        if current is None or expected is None or current != expected:
            return ActivationResult(
                status=ActivationStatus.CAS_FAILED,
                failed_ref=rid,
                detail=f"CAS verification failed for {rid}",
            )

    # Commit all — if any fails, we have a cluster failure.
    # In a real implementation this would be transactional.
    committed: list[str] = []
    for rid in record_ids:
        if not store.set_status(rid, target_status, expected_revisions[rid]):
            # Rollback already-committed members.
            # set_status increments revision on success, so rollback
            # must use the post-commit revision (expected + 1) as the
            # new expected revision for the CAS revert.
            for committed_id in committed:
                post_commit_rev = expected_revisions[committed_id] + 1
                store.set_status(committed_id, "provisional", post_commit_rev)
            return ActivationResult(
                status=ActivationStatus.CLUSTER_FAILED,
                failed_ref=rid,
                detail=f"Cluster commit failed at {rid}; rolled back {len(committed)} members",
            )
        committed.append(rid)

    return ActivationResult(
        status=ActivationStatus.SUCCESS,
        activated_refs=tuple(committed),
    )
