"""SQLite-backed persistent store for concept lattice and patch journal.

This is the durable backing for the concept lattice. Every GraphPatch that
passes consolidation eventually materializes as rows in concept_atoms and
is recorded in the append-only patch_journal.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from ..types.graph_patch import GraphPatch


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS concept_atoms (
    concept_id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    atom_kind TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'candidate_atom',
    aliases_json TEXT DEFAULT '[]',
    parents_json TEXT DEFAULT '[]',
    ports_json TEXT DEFAULT '[]',
    predicates_json TEXT DEFAULT '[]',
    affordances_json TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.5,
    stability REAL DEFAULT 0.0,
    evidence_json TEXT DEFAULT '[]',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS patch_journal (
    journal_id TEXT PRIMARY KEY,
    patch_id TEXT NOT NULL,
    source_graph_id TEXT,
    target TEXT NOT NULL,
    operations_json TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    reason TEXT,
    accepted INTEGER DEFAULT 0,
    applied_at REAL NOT NULL
);
"""


class PersistentLatticeStore:
    """SQLite-backed store for concept atoms and patch journal."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        for statement in _SCHEMA_SQL.split(";"):
            stripped = statement.strip()
            if stripped:
                self._conn.execute(stripped + ";")
        self._conn.commit()

    def load_all(self) -> dict[str, dict[str, Any]]:
        """Load all concept atoms into a dict keyed by concept_id."""
        result: dict[str, dict[str, Any]] = {}
        try:
            cursor = self._conn.execute("SELECT * FROM concept_atoms")
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                for json_field in ("aliases_json", "parents_json", "ports_json",
                                   "predicates_json", "affordances_json", "evidence_json"):
                    if isinstance(data.get(json_field), str):
                        data[json_field] = json.loads(data[json_field])
                result[data["concept_id"]] = data
        except sqlite3.OperationalError:
            pass
        return result

    def get_concept(self, concept_id: str) -> dict[str, Any] | None:
        """Get a single concept atom by ID, or None."""
        try:
            cursor = self._conn.execute(
                "SELECT * FROM concept_atoms WHERE concept_id = ?",
                (concept_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description]
            data = dict(zip(columns, row))
            for json_field in ("aliases_json", "parents_json", "ports_json",
                               "predicates_json", "affordances_json", "evidence_json"):
                if isinstance(data.get(json_field), str):
                    data[json_field] = json.loads(data[json_field])
            return data
        except sqlite3.OperationalError:
            return None

    def upsert_concept(self, concept_id: str, data: dict[str, Any]) -> None:
        """Insert or replace a concept atom row."""
        now = time.time()
        existing = self.get_concept(concept_id)
        merged = dict(existing) if existing else {}
        merged.update(data)
        merged.setdefault("created_at", now)
        merged["updated_at"] = now
        for json_field in ("aliases_json", "parents_json", "ports_json",
                           "predicates_json", "affordances_json", "evidence_json"):
            value = merged.get(json_field)
            if not isinstance(value, str):
                merged[json_field] = json.dumps(value or [])
        try:
            self._conn.execute(
                """INSERT OR REPLACE INTO concept_atoms
                   (concept_id, key, atom_kind, state, aliases_json, parents_json,
                    ports_json, predicates_json, affordances_json, confidence,
                    stability, evidence_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    concept_id,
                    str(merged.get("key", concept_id)),
                    str(merged.get("atom_kind", "entity")),
                    str(merged.get("state", "candidate_atom")),
                    str(merged.get("aliases_json", "[]")),
                    str(merged.get("parents_json", "[]")),
                    str(merged.get("ports_json", "[]")),
                    str(merged.get("predicates_json", "[]")),
                    str(merged.get("affordances_json", "[]")),
                    float(merged.get("confidence", 0.5)),
                    float(merged.get("stability", 0.0)),
                    str(merged.get("evidence_json", "[]")),
                    float(merged["created_at"]),
                    float(merged["updated_at"]),
                ),
            )
            self._conn.commit()
        except sqlite3.OperationalError as exc:
            print(f"[PersistentLatticeStore] upsert_concept error: {exc}", file=__import__("sys").stderr)

    def journal_patch(self, patch: GraphPatch, accepted: bool = True) -> None:
        """Append a GraphPatch to the patch_journal."""
        journal_id = f"jrnl_{uuid.uuid4().hex[:16]}"
        try:
            self._conn.execute(
                """INSERT INTO patch_journal
                   (journal_id, patch_id, source_graph_id, target, operations_json,
                    confidence, reason, accepted, applied_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    journal_id,
                    patch.id,
                    patch.source_graph_id,
                    patch.target,
                    json.dumps([op.to_dict() for op in patch.operations]),
                    patch.confidence,
                    patch.reason or "",
                    1 if accepted else 0,
                    time.time(),
                ),
            )
            self._conn.commit()
        except sqlite3.OperationalError as exc:
            print(f"[PersistentLatticeStore] journal_patch error: {exc}", file=__import__("sys").stderr)

    def close(self) -> None:
        self._conn.close()
