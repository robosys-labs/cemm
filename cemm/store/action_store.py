from __future__ import annotations
import sqlite3
import json
from ..types.action import Action, ActionKind, ActionStatus
from ..types.trace import Trace


def _row_to_action(row: sqlite3.Row) -> Action:
    trace = None
    if row["trace_json"]:
        try:
            td = json.loads(row["trace_json"])
            trace = Trace(**td)
        except (json.JSONDecodeError, TypeError):
            pass
    return Action(
        id=row["id"],
        kind=ActionKind(row["kind"]),
        operator_model_id=row["operator_model_id"],
        confidence=row["confidence"],
        risk=row["risk"],
        cost_ms=row["cost_ms"],
        status=ActionStatus(row["status"]),
        result_signal_id=row["result_signal_id"],
        trace=trace,
        created_at=row["created_at"],
        version=row["version"],
    )


class ActionStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def put(self, action: Action) -> None:
        trace_json = json.dumps(self._trace_to_dict(action.trace)) if action.trace else None
        self.conn.execute(
            """INSERT OR REPLACE INTO actions
               (id, kind, operator_model_id, confidence, risk, cost_ms,
                status, result_signal_id, trace_json, created_at, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                action.id, action.kind.value, action.operator_model_id,
                action.confidence, action.risk, action.cost_ms,
                action.status.value, action.result_signal_id, trace_json,
                action.created_at, action.version,
            ),
        )
        for sid in action.input_signal_ids:
            self.conn.execute("INSERT OR REPLACE INTO action_input_signals (action_id, signal_id) VALUES (?, ?)", (action.id, sid))
        for cid in action.selected_claim_ids:
            self.conn.execute("INSERT OR REPLACE INTO action_selected_claims (action_id, claim_id) VALUES (?, ?)", (action.id, cid))
        for mid in action.selected_model_ids:
            self.conn.execute("INSERT OR REPLACE INTO action_selected_models (action_id, model_id) VALUES (?, ?)", (action.id, mid))
        self.conn.commit()

    def get(self, action_id: str) -> Action | None:
        row = self.conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            return None
        action = _row_to_action(row)
        action.input_signal_ids = [r["signal_id"] for r in self.conn.execute("SELECT signal_id FROM action_input_signals WHERE action_id = ?", (action_id,))]
        action.selected_claim_ids = [r["claim_id"] for r in self.conn.execute("SELECT claim_id FROM action_selected_claims WHERE action_id = ?", (action_id,))]
        action.selected_model_ids = [r["model_id"] for r in self.conn.execute("SELECT model_id FROM action_selected_models WHERE action_id = ?", (action_id,))]
        return action

    def list_by_operator(self, operator_model_id: str, status: str | None = None, limit: int = 100) -> list[Action]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM actions WHERE operator_model_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                (operator_model_id, status, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM actions WHERE operator_model_id = ? ORDER BY created_at DESC LIMIT ?",
                (operator_model_id, limit),
            ).fetchall()
        return [_row_to_action(r) for r in rows]

    def recent(self, limit: int = 50) -> list[Action]:
        rows = self.conn.execute(
            "SELECT * FROM actions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_action(r) for r in rows]

    @staticmethod
    def _trace_to_dict(trace: Trace | None) -> dict | None:
        if trace is None:
            return None
        return {
            "context_id": trace.context_id,
            "input_signal_ids": trace.input_signal_ids,
            "selected_entity_ids": trace.selected_entity_ids,
            "selected_claim_ids": trace.selected_claim_ids,
            "selected_model_ids": trace.selected_model_ids,
            "action_id": trace.action_id,
            "operator_model_id": trace.operator_model_id,
            "causal_inference_used": trace.causal_inference_used,
            "frame_rules_applied": trace.frame_rules_applied,
            "synthesis_strategy_model_id": trace.synthesis_strategy_model_id,
            "synthesis_verified": trace.synthesis_verified,
            "permission": trace.permission,
            "confidence": trace.confidence,
            "cost_ms": trace.cost_ms,
            "fallback_used": trace.fallback_used,
        }
