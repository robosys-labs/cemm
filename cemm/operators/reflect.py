from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
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
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="reflect",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
        )
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            action_id="",
            operator_model_id="reflect_operator",
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
            success=True,
            output_text=content,
            trace=trace,
            result_signal=result_signal,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
