from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
import time, uuid


class AbstainOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.ABSTAIN

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        reason = ctx.params.get("reason", "Insufficient evidence or permission")
        output = f"I can't answer that. Reason: {reason}"
        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.TRACE,
            source_id="abstain_operator",
            source_type=SourceType.ASSISTANT,
            content=output,
            observed_at=time.time(),
            context_id=ctx.kernel.id,
            salience=0.3,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        return OperatorResult(
            success=True,
            output_text=output,
            result_signal=result_signal,
        )
