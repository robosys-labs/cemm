from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from .semantic_ref import SemanticRef


class HypothesisTargetKind(str, Enum):
    """What kind of artifact this hypothesis proposes to learn."""
    SURFACE_FORM_BINDING = "surface_form_binding"
    LEMMA_BINDING = "lemma_binding"
    MORPHOLOGICAL_RULE = "morphological_rule"
    LEXEME_SENSE_BINDING = "lexeme_sense_binding"
    GRAMMAR_OPERATOR_BINDING = "grammar_operator_binding"
    CONSTRUCTION_SCHEMA = "construction_schema"
    CONCEPT_CANDIDATE = "concept_candidate"
    ENTITY_KIND_CANDIDATE = "entity_kind_candidate"
    ENTITY_IDENTITY_BINDING = "entity_identity_binding"
    RELATION_SCHEMA = "relation_schema"
    STATE_LEXEME_BINDING = "state_lexeme_binding"
    STATE_DIMENSION_CANDIDATE = "state_dimension_candidate"
    OPERATOR_SCHEMA = "operator_schema"
    AFFORDANCE_RULE = "affordance_rule"
    CAUSAL_RULE = "causal_rule"
    REALIZATION_FORM = "realization_form"


@dataclass(frozen=True, slots=True)
class LearningHypothesis:
    """A candidate hypothesis for what a learned artifact means.
    
    Proposed during a learning episode. Collects evidence before
    becoming a session-provisional or durable binding.
    """
    hypothesis_id: str
    target_kind: HypothesisTargetKind
    proposed_artifact: dict[str, Any] = field(default_factory=dict)
    satisfied_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    applicability_context_id: str = ""
    language_tag: str = "und"
    scope: str = "session"
    confidence: float = 0.0
    
    # Artifact references
    source_refs: tuple[str, ...] = ()
    evidence_event_ids: tuple[str, ...] = ()
    provenance_ref: str = ""
    
    @property
    def is_minimally_grounded(self) -> bool:
        return len(self.missing_fields) == 0 and self.confidence >= 0.3
    
    @property
    def is_fully_specified(self) -> bool:
        return len(self.missing_fields) == 0 and self.confidence >= 0.7
    
    def with_satisfied_fields(self, fields: dict[str, Any]) -> "LearningHypothesis":
        new_artifact = dict(self.proposed_artifact)
        new_artifact.update(fields)
        new_satisfied = tuple(sorted(set(self.satisfied_fields) | set(fields.keys())))
        new_missing = tuple(f for f in self.missing_fields if f not in fields)
        return LearningHypothesis(
            hypothesis_id=self.hypothesis_id,
            target_kind=self.target_kind,
            proposed_artifact=new_artifact,
            satisfied_fields=new_satisfied,
            missing_fields=new_missing,
            applicability_context_id=self.applicability_context_id,
            language_tag=self.language_tag,
            scope=self.scope,
            confidence=self.confidence,
            source_refs=self.source_refs,
            evidence_event_ids=self.evidence_event_ids,
            provenance_ref=self.provenance_ref,
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "target_kind": self.target_kind.value,
            "satisfied_fields": list(self.satisfied_fields),
            "missing_fields": list(self.missing_fields),
            "language_tag": self.language_tag,
            "scope": self.scope,
            "confidence": self.confidence,
        }
