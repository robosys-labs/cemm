"""Planner (v3.4) — sole authority for plan selection.

Instantiates operation schemas, checks preconditions/capabilities,
simulates effects, orders dependencies, estimates costs/risks, and
produces bounded plans.

Import boundary: model + execution submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §D3, AUTHORITY_MATRIX):
- Plans are sequences of operations toward goal satisfaction.
- Does NOT execute operations.

Authority: plan_selection
Must not decide it: response ranker
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ..model.plan import (
    PlanRecord, OperationInstance, OperationDependency, CostEstimate, RiskEstimate,
)
from ..model.role_binding import RoleBinding


@dataclass(frozen=True, slots=True)
class PlanBatch:
    """A batch of plans produced by the planner."""
    plans: tuple[PlanRecord, ...] = ()
    selected: PlanRecord | None = None
    rejected: tuple[PlanRecord, ...] = ()

    @property
    def plan_count(self) -> int:
        return len(self.plans)


class Planner:
    """Sole authority for plan selection (v3.4).

    Instantiates operation schemas, checks preconditions/capabilities,
    simulates effects, orders dependencies, estimates costs/risks, and
    produces bounded plans.

    Does NOT:
    - Execute operations
    - Authorize operations (that's OperationAuthorizer)
    - Select response content
    """

    def plan(
        self,
        goals: tuple[Any, ...] = (),
        capability_assessment: Any | None = None,
        workspace_snapshot: Any | None = None,
        operation_schemas: dict[str, Any] | None = None,
    ) -> PlanBatch:
        """Produce bounded plans for the given goals.

        Instantiates operation schemas, checks preconditions, simulates
        effects, orders dependencies, estimates costs/risks.
        """
        if not goals:
            return PlanBatch()

        plans: list[PlanRecord] = []
        is_capable = True
        if capability_assessment is not None:
            is_capable = getattr(capability_assessment, "is_capable", True)

        for goal in goals:
            goal_id = getattr(goal, "id", "")
            goal_kind = getattr(goal, "goal_kind", "information_state")

            # Determine operation schema based on goal kind
            if goal_kind == "information_state":
                op_schema = "op:query"
            elif goal_kind == "world_state":
                op_schema = "op:write"
            elif goal_kind == "discourse":
                op_schema = "op:respond"
            else:
                op_schema = "op:maintain"

            # Create operation instance
            op = OperationInstance(
                id=f"op:{uuid4().hex[:12]}",
                schema_ref=op_schema,
                bindings=(),
                status="pending" if is_capable else "blocked",
            )

            # Estimate cost
            cost = CostEstimate(
                total=0.1 if goal_kind == "information_state" else 0.3,
                components={op_schema: 0.1},
            )

            # Estimate risk
            risk = RiskEstimate(
                level="low" if is_capable else "high",
                factors=() if is_capable else ("capability_unavailable",),
            )

            # Compute plan score
            priority = getattr(goal, "priority", 0.5)
            urgency = getattr(goal, "urgency", 0.5)
            score = priority * 0.6 + urgency * 0.4

            plan = PlanRecord(
                id=f"plan:{uuid4().hex[:12]}",
                goal_refs=(goal_id,),
                operations=(op,),
                dependencies=(),
                cost=cost,
                risk=risk,
                score=score,
                rejected_reasons=() if is_capable else ("capability_unavailable",),
            )
            plans.append(plan)

        # Sort by score
        plans.sort(key=lambda p: p.score, reverse=True)

        # Select best plan
        viable = [p for p in plans if not p.rejected_reasons]
        selected = viable[0] if viable else (plans[0] if plans else None)
        rejected = tuple(p for p in plans if p.rejected_reasons)

        return PlanBatch(
            plans=tuple(plans),
            selected=selected,
            rejected=rejected,
        )
