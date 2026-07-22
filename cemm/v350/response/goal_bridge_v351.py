"""Phase-12 deterministic conversational-obligation bridge.

This is intentionally not the Phase-16 utility/impact GoalArbitrator.  It supplies the
small set of discourse obligations needed by the conversational alpha while preserving
Stage-15 ownership and producing semantic response families only, never wording.
"""
from __future__ import annotations

from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref
from .csir_v351 import (
    ConversationalGoalCandidate, ConversationalGoalDecision, ResponseCorrectionIntent,
    ResponseFamily, ResponseReportIntent,
)


class ConversationalGoalBridgeV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "conversational_goal_bridge"

    def arbitrate(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, store, effect_store, semantic_capabilities
        requested = bool(getattr(cycle.input_payload, "response_requested", True))
        query_results = tuple(cycle.artifacts.get("query_results", ()) or ())
        discourse = cycle.artifacts.get("discourse_structures")
        claims = tuple(cycle.artifacts.get("claims", ()) or ())
        learning_questions = tuple(cycle.artifacts.get("learning_question_candidates", ()) or ())
        report_intents = tuple(cycle.artifacts.get("response_report_intents", ()) or ())
        correction_intents = tuple(cycle.artifacts.get("response_correction_intents", ()) or ())
        if any(not isinstance(item, ResponseReportIntent) for item in report_intents):
            raise TypeError("response_report_intents must be typed ResponseReportIntent values")
        if any(not isinstance(item, ResponseCorrectionIntent) for item in correction_intents):
            raise TypeError("response_correction_intents must be typed ResponseCorrectionIntent values")
        discourse_frontiers = tuple(getattr(discourse, "frontier_refs", ()) or ()) if discourse is not None else ()

        candidates: list[ConversationalGoalCandidate] = []

        if not requested:
            candidates.append(ConversationalGoalCandidate(
                goal_ref=artifact_ref("goal:no-response", cycle.cycle_ref),
                family=ResponseFamily.NO_RESPONSE_REQUIRED,
                target_refs=(cycle.cycle_ref,), source_refs=(cycle.cycle_ref,),
                reason_refs=("response_not_requested",), priority=1000,
            ))
        else:
            for intent in correction_intents:
                candidates.append(ConversationalGoalCandidate(
                    goal_ref=artifact_ref("goal:correct-prior-output", intent.intent_ref),
                    family=ResponseFamily.CORRECT_PRIOR_OUTPUT,
                    target_refs=(intent.target_output_ref,), source_refs=(intent.replacement_semantic_ref,),
                    reason_refs=("authorized_response_correction_intent",), priority=int(intent.priority),
                ))
            for intent in report_intents:
                candidates.append(ConversationalGoalCandidate(
                    goal_ref=artifact_ref("goal:report-semantic-source", intent.intent_ref),
                    family=intent.family, target_refs=tuple(intent.target_refs),
                    source_refs=(intent.semantic_ref,), reason_refs=("semantic_report_intent",),
                    priority=int(intent.priority),
                ))

            for result in query_results:
                if getattr(result, "answered", False):
                    candidates.append(ConversationalGoalCandidate(
                        goal_ref=artifact_ref("goal:answer-query", result.result_ref),
                        family=ResponseFamily.ANSWER_QUERY,
                        target_refs=(result.query_ref,), source_refs=(result.result_ref,),
                        reason_refs=("grounded_query_binding_available",), priority=900,
                    ))
                else:
                    unresolved_refs = tuple((*result.frontier_refs, *discourse_frontiers))
                    needs_clarification = any(
                        token in ref for ref in unresolved_refs
                        for token in ("ambigu", "reference", "grounding", "partial", "unresolved")
                    )
                    candidates.append(ConversationalGoalCandidate(
                        goal_ref=artifact_ref("goal:unresolved-query", result.result_ref),
                        family=(
                            ResponseFamily.REQUEST_CLARIFICATION
                            if needs_clarification else ResponseFamily.QUALIFY_UNCERTAINTY
                        ),
                        target_refs=(result.query_ref,), source_refs=(result.result_ref,),
                        reason_refs=((
                            "query_requires_clarification"
                            if needs_clarification else "grounded_query_has_no_supported_answer"
                        ),),
                        priority=850, blocked_by_frontier_refs=unresolved_refs,
                    ))

            if discourse is not None:
                for clarification in tuple(getattr(discourse, "clarification_targets", ()) or ()):
                    candidates.append(ConversationalGoalCandidate(
                        goal_ref=artifact_ref("goal:clarification", clarification.clarification_ref),
                        family=ResponseFamily.REQUEST_CLARIFICATION,
                        target_refs=(clarification.target_ref,),
                        source_refs=(clarification.clarification_ref,),
                        reason_refs=(clarification.reason_ref,), priority=820,
                    ))

            if not query_results and claims:
                # Acknowledgement is a semantic discourse action, not generic success text.
                # It is lower priority than any query/clarification obligation and targets
                # the exact claim occurrence that triggered it.
                latest = claims[-1]
                candidates.append(ConversationalGoalCandidate(
                    goal_ref=artifact_ref("goal:acknowledge-claim", latest.claim_ref),
                    family=ResponseFamily.ACKNOWLEDGE_TARGETED_CLAIM,
                    target_refs=(latest.claim_ref,), source_refs=(latest.claim_ref,),
                    reason_refs=("targeted_claim_received",), priority=400,
                ))

            for question in learning_questions:
                ref = str(getattr(question, "question_ref", "") or getattr(question, "frontier_ref", ""))
                if ref:
                    candidates.append(ConversationalGoalCandidate(
                        goal_ref=artifact_ref("goal:learning-question", ref),
                        family=ResponseFamily.ASK_LEARNING_QUESTION,
                        target_refs=(ref,), source_refs=(ref,),
                        reason_refs=("learning_question_candidate",), priority=300,
                    ))

            if not candidates:
                candidates.append(ConversationalGoalCandidate(
                    goal_ref=artifact_ref("goal:no-response-needed", cycle.cycle_ref),
                    family=ResponseFamily.NO_RESPONSE_REQUIRED,
                    target_refs=(cycle.cycle_ref,), source_refs=(cycle.cycle_ref,),
                    reason_refs=("no_semantic_response_obligation",), priority=0,
                ))

        ordered = tuple(sorted(candidates, key=lambda item: (-item.priority, item.goal_ref)))
        selected = (ordered[0],) if ordered else ()
        decision = ConversationalGoalDecision(
            decision_ref=artifact_ref(
                "conversational-goal-decision", cycle.cycle_ref,
                tuple(item.goal_ref for item in selected),
            ),
            candidates=ordered,
            selected_goal_refs=tuple(item.goal_ref for item in selected),
            selected_families=tuple(item.family for item in selected),
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            reason_refs=tuple(reason for item in selected for reason in item.reason_refs),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={"goal_candidates": ordered, "goal_decision": decision},
        )


__all__ = ["ConversationalGoalBridgeV351"]
