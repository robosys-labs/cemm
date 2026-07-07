"""Selector — realize top K candidates, surface score, select final output.

The selector is the last step before the ResponseBundle. It takes ranked
candidate plans, realizes the top K (budget-aware), scores the surface text,
and selects the best realized candidate.

Surface scoring is language-agnostic heuristics: nonempty, no leakage, no
generic fallback, appropriate length. It does NOT parse English meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .realization.executor import RealizationExecutor
from .types import RealizedCandidate, ResponseCandidatePlan, ResponseSituation


@dataclass
class SelectionResult:
    selected: RealizedCandidate | None = None
    rejected: list[RealizedCandidate] = field(default_factory=list)
    rejection_reasons: dict[str, list[str]] = field(default_factory=dict)


class Selector:
    """Realize top K plans and select the best surface candidate."""

    def __init__(self, realizer: RealizationExecutor | None = None) -> None:
        self._realizer = realizer or RealizationExecutor()

    def select(
        self,
        ranked_plans: list[ResponseCandidatePlan],
        situation: ResponseSituation,
        *,
        max_realized: int = 3,
    ) -> SelectionResult:
        top_k = ranked_plans[:max_realized]
        if not top_k:
            return SelectionResult()

        realized: list[RealizedCandidate] = []
        for plan in top_k:
            candidate = self._realize_plan(plan, situation)
            if candidate is not None:
                realized.append(candidate)

        if not realized:
            return SelectionResult()

        # Score surfaces and pick best
        scored = [(cand, self._surface_score(cand, situation)) for cand in realized]
        scored.sort(key=lambda pair: (-pair[1], pair[0].plan.plan_id))

        selected = scored[0][0]
        rejected = [cand for cand, _ in scored[1:]]
        reasons: dict[str, list[str]] = {}
        for cand, score in scored[1:]:
            reasons[cand.plan.plan_id] = [f"surface_score={score:.4f}"]

        return SelectionResult(
            selected=selected,
            rejected=rejected,
            rejection_reasons=reasons,
        )

    def _realize_plan(
        self,
        plan: ResponseCandidatePlan,
        situation: ResponseSituation,
    ) -> RealizedCandidate | None:
        # Create a situation copy with the plan's style for realization
        styled = self._with_style(situation, plan.style)
        try:
            candidate = self._realizer.realize_candidate(plan.moves, styled)
            # Override the plan with the candidate's plan (keeps framing variant)
            candidate.plan = plan
            return candidate
        except Exception:
            return None

    @staticmethod
    def _with_style(situation: ResponseSituation, style) -> ResponseSituation:
        # Shallow copy with overridden style
        import copy
        styled = copy.copy(situation)
        styled.style = style
        return styled

    @staticmethod
    def _surface_score(candidate: RealizedCandidate, situation: ResponseSituation) -> float:
        text = candidate.text or ""
        score = 0.0

        # Nonempty
        if not text.strip():
            return -1.0
        score += 1.0

        # Not a generic fallback
        generic_fallbacks = {
            "i don't have enough verified information to answer that.",
            "i can't help with that request.",
            "what?",
            "what",
            "huh?",
            "hmm",
        }
        if text.strip().lower() in generic_fallbacks:
            score -= 2.0

        # No internal surface leakage (role labels, relation keys)
        leakage_markers = {"possessor", "has_property", "has_name", "has_role",
                          "relation_key", "obligation_kind", "slot_fill"}
        text_lower = text.lower()
        for marker in leakage_markers:
            if marker in text_lower:
                score -= 1.5
                break

        # Appropriate length (not too short, not too long)
        length = len(text)
        if length < 5:
            score -= 1.0
        elif length > 500:
            score -= 0.5
        else:
            score += 0.5

        # Safety: safety responses should contain refusal language
        if any(m.safety_required for m in candidate.plan.moves):
            refusal_words = {"no", "can't", "cannot", "don't", "not going to"}
            if any(w in text_lower for w in refusal_words):
                score += 2.0
            else:
                score -= 3.0

        # Plan score contribution
        score += candidate.plan.total_score * 0.3

        return round(score, 4)
