from __future__ import annotations
import sqlite3
import time
from ..types.model import Model, ModelKind, ModelStatus
from ..types.permission import Permission, PermissionScope, RetentionPolicy


def _row_to_model(row: sqlite3.Row) -> Model:
    return Model(
        id=row["id"],
        kind=ModelKind(row["kind"]),
        name=row["name"],
        description=row["description"],
        registry_key=row["registry_key"],
        confidence=row["confidence"],
        trust=row["trust"],
        utility=row["utility"],
        cost_estimate_ms=row["cost_estimate_ms"],
        risk=row["risk"],
        status=ModelStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        artifact_json=row["artifact_json"],
        permission=Permission(
            scope=PermissionScope(row["permission_scope"]),
            retention=RetentionPolicy(row["permission_retention"]),
            may_store=bool(row["permission_may_store"]),
            may_retrieve=bool(row["permission_may_retrieve"]),
            may_use=bool(row["permission_may_use"]),
        ),
        version=row["version"],
    )


class ModelStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def put(self, model: Model) -> None:
        perm = model.permission or Permission.public()
        self.conn.execute(
            """INSERT OR REPLACE INTO models
               (id, kind, name, description, registry_key, confidence, trust,
                utility, cost_estimate_ms, risk, status, created_at, updated_at,
                permission_scope, permission_retention, permission_may_store,
                permission_may_retrieve, permission_may_use, version, artifact_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                model.id, model.kind.value, model.name, model.description,
                model.registry_key, model.confidence, model.trust, model.utility,
                model.cost_estimate_ms, model.risk, model.status.value,
                model.created_at, model.updated_at,
                perm.scope.value, perm.retention.value,
                int(perm.may_store), int(perm.may_retrieve), int(perm.may_use),
                model.version, model.artifact_json,
            ),
        )
        self.conn.execute("DELETE FROM model_input_types WHERE model_id = ?", (model.id,))
        for t in model.input_types:
            self.conn.execute("INSERT INTO model_input_types (model_id, input_type) VALUES (?, ?)", (model.id, t))
        self.conn.execute("DELETE FROM model_output_types WHERE model_id = ?", (model.id,))
        for t in model.output_types:
            self.conn.execute("INSERT INTO model_output_types (model_id, output_type) VALUES (?, ?)", (model.id, t))
        self.conn.execute("DELETE FROM model_preconditions WHERE model_id = ?", (model.id,))
        for p in model.preconditions:
            self.conn.execute("INSERT INTO model_preconditions (model_id, precondition) VALUES (?, ?)", (model.id, p))
        self.conn.execute("DELETE FROM model_effects WHERE model_id = ?", (model.id,))
        for e in model.effects:
            self.conn.execute("INSERT INTO model_effects (model_id, effect) VALUES (?, ?)", (model.id, e))
        self.conn.execute("DELETE FROM model_evidence WHERE model_id = ?", (model.id,))
        for s in model.evidence_signal_ids:
            self.conn.execute("INSERT INTO model_evidence (model_id, signal_id) VALUES (?, ?)", (model.id, s))
        self.conn.execute("DELETE FROM model_related_entities WHERE model_id = ?", (model.id,))
        for eid in model.related_entity_ids:
            self.conn.execute("INSERT INTO model_related_entities (model_id, entity_id) VALUES (?, ?)", (model.id, eid))
        self.conn.execute("DELETE FROM model_related_claims WHERE model_id = ?", (model.id,))
        for cid in model.related_claim_ids:
            self.conn.execute("INSERT INTO model_related_claims (model_id, claim_id) VALUES (?, ?)", (model.id, cid))
        self.conn.commit()

    def get(self, model_id: str) -> Model | None:
        row = self.conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        if row is None:
            return None
        return self._enrich(_row_to_model(row))

    def _enrich(self, m: Model) -> Model:
        m.input_types = [r["input_type"] for r in self.conn.execute("SELECT input_type FROM model_input_types WHERE model_id = ?", (m.id,))]
        m.output_types = [r["output_type"] for r in self.conn.execute("SELECT output_type FROM model_output_types WHERE model_id = ?", (m.id,))]
        m.preconditions = [r["precondition"] for r in self.conn.execute("SELECT precondition FROM model_preconditions WHERE model_id = ?", (m.id,))]
        m.effects = [r["effect"] for r in self.conn.execute("SELECT effect FROM model_effects WHERE model_id = ?", (m.id,))]
        m.evidence_signal_ids = [r["signal_id"] for r in self.conn.execute("SELECT signal_id FROM model_evidence WHERE model_id = ?", (m.id,))]
        m.related_entity_ids = [r["entity_id"] for r in self.conn.execute("SELECT entity_id FROM model_related_entities WHERE model_id = ?", (m.id,))]
        m.related_claim_ids = [r["claim_id"] for r in self.conn.execute("SELECT claim_id FROM model_related_claims WHERE model_id = ?", (m.id,))]
        return m

    def find_by_kind(self, kind: str, status: str | None = None, limit: int = 100) -> list[Model]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM models WHERE kind = ? AND status = ? ORDER BY updated_at DESC LIMIT ?",
                (kind, status, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM models WHERE kind = ? ORDER BY updated_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return [self._enrich(_row_to_model(r)) for r in rows]

    def find_by_registry_key(self, key: str) -> Model | None:
        row = self.conn.execute("SELECT * FROM models WHERE registry_key = ?", (key,)).fetchone()
        if row is None:
            return None
        return self._enrich(_row_to_model(row))

    def find_by_name(self, name: str) -> list[Model]:
        rows = self.conn.execute(
            "SELECT * FROM models WHERE name = ? ORDER BY updated_at DESC", (name,)
        ).fetchall()
        return [self._enrich(_row_to_model(r)) for r in rows]

    def update_artifact(self, model_id: str, artifact_json: str) -> None:
        self.conn.execute(
            "UPDATE models SET artifact_json = ?, updated_at = ? WHERE id = ?",
            (artifact_json, time.time(), model_id),
        )
        self.conn.commit()
