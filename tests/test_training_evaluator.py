from __future__ import annotations
from cemm.training.evaluator import Evaluator
from cemm.store.store import Store


class TestEvaluator:
    def test_create_eval_set(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "A test set")
        assert es.id is not None
        assert es.name == "test_set"

    def test_add_examples_to_set(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "")
        e.add_examples(es.id, ["ex1", "ex2"])
        count = e._conn.execute(
            "SELECT COUNT(*) FROM eval_set_examples WHERE eval_set_id = ?", (es.id,)
        ).fetchone()[0]
        assert count == 2

    def test_record_result(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "")
        r = e.record_result(es.id, "job_1", score=0.95, metrics={"precision": 0.9})
        assert r.eval_set_id == es.id
        assert r.job_id == "job_1"
        assert r.score == 0.95
        assert r.metrics == {"precision": 0.9}

    def test_get_results(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "")
        e.record_result(es.id, "job_1", score=0.9)
        e.record_result(es.id, "job_2", score=0.8)
        results = e.get_results(es.id)
        assert len(results) == 2
