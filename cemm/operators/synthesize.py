from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..synthesis.router import SynthesisRouter


class SynthesizeOperator(BaseOperator):
    _router = SynthesisRouter()

    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.SYNTHESIZE

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        strategy_name = ctx.params.get("strategy", "template")
        result = self._router.route(strategy_name, ctx.kernel, ctx.store, ctx.registry, ctx.params)
        return OperatorResult(
            success=result.success,
            output_text=result.output,
            cost_ms=result.cost_ms,
        )
