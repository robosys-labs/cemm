"""Read-only overlay of CycleWorkspace transient records over the durable store.

This lets exact-pin planners consume transient Stage-14/15/18/19 artifacts without
turning those logical stages into mandatory persistence transactions.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from .learning.model import PinnedRecord
from .runtime_generations import AUTHORITY_RECORD_KINDS
from .storage.codec import record_fingerprints, record_permission, record_ref, record_revision
from .storage.model import RecordKind, StoredRecord


_INDEX_KEY = "__transient_record_index__"


class WorkspaceRecordError(RuntimeError):
    pass


class WorkspaceRecordIndex:
    def __init__(self, workspace, base_store) -> None:
        self.__workspace = workspace
        self.__base = base_store
        self._index: dict[tuple[RecordKind, str, int], StoredRecord[Any]] = workspace.artifacts.setdefault(_INDEX_KEY, {})

    def register(self, kind: RecordKind, payload: Any) -> PinnedRecord:
        if kind in AUTHORITY_RECORD_KINDS:
            raise WorkspaceRecordError("executable semantic authority cannot be created in CycleWorkspace")
        ref = record_ref(kind, payload)
        revision = record_revision(kind, payload)
        content_fp, record_fp = record_fingerprints(kind, payload)
        key = (kind, ref, revision)
        current = self._index.get(key)
        durable = self.__base.get_record(kind, ref, revision)
        if durable is None:
            # Canonical get_record intentionally hides invalidated revisions. Exact
            # identity protection must still see them so a workspace cannot resurrect
            # or rewrite a physically existing invalidated (kind, ref, revision).
            durable = next((
                item for item in self.__base.records(kind, all_revisions=True)
                if item.record_ref == ref and item.revision == revision
            ), None)
        if durable is not None and self.__base.is_invalidated(kind, ref, revision):
            raise WorkspaceRecordError(
                f"transient record cannot resurrect invalidated durable identity: {kind.value}:{ref}@{revision}"
            )
        if durable is not None and durable.record_fingerprint != record_fp:
            raise WorkspaceRecordError(
                f"transient record collides with durable exact identity: {kind.value}:{ref}@{revision}"
            )
        if durable is not None:
            return PinnedRecord(kind, ref, revision, durable.record_fingerprint)
        stored = StoredRecord(
            record_kind=kind,
            record_ref=ref,
            revision=revision,
            payload=payload,
            content_fingerprint=content_fp,
            record_fingerprint=record_fp,
            layer="workspace",
            store_revision=self.__base.revision,
            permission_ref=record_permission(kind, payload),
        )
        if current is not None and current.record_fingerprint != record_fp:
            raise WorkspaceRecordError(f"transient identity collision: {kind.value}:{ref}@{revision}")
        self._index[key] = stored
        return PinnedRecord(kind, ref, revision, record_fp)

    def get(self, kind: RecordKind, ref: str, revision: int | None = None):
        values = [
            stored for (k, r, rev), stored in self._index.items()
            if k == kind and r == ref and (revision is None or rev == revision)
        ]
        return None if not values else max(values, key=lambda item: item.revision)

    def records(self, kind: RecordKind, *, all_revisions: bool = False):
        values = [stored for (k, _r, _rev), stored in self._index.items() if k == kind]
        if all_revisions:
            return tuple(sorted(values, key=lambda x: (x.record_ref, x.revision)))
        latest = {}
        for item in values:
            current = latest.get(item.record_ref)
            if current is None or item.revision > current.revision:
                latest[item.record_ref] = item
        return tuple(latest[key] for key in sorted(latest))

    def resolve_any(self, ref: str):
        return tuple(sorted(
            (stored for (_kind, r, _rev), stored in self._index.items() if r == ref),
            key=lambda x: (x.record_kind.value, x.revision),
        ))




class ReadOnlySemanticStoreView:
    """Public read-only facade used for signed service construction.

    It deliberately exposes no mutable connection handles and rejects the canonical
    patch/close mutators. Cycle-local services receive CycleArtifactStoreView instead.
    """

    def __init__(self, base_store) -> None:
        self.__base = base_store

    def __getattr__(self, name):
        if name.startswith("_") or name in {"apply_patch", "close"}:
            raise AttributeError(name)
        return getattr(self.__base, name)

    @property
    def repositories(self):
        return self.__base.repositories

    def snapshot(self):
        return self.__base.snapshot()

    def get_record(self, *args, **kwargs):
        return self.__base.get_record(*args, **kwargs)

    def records(self, *args, **kwargs):
        return self.__base.records(*args, **kwargs)

    def resolve_any(self, *args, **kwargs):
        return self.__base.resolve_any(*args, **kwargs)

    def is_invalidated(self, *args, **kwargs):
        return self.__base.is_invalidated(*args, **kwargs)

    def current_read_generation(self):
        return self.__base.current_read_generation()

    def current_authority_snapshot(self, **kwargs):
        return self.__base.current_authority_snapshot(**kwargs)


class CycleArtifactStoreView:
    """Read-only durable+workspace view. Writes are forbidden by construction."""

    def __init__(self, base_store, workspace) -> None:
        self.__base = base_store
        self.__workspace = workspace
        self.transient = WorkspaceRecordIndex(workspace, base_store)

    def __getattribute__(self, name):
        if name in {"base_store", "workspace", "_base", "apply_patch", "close"}:
            raise AttributeError(name)
        return object.__getattribute__(self, name)

    @property
    def repositories(self):
        # Repositories encode durable authority/world indexes.  Transient semantic
        # authority is forbidden, so delegating repository access is intentional.
        return self.__base.repositories

    @property
    def revision(self):
        return self.__base.revision

    @property
    def boot_fingerprint(self):
        return self.__base.boot_fingerprint

    @property
    def overlay_fingerprint(self):
        return self.__base.overlay_fingerprint

    def current_read_generation(self):
        return self.__base.current_read_generation()

    def current_authority_snapshot(self, **kwargs):
        return self.__base.current_authority_snapshot(**kwargs)

    @contextmanager
    def snapshot(self):
        with self.__base.snapshot() as snapshot:
            yield snapshot

    def assert_snapshot(self, snapshot):
        return self.__base.assert_snapshot(snapshot)

    def get_record(self, kind, ref, revision=None, *, snapshot=None):
        resolved = kind if isinstance(kind, RecordKind) else RecordKind(kind)
        transient = self.transient.get(resolved, ref, revision)
        durable = self.__base.get_record(resolved, ref, revision, snapshot=snapshot)
        if revision is not None:
            # register() already proves exact durable/transient identity equivalence.
            return transient if transient is not None else durable
        if transient is None:
            return durable
        if durable is None:
            return transient
        return transient if transient.revision > durable.revision else durable

    def records(self, kind, *, all_revisions=False, snapshot=None):
        resolved = kind if isinstance(kind, RecordKind) else RecordKind(kind)
        durable = self.__base.records(resolved, all_revisions=True, snapshot=snapshot)
        merged = {(x.record_ref, x.revision): x for x in durable}
        for item in self.transient.records(resolved, all_revisions=True):
            merged[(item.record_ref, item.revision)] = item
        values = tuple(merged[key] for key in sorted(merged))
        if all_revisions:
            return values
        latest = {}
        for item in values:
            if item.layer != "workspace" and self.__base.is_invalidated(
                item.record_kind, item.record_ref, item.revision, snapshot=snapshot
            ):
                continue
            current = latest.get(item.record_ref)
            if current is None or item.revision > current.revision:
                latest[item.record_ref] = item
        return tuple(latest[key] for key in sorted(latest))

    def resolve_any(self, ref, *, snapshot=None):
        merged = {(x.record_kind, x.record_ref, x.revision): x for x in self.__base.resolve_any(ref, snapshot=snapshot)}
        for item in self.transient.resolve_any(ref):
            merged[(item.record_kind, item.record_ref, item.revision)] = item
        return tuple(merged[key] for key in sorted(merged, key=lambda x: (x[0].value, x[1], x[2])))

    def is_invalidated(self, *args, **kwargs):
        return self.__base.is_invalidated(*args, **kwargs)

    def apply_patch(self, *_args, **_kwargs):
        raise WorkspaceRecordError("CycleArtifactStoreView is read-only; persist only at explicit effect boundaries")


__all__ = [
    "CycleArtifactStoreView", "ReadOnlySemanticStoreView",
    "WorkspaceRecordError", "WorkspaceRecordIndex",
]
