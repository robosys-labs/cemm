"""Tests for LegacyClaimAdapter — materializing accepted graph patch operations
into legacy Claim store rows.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.adapters.legacy_claim_adapter import LegacyClaimAdapter
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.graph_patch import GraphPatch, PatchOperation
from cemm.learning.patch_validator import PatchValidationResult


class _MockClaimStore:
    def __init__(self) -> None:
        self.claims: list[Claim] = []

    def put(self, claim: Claim) -> None:
        self.claims.append(claim)


class _MockStore:
    def __init__(self) -> None:
        self.claims = _MockClaimStore()


def _accepted_result(patch_id: str = "patch_1") -> PatchValidationResult:
    return PatchValidationResult(
        patch_id=patch_id,
        status="accepted",
        scores={"permission_valid": 1.0, "source_present": 1.0},
    )


def _rejected_result(patch_id: str = "patch_1") -> PatchValidationResult:
    return PatchValidationResult(
        patch_id=patch_id,
        status="rejected",
        scores={"permission_valid": 0.0},
        failed_checks=["permission_valid"],
    )


def _make_patch(
    operations: list[PatchOperation] | None = None,
    evidence_refs: list[str] | None = None,
) -> GraphPatch:
    return GraphPatch(
        id="patch_test",
        target="concept_lattice",
        operations=operations or [],
        evidence_refs=evidence_refs or [],
        source_refs=["src_1"],
        confidence=0.8,
    )


# ── Tests ───────────────────────────────────────────────────────────────


def test_materialize_accepted_patch() -> None:
    adapter = LegacyClaimAdapter()
    op = PatchOperation(
        operation="upsert_relation_candidate",
        target_id="rel_1",
        fields={
            "subject_entity_id": "entity_a",
            "predicate": "knows",
            "object_value": "entity_b",
        },
    )
    patch = _make_patch(operations=[op])
    validation = _accepted_result()

    claims = adapter.materialize(patch, validation)

    assert len(claims) == 1
    assert claims[0].subject_entity_id == "entity_a"
    assert claims[0].predicate == "knows"
    assert claims[0].object_value == "entity_b"
    assert claims[0].status == ClaimStatus.ACTIVE
    assert claims[0].evidence_signal_ids == []


def test_materialize_rejected_patch() -> None:
    adapter = LegacyClaimAdapter()
    op = PatchOperation(
        operation="upsert_relation_candidate",
        target_id="rel_1",
        fields={
            "subject_entity_id": "entity_a",
            "predicate": "knows",
        },
    )
    patch = _make_patch(operations=[op])
    validation = _rejected_result()

    claims = adapter.materialize(patch, validation)

    assert claims == []


def test_materialize_typed_relation_operation() -> None:
    adapter = LegacyClaimAdapter()
    op = PatchOperation(
        operation="upsert_relation_candidate",
        target_id="rel_42",
        fields={
            "subject_entity_id": "entity_x",
            "predicate": "located_in",
            "object_entity_id": "entity_y",
            "object_value": "Paris",
            "domain": "geography",
        },
    )
    patch = _make_patch(operations=[op])
    validation = _accepted_result()

    claims = adapter.materialize(patch, validation)

    assert len(claims) == 1
    claim = claims[0]
    assert claim.subject_entity_id == "entity_x"
    assert claim.predicate == "located_in"
    assert claim.object_entity_id == "entity_y"
    assert claim.object_value == "Paris"
    assert claim.domain == "geography"


def test_materialize_custom_upsert_claim_skipped() -> None:
    adapter = LegacyClaimAdapter()
    op = PatchOperation(
        operation="custom:upsert_claim",
        target_id="legacy_1",
        fields={
            "subject_entity_id": "entity_a",
            "predicate": "is",
            "object_value": "test",
        },
    )
    patch = _make_patch(operations=[op])
    validation = _accepted_result()

    claims = adapter.materialize(patch, validation)

    assert claims == []


def test_materialize_incomplete_operation() -> None:
    adapter = LegacyClaimAdapter()
    op = PatchOperation(
        operation="upsert_relation_candidate",
        target_id="rel_bad",
        fields={
            "object_value": "orphan",
        },
    )
    patch = _make_patch(operations=[op])
    validation = _accepted_result()

    claims = adapter.materialize(patch, validation)

    assert claims == []


def test_materialize_and_store() -> None:
    store = _MockStore()
    adapter = LegacyClaimAdapter(store=store)
    op = PatchOperation(
        operation="upsert_relation_candidate",
        target_id="rel_1",
        fields={
            "subject_entity_id": "entity_a",
            "predicate": "knows",
        },
    )
    patch = _make_patch(operations=[op])
    validation = _accepted_result()

    claims = adapter.materialize_and_store(patch, validation)

    assert len(claims) == 1
    assert len(store.claims.claims) == 1
    assert store.claims.claims[0] is claims[0]
    assert adapter.total_materialized == 1
