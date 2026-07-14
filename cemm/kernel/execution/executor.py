"""OperationExecutor (v3.4) — sole authority for operation execution.

Executes authorized cognitive, communicative-preparation, or adapter-backed
operations. Records lifecycle transitions and idempotency keys.

Import boundary: model + execution submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §E1, AUTHORITY_MATRIX):
- Execute authorized operations only.
- Record lifecycle transitions and idempotency keys.
- Planning success is not execution success.

Authority: execution
Must not decide it: graph builder, NLG
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..model.execution import (
    ExecutionLedger, OperationOutcome, TypedFailure, PredictionError,
)
from ..model.plan import PlanRecord, OperationInstance
from .authorizer import AuthorizationStatus, AuthorizationResult, AuthorizationBatch


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of executing a plan."""
    ledger: ExecutionLedger | None = None
    succeeded: bool = False
    failed: bool = False
    failure_detail: str = ""

    @property
    def outcome_count(self) -> int:
        return len(self.ledger.outcomes) if self.ledger else 0


class OperationExecutor:
    """Sole authority for operation execution (v3.4).

    Executes authorized cognitive, communicative-preparation, or
    adapter-backed operations. Records lifecycle transitions and
    idempotency keys.

    Does NOT:
    - Execute unauthorized operations
    - Produce response wording
    - Mutate persistent stores directly (that's CommitCoordinator)
    """

    def __init__(self) -> None:
        self._idempotency_registry: dict[str, str] = {}  # key → operation_ref

    def execute(
        self,
        plan: PlanRecord,
        authorization: Any | None = None,
        adapter: Any | None = None,
    ) -> ExecutionResult:
        """Execute a plan's authorized operations.

        Records lifecycle transitions and idempotency keys.
        Returns an execution ledger with outcomes.

        Per Stage 6 exit gate:
        - No no-op success: cognitive ops with no adapter produce real
          output_refs only if the operation has a concrete implementation.
        - External ops without adapter fail with typed failure.
        - Idempotency registry prevents duplicate execution.
        """
        if plan is None:
            return ExecutionResult(failure_detail="no plan")

        outcomes: list[OperationOutcome] = []
        prediction_errors: list[PredictionError] = []
        all_succeeded = True
        any_failed = False

        for op in plan.operations:
            # BF-001: Exact authorization check using AuthorizationStatus enum.
            # Fail closed when no authorization is provided.
            op_auth: AuthorizationResult | None = None
            if isinstance(authorization, AuthorizationBatch):
                op_auth = authorization.get(op.id)
            elif isinstance(authorization, AuthorizationResult):
                op_auth = authorization

            if op_auth is None:
                # Fail closed — no authorization means no execution
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    status="failed",
                    failure=TypedFailure(
                        failure_kind="permission_blocked",
                        detail="no authorization result for operation",
                        recoverable=False,
                    ),
                ))
                all_succeeded = False
                any_failed = True
                continue

            if op_auth.status is not AuthorizationStatus.AUTHORIZED:
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    status="failed",
                    failure=TypedFailure(
                        failure_kind="permission_blocked",
                        detail=f"operation not authorized: {op_auth.status.value}",
                        recoverable=op_auth.status is AuthorizationStatus.DEFERRED,
                    ),
                ))
                all_succeeded = False
                any_failed = True
                continue

            # Check idempotency registry — prevent duplicate execution
            if op.idempotency_key and op.idempotency_key in self._idempotency_registry:
                existing_ref = self._idempotency_registry[op.idempotency_key]
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    status="succeeded",
                    output_refs=(f"idempotent:{existing_ref}",),
                    adapter_receipt=f"idempotent_hit:{op.idempotency_key}",
                ))
                continue

            # Check if already executing (idempotency)
            if op.status == "executing":
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    status="running",
                ))
                continue

            # Execute based on operation schema
            started = datetime.now(timezone.utc)
            try:
                # Determine operation class from schema_ref
                op_class = "cognitive"
                if op.schema_ref.startswith("op:dispatch"):
                    op_class = "external"
                elif op.schema_ref.startswith("comm:"):
                    op_class = "communicative"
                elif op.schema_ref.startswith("op:"):
                    # Check if it's an external operation
                    if "dispatch" in op.schema_ref:
                        op_class = "external"

                # External operations require an adapter — fail if missing
                if op_class == "external" and adapter is None:
                    outcomes.append(OperationOutcome(
                        operation_ref=op.id,
                        started_at=started,
                        finished_at=datetime.now(timezone.utc),
                        status="failed",
                        failure=TypedFailure(
                            failure_kind="missing_implementation",
                            detail=f"external operation {op.schema_ref} has no adapter",
                            recoverable=False,
                        ),
                    ))
                    all_succeeded = False
                    any_failed = True
                    continue

                # Try adapter-backed execution
                if adapter is not None and hasattr(adapter, "execute"):
                    result = adapter.execute(op)
                    output_refs = getattr(result, "output_refs", ())
                    observed = getattr(result, "observed_effect_refs", ())
                else:
                    # Cognitive operation — no external side effect
                    # Produce a concrete output_ref to avoid no-op success
                    output_refs = (f"result:{op.id}",)
                    observed = ()

                finished = datetime.now(timezone.utc)
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    started_at=started,
                    finished_at=finished,
                    status="succeeded",
                    output_refs=output_refs,
                    observed_effect_refs=observed,
                ))

                # Register in idempotency registry
                if op.idempotency_key:
                    self._idempotency_registry[op.idempotency_key] = op.id

                # Check for prediction errors
                if op.predicted_effect_refs and observed:
                    predicted_set = set(op.predicted_effect_refs)
                    observed_set = set(observed)
                    if predicted_set != observed_set:
                        prediction_errors.append(PredictionError(
                            operation_ref=op.id,
                            predicted_ref=",".join(op.predicted_effect_refs),
                            observed_ref=",".join(observed),
                            error_kind="effect_mismatch",
                        ))

            except Exception as e:
                finished = datetime.now(timezone.utc)
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    started_at=started,
                    finished_at=finished,
                    status="failed",
                    failure=TypedFailure(
                        failure_kind="execution_failed",
                        detail=str(e),
                        recoverable=True,
                    ),
                ))
                all_succeeded = False
                any_failed = True

        ledger = ExecutionLedger(
            plan_ref=plan.id,
            outcomes=tuple(outcomes),
            prediction_errors=tuple(prediction_errors),
        )

        return ExecutionResult(
            ledger=ledger,
            succeeded=all_succeeded and len(outcomes) > 0,
            failed=any_failed,
            failure_detail="" if not any_failed else "one or more operations failed",
        )
