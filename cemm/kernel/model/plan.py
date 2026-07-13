"""OperationInstance and PlanRecord — planning records.

Import boundary: standard library only → refs, role_binding.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .role_binding import RoleBinding


@dataclass(frozen=True, slots=True)
class OperationDependency:
    """Dependency between operations in a plan."""
    source_op_ref: str  # Ref[OperationInstance]
    target_op_ref: str  # Ref[OperationInstance]
    dependency_kind: str = "sequential"  # sequential, conditional, parallel


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Estimated cost of a plan."""
    total: float = 0.0
    components: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RiskEstimate:
    """Estimated risk of a plan."""
    level: str = "low"  # low, medium, high
    factors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationInstance:
    """An instance of an operation selected for execution."""
    id: str
    schema_ref: str  # Ref[OperationSchema]
    bindings: tuple[RoleBinding, ...] = ()
    predicted_effect_refs: tuple[str, ...] = ()  # Ref[MutationTemplate]
    status: str = "pending"  # pending, authorized, executing, completed, failed
    idempotency_key: str = ""


@dataclass(frozen=True, slots=True)
class PlanRecord:
    """A plan — a sequence of operations toward goal satisfaction."""
    id: str
    goal_refs: tuple[str, ...] = ()  # Ref[GoalRecord]
    operations: tuple[OperationInstance, ...] = ()
    dependencies: tuple[OperationDependency, ...] = ()
    predicted_outcome_refs: tuple[str, ...] = ()  # Ref[SemanticPattern]
    cost: CostEstimate = field(default_factory=CostEstimate)
    risk: RiskEstimate = field(default_factory=RiskEstimate)
    score: float = 0.0
    rejected_reasons: tuple[str, ...] = ()
