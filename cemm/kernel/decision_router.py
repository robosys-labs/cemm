from __future__ import annotations

from ..types.context_kernel import ContextKernel
from ..types.packets import (
    ActionPlan,
    DecisionPacket,
    GroundedGraph,
    InferencePacket,
    MemoryPacket,
)
from ..types.context_inference import ContextInference
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..types.semantic_event_graph import SemanticEventGraph
from ..types.signal import ObservationSemantics
from .answer_graph_ranker import best_candidate


class DecisionRouter:
    def __init__(self) -> None:
        pass

    def run(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        grounded_graph: GroundedGraph | None = None,
        memory_packet: MemoryPacket | None = None,
        inference_packet: InferencePacket | None = None,
        answer_candidates: list[SemanticAnswerGraph] | None = None,
        input_text: str = "",
        observation_semantics: ObservationSemantics | None = None,
        context_inference: ContextInference | None = None,
    ) -> DecisionPacket:
        selected_claim_ids = memory_packet.selected_claim_ids if memory_packet else []
        selected_model_ids = memory_packet.selected_model_ids if memory_packet else []
        predictions = inference_packet.predictions if inference_packet else []
        missing_slots = (grounded_graph.missing_slots if grounded_graph else
                         kernel.goal.missing_slots if kernel.goal else [])
        required_slots = list(kernel.goal.required_slots) if kernel.goal else []

        # If answer candidates are provided, rank them and use the best one
        if answer_candidates:
            best = best_candidate(answer_candidates, kernel, graph, memory_packet)
            if best is not None:
                selected_claim_ids = best.selected_claim_ids
                selected_model_ids = best.selected_model_ids
                if best.intent == "answer":
                    pass  # fall through to existing logic with improved claims
                elif best.intent == "ask":
                    return DecisionPacket(
                        action_kind="ask",
                        action_plan=ActionPlan(
                            action_kind="ask",
                            execution_allowed=True,
                            confidence=best.confidence,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=best.confidence,
                        reason=f"answer candidate intent=ask (score={best.confidence:.2f})",
                    )
                elif best.intent == "abstain":
                    return DecisionPacket(
                        action_kind="abstain",
                        action_plan=ActionPlan(
                            action_kind="abstain",
                            selected_model_ids=selected_model_ids,
                            execution_allowed=False,
                            confidence=best.confidence,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=best.confidence,
                        reason=f"best answer candidate intent=abstain (score={best.confidence:.2f})",
                    )

        # Command intent detection: explicit user commands take priority
        cmd_intent = self._detect_command_intent(
            input_text, graph, kernel, selected_claim_ids,
            predictions=predictions, missing_slots=missing_slots,
        )
        if cmd_intent:
            return cmd_intent

        if missing_slots:
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    required_slots=required_slots,
                    missing_slots=missing_slots,
                    execution_allowed=True,
                    confidence=0.9,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.9,
                reason="missing required slots",
            )

        # Claim candidates from SEG: route to remember to store new knowledge
        if graph.claim_candidates and not selected_claim_ids:
            return DecisionPacket(
                action_kind="remember",
                action_plan=ActionPlan(
                    action_kind="remember",
                    execution_allowed=True,
                    confidence=0.7,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.7,
                reason="SEG contains claim candidates for storage",
            )

        # Self-query: answer from selected self claims when available
        self_query_frames = {"self_identity_query", "self_capability_query", "self_knowledge_query"}
        if any(proc.get("frame_key") in self_query_frames for proc in graph.processes) and selected_claim_ids:
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    selected_claim_ids=selected_claim_ids,
                    selected_model_ids=selected_model_ids,
                    execution_allowed=True,
                    confidence=min(0.9, graph.confidence),
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=min(0.9, graph.confidence),
                reason="self query answered from selected self claims",
            )

        # If user is asking for clarification and there are no claim candidates,
        # route to ask even if claims were retrieved (e.g. "how do you mean?"
        # retrieves self_main claims via "you" pronoun but is a question, not a query)
        if not graph.claim_candidates:
            for proc in graph.processes:
                if proc.get("frame_key") in ("request_clarification", "ask_question", "unknown_intent"):
                    return DecisionPacket(
                        action_kind="ask",
                        action_plan=ActionPlan(
                            action_kind="ask",
                            execution_allowed=True,
                            confidence=0.7,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=0.7,
                        reason="graph indicates clarification needed",
                    )

        if selected_claim_ids:
            base_confidence = 0.8
            graph_confidence = getattr(graph, 'confidence', 0.5)
            confidence = min(0.95, base_confidence * (0.5 + 0.5 * graph_confidence))

            if predictions:
                avg_pred = sum(p.get("confidence", 0) for p in predictions) / max(len(predictions), 1)
                if avg_pred > 0.5:
                    confidence = min(0.95, confidence * 1.15)
                else:
                    confidence = max(0.4, confidence * 0.85)

            if graph.temporal_edges:
                confidence = min(0.95, confidence * 1.1)

            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    selected_claim_ids=selected_claim_ids,
                    selected_model_ids=selected_model_ids,
                    execution_allowed=True,
                    confidence=confidence,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=confidence,
                reason="selected evidence available with graph confidence {:.2f}".format(graph_confidence),
            )

        for proc in graph.processes:
            if proc.get("frame_key") in ("request_clarification", "ask_question", "unknown_intent"):
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=0.7,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason="graph indicates clarification needed",
                )

        if observation_semantics and observation_semantics.confidence >= 0.5:
            speech_act = observation_semantics.speech_act
            if speech_act == "greeting":
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.7,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason=f"speech_act greeting fallback (conf={observation_semantics.confidence:.2f})",
                )
            if speech_act == "acknowledgment":
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.65,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.65,
                    reason=f"speech_act acknowledgment fallback (conf={observation_semantics.confidence:.2f})",
                )
            if speech_act == "clarification":
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=0.65,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.65,
                    reason=f"speech_act clarification fallback (conf={observation_semantics.confidence:.2f})",
                )
            if speech_act == "exit":
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=0.9,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.9,
                    reason=f"speech_act exit fallback (conf={observation_semantics.confidence:.2f})",
                )

        if context_inference and context_inference.confidence >= 0.5:
            if context_inference.frame_id in ("greeting", "session_opening", "acknowledgment"):
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=context_inference.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=context_inference.confidence,
                    reason=f"context frame {context_inference.frame_id} fallback",
                )
            if context_inference.frame_id == "clarification":
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=context_inference.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=context_inference.confidence,
                    reason="context frame clarification fallback",
                )
            if context_inference.frame_id == "session_exit":
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=context_inference.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=context_inference.confidence,
                    reason="context frame session_exit fallback",
                )

        # Short input fallback: only when the graph has no meaningful signal.
        if input_text and len(input_text.strip()) <= 3 and graph.confidence < 0.3:
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    execution_allowed=True,
                    confidence=0.7,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.7,
                reason="short input with low graph confidence — clarification needed",
            )

        return DecisionPacket(
            action_kind="abstain",
            action_plan=ActionPlan(
                action_kind="abstain",
                selected_model_ids=selected_model_ids,
                execution_allowed=False,
                confidence=max(0.4, min(0.6, graph.confidence)),
                risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
            ),
            confidence=max(0.4, min(0.6, graph.confidence)),
            reason="insufficient graph-grounded evidence (confidence={:.2f})".format(graph.confidence),
        )

    def _detect_command_intent(
        self,
        input_text: str,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        selected_claim_ids: list[str] | None = None,
        predictions: list[dict[str, Any]] | None = None,
        missing_slots: list[str] | None = None,
    ) -> DecisionPacket | None:
        frame_keys = {p.get("frame_key", "") for p in graph.processes}
        has_claims = bool(selected_claim_ids)

        if "session_exit" in frame_keys:
            return DecisionPacket(
                action_kind="abstain",
                action_plan=ActionPlan(
                    action_kind="abstain",
                    execution_allowed=False,
                    confidence=0.95,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.95,
                reason="session exit detected in SEG processes",
            )

        # Explicit commands take priority over conversational intents
        if "command_remember" in frame_keys:
            return DecisionPacket(
                action_kind="remember",
                action_plan=ActionPlan(
                    action_kind="remember",
                    execution_allowed=True,
                    confidence=0.85,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.85,
                reason="remember command detected in SEG processes",
            )

        if "command_reflect" in frame_keys:
            return DecisionPacket(
                action_kind="reflect",
                action_plan=ActionPlan(
                    action_kind="reflect",
                    execution_allowed=True,
                    confidence=0.8,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.8,
                reason="reflect command detected in SEG processes",
            )

        if "command_retrieve" in frame_keys:
            return DecisionPacket(
                action_kind="retrieve",
                action_plan=ActionPlan(
                    action_kind="retrieve",
                    execution_allowed=True,
                    confidence=0.8,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.8,
                reason="retrieve command detected in SEG processes",
            )

        # Conversational intents after commands — only when no claims selected
        if not has_claims and "greeting" in frame_keys:
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    execution_allowed=True,
                    confidence=0.75,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.75,
                reason="greeting detected in SEG processes",
            )

        if not has_claims and "acknowledgment" in frame_keys:
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    execution_allowed=True,
                    confidence=0.7,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.7,
                reason="acknowledgment detected in SEG processes",
            )

        if not has_claims and "discourse_marker" in frame_keys:
            # Discourse markers like "oh", "well" often precede real content
            # If no other intent detected, treat as conversational
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    execution_allowed=True,
                    confidence=0.6,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.6,
                reason="discourse marker — clarification needed",
            )

        return None

    def _estimate_risk(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        confidence: float | None = None,
        missing_slots: list[str] | None = None,
        predictions: list[dict[str, Any]] | None = None,
    ) -> float:
        if confidence is None:
            confidence = graph.confidence
        risk = (1.0 - confidence) * 0.5
        if missing_slots:
            risk += min(0.3, len(missing_slots) * 0.1)
        if predictions:
            risk += min(0.3, len(predictions) * 0.1)
        uncertainty = getattr(kernel.self_view, "uncertainty", 0.0)
        if uncertainty > 0.5:
            risk += (uncertainty - 0.5) * 0.2
        return min(1.0, max(0.0, risk))
