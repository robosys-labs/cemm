from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..synthesis.realizer import RealizationPipeline
import time, uuid

_pipeline = RealizationPipeline()


class AbstainOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.ABSTAIN

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        reason = ctx.params.get("reason", "Insufficient evidence or permission")
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="abstain",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            uncertainty_reasons=[reason],
            confidence=max(0.5, 1.0 - ctx.kernel.self_view.uncertainty),
        )
        result = _pipeline.run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
        output = result.output
        if not result.success:
            output = f"I can't answer that. Reason: {reason}"

        if not result.verified:
            verification_meta = result.metadata.get("verification", {})
            issues = verification_meta.get("details", ["unverified output"])
            output = f"I can't answer that. Reason: verification blocked — {'; '.join(issues)}"

        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
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
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            action_id="",
            operator_model_id="abstain_operator",
            semantic_answer_graph_id=answer_graph.id,
            synthesis_verified=result.verified,
            synthesis_verification_type="soft",
            permission="allowed",
            confidence=max(0.0, min(1.0, 1.0 - ctx.kernel.self_view.uncertainty)),
            cost_ms=cost_ms,
            fallback_used=False,
            grounded_graph_id=ctx.grounded_graph_id,
            memory_packet_id=ctx.memory_packet_id,
            inference_packet_id=ctx.inference_packet_id,
            semantic_event_graph_id=ctx.semantic_event_graph_id,
        )
        return OperatorResult(
            success=True,
            output_text=output,
            trace=trace,
            result_signal=result_signal,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
