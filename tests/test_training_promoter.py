from __future__ import annotations
from cemm.training.promoter import Promoter
from cemm.store.store import Store
from cemm.types.model import Model, ModelKind, ModelStatus
import time
import uuid


def _seed_eval(store: Store, model_id: str, score: float) -> None:
    now = time.time()
    store.conn.execute("CREATE TABLE IF NOT EXISTS training_jobs (id TEXT PRIMARY KEY)")
    eval_set_id = uuid.uuid4().hex[:16]
    store.conn.execute(
        "INSERT INTO eval_sets (id, name, created_at) VALUES (?, ?, ?)",
        (eval_set_id, "test_set", now),
    )
    job_id = uuid.uuid4().hex[:16]
    store.conn.execute(
        "INSERT OR IGNORE INTO training_jobs (id) VALUES (?)", (job_id,),
    )
    store.conn.execute(
        "INSERT INTO eval_results (id, eval_set_id, job_id, model_id, score, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex[:16], eval_set_id, job_id, model_id, score, now),
    )
    store.conn.commit()


class TestPromoter:
    def test_create_candidate(self):
        p = Promoter(Store(":memory:"))
        c = p.create_candidate("model_1", "High accuracy", score=0.95)
        assert c.model_id == "model_1"
        assert c.score == 0.95
        assert c.status == "pending"

    def test_candidate_reference_not_required(self):
        """Create candidate should succeed even if model doesn't exist yet."""
        p = Promoter(Store(":memory:"))
        c = p.create_candidate("nonexistent_model", "test", score=0.5)
        assert c.status == "pending"

    def test_approve_promotion_with_eval(self):
        store = Store(":memory:")
        now = time.time()
        model = Model(
            id="model_to_promote", kind=ModelKind.PREDICATE, name="test",
            status=ModelStatus.CANDIDATE, created_at=now, updated_at=now,
        )
        store.models.put(model)
        _seed_eval(store, "model_to_promote", 0.9)
        p = Promoter(store)
        c = p.create_candidate("model_to_promote", "Good", score=0.9)
        success = p.approve(c.id)
        assert success is True
        row = p._conn.execute(
            "SELECT status FROM promotion_candidates WHERE id = ?", (c.id,)
        ).fetchone()
        assert row[0] == "approved"
        model_row = p._conn.execute(
            "SELECT status FROM models WHERE id = ?", ("model_to_promote",)
        ).fetchone()
        assert model_row[0] == "active"

    def test_rejects_without_eval(self):
        store = Store(":memory:")
        now = time.time()
        model = Model(
            id="no_eval_model", kind=ModelKind.PREDICATE, name="test",
            status=ModelStatus.CANDIDATE, created_at=now, updated_at=now,
        )
        store.models.put(model)
        p = Promoter(store)
        c = p.create_candidate("no_eval_model", "No eval", score=0.9)
        success = p.approve(c.id)
        assert success is False

    def test_reject_promotion(self):
        store = Store(":memory:")
        now = time.time()
        model = Model(
            id="model_to_reject", kind=ModelKind.PREDICATE, name="test",
            status=ModelStatus.CANDIDATE, created_at=now, updated_at=now,
        )
        store.models.put(model)
        p = Promoter(store)
        c = p.create_candidate("model_to_reject", "Bad", score=0.2)
        success = p.reject(c.id)
        assert success is True
        row = p._conn.execute(
            "SELECT status FROM promotion_candidates WHERE id = ?", (c.id,)
        ).fetchone()
        assert row[0] == "rejected"
        model_row = p._conn.execute(
            "SELECT status FROM models WHERE id = ?", ("model_to_reject",)
        ).fetchone()
        assert model_row[0] == "candidate"

    def test_list_pending(self):
        p = Promoter(Store(":memory:"))
        p.create_candidate("m1", "test", score=0.9)
        p.create_candidate("m2", "test2", score=0.3)
        pending = p.list_pending()
        assert len(pending) == 2

    def test_list_pending_ordered_by_score(self):
        p = Promoter(Store(":memory:"))
        p.create_candidate("m1", "low", score=0.3)
        p.create_candidate("m2", "high", score=0.9)
        p.create_candidate("m3", "mid", score=0.6)
        pending = p.list_pending()
        scores = [c.score for c in pending]
        assert scores == sorted(scores, reverse=True)
