"""Generation-separated concurrent semantic store for the v3.5.1 runtime."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterator
from uuid import uuid4

from ..runtime_generations import (
    AUTHORITY_RECORD_KINDS,
    AuthoritySnapshot,
    GenerationDomain,
    ReadGeneration,
    domains_for_record_kind,
    infer_patch_domains,
)
from ..schema.model import semantic_fingerprint
from .model import GraphPatch, PatchCommitResult, PatchCommitStatus, RecordKind, StoreSnapshot, StoredRecord
from .sqlite_schema import get_meta, set_meta
from .store import SemanticStore as _LegacySemanticStore


_GENERATION_META_KEYS = {
    GenerationDomain.AUTHORITY: "authority_generation",
    GenerationDomain.WORLD: "world_revision",
    GenerationDomain.DISCOURSE: "discourse_revision",
    GenerationDomain.RUNTIME_OBSERVATION: "runtime_observation_revision",
    GenerationDomain.AUDIT: "audit_revision",
    GenerationDomain.EFFECT_JOURNAL: "effect_journal_revision",
}


class SemanticStore(_LegacySemanticStore):
    """Canonical v3.5.1 layered store.

    Read snapshots use independent connections. The inherited writer lock therefore
    protects only short write/meta transitions and is never held while a semantic
    stage computes over a snapshot.
    """

    def __init__(
        self,
        overlay_path: str | Path = ":memory:",
        *,
        boot_path: str | Path | None = None,
    ) -> None:
        requested = str(overlay_path)
        if requested == ":memory:":
            requested = (
                "file:cemm-overlay-" + uuid4().hex + "?mode=memory&cache=shared"
            )
        super().__init__(requested, boot_path=boot_path)
        self._immutable_boot_fingerprint = (
            _LegacySemanticStore.boot_fingerprint.fget(self)
        )
        self._reader_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._pass_lock = threading.RLock()
        self._active_semantic_passes = 0
        self._readers: dict[
            int, tuple[sqlite3.Connection, sqlite3.Connection | None]
        ] = {}
        self._snapshot_lock = threading.RLock()
        self._active_snapshots: dict[
            str,
            tuple[
                sqlite3.Connection,
                sqlite3.Connection | None,
                StoreSnapshot,
            ],
        ] = {}
        self._pending_patch: GraphPatch | None = None
        self._pending_domains: frozenset[GenerationDomain] = frozenset()
        self._ensure_generation_meta()

    @property
    def revision(self) -> int:
        with self._lock:
            return int(get_meta(self._overlay, "store_revision", "0"))

    @property
    def overlay_fingerprint(self) -> str:
        with self._lock:
            return get_meta(
                self._overlay,
                "overlay_root",
                get_meta(self._overlay, "record_set_fingerprint", ""),
            )

    @property
    def boot_fingerprint(self) -> str:
        cached = getattr(self, "_immutable_boot_fingerprint", None)
        if cached is not None:
            return cached
        return _LegacySemanticStore.boot_fingerprint.fget(self)

    @contextmanager
    def semantic_pass(self):
        """Pin authority publication for one full semantic pass.

        Mutable world/discourse/audit writes remain independently revisioned, but an
        executable authority patch cannot publish while any pass is active.
        """
        # Keep lock order identical to apply_patch: writer/meta lock, then pass lock.
        # This makes "pin generation + register active pass" atomic with respect to
        # authority publication without introducing an inverted-lock deadlock.
        with self._lock:
            with self._pass_lock:
                self._active_semantic_passes += 1
                authority = self.current_authority_snapshot()
        try:
            yield authority
        finally:
            with self._pass_lock:
                self._active_semantic_passes -= 1
                if self._active_semantic_passes < 0:
                    self._active_semantic_passes = 0
                    raise RuntimeError("semantic pass lease underflow")

    @property
    def active_semantic_passes(self) -> int:
        with self._pass_lock:
            return self._active_semantic_passes

    def _ensure_generation_meta(self) -> None:
        with self._lock:
            defaults = {
                "authority_generation": "1",
                "authority_fingerprint": "",
                "world_revision": "0",
                "discourse_revision": "0",
                "runtime_observation_revision": "0",
                "audit_revision": "0",
                "effect_journal_revision": "0",
                "overlay_root": get_meta(
                    self._overlay, "record_set_fingerprint", ""
                ),
            }
            for key, value in defaults.items():
                if get_meta(self._overlay, key, "") == "":
                    set_meta(self._overlay, key, value)
            if not get_meta(self._overlay, "authority_fingerprint", ""):
                set_meta(
                    self._overlay,
                    "authority_fingerprint",
                    self._initial_authority_fingerprint(),
                )

    def _initial_authority_fingerprint(self) -> str:
        """One-time legacy-overlay bootstrap of executable authority only."""
        kinds = tuple(sorted(kind.value for kind in AUTHORITY_RECORD_KINDS))
        placeholders = ",".join("?" for _ in kinds)
        import json

        candidate_rows = self._overlay.execute(
            "SELECT record_kind, record_ref, revision, record_fingerprint, "
            "lifecycle_status, payload_json "
            f"FROM record_index WHERE record_kind IN ({placeholders}) "
            "ORDER BY record_kind, record_ref, revision",
            kinds,
        ).fetchall()
        rows = []
        for row in candidate_rows:
            lifecycle = row["lifecycle_status"]
            if lifecycle is not None and str(lifecycle) != "active":
                continue
            payload = json.loads(str(row["payload_json"]))
            if "active" in payload and not bool(payload["active"]):
                continue
            rows.append(
                (
                    str(row["record_kind"]),
                    str(row["record_ref"]),
                    int(row["revision"]),
                    str(row["record_fingerprint"]),
                )
            )
        tombstones = self._overlay.execute(
            "SELECT record_kind, record_ref, revision, reason "
            f"FROM record_tombstones WHERE record_kind IN ({placeholders}) "
            "ORDER BY record_kind, record_ref, revision",
            kinds,
        ).fetchall()
        return semantic_fingerprint(
            "authority-root",
            (
                self.boot_fingerprint,
                tuple(rows),
                tuple(tuple(row) for row in tombstones),
                1,
            ),
            64,
        )

    @staticmethod
    def _generation_from_connection(
        connection: sqlite3.Connection,
        *,
        boot_fingerprint: str,
    ) -> ReadGeneration:
        return ReadGeneration(
            store_revision=int(get_meta(connection, "store_revision", "0")),
            authority_generation=int(
                get_meta(connection, "authority_generation", "1")
            ),
            authority_fingerprint=get_meta(
                connection, "authority_fingerprint", ""
            ),
            world_revision=int(
                get_meta(connection, "world_revision", "0")
            ),
            discourse_revision=int(
                get_meta(connection, "discourse_revision", "0")
            ),
            runtime_observation_revision=int(
                get_meta(
                    connection,
                    "runtime_observation_revision",
                    "0",
                )
            ),
            audit_revision=int(
                get_meta(connection, "audit_revision", "0")
            ),
            effect_journal_revision=int(
                get_meta(
                    connection,
                    "effect_journal_revision",
                    "0",
                )
            ),
            overlay_fingerprint=get_meta(
                connection,
                "overlay_root",
                get_meta(connection, "record_set_fingerprint", ""),
            ),
            boot_fingerprint=boot_fingerprint,
        )

    def current_read_generation(self) -> ReadGeneration:
        # A very short writer-lock read ensures all generation fields describe one
        # committed transition without holding the lock during semantic computation.
        with self._lock:
            return self._generation_from_connection(
                self._overlay,
                boot_fingerprint=self.boot_fingerprint,
            )

    def current_authority_snapshot(
        self,
        *,
        runtime_attestation_ref: str = "",
    ) -> AuthoritySnapshot:
        generation = self.current_read_generation()
        return AuthoritySnapshot(
            generation=generation.authority_generation,
            authority_fingerprint=generation.authority_fingerprint,
            boot_fingerprint=generation.boot_fingerprint,
            runtime_attestation_ref=runtime_attestation_ref,
        )

    @property
    def _overlay_is_uri(self) -> bool:
        return self.overlay_path.startswith("file:")

    def _open_overlay_reader(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.overlay_path,
            uri=self._overlay_is_uri,
            check_same_thread=False,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA query_only=ON")
        return connection

    def _open_boot_reader(self) -> sqlite3.Connection | None:
        if self.boot_path is None:
            return None
        uri = (
            f"file:{self.boot_path.resolve().as_posix()}"
            "?mode=ro&immutable=1"
        )
        connection = sqlite3.connect(
            uri,
            uri=True,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        return connection

    def _thread_connections(
        self,
    ) -> tuple[sqlite3.Connection, sqlite3.Connection | None]:
        ident = threading.get_ident()
        with self._reader_lock:
            found = self._readers.get(ident)
            if found is None:
                found = (
                    self._open_overlay_reader(),
                    self._open_boot_reader(),
                )
                self._readers[ident] = found
            return found

    def _connections(
        self,
        snapshot: StoreSnapshot | None,
    ) -> tuple[sqlite3.Connection | None, sqlite3.Connection]:
        if snapshot is None:
            overlay, boot = self._thread_connections()
            return boot, overlay
        self.assert_snapshot(snapshot)
        if not snapshot.snapshot_ref:
            overlay, boot = self._thread_connections()
            return boot, overlay
        with self._snapshot_lock:
            overlay, boot, _registered = self._active_snapshots[
                snapshot.snapshot_ref
            ]
        return boot, overlay

    @contextmanager
    def snapshot(self) -> Iterator[StoreSnapshot]:
        overlay = self._open_overlay_reader()
        boot = self._open_boot_reader()
        overlay.execute("BEGIN")
        # Force the SQLite read transaction to pin now, then derive every generation
        # from that same read view.
        overlay.execute(
            "SELECT value FROM meta WHERE key='store_revision'"
        ).fetchone()
        generation = self._generation_from_connection(
            overlay,
            boot_fingerprint=self.boot_fingerprint,
        )
        snapshot = StoreSnapshot(
            store_revision=generation.store_revision,
            boot_fingerprint=generation.boot_fingerprint,
            overlay_fingerprint=generation.overlay_fingerprint,
            snapshot_ref="store-snapshot:" + uuid4().hex,
            authority_generation=generation.authority_generation,
            authority_fingerprint=generation.authority_fingerprint,
            world_revision=generation.world_revision,
            discourse_revision=generation.discourse_revision,
            runtime_observation_revision=(
                generation.runtime_observation_revision
            ),
            audit_revision=generation.audit_revision,
            effect_journal_revision=generation.effect_journal_revision,
        )
        with self._snapshot_lock:
            self._active_snapshots[snapshot.snapshot_ref] = (
                overlay,
                boot,
                snapshot,
            )
        try:
            yield snapshot
        finally:
            with self._snapshot_lock:
                self._active_snapshots.pop(snapshot.snapshot_ref, None)
            try:
                overlay.rollback()
            finally:
                overlay.close()
                if boot is not None:
                    boot.close()

    def assert_snapshot(self, snapshot: StoreSnapshot | None) -> None:
        if snapshot is None:
            return
        if not snapshot.snapshot_ref:
            # Compatibility for older tests/callers constructing StoreSnapshot
            # directly. Canonical runtime snapshots always have snapshot_ref.
            if snapshot.store_revision != self.revision:
                from .store import StoreConflictError
                raise StoreConflictError("legacy snapshot is stale")
            if snapshot.overlay_fingerprint != self.overlay_fingerprint:
                from .store import StoreConflictError
                raise StoreConflictError("overlay database fingerprint changed")
            return
        with self._snapshot_lock:
            registered = self._active_snapshots.get(snapshot.snapshot_ref)
            if registered is None or registered[2] != snapshot:
                raise RuntimeError(
                    "snapshot is not active in this semantic store"
                )

    @staticmethod
    def _tombstoned_ref(
        overlay: sqlite3.Connection,
        kind: RecordKind,
        record_ref: str,
        revision: int,
    ) -> bool:
        row = overlay.execute(
            "SELECT 1 FROM record_tombstones "
            "WHERE record_kind=? AND record_ref=? "
            "AND (revision IS NULL OR revision=?) LIMIT 1",
            (kind.value, record_ref, int(revision)),
        ).fetchone()
        return row is not None

    def get_record(
        self,
        record_kind: RecordKind | str,
        record_ref: str,
        revision: int | None = None,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> StoredRecord[Any] | None:
        resolved = (
            record_kind
            if isinstance(record_kind, RecordKind)
            else RecordKind(record_kind)
        )
        boot, overlay = self._connections(snapshot)
        candidates: dict[int, StoredRecord[Any]] = {}
        for connection, layer in (
            (boot, "boot"),
            (overlay, "overlay"),
        ):
            if connection is None:
                continue
            if revision is None:
                rows = connection.execute(
                    "SELECT * FROM record_index "
                    "WHERE record_kind=? AND record_ref=? "
                    "ORDER BY revision DESC",
                    (resolved.value, record_ref),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM record_index "
                    "WHERE record_kind=? AND record_ref=? AND revision=?",
                    (resolved.value, record_ref, int(revision)),
                ).fetchall()
            for row in rows:
                rev = int(row["revision"])
                if self._tombstoned_ref(
                    overlay, resolved, record_ref, rev
                ):
                    continue
                item = self._row_to_stored(
                    row,
                    resolved,
                    layer,
                )
                if rev not in candidates or layer == "overlay":
                    candidates[rev] = item
                if revision is not None:
                    break

        if not candidates:
            return None
        return candidates[max(candidates)]

    def _cache_generation_token(
        self,
        kind: RecordKind,
        snapshot: StoreSnapshot | None,
    ) -> tuple[Any, ...]:
        generation = (
            snapshot.read_generation
            if snapshot is not None
            else self.current_read_generation()
        )
        domains = set(domains_for_record_kind(kind))
        # Effective rows can be invalidated by an authority revision even when their
        # own world/discourse generation did not change.
        domains.add(GenerationDomain.AUTHORITY)
        return generation.token_for(domains)

    def records(
        self,
        record_kind: RecordKind | str,
        *,
        all_revisions: bool = False,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StoredRecord[Any], ...]:
        resolved = (
            record_kind
            if isinstance(record_kind, RecordKind)
            else RecordKind(record_kind)
        )
        generation_token = self._cache_generation_token(resolved, snapshot)
        if all_revisions:
            generation = (
                snapshot.read_generation
                if snapshot is not None
                else self.current_read_generation()
            )
            generation_token = (
                generation_token,
                generation.token_for((GenerationDomain.AUDIT,)),
            )
        cache_key = (
            resolved,
            all_revisions,
            generation_token,
        )
        with self._cache_lock:
            cached = self._records_cache.get(cache_key)
        if cached is not None:
            return cached

        boot, overlay = self._connections(snapshot)
        tombstone_rows = overlay.execute(
            "SELECT record_ref, revision FROM record_tombstones "
            "WHERE record_kind=?",
            (resolved.value,),
        ).fetchall()
        tombstones = {
            (
                str(row["record_ref"]),
                None
                if row["revision"] is None
                else int(row["revision"]),
            )
            for row in tombstone_rows
        }

        combined: dict[
            tuple[str, int],
            StoredRecord[Any],
        ] = {}
        for connection, layer in (
            (boot, "boot"),
            (overlay, "overlay"),
        ):
            if connection is None:
                continue
            for item in self._read_rows(
                connection,
                resolved,
                layer,
            ):
                if (
                    (item.record_ref, item.revision) in tombstones
                    or (item.record_ref, None) in tombstones
                ):
                    continue
                combined[(item.record_ref, item.revision)] = item

        if all_revisions:
            result = tuple(
                combined[key] for key in sorted(combined)
            )
        else:
            latest: dict[str, StoredRecord[Any]] = {}
            for item in combined.values():
                current = latest.get(item.record_ref)
                if current is None or item.revision > current.revision:
                    latest[item.record_ref] = item
            result = tuple(
                latest[key]
                for key in sorted(latest)
                if not self.is_invalidated(
                    latest[key].record_kind,
                    latest[key].record_ref,
                    latest[key].revision,
                    snapshot=snapshot,
                )
            )

        # Reclaim only entries for the record kind being rebuilt. No unrelated cache
        # domain is flushed.
        with self._cache_lock:
            self._records_cache = {
                key: value
                for key, value in self._records_cache.items()
                if not (
                    isinstance(key, tuple)
                    and key
                    and key[0] == resolved
                )
            }
            self._records_cache[cache_key] = result
        return result

    def resolve_any(
        self,
        record_ref: str,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StoredRecord[Any], ...]:
        boot, overlay = self._connections(snapshot)
        kinds: set[RecordKind] = set()
        for connection in (boot, overlay):
            if connection is None:
                continue
            rows = connection.execute(
                "SELECT DISTINCT record_kind FROM record_index WHERE record_ref=?",
                (record_ref,),
            ).fetchall()
            for row in rows:
                kinds.add(RecordKind(str(row[0])))
        return tuple(
            item
            for kind in sorted(kinds, key=lambda value: value.value)
            for item in (
                self.get_record(
                    kind,
                    record_ref,
                    snapshot=snapshot,
                ),
            )
            if item is not None
        )

    def is_invalidated(
        self,
        record_kind: RecordKind | str,
        record_ref: str,
        revision: int,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> bool:
        resolved = (
            record_kind
            if isinstance(record_kind, RecordKind)
            else RecordKind(record_kind)
        )
        _boot, overlay = self._connections(snapshot)
        row = overlay.execute(
            "SELECT 1 FROM record_invalidations "
            "WHERE record_kind=? AND record_ref=? AND revision=? LIMIT 1",
            (
                resolved.value,
                record_ref,
                int(revision),
            ),
        ).fetchone()
        return row is not None

    def materialized_view(
        self,
        view_ref: str,
        *,
        snapshot: StoreSnapshot | None = None,
    ):
        """Resolve materialized views from the same pinned reader generation."""
        _boot, overlay = self._connections(snapshot)
        row = overlay.execute(
            "SELECT payload_json FROM record_index "
            "WHERE record_kind=? AND record_ref=? "
            "ORDER BY revision DESC LIMIT 1",
            (RecordKind.MATERIALIZED_VIEW.value, view_ref),
        ).fetchone()
        if row is None:
            return None
        stale = overlay.execute(
            "SELECT stale FROM materialized_views WHERE view_ref=?",
            (view_ref,),
        ).fetchone()
        if stale is None or bool(stale[0]):
            return None
        import json
        from .codec import decode_record

        item = decode_record(
            RecordKind.MATERIALIZED_VIEW,
            json.loads(str(row["payload_json"])),
        )
        if item.dependency_fingerprint != self.dependency_fingerprint(
            item.dependency_refs,
            snapshot=snapshot,
        ):
            return None
        return item

    def knowledge_records_for_proposition(
        self,
        proposition_ref: str,
        *,
        context_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StoredRecord[Any], ...]:
        """Indexed proposition lookup against the caller's exact read snapshot."""
        boot, overlay = self._connections(snapshot)
        refs: set[str] = set()
        for connection in (boot, overlay):
            if connection is None:
                continue
            rows = connection.execute(
                "SELECT knowledge_ref FROM knowledge_records "
                "WHERE proposition_ref=? AND context_ref IN ('global', ?)",
                (proposition_ref, context_ref),
            ).fetchall()
            refs.update(str(row[0]) for row in rows)
        return tuple(
            item
            for ref in sorted(refs)
            for item in (
                self.get_record(
                    RecordKind.KNOWLEDGE,
                    ref,
                    snapshot=snapshot,
                ),
            )
            if item is not None
        )

    def capability_records_for(
        self,
        *,
        holder_ref: str,
        action_schema_ref: str,
        action_schema_revision: int,
        context_ref: str,
        status: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StoredRecord[Any], ...]:
        """Indexed capability lookup against the caller's exact read snapshot."""
        boot, overlay = self._connections(snapshot)
        refs: set[str] = set()
        for connection in (boot, overlay):
            if connection is None:
                continue
            sql = (
                "SELECT capability_ref FROM capability_instances "
                "WHERE holder_ref=? AND action_schema_ref=? "
                "AND action_schema_revision=? AND context_ref IN ('global', ?)"
            )
            params: tuple[object, ...] = (
                holder_ref,
                action_schema_ref,
                action_schema_revision,
                context_ref,
            )
            if status is not None:
                sql += " AND status=?"
                params = (*params, status)
            rows = connection.execute(sql, params).fetchall()
            refs.update(str(row[0]) for row in rows)
        return tuple(
            item
            for ref in sorted(refs)
            for item in (
                self.get_record(
                    RecordKind.CAPABILITY_INSTANCE,
                    ref,
                    snapshot=snapshot,
                ),
            )
            if item is not None
        )

    def _domains_with_dependents(
        self,
        patch: GraphPatch,
    ) -> frozenset[GenerationDomain]:
        domains = set(infer_patch_domains(patch))
        frontier = [
            (
                operation.record_kind,
                operation.target_ref,
            )
            for operation in patch.operations
        ]
        visited = set(frontier)
        while frontier:
            kind, ref = frontier.pop()
            params = (kind.value, ref)
            rows = list(
                self._overlay.execute(
                    "SELECT dependent_kind, dependent_ref "
                    "FROM dependencies "
                    "WHERE prerequisite_kind=? AND prerequisite_ref=? "
                    "AND active=1",
                    params,
                ).fetchall()
            )
            if self._boot is not None:
                rows.extend(
                    self._boot.execute(
                        "SELECT dependent_kind, dependent_ref "
                        "FROM dependencies "
                        "WHERE prerequisite_kind=? "
                        "AND prerequisite_ref=? AND active=1",
                        params,
                    ).fetchall()
                )
            for row in rows:
                dependent = (
                    RecordKind(str(row[0])),
                    str(row[1]),
                )
                domains.update(
                    domains_for_record_kind(dependent[0])
                )
                if dependent not in visited:
                    visited.add(dependent)
                    frontier.append(dependent)
        domains.add(GenerationDomain.AUDIT)
        return frozenset(domains)

    def apply_patch(
        self,
        patch: GraphPatch,
    ) -> PatchCommitResult:
        with self._lock:
            self._pending_patch = patch
            self._pending_domains = self._domains_with_dependents(patch)
            try:
                if GenerationDomain.AUTHORITY in self._pending_domains:
                    with self._pass_lock:
                        active = self._active_semantic_passes
                    if active:
                        before = self.revision
                        return PatchCommitResult(
                            patch_ref=patch.patch_ref,
                            status=PatchCommitStatus.CONFLICT,
                            committed=False,
                            store_revision_before=before,
                            store_revision_after=before,
                            errors=(
                                "authority_generation_in_use:"
                                f"active_semantic_passes={active}",
                            ),
                        )
                return super().apply_patch(patch)
            finally:
                self._pending_patch = None
                self._pending_domains = frozenset()

    def _overlay_record_fingerprint(
        self,
        next_revision: int,
    ) -> str:
        patch = self._pending_patch
        if patch is None:
            return get_meta(
                self._overlay,
                "record_set_fingerprint",
                "",
            )
        previous = get_meta(
            self._overlay,
            "overlay_root",
            get_meta(
                self._overlay,
                "record_set_fingerprint",
                "",
            ),
        )
        return semantic_fingerprint(
            "overlay-append-root",
            (
                previous,
                patch.fingerprint,
                int(next_revision),
            ),
            64,
        )

    def _journal_patch(
        self,
        patch: GraphPatch,
        before: int,
        after: int,
    ) -> None:
        super()._journal_patch(
            patch,
            before,
            after,
        )
        domains = (
            self._pending_domains
            or infer_patch_domains(patch)
        )
        overlay_root = get_meta(
            self._overlay,
            "record_set_fingerprint",
            "",
        )
        set_meta(
            self._overlay,
            "overlay_root",
            overlay_root,
        )
        for domain in domains:
            key = _GENERATION_META_KEYS[domain]
            current = int(
                get_meta(
                    self._overlay,
                    key,
                    "0",
                )
            )
            set_meta(
                self._overlay,
                key,
                str(current + 1),
            )
        if GenerationDomain.AUTHORITY in domains:
            generation = int(
                get_meta(
                    self._overlay,
                    "authority_generation",
                    "1",
                )
            )
            previous = get_meta(
                self._overlay,
                "authority_fingerprint",
                "",
            )
            set_meta(
                self._overlay,
                "authority_fingerprint",
                semantic_fingerprint(
                    "authority-root",
                    (
                        previous,
                        patch.fingerprint,
                        generation,
                        overlay_root,
                    ),
                    64,
                ),
            )

    def close(self) -> None:
        with self._snapshot_lock:
            snapshots = list(
                self._active_snapshots.values()
            )
            self._active_snapshots.clear()
        for overlay, boot, _snapshot in snapshots:
            try:
                overlay.close()
            finally:
                if boot is not None:
                    boot.close()

        with self._reader_lock:
            readers = list(self._readers.values())
            self._readers.clear()
        for overlay, boot in readers:
            try:
                overlay.close()
            finally:
                if boot is not None:
                    boot.close()
        super().close()


__all__ = ["SemanticStore"]
