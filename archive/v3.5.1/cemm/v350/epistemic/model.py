"""Phase-11 epistemic admission and cycle-local grounded belief contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..conversation.session_memory import SessionBeliefEntry


class AdmissionClass(str, Enum):
    ATTRIBUTED_ONLY = "ATTRIBUTED_ONLY"
    SESSION_PARTICIPANT_FACT = "SESSION_PARTICIPANT_FACT"
    SCOPED_USER_ASSERTED_FACT = "SCOPED_USER_ASSERTED_FACT"
    CORROBORATION_REQUIRED = "CORROBORATION_REQUIRED"
    HIGH_RISK_NO_AUTO_ADMISSION = "HIGH_RISK_NO_AUTO_ADMISSION"
    HYPOTHETICAL_ONLY = "HYPOTHETICAL_ONLY"


class EpistemicDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    PRESERVE_ONLY = "preserve_only"


@dataclass(frozen=True, slots=True)
class AdmissionAssessment:
    assessment_ref: str
    claim_ref: str
    proposition_ref: str
    admission_class: AdmissionClass
    decision: EpistemicDecision
    source_ref: str
    source_context_ref: str
    target_context_ref: str
    permission_ref: str
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkingBeliefDelta:
    delta_ref: str
    context_ref: str
    permission_ref: str
    base_session_revision: int
    additions: tuple[SessionBeliefEntry, ...] = ()
    retract_claim_refs: tuple[str, ...] = ()
    supersede_claims: tuple[tuple[str, str], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.base_session_revision < 0:
            raise ValueError("working belief base session revision cannot be negative")
        if len(self.retract_claim_refs) != len(set(self.retract_claim_refs)):
            raise ValueError("working belief retract refs must be unique")
        old = tuple(item[0] for item in self.supersede_claims)
        if len(old) != len(set(old)):
            raise ValueError("a claim cannot be superseded twice in one working delta")


@dataclass(frozen=True, slots=True)
class EpistemicPlacement:
    placement_ref: str
    context_ref: str
    permission_ref: str
    assessments: tuple[AdmissionAssessment, ...]
    attributed_claim_refs: tuple[str, ...]
    admitted_claim_refs: tuple[str, ...]
    preserved_hypothesis_refs: tuple[str, ...]
    contradiction_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()


__all__ = [
    "AdmissionAssessment", "AdmissionClass", "EpistemicDecision",
    "EpistemicPlacement", "WorkingBeliefDelta",
]
