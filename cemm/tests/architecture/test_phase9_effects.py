"""Phase 9 gate tests: Live effects, causality, and commit correctness.

Gates (from IMPLEMENTATION_PLAN.md Phase 9):
- teaching a causal/effect schema fires no effect;
- prediction differs from observation/commit;
- auxiliary schema/concept writes cannot satisfy requested relation writes;
- completion claims require exact required commits.

Additional guardrail tests from AGENTS.md §7.7, SEMANTIC_FOUNDATIONS.md §10,
ACCEPTANCE_TESTS.md §35-37, ADR-20, AUTHORITY_MATRIX:
- Schema grounding permits interpretation/prediction/simulation/proposal only
- Schema grounding never grants execution/commit authority
- Live authorization revalidation before irreversible/critical commit
- Planning success is not execution success
- OperationAuthorizer is the sole authorization authority
- CommitCoordinator is the sole persistent-mutation authority
- Fallback success is forbidden
- Import boundaries: execution → model only
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from cemm.kernel.execution.causal_warrant import (
    CausalWarrantGrade, EffectCapability, CausalWarrantAssessment,
    CausalWarrantEvaluator,
    SCHEMA_LEVEL_CAPABILITIES, LIVE_AUTHORITY_CAPABILITIES,
)
from cemm.kernel.execution.authorizer import (
    OperationAuthorizer, AuthorizationResult, AuthorizationStatus,
    AuthorizationConditions,
)
from cemm.kernel.execution.reconciliation import (
    OutcomeReconciler, ReconciliationResult,
)
from cemm.kernel.execution.commit import (
    CommitCoordinator, WriteContractGuard, ValidationResult,
)
from cemm.kernel.model.plan import (
    OperationInstance, PlanRecord, CostEstimate, RiskEstimate,
)
from cemm.kernel.model.execution import (
    OperationOutcome, ExecutionLedger, PredictionError, TypedFailure,
)
from cemm.kernel.model.mutation import (
    MutationSet, MutationOperation, CommitOutcome, CommitOperationResult,
)
from cemm.kernel.model.identity import SemanticIdentity, Permission


# ── Helpers ────────────────────────────────────────────────────────


def make_operation(
    op_id: str = "op:1",
    predicted_effects: tuple[str, ...] = ("effect:1",),
) -> OperationInstance:
    return OperationInstance(
        id=op_id,
        schema_ref="op_schema:1",
        predicted_effect_refs=predicted_effects,
    )


def make_plan(
    plan_id: str = "plan:1",
    operations: tuple[OperationInstance, ...] = (),
) -> PlanRecord:
    return PlanRecord(
        id=plan_id,
        operations=operations,
    )


def make_mutation(
    mid: str = "mut:1",
    required: bool = True,
    action: str = "create",
    identity: SemanticIdentity | None = None,
    evidence_refs: tuple[str, ...] = ("ev:1",),
) -> MutationOperation:
    return MutationOperation(
        id=mid,
        required=required,
        action=action,
        semantic_identity=identity,
        evidence_refs=evidence_refs,
    )


# ── Gate 1: teaching a causal/effect schema fires no effect ──


def test_teaching_causal_schema_fires_no_effect():
    """Teaching a causal/effect schema fires no effect."""
    evaluator = CausalWarrantEvaluator()

    # Teach a causal claim: "Pressing this button causes shutdown"
    assessment = evaluator.assess_warrant(
        proposition_ref="prop:causal:button_shutdown",
        grade=CausalWarrantGrade.REPORTED_CLAIM,
        is_taught=True,
    )

    # Teaching alone never fires an effect
    assert assessment.is_schema_level_only
    assert assessment.intervention_blocked
    assert not assessment.policy_allows_intervention


def test_teaching_alone_never_executes():
    """Teaching alone never fires shutdown (or any other effect)."""
    evaluator = CausalWarrantEvaluator()

    # Even with the highest warrant grade, teaching doesn't execute
    assessment = evaluator.assess_warrant(
        proposition_ref="prop:causal:shutdown",
        grade=CausalWarrantGrade.INTERVENTION_SUPPORTED,
        is_taught=True,
    )

    # Cannot execute without live authorization
    assert not evaluator.can_execute(assessment, live_authorization=False)


def test_schema_permits_interpret_but_not_execution():
    """Schema grounding permits interpretation but not execution."""
    evaluator = CausalWarrantEvaluator()
    assessment = evaluator.assess_warrant(
        proposition_ref="prop:causal:1",
        grade=CausalWarrantGrade.MECHANISM_SUPPORTED,
        is_taught=True,
    )

    # Schema permits interpretation, prediction, simulation, proposal
    assert evaluator.can_interpret(assessment)
    assert evaluator.can_predict(assessment)
    assert evaluator.can_simulate(assessment)
    assert evaluator.can_propose(assessment)

    # Schema does NOT permit authorization, execution, or commit
    assert not evaluator.can_authorize(assessment, live_authorization=False)
    assert not evaluator.can_execute(assessment, live_authorization=False)


def test_schema_level_capabilities_excluded_from_live_authority():
    """Schema-level capabilities are separate from live-authority capabilities."""
    assert EffectCapability.AUTHORIZE not in SCHEMA_LEVEL_CAPABILITIES
    assert EffectCapability.EXECUTE not in SCHEMA_LEVEL_CAPABILITIES
    assert EffectCapability.COMMIT not in SCHEMA_LEVEL_CAPABILITIES

    assert EffectCapability.AUTHORIZE in LIVE_AUTHORITY_CAPABILITIES
    assert EffectCapability.EXECUTE in LIVE_AUTHORITY_CAPABILITIES
    assert EffectCapability.COMMIT in LIVE_AUTHORITY_CAPABILITIES


def test_intervention_blocked_until_required_grade():
    """Intervention planning blocked until required evidence grade/policy."""
    evaluator = CausalWarrantEvaluator()

    # Low warrant grade — intervention blocked
    assessment = evaluator.assess_warrant(
        proposition_ref="prop:causal:1",
        grade=CausalWarrantGrade.REPORTED_CLAIM,
        is_taught=True,
    )

    ready, reason = evaluator.check_intervention_readiness(
        assessment, live_authorization=True, policy_allows=True,
    )
    assert not ready
    assert "insufficient" in reason or "blocked" in reason


def test_intervention_ready_with_high_grade_and_live_auth():
    """Intervention ready with sufficient grade + live authorization + policy."""
    evaluator = CausalWarrantEvaluator()

    assessment = CausalWarrantAssessment(
        proposition_ref="prop:causal:1",
        grade=CausalWarrantGrade.INTERVENTION_SUPPORTED,
        is_schema_level_only=True,
        intervention_blocked=False,  # Unblocked by live authorization
        required_grade_for_intervention=CausalWarrantGrade.INTERVENTION_SUPPORTED,
        policy_allows_intervention=True,
    )

    ready, reason = evaluator.check_intervention_readiness(
        assessment, live_authorization=True, policy_allows=True,
    )
    assert ready
    assert reason == ""


def test_causal_warrant_grade_ordering():
    """Causal warrant grades are ordered by strength."""
    assert CausalWarrantGrade.REPORTED_CLAIM.strength < CausalWarrantGrade.INTERVENTION_SUPPORTED.strength
    assert CausalWarrantGrade.MECHANISM_SUPPORTED.is_sufficient_for(CausalWarrantGrade.PREDICTIVE_ASSOCIATION)
    assert not CausalWarrantGrade.REPORTED_CLAIM.is_sufficient_for(CausalWarrantGrade.INTERVENTION_SUPPORTED)


# ── Gate 2: prediction differs from observation/commit ──


def test_prediction_differs_from_observation():
    """Prediction differs from observation/commit."""
    reconciler = OutcomeReconciler()

    op = make_operation("op:1", predicted_effects=("effect:A", "effect:B"))
    plan = make_plan("plan:1", operations=(op,))

    # Observed only effect:A, not effect:B
    ledger = ExecutionLedger(
        plan_ref="plan:1",
        outcomes=(
            OperationOutcome(
                operation_ref="op:1",
                status="succeeded",
                observed_effect_refs=("effect:A",),
            ),
        ),
    )

    result = reconciler.reconcile(plan, ledger)

    # effect:B was predicted but not observed
    assert "effect:B" in result.unconfirmed_effect_refs
    # effect:A was both predicted and observed
    assert "effect:A" in result.confirmed_effect_refs


def test_unexpected_observation():
    """Unexpected observations are prediction errors."""
    reconciler = OutcomeReconciler()

    op = make_operation("op:1", predicted_effects=("effect:A",))
    plan = make_plan("plan:1", operations=(op,))

    # Observed effect:A AND effect:C (unexpected)
    ledger = ExecutionLedger(
        plan_ref="plan:1",
        outcomes=(
            OperationOutcome(
                operation_ref="op:1",
                status="succeeded",
                observed_effect_refs=("effect:A", "effect:C"),
            ),
        ),
    )

    result = reconciler.reconcile(plan, ledger)

    assert "effect:C" in result.unexpected_effect_refs
    assert len(result.prediction_errors) > 0


def test_planning_success_is_not_execution_success():
    """Planning success is not execution success."""
    reconciler = OutcomeReconciler()

    # Plan with no rejected reasons → planning success
    plan = make_plan("plan:1", operations=(make_operation(),))

    # But operation failed
    ledger = ExecutionLedger(
        plan_ref="plan:1",
        outcomes=(
            OperationOutcome(
                operation_ref="op:1",
                status="failed",
                failure=TypedFailure(failure_kind="execution_failed"),
            ),
        ),
    )

    result = reconciler.reconcile(plan, ledger)

    assert result.planning_success  # Plan was created
    assert not result.execution_success  # But execution failed


def test_execution_success_requires_all_succeeded():
    """Execution success requires all operations succeeded."""
    reconciler = OutcomeReconciler()

    plan = make_plan("plan:1", operations=(make_operation("op:1"), make_operation("op:2")))
    ledger = ExecutionLedger(
        plan_ref="plan:1",
        outcomes=(
            OperationOutcome(operation_ref="op:1", status="succeeded"),
            OperationOutcome(operation_ref="op:2", status="succeeded"),
        ),
    )

    result = reconciler.reconcile(plan, ledger)
    assert result.execution_success


def test_reconcile_single_operation_confirmed():
    """Reconcile a single operation — confirmed when predicted == observed."""
    reconciler = OutcomeReconciler()

    op = make_operation("op:1", predicted_effects=("effect:A",))
    outcome = OperationOutcome(
        operation_ref="op:1",
        status="succeeded",
        observed_effect_refs=("effect:A",),
    )

    confirmed, error = reconciler.reconcile_operation(op, outcome)
    assert confirmed
    assert error is None


def test_reconcile_single_operation_unconfirmed():
    """Reconcile a single operation — unconfirmed when predicted != observed."""
    reconciler = OutcomeReconciler()

    op = make_operation("op:1", predicted_effects=("effect:A", "effect:B"))
    outcome = OperationOutcome(
        operation_ref="op:1",
        status="succeeded",
        observed_effect_refs=("effect:A",),
    )

    confirmed, error = reconciler.reconcile_operation(op, outcome)
    assert not confirmed
    assert error is not None
    assert error.error_kind == "unconfirmed_prediction"


# ── Gate 3: auxiliary writes cannot satisfy requested relation writes ──


def test_auxiliary_writes_cannot_satisfy_required_writes():
    """Auxiliary schema/concept writes cannot satisfy requested relation writes."""
    guard = WriteContractGuard()

    # Mutation set with only auxiliary operations (no required)
    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            make_mutation("mut:aux:1", required=False),
        ),
    )

    result = guard.check_write_contract(mut_set)
    assert not result.is_valid
    assert any(f.failure_kind == "no_required_writes" for f in result.failures)


def test_identity_match_required():
    """Write contract checks semantic identity match."""
    guard = WriteContractGuard()

    requested_identity = SemanticIdentity(identity_kind="relation", key="knows")
    matching_op = make_mutation(
        "mut:1",
        identity=SemanticIdentity(identity_kind="relation", key="knows"),
    )
    non_matching_op = make_mutation(
        "mut:2",
        identity=SemanticIdentity(identity_kind="concept", key="person"),
    )

    assert guard.check_identity_match(matching_op, requested_identity)
    assert not guard.check_identity_match(non_matching_op, requested_identity)


def test_auxiliary_concept_write_does_not_satisfy_relation_write():
    """A concept write cannot satisfy a relation write — different identity."""
    guard = WriteContractGuard()

    relation_identity = SemanticIdentity(identity_kind="relation", key="knows")
    concept_op = make_mutation(
        "mut:1",
        identity=SemanticIdentity(identity_kind="concept", key="person"),
    )

    assert not guard.check_identity_match(concept_op, relation_identity)


# ── Gate 4: completion claims require exact required commits ──


def test_completion_requires_all_required_committed():
    """Completion claims require exact required commits."""
    coordinator = CommitCoordinator()

    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            make_mutation("mut:req:1", required=True),
            make_mutation("mut:req:2", required=True),
        ),
    )

    # Only one required operation committed
    outcome = CommitOutcome(
        mutation_set_ref="ms:1",
        results=(
            CommitOperationResult(mutation_ref="mut:req:1", status="committed"),
            CommitOperationResult(mutation_ref="mut:req:2", status="failed",
                                  failure=TypedFailure(failure_kind="execution_failed")),
        ),
        required_satisfied=False,
    )

    completed, reason = coordinator.check_completion(mut_set, outcome)
    assert not completed
    assert "mut:req:2" in reason


def test_completion_satisfied_when_all_required_committed():
    """Completion satisfied when all required operations committed."""
    coordinator = CommitCoordinator()

    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            make_mutation("mut:req:1", required=True),
            make_mutation("mut:aux:1", required=False),
        ),
    )

    outcome = CommitOutcome(
        mutation_set_ref="ms:1",
        results=(
            CommitOperationResult(mutation_ref="mut:req:1", status="committed"),
            CommitOperationResult(mutation_ref="mut:aux:1", status="committed"),
        ),
        required_satisfied=True,
    )

    completed, reason = coordinator.check_completion(mut_set, outcome)
    assert completed


def test_any_patch_committed_does_not_satisfy_required():
    """Confirming a write because any patch committed is forbidden."""
    guard = WriteContractGuard()

    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            make_mutation("mut:req:1", required=True),
            make_mutation("mut:aux:1", required=False),
        ),
    )

    # Only auxiliary committed, required failed
    outcome = CommitOutcome(
        mutation_set_ref="ms:1",
        results=(
            CommitOperationResult(mutation_ref="mut:req:1", status="failed",
                                  failure=TypedFailure(failure_kind="execution_failed")),
            CommitOperationResult(mutation_ref="mut:aux:1", status="committed"),
        ),
        required_satisfied=False,
    )

    completed, reason = guard.check_completion(mut_set, outcome)
    assert not completed
    assert "mut:req:1" in reason


# ── OperationAuthorizer tests ──


def test_authorizer_grants_with_all_conditions():
    """OperationAuthorizer grants when all conditions pass."""
    authorizer = OperationAuthorizer()
    op = make_operation()
    conditions = AuthorizationConditions(
        permission_allowed=True,
        safety_passed=True,
        privacy_passed=True,
        capability_available=True,
        resources_available=True,
        context_valid=True,
        schema_use_valid=True,
        risk_level="low",
        risk_threshold="medium",
        environment_fingerprint="fp:v1",
    )

    result = authorizer.authorize(op, conditions)
    assert result.status == AuthorizationStatus.AUTHORIZED
    assert result.revalidation_required


def test_authorizer_denies_on_permission_blocked():
    """OperationAuthorizer denies when permission is blocked."""
    authorizer = OperationAuthorizer()
    op = make_operation()
    conditions = AuthorizationConditions(permission_allowed=False)

    result = authorizer.authorize(op, conditions)
    assert result.status == AuthorizationStatus.DENIED
    assert result.failure.failure_kind == "permission_blocked"


def test_authorizer_denies_on_capability_unavailable():
    """OperationAuthorizer denies when capability is unavailable."""
    authorizer = OperationAuthorizer()
    op = make_operation()
    conditions = AuthorizationConditions(
        permission_allowed=True,
        safety_passed=True,
        privacy_passed=True,
        capability_available=False,
        resources_available=True,
        context_valid=True,
        schema_use_valid=True,
        risk_level="low",
    )

    result = authorizer.authorize(op, conditions)
    assert result.status == AuthorizationStatus.DENIED
    assert result.failure.failure_kind == "capability_unavailable"


def test_authorizer_denies_on_safety_violation():
    """OperationAuthorizer denies when safety check fails."""
    authorizer = OperationAuthorizer()
    op = make_operation()
    conditions = AuthorizationConditions(
        permission_allowed=True,
        safety_passed=False,
        privacy_passed=True,
        capability_available=True,
        resources_available=True,
        context_valid=True,
        schema_use_valid=True,
        risk_level="low",
    )

    result = authorizer.authorize(op, conditions)
    assert result.status == AuthorizationStatus.DENIED
    assert result.failure.failure_kind == "safety_violation"


def test_authorizer_denies_on_risk_exceeded():
    """OperationAuthorizer denies when risk exceeds threshold."""
    authorizer = OperationAuthorizer()
    op = make_operation()
    conditions = AuthorizationConditions(
        permission_allowed=True,
        safety_passed=True,
        privacy_passed=True,
        capability_available=True,
        resources_available=True,
        context_valid=True,
        schema_use_valid=True,
        risk_level="high",
        risk_threshold="low",
    )

    result = authorizer.authorize(op, conditions)
    assert result.status == AuthorizationStatus.DENIED
    assert result.failure.failure_kind == "risk_exceeded"


def _full_conditions(**overrides) -> AuthorizationConditions:
    """Return AuthorizationConditions with all gates True, plus overrides."""
    defaults = dict(
        permission_allowed=True,
        safety_passed=True,
        privacy_passed=True,
        capability_available=True,
        resources_available=True,
        context_valid=True,
        schema_use_valid=True,
        risk_level="low",
    )
    defaults.update(overrides)
    return AuthorizationConditions(**defaults)


def test_authorizer_revalidation_fingerprint_change():
    """Authorization is revalidated before irreversible execution and critical commit.
    Fingerprint change blocks revalidation."""
    authorizer = OperationAuthorizer()
    op = make_operation()

    # Original authorization
    conditions = _full_conditions(environment_fingerprint="fp:v1")
    original = authorizer.authorize(op, conditions)
    assert original.status == AuthorizationStatus.AUTHORIZED

    # Revalidation with changed fingerprint
    new_conditions = _full_conditions(environment_fingerprint="fp:v2")
    revalidated = authorizer.revalidate(original, new_conditions)
    assert revalidated.status == AuthorizationStatus.DENIED
    assert revalidated.failure.failure_kind == "commit_conflict"


def test_authorizer_revalidation_same_fingerprint():
    """Revalidation with same fingerprint re-checks all conditions."""
    authorizer = OperationAuthorizer()
    op = make_operation()

    conditions = _full_conditions(environment_fingerprint="fp:v1")
    original = authorizer.authorize(op, conditions)
    assert original.status == AuthorizationStatus.AUTHORIZED

    # Revalidation with same fingerprint but conditions still pass
    revalidated = authorizer.revalidate(original, conditions)
    assert revalidated.status == AuthorizationStatus.AUTHORIZED


def test_authorizer_revalidation_permission_revoked():
    """Revalidation catches permission revocation."""
    authorizer = OperationAuthorizer()
    op = make_operation()

    conditions = _full_conditions(environment_fingerprint="fp:v1")
    original = authorizer.authorize(op, conditions)
    assert original.status == AuthorizationStatus.AUTHORIZED

    # Permission revoked during revalidation
    new_conditions = _full_conditions(environment_fingerprint="fp:v1", permission_allowed=False)
    revalidated = authorizer.revalidate(original, new_conditions)
    assert revalidated.status == AuthorizationStatus.DENIED


# ── CommitCoordinator tests ──


def test_commit_coordinator_atomic_commit():
    """CommitCoordinator commits atomically — all or nothing."""
    coordinator = CommitCoordinator()

    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            make_mutation("mut:1", required=True),
            make_mutation("mut:2", required=True),
        ),
    )

    outcome = coordinator.commit(mut_set)
    assert outcome.required_satisfied
    assert all(r.status == "committed" for r in outcome.results)
    assert outcome.committed_revision is not None


def test_commit_coordinator_validation_failure():
    """CommitCoordinator validates before commit — missing evidence fails."""
    coordinator = CommitCoordinator()

    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            MutationOperation(
                id="mut:1",
                required=True,
                evidence_refs=(),  # No evidence!
            ),
        ),
    )

    outcome = coordinator.commit(mut_set)
    assert not outcome.required_satisfied
    assert all(r.status == "failed" for r in outcome.results)


def test_commit_coordinator_critical_requires_required():
    """Critical commit requires at least one required operation."""
    coordinator = CommitCoordinator()

    mut_set = MutationSet(
        id="ms:1",
        phase="critical",
        operations=(
            make_mutation("mut:1", required=False),
        ),
    )

    outcome = coordinator.commit(mut_set)
    assert not outcome.required_satisfied


def test_commit_coordinator_no_fallback_success():
    """CommitCoordinator never uses fallback success."""
    coordinator = CommitCoordinator()

    # Empty mutation set
    mut_set = MutationSet(id="ms:1", phase="critical")

    outcome = coordinator.commit(mut_set)
    assert not outcome.required_satisfied
    assert outcome.committed_revision is None


# ── Import boundary tests ──


def test_phase9_imports_no_engine():
    """Phase 9 execution modules must not import any engine module."""
    import cemm.kernel.execution.causal_warrant as cw_mod
    import cemm.kernel.execution.authorizer as au_mod
    import cemm.kernel.execution.reconciliation as rc_mod
    import cemm.kernel.execution.commit as co_mod

    forbidden = [
        "cemm.legacy.v3_3.semantic_kernel_runtime",
        "cemm.legacy.v3_3.meaning_perceptor",
        "cemm.legacy.v3_3.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    for mod in [cw_mod, au_mod, rc_mod, co_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_execution_does_not_import_schema():
    """Execution modules must not import schema submodules.

    Execution is downstream of schema — it uses model records only.
    The authorizer checks schema_use_valid as a boolean condition,
    but does not import the schema store.
    """
    import cemm.kernel.execution.causal_warrant as cw_mod
    import cemm.kernel.execution.authorizer as au_mod
    import cemm.kernel.execution.reconciliation as rc_mod
    import cemm.kernel.execution.commit as co_mod

    forbidden_schema = [
        "from ..schema.",
        "from cemm.kernel.schema.",
    ]
    for mod in [cw_mod, au_mod, rc_mod, co_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden_schema:
            assert f not in source, f"{mod.__file__} imports forbidden schema module {f}"
