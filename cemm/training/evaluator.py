from __future__ import annotations
import json
import sqlite3
import time
import uuid
from typing import Any
from ..store.store import Store
from .types import EvalSet, EvalResult


class Evaluator:
    def __init__(self, store: Store) -> None:
        self._conn: sqlite3.Connection = store.conn
        self._conn.executescript(
            "CREATE TABLE IF NOT EXISTS training_jobs (id TEXT PRIMARY KEY);"
            "CREATE TABLE IF NOT EXISTS training_examples (id TEXT PRIMARY KEY);"
        )

    def create_eval_set(self, name: str, description: str | None = None) -> EvalSet:
        es_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO eval_sets (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (es_id, name, description, now),
        )
        self._conn.commit()
        return EvalSet(id=es_id, name=name, description=description, created_at=now)

    def add_examples(self, eval_set_id: str, example_ids: list[str]) -> None:
        for ex_id in example_ids:
            self._conn.execute(
                "INSERT OR IGNORE INTO training_examples (id) VALUES (?)",
                (ex_id,),
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO eval_set_examples (eval_set_id, example_id) VALUES (?, ?)",
                (eval_set_id, ex_id),
            )
        self._conn.commit()

    def record_result(
        self, eval_set_id: str, job_id: str,
        score: float | None = None, metrics: dict[str, Any] | None = None,
        model_id: str | None = None,
    ) -> EvalResult:
        r_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT OR IGNORE INTO training_jobs (id) VALUES (?)",
            (job_id,),
        )
        self._conn.execute(
            "INSERT INTO eval_results (id, eval_set_id, job_id, model_id, score, metrics_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r_id, eval_set_id, job_id, model_id, score,
             json.dumps(metrics) if metrics else None, now),
        )
        self._conn.commit()
        return EvalResult(
            id=r_id, eval_set_id=eval_set_id, job_id=job_id,
            score=score, metrics=metrics, created_at=now,
        )

    def get_results(self, eval_set_id: str) -> list[EvalResult]:
        rows = self._conn.execute(
            "SELECT id, eval_set_id, job_id, score, metrics_json, created_at "
            "FROM eval_results WHERE eval_set_id = ? ORDER BY created_at",
            (eval_set_id,),
        ).fetchall()
        return [
            EvalResult(
                id=r[0], eval_set_id=r[1], job_id=r[2],
                score=r[3], metrics=json.loads(r[4]) if r[4] else None,
                created_at=r[5],
            )
            for r in rows
        ]
