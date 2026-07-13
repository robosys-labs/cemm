"""OutcomeReconciler — compare predicted and observed effects.

Import boundary: model submodules only. No engine, schema, or epistemics imports.

Architectural guardrails (CORE_LOOP.md E3, AUTHORITY_MATRIX):
- OutcomeReconciler is the sole authority for confirmed/predicted deltas
  and ledger.
- Compare predicted and observed effects.
- Produce actual event/state propositions, goal progress, prediction
  errors, competence updates, and mutation candidates.
- Planning success is not execution success.
- Prediction differs from observation/commit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.execution import (
    OperationOutcome, PredictionError, ExecutionLedger, TypedFailure,
)
from ..model.plan import OperationInstance, PlanRecord


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    """Result of reconciling predicted and observed effects.

    OutcomeReconciler produces confirmed/predicted deltas and ledger.
    Planning success is not execution success.
    """
    plan_ref: str
    predicted_effect_refs: tuple[str, ...] = ()
    observed_effect_refs: tuple[str, ...] = ()
    confirmed_effect_refs: tuple[str, ...] = ()  # Both predicted AND observed
    unexpected_effect_refs: tuple[str, ...] = ()  # Observed but NOT predicted
    unconfirmed_effect_refs: tuple[str, ...] = ()  # Predicted but NOT observed
    prediction_errors: tuple[PredictionError, ...] = ()
    planning_success: bool = False
    execution_success: bool = False
    goal_progress_refs: tuple[str, ...] = ()


class OutcomeReconciler:
    """Reconciles predicted and observed effects.

    OutcomeReconciler is the sole authority for confirmed/predicted deltas
    and ledger.

    Planning success is not execution success.
    Prediction differs from observation/commit.
    """

    def reconcile(
        self,
        plan: PlanRecord,
        ledger: ExecutionLedger,
    ) -> ReconciliationResult:
        """Reconcile predicted effects with observed outcomes.

        Compare predicted and observed effects. Produce actual
        event/state propositions, goal progress, prediction errors,
        competence updates, and mutation candidates.
        """
        # Collect all predicted effects from the plan
        predicted: set[str] = set()
        for op in plan.operations:
            predicted.update(op.predicted_effect_refs)

        # Collect all observed effects from the ledger
        observed: set[str] = set()
        for outcome in ledger.outcomes:
            observed.update(outcome.observed_effect_refs)

        # Confirmed: both predicted and observed
        confirmed = predicted & observed

        # Unexpected: observed but not predicted
        unexpected = observed - predicted

        # Unconfirmed: predicted but not observed
        unconfirmed = predicted - observed

        # Build prediction errors
        errors: list[PredictionError] = []

        # Unconfirmed predictions are prediction errors
        for eff in unconfirmed:
            errors.append(PredictionError(
                operation_ref="",
                predicted_ref=eff,
                observed_ref="",
                error_kind="unconfirmed_prediction",
            ))

        # Unexpected observations are prediction errors
        for eff in unexpected:
            errors.append(PredictionError(
                operation_ref="",
                predicted_ref="",
                observed_ref=eff,
                error_kind="unexpected_observation",
            ))

        # Check for operation failures
        operation_failures = [
            o for o in ledger.outcomes
            if o.status == "failed" or o.failure is not None
        ]

        # Planning success: plan was created and not rejected
        planning_success = len(plan.rejected_reasons) == 0

        # Execution success: all operations succeeded and no failures
        execution_success = (
            planning_success
            and len(operation_failures) == 0
            and all(o.status == "succeeded" for o in ledger.outcomes)
            and len(ledger.outcomes) > 0
        )

        return ReconciliationResult(
            plan_ref=plan.id,
            predicted_effect_refs=tuple(predicted),
            observed_effect_refs=tuple(observed),
            confirmed_effect_refs=tuple(confirmed),
            unexpected_effect_refs=tuple(unexpected),
            unconfirmed_effect_refs=tuple(unconfirmed),
            prediction_errors=tuple(errors),
            planning_success=planning_success,
            execution_success=execution_success,
        )

    def reconcile_operation(
        self,
        operation: OperationInstance,
        outcome: OperationOutcome,
    ) -> tuple[bool, PredictionError | None]:
        """Reconcile a single operation's predicted vs observed effects.

        Returns (is_confirmed, prediction_error).
        """
        predicted = set(operation.predicted_effect_refs)
        observed = set(outcome.observed_effect_refs)

        # Check for unconfirmed predictions
        unconfirmed = predicted - observed
        if unconfirmed:
            return (False, PredictionError(
                operation_ref=operation.id,
                predicted_ref=next(iter(unconfirmed)),
                observed_ref="",
                error_kind="unconfirmed_prediction",
            ))

        # Check for unexpected observations
        unexpected = observed - predicted
        if unexpected:
            return (False, PredictionError(
                operation_ref=operation.id,
                predicted_ref="",
                observed_ref=next(iter(unexpected)),
                error_kind="unexpected_observation",
            ))

        return (True, None)
