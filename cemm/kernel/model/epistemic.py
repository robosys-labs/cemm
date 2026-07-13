"""EpistemicAssessment — truth/admissibility assessment for a proposition.

Import boundary: standard library only → refs, identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import AssessmentEnvironmentFingerprint


@dataclass(frozen=True, slots=True)
class EpistemicAssessment:
    """Epistemic assessment of a proposition in a context.

    Decides admissibility — whether a proposition can be used as
    actual-world knowledge, attributed theory, or is contested/blocked.
    """
    proposition_ref: str  # Ref[Proposition]
    context_ref: str  # Ref[ContextFrame]
    support_state: str = "neither"  # supported, refuted, both, neither
    support_score: float = 0.0
    opposition_score: float = 0.0
    confidence: float = 0.0
    accessible: bool = True
    fresh_enough: bool = True
    permission_allowed: bool = True
    schema_use_valid: bool = True
    admissibility: str = "admitted"  # admitted, attributed_only, contested, blocked
    causal_warrant_grade: str | None = None
    lineage_independence_count: int = 0
    explanation_refs: tuple[str, ...] = ()
    environment_fingerprint: AssessmentEnvironmentFingerprint | None = None
