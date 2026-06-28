from __future__ import annotations
import sqlite3
import json
from ..types.self_state import SelfState, InternalMode, SelfMetacognition, SelfEpistemic, SelfMetaMemory


def _row_to_self_state(row: sqlite3.Row) -> SelfState:
    return SelfState(
        id=row["id"],
        name=row["name"],
        identity_claim_ids=json.loads(row["identity_claim_ids_json"]),
        created_at=row["created_at"],
        mode=InternalMode(row["mode"]),
        load=row["load"],
        uncertainty=row["uncertainty"],
        coherence=row["coherence"],
        recent_error_rate=row["recent_error_rate"],
        current_budget_pressure=row["current_budget_pressure"],
        metacognition=SelfMetacognition(**json.loads(row["metacognition_json"])),
        epistemic=SelfEpistemic(**json.loads(row["epistemic_json"])),
        meta_memory=SelfMetaMemory(**json.loads(row["meta_memory_json"])),
        current_context_id=row["current_context_id"],
        last_reflection_signal_id=row["last_reflection_signal_id"],
        updated_at=row["updated_at"],
        version=row["version"],
    )


class SelfStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def put(self, state: SelfState) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO self_states
               (id, name, identity_claim_ids_json, mode, load, uncertainty,
                coherence, recent_error_rate, current_budget_pressure,
                metacognition_json, epistemic_json, meta_memory_json,
                current_context_id, last_reflection_signal_id,
                created_at, updated_at, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.id, state.name, json.dumps(state.identity_claim_ids),
                state.mode.value, state.load, state.uncertainty,
                state.coherence, state.recent_error_rate, state.current_budget_pressure,
                json.dumps({
                    "known_limits": state.metacognition.known_limits,
                    "active_assumptions": state.metacognition.active_assumptions,
                    "reliability_by_domain": state.metacognition.reliability_by_domain,
                    "preferred_strategies": state.metacognition.preferred_strategies,
                }),
                json.dumps({
                    "open_contradiction_claim_ids": state.epistemic.open_contradiction_claim_ids,
                    "low_confidence_domain_keys": state.epistemic.low_confidence_domain_keys,
                    "calibration_error_by_domain": state.epistemic.calibration_error_by_domain,
                    "coverage_gap_claim_ids": state.epistemic.coverage_gap_claim_ids,
                }),
                json.dumps({
                    "recently_written_claim_ids": state.meta_memory.recently_written_claim_ids,
                    "recently_superseded_claim_ids": state.meta_memory.recently_superseded_claim_ids,
                    "frequently_used_model_ids": state.meta_memory.frequently_used_model_ids,
                    "failed_retrieval_patterns": state.meta_memory.failed_retrieval_patterns,
                }),
                state.current_context_id,
                state.last_reflection_signal_id,
                state.created_at, state.updated_at, state.version,
            ),
        )
        self.conn.execute("DELETE FROM self_milestone_signals WHERE self_id = ?", (state.id,))
        for sid in state.milestone_signal_ids:
            self.conn.execute(
                "INSERT OR REPLACE INTO self_milestone_signals (self_id, signal_id) VALUES (?, ?)",
                (state.id, sid),
            )
        self.conn.execute("DELETE FROM self_active_projects WHERE self_id = ?", (state.id,))
        for pid in state.active_project_ids:
            self.conn.execute(
                "INSERT OR REPLACE INTO self_active_projects (self_id, project_id) VALUES (?, ?)",
                (state.id, pid),
            )
        self.conn.execute("DELETE FROM self_learned_models WHERE self_id = ?", (state.id,))
        for mid in state.learned_model_ids:
            self.conn.execute(
                "INSERT OR REPLACE INTO self_learned_models (self_id, model_id) VALUES (?, ?)",
                (state.id, mid),
            )
        self.conn.commit()

    def get(self, self_id: str) -> SelfState | None:
        row = self.conn.execute("SELECT * FROM self_states WHERE id = ?", (self_id,)).fetchone()
        if row is None:
            return None
        state = _row_to_self_state(row)
        state.milestone_signal_ids = [
            r["signal_id"] for r in self.conn.execute(
                "SELECT signal_id FROM self_milestone_signals WHERE self_id = ?", (self_id,)
            )
        ]
        state.active_project_ids = [
            r["project_id"] for r in self.conn.execute(
                "SELECT project_id FROM self_active_projects WHERE self_id = ?", (self_id,)
            )
        ]
        state.learned_model_ids = [
            r["model_id"] for r in self.conn.execute(
                "SELECT model_id FROM self_learned_models WHERE self_id = ?", (self_id,)
            )
        ]
        return state

    def latest(self) -> SelfState | None:
        row = self.conn.execute(
            "SELECT * FROM self_states ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return self.get(row["id"])

    def update_uncertainty(self, self_id: str, uncertainty: float) -> None:
        self.conn.execute(
            "UPDATE self_states SET uncertainty = ?, updated_at = ? WHERE id = ?",
            (uncertainty, __import__("time").time(), self_id),
        )
        self.conn.commit()

    def update_error_rate(self, self_id: str, error_rate: float) -> None:
        self.conn.execute(
            "UPDATE self_states SET recent_error_rate = ?, updated_at = ? WHERE id = ?",
            (error_rate, __import__("time").time(), self_id),
        )
        self.conn.commit()
