from __future__ import annotations
from ..types.action import Action, ActionKind, ActionStatus
from ..types.self_view import SelfView
from ..types.trace import Trace
import time


class ModeController:
    UNCERTAINTY_HIGH = 0.7
    COHERENCE_LOW = 0.4
    ERROR_RATE_HIGH = 0.3

    def __init__(self) -> None:
        self._last_mode: str | None = None

    def evaluate(self, self_view: SelfView) -> str | None:
        target = self._determine_mode(self_view)
        current = self_view.mode

        if target != current:
            self._last_mode = current
            return target
        return None

    def _determine_mode(self, self_view: SelfView) -> str:
        if self_view.uncertainty > self.UNCERTAINTY_HIGH:
            return "researcher"
        if self_view.coherence < self.COHERENCE_LOW:
            return "reflector"
        if self_view.recent_error_rate > self.ERROR_RATE_HIGH:
            return "reflector"
        return "assistant"

    @staticmethod
    def create_reflect_action(old_mode: str, new_mode: str, kernel_id: str) -> Action:
        return Action(
            id=f"mode_{old_mode}_to_{new_mode}_{int(time.time())}",
            kind=ActionKind.REFLECT,
            operator_model_id="mode_controller",
            status=ActionStatus.EXECUTED,
            confidence=0.9,
            trace=Trace(
                context_id=kernel_id,
                input_signal_ids=[],
                selected_claim_ids=[],
                selected_model_ids=[],
                action_id="",
                operator_model_id="mode_controller",
                causal_inference_used=False,
                frame_rules_applied=True,
                synthesis_verified=True,
                synthesis_verification_type="hard",
                permission="allowed",
                confidence=0.9,
                cost_ms=0.5,
                fallback_used=False,
            ),
            created_at=time.time(),
        )
