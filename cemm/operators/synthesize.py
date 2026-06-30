from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..synthesis.router import SynthesisRouter
import time, uuid


class SynthesizeOperator(BaseOperator):
    _router = SynthesisRouter()

    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.SYNTHESIZE

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        strategy_name = ctx.params.get("strategy", "template")
        result = self._router.route(strategy_name, ctx.kernel, ctx.store, ctx.registry, ctx.params)
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="synthesize",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
        )
        cost_ms = float(result.cost_ms) if result.cost_ms else ((time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0)
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            action_id="",
            operator_model_id="synthesize_operator",
            synthesis_strategy_model_id=strategy_name,
            permission="allowed",
            confidence=0.6,
            cost_ms=cost_ms,
            grounded_graph_id=ctx.grounded_graph_id,
            memory_packet_id=ctx.memory_packet_id,
            inference_packet_id=ctx.inference_packet_id,
            semantic_event_graph_id=ctx.semantic_event_graph_id,
            semantic_answer_graph_id=answer_graph.id,
        )
        return OperatorResult(
            success=result.success,
            output_text=result.output,
            trace=trace,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
