"""CausalRuleCandidateBuilder — builds causal rule candidates from evidence.
Requires antecedent/effect, temporal order, scope, and source independence.
"""

from __future__ import annotations

from typing import Any
import uuid

from ..types.learning_hypothesis import LearningHypothesis, HypothesisTargetKind
from ..legacy.v3_3.causal_effect_graph import CausalRule


class CausalRuleCandidateBuilder:
    """Builds causal rule candidates.

    Causal hypotheses remain candidates until antecedent/effect, direction,
    temporal ordering, scope, and confounder policy are adequately supported.
    """

    def propose(
        self,
        antecedent_key: str,
        effect_key: str,
        scope: str = "session",
    ) -> LearningHypothesis:
        proposed = {
            "antecedent": antecedent_key,
            "effect": effect_key,
            "direction": "forward",
            "temporal_order": "concurrent",
            "scope": scope,
        }
        return LearningHypothesis(
            hypothesis_id=uuid.uuid4().hex[:16],
            target_kind=HypothesisTargetKind.CAUSAL_RULE,
            proposed_artifact=proposed,
            missing_fields=("temporal_order", "scope"),
        )

    def to_causal_rule(
        self,
        hypothesis: LearningHypothesis,
        confidence: float = 0.5,
    ) -> CausalRule:
        art = hypothesis.proposed_artifact
        return CausalRule(
            rule_id=hypothesis.hypothesis_id,
            antecedent_key=art.get("antecedent", ""),
            effect_key=art.get("effect", ""),
            direction=art.get("direction", "forward"),
            scope=art.get("scope", "session"),
            confidence=confidence,
        )
