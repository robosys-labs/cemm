"""StateLexemeLearner — learns state term bindings to existing state coordinates.
Proposes new dimensions only when existing schemas cannot represent the evidence.
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict

from ..types.semantic_gap import SemanticGap, GapKind
from ..types.learning_hypothesis import LearningHypothesis, HypothesisTargetKind
from ..types.learning_episode import QuestionActKind


class StateLexemeLearner:
    """Learns state term bindings (adjective, state verb) to state coordinates.
    
    Maps surface forms to:
    - holder entity kinds
    - state family
    - dimension
    - value or polarity/intensity
    - scale/units
    - temporal persistence
    """
    
    def propose_hypothesis(
        self,
        surface: str,
        language: str,
        context_family: str = "",
        context_dimension: str = "",
    ) -> LearningHypothesis:
        """Propose a hypothesis for a new state lexeme binding."""
        proposed = {
            "surface": surface,
            "language": language,
            "state_family": context_family,
            "dimension": context_dimension,
        }
        missing = []
        if not context_family:
            missing.append("state_family")
        if not context_dimension:
            missing.append("dimension")
        missing.extend(["value_or_polarity", "holder_kind"])
        
        return LearningHypothesis(
            hypothesis_id=f"sl_{surface}_{language}",
            target_kind=HypothesisTargetKind.STATE_LEXEME_BINDING,
            proposed_artifact=proposed,
            missing_fields=tuple(missing),
            language_tag=language,
        )
    
    def gap_for_missing_dimension(
        self,
        surface: str,
        language: str,
        group_id: str,
    ) -> SemanticGap:
        from ..types.semantic_ref import SemanticRef, SemanticRefKind
        span_ref = SemanticRef(kind=SemanticRefKind.SPAN, id=f"span_{surface}", label=surface)
        return SemanticGap(
            gap_id=f"sg_state_{surface}",
            branch_id="",
            group_id=group_id,
            span_ref=span_ref,
            language_tag=language,
            gap_kind=GapKind.STATE_DIMENSION,
            required_fields=("state_family", "dimension", "value_or_polarity"),
            surface_form=surface,
        )
