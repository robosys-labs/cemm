"""Policy for selective independent semantic round-trip verification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .proof import SemanticPreservationAssessment


class VerificationMode(str, Enum):
    BLOCK = "block"
    PROOF_ONLY = "proof_only"
    PROOF_PLUS_INDEPENDENT_ROUNDTRIP = "proof_plus_independent_roundtrip"


class RoundTripReason(str, Enum):
    NOVELTY = "novelty"
    HIGH_RISK = "high_risk"
    AUDIT = "audit"
    RELEASE_COMPETENCE = "release_competence"
    UNREVIEWED_TRANSFORM = "unreviewed_transform"
    CHANNEL_TRANSFORM = "channel_transform"


@dataclass(frozen=True, slots=True)
class VerificationPolicyDecision:
    mode: VerificationMode
    reason_refs: tuple[str, ...]


class SelectiveRoundTripPolicy:
    """Cheap proof is mandatory. Full re-analysis is additive, never a proof bypass."""

    def decide(
        self,
        *,
        preservation: SemanticPreservationAssessment,
        novelty: bool = False,
        risk_refs: Iterable[str] = (),
        audit_required: bool = False,
        release_competence: bool = False,
        unreviewed_transform: bool = False,
        channel: Any | None = None,
    ) -> VerificationPolicyDecision:
        if not preservation.passed:
            return VerificationPolicyDecision(
                VerificationMode.BLOCK,
                tuple(sorted(set(("semantic_preservation_proof_failed", *preservation.reason_refs)))),
            )
        reasons = []
        if novelty:
            reasons.append(RoundTripReason.NOVELTY.value)
        if tuple(risk_refs):
            reasons.append(RoundTripReason.HIGH_RISK.value)
        if audit_required:
            reasons.append(RoundTripReason.AUDIT.value)
        if release_competence:
            reasons.append(RoundTripReason.RELEASE_COMPETENCE.value)
        if unreviewed_transform:
            reasons.append(RoundTripReason.UNREVIEWED_TRANSFORM.value)
        if channel is not None and getattr(channel, "transformation_refs", ()):
            if not getattr(channel, "content_preserving_transform_only", False) or getattr(channel, "requires_post_transform_roundtrip", False):
                reasons.append(RoundTripReason.CHANNEL_TRANSFORM.value)
        return VerificationPolicyDecision(
            VerificationMode.PROOF_PLUS_INDEPENDENT_ROUNDTRIP if reasons else VerificationMode.PROOF_ONLY,
            tuple(sorted(set(reasons))),
        )


__all__ = [
    "RoundTripReason", "SelectiveRoundTripPolicy", "VerificationMode",
    "VerificationPolicyDecision",
]
