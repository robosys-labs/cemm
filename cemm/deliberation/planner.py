"""Budget-aware deliberation strategy selection."""

from __future__ import annotations

from typing import Any

from cemm.budget import BudgetController
from cemm.response.types import BudgetDecision, BudgetFrame, ResponseSituation

from .source_mapper import SourceMapper
from .types import DeliberationPlan, SourceDescriptor


class DeliberationPlanner:
    def __init__(self) -> None:
        self._budget_controller = BudgetController()
        self._source_mapper = SourceMapper()

    def plan(self, situation: ResponseSituation, sources: list[Any] | None = None) -> DeliberationPlan:
        decision = situation.budget_decision or self._budget_controller.decide(situation)
        situation.budget_decision = decision
        descriptors = [self._source_mapper.describe(s) for s in (sources or [])]
        risk = decision.risk_level
        if self._is_safety_risk(situation, risk):
            return self._plan("safety_first", "none", "none", "none", situation, decision, descriptors, ["safety_risk"])
        if not descriptors:
            if self._needs_clarification(situation):
                return self._plan("ask_clarification", "none", "none", "none", situation, decision, descriptors, ["missing_required_slots"])
            return self._plan("direct_answer", "shallow", "narrow", "none", situation, decision, descriptors, ["no_large_sources"])

        source_load = self._source_load(descriptors)
        budget = decision.input_budget
        pressure = decision.pressure
        remaining = budget.remaining_time_ms
        allow_recursive = bool(budget.allow_recursive_distillation or decision.stage_budget.allow_recursive_distillation)

        if source_load >= 0.65 and (pressure >= 0.65 or remaining <= 300000):
            return self._plan("rapid_skim", "sampled", "sampled", "rapid_skim", situation, decision, descriptors, ["large_source_tight_budget"])
        if source_load >= 0.45 and allow_recursive and remaining >= 300000:
            return self._plan("recursive_distill", "recursive", "sampled", "recursive", situation, decision, descriptors, ["recursive_distillation_allowed"])
        if source_load >= 0.45 and budget.coverage_target >= 0.85 and remaining >= 900000:
            return self._plan("deep_synthesis", "deep", "broad", "deep", situation, decision, descriptors, ["high_coverage_budget"])
        if source_load >= 0.45 and budget.allow_partial_answer:
            return self._plan("partial_with_limits", "sampled", "sampled", "rapid_skim", situation, decision, descriptors, ["partial_answer_allowed"])
        if source_load >= 0.45:
            return self._plan("ask_clarification", "none", "none", "none", situation, decision, descriptors, ["budget_insufficient_without_partial"])
        return self._plan("direct_answer", "shallow", "narrow", "none", situation, decision, descriptors, ["small_source"])

    def _plan(
        self,
        strategy: str,
        depth: str,
        retrieval_policy: str,
        distillation_policy: str,
        situation: ResponseSituation,
        decision: BudgetDecision,
        descriptors: list[SourceDescriptor],
        reasons: list[str],
    ) -> DeliberationPlan:
        budget: BudgetFrame = decision.input_budget
        disclosure: list[str] = []
        if strategy in {"rapid_skim", "partial_with_limits"}:
            disclosure.extend(["coverage_note", "read_units_note", "blind_spots_note"])
        max_steps = 0
        if strategy == "recursive_distill":
            max_steps = max(1, min(budget.max_recursive_steps, decision.stage_budget.max_query_inference_depth + 1))
        elif strategy == "deep_synthesis":
            max_steps = max(1, budget.max_recursive_steps)
        return DeliberationPlan(
            strategy=strategy,
            depth=depth,
            retrieval_policy=retrieval_policy,
            distillation_policy=distillation_policy,
            confidence_target=max(budget.required_confidence, 0.7 if strategy == "safety_first" else budget.required_confidence),
            coverage_target=budget.coverage_target,
            max_recursive_steps=max_steps,
            stop_conditions=self._stop_conditions(strategy, decision),
            disclosure_requirements=disclosure,
            source_ids=[d.source_id for d in descriptors],
            reasons=reasons,
            diagnostics={
                "pressure": decision.pressure,
                "task_size": decision.task_size,
                "risk_level": decision.risk_level,
                "source_load": self._source_load(descriptors),
                "source_count": len(descriptors),
            },
        )

    @staticmethod
    def _stop_conditions(strategy: str, decision: BudgetDecision) -> list[str]:
        base = ["budget_exhausted", "confidence_target_met"]
        if strategy in {"rapid_skim", "partial_with_limits"}:
            base.append("minimum_viable_coverage_met")
        if decision.stage_budget.stop_on_first_sufficient_query:
            base.append("first_sufficient_evidence")
        return base

    @staticmethod
    def _is_safety_risk(situation: ResponseSituation, risk: str) -> bool:
        safety = situation.safety_frame
        category = getattr(safety, "category", "") if safety is not None else ""
        return bool(category and category != "none") or risk in {"high", "critical"}

    @staticmethod
    def _needs_clarification(situation: ResponseSituation) -> bool:
        obligation = situation.obligation_frame
        if obligation is None:
            return False
        blocked = list(getattr(obligation, "blocked_by", []) or [])
        missing = list(getattr(obligation, "required_slots", []) or [])
        binding = situation.answer_binding
        has_answer = bool(getattr(binding, "has_answer", False))
        return bool(blocked) or (bool(missing) and not has_answer)

    @staticmethod
    def _source_load(descriptors: list[SourceDescriptor]) -> float:
        if not descriptors:
            return 0.0
        scores = []
        for d in descriptors:
            unit = min(1.0, d.unit_count / 120.0) if d.unit_count else 0.0
            token = min(1.0, d.token_count / 120000.0) if d.token_count else 0.0
            sections = min(1.0, d.section_count / 60.0) if d.section_count else 0.0
            artifacts = min(1.0, d.artifact_count / 40.0) if d.artifact_count else 0.0
            scores.append(max(unit, token, sections, artifacts))
        return max(scores)
