from __future__ import annotations
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
        now = time.time()
        row = self._conn.execute(
            "SELECT model_id FROM promotion_candidates WHERE id = ? AND status = 'pending'",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return False
        model_id = row[0]
        self._conn.execute(
            "UPDATE promotion_candidates SET status = 'approved', reviewed_at = ? WHERE id = ?",
            (now, candidate_id),
        )
        self._conn.execute(
            "UPDATE models SET status = 'active' WHERE id = ?", (model_id,),
        )
        self._conn.commit()
        return True

    def reject(self, candidate_id: str) -> bool:
        now = time.time()
        self._conn.execute(
            "UPDATE promotion_candidates SET status = 'rejected', reviewed_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (now, candidate_id),
        )
        self._conn.commit()
        return self._conn.total_changes > 0

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
