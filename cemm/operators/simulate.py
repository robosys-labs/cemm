from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.signal import Signal, SignalKind, SourceType
from ..causal.inference import CausalInference
import time, uuid


class SimulateOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.SIMULATE

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        now = time.time()
        engine = CausalInference(ctx.store)
        action_or_event = ctx.params.get("action_or_event", "")
        active_claim_ids = ctx.selected_claim_ids or ctx.kernel.world.active_claim_ids
        predictions = engine.predict(action_or_event, active_claim_ids, ctx.kernel)

        output = f"Simulated: {action_or_event}\n"
        for p in predictions:
            output += f"  -> {p['predicate']}: {p.get('object_value') or p.get('object_entity_id') or ''} (confidence: {p['confidence']:.2f})\n"
        output = output.strip()

        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.SIMULATION_RESULT,
            source_id="simulate_operator",
            source_type=SourceType.ASSISTANT,
            content=output,
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.5,
            trust=0.6,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        return OperatorResult(
            success=True,
            output_text=output,
            result_signal=result_signal,
            cost_ms=2.0,
        )
