from __future__ import annotations

from ..store.artifact_store import ArtifactStore
from ..types.context_kernel import ContextKernel
from ..types.packets import (
    ActionPlan,
    DecisionPacket,
    GroundedGraph,
    InferencePacket,
    MemoryPacket,
)
from ..types.semantic_event_graph import SemanticEventGraph


class DecisionRouter:
    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self._artifact_store = artifact_store

    def run(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        grounded_graph: GroundedGraph | None = None,
        memory_packet: MemoryPacket | None = None,
        inference_packet: InferencePacket | None = None,
    ) -> DecisionPacket:
        selected_claim_ids = memory_packet.selected_claim_ids if memory_packet else []
        selected_model_ids = memory_packet.selected_model_ids if memory_packet else []
        predictions = inference_packet.predictions if inference_packet else []
        missing_slots = (grounded_graph.missing_slots if grounded_graph else
                         kernel.goal.missing_slots if kernel.goal else [])
        required_slots = list(kernel.goal.required_slots) if kernel.goal else []

        if self._artifact_store:
            artifact = self._artifact_store.get_active_artifact("operator")
            if artifact:
                match_text = f"claims={len(selected_claim_ids)},slots={len(missing_slots)}"
                best = self._artifact_store.find_example(artifact, match_text)
                if best and best.get("confidence", 0) >= 0.7:
                    output = best.get("output", {})
                    action_str = output.get("action_kind", "")
                    if action_str == "answer":
                        return DecisionPacket(
                            action_kind="answer",
                            action_plan=ActionPlan(
                                action_kind="answer",
                                selected_claim_ids=selected_claim_ids,
                                selected_model_ids=selected_model_ids,
                                execution_allowed=True,
                                confidence=output.get("confidence", 0.8),
                                risk=0.0,
                            ),
                            confidence=output.get("confidence", 0.8),
                            reason=output.get("reason", "artifact-based decision"),
                        )
                    elif action_str == "ask":
                        return DecisionPacket(
                            action_kind="ask",
                            action_plan=ActionPlan(
                                action_kind="ask",
                                required_slots=output.get("required_slots", []),
                                missing_slots=output.get("missing_slots", []),
                                execution_allowed=True,
                                confidence=output.get("confidence", 0.8),
                                risk=0.0,
                            ),
                            confidence=output.get("confidence", 0.8),
                            reason=output.get("reason", "artifact-based decision"),
                        )
                    elif action_str == "abstain":
                        return DecisionPacket(
                            action_kind="abstain",
                            action_plan=ActionPlan(
                                action_kind="abstain",
                                selected_model_ids=selected_model_ids,
                                execution_allowed=False,
                                confidence=output.get("confidence", 0.6),
                                risk=0.0,
                            ),
                            confidence=output.get("confidence", 0.6),
                            reason=output.get("reason", "artifact-based abstain"),
                        )
        if missing_slots:
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    required_slots=required_slots,
                    missing_slots=missing_slots,
                    execution_allowed=True,
                    confidence=0.9,
                    risk=0.0,
                ),
                confidence=0.9,
                reason="missing required slots",
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
                    risk=0.0,
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
                        risk=0.0,
                    ),
                    confidence=0.7,
                    reason="graph indicates clarification needed",
                )

        return DecisionPacket(
            action_kind="abstain",
            action_plan=ActionPlan(
                action_kind="abstain",
                selected_model_ids=selected_model_ids,
                execution_allowed=False,
                confidence=max(0.4, min(0.6, graph.confidence)),
                risk=0.0,
            ),
            confidence=max(0.4, min(0.6, graph.confidence)),
            reason="insufficient graph-grounded evidence (confidence={:.2f})".format(graph.confidence),
        )
