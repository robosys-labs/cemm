"""Stage 4 exit gate tests — canonical retrieval and epistemics.

Tests verify:
1. SemanticQueryPattern builds from interpretations, open ports, and goals
2. SemanticRetriever queries schema store and durable store
3. Open ports use role_schema_ref, not role_name
4. Evidence aggregation by lineage works correctly
5. Temporal validity checking works (expired evidence is not fresh)
6. Four-state truth maintenance (supported/refuted/both/neither)
7. Knowledge derivation with 7 conditions
8. Self-reports are evidence-bound (unbacked is realization error)
9. Knowledge assessments and self-reports wired into cycle
10. Capability evaluator requires live records
11. Attributed context stays attributed (not admitted as actual-world)
12. Absence is not falsity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

import pytest

from cemm.kernel.epistemics.query_pattern import (
    SemanticQueryPattern,
    QueryPatternKind,
    EvidencePolicy,
    QueryPatternBuilder,
    ReferentConstraint,
)
from cemm.kernel.epistemics.retriever import (
    SemanticRetriever,
    RetrievalResult,
    RetrievalBatch,
)
from cemm.kernel.epistemics.evaluator import (
    EpistemicEvaluator,
    EvidenceRecord,
    SupportState,
    AdmissibilityLevel,
    KnowledgeAssessment,
)
from cemm.kernel.epistemics.truth_maintenance import (
    TruthMaintenance,
    LineageGraph,
    LineageNode,
)
from cemm.kernel.epistemics.knowledge_derivation import (
    KnowledgeDeriver,
    UnderstandingAssessment,
    BeliefAssessment,
    SelfReport,
)
from cemm.kernel.self_model.self_report import SelfReportBuilder
from cemm.kernel.self_model.capability_evaluator import (
    CapabilityEvaluator,
    CompetenceRecord,
    ImplementationRecord,
    ComponentHealthRecord,
    ChannelRecord,
    ResourceRecord,
    PermissionRecord,
    ContextualPrecondition,
)
from cemm.kernel.model.proposition import Proposition
from cemm.kernel.model.context_frame import ContextFrame
from cemm.kernel.model.identity import TimeExtent
from cemm.kernel.schema.use_profile import (
    SchemaUseProfile,
    UseProfileLevel,
    SemanticOperation,
    ACTIVE_OPERATIONS,
    PARTIAL_OPERATIONS,
    OPAQUE_OPERATIONS,
)


# ── Helpers ───────────────────────────────────────────────────────


def make_proposition(
    prop_id: str = "prop:test",
    predication_ref: str = "pred:test",
) -> Proposition:
    return Proposition(
        id=prop_id,
        predication_ref=predication_ref,
        context_ref="ctx:actual",
    )


def make_context(
    ctx_id: str = "ctx:actual",
    context_kind: str = "actual",
) -> ContextFrame:
    return ContextFrame(id=ctx_id, context_kind=context_kind)


def make_evidence(
    evidence_id: str = "ev:test",
    prop_ref: str = "prop:test",
    supports: bool = True,
    confidence: float = 0.8,
    is_independent: bool = True,
    temporal_validity: TimeExtent | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        proposition_ref=prop_ref,
        supports=supports,
        confidence=confidence,
        is_independent=is_independent,
        temporal_validity=temporal_validity,
    )


@dataclass(frozen=True, slots=True)
class MockInterpretation:
    proposition_ref: str = "prop:test"
    proposition: Any = None
    context_frame: Any = None
    context_ref: str = "ctx:actual"
    operation_schema_ref: str = ""

    def __post_init__(self):
        if self.proposition is None:
            object.__setattr__(self, "proposition", make_proposition())
        if self.context_frame is None:
            object.__setattr__(self, "context_frame", make_context())


@dataclass(frozen=True, slots=True)
class MockOpenPort:
    role_name: str = "agent"
    role_schema_ref: str = "role:agent"


# ── 1. SemanticQueryPattern ───────────────────────────────────────


class TestQueryPatternBuilder:
    def test_build_from_interpretations(self):
        builder = QueryPatternBuilder()
        interp = MockInterpretation()
        patterns = builder.build_from_interpretations([interp])
        assert len(patterns) == 1
        assert patterns[0].pattern_kind == QueryPatternKind.PROPOSITION_LOOKUP
        assert patterns[0].proposition_ref == "prop:test"

    def test_build_from_empty_interpretations(self):
        builder = QueryPatternBuilder()
        patterns = builder.build_from_interpretations(None)
        assert len(patterns) == 0

    def test_build_from_open_ports_uses_role_schema_ref(self):
        builder = QueryPatternBuilder()
        port = MockOpenPort(role_schema_ref="role:agent")
        patterns = builder.build_from_open_ports((port,))
        assert len(patterns) == 1
        assert patterns[0].pattern_kind == QueryPatternKind.OPEN_PORT_FILL
        assert patterns[0].open_port_role_schema_ref == "role:agent"

    def test_open_port_without_role_schema_ref_skipped(self):
        builder = QueryPatternBuilder()
        port = MockOpenPort(role_schema_ref="")
        patterns = builder.build_from_open_ports((port,))
        assert len(patterns) == 0

    def test_build_from_goals(self):
        builder = QueryPatternBuilder()
        patterns = builder.build_from_goals(("goal:1", "goal:2"))
        assert len(patterns) == 2
        assert patterns[0].pattern_kind == QueryPatternKind.GOAL_QUERY
        assert patterns[0].goal_ref == "goal:1"


# ── 2. SemanticRetriever ──────────────────────────────────────────


class TestSemanticRetriever:
    def test_retrieve_with_schema_store(self):
        from cemm.kernel.schema.store import SemanticSchemaStore
        from cemm.kernel.schema.envelope import SchemaEnvelope

        store = SemanticSchemaStore()
        env = SchemaEnvelope(
            record_id="schema:test:v1",
            semantic_key="pred:test",
            schema_kind="PredicateSchema",
        )
        store.register(env)

        retriever = SemanticRetriever(schema_store=store)
        interp = MockInterpretation()
        batch = retriever.retrieve(
            selected_interpretations=[interp],
            schema_store=store,
        )
        assert not batch.is_empty
        assert batch.total_records > 0

    def test_retrieve_empty_without_stores(self):
        retriever = SemanticRetriever()
        batch = retriever.retrieve()
        assert batch.is_empty

    def test_retrieve_open_ports(self):
        retriever = SemanticRetriever()
        port = MockOpenPort(role_schema_ref="role:agent")
        batch = retriever.retrieve(open_ports=(port,))
        assert len(batch.results) == 1
        assert batch.results[0].is_empty

    def test_retrieve_with_truth_maintenance(self):
        tm = TruthMaintenance()
        ev = make_evidence()
        tm.add_evidence(ev)
        retriever = SemanticRetriever(truth_maintenance=tm)
        interp = MockInterpretation()
        batch = retriever.retrieve(
            selected_interpretations=[interp],
        )
        # Should have evidence refs from truth maintenance
        assert any(r.evidence_refs for r in batch.results)


# ── 3. Evidence aggregation by lineage ────────────────────────────


class TestEvidenceLineage:
    def test_lineage_independent_count(self):
        tm = TruthMaintenance()
        ev1 = make_evidence("ev:1", is_independent=True)
        ev2 = make_evidence("ev:2", is_independent=True)
        ev3 = make_evidence("ev:3", is_independent=False)
        count = tm.check_lineage_independence((ev1, ev2, ev3))
        assert count == 2

    def test_lineage_graph_independent_roots(self):
        graph = LineageGraph(
            nodes=(
                LineageNode(node_id="n1", is_independent=True),
                LineageNode(node_id="n2", is_independent=True),
                LineageNode(
                    node_id="n3",
                    is_independent=False,
                    parent_refs=("n1",),
                ),
            )
        )
        roots = graph.independent_roots()
        assert "n1" in roots
        assert "n2" in roots
        assert "n3" not in roots

    def test_aggregate_support(self):
        tm = TruthMaintenance()
        tm.add_evidence(make_evidence("ev:s1", supports=True, confidence=0.7))
        tm.add_evidence(make_evidence("ev:s2", supports=True, confidence=0.5))
        tm.add_evidence(make_evidence("ev:o1", supports=False, confidence=0.3))
        support, opposition, independent = tm.aggregate_support("prop:test")
        assert support == pytest.approx(1.2)
        assert opposition == pytest.approx(0.3)
        assert independent == 2


# ── 4. Temporal validity ──────────────────────────────────────────


class TestTemporalValidity:
    def test_expired_evidence_not_fresh(self):
        past_end = datetime.now(timezone.utc) - timedelta(days=1)
        ev = make_evidence(
            temporal_validity=TimeExtent(end=past_end),
        )
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        assessment = evaluator.evaluate(
            proposition=prop,
            context=ctx,
            evidence=(ev,),
        )
        assert not assessment.fresh_enough

    def test_valid_evidence_is_fresh(self):
        future_end = datetime.now(timezone.utc) + timedelta(days=1)
        ev = make_evidence(
            temporal_validity=TimeExtent(end=future_end),
        )
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        assessment = evaluator.evaluate(
            proposition=prop,
            context=ctx,
            evidence=(ev,),
        )
        assert assessment.fresh_enough

    def test_no_temporal_validity_is_fresh(self):
        ev = make_evidence(temporal_validity=None)
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        assessment = evaluator.evaluate(
            proposition=prop,
            context=ctx,
            evidence=(ev,),
        )
        assert assessment.fresh_enough


# ── 5. Four-state truth maintenance ───────────────────────────────


class TestTruthMaintenanceStates:
    def test_supported_state(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(proposition=prop, context=ctx, evidence=(ev,))
        assert assessment.support_state == SupportState.SUPPORTED.value

    def test_refuted_state(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        ev = make_evidence(supports=False, confidence=0.8)
        assessment = evaluator.evaluate(proposition=prop, context=ctx, evidence=(ev,))
        assert assessment.support_state == SupportState.REFUTED.value

    def test_both_state(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        ev1 = make_evidence("ev:s", supports=True, confidence=0.8)
        ev2 = make_evidence("ev:o", supports=False, confidence=0.6)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev1, ev2),
        )
        assert assessment.support_state == SupportState.BOTH.value

    def test_neither_state(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(),
        )
        assert assessment.support_state == SupportState.NEITHER.value

    def test_absence_is_not_falsity(self):
        """No evidence → NEITHER, not REFUTED."""
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context()
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(),
        )
        assert assessment.support_state == SupportState.NEITHER.value
        assert assessment.admissibility == AdmissibilityLevel.BLOCKED.value


# ── 6. Admissibility by context ───────────────────────────────────


class TestAdmissibility:
    def test_actual_context_supported_is_admitted(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(context_kind="actual")
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev,),
        )
        assert assessment.admissibility == AdmissibilityLevel.ADMITTED.value

    def test_believed_context_is_attributed_only(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(ctx_id="ctx:belief", context_kind="believed")
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev,),
        )
        assert assessment.admissibility == AdmissibilityLevel.ATTRIBUTED_ONLY.value

    def test_hypothetical_context_is_attributed_only(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(ctx_id="ctx:hyp", context_kind="hypothetical")
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev,),
        )
        assert assessment.admissibility == AdmissibilityLevel.ATTRIBUTED_ONLY.value

    def test_contested_proposition(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(context_kind="actual")
        ev1 = make_evidence("ev:s", supports=True, confidence=0.8)
        ev2 = make_evidence("ev:o", supports=False, confidence=0.6)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev1, ev2),
        )
        assert assessment.admissibility == AdmissibilityLevel.CONTESTED.value


# ── 7. Knowledge derivation ───────────────────────────────────────


class TestKnowledgeDerivation:
    def test_knows_requires_all_conditions(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(context_kind="actual")
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev,),
        )
        knowledge = evaluator.derive_knowledge(
            proposition=prop,
            context=ctx,
            assessment=assessment,
            is_grounded=True,
        )
        # Should NOT be known — schema_use_valid is False (no profile)
        assert not knowledge.is_known
        assert any("schemas not executable" in lim for lim in knowledge.limitations)

    def test_knows_with_all_conditions_met(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(context_kind="actual")
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev,),
        )
        profile = SchemaUseProfile(
            schema_record_ref="schema:test:v1",
            context_ref="ctx:actual",
            level=UseProfileLevel.ACTIVE,
            permitted_semantic_operations=frozenset(op.value for op in ACTIVE_OPERATIONS),
        )
        knowledge = evaluator.derive_knowledge(
            proposition=prop,
            context=ctx,
            assessment=assessment,
            is_grounded=True,
            schema_use_profile=profile,
        )
        assert knowledge.is_known
        assert knowledge.is_grounded
        assert knowledge.evidence_satisfies_policy
        assert knowledge.schemas_executable

    def test_believed_context_not_known(self):
        evaluator = EpistemicEvaluator()
        prop = make_proposition()
        ctx = make_context(ctx_id="ctx:belief", context_kind="believed")
        ev = make_evidence(supports=True, confidence=0.8)
        assessment = evaluator.evaluate(
            proposition=prop, context=ctx, evidence=(ev,),
        )
        profile = SchemaUseProfile(
            schema_record_ref="schema:test:v1",
            context_ref="ctx:belief",
            level=UseProfileLevel.ACTIVE,
            permitted_semantic_operations=frozenset(op.value for op in ACTIVE_OPERATIONS),
        )
        knowledge = evaluator.derive_knowledge(
            proposition=prop,
            context=ctx,
            assessment=assessment,
            is_grounded=True,
            schema_use_profile=profile,
        )
        # Believed context → attributed_only → not known as actual-world
        assert not knowledge.is_known
        assert any("admissibility is attributed_only" in lim for lim in knowledge.limitations)


# ── 8. Self-reports ───────────────────────────────────────────────


class TestSelfReports:
    def test_self_report_must_be_backed(self):
        report = SelfReport(
            report_kind="knows",
            is_true=True,
            evidence_refs=(),
            is_backed=False,
        )
        with pytest.raises(AssertionError, match="Unbacked"):
            report.assert_backed()

    def test_backed_self_report_passes(self):
        report = SelfReport(
            report_kind="knows",
            is_true=True,
            evidence_refs=("prop:test",),
            is_backed=True,
        )
        report.assert_backed()

    def test_report_knows_true(self):
        builder = SelfReportBuilder()
        knowledge = KnowledgeAssessment(
            proposition_ref="prop:test",
            is_known=True,
        )
        report = builder.report_knows("prop:test", knowledge)
        assert report.is_true
        assert report.is_backed

    def test_report_knows_false_with_limitations(self):
        builder = SelfReportBuilder()
        knowledge = KnowledgeAssessment(
            proposition_ref="prop:test",
            is_known=False,
            limitations=("not grounded",),
        )
        report = builder.report_knows("prop:test", knowledge)
        assert not report.is_true
        assert report.is_backed
        assert "not grounded" in report.limitations


# ── 9. Understanding is operation-relative ────────────────────────


class TestOperationRelativeUnderstanding:
    def test_partial_understanding_cannot_classify(self):
        builder = SelfReportBuilder()
        profile = SchemaUseProfile(
            schema_record_ref="schema:test:v1",
            context_ref="ctx:actual",
            level=UseProfileLevel.PARTIAL,
            permitted_semantic_operations=frozenset(op.value for op in PARTIAL_OPERATIONS),
        )
        understanding = builder.derive_operation_relative_understanding(
            schema_record_ref="schema:test:v1",
            use_profile=profile,
            requested_operation=SemanticOperation.CLASSIFY,
        )
        assert not understanding.can_perform

    def test_active_understanding_can_classify(self):
        builder = SelfReportBuilder()
        profile = SchemaUseProfile(
            schema_record_ref="schema:test:v1",
            context_ref="ctx:actual",
            level=UseProfileLevel.ACTIVE,
            permitted_semantic_operations=frozenset(op.value for op in ACTIVE_OPERATIONS),
        )
        understanding = builder.derive_operation_relative_understanding(
            schema_record_ref="schema:test:v1",
            use_profile=profile,
            requested_operation=SemanticOperation.CLASSIFY,
        )
        assert understanding.can_perform

    def test_opaque_understanding_cannot_do_anything(self):
        builder = SelfReportBuilder()
        profile = SchemaUseProfile(
            schema_record_ref="schema:test:v1",
            context_ref="ctx:actual",
            level=UseProfileLevel.OPAQUE,
            permitted_semantic_operations=frozenset(op.value for op in OPAQUE_OPERATIONS),
        )
        understanding = builder.derive_operation_relative_understanding(
            schema_record_ref="schema:test:v1",
            use_profile=profile,
            requested_operation=SemanticOperation.TYPED_REFERENCE,
        )
        assert not understanding.can_perform


# ── 10. Capability evaluator ──────────────────────────────────────


class TestCapabilityWithLiveRecords:
    def test_no_live_records_means_incapable(self):
        evaluator = CapabilityEvaluator()
        assessment = evaluator.evaluate(
            subject_ref="self",
            operation_schema_ref="op:understand",
        )
        assert assessment.status == "incapable"

    def test_all_conditions_met_is_capable(self):
        evaluator = CapabilityEvaluator()
        assessment = evaluator.evaluate(
            subject_ref="self",
            operation_schema_ref="op:test",
            competence=CompetenceRecord(
                schema_ref="op:test", is_competent=True, competence_score=0.9,
            ),
            implementation=ImplementationRecord(
                operation_ref="op:test", is_registered=True, implementation_id="impl1",
            ),
            component_health=ComponentHealthRecord(component_id="comp1", health="healthy"),
            input_channel=ChannelRecord(channel_kind="input", channel_id="ch1", is_available=True),
            output_channel=ChannelRecord(channel_kind="output", channel_id="ch2", is_available=True),
            resources=(ResourceRecord(
                resource_kind="tokens", status="available",
                available_amount=100, required_amount=10,
            ),),
            permission=PermissionRecord(operation_ref="op:test", is_allowed=True),
            preconditions=(ContextualPrecondition(precondition_id="pre1", is_satisfied=True),),
        )
        assert assessment.status == "capable"
        assert all(c.satisfied for c in assessment.condition_results)


# ── 11. Cycle integration ─────────────────────────────────────────


class TestCycleIntegration:
    def test_cycle_has_knowledge_assessments_field(self):
        from cemm.kernel.model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot
        snapshot = KernelSnapshot(schema_store_revision=1)
        trigger = CycleTrigger(trigger_kind="test")
        cycle = CognitiveCycle(
            cycle_id="test",
            trigger=trigger,
            snapshot=snapshot,
        )
        assert cycle.knowledge_assessments == ()
        assert cycle.self_reports == ()

    def test_cycle_know_stage_wires_knowledge(self):
        from cemm.kernel.model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot
        from cemm.kernel.cycle.kernel import CognitiveKernel
        from cemm.kernel.understanding.composer import SemanticComposer
        from cemm.kernel.understanding.grounding import GroundingResolver
        from cemm.kernel.understanding.interpreter import InterpretationResolver
        from cemm.kernel.understanding.gap_detector import GapDetector
        from cemm.kernel.understanding.workspace import WorkspaceController
        from cemm.kernel.schema.store import SemanticSchemaStore
        from cemm.kernel.learning.coordinator import LearningCoordinator
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        from cemm.kernel.execution.planner import Planner
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import OperationAuthorizer
        from cemm.kernel.execution.reconciliation import OutcomeReconciler
        from cemm.kernel.execution.commit import CommitCoordinator
        from cemm.kernel.response.planner import ResponsePlanner
        from cemm.kernel.response.common_ground import CommonGroundManager

        store = SemanticSchemaStore()
        tm = TruthMaintenance()
        kernel = CognitiveKernel(
            schema_store=store,
            percept_adapter=type("MockAdapter", (), {"adapt": lambda self, t: None})(),
            semantic_composer=SemanticComposer(store=store),
            grounding_resolver=GroundingResolver(store=store),
            interpretation_resolver=InterpretationResolver(),
            workspace_controller=WorkspaceController(),
            semantic_retriever=SemanticRetriever(
                schema_store=store, truth_maintenance=tm,
            ),
            epistemic_evaluator=EpistemicEvaluator(truth_maintenance=tm),
            capability_evaluator=CapabilityEvaluator(),
            gap_detector=GapDetector(),
            self_report_builder=SelfReportBuilder(),
            learning_coordinator=LearningCoordinator(store=store),
            goal_arbiter=GoalArbiter(),
            planner=Planner(),
            operation_authorizer=OperationAuthorizer(),
            operation_executor=OperationExecutor(),
            outcome_reconciler=OutcomeReconciler(),
            commit_coordinator=CommitCoordinator(),
            response_planner=ResponsePlanner(),
            message_renderer=type("R", (), {"render": lambda self, plan, language="en": None})(),
            common_ground_manager=CommonGroundManager(),
        )
        trigger = CycleTrigger(trigger_kind="test")
        cycle = kernel.run(trigger)
        # Knowledge assessments and self_reports should be tuples (possibly empty)
        assert isinstance(cycle.knowledge_assessments, tuple)
        assert isinstance(cycle.self_reports, tuple)
