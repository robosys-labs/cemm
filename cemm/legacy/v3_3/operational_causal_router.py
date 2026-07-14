"""DEPRECATED: Replaced by cemm.kernel.execution.reconciliation.OutcomeReconciler.

This module is retained for legacy compatibility only. The v3.4 canonical
execution path uses OutcomeReconciler for effect reconciliation.
Do not use for new code — redirect to OutcomeReconciler.

Route operational meanings and state transmutations into effects."""

from __future__ import annotations

import uuid
from typing import Any

from ...types.meaning_percept import SafetyFrame
from ...types.operational_meaning import OperationalEffect, OperationalMeaningFrame
from ...types.state_transmutation import StateTransmutationFrame


class OperationalCausalRouter:
    """Produce explicit effects for query/write/reaction/safety decisions."""

    def route(
        self,
        frames: list[OperationalMeaningFrame],
        transmutations: list[StateTransmutationFrame],
        affordance_predictions: list[Any] | None = None,
        causal_predictions: list[Any] | None = None,
        safety_frame: SafetyFrame | None = None,
    ) -> list[OperationalEffect]:
        effects: list[OperationalEffect] = []
        for frame in frames:
            effects.extend(self._effects_for_frame(frame, transmutations, safety_frame))
        for prediction in affordance_predictions or []:
            effect = self._effect_for_prediction(prediction)
            if effect is not None:
                effects.append(effect)
        for effect in effects:
            source = next((f for f in frames if f.frame_id == effect.source_frame_id), None)
            if source is not None:
                source.effects.append(effect)
        return effects

    def _effects_for_frame(
        self,
        frame: OperationalMeaningFrame,
        transmutations: list[StateTransmutationFrame],
        safety_frame: SafetyFrame | None = None,
    ) -> list[OperationalEffect]:
        frame_transmutations = [
            t for t in transmutations
            if t.source_frame_id == frame.frame_id
        ]
        effects: list[OperationalEffect] = []

        if frame.is_query:
            effects.append(self._effect(frame, "activate_query", frame.target_scope, {
                "query_policy": frame.query_policy,
                "dimension": frame.dimension,
            }))

        if frame.is_writable:
            effects.append(self._effect(frame, "activate_write", frame.target_scope, {
                "persistence_policy": frame.persistence_policy,
                "transmutation_ids": [t.transmutation_id for t in frame_transmutations],
            }))

        if frame.frame_type in ("style_feedback", "response_feedback"):
            dimension = frame.dimension or frame.features.get("dimension", "response_detail")
            effect_type = "decrease_response_detail" if dimension in {"verbosity", "response_detail", "detail"} else "increase_repair_debt"
            effects.append(self._effect(frame, effect_type, "conversation:style", {
                "dimension": dimension,
            }, strength=0.15))

        if frame.frame_type == "session_exit":
            effects.append(self._effect(frame, "set_exit_requested", "conversation:session", {
                "status": "closing",
            }, strength=1.0))

        if frame.frame_type == "safety_candidate" and safety_frame is not None:
            effects.append(self._effect(
                frame, "activate_safety_refusal", "conversation:safety", {
                    "category": safety_frame.category,
                    "severity": safety_frame.severity,
                    "response_mode": safety_frame.allowed_response_mode,
                    "must_not_do": safety_frame.must_not_do,
                    "harmful_outcomes": [o.changed_dimension for o in safety_frame.harmful_outcomes],
                    "requested_action": safety_frame.requested_action,
                },
                strength=1.0, reversible=False,
            ))
        elif frame.frame_type == "safety_candidate":
            effects.append(self._effect(frame, "activate_safety_refusal", "conversation:safety", {
                "risk": "candidate",
            }, strength=1.0, reversible=False))

        return effects

    def _effect_for_prediction(self, prediction: Any) -> OperationalEffect | None:
        effect_type = getattr(prediction, "effect_type", "")
        if effect_type != "evaluation_shift":
            return None
        return OperationalEffect(
            effect_id=f"oe_{uuid.uuid4().hex[:12]}",
            source_frame_id=getattr(prediction, "source_frame_id", ""),
            effect_type="increase_repair_debt",
            target="conversation:style",
            delta={"prediction": getattr(prediction, "affordance_key", "")},
            strength=float(getattr(prediction, "confidence", 0.5) or 0.5),
            reversible=True,
        )

    @staticmethod
    def _effect(
        frame: OperationalMeaningFrame,
        effect_type: str,
        target: str,
        delta: dict[str, Any],
        *,
        strength: float = 0.8,
        reversible: bool = True,
    ) -> OperationalEffect:
        return OperationalEffect(
            effect_id=f"oe_{uuid.uuid4().hex[:12]}",
            source_frame_id=frame.frame_id,
            effect_type=effect_type,
            target=target,
            delta=delta,
            strength=strength,
            reversible=reversible,
            evidence_refs=list(frame.evidence_refs),
        )
