from __future__ import annotations
import json
import sqlite3
import time
import uuid
from ..store.store import Store
from .types import PromotionCandidate


class Promoter:
    def __init__(self, store: Store) -> None:
        self._conn: sqlite3.Connection = store.conn

    def create_candidate(
        self, model_id: str, reason: str, score: float = 0.0,
    ) -> PromotionCandidate:
        c_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO promotion_candidates (id, model_id, reason, score, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (c_id, model_id, reason, score, now),
        )
        self._conn.commit()
        return PromotionCandidate(
            id=c_id, model_id=model_id, reason=reason,
            score=score, status="pending", created_at=now,
        )

    def approve(self, candidate_id: str) -> bool:
        candidate = self._conn.execute(
            "SELECT * FROM promotion_candidates WHERE id = ? AND status = 'pending'",
            (candidate_id,),
        ).fetchone()
        if not candidate:
            return False
        model_id = candidate["model_id"]
        if not self._candidate_has_passing_eval(candidate_id):
            return False
        if not self._candidate_permission_safe(model_id):
            return False
        if not self._candidate_risk_acceptable(model_id):
            return False
        now = time.time()
        self._conn.execute(
            "UPDATE promotion_candidates SET status = 'approved', reviewed_at = ? WHERE id = ?",
            (now, candidate_id),
        )
        self._conn.execute(
            "UPDATE models SET status = 'active' WHERE id = ?", (model_id,),
        )
        try:
            artifact = self._build_artifact_for_model(self._conn, model_id)
            if not artifact:
                artifact = self._build_induction_artifact(self._conn, model_id)
            if artifact:
                self._conn.execute(
                    "UPDATE models SET artifact_json = ?, updated_at = ? WHERE id = ?",
                    (artifact, time.time(), model_id),
                )
        except Exception:
            pass
        self._conn.commit()
        return True

    def _candidate_has_passing_eval(self, candidate_id: str) -> bool:
        pc = self._conn.execute(
            "SELECT model_id FROM promotion_candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if not pc:
            return False
        model_id = pc["model_id"]

        row = self._conn.execute(
            "SELECT score FROM eval_results WHERE model_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (model_id,),
        ).fetchone()
        if row is not None:
            return row["score"] >= 0.6

        try:
            row = self._conn.execute(
                """
                SELECT er.score FROM eval_results er
                JOIN agent_runs ar ON ar.job_id = er.job_id
                WHERE ar.model = ?
                ORDER BY er.created_at DESC LIMIT 1
                """,
                (model_id,),
            ).fetchone()
            if row is not None:
                return row["score"] >= 0.6
        except Exception:
            pass

        return False

    def _candidate_permission_safe(self, model_id: str) -> bool:
        row = self._conn.execute(
            "SELECT permission_scope FROM models WHERE id = ?", (model_id,),
        ).fetchone()
        if not row:
            return False
        return row["permission_scope"] in ("public", "user_private")

    def _candidate_risk_acceptable(self, model_id: str) -> bool:
        row = self._conn.execute(
            "SELECT risk FROM models WHERE id = ?", (model_id,),
        ).fetchone()
        if not row:
            return False
        return row["risk"] <= 0.3

    def reject(self, candidate_id: str) -> bool:
        now = time.time()
        self._conn.execute(
            "UPDATE promotion_candidates SET status = 'rejected', reviewed_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (now, candidate_id),
        )
        self._conn.commit()
        return self._conn.total_changes > 0

    @staticmethod
    def _build_artifact_for_model(conn: sqlite3.Connection, model_id: str) -> str | None:
        model = conn.execute(
            "SELECT kind FROM models WHERE id = ?", (model_id,),
        ).fetchone()
        if not model:
            return None
        kind = model["kind"]
        TASK_BY_KIND = {
            "uol_semantic": "uol_mapping",
            "operator": "operator_selection",
            "synthesis_strategy": "semantic_text_realization",
            "context_rule": "context_inference",
            "frame_rule": "frame_classification",
            "predicate": "claim_extraction",
            "causal_rule": "causal_effect_prediction",
        }
        task_type = TASK_BY_KIND.get(kind)
        if not task_type:
            return None
        rows = conn.execute(
            """
            SELECT ao.output_json, ao.confidence, tj.payload_json, tj.id AS job_id
            FROM agent_outputs ao
            JOIN training_jobs tj ON tj.id = ao.job_id
            WHERE tj.task_type = ?
            ORDER BY ao.created_at DESC LIMIT 100
            """,
            (task_type,),
        ).fetchall()
        if not rows:
            return None
        examples = []
        for row in rows:
            try:
                output = json.loads(row["output_json"])
                payload = json.loads(row["payload_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            examples.append({
                "job_id": row["job_id"],
                "task_type": task_type,
                "input": payload,
                "output": output,
                "confidence": row["confidence"],
            })
        artifact = {
            "version": "cemm.artifact.v1",
            "task_type": task_type,
            "model_kind": kind,
            "example_count": len(examples),
            "examples": examples,
        }
        return json.dumps(artifact, sort_keys=True)

    @staticmethod
    def _build_induction_artifact(conn: sqlite3.Connection, model_id: str) -> str | None:
        row = conn.execute(
            "SELECT kind, name, description, confidence, trust, risk "
            "FROM models WHERE id = ?", (model_id,),
        ).fetchone()
        if not row:
            return None
        model_data = dict(row)
        precondition_rows = conn.execute(
            "SELECT precondition FROM model_preconditions WHERE model_id = ?",
            (model_id,),
        ).fetchall()
        preconditions = [r[0] for r in precondition_rows]
        effect_rows = conn.execute(
            "SELECT effect FROM model_effects WHERE model_id = ?",
            (model_id,),
        ).fetchall()
        effects = [r[0] for r in effect_rows]
        evidence_rows = conn.execute(
            "SELECT signal_id FROM model_evidence WHERE model_id = ?",
            (model_id,),
        ).fetchall()
        signal_ids = [r[0] for r in evidence_rows]

        task_type = {
            "causal_rule": "causal_effect_prediction",
            "context_rule": "context_inference",
            "predicate": "claim_extraction",
            "uol_semantic": "uol_mapping",
        }.get(model_data["kind"], "operator_selection")

        example = {
            "input": {
                "kind": model_data["kind"],
                "preconditions": preconditions,
                "effects": effects,
                "evidence_signal_ids": signal_ids,
                "description": model_data["description"],
            },
            "output": {
                "kind": model_data["kind"],
                "confidence": model_data["confidence"],
                "description": model_data["description"],
            },
            "confidence": model_data["confidence"],
        }
        artifact = {
            "version": "cemm.artifact.v1",
            "task_type": task_type,
            "model_kind": model_data["kind"],
            "example_count": 1,
            "examples": [example],
        }
        return json.dumps(artifact, sort_keys=True)

    def list_pending(self) -> list[PromotionCandidate]:
        rows = self._conn.execute(
            "SELECT id, model_id, reason, score, status, created_at, reviewed_at "
            "FROM promotion_candidates WHERE status = 'pending' ORDER BY score DESC",
        ).fetchall()
        return [
            PromotionCandidate(id=r[0], model_id=r[1], reason=r[2],
                              score=r[3], status=r[4], created_at=r[5],
                              reviewed_at=r[6])
            for r in rows
        ]
