from __future__ import annotations
import json
import sqlite3
import time
import uuid
from typing import Any
from ..store.store import Store
from .types import TrainingLabel


class DisagreementScorer:
    def score(self, output_a: dict[str, Any], output_b: dict[str, Any]) -> float:
        s = 0.0
        s += self._structure_mismatch(output_a, output_b)
        s += self._value_mismatch(output_a, output_b)
        s += self._confidence_gap(output_a, output_b)
        s += self._evidence_mismatch(output_a, output_b)
        s += self._frame_mismatch(output_a, output_b)
        s += self._contradiction_flag(output_a, output_b)
        return min(s, 1.0)

    @staticmethod
    def _structure_mismatch(a: dict, b: dict) -> float:
        skip = {"confidence", "evidence_refs", "uncertainty_reason"}
        a_keys = set(a.keys()) - skip
        b_keys = set(b.keys()) - skip
        if not a_keys and not b_keys:
            return 0.0
        overlap = a_keys & b_keys
        total = a_keys | b_keys
        return 1.0 - (len(overlap) / len(total))

    @staticmethod
    def _value_mismatch(a: dict, b: dict) -> float:
        skip = {"confidence", "evidence_refs", "uncertainty_reason"}
        shared = set(a.keys()) & set(b.keys()) - skip
        if not shared:
            return 0.0
        differing = sum(1 for k in shared if json.dumps(a[k], sort_keys=True, default=str) != json.dumps(b[k], sort_keys=True, default=str))
        return differing / len(shared)

    @staticmethod
    def _confidence_gap(a: dict, b: dict) -> float:
        ca = a.get("confidence", 0.5) if isinstance(a.get("confidence"), (int, float)) else 0.5
        cb = b.get("confidence", 0.5) if isinstance(b.get("confidence"), (int, float)) else 0.5
        return abs(ca - cb)

    @staticmethod
    def _evidence_mismatch(a: dict, b: dict) -> float:
        ea = set(a.get("evidence_refs", []))
        eb = set(b.get("evidence_refs", []))
        if not ea and not eb:
            return 0.0
        overlap = ea & eb
        total = ea | eb
        return 1.0 - (len(overlap) / len(total))

    @staticmethod
    def _frame_mismatch(a: dict, b: dict) -> float:
        fa = a.get("context_frame") or a.get("frame_id")
        fb = b.get("context_frame") or b.get("frame_id")
        if fa is None and fb is None:
            return 0.0
        return 0.0 if fa == fb else 1.0

    @staticmethod
    def _contradiction_flag(a: dict, b: dict) -> float:
        contradictions = a.get("contradictions", [])
        if isinstance(contradictions, list):
            return 1.0 if contradictions else 0.0
        return 0.0


class Arbiter:
    def __init__(self, store: Store | None = None) -> None:
        self._scorer = DisagreementScorer()
        self._store = store
        self._conn: sqlite3.Connection | None = store.conn if store else None

    def arbitrate(self, agent_outputs: list[dict[str, Any]]) -> dict[str, Any]:
        if not agent_outputs:
            return {"final_label": None, "confidence": 0.0,
                    "explanation": "No agent outputs", "chosen_agent": None}
        if len(agent_outputs) == 1:
            o = agent_outputs[0]
            return {"final_label": o.get("data"), "confidence": o.get("confidence", 0.5),
                    "explanation": "Single agent", "chosen_agent": o.get("agent")}
        best = max(agent_outputs, key=lambda o: o.get("confidence", 0.0))
        return {"final_label": best.get("data"), "confidence": best.get("confidence", 0.5),
                "explanation": "Selected highest confidence agent",
                "chosen_agent": best.get("agent")}

    def store_label(
        self, job_id: str, label: dict[str, Any],
        confidence: float | None = None, source: str = "arbiter",
    ) -> TrainingLabel | None:
        if self._conn is None:
            return None
        self._conn.executescript(
            "CREATE TABLE IF NOT EXISTS training_jobs (id TEXT PRIMARY KEY);"
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO training_jobs (id) VALUES (?)",
            (job_id,),
        )
        label_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO training_labels (id, job_id, arbiter_label_json, final_confidence, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (label_id, job_id, json.dumps(label) if label else None,
             confidence, source, now),
        )
        self._conn.commit()
        return TrainingLabel(
            id=label_id, job_id=job_id,
            arbiter_label=label, final_confidence=confidence,
            source=source, created_at=now,
        )
