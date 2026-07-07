"""Canonical response formation engine.

Phase 1-3 implementation:
    ResponseSituation
    -> PrimitiveGoalComposer
    -> ResponseMoveComposer
    -> RealizationExecutor
    -> ResponseBundle

Candidate expansion/ranking can be added later without changing the semantic
contract: goals and moves stay language-agnostic; realization stays
language-specific.
"""

from __future__ import annotations

from .primitive_goal_composer import PrimitiveGoalComposer
from .realization_executor import RealizationExecutor
from .response_move_composer import ResponseMoveComposer
from .types import ResponseBundle, ResponseEvidencePacket, ResponseSituation


class ResponseFormationEngine:
    def __init__(self) -> None:
        self._goal_composer = PrimitiveGoalComposer()
        self._move_composer = ResponseMoveComposer()
        self._realizer = RealizationExecutor()

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
        realized = self._realizer.realize_candidate(moves, situation)

        evidence_refs = _dedupe([
            *getattr(situation.evidence, "evidence_refs", []),
            *[ref for move in moves for ref in move.evidence_refs],
        ])
        safety_tags = realized.plan.safety_tags
        required_components = set().union(*(move.required_components for move in moves)) if moves else set()
        satisfied_components = set().union(*(move.satisfied_components for move in moves)) if moves else set()
        missing_components = sorted(required_components - satisfied_components)

        text = realized.text
        if missing_components and any(move.safety_required for move in moves):
            text = "No. I can't help with that request."
        if not text:
            text = "I don't have enough verified information to answer that."

        obligation_kind = ""
        if situation.obligation_frame is not None:
            obligation_kind = getattr(situation.obligation_frame, "obligation_kind", "") or ""

        return ResponseBundle(
            text=text,
            language=realized.language,
            moves=moves,
            evidence_refs=evidence_refs,
            safety_tags=safety_tags,
            style=situation.style,
            selected_plan_id=realized.plan.plan_id,
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
                "grammar_trace": realized.grammar_trace,
                "phase": "deterministic_v3_1",
            },
        )


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
