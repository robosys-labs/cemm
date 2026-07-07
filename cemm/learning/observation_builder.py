"""Build sanitized learning observations from response artifacts."""

from __future__ import annotations

from typing import Any

from cemm.response.types import ResponseBundle, ResponseSituation

from .outcome_interpreter import OutcomeInterpreter
from .learning_types import LearningObservation, OutcomeSignal


class LearningObservationBuilder:
    def __init__(self) -> None:
        self._outcome_interpreter = OutcomeInterpreter()

    def build(
        self,
        *,
        situation: ResponseSituation,
        bundle: ResponseBundle,
        explicit_outcome: OutcomeSignal | None = None,
    ) -> LearningObservation:
        decision = bundle.budget_decision or situation.budget_decision
        stage = getattr(decision, "stage_budget", None)
        distillation = bundle.distillation_result or situation.distillation_result
        safety_tags = list(bundle.safety_tags or [])
        write = bundle.write_outcome or situation.write_outcome
        outcome = self._outcome_interpreter.interpret(situation.reaction_signal, explicit_outcome)
        selected_plan = _selected_plan(bundle)
        return LearningObservation(
            selected_plan_id=bundle.selected_plan_id,
            framing_variant=getattr(selected_plan, "framing_variant", "") or _diag(bundle, "selected_plan", "framing_variant"),
            move_types=[move.move_type for move in bundle.moves],
            obligation_kind=bundle.obligation_kind,
            budget_pressure=float(getattr(decision, "pressure", 0.0) or 0.0),
            selector_mode=str(getattr(stage, "selector_mode", "") or ""),
            candidate_count=int(_diag(bundle, "candidate_count") or 0),
            rejected_count=len(bundle.rejected_plans or []),
            realized_language=bundle.language,
            evidence_ref_count=len(bundle.evidence_refs or []),
            coverage_estimate=_maybe_float(getattr(distillation, "coverage_estimate", None)),
            partial_coverage=bool(getattr(distillation, "partial", False)) if distillation is not None else False,
            safety_categories=safety_tags,
            write_commit_status=getattr(write, "commit_status", "") if write is not None else "",
            outcome=outcome,
            source_refs=_dedupe([*bundle.evidence_refs, *outcome.source_refs, bundle.selected_plan_id]),
        )


def _selected_plan(bundle: ResponseBundle) -> Any | None:
    selected = bundle.diagnostics.get("selected_plan", {}) if isinstance(bundle.diagnostics, dict) else {}
    if selected:
        return type("SelectedPlanView", (), selected)()
    return None


def _diag(bundle: ResponseBundle, *path: str) -> Any:
    value: Any = bundle.diagnostics if isinstance(bundle.diagnostics, dict) else {}
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
