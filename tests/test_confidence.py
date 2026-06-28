import pytest
import math
from cemm.confidence.log_odds import (
    log_odds, probability, update_log_odds,
    prior_log_odds, source_evidence_weight,
)
from cemm.confidence.scoring import score_claim, score_model, score_action


class TestLogOdds:
    def test_log_odds_conversion(self):
        assert log_odds(0.5) == 0.0
        assert abs(log_odds(0.9) - math.log(9.0)) < 0.001

    def test_probability_conversion(self):
        assert probability(0.0) == 0.5
        assert abs(probability(math.log(9.0)) - 0.9) < 0.001

    def test_update_log_odds_with_defaults(self):
        result = update_log_odds(current_log_odds=0.0)
        # With defaults: source_evidence_weight(0.5,0)=0 + direct_confirmation_weight(0,0)=0
        # + frame_validity_weight(0.5,1.0)=0.25 + contradiction_weight(0)=0 + staleness_weight(0)=0
        assert result == 0.25

    def test_source_evidence_weight_zero_evidence(self):
        w = source_evidence_weight(0.8, 0)
        assert w == 0.0


class TestScoring:
    def test_score_claim_zero_without_permission(self):
        s = score_claim(permission_valid=False)
        assert s == 0.0

    def test_score_claim_positive(self):
        s = score_claim(relevance=0.8, trust=0.9, confidence=0.9, salience=0.5, recency=1.0)
        assert s > 0.0

    def test_score_model_zero_without_permission(self):
        s = score_model(permission_valid=False)
        assert s == 0.0

    def test_score_action_zero_without_permission(self):
        s = score_action(permission_valid=False)
        assert s == 0.0
