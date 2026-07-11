from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class EvidenceKind(str, Enum):
    """Kinds of learning evidence events."""
    OBSERVED_OCCURRENCE = "observed_occurrence"
    EXPLICIT_DEFINITION = "explicit_definition"
    EXPLICIT_CONFIRMATION = "explicit_confirmation"
    EXPLICIT_CORRECTION = "explicit_correction"
    SUCCESSFUL_INTERPRETATION = "successful_interpretation"
    SUCCESSFUL_USE = "successful_use"
    REPAIR_CAUSED = "repair_caused"
    PREDICTION_CONFIRMED = "prediction_confirmed"
    PREDICTION_FAILED = "prediction_failed"
    INDEPENDENT_SOURCE_SUPPORT = "independent_source_support"
    CONTRADICTION = "contradiction"
    CONTEXT_RESTRICTION = "context_restriction"
    TEMPORAL_SUPERSESSION = "temporal_supersession"
    TRANSLATION_ALIGNMENT = "translation_alignment"
    MULTIMODAL_ALIGNMENT = "multimodal_alignment"
    USER_CONFIRMATION = "user_confirmation"
    USER_CORRECTION = "user_correction"


class EvidenceStance(str, Enum):
    """How this evidence event relates to the hypothesis."""
    SUPPORT = "support"
    CONTRADICT = "contradict"
    RESTRICT = "restrict"
    SUPERSEDE = "supersede"


@dataclass(frozen=True, slots=True)
class LearningEvidenceEvent:
    """An append-only evidence event in a learning artifact's evidence ledger.

    Never deleted or mutated. New events are appended. The KnowledgeStrength
    is derived from the full event history.
    """
    event_id: str
    target_hypothesis_id: str
    evidence_kind: EvidenceKind
    stance: EvidenceStance = EvidenceStance.SUPPORT
    weight: float = 0.5
    source_id: str = ""
    source_trust: float = 0.5
    independence_key: str = ""
    language_tag: str = "und"
    context_signature_id: str = ""
    observed_at: float = 0.0
    signal_id: str = ""
    turn_index: int = 0
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "target_hypothesis_id": self.target_hypothesis_id,
            "evidence_kind": self.evidence_kind.value,
            "stance": self.stance.value,
            "weight": self.weight,
            "source_id": self.source_id,
            "source_trust": self.source_trust,
            "independence_key": self.independence_key,
            "language_tag": self.language_tag,
            "observed_at": self.observed_at,
            "turn_index": self.turn_index,
        }


class UseOutcomeKind(str, Enum):
    """Outcome of using a learned artifact in interpretation/response."""
    BINDING_SELECTED = "binding_selected"
    BRANCH_MARGIN = "branch_margin"
    QUERY_SUCCESS = "query_success"
    QUERY_FAILURE = "query_failure"
    WRITE_SUCCESS = "write_success"
    WRITE_FAILURE = "write_failure"
    STATE_APPLIED = "state_applied"
    RESPONSE_SUCCESS = "response_success"
    RESPONSE_REPAIR = "response_repair"
    USER_CONFIRMATION = "user_confirmation"
    USER_CORRECTION = "user_correction"
    SUBSEQUENT_REFERENCE_RESOLVED = "subsequent_reference_resolved"
    SUBSEQUENT_REFERENCE_FAILED = "subsequent_reference_failed"


@dataclass(frozen=True, slots=True)
class LearningUseOutcome:
    """Evidence from using a learned artifact during interpretation."""
    outcome_id: str
    hypothesis_id: str
    outcome_kind: UseOutcomeKind
    confidence: float = 0.5
    signal_id: str = ""
    turn_index: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_evidence_event(self) -> LearningEvidenceEvent:
        kind_map = {
            UseOutcomeKind.BINDING_SELECTED: EvidenceKind.SUCCESSFUL_INTERPRETATION,
            UseOutcomeKind.QUERY_SUCCESS: EvidenceKind.SUCCESSFUL_USE,
            UseOutcomeKind.WRITE_SUCCESS: EvidenceKind.SUCCESSFUL_USE,
            UseOutcomeKind.RESPONSE_SUCCESS: EvidenceKind.SUCCESSFUL_USE,
            UseOutcomeKind.RESPONSE_REPAIR: EvidenceKind.REPAIR_CAUSED,
            UseOutcomeKind.USER_CONFIRMATION: EvidenceKind.USER_CONFIRMATION,
            UseOutcomeKind.USER_CORRECTION: EvidenceKind.USER_CORRECTION,
            UseOutcomeKind.SUBSEQUENT_REFERENCE_RESOLVED: EvidenceKind.SUCCESSFUL_USE,
            UseOutcomeKind.SUBSEQUENT_REFERENCE_FAILED: EvidenceKind.REPAIR_CAUSED,
        }
        evidence_kind = kind_map.get(self.outcome_kind, EvidenceKind.OBSERVED_OCCURRENCE)
        stance = EvidenceStance.SUPPORT if self.confidence >= 0.5 else EvidenceStance.CONTRADICT
        return LearningEvidenceEvent(
            event_id=f"ev_{self.outcome_id}",
            target_hypothesis_id=self.hypothesis_id,
            evidence_kind=evidence_kind,
            stance=stance,
            weight=self.confidence,
            source_id=self.signal_id,
            signal_id=self.signal_id,
            turn_index=self.turn_index,
            observed_at=0.0,
        )
