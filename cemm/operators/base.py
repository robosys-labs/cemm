from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from ..types.action import Action, ActionKind, ActionStatus
from ..types.signal import Signal
from ..types.trace import Trace
from ..types.context_kernel import ContextKernel
from ..types.operator_spec import OperatorSpec
from ..store.store import Store
from ..registry import Registry


@dataclass
class OperatorContext:
    kernel: ContextKernel
    input_signal: Signal
    store: Store
    registry: Registry
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    budget_override: dict | None = None


@dataclass
class OperatorResult:
    success: bool = True
    output_text: str = ""
    trace: Trace | None = None
    result_signal: Signal | None = None
    new_claim_ids: list[str] = field(default_factory=list)
    new_model_ids: list[str] = field(default_factory=list)
    action: Action | None = None
    cost_ms: float = 0.0
    fallback_used: bool = False


class BaseOperator(ABC):
    @property
    @abstractmethod
    def action_kind(self) -> ActionKind:
        ...

    @abstractmethod
    def execute(self, ctx: OperatorContext) -> OperatorResult:
        ...

    def spec(self) -> OperatorSpec:
        return OperatorSpec(
            model_id=self.__class__.__name__,
            action_kind=self.action_kind,
            requires_permission=True,
        )
