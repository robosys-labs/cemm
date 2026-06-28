from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.operator_spec import OperatorSpec


class OperatorRegistry:
    def __init__(self) -> None:
        self._operators: dict[ActionKind, BaseOperator] = {}
        self._specs: dict[str, OperatorSpec] = {}

    def register(self, operator: BaseOperator) -> None:
        self._operators[operator.action_kind] = operator
        spec = operator.spec()
        self._specs[operator.action_kind.value] = spec

    def get(self, kind: ActionKind) -> BaseOperator | None:
        return self._operators.get(kind)

    def get_spec(self, kind: ActionKind) -> OperatorSpec | None:
        return self._specs.get(kind.value)

    def get_spec_by_model_id(self, model_id: str) -> OperatorSpec | None:
        for spec in self._specs.values():
            if spec.model_id == model_id:
                return spec
        return None

    def execute(self, kind: ActionKind, ctx: OperatorContext) -> OperatorResult:
        op = self.get(kind)
        if op is None:
            return OperatorResult(
                success=False,
                output_text=f"Unknown operator: {kind.value}",
            )
        return op.execute(ctx)
