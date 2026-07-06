"""CausalBridge — adapter bridging legacy CausalInference to the semantic runtime.

Converts CausalInference predictions into AffordancePrediction objects
that can be attached to the UOLGraph, enabling the semantic runtime to
consume causal predictions without modifying the legacy inference engine.
"""

from __future__ import annotations

from typing import Any

from ..types.uol_graph import AffordancePrediction


class CausalBridge:
    """Bridge between CausalInference and the semantic runtime.

    Wraps CausalInference.predict() and converts InferencePacket predictions
    into AffordancePrediction objects compatible with the UOLGraph pipeline.
    """

    def __init__(self, causal_inference: Any | None = None) -> None:
        self._causal = causal_inference

    def predict(
        self,
        graph: Any,
        kernel: Any,
        active_claim_ids: list[str] | None = None,
        action_or_event: str = "",
    ) -> list[AffordancePrediction]:
        """Run causal inference and convert to AffordancePredictions.

        Returns a list of AffordancePrediction objects that can be added
        to the graph's affordance_predictions list.
        """
        if self._causal is None:
            return []

        try:
            packet = self._causal.predict(
                action_or_event=action_or_event or "turn",
                active_claim_ids=active_claim_ids or [],
                kernel=kernel,
                graph=graph,
            )
        except Exception:
            return []

        predictions: list[AffordancePrediction] = []
        for i, pred in enumerate(packet.predictions):
            predictions.append(AffordancePrediction(
                id=f"causal_{i}",
                affordance_key=pred.get("predicate", "causal_effect"),
                trigger_atom_ids=[],
                predicted_patch_template={
                    "target": "episodic_trace",
                    "operation": "causal_prediction",
                    "predicate": pred.get("predicate", ""),
                    "model_id": pred.get("model_id", ""),
                },
                effect_type="causal_effect",
                confidence=pred.get("confidence", 0.5),
                evidence_refs=[],
                reason=f"causal_model:{pred.get('model_id', 'unknown')}",
            ))

        return predictions
