"""SQLite durable semantic store and GraphPatch commit authority."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable, Iterator, Mapping

from .model import (
    GraphPatch,
    KnowledgeRecord,
    PatchCommitResult,
    PatchOperation,
    PatchOperationKind,
    Polarity,
    PortBinding,
    Predication,
    Referent,
    ReferentKind,
    TruthStatus,
    canonical_data,
)


class StoreConflictError(RuntimeError):
    pass


class StoreValidationError(ValueError):
    pass


class SemanticStore:
    """Durable proposition/referent store.

    All mutating public behavior goes through :meth:`apply_patch`.  Read methods
    return immutable canonical records.  A monotonically increasing store
    revision provides pinned-snapshot/CAS behavior for cognitive cycles.
    """

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT OR IGNORE INTO meta(key, value) VALUES ('store_revision', '0');

            CREATE TABLE IF NOT EXISTS referents (
                referent_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                type_refs_json TEXT NOT NULL,
                payload_json TEXT,
                scope_ref TEXT NOT NULL,
                context_ref TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                revision INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS referents_kind_idx ON referents(kind);

            CREATE TABLE IF NOT EXISTS aliases (
                language_tag TEXT NOT NULL,
                normalized_surface TEXT NOT NULL,
                referent_ref TEXT NOT NULL,
                confidence REAL NOT NULL,
                source_ref TEXT NOT NULL,
                revision INTEGER NOT NULL,
                PRIMARY KEY(language_tag, normalized_surface, referent_ref),
                FOREIGN KEY(referent_ref) REFERENCES referents(referent_id)
            );
            CREATE INDEX IF NOT EXISTS aliases_lookup_idx
                ON aliases(language_tag, normalized_surface, confidence DESC);

            CREATE TABLE IF NOT EXISTS predications (
                predication_id TEXT PRIMARY KEY,
                predicate_schema_ref TEXT NOT NULL,
                bindings_json TEXT NOT NULL,
                context_ref TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                assumptions_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                revision INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS predications_predicate_idx
                ON predications(predicate_schema_ref);

            CREATE TABLE IF NOT EXISTS proposition_contents (
                proposition_ref TEXT NOT NULL,
                predication_ref TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                PRIMARY KEY(proposition_ref, predication_ref)
            );
            CREATE INDEX IF NOT EXISTS proposition_contents_pred_idx
                ON proposition_contents(predication_ref);

            CREATE TABLE IF NOT EXISTS port_fillers (
                predication_ref TEXT NOT NULL,
                port_id TEXT NOT NULL,
                referent_ref TEXT,
                open_variable_ref TEXT,
                ordinal INTEGER NOT NULL,
                PRIMARY KEY(predication_ref, port_id, ordinal)
            );
            CREATE INDEX IF NOT EXISTS port_fillers_lookup_idx
                ON port_fillers(port_id, referent_ref);

            CREATE TABLE IF NOT EXISTS knowledge (
                knowledge_id TEXT PRIMARY KEY,
                proposition_ref TEXT NOT NULL,
                truth_status TEXT NOT NULL,
                context_ref TEXT NOT NULL,
                source_refs_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                scope_ref TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                permission_ref TEXT NOT NULL,
                valid_time_ref TEXT,
                superseded_by TEXT,
                metadata_json TEXT NOT NULL,
                revision INTEGER NOT NULL,
                FOREIGN KEY(proposition_ref) REFERENCES referents(referent_id)
            );
            CREATE INDEX IF NOT EXISTS knowledge_active_idx
                ON knowledge(context_ref, scope_ref, truth_status, superseded_by);
            CREATE INDEX IF NOT EXISTS knowledge_prop_idx ON knowledge(proposition_ref);

            CREATE TABLE IF NOT EXISTS patches (
                patch_id TEXT PRIMARY KEY,
                context_ref TEXT NOT NULL,
                scope_ref TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                operations_json TEXT NOT NULL,
                revision_before INTEGER NOT NULL,
                revision_after INTEGER NOT NULL,
                metadata_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS discourse_turns (
                turn_id TEXT PRIMARY KEY,
                context_ref TEXT NOT NULL,
                speaker_ref TEXT NOT NULL,
                proposition_refs_json TEXT NOT NULL,
                language_tag TEXT NOT NULL,
                raw_observation_ref TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS discourse_context_idx
                ON discourse_turns(context_ref, ordinal DESC);

            CREATE TABLE IF NOT EXISTS mentions (
                mention_id TEXT PRIMARY KEY,
                context_ref TEXT NOT NULL,
                turn_ref TEXT NOT NULL,
                referent_ref TEXT NOT NULL,
                salience REAL NOT NULL,
                grammatical_role TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS mentions_context_idx
                ON mentions(context_ref, salience DESC);

            CREATE TABLE IF NOT EXISTS open_questions (
                question_id TEXT PRIMARY KEY,
                context_ref TEXT NOT NULL,
                proposition_ref TEXT NOT NULL,
                variable_refs_json TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS open_questions_context_idx
                ON open_questions(context_ref, status);

            CREATE TABLE IF NOT EXISTS world_tracks (
                track_id TEXT PRIMARY KEY,
                context_ref TEXT NOT NULL,
                referent_ref TEXT NOT NULL,
                modality TEXT NOT NULL,
                state_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                observed_at TEXT NOT NULL,
                revision INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS world_tracks_context_idx
                ON world_tracks(context_ref, confidence DESC);

            CREATE TABLE IF NOT EXISTS schema_candidates (
                candidate_ref TEXT PRIMARY KEY,
                scope_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                revision INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule_candidates (
                candidate_ref TEXT PRIMARY KEY,
                scope_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                revision INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_records (
                evidence_id TEXT PRIMARY KEY,
                source_ref TEXT NOT NULL,
                confidence REAL NOT NULL,
                lineage_ref TEXT NOT NULL,
                span_start INTEGER,
                span_end INTEGER,
                metadata_json TEXT NOT NULL,
                revision INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS evidence_lineage_idx
                ON evidence_records(lineage_ref, confidence DESC);

            CREATE TABLE IF NOT EXISTS schema_revisions (
                schema_ref TEXT NOT NULL,
                revision INTEGER NOT NULL,
                schema_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                scope_ref TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                field_provenance_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                support_lineage_refs_json TEXT NOT NULL,
                counterevidence_refs_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                permission_ref TEXT NOT NULL,
                dependency_refs_json TEXT NOT NULL,
                competence_case_refs_json TEXT NOT NULL,
                environment_fingerprint TEXT NOT NULL,
                competence_passed INTEGER NOT NULL,
                epistemically_admissible INTEGER NOT NULL,
                PRIMARY KEY(schema_ref, revision)
            );
            CREATE INDEX IF NOT EXISTS schema_revisions_active_idx
                ON schema_revisions(schema_ref, scope_ref, status, revision DESC);

            CREATE TABLE IF NOT EXISTS rule_revisions (
                rule_ref TEXT NOT NULL,
                revision INTEGER NOT NULL,
                status TEXT NOT NULL,
                scope_ref TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                support_lineage_refs_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                environment_fingerprint TEXT NOT NULL,
                PRIMARY KEY(rule_ref, revision)
            );
            CREATE INDEX IF NOT EXISTS rule_revisions_active_idx
                ON rule_revisions(rule_ref, scope_ref, status, revision DESC);

            CREATE TABLE IF NOT EXISTS dependencies (
                dependency_id TEXT PRIMARY KEY,
                dependent_ref TEXT NOT NULL,
                dependency_ref TEXT NOT NULL,
                dependency_kind TEXT NOT NULL,
                dependent_revision INTEGER NOT NULL,
                dependency_revision INTEGER NOT NULL,
                active INTEGER NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS dependencies_reverse_idx
                ON dependencies(dependency_ref, active);

            CREATE TABLE IF NOT EXISTS invalidations (
                invalidation_id TEXT PRIMARY KEY,
                target_ref TEXT NOT NULL,
                reason TEXT NOT NULL,
                cause_ref TEXT NOT NULL,
                prior_fingerprint TEXT NOT NULL,
                invalidated_at_revision INTEGER NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS invalidations_target_idx
                ON invalidations(target_ref, invalidated_at_revision DESC);

            CREATE TABLE IF NOT EXISTS capability_observations (
                observation_id TEXT PRIMARY KEY,
                capability_ref TEXT NOT NULL,
                available INTEGER NOT NULL,
                confidence REAL NOT NULL,
                source_ref TEXT NOT NULL,
                context_ref TEXT NOT NULL,
                resource_state_json TEXT NOT NULL,
                valid_until TEXT,
                evidence_refs_json TEXT NOT NULL,
                revision INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS capability_context_idx
                ON capability_observations(context_ref, capability_ref, confidence DESC);

            CREATE TABLE IF NOT EXISTS operation_ledger (
                ledger_ref TEXT PRIMARY KEY,
                plan_ref TEXT NOT NULL,
                operation_ref TEXT NOT NULL,
                status TEXT NOT NULL,
                authorization_fingerprint TEXT NOT NULL,
                capability_evidence_refs_json TEXT NOT NULL,
                observed_proposition_refs_json TEXT NOT NULL,
                errors_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS emission_ledger (
                ledger_ref TEXT PRIMARY KEY,
                plan_ref TEXT NOT NULL,
                proof_ref TEXT NOT NULL,
                language_tag TEXT NOT NULL,
                surface_hash TEXT NOT NULL,
                authorized INTEGER NOT NULL,
                covered_semantic_refs_json TEXT NOT NULL,
                schema_revisions_json TEXT NOT NULL,
                reasons_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS truth_assessments (
                assessment_id TEXT PRIMARY KEY,
                proposition_signature TEXT NOT NULL,
                context_ref TEXT NOT NULL,
                truth_status TEXT NOT NULL,
                support_knowledge_refs_json TEXT NOT NULL,
                opposition_knowledge_refs_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                valid_time_ref TEXT,
                evidence_refs_json TEXT NOT NULL,
                store_revision INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS truth_signature_idx
                ON truth_assessments(proposition_signature, context_ref, store_revision DESC);
            """
        )
        self._ensure_column("knowledge", "root_lineage_refs_json", "TEXT NOT NULL DEFAULT '[]'")
        self._ensure_column("knowledge", "derivation_refs_json", "TEXT NOT NULL DEFAULT '[]'")
        self._ensure_column("knowledge", "valid_from", "TEXT")
        self._ensure_column("knowledge", "valid_to", "TEXT")
        self._connection.commit()

    def _ensure_column(self, table: str, column: str, declaration: str) -> None:
        columns = {str(row["name"]) for row in self._connection.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            self._connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    @property
    def revision(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM meta WHERE key='store_revision'"
        ).fetchone()
        return int(row["value"])

    @contextmanager
    def snapshot(self) -> Iterator[int]:
        with self._lock:
            self._connection.execute("BEGIN")
            revision = self.revision
            try:
                yield revision
            finally:
                self._connection.rollback()

    def apply_patch(self, patch: GraphPatch) -> PatchCommitResult:
        with self._lock:
            before = self.revision
            if patch.expected_store_revision is not None and patch.expected_store_revision != before:
                return PatchCommitResult(
                    patch_id=patch.patch_id,
                    committed=False,
                    store_revision_before=before,
                    store_revision_after=before,
                    blocked_operation_refs=tuple(op.operation_id for op in patch.operations),
                    errors=(
                        f"store_revision_conflict:{patch.expected_store_revision}!={before}",
                    ),
                )
            existing = self._connection.execute(
                "SELECT revision_after FROM patches WHERE patch_id=?", (patch.patch_id,)
            ).fetchone()
            if existing is not None:
                return PatchCommitResult(
                    patch_id=patch.patch_id,
                    committed=True,
                    store_revision_before=before,
                    store_revision_after=int(existing["revision_after"]),
                    applied_operation_refs=tuple(op.operation_id for op in patch.operations),
                )
            applied: list[str] = []
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                for operation in patch.operations:
                    self._apply_operation(operation)
                    applied.append(operation.operation_id)
                after = before + 1
                self._connection.execute(
                    "UPDATE meta SET value=? WHERE key='store_revision'", (str(after),)
                )
                self._connection.execute(
                    """INSERT INTO patches(
                        patch_id, context_ref, scope_ref, source_ref,
                        evidence_refs_json, operations_json, revision_before,
                        revision_after, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        patch.patch_id,
                        patch.context_ref,
                        patch.scope_ref,
                        patch.source_ref,
                        _json(patch.evidence_refs),
                        _json(patch.operations),
                        before,
                        after,
                        _json(patch.metadata),
                    ),
                )
                self._connection.commit()
                return PatchCommitResult(
                    patch_id=patch.patch_id,
                    committed=True,
                    store_revision_before=before,
                    store_revision_after=after,
                    applied_operation_refs=tuple(applied),
                )
            except Exception as exc:
                self._connection.rollback()
                return PatchCommitResult(
                    patch_id=patch.patch_id,
                    committed=False,
                    store_revision_before=before,
                    store_revision_after=before,
                    applied_operation_refs=(),
                    blocked_operation_refs=tuple(op.operation_id for op in patch.operations),
                    errors=(f"{type(exc).__name__}:{exc}",),
                )

    def _apply_operation(self, operation: PatchOperation) -> None:
        handlers = {
            PatchOperationKind.UPSERT_REFERENT: self._upsert_referent,
            PatchOperationKind.ADD_ALIAS: self._add_alias,
            PatchOperationKind.UPSERT_PREDICATION: self._upsert_predication,
            PatchOperationKind.UPSERT_PROPOSITION: self._upsert_proposition,
            PatchOperationKind.UPSERT_KNOWLEDGE: self._upsert_knowledge,
            PatchOperationKind.SUPERSEDE_KNOWLEDGE: self._supersede_knowledge,
            PatchOperationKind.RETRACT_SUPPORT: self._retract_support,
            PatchOperationKind.UPSERT_DISCOURSE_TURN: self._upsert_discourse_turn,
            PatchOperationKind.UPSERT_MENTION: self._upsert_mention,
            PatchOperationKind.UPSERT_OPEN_QUESTION: self._upsert_open_question,
            PatchOperationKind.CLOSE_OPEN_QUESTION: self._close_open_question,
            PatchOperationKind.UPSERT_WORLD_TRACK: self._upsert_world_track,
            PatchOperationKind.UPSERT_SCHEMA_CANDIDATE: self._upsert_schema_candidate,
            PatchOperationKind.UPSERT_RULE_CANDIDATE: self._upsert_rule_candidate,
            PatchOperationKind.UPSERT_EVIDENCE: self._upsert_evidence,
            PatchOperationKind.UPSERT_SCHEMA_REVISION: self._upsert_schema_revision,
            PatchOperationKind.UPSERT_RULE_REVISION: self._upsert_rule_revision,
            PatchOperationKind.ADD_DEPENDENCY: self._add_dependency,
            PatchOperationKind.RECORD_INVALIDATION: self._record_invalidation,
            PatchOperationKind.UPSERT_CAPABILITY_OBSERVATION: self._upsert_capability_observation,
            PatchOperationKind.UPSERT_OPERATION_LEDGER: self._upsert_operation_ledger,
            PatchOperationKind.UPSERT_EMISSION_LEDGER: self._upsert_emission_ledger,
            PatchOperationKind.UPSERT_TRUTH_ASSESSMENT: self._upsert_truth_assessment,
        }
        handler = handlers.get(operation.kind)
        if handler is None:
            raise StoreValidationError(f"unsupported patch operation {operation.kind}")
        handler(operation)

    def _check_expected(self, table: str, id_field: str, target: str, expected: int | None) -> None:
        if expected is None:
            return
        row = self._connection.execute(
            f"SELECT revision FROM {table} WHERE {id_field}=?", (target,)
        ).fetchone()
        actual = 0 if row is None else int(row["revision"])
        if actual != expected:
            raise StoreConflictError(f"{table}:{target}:{expected}!={actual}")

    def _upsert_referent(self, operation: PatchOperation) -> None:
        self._check_expected("referents", "referent_id", operation.target_ref, operation.expected_revision)
        value = operation.payload
        kind = ReferentKind(str(value["kind"]))
        revision = int(value.get("revision", 1))
        self._connection.execute(
            """INSERT INTO referents(
                referent_id, kind, type_refs_json, payload_json, scope_ref,
                context_ref, provenance_json, metadata_json, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(referent_id) DO UPDATE SET
                kind=excluded.kind,
                type_refs_json=excluded.type_refs_json,
                payload_json=excluded.payload_json,
                scope_ref=excluded.scope_ref,
                context_ref=excluded.context_ref,
                provenance_json=excluded.provenance_json,
                metadata_json=excluded.metadata_json,
                revision=MAX(referents.revision + 1, excluded.revision)
            """,
            (
                operation.target_ref,
                kind.value,
                _json(value.get("type_refs", ())),
                _json(value.get("payload")) if value.get("payload") is not None else None,
                str(value.get("scope_ref", "global")),
                str(value.get("context_ref", "actual")),
                _json(value.get("provenance", ())),
                _json(value.get("metadata", {})),
                revision,
            ),
        )

    def _add_alias(self, operation: PatchOperation) -> None:
        value = operation.payload
        referent_ref = str(value.get("referent_ref") or operation.target_ref)
        if self._connection.execute(
            "SELECT 1 FROM referents WHERE referent_id=?", (referent_ref,)
        ).fetchone() is None:
            raise StoreValidationError(f"alias target does not exist: {referent_ref}")
        self._connection.execute(
            """INSERT INTO aliases(
                language_tag, normalized_surface, referent_ref, confidence,
                source_ref, revision
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(language_tag, normalized_surface, referent_ref) DO UPDATE SET
                confidence=MAX(aliases.confidence, excluded.confidence),
                source_ref=excluded.source_ref,
                revision=aliases.revision + 1
            """,
            (
                str(value["language_tag"]),
                normalize_surface(str(value["surface"])),
                referent_ref,
                float(value.get("confidence", 1.0)),
                str(value.get("source_ref", "unknown")),
                int(value.get("revision", 1)),
            ),
        )

    def _upsert_predication(self, operation: PatchOperation) -> None:
        self._check_expected("predications", "predication_id", operation.target_ref, operation.expected_revision)
        value = operation.payload
        bindings = tuple(value.get("bindings", ()))
        self._connection.execute(
            """INSERT INTO predications(
                predication_id, predicate_schema_ref, bindings_json, context_ref,
                evidence_json, assumptions_json, confidence, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(predication_id) DO UPDATE SET
                predicate_schema_ref=excluded.predicate_schema_ref,
                bindings_json=excluded.bindings_json,
                context_ref=excluded.context_ref,
                evidence_json=excluded.evidence_json,
                assumptions_json=excluded.assumptions_json,
                confidence=excluded.confidence,
                revision=predications.revision + 1
            """,
            (
                operation.target_ref,
                str(value["predicate_schema_ref"]),
                _json(bindings),
                str(value.get("context_ref", "actual")),
                _json(value.get("source_evidence_refs", ())),
                _json(value.get("assumptions", ())),
                float(value.get("confidence", 1.0)),
                int(value.get("revision", 1)),
            ),
        )
        self._connection.execute("DELETE FROM port_fillers WHERE predication_ref=?", (operation.target_ref,))
        for binding in bindings:
            port_id = str(binding["port_id"])
            refs = tuple(map(str, binding.get("referent_refs", ())))
            if refs:
                for ordinal, ref in enumerate(refs):
                    if self._connection.execute(
                        "SELECT 1 FROM referents WHERE referent_id=?", (ref,)
                    ).fetchone() is None:
                        raise StoreValidationError(f"port filler does not exist: {ref}")
                    self._connection.execute(
                        "INSERT INTO port_fillers VALUES (?, ?, ?, NULL, ?)",
                        (operation.target_ref, port_id, ref, ordinal),
                    )
            else:
                variable = binding.get("open_variable_ref")
                if not variable:
                    raise StoreValidationError("binding requires referent or open variable")
                self._connection.execute(
                    "INSERT INTO port_fillers VALUES (?, ?, NULL, ?, 0)",
                    (operation.target_ref, port_id, str(variable)),
                )

    def _upsert_proposition(self, operation: PatchOperation) -> None:
        value = dict(operation.payload)
        value.setdefault("kind", ReferentKind.PROPOSITION.value)
        self._upsert_referent(
            PatchOperation(
                operation_id=operation.operation_id,
                kind=PatchOperationKind.UPSERT_REFERENT,
                target_ref=operation.target_ref,
                payload=value,
                expected_revision=operation.expected_revision,
                reversible=operation.reversible,
            )
        )
        payload = value.get("payload") or {}
        predication_refs = tuple(map(str, payload.get("predication_refs", ())))
        self._connection.execute(
            "DELETE FROM proposition_contents WHERE proposition_ref=?", (operation.target_ref,)
        )
        for ordinal, ref in enumerate(predication_refs):
            if self._connection.execute(
                "SELECT 1 FROM predications WHERE predication_id=?", (ref,)
            ).fetchone() is None:
                raise StoreValidationError(f"proposition predication missing: {ref}")
            self._connection.execute(
                "INSERT INTO proposition_contents VALUES (?, ?, ?)",
                (operation.target_ref, ref, ordinal),
            )

    def _upsert_knowledge(self, operation: PatchOperation) -> None:
        self._check_expected("knowledge", "knowledge_id", operation.target_ref, operation.expected_revision)
        value = operation.payload
        proposition_ref = str(value["proposition_ref"])
        if self._connection.execute(
            "SELECT 1 FROM referents WHERE referent_id=? AND kind=?",
            (proposition_ref, ReferentKind.PROPOSITION.value),
        ).fetchone() is None:
            raise StoreValidationError(f"knowledge proposition missing: {proposition_ref}")
        self._connection.execute(
            """INSERT INTO knowledge(
                knowledge_id, proposition_ref, truth_status, context_ref,
                source_refs_json, evidence_refs_json, confidence, scope_ref,
                sensitivity, permission_ref, valid_time_ref, superseded_by,
                metadata_json, revision, root_lineage_refs_json,
                derivation_refs_json, valid_from, valid_to
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(knowledge_id) DO UPDATE SET
                proposition_ref=excluded.proposition_ref,
                truth_status=excluded.truth_status,
                context_ref=excluded.context_ref,
                source_refs_json=excluded.source_refs_json,
                evidence_refs_json=excluded.evidence_refs_json,
                confidence=excluded.confidence,
                scope_ref=excluded.scope_ref,
                sensitivity=excluded.sensitivity,
                permission_ref=excluded.permission_ref,
                valid_time_ref=excluded.valid_time_ref,
                superseded_by=excluded.superseded_by,
                metadata_json=excluded.metadata_json,
                root_lineage_refs_json=excluded.root_lineage_refs_json,
                derivation_refs_json=excluded.derivation_refs_json,
                valid_from=excluded.valid_from,
                valid_to=excluded.valid_to,
                revision=knowledge.revision + 1
            """,
            (
                operation.target_ref,
                proposition_ref,
                str(value.get("truth_status", TruthStatus.SUPPORTED.value)),
                str(value.get("context_ref", "actual")),
                _json(value.get("source_refs", ())),
                _json(value.get("evidence_refs", ())),
                float(value.get("confidence", 1.0)),
                str(value.get("scope_ref", "global")),
                str(value.get("sensitivity", "normal")),
                str(value.get("permission_ref", "conversation")),
                value.get("valid_time_ref"),
                value.get("superseded_by"),
                _json(value.get("metadata", {})),
                int(value.get("revision", 1)),
                _json(value.get("root_lineage_refs", ())),
                _json(value.get("derivation_refs", ())),
                value.get("valid_from"),
                value.get("valid_to"),
            ),
        )

    def _supersede_knowledge(self, operation: PatchOperation) -> None:
        self._check_expected("knowledge", "knowledge_id", operation.target_ref, operation.expected_revision)
        replacement = str(operation.payload["superseded_by"])
        changed = self._connection.execute(
            "UPDATE knowledge SET superseded_by=?, revision=revision+1 WHERE knowledge_id=?",
            (replacement, operation.target_ref),
        ).rowcount
        if changed != 1:
            raise StoreValidationError(f"knowledge not found: {operation.target_ref}")

    def _retract_support(self, operation: PatchOperation) -> None:
        value = operation.payload
        source_ref = str(value["source_ref"])
        row = self._connection.execute(
            "SELECT source_refs_json FROM knowledge WHERE knowledge_id=?", (operation.target_ref,)
        ).fetchone()
        if row is None:
            raise StoreValidationError(f"knowledge not found: {operation.target_ref}")
        sources = [item for item in json.loads(row["source_refs_json"]) if item != source_ref]
        status = TruthStatus.UNDETERMINED.value if not sources else None
        self._connection.execute(
            "UPDATE knowledge SET source_refs_json=?, truth_status=COALESCE(?, truth_status), revision=revision+1 WHERE knowledge_id=?",
            (_json(sources), status, operation.target_ref),
        )

    def _upsert_discourse_turn(self, operation: PatchOperation) -> None:
        value = operation.payload
        ordinal = int(value.get("ordinal") or self._next_turn_ordinal(str(value["context_ref"])))
        self._connection.execute(
            """INSERT INTO discourse_turns VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(turn_id) DO UPDATE SET
                proposition_refs_json=excluded.proposition_refs_json,
                metadata_json=excluded.metadata_json
            """,
            (
                operation.target_ref,
                str(value["context_ref"]),
                str(value["speaker_ref"]),
                _json(value.get("proposition_refs", ())),
                str(value.get("language_tag", "und")),
                str(value.get("raw_observation_ref", "")),
                ordinal,
                _json(value.get("metadata", {})),
            ),
        )

    def _upsert_mention(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO mentions VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mention_id) DO UPDATE SET
                referent_ref=excluded.referent_ref,
                salience=excluded.salience,
                grammatical_role=excluded.grammatical_role,
                metadata_json=excluded.metadata_json
            """,
            (
                operation.target_ref,
                str(value["context_ref"]),
                str(value["turn_ref"]),
                str(value["referent_ref"]),
                float(value.get("salience", 0.5)),
                str(value.get("grammatical_role", "mention")),
                _json(value.get("metadata", {})),
            ),
        )

    def _upsert_open_question(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO open_questions VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(question_id) DO UPDATE SET
                proposition_ref=excluded.proposition_ref,
                variable_refs_json=excluded.variable_refs_json,
                status=excluded.status,
                metadata_json=excluded.metadata_json
            """,
            (
                operation.target_ref,
                str(value["context_ref"]),
                str(value["proposition_ref"]),
                _json(value.get("variable_refs", ())),
                str(value.get("status", "open")),
                _json(value.get("metadata", {})),
            ),
        )

    def _close_open_question(self, operation: PatchOperation) -> None:
        self._connection.execute(
            "UPDATE open_questions SET status='closed' WHERE question_id=?",
            (operation.target_ref,),
        )

    def _upsert_world_track(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO world_tracks VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                referent_ref=excluded.referent_ref,
                state_json=excluded.state_json,
                confidence=excluded.confidence,
                observed_at=excluded.observed_at,
                revision=world_tracks.revision+1
            """,
            (
                operation.target_ref,
                str(value["context_ref"]),
                str(value["referent_ref"]),
                str(value.get("modality", "unknown")),
                _json(value.get("state", {})),
                float(value.get("confidence", 0.5)),
                str(value.get("observed_at", "")),
                int(value.get("revision", 1)),
            ),
        )

    def _upsert_schema_candidate(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO schema_candidates VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_ref) DO UPDATE SET
                status=excluded.status,
                payload_json=excluded.payload_json,
                evidence_refs_json=excluded.evidence_refs_json,
                revision=schema_candidates.revision+1
            """,
            (
                operation.target_ref,
                str(value.get("scope_ref", "session")),
                str(value.get("status", "candidate")),
                _json(value.get("payload", {})),
                _json(value.get("evidence_refs", ())),
                int(value.get("revision", 1)),
            ),
        )

    def _upsert_rule_candidate(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO rule_candidates VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_ref) DO UPDATE SET
                status=excluded.status,
                payload_json=excluded.payload_json,
                evidence_refs_json=excluded.evidence_refs_json,
                revision=rule_candidates.revision+1
            """,
            (
                operation.target_ref,
                str(value.get("scope_ref", "session")),
                str(value.get("status", "candidate")),
                _json(value.get("payload", {})),
                _json(value.get("evidence_refs", ())),
                int(value.get("revision", 1)),
            ),
        )

    def _upsert_evidence(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO evidence_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(evidence_id) DO UPDATE SET
                source_ref=excluded.source_ref,
                confidence=MAX(evidence_records.confidence, excluded.confidence),
                lineage_ref=excluded.lineage_ref,
                span_start=excluded.span_start,
                span_end=excluded.span_end,
                metadata_json=excluded.metadata_json,
                revision=evidence_records.revision+1
            """,
            (operation.target_ref, str(value.get("source_ref", "unknown")),
             float(value.get("confidence", 1.0)), str(value.get("lineage_ref", "")),
             value.get("span_start"), value.get("span_end"),
             _json(value.get("metadata", {})), int(value.get("revision", 1))),
        )

    def _upsert_schema_revision(self, operation: PatchOperation) -> None:
        value = operation.payload
        revision = int(value.get("revision", 1))
        self._connection.execute(
            """INSERT INTO schema_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(schema_ref, revision) DO UPDATE SET
                status=excluded.status, payload_json=excluded.payload_json,
                field_provenance_json=excluded.field_provenance_json,
                evidence_refs_json=excluded.evidence_refs_json,
                support_lineage_refs_json=excluded.support_lineage_refs_json,
                counterevidence_refs_json=excluded.counterevidence_refs_json,
                confidence=excluded.confidence, permission_ref=excluded.permission_ref,
                dependency_refs_json=excluded.dependency_refs_json,
                competence_case_refs_json=excluded.competence_case_refs_json,
                environment_fingerprint=excluded.environment_fingerprint,
                competence_passed=excluded.competence_passed,
                epistemically_admissible=excluded.epistemically_admissible
            """,
            (operation.target_ref, revision, str(value.get("schema_kind", "learned")),
             str(value.get("status", "candidate")), str(value.get("scope_ref", "session")),
             _json(value.get("payload", {})), _json(value.get("field_provenance", {})),
             _json(value.get("evidence_refs", ())), _json(value.get("support_lineage_refs", ())),
             _json(value.get("counterevidence_refs", ())), float(value.get("confidence", 0.5)),
             str(value.get("permission_ref", "private_learning")),
             _json(value.get("dependency_refs", ())), _json(value.get("competence_case_refs", ())),
             str(value.get("environment_fingerprint", "")),
             int(bool(value.get("competence_passed", False))),
             int(bool(value.get("epistemically_admissible", False)))),
        )

    def _upsert_rule_revision(self, operation: PatchOperation) -> None:
        value = operation.payload
        revision = int(value.get("revision", 1))
        self._connection.execute(
            """INSERT INTO rule_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rule_ref, revision) DO UPDATE SET
                status=excluded.status, payload_json=excluded.payload_json,
                evidence_refs_json=excluded.evidence_refs_json,
                support_lineage_refs_json=excluded.support_lineage_refs_json,
                confidence=excluded.confidence, environment_fingerprint=excluded.environment_fingerprint
            """,
            (operation.target_ref, revision, str(value.get("status", "candidate")),
             str(value.get("scope_ref", "session")), _json(value.get("payload", {})),
             _json(value.get("evidence_refs", ())), _json(value.get("support_lineage_refs", ())),
             float(value.get("confidence", 0.5)), str(value.get("environment_fingerprint", ""))),
        )

    def _add_dependency(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO dependencies VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dependency_id) DO UPDATE SET active=excluded.active, metadata_json=excluded.metadata_json""",
            (operation.target_ref, str(value["dependent_ref"]), str(value["dependency_ref"]),
             str(value.get("dependency_kind", "semantic")), int(value.get("dependent_revision", 1)),
             int(value.get("dependency_revision", 1)), int(bool(value.get("active", True))),
             _json(value.get("metadata", {}))),
        )

    def _record_invalidation(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            "INSERT OR REPLACE INTO invalidations VALUES (?, ?, ?, ?, ?, ?, ?)",
            (operation.target_ref, str(value["target_ref"]), str(value["reason"]),
             str(value["cause_ref"]), str(value.get("prior_fingerprint", "")),
             int(value.get("invalidated_at_revision", self.revision)), _json(value.get("metadata", {}))),
        )
        self._connection.execute(
            "UPDATE dependencies SET active=0 WHERE dependent_ref=?", (str(value["target_ref"]),)
        )

    def _upsert_capability_observation(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            """INSERT INTO capability_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(observation_id) DO UPDATE SET
                available=excluded.available, confidence=excluded.confidence,
                resource_state_json=excluded.resource_state_json, valid_until=excluded.valid_until,
                evidence_refs_json=excluded.evidence_refs_json, revision=capability_observations.revision+1""",
            (operation.target_ref, str(value["capability_ref"]), int(bool(value.get("available", False))),
             float(value.get("confidence", 0.5)), str(value.get("source_ref", "runtime")),
             str(value.get("context_ref", "actual")), _json(value.get("resource_state", {})),
             value.get("valid_until"), _json(value.get("evidence_refs", ())), int(value.get("revision", 1))),
        )

    def _upsert_operation_ledger(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            "INSERT OR REPLACE INTO operation_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (operation.target_ref, str(value["plan_ref"]), str(value["operation_ref"]),
             str(value["status"]), str(value.get("authorization_fingerprint", "")),
             _json(value.get("capability_evidence_refs", ())),
             _json(value.get("observed_proposition_refs", ())),
             _json(value.get("errors", ())), _json(value.get("metadata", {}))),
        )

    def _upsert_emission_ledger(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            "INSERT OR REPLACE INTO emission_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (operation.target_ref, str(value["plan_ref"]), str(value["proof_ref"]),
             str(value["language_tag"]), str(value["surface_hash"]),
             int(bool(value.get("authorized", False))),
             _json(value.get("covered_semantic_refs", ())),
             _json(value.get("schema_revisions", {})), _json(value.get("reasons", ()))),
        )

    def _upsert_truth_assessment(self, operation: PatchOperation) -> None:
        value = operation.payload
        self._connection.execute(
            "INSERT OR REPLACE INTO truth_assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (operation.target_ref, str(value["proposition_signature"]), str(value["context_ref"]),
             str(value["truth_status"]), _json(value.get("support_knowledge_refs", ())),
             _json(value.get("opposition_knowledge_refs", ())), float(value.get("confidence", 0.0)),
             value.get("valid_time_ref"), _json(value.get("evidence_refs", ())),
             int(value.get("store_revision", self.revision))),
        )

    def _next_turn_ordinal(self, context_ref: str) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(MAX(ordinal), 0) AS value FROM discourse_turns WHERE context_ref=?",
            (context_ref,),
        ).fetchone()
        return int(row["value"]) + 1

    def get_referent(self, referent_ref: str) -> Referent | None:
        row = self._connection.execute(
            "SELECT * FROM referents WHERE referent_id=?", (referent_ref,)
        ).fetchone()
        return _referent_from_row(row) if row is not None else None

    def get_predication(self, predication_ref: str) -> Predication | None:
        row = self._connection.execute(
            "SELECT * FROM predications WHERE predication_id=?", (predication_ref,)
        ).fetchone()
        return _predication_from_row(row) if row is not None else None

    def resolve_alias(self, surface: str, language_tag: str, limit: int = 8) -> tuple[tuple[Referent, float], ...]:
        rows = self._connection.execute(
            """SELECT a.confidence, r.* FROM aliases a
            JOIN referents r ON r.referent_id=a.referent_ref
            WHERE a.language_tag IN (?, 'und') AND a.normalized_surface=?
            ORDER BY a.confidence DESC LIMIT ?""",
            (language_tag, normalize_surface(surface), limit),
        ).fetchall()
        return tuple((_referent_from_row(row), float(row["confidence"])) for row in rows)

    def aliases_for(self, referent_ref: str, language_tag: str) -> tuple[str, ...]:
        rows = self._connection.execute(
            """SELECT normalized_surface FROM aliases
            WHERE referent_ref=? AND language_tag IN (?, 'und')
            ORDER BY confidence DESC, normalized_surface""",
            (referent_ref, language_tag),
        ).fetchall()
        return tuple(str(row["normalized_surface"]) for row in rows)

    def recent_mentions(self, context_ref: str, limit: int = 20) -> tuple[tuple[Referent, float, str], ...]:
        rows = self._connection.execute(
            """SELECT m.salience, m.grammatical_role, r.* FROM mentions m
            JOIN referents r ON r.referent_id=m.referent_ref
            WHERE m.context_ref=? ORDER BY m.salience DESC LIMIT ?""",
            (context_ref, limit),
        ).fetchall()
        return tuple(
            (_referent_from_row(row), float(row["salience"]), str(row["grammatical_role"]))
            for row in rows
        )

    def recent_turns(self, context_ref: str, limit: int = 10) -> tuple[Mapping[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT * FROM discourse_turns WHERE context_ref=? ORDER BY ordinal DESC LIMIT ?",
            (context_ref, limit),
        ).fetchall()
        return tuple(
            {
                "turn_id": row["turn_id"],
                "speaker_ref": row["speaker_ref"],
                "proposition_refs": tuple(json.loads(row["proposition_refs_json"])),
                "language_tag": row["language_tag"],
                "ordinal": row["ordinal"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        )

    def open_questions(self, context_ref: str) -> tuple[Mapping[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT * FROM open_questions WHERE context_ref=? AND status='open'",
            (context_ref,),
        ).fetchall()
        return tuple(
            {
                "question_id": row["question_id"],
                "proposition_ref": row["proposition_ref"],
                "variable_refs": tuple(json.loads(row["variable_refs_json"])),
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        )

    def world_tracks(self, context_ref: str) -> tuple[Mapping[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT * FROM world_tracks WHERE context_ref=? ORDER BY confidence DESC",
            (context_ref,),
        ).fetchall()
        return tuple(
            {
                "track_id": row["track_id"],
                "referent_ref": row["referent_ref"],
                "modality": row["modality"],
                "state": json.loads(row["state_json"]),
                "confidence": row["confidence"],
                "observed_at": row["observed_at"],
            }
            for row in rows
        )

    def knowledge_record(self, knowledge_id: str) -> KnowledgeRecord | None:
        row = self._connection.execute(
            "SELECT * FROM knowledge WHERE knowledge_id=?", (knowledge_id,)
        ).fetchone()
        return _knowledge_from_row(row) if row is not None else None

    def active_knowledge(self, *, context_ref: str | None = None, scope_refs: Iterable[str] = ()) -> tuple[KnowledgeRecord, ...]:
        clauses = ["superseded_by IS NULL"]
        params: list[Any] = []
        if context_ref is not None:
            clauses.append("context_ref IN (?, 'actual')")
            params.append(context_ref)
        scopes = tuple(scope_refs)
        if scopes:
            clauses.append("scope_ref IN (%s)" % ",".join("?" for _ in scopes))
            params.extend(scopes)
        rows = self._connection.execute(
            "SELECT * FROM knowledge WHERE " + " AND ".join(clauses) + " ORDER BY confidence DESC",
            tuple(params),
        ).fetchall()
        return tuple(_knowledge_from_row(row) for row in rows)

    def knowledge_for_predicate(
        self,
        predicate_schema_ref: str,
        *,
        context_ref: str | None = None,
        scope_refs: Iterable[str] = (),
    ) -> tuple[tuple[KnowledgeRecord, Predication, Referent], ...]:
        clauses = ["p.predicate_schema_ref=?", "k.superseded_by IS NULL"]
        params: list[Any] = [predicate_schema_ref]
        if context_ref is not None:
            clauses.append("k.context_ref IN (?, 'actual')")
            params.append(context_ref)
        scopes = tuple(scope_refs)
        if scopes:
            clauses.append("k.scope_ref IN (%s)" % ",".join("?" for _ in scopes))
            params.extend(scopes)
        rows = self._connection.execute(
            """SELECT k.knowledge_id, p.predication_id, r.referent_id
            FROM knowledge k
            JOIN proposition_contents pc ON pc.proposition_ref=k.proposition_ref
            JOIN predications p ON p.predication_id=pc.predication_ref
            JOIN referents r ON r.referent_id=k.proposition_ref
            WHERE """ + " AND ".join(clauses) + " ORDER BY k.confidence DESC",
            tuple(params),
        ).fetchall()
        result = []
        for row in rows:
            knowledge_row = self._connection.execute(
                "SELECT * FROM knowledge WHERE knowledge_id=?", (row["knowledge_id"],)
            ).fetchone()
            predication_row = self._connection.execute(
                "SELECT * FROM predications WHERE predication_id=?", (row["predication_id"],)
            ).fetchone()
            proposition_row = self._connection.execute(
                "SELECT * FROM referents WHERE referent_id=?", (row["referent_id"],)
            ).fetchone()
            result.append((
                _knowledge_from_row(knowledge_row),
                _predication_from_row(predication_row),
                _referent_from_row(proposition_row),
            ))
        return tuple(result)

    def latest_active_for_signature(
        self,
        predicate_ref: str,
        fixed_ports: Mapping[str, str],
        *,
        context_ref: str | None = None,
        scope_refs: Iterable[str] = (),
    ) -> tuple[KnowledgeRecord, ...]:
        matches: list[KnowledgeRecord] = []
        for knowledge, predication, _ in self.knowledge_for_predicate(
            predicate_ref, context_ref=context_ref, scope_refs=scope_refs
        ):
            bound = {
                binding.port_id: binding.referent_refs[0]
                for binding in predication.bindings
                if len(binding.referent_refs) == 1
            }
            if all(bound.get(port) == ref for port, ref in fixed_ports.items()):
                matches.append(knowledge)
        return tuple(matches)

    def hydrate_candidates(self) -> tuple[tuple[str, Mapping[str, Any]], tuple[str, Mapping[str, Any]]]:
        schemas = tuple(
            (row["candidate_ref"], json.loads(row["payload_json"]))
            for row in self._connection.execute("SELECT * FROM schema_candidates").fetchall()
        )
        rules = tuple(
            (row["candidate_ref"], json.loads(row["payload_json"]))
            for row in self._connection.execute("SELECT * FROM rule_candidates").fetchall()
        )
        return schemas, rules


    def schema_candidate(self, candidate_ref: str) -> Mapping[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM schema_candidates WHERE candidate_ref=?", (candidate_ref,)
        ).fetchone()
        if row is None:
            return None
        return {
            "candidate_ref": row["candidate_ref"], "scope_ref": row["scope_ref"],
            "status": row["status"], "payload": json.loads(row["payload_json"]),
            "evidence_refs": tuple(json.loads(row["evidence_refs_json"])),
            "revision": int(row["revision"]),
        }

    def rule_candidate(self, candidate_ref: str) -> Mapping[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM rule_candidates WHERE candidate_ref=?", (candidate_ref,)
        ).fetchone()
        if row is None:
            return None
        return {
            "candidate_ref": row["candidate_ref"], "scope_ref": row["scope_ref"],
            "status": row["status"], "payload": json.loads(row["payload_json"]),
            "evidence_refs": tuple(json.loads(row["evidence_refs_json"])),
            "revision": int(row["revision"]),
        }

    def latest_schema_revision(self, schema_ref: str, *, context_ref: str | None = None) -> Mapping[str, Any] | None:
        params: list[Any] = [schema_ref]
        clause = "schema_ref=?"
        if context_ref is not None:
            clause += " AND scope_ref IN (?, 'global')"
            params.append(context_ref)
        row = self._connection.execute(
            "SELECT * FROM schema_revisions WHERE " + clause + " ORDER BY revision DESC LIMIT 1",
            tuple(params),
        ).fetchone()
        return _schema_revision_from_row(row) if row is not None else None

    def latest_rule_revisions(self, *, context_ref: str | None = None) -> tuple[Mapping[str, Any], ...]:
        params: tuple[Any, ...] = ()
        where = ""
        if context_ref is not None:
            where = "WHERE scope_ref IN (?, 'global')"
            params = (context_ref,)
        rows = self._connection.execute(
            f"""SELECT r.* FROM rule_revisions r
            JOIN (SELECT rule_ref, MAX(revision) AS max_revision FROM rule_revisions {where} GROUP BY rule_ref) latest
              ON latest.rule_ref=r.rule_ref AND latest.max_revision=r.revision""", params
        ).fetchall()
        return tuple(_rule_revision_from_row(row) for row in rows)

    def all_schema_revisions(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(_schema_revision_from_row(row) for row in self._connection.execute(
            "SELECT * FROM schema_revisions ORDER BY schema_ref, revision"
        ).fetchall())

    def dependents_of(self, dependency_ref: str) -> tuple[Mapping[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT * FROM dependencies WHERE dependency_ref=? AND active=1", (dependency_ref,)
        ).fetchall()
        return tuple({
            "dependency_id": row["dependency_id"],
            "dependent_ref": row["dependent_ref"],
            "dependency_ref": row["dependency_ref"],
            "dependency_kind": row["dependency_kind"],
            "dependent_revision": int(row["dependent_revision"]),
            "dependency_revision": int(row["dependency_revision"]),
            "active": bool(row["active"]),
            "metadata": json.loads(row["metadata_json"]),
        } for row in rows)

    def capability_observations(self, context_ref: str) -> tuple[Mapping[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT * FROM capability_observations WHERE context_ref IN (?, 'actual') ORDER BY confidence DESC",
            (context_ref,),
        ).fetchall()
        return tuple({
            "observation_id": row["observation_id"], "capability_ref": row["capability_ref"],
            "available": bool(row["available"]), "confidence": float(row["confidence"]),
            "source_ref": row["source_ref"], "context_ref": row["context_ref"],
            "resource_state": json.loads(row["resource_state_json"]),
            "valid_until": row["valid_until"],
            "evidence_refs": tuple(json.loads(row["evidence_refs_json"])),
        } for row in rows)

    def latest_truth_assessment(self, proposition_signature: str, context_ref: str) -> Mapping[str, Any] | None:
        row = self._connection.execute(
            """SELECT * FROM truth_assessments WHERE proposition_signature=? AND context_ref=?
            ORDER BY store_revision DESC LIMIT 1""", (proposition_signature, context_ref)
        ).fetchone()
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}

    def evidence_record(self, evidence_id: str) -> Mapping[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM evidence_records WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "evidence_id": row["evidence_id"],
            "source_ref": row["source_ref"],
            "confidence": float(row["confidence"]),
            "lineage_ref": row["lineage_ref"],
            "span_start": row["span_start"],
            "span_end": row["span_end"],
            "metadata": json.loads(row["metadata_json"]),
            "revision": int(row["revision"]),
        }

    def evidence_by_lineage(self, lineage_ref: str) -> tuple[Mapping[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT * FROM evidence_records WHERE lineage_ref=? ORDER BY confidence DESC",
            (lineage_ref,),
        ).fetchall()
        return tuple(self.evidence_record(str(row["evidence_id"])) for row in rows)

    def invalidations_for(self, target_ref: str | None = None) -> tuple[Mapping[str, Any], ...]:
        if target_ref is None:
            rows = self._connection.execute(
                "SELECT * FROM invalidations ORDER BY invalidated_at_revision DESC"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM invalidations WHERE target_ref=? ORDER BY invalidated_at_revision DESC",
                (target_ref,),
            ).fetchall()
        return tuple({
            "invalidation_id": row["invalidation_id"],
            "target_ref": row["target_ref"],
            "reason": row["reason"],
            "cause_ref": row["cause_ref"],
            "prior_fingerprint": row["prior_fingerprint"],
            "invalidated_at_revision": int(row["invalidated_at_revision"]),
            "metadata": json.loads(row["metadata_json"]),
        } for row in rows)

    def operation_ledgers(self, *, plan_ref: str | None = None) -> tuple[Mapping[str, Any], ...]:
        if plan_ref is None:
            rows = self._connection.execute("SELECT * FROM operation_ledger ORDER BY rowid").fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM operation_ledger WHERE plan_ref=? ORDER BY rowid", (plan_ref,)
            ).fetchall()
        return tuple({
            "ledger_ref": row["ledger_ref"],
            "plan_ref": row["plan_ref"],
            "operation_ref": row["operation_ref"],
            "status": row["status"],
            "authorization_fingerprint": row["authorization_fingerprint"],
            "capability_evidence_refs": tuple(json.loads(row["capability_evidence_refs_json"])),
            "observed_proposition_refs": tuple(json.loads(row["observed_proposition_refs_json"])),
            "errors": tuple(json.loads(row["errors_json"])),
            "metadata": json.loads(row["metadata_json"]),
        } for row in rows)

    def emission_ledgers(self, *, plan_ref: str | None = None) -> tuple[Mapping[str, Any], ...]:
        if plan_ref is None:
            rows = self._connection.execute("SELECT * FROM emission_ledger ORDER BY rowid").fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM emission_ledger WHERE plan_ref=? ORDER BY rowid", (plan_ref,)
            ).fetchall()
        return tuple({
            "ledger_ref": row["ledger_ref"],
            "plan_ref": row["plan_ref"],
            "proof_ref": row["proof_ref"],
            "language_tag": row["language_tag"],
            "surface_hash": row["surface_hash"],
            "authorized": bool(row["authorized"]),
            "covered_semantic_refs": tuple(json.loads(row["covered_semantic_refs_json"])),
            "schema_revisions": json.loads(row["schema_revisions_json"]),
            "reasons": tuple(json.loads(row["reasons_json"])),
        } for row in rows)

    def audit_counts(self) -> Mapping[str, int]:
        """Return stable record-family counts for diagnostics and release proof."""
        tables = (
            "referents", "predications", "knowledge", "aliases",
            "discourse_turns", "mentions", "open_questions", "world_tracks",
            "schema_candidates", "rule_candidates", "schema_revisions", "rule_revisions",
            "evidence_records", "dependencies", "invalidations",
            "capability_observations", "operation_ledger", "emission_ledger",
            "truth_assessments", "patches",
        )
        return {
            table: int(self._connection.execute(
                f"SELECT COUNT(*) AS value FROM {table}"
            ).fetchone()["value"])
            for table in tables
        }

    def truth_assessments(self, context_ref: str | None = None) -> tuple[Mapping[str, Any], ...]:
        if context_ref is None:
            rows = self._connection.execute(
                "SELECT * FROM truth_assessments ORDER BY store_revision DESC"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM truth_assessments WHERE context_ref=? ORDER BY store_revision DESC",
                (context_ref,),
            ).fetchall()
        return tuple({
            "assessment_id": row["assessment_id"],
            "proposition_signature": row["proposition_signature"],
            "context_ref": row["context_ref"],
            "truth_status": row["truth_status"],
            "support_knowledge_refs": tuple(json.loads(row["support_knowledge_refs_json"])),
            "opposition_knowledge_refs": tuple(json.loads(row["opposition_knowledge_refs_json"])),
            "confidence": float(row["confidence"]),
            "valid_time_ref": row["valid_time_ref"],
            "evidence_refs": tuple(json.loads(row["evidence_refs_json"])),
            "store_revision": int(row["store_revision"]),
        } for row in rows)


def normalize_surface(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _json(value: Any) -> str:
    return json.dumps(canonical_data(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _referent_from_row(row: sqlite3.Row) -> Referent:
    return Referent(
        referent_id=str(row["referent_id"]),
        kind=ReferentKind(str(row["kind"])),
        type_refs=tuple(json.loads(row["type_refs_json"])),
        payload=json.loads(row["payload_json"]) if row["payload_json"] else None,
        scope_ref=str(row["scope_ref"]),
        context_ref=str(row["context_ref"]),
        provenance=(),
        revision=int(row["revision"]),
        metadata=json.loads(row["metadata_json"]),
    )


def _predication_from_row(row: sqlite3.Row) -> Predication:
    bindings = []
    for value in json.loads(row["bindings_json"]):
        refs = tuple(value.get("referent_refs", ()))
        variable = value.get("open_variable_ref")
        bindings.append(PortBinding(
            port_id=str(value["port_id"]),
            referent_refs=refs,
            open_variable_ref=variable,
            confidence=float(value.get("confidence", 1.0)),
            evidence_refs=tuple(value.get("evidence_refs", ())),
            assumptions=tuple(value.get("assumptions", ())),
        ))
    return Predication(
        predication_id=str(row["predication_id"]),
        predicate_schema_ref=str(row["predicate_schema_ref"]),
        bindings=tuple(bindings),
        context_ref=str(row["context_ref"]),
        source_evidence_refs=tuple(json.loads(row["evidence_json"])),
        assumptions=tuple(json.loads(row["assumptions_json"])),
        confidence=float(row["confidence"]),
        revision=int(row["revision"]),
    )



def _schema_revision_from_row(row: sqlite3.Row) -> Mapping[str, Any]:
    return {
        "schema_ref": row["schema_ref"], "revision": int(row["revision"]),
        "schema_kind": row["schema_kind"], "status": row["status"],
        "scope_ref": row["scope_ref"], "payload": json.loads(row["payload_json"]),
        "field_provenance": json.loads(row["field_provenance_json"]),
        "evidence_refs": tuple(json.loads(row["evidence_refs_json"])),
        "support_lineage_refs": tuple(json.loads(row["support_lineage_refs_json"])),
        "counterevidence_refs": tuple(json.loads(row["counterevidence_refs_json"])),
        "confidence": float(row["confidence"]), "permission_ref": row["permission_ref"],
        "dependency_refs": tuple(json.loads(row["dependency_refs_json"])),
        "competence_case_refs": tuple(json.loads(row["competence_case_refs_json"])),
        "environment_fingerprint": row["environment_fingerprint"],
        "competence_passed": bool(row["competence_passed"]),
        "epistemically_admissible": bool(row["epistemically_admissible"]),
    }


def _rule_revision_from_row(row: sqlite3.Row) -> Mapping[str, Any]:
    return {
        "rule_ref": row["rule_ref"], "revision": int(row["revision"]),
        "status": row["status"], "scope_ref": row["scope_ref"],
        "payload": json.loads(row["payload_json"]),
        "evidence_refs": tuple(json.loads(row["evidence_refs_json"])),
        "support_lineage_refs": tuple(json.loads(row["support_lineage_refs_json"])),
        "confidence": float(row["confidence"]),
        "environment_fingerprint": row["environment_fingerprint"],
    }

def _knowledge_from_row(row: sqlite3.Row) -> KnowledgeRecord:
    return KnowledgeRecord(
        knowledge_id=str(row["knowledge_id"]),
        proposition_ref=str(row["proposition_ref"]),
        truth_status=TruthStatus(str(row["truth_status"])),
        context_ref=str(row["context_ref"]),
        source_refs=tuple(json.loads(row["source_refs_json"])),
        evidence_refs=tuple(json.loads(row["evidence_refs_json"])),
        confidence=float(row["confidence"]),
        scope_ref=str(row["scope_ref"]),
        sensitivity=str(row["sensitivity"]),
        permission_ref=str(row["permission_ref"]),
        valid_time_ref=row["valid_time_ref"],
        revision=int(row["revision"]),
        superseded_by=row["superseded_by"],
        metadata=json.loads(row["metadata_json"]),
        root_lineage_refs=tuple(json.loads(row["root_lineage_refs_json"])) if "root_lineage_refs_json" in row.keys() else (),
        derivation_refs=tuple(json.loads(row["derivation_refs_json"])) if "derivation_refs_json" in row.keys() else (),
        valid_from=row["valid_from"] if "valid_from" in row.keys() else None,
        valid_to=row["valid_to"] if "valid_to" in row.keys() else None,
    )
