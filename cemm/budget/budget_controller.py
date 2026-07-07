"""BudgetController — canonical Phase 5 budget arbitration."""

from __future__ import annotations

from typing import Any

from cemm.response.types import BudgetDecision, BudgetFrame, ResponseSituation
from .deadline_parser import DeadlineParser
from .stage_budget_allocator import StageBudgetAllocator
from .task_size_estimator import TaskSizeEstimator


class BudgetController:
    def __init__(self) -> None:
        self._deadline_parser = DeadlineParser()
        self._task_size_estimator = TaskSizeEstimator()
        self._allocator = StageBudgetAllocator()

    def decide(self, situation: ResponseSituation) -> BudgetDecision:
        base = situation.budget_frame
        if base is None:
            base = BudgetFrame()
        hint = self._deadline_parser.parse(percept=situation.percept, signal=situation.signal, kernel=situation.kernel)
        budget = self._deadline_parser.apply(base, hint)
        task = self._task_size_estimator.estimate(situation=situation)
        risk = self._risk_level(situation, budget)
        decision = self._allocator.allocate(budget, task_size=task.score, risk_level=risk, temperature=situation.temperature)
        decision.stage_budget.diagnostics.update({
            "deadline_hint_ms": hint.deadline_ms,
            "deadline_source": hint.source,
            "task_level": task.level,
            "task_features": task.features,
        })
        if hint.deadline_ms > 0:
            decision.reasons.append("semantic_deadline")
        return decision

    @staticmethod
    def _risk_level(situation: ResponseSituation, budget: BudgetFrame) -> str:
        safety = situation.safety_frame
        if safety is not None:
            category = (getattr(safety, "category", "") or getattr(safety, "risk_type", "") or "").lower()
            severity = (getattr(safety, "severity", "") or getattr(safety, "risk_level", "") or "").lower()
            if category and category not in {"none", "safe", "low"}:
                return severity or "high"
        return (budget.risk_level or "normal").lower()
