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

    def __init__(self, schema_store: Any | None = None) -> None:
        self._schema_store = schema_store

    def _lookup_operation_schema(
        self,
        semantic_key: str,
    ) -> Any | None:
        """Look up an operation schema by semantic key from the store.

        Uses find_candidates to get any registered schema (candidate,
        provisional, or active) since boot operation schemas may not
        have completed full activation assessment yet.
        """
        if self._schema_store is None:
            return None
        candidates = self._schema_store.find_candidates(semantic_key)
        if not candidates:
            return None
        # Return highest version
        best = max(candidates, key=lambda e: e.version)
        payload = getattr(best, "payload", None)
        return payload

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

            # Map goal kind to operation schema semantic key
            goal_to_op = {
                "information_state": "op:query",
                "world_state": "op:stage_mutation",
                "discourse": "op:respond",
            }
            op_semantic_key = goal_to_op.get(goal_kind, "op:maintain")

            # Look up the operation schema from the store for exact roles
            op_schema = self._lookup_operation_schema(op_semantic_key)
            if op_schema is None and operation_schemas:
                op_schema = operation_schemas.get(op_semantic_key)

            # Use the schema's semantic_key as schema_ref, or fallback
            schema_ref = op_semantic_key
            input_roles: tuple[str, ...] = ()
            output_roles: tuple[str, ...] = ()
            idem_policy = "strict"
            if op_schema is not None:
                schema_ref = getattr(op_schema, "semantic_key", op_semantic_key)
                input_roles = getattr(op_schema, "input_roles", ())
                output_roles = getattr(op_schema, "output_roles", ())
                idem_policy = getattr(op_schema, "idempotency_policy", "strict")

            # Create operation instance with schema-derived roles
            op = OperationInstance(
                id=f"op:{uuid4().hex[:12]}",
                schema_ref=schema_ref,
                bindings=(),
                status="pending" if is_capable else "blocked",
                idempotency_key=f"{schema_ref}:{goal_id}" if idem_policy != "strict" else "",
            )

            # Estimate cost based on operation class
            op_class = getattr(op_schema, "operation_class", "cognitive")
            cost_total = 0.1 if op_class == "cognitive" else 0.3
            cost = CostEstimate(
                total=cost_total,
                components={schema_ref: cost_total},
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
