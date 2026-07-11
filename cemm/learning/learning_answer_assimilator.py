"""LearningAnswerAssimilator — assimilates user answers under episode expectations.
Runs normal perception but uses episode expectations for constrained interpretation.
"""

from __future__ import annotations

from typing import Any

from ..types.semantic_gap import SemanticGap
from ..types.learning_episode import LearningEpisode, LearningObligation
from ..types.learning_hypothesis import LearningHypothesis


class LearningAnswerAssimilator:
    """Assimilates user answers to learning questions under episode expectations.
    
    The active episode supplies an expectation frame:
    - expected answer kind
    - open semantic fields
    - candidate hypotheses
    - referent and topic bindings
    - question provenance
    
    Normal perception still runs, but episode constraints improve ranking
    rather than replacing evidence.
    """
    
    def assimilate(
        self,
        episode: LearningEpisode,
        obligation: LearningObligation,
        user_text: str,
        percept: Any,
    ) -> list[tuple[str, Any]]:
        """Extract field values from user response.
        
        Returns list of (field_name, value) tuples that can be used
        to update the hypothesis.
        """
        filled_fields: list[tuple[str, Any]] = []
        
        expected_kind = obligation.expected_answer_schema.get("answer_kind", "")
        
        # Simple extraction based on expected answer kind
        tokens = user_text.strip().lower().split()
        
        if expected_kind == "semantic_type":
            # Extract noun phrases as semantic type candidates
            for token in tokens:
                if len(token) > 2:
                    filled_fields.append(("semantic_type", token))
                    break
        
        elif expected_kind == "entity_reference":
            for token in tokens:
                if len(token) > 1:
                    filled_fields.append(("entity_ref", token))
                    break
        
        elif expected_kind == "state_change":
            for token in tokens:
                if len(token) > 2 and token not in ("the", "a", "an", "is", "it"):
                    filled_fields.append(("effect_description", token))
                    break
        
        elif expected_kind == "dimension_name":
            for token in tokens:
                if len(token) > 2:
                    filled_fields.append(("dimension", token))
                    break
        
        elif expected_kind == "value_description":
            for token in tokens:
                if len(token) > 1:
                    filled_fields.append(("value", token))
                    break
        
        elif expected_kind == "direction":
            direction_words = {"from", "to", "toward", "away", "into", "onto", "across", "through", "around", "between"}
            for token in tokens:
                if token in direction_words:
                    filled_fields.append(("direction", token))
                    break
            if not filled_fields and tokens:
                filled_fields.append(("direction", tokens[0]))
        
        elif expected_kind in ("time_description", "spatial_relation"):
            if tokens:
                filled_fields.append(("description", " ".join(tokens)))
        
        else:
            # free_form — just use the whole text
            filled_fields.append(("description", user_text))
        
        return filled_fields
