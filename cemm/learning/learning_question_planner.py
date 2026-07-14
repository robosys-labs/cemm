"""DEPRECATED: Replaced by cemm.kernel.learning.grounding_frontier.GroundingFrontierBuilder.

This module is retained for legacy compatibility only. The v3.4 canonical
learning path uses GroundingFrontier for probe planning.
Do not use for new code — redirect to GroundingFrontierBuilder.

LearningQuestionPlanner — chooses one semantic question act per turn.
Maximizes expected uncertainty reduction per interaction cost.

utility = expected_entropy_reduction * downstream_blocking_weight * reuse_value / question_cost
"""

from __future__ import annotations

from typing import Any
import math

from ..types.learning_episode import QuestionActKind, LearningObligation


class LearningQuestionPlanner:
    """Plans which learning question to ask to resolve semantic gaps.
    
    Selects the single highest-utility question per turn.
    """
    
    def plan(
        self,
        gaps: list[Any],
        hypotheses: list[Any],
        asked_fields: set[str],
        blocking_gap_ids: set[str],
    ) -> LearningObligation | None:
        """Select one question to ask from available gaps.
        
        Returns a LearningObligation with:
        - question_act: which type of question
        - expected_answer_schema: what the answer should contain
        - utility: the computed utility score
        """
        candidates: list[LearningObligation] = []
        
        for gap in gaps:
            if gap.gap_id in asked_fields:
                continue
            
            utility = self._compute_utility(gap, blocking_gap_ids)
            question_act = self._gap_kind_to_question_act(gap.gap_kind)
            
            candidates.append(LearningObligation(
                obligation_id=f"lq_{gap.gap_id}",
                episode_id="",
                gap_ids=(gap.gap_id,),
                question_act=question_act,
                expected_answer_schema=self._expected_schema(question_act),
                utility=utility,
            ))
        
        if not candidates:
            return None
        
        # Sort by utility descending
        candidates.sort(key=lambda c: c.utility, reverse=True)
        return candidates[0]
    
    def _compute_utility(
        self,
        gap: Any,
        blocking_gap_ids: set[str],
    ) -> float:
        entropy_reduction = getattr(gap, "entropy", 0.5)
        is_blocking = gap.gap_id in blocking_gap_ids
        blocking_weight = 2.0 if is_blocking else 0.5
        return entropy_reduction * blocking_weight
    
    def _gap_kind_to_question_act(self, gap_kind: Any) -> QuestionActKind:
        kind_str = gap_kind.value if hasattr(gap_kind, "value") else str(gap_kind)
        mapping = {
            "lexeme_sense": QuestionActKind.ASK_SEMANTIC_KIND,
            "entity_identity": QuestionActKind.ASK_REFERENT_IDENTITY,
            "operator_identity": QuestionActKind.ASK_SEMANTIC_KIND,
            "required_port": QuestionActKind.ASK_OPERATOR_ACTOR,
            "state_family": QuestionActKind.ASK_STATE_DIMENSION,
            "state_dimension": QuestionActKind.ASK_STATE_DIMENSION,
            "state_value_or_scale": QuestionActKind.ASK_STATE_VALUE_OR_POLARITY,
            "relation_orientation": QuestionActKind.ASK_RELATION_ORIENTATION,
            "temporal_anchor": QuestionActKind.ASK_TEMPORAL_SCOPE,
            "geospatial_anchor": QuestionActKind.ASK_GEOSPATIAL_RELATION,
            "grammatical_function": QuestionActKind.ASK_GRAMMATICAL_FUNCTION,
            "causal_effect": QuestionActKind.ASK_OPERATOR_EFFECT,
        }
        return mapping.get(kind_str, QuestionActKind.ASK_SEMANTIC_KIND)
    
    def _expected_schema(self, question_act: QuestionActKind) -> dict[str, Any]:
        schemas = {
            QuestionActKind.ASK_SEMANTIC_KIND: {"answer_kind": "semantic_type"},
            QuestionActKind.ASK_REFERENT_IDENTITY: {"answer_kind": "entity_reference"},
            QuestionActKind.ASK_OPERATOR_ACTOR: {"answer_kind": "entity_reference"},
            QuestionActKind.ASK_OPERATOR_TARGET: {"answer_kind": "entity_reference"},
            QuestionActKind.ASK_OPERATOR_EFFECT: {"answer_kind": "state_change"},
            QuestionActKind.ASK_STATE_DIMENSION: {"answer_kind": "dimension_name"},
            QuestionActKind.ASK_STATE_VALUE_OR_POLARITY: {"answer_kind": "value_description"},
            QuestionActKind.ASK_RELATION_ORIENTATION: {"answer_kind": "direction"},
            QuestionActKind.ASK_TEMPORAL_SCOPE: {"answer_kind": "time_description"},
            QuestionActKind.ASK_GEOSPATIAL_RELATION: {"answer_kind": "spatial_relation"},
        }
        return schemas.get(question_act, {"answer_kind": "free_form"})
