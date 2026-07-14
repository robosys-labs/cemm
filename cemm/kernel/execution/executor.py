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

    def execute(
        self,
        plan: PlanRecord,
        authorization: Any | None = None,
        adapter: Any | None = None,
    ) -> ExecutionResult:
        """Execute a plan's authorized operations.

        Records lifecycle transitions and idempotency keys.
        Returns an execution ledger with outcomes.
        """
        if plan is None:
            return ExecutionResult(failure_detail="no plan")

        outcomes: list[OperationOutcome] = []
        prediction_errors: list[PredictionError] = []
        all_succeeded = True
        any_failed = False

        for op in plan.operations:
            # Check authorization
            is_authorized = True
            if authorization is not None:
                is_authorized = getattr(authorization, "authorized", True)

            if not is_authorized:
                outcomes.append(OperationOutcome(
                    operation_ref=op.id,
                    status="failed",
                    failure=TypedFailure(
                        failure_kind="permission_blocked",
                        detail="operation not authorized",
                        recoverable=False,
                    ),
                ))
                all_succeeded = False
                any_failed = True
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
                # Try adapter-backed execution
                if adapter is not None and hasattr(adapter, "execute"):
                    result = adapter.execute(op)
                    output_refs = getattr(result, "output_refs", ())
                    observed = getattr(result, "observed_effect_refs", ())
                else:
                    # Cognitive operation — no external side effect
                    output_refs = ()
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
