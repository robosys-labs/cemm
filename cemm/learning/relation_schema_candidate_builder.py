"""RelationSchemaCandidateBuilder — builds candidate relation schemas from evidence.
Learns source/target roles, relation family, inverse, symmetry, and context.
"""

from __future__ import annotations

from typing import Any

from ..types.learning_hypothesis import LearningHypothesis, HypothesisTargetKind
from ..types.semantic_gap import SemanticGap, GapKind
from ..types.semantic_ref import SemanticRef, SemanticRefKind


class RelationSchemaCandidateBuilder:
    """Builds relation schema candidates.

    Relation learning requires:
    - source/target roles
    - relation family
    - inverse/composition policy
    - context restrictions
    """

    def propose_relation(
        self,
        surface: str,
        language: str,
        relation_family: str = "",
        source_kind: str = "",
        target_kind: str = "",
    ) -> LearningHypothesis:
        proposed = {
            "surface": surface,
            "language": language,
            "relation_family": relation_family,
            "source_kind": source_kind,
            "target_kind": target_kind,
            "inverse": "",
            "is_symmetric": False,
        }
        missing = []
        if not relation_family:
            missing.append("relation_family")
        if not source_kind:
            missing.append("source_kind")
        if not target_kind:
            missing.append("target_kind")

        return LearningHypothesis(
            hypothesis_id=f"rel_{surface}_{language}",
            target_kind=HypothesisTargetKind.RELATION_SCHEMA,
            proposed_artifact=proposed,
            missing_fields=tuple(missing),
            language_tag=language,
        )

    def gap_for_relation_orientation(
        self,
        surface: str,
        language: str,
        group_id: str,
    ) -> SemanticGap:
        span_ref = SemanticRef(kind=SemanticRefKind.SPAN, id=f"span_{surface}", label=surface)
        return SemanticGap(
            gap_id=f"gap_rel_{surface}",
            branch_id="",
            group_id=group_id,
            span_ref=span_ref,
            language_tag=language,
            gap_kind=GapKind.RELATION_ORIENTATION,
            required_fields=("source_role", "target_role"),
            surface_form=surface,
        )
