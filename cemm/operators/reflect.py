from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
import time, uuid


class ReflectOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.REFLECT

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        now = time.time()
        self_state = ctx.store.self_store.latest()
        reflection_parts = []
        if self_state:
            if self_state.uncertainty > 0.7:
                reflection_parts.append(f"High uncertainty ({self_state.uncertainty:.2f})")
            if self_state.recent_error_rate > 0.3:
                reflection_parts.append(f"Elevated error rate ({self_state.recent_error_rate:.2f})")
            if self_state.epistemic.open_contradiction_claim_ids:
                reflection_parts.append(f"Open contradictions: {len(self_state.epistemic.open_contradiction_claim_ids)}")
        content = "; ".join(reflection_parts) if reflection_parts else "No issues detected"

        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.REFLECTION,
            source_id="reflect_operator",
            source_type=SourceType.ASSISTANT,
            content=content,
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.4,
            trust=0.8,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        return OperatorResult(
            success=True,
            output_text=content,
            result_signal=result_signal,
        )
