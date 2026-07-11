from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class PromotionState(str, Enum):
    """Promotion states for learned artifacts."""
    OBSERVED_CANDIDATE = "observed_candidate"
    HYPOTHESIZED = "hypothesized"
    MINIMALLY_GROUNDED = "minimally_grounded"
    SESSION_PROVISIONAL = "session_provisional"
    USER_SCOPED_ACTIVE = "user_scoped_active"
    DOMAIN_SCOPED_ACTIVE = "domain_scoped_active"
    LANGUAGE_SCOPED_ACTIVE = "language_scoped_active"
    STABLE = "stable"
    CONTESTED = "contested"
    SUPERSEDED = "superseded"
    RETIRED = "retired"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class KnowledgeStrength:
    """Derived knowledge strength vector computed from an append-only evidence ledger.

    Never stored as a single mutable confidence number. All fields are derived
    from evidence events via KnowledgeStrengthProjector.
    """
    semantic_confidence: float = 0.0
    source_trust: float = 0.0
    support_mass: float = 0.0
    contradiction_mass: float = 0.0
    source_diversity: float = 0.0
    context_coverage: float = 0.0
    language_coverage: float = 0.0
    successful_use_rate: float = 0.0
    repair_failure_rate: float = 0.0
    stability: float = 0.0
    freshness: float = 0.0
    promotion_state: PromotionState = PromotionState.OBSERVED_CANDIDATE

    @property
    def net_support(self) -> float:
        return self.support_mass - self.contradiction_mass

    @property
    def is_promotable(self) -> bool:
        return (
            self.semantic_confidence >= 0.6
            and self.source_diversity >= 0.3
            and self.contradiction_mass < self.support_mass
            and self.stability >= 0.3
        )

    @property
    def is_contested(self) -> bool:
        return self.contradiction_mass >= self.support_mass * 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_confidence": self.semantic_confidence,
            "source_trust": self.source_trust,
            "support_mass": self.support_mass,
            "contradiction_mass": self.contradiction_mass,
            "source_diversity": self.source_diversity,
            "context_coverage": self.context_coverage,
            "language_coverage": self.language_coverage,
            "successful_use_rate": self.successful_use_rate,
            "repair_failure_rate": self.repair_failure_rate,
            "stability": self.stability,
            "freshness": self.freshness,
            "promotion_state": self.promotion_state.value,
        }


def compute_knowledge_strength(
    support_events: int = 0,
    contradiction_events: int = 0,
    independent_sources: int = 1,
    total_uses: int = 0,
    failures: int = 0,
    age_hours: float = 0.0,
    source_trust: float = 0.5,
) -> KnowledgeStrength:
    """Compute KnowledgeStrength from raw event counts.

    This is a simple projection used before the full evidence-ledger-based
    KnowledgeStrengthProjector is available.
    """
    support_mass = min(1.0, support_events * 0.15)
    contradiction_mass = min(1.0, contradiction_events * 0.2)
    source_diversity = min(1.0, independent_sources * 0.25)

    use_rate = 0.0
    fail_rate = 0.0
    if total_uses > 0:
        use_rate = (total_uses - failures) / total_uses
        fail_rate = failures / total_uses

    stability = min(1.0, (support_events + 1) * 0.1)
    freshness = max(0.0, 1.0 - age_hours / 720.0)  # 30-day half-life

    # Semantic confidence combines support, trust, and diversity
    raw_conf = (support_mass * 0.4 + source_trust * 0.3 + source_diversity * 0.3)
    # Penalize by contradiction
    if support_mass + contradiction_mass > 0:
        contradiction_penalty = contradiction_mass / (support_mass + contradiction_mass)
        raw_conf *= (1.0 - contradiction_penalty * 0.5)
    semantic_confidence = max(0.0, min(1.0, raw_conf))

    return KnowledgeStrength(
        semantic_confidence=semantic_confidence,
        source_trust=source_trust,
        support_mass=support_mass,
        contradiction_mass=contradiction_mass,
        source_diversity=source_diversity,
        context_coverage=source_diversity,
        language_coverage=1.0 if source_diversity > 0.5 else source_diversity,
        successful_use_rate=use_rate,
        repair_failure_rate=fail_rate,
        stability=stability,
        freshness=freshness,
    )
