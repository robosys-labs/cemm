"""ReactionContractBuilder — build style/temperature/session reaction contracts.

Builds reaction contracts from feedback, affect, and previous-response
evaluation. These are session-level state changes, not durable writes.
"""

from __future__ import annotations

from typing import Any

from ..types.obligation_contract import ReactionContract
from ..types.operational_meaning import OperationalMeaningFrame, OperationalEffect


_DIMENSION_TO_STYLE: dict[str, dict[str, float]] = {
    "verbosity": {"detail": -0.15, "terseness": 0.1},
    "response_detail": {"detail": -0.15, "terseness": 0.1},
    "detail": {"detail": -0.15, "terseness": 0.1},
    "naturalness": {"warmth": 0.1, "formality": -0.1},
    "warmth": {"warmth": 0.1},
    "directness": {"directness": 0.1},
    "formality": {"formality": -0.1},
}


class ReactionContractBuilder:
    """Build reaction contracts from feedback and affect meaning frames."""

    def build(
        self,
        frame: OperationalMeaningFrame,
        effects: list[OperationalEffect] | None = None,
    ) -> ReactionContract | None:
        if frame.frame_type not in ("style_feedback", "response_feedback", "user_state_report"):
            return None

        style_delta: dict[str, float] = {}
        repair_debt_delta = 0.0

        dimension = frame.dimension or frame.features.get("dimension", "")
        if dimension in _DIMENSION_TO_STYLE:
            style_delta = dict(_DIMENSION_TO_STYLE[dimension])

        if effects:
            for effect in effects:
                if effect.effect_type == "increase_repair_debt":
                    repair_debt_delta += effect.strength
                elif effect.effect_type == "decrease_response_detail":
                    style_delta["detail"] = min(style_delta.get("detail", 0.0) - effect.strength, 0.0)
                elif effect.effect_type == "increase_directness":
                    style_delta["directness"] = style_delta.get("directness", 0.0) + effect.strength

        if frame.frame_type == "user_state_report":
            affect = frame.features.get("affect", "")
            if affect in ("positive", "great", "good", "happy"):
                style_delta["warmth"] = style_delta.get("warmth", 0.0) + 0.05
            elif affect in ("negative", "sad", "angry"):
                style_delta["warmth"] = style_delta.get("warmth", 0.0) + 0.05

        reaction_kind = "style_adjust" if style_delta else "repair_debt_update"
        if repair_debt_delta > 0 and not style_delta:
            reaction_kind = "repair_debt_update"

        return ReactionContract(
            reaction_kind=reaction_kind,
            target=frame.target_scope,
            style_delta=style_delta,
            repair_debt_delta=repair_debt_delta,
            persistence_policy="session_state",
            source_refs=list(frame.source_refs),
        )
