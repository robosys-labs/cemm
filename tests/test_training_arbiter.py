from __future__ import annotations
from cemm.training.arbiter import DisagreementScorer, Arbiter
from cemm.store.store import Store
import json


class TestDisagreementScorer:
    def test_identical_outputs_no_disagreement(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}], "confidence": 0.9}
        b = {"entities": [{"name": "A"}], "confidence": 0.9}
        assert scorer.score(a, b) == 0.0

    def test_different_entities_high_disagreement(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}], "confidence": 0.9}
        b = {"entities": [{"name": "B"}], "confidence": 0.9}
        assert scorer.score(a, b) > 0.0

    def test_confidence_gap_adds_disagreement(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}], "confidence": 0.9}
        b = {"entities": [{"name": "A"}], "confidence": 0.3}
        assert scorer.score(a, b) > 0.0

    def test_disagreement_bounded(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}, {"name": "B"}], "confidence": 0.9,
             "evidence_refs": ["e1"], "uncertainty_reason": "low"}
        b = {"entities": [{"name": "C"}], "confidence": 0.1,
             "evidence_refs": ["e2"], "uncertainty_reason": "high"}
        assert 0.0 <= scorer.score(a, b) <= 1.0


class TestArbiter:
    def test_picks_highest_confidence(self):
        arbiter = Arbiter()
        outputs = [
            {"data": {"label": "A"}, "confidence": 0.9, "agent": "extractor"},
            {"data": {"label": "B"}, "confidence": 0.3, "agent": "critic"},
        ]
        result = arbiter.arbitrate(outputs)
        assert result["chosen_agent"] == "extractor"
        assert result["final_label"] == {"label": "A"}

    def test_single_agent_no_arbitration(self):
        arbiter = Arbiter()
        outputs = [{"data": {"label": "A"}, "confidence": 0.9, "agent": "extractor"}]
        result = arbiter.arbitrate(outputs)
        assert result["chosen_agent"] == "extractor"

    def test_empty_outputs_returns_default(self):
        arbiter = Arbiter()
        result = arbiter.arbitrate([])
        assert result["chosen_agent"] is None

    def test_score_and_store(self):
        """Integration: score disagreement then arbitrate."""
        store = Store(":memory:")
        arbiter = Arbiter(store=store)
        outputs = [
            {"data": {"label": "A"}, "confidence": 0.95, "agent": "extractor"},
            {"data": {"label": "B"}, "confidence": 0.4, "agent": "critic"},
        ]
        result = arbiter.arbitrate(outputs)
        assert result["chosen_agent"] == "extractor"
        assert result["final_label"] == {"label": "A"}

    def test_store_label(self):
        store = Store(":memory:")
        arbiter = Arbiter(store=store)
        label = arbiter.store_label("job_1", {"result": "ok"}, confidence=0.95)
        assert label.job_id == "job_1"
        assert label.final_confidence == 0.95
        assert label.source == "arbiter"
