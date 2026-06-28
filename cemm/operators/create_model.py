from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.model import Model, ModelKind, ModelStatus
from ..types.signal import Signal, SignalKind, SourceType
import time, uuid


class CreateModelOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.CREATE_MODEL

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
        return OperatorResult(
            success=True,
            output_text=f"Created candidate model {name}",
            result_signal=result_signal,
            new_model_ids=[model.id],
        )
