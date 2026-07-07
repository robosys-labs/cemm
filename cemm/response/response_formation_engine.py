"""ResponseFormationEngine — the canonical response formation path.

Replaces SemanticRealizer in SemanticKernelRuntime.

Pipeline:
    ResponseSituation
    -> PrimitiveGoalComposer
    -> ResponseMoveComposer
    -> RealizationExecutor
    -> ResponseBundle

Phase 1-3: deterministic, no candidate variation.
Phase 4 will add CandidateGenerator + PlanGateAndRanker + Selector.
"""

from __future__ import annotations

from typing import Any

from .primitive_goal_composer import PrimitiveGoalComposer
from .response_move_composer import ResponseMoveComposer
from .realization_executor import RealizationExecutor
from .types import (
    InternalActionProposal,
    ResponseBundle,
    ResponseCandidatePlan,
    ResponseMove,
    ResponseSituation,
)


class ResponseFormationEngine:
    """The single canonical response formation path.

    Phase 1-3: deterministic path (no candidate variation).
    """

    def __init__(self) -> None:
        self._goal_composer = PrimitiveGoalComposer()
        self._move_composer = ResponseMoveComposer()
        self._realizer = RealizationExecutor()

    def form(self, situation: ResponseSituation) -> ResponseBundle:
        # 1. Compose primitive goals from situation
        goals = self._goal_composer.compose(situation)

        # 2. Compose response moves from goals
        moves = self._move_composer.compose(goals, situation)

        # 3. Realize surface text from moves + slots
        text = self._realizer.realize(moves, situation)

        # 4. Build the bundle
        obligation_kind = ""
        if situation.obligation_frame is not None:
            obligation_kind = situation.obligation_frame.obligation_kind

        # Collect evidence refs from moves
        evidence_refs: list[str] = []
        for move in moves:
            evidence_refs.extend(move.evidence_refs)

        # Collect safety tags
        safety_tags: list[str] = []
        if situation.safety_frame is not None:
            safety_tags.append(situation.safety_frame.category)

        # Build a single plan (Phase 4 will have multiple)
        plan = ResponseCandidatePlan(
            plan_id="deterministic",
            moves=moves,
            framing_variant="direct",
            evidence_refs=evidence_refs,
            safety_tags=safety_tags,
            total_score=1.0,
        )

        return ResponseBundle(
            text=text,
            moves=moves,
            evidence_refs=evidence_refs,
            safety_tags=safety_tags,
            style=situation.style,
            selected_plan_id=plan.plan_id,
            write_outcome=situation.write_outcome,
            obligation_kind=obligation_kind,
            confidence=max((m.confidence for m in moves), default=0.3),
            diagnostics={
                "goals": [g.goal_type for g in goals],
                "moves": [m.move_type for m in moves],
                "phase": "deterministic",
            },
        )
