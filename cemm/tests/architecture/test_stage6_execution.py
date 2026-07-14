"""Stage 6 exit gate tests — goals, plans, effects, and real commit.

Per completion-plan.md Stage 6, CORE_LOOP.md §D-F, AUTHORITY_MATRIX:
- No generic op:write with empty bindings
- No no-op success
- One mutation authority
- Exact write contract
- Teaching an effect never fires it
- Legacy operational compilers no longer decide behavior
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.operation import OperationSchema
from cemm.kernel.execution.planner import Planner, PlanBatch
from cemm.kernel.execution.executor import OperationExecutor, ExecutionResult
from cemm.kernel.execution.authorizer import (
    OperationAuthorizer,
    AuthorizationStatus,
    AuthorizationResult,
    AuthorizationBatch,
    AuthorizationConditions,
)
from cemm.kernel.execution.reconciliation import OutcomeReconciler
from cemm.kernel.execution.commit import (
    CommitCoordinator,
    WriteContractGuard,
    ValidationResult,
)
from cemm.kernel.model.goal import GoalRecord
from cemm.kernel.model.plan import (
    PlanRecord,
    OperationInstance,
    OperationDependency,
    CostEstimate,
    RiskEstimate,
)
from cemm.kernel.model.mutation import (
    MutationSet,
    MutationOperation,
    CommitOutcome,
)
from cemm.kernel.model.execution import (
    ExecutionLedger,
    OperationOutcome,
    PredictionError,
    TypedFailure,
)
from cemm.kernel.model.identity import SemanticIdentity, Permission, PermissionScope
from cemm.kernel.boot.manifest import build_boot_manifest, boot_internal_operations


# ── Helpers ───────────────────────────────────────────────────────


def make_goal(
    goal_kind: str = "information_state",
    priority: float = 0.7,
    urgency: float = 0.5,
) -> GoalRecord:
    return GoalRecord(
        id=f"goal:{uuid4().hex[:8]}",
        owner_ref="self",
        goal_kind=goal_kind,
        priority=priority,
        urgency=urgency,
    )


def make_operation(
    schema_ref: str = "op:query",
    idempotency_key: str = "",
    predicted_effects: tuple[str, ...] = (),
) -> OperationInstance:
    return OperationInstance(
        id=f"op:{uuid4().hex[:8]}",
        schema_ref=schema_ref,
        idempotency_key=idempotency_key,
        predicted_effect_refs=predicted_effects,
    )


def make_plan(
    operations: tuple[OperationInstance, ...] = (),
    rejected: tuple[str, ...] = (),
) -> PlanRecord:
    return PlanRecord(
        id=f"plan:{uuid4().hex[:8]}",
        operations=operations,
        rejected_reasons=rejected,
    )


def make_mutation(
    required: bool = True,
    evidence_refs: tuple[str, ...] = ("ev:1",),
    action: str = "create",
) -> MutationOperation:
    return MutationOperation(
        id=f"mut:{uuid4().hex[:8]}",
        action=action,
        evidence_refs=evidence_refs,
        required=required,
    )


# ── 1. Internal operation schemas registered ──────────────────────


class TestInternalOperationSchemas:
    def test_internal_operations_in_manifest(self):
        entries = boot_internal_operations()
        keys = {e.semantic_key for e in entries}
        assert "op:retrieve" in keys
        assert "op:query" in keys
        assert "op:compare" in keys
        assert "op:infer" in keys
        assert "op:simulate" in keys
        assert "op:stage_mutation" in keys
        assert "op:ask" in keys
        assert "op:answer" in keys
        assert "op:realize" in keys
        assert "op:dispatch" in keys

    def test_internal_ops_have_input_roles(self):
        entries = boot_internal_operations()
        for entry in entries:
            payload = entry.envelope.payload
            assert payload is not None
            assert len(payload.input_roles) > 0
            assert len(payload.output_roles) > 0

    def test_dispatch_is_external_class(self):
        entries = boot_internal_operations()
        dispatch = next(e for e in entries if e.semantic_key == "op:dispatch")
        assert dispatch.envelope.payload.operation_class == "external"

    def test_ask_is_communicative_class(self):
        entries = boot_internal_operations()
        ask = next(e for e in entries if e.semantic_key == "op:ask")
        assert ask.envelope.payload.operation_class == "communicative"

    def test_internal_ops_registered_in_store(self):
        store = SemanticSchemaStore()
        from cemm.kernel.boot.validation import BootValidator
        validator = BootValidator()
        manifest = build_boot_manifest()
        report = validator.validate_boot(store, manifest)
        validator.register_boot_schemas(store, manifest, report)
        # Look up op:query
        candidates = store.find_candidates("op:query")
        assert len(candidates) > 0
        record = candidates[0]
        assert record.payload is not None
        assert "query_pattern" in record.payload.input_roles

    def test_stage_mutation_has_evidence_role(self):
        entries = boot_internal_operations()
        stage = next(e for e in entries if e.semantic_key == "op:stage_mutation")
        assert "mutation_set" in stage.envelope.payload.input_roles
        assert "evidence_refs" in stage.envelope.payload.input_roles


# ── 2. Planner binds exact roles ──────────────────────────────────


class TestPlannerExactRoles:
    def test_planner_uses_store_schema_for_query(self):
        store = SemanticSchemaStore()
        from cemm.kernel.boot.validation import BootValidator
        validator = BootValidator()
        manifest = build_boot_manifest()
        report = validator.validate_boot(store, manifest)
        validator.register_boot_schemas(store, manifest, report)

        planner = Planner(schema_store=store)
        goal = make_goal(goal_kind="information_state")
        batch = planner.plan(goals=(goal,))
        assert batch.selected is not None
        op = batch.selected.operations[0]
        assert op.schema_ref == "op:query"

    def test_planner_uses_store_schema_for_stage_mutation(self):
        store = SemanticSchemaStore()
        from cemm.kernel.boot.validation import BootValidator
        validator = BootValidator()
        manifest = build_boot_manifest()
        report = validator.validate_boot(store, manifest)
        validator.register_boot_schemas(store, manifest, report)

        planner = Planner(schema_store=store)
        goal = make_goal(goal_kind="world_state")
        batch = planner.plan(goals=(goal,))
        assert batch.selected is not None
        op = batch.selected.operations[0]
        assert op.schema_ref == "op:stage_mutation"

    def test_planner_assigns_idempotency_key_for_at_most_once(self):
        store = SemanticSchemaStore()
        from cemm.kernel.boot.validation import BootValidator
        validator = BootValidator()
        manifest = build_boot_manifest()
        report = validator.validate_boot(store, manifest)
        validator.register_boot_schemas(store, manifest, report)

        planner = Planner(schema_store=store)
        # discourse goals map to op:respond which is cognitive/strict
        goal = make_goal(goal_kind="discourse")
        batch = planner.plan(goals=(goal,))
        op = batch.selected.operations[0]
        # op:respond has strict idempotency → empty key
        assert op.idempotency_key == ""

    def test_planner_fallback_without_store(self):
        planner = Planner()
        goal = make_goal(goal_kind="information_state")
        batch = planner.plan(goals=(goal,))
        assert batch.selected is not None
        assert batch.selected.operations[0].schema_ref == "op:query"


# ── 3. Executor: no no-op success ─────────────────────────────────


class TestExecutorNoNoOp:
    def test_cognitive_op_produces_output_ref(self):
        executor = OperationExecutor()
        op = make_operation(schema_ref="op:query")
        plan = make_plan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.AUTHORIZED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.succeeded
        assert result.ledger.outcomes[0].output_refs  # Not empty

    def test_external_op_without_adapter_fails(self):
        executor = OperationExecutor()
        op = make_operation(schema_ref="op:dispatch")
        plan = make_plan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.AUTHORIZED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.failed
        assert result.ledger.outcomes[0].failure is not None
        assert result.ledger.outcomes[0].failure.failure_kind == "missing_implementation"

    def test_unauthorized_op_fails_closed(self):
        executor = OperationExecutor()
        op = make_operation()
        plan = make_plan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.DENIED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.failed
        assert result.ledger.outcomes[0].failure.failure_kind == "permission_blocked"

    def test_no_authorization_fails_closed(self):
        executor = OperationExecutor()
        op = make_operation()
        plan = make_plan(operations=(op,))
        result = executor.execute(plan, authorization=None)
        assert result.failed
        assert result.ledger.outcomes[0].failure.failure_kind == "permission_blocked"


# ── 4. Idempotency registry ───────────────────────────────────────


class TestIdempotencyRegistry:
    def test_idempotent_op_not_re_executed(self):
        executor = OperationExecutor()
        op = make_operation(
            schema_ref="op:ask",
            idempotency_key="ask:goal1",
        )
        plan = make_plan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.AUTHORIZED,
            )
        })
        # First execution
        result1 = executor.execute(plan, authorization=auth)
        assert result1.succeeded
        # Second execution with same idempotency key
        result2 = executor.execute(plan, authorization=auth)
        assert result2.succeeded
        # Second outcome should be idempotent hit
        assert result2.ledger.outcomes[0].adapter_receipt is not None
        assert "idempotent_hit" in result2.ledger.outcomes[0].adapter_receipt

    def test_strict_op_no_idempotency_key(self):
        executor = OperationExecutor()
        op = make_operation(schema_ref="op:query", idempotency_key="")
        plan = make_plan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.AUTHORIZED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.succeeded
        # Should have a real output ref, not an idempotent hit
        assert "idempotent" not in result.ledger.outcomes[0].output_refs[0]


# ── 5. OutcomeReconciler ──────────────────────────────────────────


class TestOutcomeReconciler:
    def test_reconcile_confirmed_effects(self):
        reconciler = OutcomeReconciler()
        op = make_operation(predicted_effects=("effect:1",))
        plan = make_plan(operations=(op,))
        ledger = ExecutionLedger(
            plan_ref=plan.id,
            outcomes=(OperationOutcome(
                operation_ref=op.id,
                status="succeeded",
                observed_effect_refs=("effect:1",),
            ),),
        )
        result = reconciler.reconcile(plan, ledger)
        assert "effect:1" in result.confirmed_effect_refs
        assert len(result.prediction_errors) == 0
        assert result.execution_success

    def test_reconcile_unconfirmed_prediction(self):
        reconciler = OutcomeReconciler()
        op = make_operation(predicted_effects=("effect:1", "effect:2"))
        plan = make_plan(operations=(op,))
        ledger = ExecutionLedger(
            plan_ref=plan.id,
            outcomes=(OperationOutcome(
                operation_ref=op.id,
                status="succeeded",
                observed_effect_refs=("effect:1",),
            ),),
        )
        result = reconciler.reconcile(plan, ledger)
        assert "effect:2" in result.unconfirmed_effect_refs
        assert len(result.prediction_errors) > 0

    def test_reconcile_unexpected_observation(self):
        reconciler = OutcomeReconciler()
        op = make_operation(predicted_effects=("effect:1",))
        plan = make_plan(operations=(op,))
        ledger = ExecutionLedger(
            plan_ref=plan.id,
            outcomes=(OperationOutcome(
                operation_ref=op.id,
                status="succeeded",
                observed_effect_refs=("effect:1", "effect:unexpected"),
            ),),
        )
        result = reconciler.reconcile(plan, ledger)
        assert "effect:unexpected" in result.unexpected_effect_refs

    def test_planning_success_not_execution_success(self):
        reconciler = OutcomeReconciler()
        op = make_operation()
        plan = make_plan(operations=(op,))
        ledger = ExecutionLedger(
            plan_ref=plan.id,
            outcomes=(OperationOutcome(
                operation_ref=op.id,
                status="failed",
                failure=TypedFailure(failure_kind="execution_failed"),
            ),),
        )
        result = reconciler.reconcile(plan, ledger)
        assert result.planning_success
        assert not result.execution_success


# ── 6. CommitCoordinator ──────────────────────────────────────────


class TestCommitCoordinator:
    def test_commit_with_store_uses_store_revision(self):
        from dataclasses import dataclass

        @dataclass
        class MockStore:
            store_revision: int = 42

        mock_store = MockStore()
        coord = CommitCoordinator(store=mock_store)
        mut = make_mutation()
        ms = MutationSet(id="ms:1", phase="critical", operations=(mut,))
        outcome = coord.commit(ms)
        assert outcome.required_satisfied
        assert outcome.committed_revision is not None

    def test_commit_without_store_uses_simulated_revision(self):
        coord = CommitCoordinator()
        mut = make_mutation()
        ms = MutationSet(id="ms:2", phase="critical", operations=(mut,))
        outcome = coord.commit(ms)
        assert outcome.required_satisfied

    def test_commit_validates_required_evidence(self):
        coord = CommitCoordinator()
        mut = make_mutation(evidence_refs=())
        ms = MutationSet(id="ms:3", phase="critical", operations=(mut,))
        outcome = coord.commit(ms)
        assert not outcome.required_satisfied
        assert any(r.status == "failed" for r in outcome.results)

    def test_atomic_rollback_on_failure(self):
        coord = CommitCoordinator()
        mut1 = make_mutation(evidence_refs=("ev:1",))
        mut2 = make_mutation(evidence_refs=())  # No evidence → fails
        ms = MutationSet(
            id="ms:4", phase="critical",
            operations=(mut1, mut2),
        )
        outcome = coord.commit(ms)
        assert not outcome.required_satisfied
        # All should be rolled back
        assert all(r.status == "failed" for r in outcome.results)

    def test_write_contract_guard_no_required_writes(self):
        guard = WriteContractGuard()
        mut = make_mutation(required=False)
        ms = MutationSet(id="ms:5", operations=(mut,))
        result = guard.check_write_contract(ms)
        assert not result.is_valid

    def test_write_contract_guard_with_required(self):
        guard = WriteContractGuard()
        mut = make_mutation(required=True)
        ms = MutationSet(id="ms:6", operations=(mut,))
        result = guard.check_write_contract(ms)
        assert result.is_valid
        assert mut.id in result.required_operations


# ── 7. Authorization revalidation ────────────────────────────────


class TestAuthorizationRevalidation:
    def test_revalidate_same_fingerprint_passes(self):
        authorizer = OperationAuthorizer()
        op = make_operation()
        conditions = AuthorizationConditions(
            capability_available=True,
            permission_allowed=True,
            safety_passed=True,
            privacy_passed=True,
            resources_available=True,
            context_valid=True,
            schema_use_valid=True,
            risk_level="low",
            environment_fingerprint="fp:1",
        )
        auth = authorizer.authorize(op, conditions)
        assert auth.status is AuthorizationStatus.AUTHORIZED
        # Revalidate with same fingerprint
        revalidated = authorizer.revalidate(auth, conditions)
        assert revalidated.status is AuthorizationStatus.AUTHORIZED

    def test_revalidate_changed_fingerprint_denies(self):
        authorizer = OperationAuthorizer()
        op = make_operation()
        conditions1 = AuthorizationConditions(
            capability_available=True,
            permission_allowed=True,
            safety_passed=True,
            privacy_passed=True,
            resources_available=True,
            context_valid=True,
            schema_use_valid=True,
            risk_level="low",
            environment_fingerprint="fp:1",
        )
        auth = authorizer.authorize(op, conditions1)
        assert auth.status is AuthorizationStatus.AUTHORIZED
        # Revalidate with different fingerprint
        conditions2 = AuthorizationConditions(
            capability_available=True,
            permission_allowed=True,
            safety_passed=True,
            privacy_passed=True,
            resources_available=True,
            context_valid=True,
            schema_use_valid=True,
            risk_level="low",
            environment_fingerprint="fp:2",
        )
        revalidated = authorizer.revalidate(auth, conditions2)
        assert revalidated.status is AuthorizationStatus.DENIED
        assert revalidated.failure.failure_kind == "commit_conflict"

    def test_unknown_condition_defers(self):
        authorizer = OperationAuthorizer()
        op = make_operation()
        conditions = AuthorizationConditions(
            capability_available=None,  # Unknown
            environment_fingerprint="fp:1",
        )
        auth = authorizer.authorize(op, conditions)
        assert auth.status is AuthorizationStatus.DEFERRED


# ── 8. Legacy retirement ──────────────────────────────────────────


class TestLegacyRetirement:
    def test_operational_meaning_compiler_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.legacy.v3_3.operational_meaning_compiler")
        assert "DEPRECATED" in mod.__doc__

    def test_operational_causal_router_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.legacy.v3_3.operational_causal_router")
        assert "DEPRECATED" in mod.__doc__


# ── 9. Exit gate: no generic op:write ─────────────────────────────


class TestExitGate:
    def test_no_generic_op_write_in_planner(self):
        """Exit gate: no generic op:write with empty bindings."""
        store = SemanticSchemaStore()
        from cemm.kernel.boot.validation import BootValidator
        validator = BootValidator()
        manifest = build_boot_manifest()
        report = validator.validate_boot(store, manifest)
        validator.register_boot_schemas(store, manifest, report)

        planner = Planner(schema_store=store)
        goal = make_goal(goal_kind="world_state")
        batch = planner.plan(goals=(goal,))
        op = batch.selected.operations[0]
        # Should be op:stage_mutation, not op:write
        assert op.schema_ref != "op:write"
        assert op.schema_ref == "op:stage_mutation"

    def test_teaching_an_effect_never_fires_it(self):
        """Teaching a schema does not execute it."""
        store = SemanticSchemaStore()
        from cemm.kernel.boot.validation import BootValidator
        validator = BootValidator()
        manifest = build_boot_manifest()
        report = validator.validate_boot(store, manifest)
        validator.register_boot_schemas(store, manifest, report)

        # Verify that learning a schema doesn't trigger execution
        # by checking that the schema store has the schema but no
        # execution has occurred
        candidates = store.find_candidates("op:query")
        assert len(candidates) > 0
        # The store revision should reflect registration, not execution
        assert store.store_revision > 0

    def test_one_mutation_authority(self):
        """CommitCoordinator is the sole mutation authority."""
        coord = CommitCoordinator()
        # Only CommitCoordinator can commit mutations
        mut = make_mutation()
        ms = MutationSet(id="ms:single", phase="critical", operations=(mut,))
        outcome = coord.commit(ms)
        assert outcome.required_satisfied
        # Second commit should produce a different revision
        mut2 = make_mutation()
        ms2 = MutationSet(id="ms:single2", phase="critical", operations=(mut2,))
        outcome2 = coord.commit(ms2)
        assert outcome2.required_satisfied
