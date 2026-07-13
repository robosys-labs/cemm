"""ExecutionLedger and OperationOutcome — execution tracking records.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class TypedFailure:
    """A typed failure for an operation."""
    failure_kind: str
    detail: str = ""
    recoverable: bool = False


@dataclass(frozen=True, slots=True)
class PredictionError:
    """Discrepancy between predicted and observed effects."""
    operation_ref: str  # Ref[OperationInstance]
    predicted_ref: str = ""
    observed_ref: str = ""
    error_kind: str = ""


@dataclass(frozen=True, slots=True)
class OperationOutcome:
    """Outcome of a single operation execution."""
    operation_ref: str  # Ref[OperationInstance]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str = "pending"  # pending, running, succeeded, failed, cancelled
    output_refs: tuple[str, ...] = ()
    observed_effect_refs: tuple[str, ...] = ()
    failure: TypedFailure | None = None
    adapter_receipt: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionLedger:
    """Ledger of outcomes for a plan execution."""
    plan_ref: str  # Ref[PlanRecord]
    outcomes: tuple[OperationOutcome, ...] = ()
    prediction_errors: tuple[PredictionError, ...] = ()
