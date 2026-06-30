from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.model import Model, ModelKind, ModelStatus
from ..types.signal import Signal, SignalKind, SourceType
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
import time, uuid


class CreateModelOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.CREATE_MODEL_CANDIDATE

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        now = time.time()
        kind_str = ctx.params.get("kind", "predicate")
        name = ctx.params.get("name", "unnamed")
        description = ctx.params.get("description", "")

        model = Model(
            id=uuid.uuid4().hex[:16],
            kind=ModelKind(kind_str),
            name=name,
            description=description,
            evidence_signal_ids=[ctx.input_signal.id],
            status=ModelStatus.CANDIDATE,
            created_at=now,
            updated_at=now,
            permission=ctx.kernel.permission,
        )
        ctx.store.models.put(model)

        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.MEMORY_UPDATE,
            source_id="create_model_operator",
            source_type=SourceType.ASSISTANT,
            content=f"Created candidate model: {name} ({kind_str})",
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.5,
            trust=0.8,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="create_model",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_model_ids=[model.id],
        )
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_model_ids=[model.id],
            action_id="",
            operator_model_id="create_model_operator",
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
            output_text=f"Created candidate model {name}",
            trace=trace,
            result_signal=result_signal,
            new_model_ids=[model.id],
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
