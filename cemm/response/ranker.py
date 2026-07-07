"""Plan ranker — scores and sorts candidate plans.

Scoring is language-agnostic. It uses plan metadata, confidence, safety,
evidence, and framing variant weights. Surface text is not evaluated here —
that happens in the Selector after realization.
"""

from __future__ import annotations

from .types import ResponseCandidatePlan, ResponseSituation


class PlanRanker:
    """Score and rank candidate plans that passed hard gates."""

    def rank(
        self,
        plans: list[ResponseCandidatePlan],
        situation: ResponseSituation,
    ) -> list[ResponseCandidatePlan]:
        scored = [(plan, self._score(plan, situation)) for plan in plans]
        scored.sort(key=lambda pair: (-pair[1], pair[0].plan_id))
        return [plan for plan, _ in scored]

    def _score(self, plan: ResponseCandidatePlan, situation: ResponseSituation) -> float:
        parts: dict[str, float] = {}

        # Confidence: average move confidence
        move_confidences = [m.confidence for m in plan.moves]
        parts["confidence"] = sum(move_confidences) / len(move_confidences) if move_confidences else 0.3

        # Safety: safety moves get priority boost
        if any(m.safety_required for m in plan.moves):
            parts["safety"] = 1.0
        else:
            parts["safety"] = 0.0

        # Evidence: having evidence refs when answer is present
        if any(m.move_type == "answer" for m in plan.moves):
            parts["evidence"] = min(len(plan.evidence_refs) / 3.0, 1.0) if plan.evidence_refs else 0.0
        else:
            parts["evidence"] = 0.5

        # Framing variant weights from the plan
        for key, weight in plan.score_parts.items():
            if key in parts:
                parts[key] *= weight

        # Style alignment: prefer styles that match situation temperature
        style = plan.style
        temp = situation.temperature
        warmth_match = 1.0 - abs(style.warmth - (0.5 + temp.user_frustration * 0.3))
        parts["style_alignment"] = max(0.0, warmth_match)

        # Completeness: ratio of satisfied to required components
        if plan.required_components:
            completeness = len(plan.satisfied_components & plan.required_components) / len(plan.required_components)
        else:
            completeness = 1.0
        parts["completeness"] = completeness

        # Weighted sum
        weights = {
            "confidence": 1.0,
            "safety": 2.0,
            "evidence": 0.8,
            "style_alignment": 0.5,
            "completeness": 1.5,
        }
        total = sum(parts.get(k, 0.0) * w for k, w in weights.items())
        plan.score_parts = {k: round(v, 4) for k, v in parts.items()}
        plan.total_score = round(total, 4)
        return total
