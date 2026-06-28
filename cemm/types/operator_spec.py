from __future__ import annotations
from dataclasses import dataclass, field
from .action import ActionKind


@dataclass
class OperatorSpec:
    model_id: str
    action_kind: ActionKind
    required_slots: list[str] = field(default_factory=list)
    accepted_inputs: list[str] = field(default_factory=list)
    produces_signal_kind: str = "trace"
    may_mutate_memory: bool = False
    requires_permission: bool = True
    estimated_cost_ms: float = 10.0
    risk: float = 0.0
