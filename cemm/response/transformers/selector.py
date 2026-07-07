"""Budget-aware response selector."""

from __future__ import annotations

from ..types import ResponseCandidatePlan, ResponseSituation


class Selector:
    def select(self, plans: list[ResponseCandidatePlan], situation: ResponseSituation) -> ResponseCandidatePlan:
        if not plans:
            return ResponseCandidatePlan(plan_id="none", blocked_reason="no_plans")
        stage = getattr(getattr(situation, "budget_decision", None), "stage_budget", None)
        mode = getattr(stage, "selector_mode", "score") if stage is not None else "score"
        viable = [plan for plan in plans if not plan.blocked_reason]
        if not viable:
            return plans[0]
        if mode == "deterministic_strict":
            return sorted(viable, key=lambda p: (-p.score_parts.get("safety", 0.0), -p.total_score, p.estimated_cost_ms, p.plan_id))[0]
        if mode == "first_good_enough":
            threshold = max(0.62, float(getattr(situation.budget_frame, "required_confidence", 0.3) or 0.3))
            for plan in viable:
                if plan.total_score >= threshold:
                    return plan
            return viable[0]
        return viable[0]
