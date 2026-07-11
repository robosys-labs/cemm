"""TurnExecutionPlanner — plans contract execution order from obligation graph.

Produces an ordered list of ExecutionPlanSteps respecting dependencies,
blocking, and budget constraints. Only safety, permission denial, hard
contradiction, or required clarification globally preempt ordinary
compatible obligations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types.obligation_graph import ObligationGraph, ObligationNodeKind
from ..types.obligation_contract import ObligationContract


@dataclass(frozen=True, slots=True)
class ExecutionPlanStep:
    """One step in the execution plan."""
    node_id: str
    kind: ObligationNodeKind
    priority: int = 0
    budget_cost: float = 1.0
    is_required: bool = True


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Ordered plan of steps to execute."""
    steps: tuple[ExecutionPlanStep, ...] = ()


class TurnExecutionPlanner:
    """Plans execution order from obligation graph and contracts.

    Produces exactly one ExecutionPlan per turn. The plan is consumed
    by ContractExecutor.
    """

    def plan(
        self,
        graph: ObligationGraph | None,
        contract: ObligationContract | None,
    ) -> list[ExecutionPlanStep]:
        """Produce ordered list of execution steps.

        Delegates topological ordering to ObligationGraph.execution_order().
        Blocked nodes are automatically excluded.
        """
        if graph is None:
            return []

        order = graph.execution_order()
        steps: list[ExecutionPlanStep] = []

        for node_id in order:
            node = graph.get_node(node_id)
            if node is None:
                continue
            step = ExecutionPlanStep(
                node_id=node.node_id,
                kind=node.kind,
                priority=node.priority,
                budget_cost=node.budget_cost,
                is_required=node.is_required,
            )
            steps.append(step)

        return steps
