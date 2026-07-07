"""Hard gates for candidate plan filtering.

Gates are binary pass/fail checks. A candidate that fails any gate is rejected.
Rejected candidates remain diagnosable via GateResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import ResponseCandidatePlan, ResponseSituation


@dataclass
class GateResult:
    plan_id: str
    passed: bool
    failed_checks: list[str] = field(default_factory=list)
    notes: dict[str, str] = field(default_factory=dict)


class PlanGate:
    """Validate candidate plans against hard constraints."""

    def filter(
        self,
        plans: list[ResponseCandidatePlan],
        situation: ResponseSituation,
    ) -> tuple[list[ResponseCandidatePlan], list[GateResult]]:
        results: list[GateResult] = []
        passed: list[ResponseCandidatePlan] = []
        for plan in plans:
            result = self._check(plan, situation)
            results.append(result)
            if result.passed:
                passed.append(plan)
        return passed, results

    def _check(self, plan: ResponseCandidatePlan, situation: ResponseSituation) -> GateResult:
        failed: list[str] = []
        notes: dict[str, str] = {}

        # Gate 1: required goals satisfied
        required = plan.required_components
        satisfied = plan.satisfied_components
        missing = required - satisfied
        if missing:
            failed.append("required_goals_not_satisfied")
            notes["missing"] = ", ".join(sorted(missing))

        # Gate 2: safety constraints satisfied
        if self._has_safety_move(plan):
            if not any(m.safety_required for m in plan.moves):
                failed.append("safety_constraint_dropped")

        # Gate 3: evidence available when required
        evidence_policy = ""
        if situation.obligation_frame is not None:
            evidence_policy = getattr(situation.obligation_frame, "evidence_policy", "") or ""
        if evidence_policy == "required" and self._has_answer_move(plan):
            if not plan.evidence_refs:
                failed.append("evidence_required_but_missing")

        # Gate 4: write claim truthful
        if self._has_write_claim(plan):
            write = situation.write_outcome
            if write is not None and not write.committed:
                failed.append("write_claim_without_commit")

        # Gate 5: no internal surface leakage
        # (checked at surface level by selector, but we can check plan-level tags)
        for move in plan.moves:
            if "internal" in move.tags:
                failed.append("internal_surface_leakage")
                break

        # Gate 6: nonempty moves
        if not plan.moves:
            failed.append("no_moves")

        return GateResult(
            plan_id=plan.plan_id,
            passed=len(failed) == 0,
            failed_checks=failed,
            notes=notes,
        )

    @staticmethod
    def _has_safety_move(plan: ResponseCandidatePlan) -> bool:
        return any(m.safety_required for m in plan.moves)

    @staticmethod
    def _has_answer_move(plan: ResponseCandidatePlan) -> bool:
        return any(m.move_type == "answer" for m in plan.moves)

    @staticmethod
    def _has_write_claim(plan: ResponseCandidatePlan) -> bool:
        return any(m.move_type == "confirm_memory_write" for m in plan.moves)
