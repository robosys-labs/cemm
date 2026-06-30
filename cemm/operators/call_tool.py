from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
import time, uuid


class CallToolOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.CALL_TOOL

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        tool_id = ctx.params.get("tool_id", "")
        if not tool_id:
            return OperatorResult(
                success=False,
                output_text="No tool_id specified for CALL_TOOL",
            )
        output = f"Calling tool {tool_id}"
        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.TRACE,
            source_id="call_tool_operator",
            source_type=SourceType.ASSISTANT,
            content=output,
            observed_at=time.time(),
            context_id=ctx.kernel.id,
            salience=0.7,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="call_tool",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            action_candidates=[{"tool_id": tool_id}],
        )
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            action_id="",
            operator_model_id="call_tool_operator",
            permission="allowed",
            confidence=0.7,
            cost_ms=cost_ms,
            grounded_graph_id=ctx.grounded_graph_id,
            memory_packet_id=ctx.memory_packet_id,
            inference_packet_id=ctx.inference_packet_id,
            semantic_event_graph_id=ctx.semantic_event_graph_id,
            semantic_answer_graph_id=answer_graph.id,
        )
        return OperatorResult(
            success=True,
            output_text=output,
            trace=trace,
            result_signal=result_signal,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
