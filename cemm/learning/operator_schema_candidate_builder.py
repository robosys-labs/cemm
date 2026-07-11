"""OperatorSchemaCandidateBuilder — builds operator schema candidates.
Prefers alias-to-existing-operator over new operator creation.
"""

from __future__ import annotations

from typing import Any

from ..types.learning_hypothesis import LearningHypothesis, HypothesisTargetKind
from ..types.semantic_gap import SemanticGap, GapKind
from ..types.semantic_ref import SemanticRef, SemanticRefKind


class OperatorSchemaCandidateBuilder:
    """Builds operator schema candidates from learned surface forms.
    
    For a new operator, acquires typed ports, preconditions, state/relation deltas,
    temporal profile, and permission/risk metadata.
    """
    
    def propose_alias(
        self,
        surface: str,
        language: str,
        existing_operator_key: str,
    ) -> LearningHypothesis:
        """Propose an alias binding an existing operator."""
        proposed = {
            "surface": surface,
            "language": language,
            "operator_key": existing_operator_key,
            "alias_type": "direct",
        }
        return LearningHypothesis(
            hypothesis_id=f"op_alias_{surface}_{language}",
            target_kind=HypothesisTargetKind.LEXEME_SENSE_BINDING,
            proposed_artifact=proposed,
            satisfied_fields=("operator_key",),
            language_tag=language,
            confidence=0.7,
        )
    
    def propose_new_operator(
        self,
        surface: str,
        language: str,
        group_id: str,
    ) -> tuple[LearningHypothesis, list[SemanticGap]]:
        """Propose a new operator schema with missing-field gaps."""
        proposed = {
            "surface": surface,
            "language": language,
            "operator_family": "",
            "typed_ports": {},
            "preconditions": [],
            "state_deltas": [],
            "relation_deltas": [],
            "temporal_profile": "",
            "risk_level": "unknown",
        }
        hypothesis = LearningHypothesis(
            hypothesis_id=f"op_new_{surface}_{language}",
            target_kind=HypothesisTargetKind.OPERATOR_SCHEMA,
            proposed_artifact=proposed,
            missing_fields=("operator_family", "typed_ports", "state_deltas"),
            language_tag=language,
        )
        
        span_ref = SemanticRef(kind=SemanticRefKind.SPAN, id=f"span_{surface}", label=surface)
        gaps = [
            SemanticGap(
                gap_id=f"gap_op_family_{surface}",
                branch_id="",
                group_id=group_id,
                span_ref=span_ref,
                language_tag=language,
                gap_kind=GapKind.OPERATOR_IDENTITY,
                required_fields=("operator_family",),
                surface_form=surface,
            ),
            SemanticGap(
                gap_id=f"gap_op_ports_{surface}",
                branch_id="",
                group_id=group_id,
                span_ref=span_ref,
                language_tag=language,
                gap_kind=GapKind.REQUIRED_PORT,
                required_fields=("actor", "target"),
                surface_form=surface,
            ),
        ]
        return hypothesis, gaps
