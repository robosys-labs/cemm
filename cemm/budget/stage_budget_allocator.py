"""Allocate response-stage spend from a BudgetFrame."""

from __future__ import annotations

from typing import Any

from cemm.response.types import BudgetDecision, BudgetFrame, StageBudget


_HIGH_RISK = {"high", "critical", "imminent", "unsafe", "safety"}


class StageBudgetAllocator:
    def allocate(self, budget: BudgetFrame, *, task_size: float = 0.0, risk_level: str = "normal", temperature: Any | None = None) -> BudgetDecision:
        remaining = max(0.0, float(budget.remaining_time_ms or 0.0))
        target = max(1.0, float(budget.latency_target_ms or 1.0))
        urgency = float(getattr(temperature, "user_urgency", 0.0) or 0.0)
        pressure = max(0.0, min(1.0, 1.0 - min(1.0, remaining / max(target * 8.0, 1.0))))
        pressure = max(pressure, max(0.0, min(1.0, urgency)))

        risk = (risk_level or budget.risk_level or "normal").lower()
        high_risk = risk in _HIGH_RISK
        reasons: list[str] = []
        if pressure >= 0.7:
            reasons.append("tight_time_budget")
        if task_size >= 0.65:
            reasons.append("large_task")
        if high_risk:
            reasons.append("high_risk")

        if high_risk:
            selector_mode = "deterministic_strict"
            candidate_limit = 1
            realized_limit = 1
        elif pressure >= 0.75:
            selector_mode = "first_good_enough"
            candidate_limit = min(2, max(1, budget.max_candidate_plans))
            realized_limit = 1
        elif pressure >= 0.45 or task_size >= 0.75:
            selector_mode = "score"
            candidate_limit = min(4, max(1, budget.max_candidate_plans))
            realized_limit = min(2, max(1, budget.max_realized_candidates))
        else:
            selector_mode = "score"
            candidate_limit = max(1, budget.max_candidate_plans)
            realized_limit = max(1, budget.max_realized_candidates)

        detail_level = max(0.0, min(1.0, budget.coverage_target))
        if pressure >= 0.7:
            detail_level = min(detail_level, 0.35)
        elif task_size >= 0.75:
            detail_level = min(detail_level, 0.55)

        stage = StageBudget(
            attention_focus_limit=max(4, int(8 + (1.0 - pressure) * 24)),
            query_result_limit=max(1, int(4 + (1.0 - pressure) * 28)),
            candidate_plan_limit=int(candidate_limit),
            realized_candidate_limit=int(min(candidate_limit, realized_limit)),
            explanation_depth=1 if pressure >= 0.6 else 2 if task_size < 0.65 else 1,
            selector_mode=selector_mode,
            allow_inverse_query=not pressure >= 0.85 and not high_risk,
            allow_inheritance_query=not pressure >= 0.9,
            allow_recursive_distillation=bool(budget.allow_recursive_distillation and not high_risk and pressure < 0.45),
            allow_composition_query=bool(budget.allow_recursive_distillation and not high_risk and pressure < 0.30 and task_size >= 0.35),
            max_query_inference_depth=0 if pressure >= 0.9 else 1 if pressure >= 0.55 or high_risk else 2,
            stop_on_first_sufficient_query=bool(pressure >= 0.65 or high_risk),
            query_min_confidence=max(0.7 if high_risk else 0.55 if pressure >= 0.75 else 0.5, float(budget.required_confidence or 0.0)),
            detail_level=detail_level,
            diagnostics={
                "remaining_time_ms": remaining,
                "latency_target_ms": target,
                "pressure": pressure,
                "task_size": task_size,
                "risk_level": risk,
            },
        )
        return BudgetDecision(
            input_budget=budget,
            stage_budget=stage,
            pressure=pressure,
            task_size=task_size,
            risk_level=risk,
            reasons=reasons,
        )
