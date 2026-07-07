"""Canonical response formation engine.

Phase 1-4 implementation:
    ResponseSituation
    -> PrimitiveGoalComposer
    -> ResponseMoveComposer
    -> CandidateGenerator (framing variants)
    -> PlanGate (hard gates)
    -> PlanRanker (plan scoring)
    -> Selector (realize top K, surface score, select)
    -> ResponseBundle

Goals and moves stay language-agnostic; realization stays language-specific.
Rejected candidates remain diagnosable in the ResponseBundle.
"""

from __future__ import annotations

from .candidate_generator import CandidateGenerator
from .plan_gate import PlanGate
from .primitive_goal_composer import PrimitiveGoalComposer
from .ranker import PlanRanker
from .realization_executor import RealizationExecutor
from .response_move_composer import ResponseMoveComposer
from .selector import Selector
from .types import ResponseBundle, ResponseEvidencePacket, ResponseSituation


class ResponseFormationEngine:
    def __init__(self) -> None:
        self._goal_composer = PrimitiveGoalComposer()
        self._move_composer = ResponseMoveComposer()
        self._candidate_gen = CandidateGenerator()
        self._gate = PlanGate()
        self._ranker = PlanRanker()
        self._realizer = RealizationExecutor()
        self._selector = Selector(self._realizer)

    def form(self, situation: ResponseSituation) -> ResponseBundle:
        if situation.evidence is None:
            situation.evidence = ResponseEvidencePacket.from_runtime(
                semantic_query=situation.semantic_query,
                answer_binding=situation.answer_binding,
                relation_frames=situation.relation_frames,
            )
        elif situation.answer_binding is None:
            situation.answer_binding = situation.evidence.answer_binding

        goals = self._goal_composer.compose(situation)
        moves = self._move_composer.compose(goals, situation)

        # Phase 4: candidate generation -> gate -> rank -> select
        candidates = self._candidate_gen.generate(moves, goals, situation)
        gated, gate_results = self._gate.filter(candidates, situation)
        ranked = self._ranker.rank(gated, situation)

        max_realized = situation.budget_frame.max_realized_candidates
        selection = self._selector.select(ranked, situation, max_realized=max_realized)

        if selection.selected is None:
            realized = self._realizer.realize_candidate(moves, situation)
            selected_text = realized.text
            selected_plan = realized.plan
            selected_language = realized.language
            grammar_trace = realized.grammar_trace
            rejected_plans: list = []
        else:
            selected = selection.selected
            selected_text = selected.text
            selected_plan = selected.plan
            selected_language = selected.language
            grammar_trace = selected.grammar_trace
            rejected_plans = selection.rejected

        gate_diag = [{"plan_id": r.plan_id, "passed": r.passed,
                      "failed_checks": r.failed_checks} for r in gate_results]

        evidence_refs = _dedupe([
            *getattr(situation.evidence, "evidence_refs", []),
            *[ref for move in moves for ref in move.evidence_refs],
        ])
        safety_tags = selected_plan.safety_tags
        required_components = set().union(*(move.required_components for move in moves)) if moves else set()
        satisfied_components = set().union(*(move.satisfied_components for move in moves)) if moves else set()
        missing_components = sorted(required_components - satisfied_components)

        text = selected_text
        if missing_components and any(move.safety_required for move in moves):
            text = "No. I can't help with that request."
        if not text:
            text = "I don't have enough verified information to answer that."

        obligation_kind = ""
        if situation.obligation_frame is not None:
            obligation_kind = getattr(situation.obligation_frame, "obligation_kind", "") or ""

        return ResponseBundle(
            text=text,
            language=selected_language,
            moves=moves,
            evidence_refs=evidence_refs,
            safety_tags=safety_tags,
            style=situation.style,
            selected_plan_id=selected_plan.plan_id,
            rejected_plans=[c.plan for c in rejected_plans],
            write_outcome=situation.write_outcome,
            obligation_kind=obligation_kind,
            confidence=max((move.confidence for move in moves), default=0.3),
            diagnostics={
                "goals": [
                    {
                        "type": goal.goal_type,
                        "required": goal.required,
                        "reason": goal.reason,
                        "constraints": sorted(goal.constraints),
                    }
                    for goal in goals
                ],
                "moves": [
                    {
                        "type": move.move_type,
                        "required_components": sorted(move.required_components),
                        "satisfied_components": sorted(move.satisfied_components),
                        "tags": sorted(move.tags),
                    }
                    for move in moves
                ],
                "missing_components": missing_components,
                "grammar_trace": grammar_trace,
                "phase": "candidate_ranked_v3_1",
                "candidate_count": len(candidates),
                "gated_count": len(gated),
                "gate_results": gate_diag,
                "selected_framing": selected_plan.framing_variant,
                "rejected_framings": [c.plan.framing_variant for c in rejected_plans],
            },
        )


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
