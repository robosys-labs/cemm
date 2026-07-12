from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HypothesisTargetKind(str, Enum):
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
    hypothesis_id: str
    target_kind: HypothesisTargetKind
    proposed_artifact: dict[str, Any] = field(default_factory=dict)
    satisfied_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    applicability_context_id: str = ""
    language_tag: str = "und"
    scope: str = "session"
    confidence: float = 0.0
    source_refs: tuple[str, ...] = ()
    evidence_event_ids: tuple[str, ...] = ()
    provenance_ref: str = ""

    @property
    def is_minimally_grounded(self) -> bool:
        return not self.missing_fields and self.confidence >= 0.3

    @property
    def is_fully_specified(self) -> bool:
        return not self.missing_fields and self.confidence >= 0.7

    def with_satisfied_fields(self, fields: dict[str, Any]) -> "LearningHypothesis":
        artifact = {**self.proposed_artifact, **fields}
        satisfied = tuple(sorted(set(self.satisfied_fields) | set(fields)))
        missing = tuple(field for field in self.missing_fields if field not in fields)
        return LearningHypothesis(
            hypothesis_id=self.hypothesis_id,
            target_kind=self.target_kind,
            proposed_artifact=artifact,
            satisfied_fields=satisfied,
            missing_fields=missing,
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
            "proposed_artifact": dict(self.proposed_artifact),
            "satisfied_fields": list(self.satisfied_fields),
            "missing_fields": list(self.missing_fields),
            "applicability_context_id": self.applicability_context_id,
            "language_tag": self.language_tag,
            "scope": self.scope,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "evidence_event_ids": list(self.evidence_event_ids),
            "provenance_ref": self.provenance_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningHypothesis":
        raw_kind = str(data.get("target_kind", HypothesisTargetKind.CONCEPT_CANDIDATE.value) or HypothesisTargetKind.CONCEPT_CANDIDATE.value)
        try:
            target_kind = HypothesisTargetKind(raw_kind)
        except ValueError:
            target_kind = HypothesisTargetKind.CONCEPT_CANDIDATE
        return cls(
            hypothesis_id=str(data.get("hypothesis_id", "") or ""),
            target_kind=target_kind,
            proposed_artifact=dict(data.get("proposed_artifact", {}) or {}),
            satisfied_fields=tuple(str(v) for v in data.get("satisfied_fields", []) or [] if v),
            missing_fields=tuple(str(v) for v in data.get("missing_fields", []) or [] if v),
            applicability_context_id=str(data.get("applicability_context_id", "") or ""),
            language_tag=str(data.get("language_tag", "und") or "und"),
            scope=str(data.get("scope", "session") or "session"),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            source_refs=tuple(str(v) for v in data.get("source_refs", []) or [] if v),
            evidence_event_ids=tuple(str(v) for v in data.get("evidence_event_ids", []) or [] if v),
            provenance_ref=str(data.get("provenance_ref", "") or ""),
        )
