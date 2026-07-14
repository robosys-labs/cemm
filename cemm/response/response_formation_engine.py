"""DEPRECATED: Replaced by cemm.kernel.response.planner.ResponsePlanner + cemm.kernel.response.renderer.MessageRenderer.

This module is retained for legacy compatibility only. The v3.4 canonical
response path uses ResponsePlanner for content selection and MessageRenderer
for surface realization. Do not use for new code — redirect to the v3.4
response pipeline.

Canonical budget-aware response formation engine."""

from __future__ import annotations

from cemm.actions import InternalActionAuthorizer, InternalActionProposer
from cemm.budget import BudgetController
from cemm.learning import ResponseBudgetLearningExtractor

from .primitive_goal_composer import PrimitiveGoalComposer
from .realization_executor import RealizationExecutor
from .response_move_composer import ResponseMoveComposer
from .transformers import CandidateGenerator, PlanGateAndRanker, Selector
from .types import RealizedCandidate, ResponseBundle, ResponseEvidencePacket, ResponseSituation


class ResponseFormationEngine:
    """Single canonical response formation path.

    Phase 8 adds internal action proposal and authorization. The engine still
    does not execute side effects; it returns authorized/rejected proposals for
    the runtime authority layer.
    """

    def __init__(self) -> None:
        self._budget_controller = BudgetController()
        self._goal_composer = PrimitiveGoalComposer()
        self._move_composer = ResponseMoveComposer()
        self._candidate_generator = CandidateGenerator()
        self._ranker = PlanGateAndRanker()
        self._selector = Selector()
        self._realizer = RealizationExecutor()
        self._action_proposer = InternalActionProposer()
        self._action_authorizer = InternalActionAuthorizer()
        self._learning_extractor = ResponseBudgetLearningExtractor()

    def form(self, situation: ResponseSituation) -> ResponseBundle:
        self._ensure_evidence(situation)
        if situation.budget_decision is None:
            situation.budget_decision = self._budget_controller.decide(situation)

        goals = self._goal_composer.compose(situation)
        moves = self._move_composer.compose(goals, situation)
        plans = self._candidate_generator.generate(moves, situation)
        ranked = self._ranker.rank(plans, situation)
        selected_plan = self._selector.select(ranked, situation)

        required_components = selected_plan.required_components
        satisfied_components = selected_plan.satisfied_components
        missing_components = sorted(required_components - satisfied_components)
        is_blocked = bool(
            selected_plan.blocked_reason
            or (missing_components and any(move.safety_required for move in selected_plan.moves))
        )

        if is_blocked:
            text = self._blocked_fallback(selected_plan.blocked_reason or ",".join(missing_components))
            proposed_actions: list = []
            authorization = self._action_authorizer.authorize([], situation, selected_plan)
            realized = self._dummy_realized()
        else:
            realized = self._realizer.realize_plan(selected_plan, situation)
            proposed_actions = self._action_proposer.propose(situation, selected_plan, realized)
            authorization = self._action_authorizer.authorize(proposed_actions, situation, selected_plan)
            text = realized.text
        if not text:
            text = "I don't have enough verified information to answer that."

        obligation_kind = getattr(situation.obligation_frame, "obligation_kind", "") if situation.obligation_frame is not None else ""
        evidence_refs = _dedupe([
            *getattr(situation.evidence, "evidence_refs", []),
            *selected_plan.evidence_refs,
            *[ref for move in selected_plan.moves for ref in move.evidence_refs],
        ])
        rejected = [plan for plan in ranked if plan.plan_id != selected_plan.plan_id]

        bundle = ResponseBundle(
            text=text,
            language=realized.language,
            moves=selected_plan.moves,
            internal_actions=authorization.authorized_actions,
            proposed_internal_actions=authorization.proposed_actions,
            rejected_internal_actions=authorization.rejected_actions,
            evidence_refs=evidence_refs,
            safety_tags=selected_plan.safety_tags,
            style=selected_plan.style,
            selected_plan_id=selected_plan.plan_id,
            rejected_plans=rejected,
            write_outcome=situation.write_outcome,
            obligation_kind=obligation_kind,
            confidence=max((move.confidence for move in selected_plan.moves), default=0.3),
            diagnostics={
                "phase": "budget_aware_v3_1_phase8",
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
                    for move in selected_plan.moves
                ],
                "candidate_count": len(plans),
                "ranked_count": len(ranked),
                "selected_plan": {
                    "plan_id": selected_plan.plan_id,
                    "framing_variant": selected_plan.framing_variant,
                    "score": selected_plan.total_score,
                    "score_parts": selected_plan.score_parts,
                    "blocked_reason": selected_plan.blocked_reason,
                    "estimated_cost_ms": selected_plan.estimated_cost_ms,
                    "rank": selected_plan.rank,
                },
                "rejected_plans": [
                    {
                        "plan_id": plan.plan_id,
                        "framing_variant": plan.framing_variant,
                        "score": plan.total_score,
                        "blocked_reason": plan.blocked_reason,
                        "rank": plan.rank,
                    }
                    for plan in rejected
                ],
                "missing_components": missing_components,
                "grammar": realized.grammar_trace,
                "budget": self._budget_diagnostics(situation),
                "actions": authorization.diagnostics(),
            },
            budget_decision=situation.budget_decision,
            deliberation_plan=situation.deliberation_plan,
            distillation_result=situation.distillation_result,
            action_authorization=authorization,
        )
        learning = self._learning_extractor.extract(situation=situation, bundle=bundle)
        bundle.learning_result = learning
        bundle.learning_patch_candidates = learning.patch_candidates
        bundle.diagnostics["learning"] = learning.diagnostics
        return bundle

    @staticmethod
    def _ensure_evidence(situation: ResponseSituation) -> None:
        if situation.evidence is None:
            situation.evidence = ResponseEvidencePacket.from_runtime(
                semantic_query=situation.semantic_query,
                answer_binding=situation.answer_binding,
                relation_frames=situation.relation_frames,
            )
        elif situation.answer_binding is None:
            situation.answer_binding = situation.evidence.answer_binding

    @staticmethod
    def _blocked_fallback(reason: str) -> str:
        if "safety" in reason or "explicit_negative" in reason or "no_instruction" in reason:
            return "No. I can't help with that request."
        return "I don't have enough verified information to answer that."

    @staticmethod
    def _dummy_realized() -> RealizedCandidate:
        return RealizedCandidate(
            text="",
            language="en",
            grammar_trace={"blocked": True},
        )

    @staticmethod
    def _budget_diagnostics(situation: ResponseSituation) -> dict:
        decision = situation.budget_decision
        if decision is None:
            return {}
        stage = decision.stage_budget
        return {
            "pressure": decision.pressure,
            "task_size": decision.task_size,
            "risk_level": decision.risk_level,
            "reasons": list(decision.reasons),
            "stage": {
                "candidate_plan_limit": stage.candidate_plan_limit,
                "realized_candidate_limit": stage.realized_candidate_limit,
                "selector_mode": stage.selector_mode,
                "detail_level": stage.detail_level,
                "query_result_limit": stage.query_result_limit,
                "attention_focus_limit": stage.attention_focus_limit,
            },
            **stage.diagnostics,
        }


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
