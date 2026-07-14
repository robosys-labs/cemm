"""Tests for v3.4 canonical components built for the full cutover.

Tests each new component independently:
- GapDetector
- InterpretationResolver (v3.4)
- WorkspaceController
- SemanticRetriever
- GoalArbiter
- Planner (v3.4)
- OperationExecutor (v3.4)
"""
from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import Any


# ── Test fixtures ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MockGroundingAssessment:
    referent_ref: str = "ref:unknown:test"
    is_unknown: bool = True
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class MockEpistemicAssessment:
    proposition_ref: str = "prop:test1"
    admissibility: str = "blocked"
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class MockCapabilityAssessment:
    is_capable: bool = False
    limitations: tuple[str, ...] = ("missing_competence",)


@dataclass(frozen=True, slots=True)
class MockOpenPort:
    role_name: str = "agent"
    role_schema_ref: str = ""


@dataclass(frozen=True, slots=True)
class MockCandidateGraph:
    open_ports: tuple[Any, ...] = ()
    opaque_lexeme_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MockSelectedInterpretation:
    id: str = "interp:test1"
    proposition_ref: str = "prop:test1"
    confidence: float = 0.8
    is_opaque: bool = False
    is_provisional: bool = False


@dataclass(frozen=True, slots=True)
class MockGap:
    id: str = "gap:test1"
    learnable: bool = True
    blocked_stage: str = "ground"


@dataclass(frozen=True, slots=True)
class MockGoal:
    id: str = "goal:test1"
    goal_kind: str = "information_state"
    priority: float = 0.8
    urgency: float = 0.7


@dataclass(frozen=True, slots=True)
class MockCommunicativeForce:
    force: str = "ask"
    target_proposition_ref: str = "prop:test1"


@dataclass(frozen=True, slots=True)
class MockPlan:
    id: str = "plan:test1"
    goal_refs: tuple[str, ...] = ("goal:test1",)
    operations: tuple[Any, ...] = ()
    rejected_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MockOperation:
    id: str = "op:test1"
    schema_ref: str = "op:query"
    status: str = "pending"
    predicted_effect_refs: tuple[str, ...] = ()
    bindings: tuple = ()
    idempotency_key: str = ""


# ── GapDetector tests ──


