"""Cycle-local resolver overlay for pre-commit semantic previews.

The staged overlay is deliberately non-durable.  It gives proof engines an exact
read view of records proposed for the current CAS commit while preserving the
immutable store snapshot underneath.  No staged record becomes runtime authority
unless the corresponding GraphPatch subsequently commits successfully.
"""
from __future__ import annotations

from typing import Iterable

from ..storage import (
    RecordKind,
    SemanticStore,
    StoreSnapshot,
    StoredRecord,
    record_fingerprints,
    record_ref,
    record_revision,
)


class StagedResolver:
    """Overlay exact cycle-local records over one pinned store snapshot."""

    def __init__(
        self,
        store: SemanticStore,
        snapshot: StoreSnapshot,
        records: Iterable[tuple[RecordKind, object]] = (),
    ) -> None:
        store.assert_snapshot(snapshot)
        self._store = store
        self._snapshot = snapshot
        staged: dict[tuple[RecordKind, str, int], StoredRecord] = {}
        for kind, payload in records:
            ref = record_ref(kind, payload)
            revision = record_revision(kind, payload)
            content_fp, record_fp = record_fingerprints(kind, payload)
            key = (kind, ref, revision)
            if key in staged and staged[key].record_fingerprint != record_fp:
                raise ValueError(
                    f"conflicting staged records for {kind.value}:{ref}@{revision}"
                )
            staged[key] = StoredRecord(
                record_kind=kind,
                record_ref=ref,
                revision=revision,
                payload=payload,
                content_fingerprint=content_fp,
                record_fingerprint=record_fp,
                layer="cycle-staged",
                store_revision=snapshot.store_revision,
                lifecycle_status=getattr(
                    getattr(payload, "lifecycle_status", None), "value", None
                ),
                context_ref=getattr(payload, "context_ref", None),
                valid_from=getattr(payload, "valid_from", None),
                valid_to=getattr(payload, "valid_to", None),
                permission_ref=getattr(payload, "permission_ref", None),
            )
        self._staged = staged

    @property
    def snapshot(self) -> StoreSnapshot:
        return self._snapshot

    def resolve(
        self,
        record_kind: RecordKind,
        record_ref_value: str,
        revision: int | None = None,
    ):
        if revision is not None:
            staged = self._staged.get(
                (record_kind, record_ref_value, int(revision))
            )
            if staged is not None:
                return staged
            return self._store.get_record(
                record_kind,
                record_ref_value,
                int(revision),
                snapshot=self._snapshot,
            )
        staged_matches = [
            value
            for (kind, ref, _revision), value in self._staged.items()
            if kind == record_kind and ref == record_ref_value
        ]
        if staged_matches:
            return max(staged_matches, key=lambda item: item.revision)
        return self._store.get_record(
            record_kind, record_ref_value, snapshot=self._snapshot
        )

    def records(self, record_kind: RecordKind):
        base = list(
            self._store.records(
                record_kind, all_revisions=True, snapshot=self._snapshot
            )
        )
        by_key = {(item.record_ref, item.revision): item for item in base}
        for (kind, ref, revision), item in self._staged.items():
            if kind == record_kind:
                by_key[(ref, revision)] = item
        return tuple(
            sorted(by_key.values(), key=lambda item: (item.record_ref, item.revision))
        )

    def resolve_any(self, record_ref_value: str):
        result = []
        for kind in RecordKind:
            item = self.resolve(kind, record_ref_value)
            if item is not None:
                result.append(item)
        return tuple(result)
