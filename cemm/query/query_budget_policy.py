"""Derive query spend rules from BudgetDecision/StageBudget.

No surface-language parsing is allowed here.  The policy is computed from
BudgetFrame, BudgetDecision, risk, confidence target, and stage-budget fields.
"""

from __future__ import annotations

from typing import Any

from cemm.response.types import BudgetDecision, BudgetFrame, StageBudget
from .types import QueryBudgetPolicy

_HIGH_RISK = {"high", "critical", "imminent", "unsafe", "safety"}


class QueryBudgetPolicyBuilder:
    def build(
        self,
        *,
        budget_decision: BudgetDecision | None = None,
        budget_frame: BudgetFrame | None = None,
        evidence_policy: str = "",
    ) -> QueryBudgetPolicy:
        budget = budget_frame or getattr(budget_decision, "input_budget", None) or BudgetFrame()
        stage = getattr(budget_decision, "stage_budget", None) or StageBudget()
        pressure = float(getattr(budget_decision, "pressure", 0.0) or 0.0)
        risk = str(getattr(budget_decision, "risk_level", getattr(budget, "risk_level", "normal")) or "normal").lower()
        high_risk = risk in _HIGH_RISK

        max_results = max(1, int(getattr(stage, "query_result_limit", 8) or 8))
        if pressure >= 0.85:
            max_results = min(max_results, 3)
        elif pressure >= 0.65:
            max_results = min(max_results, 6)
        if high_risk:
            max_results = min(max_results, 4)

        max_frame_scan = max(max_results, int(max_results * (2 if pressure >= 0.75 else 4)))
        if pressure < 0.35:
            max_frame_scan = max(max_frame_scan, 128)

        min_conf = max(0.0, min(1.0, float(getattr(budget, "required_confidence", 0.5) or 0.5)))
        min_conf = max(min_conf, float(getattr(stage, "query_min_confidence", 0.0) or 0.0))
        if high_risk:
            min_conf = max(min_conf, 0.7)
        elif pressure >= 0.75:
            min_conf = max(min_conf, 0.55)

        return QueryBudgetPolicy(
            max_results=max_results,
            max_frame_scan=max_frame_scan,
            max_inference_depth=max(0, int(getattr(stage, "max_query_inference_depth", getattr(stage, "explanation_depth", 1)) or 1)),
            explanation_depth=max(0, int(getattr(stage, "explanation_depth", 1) or 1)),
            allow_inverse=bool(getattr(stage, "allow_inverse_query", True)) and not pressure >= 0.9,
            allow_inheritance=bool(getattr(stage, "allow_inheritance_query", True)) and not pressure >= 0.95,
            allow_composition=bool(getattr(stage, "allow_composition_query", False)) and pressure < 0.35 and not high_risk,
            stop_on_first_sufficient=bool(getattr(stage, "stop_on_first_sufficient_query", pressure >= 0.65 or high_risk)) or high_risk,
            min_confidence=min_conf,
            require_evidence_refs=(evidence_policy == "required") or high_risk,
            prefer_current_turn=True,
            diagnostics={
                "pressure": pressure,
                "risk_level": risk,
                "evidence_policy": evidence_policy,
                "source": "budget_decision" if budget_decision is not None else "budget_frame",
            },
        )
