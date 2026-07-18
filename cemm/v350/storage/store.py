"""Read-only boot plus writable-overlay semantic store for CEMM v3.5."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable, Iterator, Mapping

from ..schema.model import semantic_fingerprint
from .codec import decode_record, record_fingerprints, record_ref
from .model import (
    DependencyEdge,
    GraphPatch,
    MaterializedViewRecord,
    PatchCommitResult,
    PatchCommitStatus,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
    StoreSnapshot,
    StoredRecord,
)
from .persistence import canonical_json, tombstone_record, write_record
from .sqlite_schema import (
    configure_connection,
    get_meta,
    initialize_schema,
    require_schema_compatible,
    set_meta,
)
from .validation import CommitValidationError, CommitValidator


class StoreError(RuntimeError):
    pass


class StoreConflictError(StoreError):
    pass


class ReadOnlyBootError(StoreError):
    pass


@dataclass(frozen=True, slots=True)
class _PreparedOperation:
    operation: PatchOperation
    record: Any | None


class _StagedResolver:
    def __init__(
        self,
        store: "SemanticStore",
        prepared: Iterable[_PreparedOperation],
    ) -> None:
        self._store = store
        self._staged: dict[tuple[RecordKind, str, int], StoredRecord[Any]] = {}
        self._tombstones: set[tuple[RecordKind, str, int | None]] = set()
        next_store_revision = store.revision + 1
        for item in prepared:
            operation = item.operation
            if operation.operation_kind in {
                PatchOperationKind.TOMBSTONE,
                PatchOperationKind.INVALIDATE,
            }:
                self._tombstones.add(
                    (operation.record_kind, operation.target_ref, operation.record_revision)
                )
                continue
            if item.record is None:
                continue
            content_fp, record_fp = record_fingerprints(operation.record_kind, item.record)
            self._staged[
                (operation.record_kind, operation.target_ref, operation.record_revision)
            ] = StoredRecord(
                record_kind=operation.record_kind,
                record_ref=operation.target_ref,
                revision=operation.record_revision,
                payload=item.record,
                content_fingerprint=content_fp,
                record_fingerprint=record_fp,
                layer="staged",
                store_revision=next_store_revision,
            )

    def resolve(
        self, record_kind: RecordKind, record_ref: str, revision: int | None = None
    ) -> StoredRecord[Any] | None:
        candidates = [
            item
            for (kind, ref, rev), item in self._staged.items()
            if kind == record_kind and ref == record_ref and (revision is None or rev == revision)
            and not self._is_tombstoned(kind, ref, rev)
        ]
        if candidates:
            return max(candidates, key=lambda item: item.revision)
        if revision is not None and self._is_tombstoned(record_kind, record_ref, revision):
            return None
        if revision is None and (record_kind, record_ref, None) in self._tombstones:
            return None
        return self._store.get_record(record_kind, record_ref, revision)

    def records(self, record_kind: RecordKind) -> tuple[StoredRecord[Any], ...]:
        base = {
            (item.record_ref, item.revision): item
            for item in self._store.records(record_kind, all_revisions=True)
            if not self._is_tombstoned(record_kind, item.record_ref, item.revision)
        }
        for (kind, ref, revision), item in self._staged.items():
            if kind == record_kind and not self._is_tombstoned(kind, ref, revision):
                base[(ref, revision)] = item
        return tuple(base[key] for key in sorted(base))

    def resolve_any(self, record_ref: str) -> tuple[StoredRecord[Any], ...]:
        result = []
        for kind in RecordKind:
            value = self.resolve(kind, record_ref)
            if value is not None:
                result.append(value)
        return tuple(result)

    def _is_tombstoned(self, kind: RecordKind, ref: str, revision: int) -> bool:
        return (kind, ref, revision) in self._tombstones or (kind, ref, None) in self._tombstones


class SemanticStore:
    """One logical store composed of an immutable boot DB and one overlay DB.

    Every mutation is an atomic :class:`GraphPatch`.  Readers may pin a snapshot
    that includes the overlay revision and immutable boot fingerprint.
    """

    def __init__(
        self,
        overlay_path: str | Path = ":memory:",
        *,
        boot_path: str | Path | None = None,
    ) -> None:
        self.overlay_path = str(overlay_path)
        self.boot_path = None if boot_path is None else Path(boot_path)
        self._lock = threading.RLock()
        self._overlay = sqlite3.connect(
            self.overlay_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self._overlay.row_factory = sqlite3.Row
        configure_connection(self._overlay)
        self._overlay.execute("BEGIN IMMEDIATE")
        try:
            initialize_schema(self._overlay)
            self._overlay.commit()
        except Exception:
            self._overlay.rollback()
            raise
        self._boot: sqlite3.Connection | None = None
        self._records_cache: dict[
            tuple[RecordKind, bool, int, str, str], tuple[StoredRecord[Any], ...]
        ] = {}
        if self.boot_path is not None:
            if not self.boot_path.is_file():
                raise FileNotFoundError(self.boot_path)
            uri = f"file:{self.boot_path.resolve().as_posix()}?mode=ro&immutable=1"
            self._boot = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self._boot.row_factory = sqlite3.Row
            require_schema_compatible(self._boot)
        self._repositories = None

    @property
    def revision(self) -> int:
        return int(get_meta(self._overlay, "store_revision", "0"))

    @property
    def boot_fingerprint(self) -> str:
        if self._boot is None:
            return "boot-database:none"
        return get_meta(self._boot, "boot_fingerprint", "") or "boot-database:none"

    @property
    def overlay_fingerprint(self) -> str:
        return get_meta(self._overlay, "record_set_fingerprint", "")

    @property
    def repositories(self):
        if self._repositories is None:
            from .repositories import RepositorySet

            self._repositories = RepositorySet(self)
        return self._repositories

    def close(self) -> None:
        with self._lock:
            if self._boot is not None:
                self._boot.close()
                self._boot = None
            self._overlay.close()

    @contextmanager
    def snapshot(self) -> Iterator[StoreSnapshot]:
        with self._lock:
            self._overlay.execute("BEGIN")
            snapshot = StoreSnapshot(
                store_revision=self.revision,
                boot_fingerprint=self.boot_fingerprint,
                overlay_fingerprint=self.overlay_fingerprint,
            )
            try:
                yield snapshot
            finally:
                self._overlay.rollback()

    def assert_snapshot(self, snapshot: StoreSnapshot | None) -> None:
        if snapshot is None:
            return
        if snapshot.store_revision != self.revision:
            raise StoreConflictError(
                f"snapshot revision {snapshot.store_revision} is stale; current={self.revision}"
            )
        if snapshot.boot_fingerprint != self.boot_fingerprint:
            raise StoreConflictError("boot database fingerprint changed")
        if snapshot.overlay_fingerprint != self.overlay_fingerprint:
            raise StoreConflictError("overlay database fingerprint changed")

    def get_record(
        self,
        record_kind: RecordKind | str,
        record_ref: str,
        revision: int | None = None,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> StoredRecord[Any] | None:
        self.assert_snapshot(snapshot)
        resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
        candidates = [
            item
            for item in self.records(resolved, all_revisions=True, snapshot=snapshot)
            if item.record_ref == record_ref and (revision is None or item.revision == revision)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.revision)

    def records(
        self,
        record_kind: RecordKind | str,
        *,
        all_revisions: bool = False,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StoredRecord[Any], ...]:
        self.assert_snapshot(snapshot)
        resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
        store_revision = self.revision if snapshot is None else snapshot.store_revision
        boot_fingerprint = self.boot_fingerprint if snapshot is None else snapshot.boot_fingerprint
        overlay_fingerprint = self.overlay_fingerprint if snapshot is None else snapshot.overlay_fingerprint
        cache_key = (resolved, all_revisions, store_revision, boot_fingerprint, overlay_fingerprint)
        cached = self._records_cache.get(cache_key)
        if cached is not None:
            return cached
        self._records_cache = {
            key: value for key, value in self._records_cache.items()
            if key[2:] == cache_key[2:]
        }
        tombstones = self._tombstones(resolved)
        combined: dict[tuple[str, int], StoredRecord[Any]] = {}
        if self._boot is not None:
            for item in self._read_rows(self._boot, resolved, "boot"):
                if not _tombstoned(tombstones, item.record_ref, item.revision):
                    combined[(item.record_ref, item.revision)] = item
        for item in self._read_rows(self._overlay, resolved, "overlay"):
            if not _tombstoned(tombstones, item.record_ref, item.revision):
                combined[(item.record_ref, item.revision)] = item
        if all_revisions:
            result = tuple(combined[key] for key in sorted(combined))
            self._records_cache[cache_key] = result
            return result
        latest: dict[str, StoredRecord[Any]] = {}
        for item in combined.values():
            current = latest.get(item.record_ref)
            if current is None or item.revision > current.revision:
                latest[item.record_ref] = item
        result = tuple(latest[key] for key in sorted(latest))
        self._records_cache[cache_key] = result
        return result

    def resolve_any(
        self, record_ref: str, *, snapshot: StoreSnapshot | None = None
    ) -> tuple[StoredRecord[Any], ...]:
        result = []
        for kind in RecordKind:
            item = self.get_record(kind, record_ref, snapshot=snapshot)
            if item is not None:
                result.append(item)
        return tuple(result)

    def apply_patch(self, patch: GraphPatch) -> PatchCommitResult:
        with self._lock:
            self._overlay.execute("BEGIN IMMEDIATE")
            before = self.revision
            try:
                prior = self._overlay.execute(
                    "SELECT patch_fingerprint, revision_after FROM patch_journal WHERE patch_ref=?",
                    (patch.patch_ref,),
                ).fetchone()
                if prior is not None:
                    if str(prior["patch_fingerprint"]) != patch.fingerprint:
                        self._overlay.rollback()
                        return PatchCommitResult(
                            patch_ref=patch.patch_ref,
                            status=PatchCommitStatus.CONFLICT,
                            committed=False,
                            store_revision_before=before,
                            store_revision_after=before,
                            errors=("patch_ref_reused_with_different_content",),
                        )
                    self._overlay.rollback()
                    return PatchCommitResult(
                        patch_ref=patch.patch_ref,
                        status=PatchCommitStatus.IDEMPOTENT,
                        committed=True,
                        store_revision_before=before,
                        store_revision_after=int(prior["revision_after"]),
                    )
                if patch.expected_store_revision is not None and patch.expected_store_revision != before:
                    self._overlay.rollback()
                    return PatchCommitResult(
                        patch_ref=patch.patch_ref,
                        status=PatchCommitStatus.CONFLICT,
                        committed=False,
                        store_revision_before=before,
                        store_revision_after=before,
                        errors=(
                            f"store_revision_conflict:{patch.expected_store_revision}!={before}",
                        ),
                    )
                prepared = self._prepare(patch.operations)
                staged = _StagedResolver(self, prepared)
                self._validate_cas(prepared)
                CommitValidator(staged).require_valid(
                    (item.operation, item.record) for item in prepared
                )
                after = before + 1
                changed_refs: set[str] = set()
                applied: list[str] = []
                for item in prepared:
                    operation = item.operation
                    changed_refs.add(operation.target_ref)
                    if operation.operation_kind in {
                        PatchOperationKind.UPSERT,
                        PatchOperationKind.MATERIALIZE,
                    }:
                        assert item.record is not None
                        write_record(
                            self._overlay,
                            operation.record_kind,
                            item.record,
                            revision=operation.record_revision,
                            store_revision=after,
                        )
                        self._write_operation_dependencies(operation, after)
                    elif operation.operation_kind == PatchOperationKind.TOMBSTONE:
                        tombstone_record(
                            self._overlay,
                            operation.record_kind,
                            operation.target_ref,
                            operation.record_revision,
                            reason=operation.reason or "retracted_by_patch",
                            store_revision=after,
                        )
                    elif operation.operation_kind == PatchOperationKind.INVALIDATE:
                        self._invalidate_target(operation.target_ref, after)
                    applied.append(operation.operation_ref)
                invalidated = self._invalidate_dependents(changed_refs, after)
                set_meta(self._overlay, "store_revision", str(after))
                set_meta(
                    self._overlay,
                    "record_set_fingerprint",
                    self._overlay_record_fingerprint(after),
                )
                self._journal_patch(patch, before, after)
                self._overlay.commit()
                return PatchCommitResult(
                    patch_ref=patch.patch_ref,
                    status=PatchCommitStatus.COMMITTED,
                    committed=True,
                    store_revision_before=before,
                    store_revision_after=after,
                    applied_operation_refs=tuple(applied),
                    invalidated_view_refs=tuple(sorted(invalidated)),
                )
            except (CommitValidationError, StoreConflictError, ValueError, TypeError) as exc:
                self._overlay.rollback()
                errors = (
                    tuple(
                        f"{item.code}:{item.target_ref}:{item.message}"
                        for item in exc.errors
                    )
                    if isinstance(exc, CommitValidationError)
                    else (str(exc),)
                )
                return PatchCommitResult(
                    patch_ref=patch.patch_ref,
                    status=(
                        PatchCommitStatus.CONFLICT
                        if isinstance(exc, StoreConflictError)
                        else PatchCommitStatus.REJECTED
                    ),
                    committed=False,
                    store_revision_before=before,
                    store_revision_after=before,
                    errors=errors,
                )
            except Exception:
                self._overlay.rollback()
                raise

    def materialized_view(
        self,
        view_ref: str,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> MaterializedViewRecord | None:
        self.assert_snapshot(snapshot)
        row = self._overlay.execute(
            "SELECT payload_json FROM record_index WHERE record_kind=? AND record_ref=? "
            "ORDER BY revision DESC LIMIT 1",
            (RecordKind.MATERIALIZED_VIEW.value, view_ref),
        ).fetchone()
        if row is None:
            return None
        stale = self._overlay.execute(
            "SELECT stale FROM materialized_views WHERE view_ref=?",
            (view_ref,),
        ).fetchone()
        if stale is None or bool(stale[0]):
            return None
        item = decode_record(RecordKind.MATERIALIZED_VIEW, json.loads(str(row["payload_json"])))
        if item.dependency_fingerprint != self.dependency_fingerprint(item.dependency_refs):
            return None
        return item

    def dependency_fingerprint(
        self,
        dependency_refs: Iterable[str],
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> str:
        self.assert_snapshot(snapshot)
        items = []
        for ref in sorted(set(dependency_refs)):
            records = self.resolve_any(ref, snapshot=snapshot)
            items.append(
                (
                    ref,
                    tuple(
                        sorted(
                            (
                                item.record_kind.value,
                                item.revision,
                                item.record_fingerprint,
                            )
                            for item in records
                        )
                    ),
                )
            )
        return semantic_fingerprint("dependency-set", tuple(items), 64)

    def _prepare(self, operations: Iterable[PatchOperation]) -> tuple[_PreparedOperation, ...]:
        result = []
        identities: set[tuple[RecordKind, str, int]] = set()
        for operation in operations:
            identity = (
                operation.record_kind,
                operation.target_ref,
                operation.record_revision,
            )
            if identity in identities:
                raise ValueError(f"duplicate patch target revision: {identity}")
            identities.add(identity)
            record = None
            if operation.operation_kind in {
                PatchOperationKind.UPSERT,
                PatchOperationKind.MATERIALIZE,
            }:
                record = decode_record(operation.record_kind, operation.payload)
                actual_ref = record_ref(operation.record_kind, record)
                if actual_ref != operation.target_ref:
                    raise ValueError(
                        f"operation target {operation.target_ref} does not match payload ref {actual_ref}"
                    )
            result.append(_PreparedOperation(operation, record))
        return tuple(result)

    def _validate_cas(self, prepared: Iterable[_PreparedOperation]) -> None:
        for item in prepared:
            operation = item.operation
            current = self.get_record(operation.record_kind, operation.target_ref)
            if operation.operation_kind in {
                PatchOperationKind.UPSERT,
                PatchOperationKind.MATERIALIZE,
            }:
                exact = self.get_record(
                    operation.record_kind,
                    operation.target_ref,
                    operation.record_revision,
                )
                if exact is not None:
                    raise StoreConflictError(
                        f"record_revision_immutable:{operation.target_ref}@"
                        f"{operation.record_revision}"
                    )
            if operation.expected_record_revision is not None:
                observed = None if current is None else current.revision
                if observed != operation.expected_record_revision:
                    raise StoreConflictError(
                        f"record_revision_conflict:{operation.target_ref}:"
                        f"{operation.expected_record_revision}!={observed}"
                    )
            if operation.expected_record_fingerprint is not None:
                observed_fp = None if current is None else current.record_fingerprint
                if observed_fp != operation.expected_record_fingerprint:
                    raise StoreConflictError(
                        f"record_fingerprint_conflict:{operation.target_ref}"
                    )
            if (
                operation.operation_kind in {
                    PatchOperationKind.UPSERT,
                    PatchOperationKind.MATERIALIZE,
                }
                and current is not None
                and operation.record_revision < current.revision
            ):
                raise StoreConflictError(
                    f"record_revision_regression:{operation.target_ref}:"
                    f"{operation.record_revision}<{current.revision}"
                )

    def _write_operation_dependencies(self, operation: PatchOperation, store_revision: int) -> None:
        for dependency in operation.dependencies:
            dependency_ref = semantic_fingerprint(
                "dependency",
                (
                    operation.record_kind.value,
                    operation.target_ref,
                    operation.record_revision,
                    None if dependency.record_kind is None else dependency.record_kind.value,
                    dependency.record_ref,
                    dependency.revision,
                    dependency.dependency_kind,
                ),
                48,
            )
            edge = DependencyEdge(
                dependency_ref=dependency_ref,
                dependent_kind=operation.record_kind,
                dependent_ref=operation.target_ref,
                dependent_revision=operation.record_revision,
                prerequisite_kind=dependency.record_kind,
                prerequisite_ref=dependency.record_ref,
                prerequisite_revision=dependency.revision,
                prerequisite_fingerprint=dependency.fingerprint,
                dependency_kind=dependency.dependency_kind,
            )
            write_record(
                self._overlay,
                RecordKind.DEPENDENCY,
                edge,
                revision=1,
                store_revision=store_revision,
            )

    def _invalidate_target(self, target_ref: str, store_revision: int) -> None:
        row = self._overlay.execute(
            "SELECT view_ref FROM materialized_views WHERE view_ref=?",
            (target_ref,),
        ).fetchone()
        if row is not None:
            self._overlay.execute(
                "UPDATE materialized_views SET stale=1 WHERE view_ref=?",
                (target_ref,),
            )

    def _invalidate_dependents(self, changed_refs: set[str], store_revision: int) -> set[str]:
        invalidated: set[str] = set()
        frontier = list(sorted(changed_refs))
        visited = set(frontier)
        while frontier:
            prerequisite = frontier.pop(0)
            rows = self._overlay.execute(
                "SELECT dependent_kind, dependent_ref FROM dependencies "
                "WHERE prerequisite_ref=? AND active=1 ORDER BY dependent_kind, dependent_ref",
                (prerequisite,),
            ).fetchall()
            if self._boot is not None:
                rows += self._boot.execute(
                    "SELECT dependent_kind, dependent_ref FROM dependencies "
                    "WHERE prerequisite_ref=? AND active=1 ORDER BY dependent_kind, dependent_ref",
                    (prerequisite,),
                ).fetchall()
            for row in rows:
                dependent_ref = str(row["dependent_ref"])
                dependent_kind = RecordKind(str(row["dependent_kind"]))
                if dependent_kind == RecordKind.MATERIALIZED_VIEW:
                    self._overlay.execute(
                        "UPDATE materialized_views SET stale=1 WHERE view_ref=?",
                        (dependent_ref,),
                    )
                    invalidated.add(dependent_ref)
                if dependent_ref not in visited:
                    visited.add(dependent_ref)
                    frontier.append(dependent_ref)
        return invalidated

    def _journal_patch(self, patch: GraphPatch, before: int, after: int) -> None:
        self._overlay.execute(
            """
            INSERT INTO patch_journal(
                patch_ref, patch_fingerprint, context_ref, scope_ref, source_ref,
                permission_ref, evidence_refs_json, validation_requirements_json,
                rollback_hint, metadata_json, revision_before, revision_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patch.patch_ref,
                patch.fingerprint,
                patch.context_ref,
                patch.scope_ref,
                patch.source_ref,
                patch.permission_ref,
                canonical_json(patch.evidence_refs),
                canonical_json(patch.validation_requirements),
                patch.rollback_hint,
                canonical_json(patch.metadata),
                before,
                after,
            ),
        )
        self._overlay.executemany(
            """
            INSERT INTO patch_operations(
                patch_ref, ordinal, operation_ref, operation_kind, record_kind,
                target_ref, record_revision, expected_record_revision,
                expected_record_fingerprint, dependencies_json, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    patch.patch_ref,
                    ordinal,
                    operation.operation_ref,
                    operation.operation_kind.value,
                    operation.record_kind.value,
                    operation.target_ref,
                    operation.record_revision,
                    operation.expected_record_revision,
                    operation.expected_record_fingerprint,
                    canonical_json(operation.dependencies),
                    operation.reason,
                )
                for ordinal, operation in enumerate(patch.operations)
            ),
        )

    def _read_rows(
        self,
        connection: sqlite3.Connection,
        record_kind: RecordKind,
        layer: str,
    ) -> tuple[StoredRecord[Any], ...]:
        rows = connection.execute(
            """
            SELECT record_ref, revision, lifecycle_status, context_ref,
                   valid_from, valid_to, permission_ref, content_fingerprint,
                   record_fingerprint, payload_json, store_revision
            FROM record_index
            WHERE record_kind=?
            ORDER BY record_ref, revision
            """,
            (record_kind.value,),
        ).fetchall()
        result = []
        for row in rows:
            payload = decode_record(record_kind, json.loads(str(row["payload_json"])))
            result.append(
                StoredRecord(
                    record_kind=record_kind,
                    record_ref=str(row["record_ref"]),
                    revision=int(row["revision"]),
                    payload=payload,
                    content_fingerprint=str(row["content_fingerprint"]),
                    record_fingerprint=str(row["record_fingerprint"]),
                    layer=layer,
                    store_revision=int(row["store_revision"]),
                    lifecycle_status=(
                        None
                        if row["lifecycle_status"] is None
                        else str(row["lifecycle_status"])
                    ),
                    context_ref=None if row["context_ref"] is None else str(row["context_ref"]),
                    valid_from=None if row["valid_from"] is None else str(row["valid_from"]),
                    valid_to=None if row["valid_to"] is None else str(row["valid_to"]),
                    permission_ref=(
                        None if row["permission_ref"] is None else str(row["permission_ref"])
                    ),
                )
            )
        return tuple(result)

    def _tombstones(self, record_kind: RecordKind) -> set[tuple[str, int | None]]:
        rows = self._overlay.execute(
            "SELECT record_ref, revision FROM record_tombstones WHERE record_kind=?",
            (record_kind.value,),
        ).fetchall()
        return {
            (str(row["record_ref"]), None if row["revision"] is None else int(row["revision"]))
            for row in rows
        }

    def _overlay_record_fingerprint(self, next_revision: int) -> str:
        rows = self._overlay.execute(
            "SELECT record_kind, record_ref, revision, record_fingerprint "
            "FROM record_index ORDER BY record_kind, record_ref, revision"
        ).fetchall()
        tombstones = self._overlay.execute(
            "SELECT record_kind, record_ref, revision, reason "
            "FROM record_tombstones ORDER BY record_kind, record_ref, revision"
        ).fetchall()
        return semantic_fingerprint(
            "overlay-record-set",
            (
                next_revision,
                tuple(tuple(row) for row in rows),
                tuple(tuple(row) for row in tombstones),
            ),
            64,
        )


def _tombstoned(
    tombstones: set[tuple[str, int | None]], record_ref: str, revision: int
) -> bool:
    return (record_ref, revision) in tombstones or (record_ref, None) in tombstones
