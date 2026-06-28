from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
import time, uuid


class AskOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.ASK

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        question = ctx.params.get("question", "Could you clarify?")
        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.TRACE,
            source_id="ask_operator",
            source_type=SourceType.ASSISTANT,
            content=question,
            observed_at=time.time(),
            context_id=ctx.kernel.id,
            salience=0.6,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        return OperatorResult(
            success=True,
            output_text=question,
            result_signal=result_signal,
        )