class TestGapDetector:
    def test_detect_unknown_referent_creates_gap(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        detector = GapDetector()
        result = detector.detect(
            grounding_assessments=[MockGroundingAssessment(is_unknown=True)],
        )
        assert result.gap_count > 0
        assert any(g.gap_kind == "missing_semantic_family" for g in result.gaps)

    def test_detect_blocked_admissibility_creates_gap(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        detector = GapDetector()
        result = detector.detect(
            epistemic_assessments=[MockEpistemicAssessment(admissibility="blocked")],
        )
        assert any(g.gap_kind == "actual_context_not_admitted" for g in result.gaps)

    def test_detect_open_ports_create_gaps(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        detector = GapDetector()
        result = detector.detect(
            candidate_graph=MockCandidateGraph(
                open_ports=(MockOpenPort(role_name="agent"),),
            ),
        )
        assert any(g.gap_kind == "missing_required_role" for g in result.gaps)

    def test_detect_opaque_lexemes_create_gaps(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        detector = GapDetector()
        result = detector.detect(
            candidate_graph=MockCandidateGraph(
                opaque_lexeme_refs=("opaque:engineer:abc",),
            ),
        )
        assert any(g.gap_kind == "sense_individuation_pending" for g in result.gaps)

    def test_detect_missing_competence_creates_gap(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        detector = GapDetector()
        result = detector.detect(
            capability_assessment=MockCapabilityAssessment(is_capable=False),
        )
        assert any(g.gap_kind == "missing_independent_competence" for g in result.gaps)

    def test_no_gaps_when_all_clear(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        detector = GapDetector()
        result = detector.detect(
            grounding_assessments=[MockGroundingAssessment(is_unknown=False)],
            epistemic_assessments=[MockEpistemicAssessment(admissibility="admitted")],
        )
        assert result.gap_count == 0

    def test_blocking_classification(self):
        from cemm.kernel.understanding.gap_detector import GapDetector
        from cemm.kernel.model.gap import GapRecord
        detector = GapDetector()
        gaps = (
            GapRecord(id="g1", gap_kind="missing_semantic_family", target_artifact_ref="ref1", blocked_stage="ground"),
            GapRecord(id="g2", gap_kind="stale_assessment", target_artifact_ref="ref2", blocked_stage="know"),
        )
        blocking = detector.classify_blocking(gaps, {"ref1"})
        assert any(g.id == "g1" for g in blocking)


# ── InterpretationResolver tests ──


class TestInterpretationResolver:
    def test_empty_graph_returns_empty(self):
        from cemm.kernel.understanding.interpreter import InterpretationResolver
        from cemm.kernel.understanding.candidate_graph import CandidateGraph
        resolver = InterpretationResolver()
        result = resolver.resolve(CandidateGraph())
        assert not result.has_selection
        assert result.selected_count == 0

    def test_selects_best_proposition(self):
        from cemm.kernel.understanding.interpreter import InterpretationResolver
        from cemm.kernel.understanding.candidate_graph import (
            CandidateGraph, CandidateProposition, CandidateCommunicativeForce,
        )
        from cemm.kernel.model.proposition import Proposition

        prop1 = Proposition(id="prop1", predication_ref="pred1", context_ref="ctx1")
        prop2 = Proposition(id="prop2", predication_ref="pred2", context_ref="ctx1")

        graph = CandidateGraph(
            candidate_propositions=(
                CandidateProposition(proposition=prop1, confidence=0.3),
                CandidateProposition(proposition=prop2, confidence=0.8),
            ),
            candidate_communicative_forces=(
                CandidateCommunicativeForce(force="assert", target_proposition_ref="prop2", confidence=0.9),
            ),
        )

        resolver = InterpretationResolver()
        result = resolver.resolve(graph)
        assert result.has_selection
        assert result.primary is not None
        assert result.primary.proposition_ref == "prop2"

    def test_rejects_lower_confidence_alternatives(self):
        from cemm.kernel.understanding.interpreter import InterpretationResolver
        from cemm.kernel.understanding.candidate_graph import (
            CandidateGraph, CandidateProposition, CandidateCommunicativeForce,
        )
        from cemm.kernel.model.proposition import Proposition

        prop1 = Proposition(id="prop1", predication_ref="pred1", context_ref="ctx1")
        prop2 = Proposition(id="prop2", predication_ref="pred2", context_ref="ctx1")

        graph = CandidateGraph(
            candidate_propositions=(
                CandidateProposition(proposition=prop1, confidence=0.2),
                CandidateProposition(proposition=prop2, confidence=0.9),
            ),
            candidate_communicative_forces=(
                CandidateCommunicativeForce(force="ask", target_proposition_ref=""),
            ),
        )

        resolver = InterpretationResolver()
        result = resolver.resolve(graph)
        assert len(result.rejected) > 0

    def test_provisional_from_attributed_admissibility(self):
        from cemm.kernel.understanding.interpreter import InterpretationResolver
        from cemm.kernel.understanding.candidate_graph import (
            CandidateGraph, CandidateProposition,
        )
        from cemm.kernel.model.proposition import Proposition

        prop = Proposition(id="prop1", predication_ref="pred1", context_ref="ctx1")
        graph = CandidateGraph(
            candidate_propositions=(
                CandidateProposition(proposition=prop, confidence=0.5),
            ),
        )

        @dataclass(frozen=True, slots=True)
        class MockEA:
            proposition_ref: str = "prop1"
            admissibility: str = "attributed_only"
            confidence: float = 0.3

        resolver = InterpretationResolver()
        result = resolver.resolve(graph, epistemic_assessments=[MockEA()])
        assert result.primary is not None
        assert result.primary.is_provisional


# ── WorkspaceController tests ──


class TestWorkspaceController:
    def test_empty_workspace(self):
        from cemm.kernel.understanding.workspace import WorkspaceController
        controller = WorkspaceController()
        snapshot = controller.focus()
        assert snapshot.is_empty

    def test_focus_with_interpretations(self):
        from cemm.kernel.understanding.workspace import WorkspaceController
        controller = WorkspaceController()
        snapshot = controller.focus(
            selected_interpretations=[MockSelectedInterpretation(confidence=0.9)],
        )
        assert not snapshot.is_empty
        assert snapshot.bounded_size == 1

    def test_focus_with_gaps_high_urgency(self):
        from cemm.kernel.understanding.workspace import WorkspaceController
        controller = WorkspaceController()
        snapshot = controller.focus(
            gaps=[MockGap(learnable=True)],
        )
        assert not snapshot.is_empty
        gap_entry = [e for e in snapshot.entries if e.item_kind == "gap"]
        assert len(gap_entry) == 1
        assert gap_entry[0].urgency > 0.5

    def test_focus_bounds_entries(self):
        from cemm.kernel.understanding.workspace import WorkspaceController
        controller = WorkspaceController(max_entries=2)
        interps = [MockSelectedInterpretation(id=f"interp:{i}", proposition_ref=f"prop:{i}") for i in range(10)]
        snapshot = controller.focus(selected_interpretations=interps)
        assert snapshot.bounded_size == 2

    def test_focus_weights_sum_to_one(self):
        from cemm.kernel.understanding.workspace import WorkspaceController
        controller = WorkspaceController()
        snapshot = controller.focus(
            selected_interpretations=[
                MockSelectedInterpretation(id="i1", proposition_ref="p1", confidence=0.9),
                MockSelectedInterpretation(id="i2", proposition_ref="p2", confidence=0.5),
            ],
        )
        if snapshot.focus_weights:
            total = sum(snapshot.focus_weights.values())
            assert 0.99 <= total <= 1.01


# ── SemanticRetriever tests ──


class TestSemanticRetriever:
    def test_empty_store_returns_empty(self):
        from cemm.kernel.epistemics.retriever import SemanticRetriever
        retriever = SemanticRetriever()
        result = retriever.retrieve()
        assert result.is_empty

    def test_retrieve_with_interpretations(self):
        from cemm.kernel.epistemics.retriever import SemanticRetriever
        retriever = SemanticRetriever()
        result = retriever.retrieve(
            selected_interpretations=[MockSelectedInterpretation()],
        )
        # No store, so results are empty
        assert result.is_empty

    def test_retrieve_open_ports(self):
        from cemm.kernel.epistemics.retriever import SemanticRetriever
        retriever = SemanticRetriever(store=object())  # non-None store
        result = retriever.retrieve(
            open_ports=(MockOpenPort(role_name="agent", role_schema_ref="role:agent"),),
        )
        assert len(result.results) == 1
        assert result.results[0].is_empty


# ── GoalArbiter tests ──


class TestGoalArbiter:
    def test_no_goals_when_empty(self):
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        arbiter = GoalArbiter()
        result = arbiter.derive_and_arbitrate()
        assert result.active_count == 0

    def test_ask_force_creates_information_goal(self):
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        arbiter = GoalArbiter()
        result = arbiter.derive_and_arbitrate(
            communicative_forces=(MockCommunicativeForce(force="ask"),),
        )
        assert result.active_count > 0
        assert any(g.goal_kind == "information_state" for g in result.active_goals)

    def test_request_force_creates_world_state_goal(self):
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        arbiter = GoalArbiter()
        result = arbiter.derive_and_arbitrate(
            communicative_forces=(MockCommunicativeForce(force="request"),),
        )
        assert any(g.goal_kind == "world_state" for g in result.active_goals)

    def test_learnable_gap_creates_goal(self):
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        arbiter = GoalArbiter()
        result = arbiter.derive_and_arbitrate(
            gaps=[MockGap(learnable=True)],
        )
        assert any(g.goal_kind == "information_state" for g in result.active_goals)

    def test_primary_goal_is_highest_priority(self):
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        arbiter = GoalArbiter()
        result = arbiter.derive_and_arbitrate(
            communicative_forces=(
                MockCommunicativeForce(force="assert"),
                MockCommunicativeForce(force="correct"),
            ),
        )
        assert result.primary_goal is not None
        assert result.primary_goal.priority >= 0.5


# ── Planner tests ──


class TestPlanner:
    def test_no_plan_when_no_goals(self):
        from cemm.kernel.execution.planner import Planner
        planner = Planner()
        result = planner.plan()
        assert result.plan_count == 0

    def test_plan_for_information_goal(self):
        from cemm.kernel.execution.planner import Planner
        planner = Planner()
        result = planner.plan(goals=(MockGoal(goal_kind="information_state"),))
        assert result.plan_count > 0
        assert result.selected is not None
        assert result.selected.operations[0].schema_ref == "op:query"

    def test_plan_for_world_state_goal(self):
        from cemm.kernel.execution.planner import Planner
        planner = Planner()
        result = planner.plan(goals=(MockGoal(goal_kind="world_state"),))
        assert result.selected.operations[0].schema_ref == "op:stage_mutation"

    def test_plan_rejected_when_not_capable(self):
        from cemm.kernel.execution.planner import Planner
        planner = Planner()
        result = planner.plan(
            goals=(MockGoal(),),
            capability_assessment=MockCapabilityAssessment(is_capable=False),
        )
        assert len(result.rejected) > 0

    def test_plan_score_reflects_priority(self):
        from cemm.kernel.execution.planner import Planner
        planner = Planner()
        high = MockGoal(id="g1", priority=0.9, urgency=0.9)
        low = MockGoal(id="g2", priority=0.1, urgency=0.1)
        result = planner.plan(goals=(low, high))
        assert result.selected.goal_refs == ("g1",)


# ── OperationAuthorizer fail-closed tests (BF-003) ──


class TestAuthorizerFailClosed:
    def test_empty_conditions_never_authorize(self):
        from cemm.kernel.execution.authorizer import OperationAuthorizer, AuthorizationConditions, AuthorizationStatus
        authorizer = OperationAuthorizer()
        op = MockOperation()
        result = authorizer.authorize(op, AuthorizationConditions())
        assert result.status is not AuthorizationStatus.AUTHORIZED

    def test_missing_permission_never_authorizes(self):
        from cemm.kernel.execution.authorizer import OperationAuthorizer, AuthorizationConditions, AuthorizationStatus
        authorizer = OperationAuthorizer()
        op = MockOperation()
        result = authorizer.authorize(op, AuthorizationConditions(
            permission_allowed=None,
            safety_passed=True,
            privacy_passed=True,
            capability_available=True,
            resources_available=True,
            context_valid=True,
            schema_use_valid=True,
            risk_level="low",
        ))
        assert result.status is AuthorizationStatus.DEFERRED

    def test_denied_permission_produces_denied(self):
        from cemm.kernel.execution.authorizer import OperationAuthorizer, AuthorizationConditions, AuthorizationStatus
        authorizer = OperationAuthorizer()
        op = MockOperation()
        result = authorizer.authorize(op, AuthorizationConditions(
            permission_allowed=False,
        ))
        assert result.status is AuthorizationStatus.DENIED

    def test_unknown_risk_never_authorizes(self):
        from cemm.kernel.execution.authorizer import OperationAuthorizer, AuthorizationConditions, AuthorizationStatus
        authorizer = OperationAuthorizer()
        op = MockOperation()
        result = authorizer.authorize(op, AuthorizationConditions(
            permission_allowed=True,
            safety_passed=True,
            privacy_passed=True,
            capability_available=True,
            resources_available=True,
            context_valid=True,
            schema_use_valid=True,
            risk_level="unknown",
        ))
        assert result.status is not AuthorizationStatus.AUTHORIZED

    def test_fully_specified_low_risk_authorizes(self):
        from cemm.kernel.execution.authorizer import OperationAuthorizer, AuthorizationConditions, AuthorizationStatus
        authorizer = OperationAuthorizer()
        op = MockOperation()
        result = authorizer.authorize(op, AuthorizationConditions(
            permission_allowed=True,
            safety_passed=True,
            privacy_passed=True,
            capability_available=True,
            resources_available=True,
            context_valid=True,
            schema_use_valid=True,
            risk_level="low",
        ))
        assert result.status is AuthorizationStatus.AUTHORIZED


# ── OperationExecutor tests ──


class TestOperationExecutor:
    def test_no_plan_returns_failure(self):
        from cemm.kernel.execution.executor import OperationExecutor
        executor = OperationExecutor()
        result = executor.execute(None)
        assert result.failure_detail == "no plan"
        assert not result.succeeded

    def test_execute_authorized_operation(self):
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import AuthorizationResult, AuthorizationStatus, AuthorizationBatch
        executor = OperationExecutor()
        op = MockOperation()
        plan = MockPlan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.AUTHORIZED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.succeeded
        assert result.outcome_count == 1

    def test_execute_unauthorized_fails(self):
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import AuthorizationResult, AuthorizationStatus, AuthorizationBatch
        executor = OperationExecutor()
        op = MockOperation()
        plan = MockPlan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.DENIED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.failed
        assert not result.succeeded

    def test_execute_records_outcome_status(self):
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import AuthorizationResult, AuthorizationStatus, AuthorizationBatch
        executor = OperationExecutor()
        op = MockOperation()
        plan = MockPlan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.AUTHORIZED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.ledger is not None
        assert result.ledger.outcomes[0].status == "succeeded"

    def test_execute_multiple_operations(self):
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import AuthorizationResult, AuthorizationStatus, AuthorizationBatch
        executor = OperationExecutor()
        op1 = MockOperation(id="op1")
        op2 = MockOperation(id="op2")
        plan = MockPlan(operations=(op1, op2))
        auth = AuthorizationBatch(by_operation_ref={
            op1.id: AuthorizationResult(operation_ref=op1.id, status=AuthorizationStatus.AUTHORIZED),
            op2.id: AuthorizationResult(operation_ref=op2.id, status=AuthorizationStatus.AUTHORIZED),
        })
        result = executor.execute(plan, authorization=auth)
        assert result.outcome_count == 2
        assert result.succeeded

    def test_execute_no_authorization_fails_closed(self):
        from cemm.kernel.execution.executor import OperationExecutor
        executor = OperationExecutor()
        plan = MockPlan(operations=(MockOperation(),))
        result = executor.execute(plan, authorization=None)
        assert result.failed
        assert not result.succeeded

    def test_execute_deferred_authorization_fails(self):
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import AuthorizationResult, AuthorizationStatus, AuthorizationBatch
        executor = OperationExecutor()
        op = MockOperation()
        plan = MockPlan(operations=(op,))
        auth = AuthorizationBatch(by_operation_ref={
            op.id: AuthorizationResult(
                operation_ref=op.id,
                status=AuthorizationStatus.DEFERRED,
            )
        })
        result = executor.execute(plan, authorization=auth)
        assert result.failed
        assert not result.succeeded

    def test_execute_auth_for_op_a_does_not_authorize_op_b(self):
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import AuthorizationResult, AuthorizationStatus, AuthorizationBatch
        executor = OperationExecutor()
        op1 = MockOperation(id="op1")
        op2 = MockOperation(id="op2")
        plan = MockPlan(operations=(op1, op2))
        auth = AuthorizationBatch(by_operation_ref={
            op1.id: AuthorizationResult(operation_ref=op1.id, status=AuthorizationStatus.AUTHORIZED),
        })
        result = executor.execute(plan, authorization=auth)
        assert result.failed
        assert result.outcome_count == 2
        statuses = [o.status for o in result.ledger.outcomes]
        assert "succeeded" in statuses
        assert "failed" in statuses


# ── KernelSnapshot pinning tests ──


def test_pin_snapshot_creates_immutable_snapshot():
    """pin_snapshot creates a frozen KernelSnapshot with all revisions."""
    from cemm.kernel.model.cycle import pin_snapshot, KernelSnapshot

    snap = pin_snapshot(
        schema_store_revision=42,
        semantic_memory_revision=7,
        kernel_foundation_version="v3.4",
    )
    assert isinstance(snap, KernelSnapshot)
    assert snap.schema_store_revision == 42
    assert snap.semantic_memory_revision == 7
    assert snap.kernel_foundation_version == "v3.4"


def test_kernel_snapshot_pin_static_method():
    """KernelSnapshot.pin() static method works identically to pin_snapshot()."""
    from cemm.kernel.model.cycle import KernelSnapshot

    snap = KernelSnapshot.pin(schema_store_revision=10)
    assert snap.schema_store_revision == 10


def test_kernel_snapshot_is_frozen():
    """KernelSnapshot is immutable."""
    from cemm.kernel.model.cycle import pin_snapshot

    snap = pin_snapshot(schema_store_revision=1)
    with pytest.raises(Exception):
        snap.schema_store_revision = 2  # type: ignore


def test_kernel_snapshot_fingerprint():
    """KernelSnapshot.fingerprint derives from pinned revisions."""
    from cemm.kernel.model.cycle import pin_snapshot

    snap = pin_snapshot(
        schema_store_revision=5,
        kernel_foundation_version="v3.4",
        grounding_policy_version="gp1",
    )
    fp = snap.fingerprint
    assert fp.schema_store_revision == 5
    assert fp.kernel_foundation_version == "v3.4"
    assert fp.grounding_policy_version == "gp1"


def test_run_turn_pins_snapshot():
    """run_turn pins a KernelSnapshot at ORIENT and stores it on the result."""
    from cemm.kernel.model.cycle import KernelSnapshot
    from cemm.tests.harness import SeededSystem

    system = SeededSystem()
    result = system.run("hello")
    cycle = result.get("cycle")
    assert cycle is not None
    assert cycle.kernel_snapshot is not None
    assert isinstance(cycle.kernel_snapshot, KernelSnapshot)
