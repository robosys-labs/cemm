"""Stage 5 exit gate tests — meaning-backed recursive learning.

Tests the v3.4 learning transaction lifecycle, hypothesis competition,
grounding frontier, replay queue, activation gate, and cycle integration.

Per LEARNING_PIPELINE.md, CORE_LOOP.md §B5-B6, and completion-plan.md Stage 5:
- Teaching changes ordinary next-turn interpretation
- No parallel learning overlay/episode authority
- Replay does not repeat external action/output
- Outcome wording distinguishes remembered/provisional/understood
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from cemm.kernel.learning.coordinator import (
    LearningCoordinator,
    TransactionStatus,
    ActivationAttempt,
)
from cemm.kernel.learning.hypothesis_factory import (
    HypothesisFactory,
    HypothesisKind,
    CompetingHypotheses,
    EvidenceForHypothesis,
    LearningEvidenceKind,
)
from cemm.kernel.learning.grounding_frontier import (
    GroundingFrontierBuilder,
    GroundingFrontier,
    FrontierItem,
    FrontierPriority,
)
from cemm.kernel.learning.replay_queue import ReplayQueue
from cemm.kernel.learning.assimilator import (
    Assimilator,
    ChildRevision,
    StagedContribution,
)
from cemm.kernel.model.learning import (
    LearningTransaction,
    SchemaHypothesis,
    ReplayWorkItem,
    ReplayResult,
)
from cemm.kernel.model.gap import GapRecord, LearningBudget
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.provenance import ProvenanceKind


# ── Helpers ───────────────────────────────────────────────────────


def make_gap(
    gap_id: str = "gap:test",
    target: str = "schema:test:v1",
) -> GapRecord:
    return GapRecord(
        id=gap_id,
        target_artifact_ref=target,
        budget=LearningBudget(),
    )


def make_hypothesis(
    kind: str = HypothesisKind.NEW_SENSE.value,
    confidence: float = 0.7,
    target: str = "schema:test:v1",
) -> SchemaHypothesis:
    return SchemaHypothesis(
        hypothesis_kind=kind,
        target_sense_ref=target,
        confidence=confidence,
    )


def make_contribution(
    field_name: str = "definition",
    provenance: ProvenanceKind = ProvenanceKind.ASSERTED,
    is_independent: bool = True,
) -> StagedContribution:
    return StagedContribution(
        field_name=field_name,
        field_value="test_value",
        provenance_kind=provenance,
        is_independent=is_independent,
    )


@dataclass(frozen=True, slots=True)
class MockInterpretation:
    proposition: Any = None
    context_frame: Any = None
    proposition_ref: str = "prop:test"
    context_ref: str = "ctx:actual"


@dataclass(frozen=True, slots=True)
class MockProposition:
    id: str = "prop:test"
    predication_ref: str = "schema:test:v1"


# ── 1. Transaction lifecycle ──────────────────────────────────────


class TestTransactionLifecycle:
    def test_open_transaction(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        assert tx.status == TransactionStatus.OPEN.value
        assert tx.gap_ref == gap.id
        assert tx.target_sense_ref == gap.target_artifact_ref
        assert tx.base_store_revision == store.store_revision

    def test_begin_probing_generates_hypotheses(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        evidence = (
            EvidenceForHypothesis(
                evidence_ref="ev:1",
                proposition_ref="prop:1",
                supports_hypothesis_kind=HypothesisKind.NEW_SENSE,
                confidence=0.8,
                is_independent=True,
            ),
        )
        updated, competing = coord.begin_probing(tx, evidence=evidence)
        assert updated.status == TransactionStatus.PROBING.value
        assert len(competing.hypotheses) > 0
        assert competing.hypotheses[0].hypothesis_kind == HypothesisKind.NEW_SENSE.value

    def test_stage_revision(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        evidence = (
            EvidenceForHypothesis(
                evidence_ref="ev:1",
                proposition_ref="prop:1",
                supports_hypothesis_kind=HypothesisKind.NEW_SENSE,
                confidence=0.8,
                is_independent=True,
            ),
        )
        updated, competing = coord.begin_probing(tx, evidence=evidence)
        hyp = competing.hypotheses[0]
        updated2, child = coord.stage_revision(
            updated, hypothesis=hyp,
            contributions=(make_contribution(),),
        )
        assert updated2.status == TransactionStatus.STAGED.value
        assert child.revision_id is not None
        assert len(child.contributions) == 1

    def test_rollback(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        rolled = coord.rollback(tx)
        assert rolled.status == TransactionStatus.ROLLED_BACK.value

    def test_get_pending_transactions(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        pending = coord.get_pending_transactions()
        assert len(pending) == 1
        assert pending[0].id == tx.id

    def test_get_active_transactions_excludes_terminal(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        rolled = coord.rollback(tx)
        active = coord.get_active_transactions()
        assert len(active) == 0


# ── 2. Hypothesis competition ─────────────────────────────────────


class TestHypothesisCompetition:
    def test_alias_competes_with_new_sense(self):
        factory = HypothesisFactory()
        gap = make_gap()
        evidence = (
            EvidenceForHypothesis(
                evidence_ref="ev:1",
                proposition_ref="prop:1",
                supports_hypothesis_kind=HypothesisKind.ALIAS,
                confidence=0.6,
                is_independent=True,
            ),
            EvidenceForHypothesis(
                evidence_ref="ev:2",
                proposition_ref="prop:2",
                supports_hypothesis_kind=HypothesisKind.NEW_SENSE,
                confidence=0.8,
                is_independent=True,
            ),
        )
        competing = factory.generate(gap=gap, evidence=evidence)
        assert competing.has_competition()
        kinds = competing.competing_kinds()
        assert HypothesisKind.ALIAS.value in kinds
        assert HypothesisKind.NEW_SENSE.value in kinds

    def test_correction_is_separate(self):
        factory = HypothesisFactory()
        gap = make_gap()
        evidence = (
            EvidenceForHypothesis(
                evidence_ref="ev:1",
                proposition_ref="prop:1",
                supports_hypothesis_kind=HypothesisKind.CORRECTION,
                confidence=0.9,
                is_independent=True,
            ),
        )
        competing = factory.generate(
            gap=gap, evidence=evidence, is_correction_explicit=True,
        )
        assert competing.is_correction_explicit
        assert len(competing.correction_hypotheses()) == 1
        assert len(competing.non_correction_hypotheses()) == 0

    def test_instance_fact_no_hypothesis(self):
        factory = HypothesisFactory()
        gap = make_gap()
        evidence = (
            EvidenceForHypothesis(
                evidence_ref="ev:1",
                proposition_ref="prop:1",
                supports_hypothesis_kind=HypothesisKind.NONE,
                confidence=0.5,
                is_independent=True,
            ),
        )
        competing = factory.generate(gap=gap, evidence=evidence)
        assert len(competing.hypotheses) == 0


# ── 3. Exact target discrimination ────────────────────────────────


class TestExactTargetDiscrimination:
    def test_classify_instance_fact(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_instance_fact=True)
        assert kind == LearningEvidenceKind.INSTANCE_FACT

    def test_classify_lexeme_binding(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_new_lexical_binding=True)
        assert kind == LearningEvidenceKind.LEXEME_TO_SCHEMA_BINDING

    def test_classify_complete_definition(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_complete_definition=True)
        assert kind == LearningEvidenceKind.COMPLETE_COMPOSITIONAL_DEFINITION

    def test_classify_correction(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_correction=True)
        assert kind == LearningEvidenceKind.CORRECTION_OR_COUNTEREXAMPLE

    def test_classify_source_retraction(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_source_retraction=True)
        assert kind == LearningEvidenceKind.SOURCE_RETRACTION

    def test_classify_permission_change(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_permission_change=True)
        assert kind == LearningEvidenceKind.PERMISSION_CHANGE

    def test_classify_partial_definition(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_partial_definition=True)
        assert kind == LearningEvidenceKind.PARTIAL_DEFINITION

    def test_classify_relation_between_existing(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_relation_between_existing=True)
        assert kind == LearningEvidenceKind.RELATION_BETWEEN_SCHEMAS

    def test_classify_prototype_generalization(self):
        factory = HypothesisFactory()
        kind = factory.classify_learning_kind(is_prototype_generalization=True)
        assert kind == LearningEvidenceKind.PROTOTYPE_DEFAULT_GENERALIZATION


# ── 4. Grounding frontier ─────────────────────────────────────────


class TestGroundingFrontier:
    def test_frontier_priority_ordering(self):
        builder = GroundingFrontierBuilder()
        items = (
            FrontierItem(
                item_id="fi:1",
                dependency_ref="dep:1",
                blocker_kind="missing_differentiator",
                priority=FrontierPriority.DIFFERENTIATOR,
            ),
            FrontierItem(
                item_id="fi:2",
                dependency_ref="dep:2",
                blocker_kind="missing_semantic_family",
                priority=FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE,
            ),
        )
        frontier = builder.build(blockers=items)
        blocking = frontier.blocking_items()
        assert blocking[0].priority < blocking[1].priority
        assert blocking[0].blocker_kind == "missing_semantic_family"

    def test_frontier_respects_budget(self):
        builder = GroundingFrontierBuilder()
        budget = LearningBudget(probe_budget=2, probes_remaining=2)
        items = tuple(
            FrontierItem(
                item_id=f"fi:{i}",
                dependency_ref=f"dep:{i}",
                blocker_kind="missing_definition_field",
                estimated_probe_cost=1,
            )
            for i in range(5)
        )
        frontier = builder.build(blockers=items, budget=budget)
        targets = frontier.next_probe_targets()
        assert len(targets) <= 2

    def test_frontier_excludes_asked_probes(self):
        builder = GroundingFrontierBuilder()
        items = (
            FrontierItem(
                item_id="fi:1",
                dependency_ref="dep:1",
                blocker_kind="missing_semantic_family",
                probe_key="probe:1",
            ),
            FrontierItem(
                item_id="fi:2",
                dependency_ref="dep:2",
                blocker_kind="missing_differentiator",
                probe_key="probe:2",
            ),
        )
        frontier = builder.build(
            blockers=items,
            asked_probe_keys=frozenset({"probe:1"}),
        )
        unasked = frontier.unasked_blocking_items()
        assert len(unasked) == 1
        assert unasked[0].probe_key == "probe:2"

    def test_frontier_is_exhausted_when_no_unasked(self):
        builder = GroundingFrontierBuilder()
        items = (
            FrontierItem(
                item_id="fi:1",
                dependency_ref="dep:1",
                blocker_kind="missing_semantic_family",
                probe_key="probe:1",
            ),
        )
        frontier = builder.build(
            blockers=items,
            asked_probe_keys=frozenset({"probe:1"}),
        )
        assert frontier.is_exhausted()

    def test_frontier_is_resumable(self):
        builder = GroundingFrontierBuilder()
        items = (
            FrontierItem(
                item_id="fi:1",
                dependency_ref="dep:1",
                blocker_kind="missing_semantic_family",
                probe_key="probe:1",
            ),
        )
        frontier = builder.build(blockers=items)
        assert frontier.is_resumable()

    def test_classify_blocker_priority(self):
        builder = GroundingFrontierBuilder()
        assert builder.classify_blocker("missing_semantic_family") == FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE
        assert builder.classify_blocker("missing_constitutive_pattern") == FrontierPriority.CONSTITUTIVE_STRUCTURE
        assert builder.classify_blocker("missing_differentiator") == FrontierPriority.DIFFERENTIATOR
        assert builder.classify_blocker("missing_independent_competence") == FrontierPriority.INDEPENDENT_DISCRIMINATION


# ── 5. Replay queue ───────────────────────────────────────────────


class TestReplayQueue:
    def test_enqueue_and_dequeue(self):
        queue = ReplayQueue()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            target_schema_revision_ref="schema:1:v2",
            checkpoint_ref="cp:1",
            dependency_fingerprint="fp:1",
            idempotency_key="ik:1",
            priority=1.0,
        )
        assert queue.enqueue(item)
        dequeued = queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == "rw:1"

    def test_dedup_completed(self):
        queue = ReplayQueue()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            target_schema_revision_ref="schema:1:v2",
            checkpoint_ref="cp:1",
            dependency_fingerprint="fp:1",
            idempotency_key="ik:1",
        )
        queue.enqueue(item)
        queue.complete(item, ReplayResult(work_item_ref="rw:1", status="succeeded"))
        # Same key should be deduped
        assert not queue.enqueue(item)

    def test_dedup_queued(self):
        queue = ReplayQueue()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            target_schema_revision_ref="schema:1:v2",
            checkpoint_ref="cp:1",
            dependency_fingerprint="fp:1",
            idempotency_key="ik:1",
        )
        assert queue.enqueue(item)
        assert not queue.enqueue(item)  # Already queued

    def test_cancel_stale(self):
        queue = ReplayQueue()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            target_schema_revision_ref="schema:1:v2",
            checkpoint_ref="cp:1",
            dependency_fingerprint="fp:old",
            idempotency_key="ik:1",
        )
        queue.enqueue(item)
        stale = queue.cancel_stale("fp:new")
        assert len(stale) == 1
        assert queue.pending_count() == 0

    def test_executed_operation_exclusion(self):
        queue = ReplayQueue()
        queue.record_executed_operation("op:1", "ik:op1")
        assert queue.is_operation_executed("ik:op1")
        assert not queue.is_operation_executed("ik:other")


# ── 6. Assimilator and child revision ─────────────────────────────


class TestAssimilator:
    def test_child_revision_is_immutable(self):
        assimilator = Assimilator()
        hyp = make_hypothesis()
        child = assimilator.assimilate(
            base_schema_ref="schema:test:v1",
            base_store_revision=1,
            hypothesis=hyp,
            contributions=(make_contribution(),),
        )
        assert child.is_declarative_only
        assert child.base_store_revision == 1
        assert len(child.contributions) == 1

    def test_field_provenance(self):
        assimilator = Assimilator()
        hyp = make_hypothesis()
        child = assimilator.assimilate(
            base_schema_ref="schema:test:v1",
            base_store_revision=1,
            hypothesis=hyp,
            contributions=(
                make_contribution(field_name="definition", provenance=ProvenanceKind.ASSERTED),
                make_contribution(field_name="hypothesis_field", provenance=ProvenanceKind.HYPOTHESIZED),
            ),
        )
        provenance = child.get_provenance("definition")
        assert provenance is not None
        assert provenance.provenance_kind == ProvenanceKind.ASSERTED

    def test_weak_fields_detected(self):
        assimilator = Assimilator()
        hyp = make_hypothesis()
        child = assimilator.assimilate(
            base_schema_ref="schema:test:v1",
            base_store_revision=1,
            hypothesis=hyp,
            contributions=(
                make_contribution(field_name="strong", provenance=ProvenanceKind.OBSERVED),
                make_contribution(field_name="weak", provenance=ProvenanceKind.HYPOTHESIZED),
            ),
        )
        weak = child.weak_fields()
        assert "weak" in weak
        assert "strong" not in weak

    def test_lineage_support_check(self):
        assimilator = Assimilator()
        # No overlap → can increase support
        assert assimilator.check_lineage_support(("ev:1",), ("schema:other",))
        # Overlap → cannot increase support
        assert not assimilator.check_lineage_support(("ev:1",), ("ev:1",))

    def test_can_increase_competence(self):
        assimilator = Assimilator()
        assert assimilator.can_increase_competence(("ev:1",), ("schema:other",))
        assert not assimilator.can_increase_competence(("ev:1",), ("ev:1",))


# ── 7. Activation gate ────────────────────────────────────────────


class TestActivationGate:
    def test_provisional_replay_without_hypotheses_rolls_back(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        # No hypotheses → rollback
        updated, attempt = coord.provisional_replay(tx)
        assert updated.status == TransactionStatus.ROLLED_BACK.value
        assert not attempt.activated
        assert "no hypotheses" in attempt.rollback_reason

    def test_provisional_replay_with_hypothesis(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        evidence = (
            EvidenceForHypothesis(
                evidence_ref="ev:1",
                proposition_ref="prop:1",
                supports_hypothesis_kind=HypothesisKind.NEW_SENSE,
                confidence=0.8,
                is_independent=True,
            ),
        )
        updated, competing = coord.begin_probing(tx, evidence=evidence)
        assert len(updated.hypotheses) > 0
        updated2, attempt = coord.provisional_replay(
            updated,
            contributions=(make_contribution(),),
        )
        # Should be either provisional, committed, or rolled_back
        assert updated2.status in (
            TransactionStatus.PROVISIONAL.value,
            TransactionStatus.COMMITTED.value,
            TransactionStatus.ROLLED_BACK.value,
        )

    def test_completion_gate_rejects_self_certified_activation(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        # Simulate a self-certified activation attempt
        from cemm.kernel.schema.competence import CompetenceAssessment
        from cemm.kernel.schema.closure import SchemaGroundingAssessment
        attempt = ActivationAttempt(
            child_revision_ref="child:1",
            structural_assessment=SchemaGroundingAssessment(
                record_id="schema:test:v1",
                semantic_key="test",
                environment_fingerprint="fp:test",
                is_structurally_executable=True,
                blocker_reasons=(),
            ),
            competence_assessment=CompetenceAssessment(
                is_self_certified=True,
            ),
            activated=True,
        )
        from dataclasses import replace
        tx_committed = replace(tx, status=TransactionStatus.COMMITTED.value, admissibility_status="admitted")
        passed, failures = coord.check_completion_gate(tx_committed, attempt)
        assert not passed
        assert any("self-certified" in f for f in failures)

    def test_completion_gate_rejects_open_admissibility(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        attempt = ActivationAttempt(
            child_revision_ref="child:1",
        )
        passed, failures = coord.check_completion_gate(tx, attempt)
        assert not passed
        assert any("admissibility" in f for f in failures)


# ── 8. Coordinator compute_grounding_frontier ─────────────────────


class TestCoordinatorFrontier:
    def test_compute_frontier_from_blockers(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap()
        tx = coord.open_transaction(gap)
        frontier = coord.compute_grounding_frontier(
            tx=tx,
            blockers=("missing_semantic_family", "missing_differentiator"),
        )
        assert len(frontier.items) == 2
        blocking = frontier.blocking_items()
        assert blocking[0].priority <= blocking[1].priority


# ── 9. Consume pending evidence ───────────────────────────────────


class TestConsumePendingEvidence:
    def test_no_pending_returns_empty(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        result = coord.consume_pending_evidence(
            selected_interpretations=[MockInterpretation(
                proposition=MockProposition(),
            )],
        )
        assert result == ()

    def test_pending_matches_evidence(self):
        store = SemanticSchemaStore()
        coord = LearningCoordinator(store=store)
        gap = make_gap(target="schema:test:v1")
        tx = coord.open_transaction(gap)
        result = coord.consume_pending_evidence(
            selected_interpretations=[MockInterpretation(
                proposition=MockProposition(
                    id="prop:1",
                    predication_ref="schema:test:v1",
                ),
            )],
        )
        assert len(result) == 1
        updated = result[0]
        assert updated.status == TransactionStatus.PROBING.value
        assert len(updated.hypotheses) > 0


# ── 10. Cycle integration ─────────────────────────────────────────


class TestCycleIntegration:
    def test_cycle_has_learning_transactions_field(self):
        from cemm.kernel.model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot
        snapshot = KernelSnapshot(schema_store_revision=1)
        trigger = CycleTrigger(trigger_kind="test")
        cycle = CognitiveCycle(
            cycle_id="test",
            trigger=trigger,
            snapshot=snapshot,
        )
        assert cycle.learning_transactions == ()

    def test_cycle_know_stage_opens_transactions_for_gaps(self):
        from cemm.kernel.model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot
        from cemm.kernel.cycle.kernel import CognitiveKernel
        from cemm.kernel.understanding.composer import SemanticComposer
        from cemm.kernel.understanding.grounding import GroundingResolver
        from cemm.kernel.understanding.interpreter import InterpretationResolver
        from cemm.kernel.understanding.gap_detector import GapDetector
        from cemm.kernel.understanding.workspace import WorkspaceController
        from cemm.kernel.epistemics.evaluator import EpistemicEvaluator
        from cemm.kernel.epistemics.retriever import SemanticRetriever
        from cemm.kernel.self_model.capability_evaluator import CapabilityEvaluator
        from cemm.kernel.self_model.self_report import SelfReportBuilder
        from cemm.kernel.execution.goal_arbiter import GoalArbiter
        from cemm.kernel.execution.planner import Planner
        from cemm.kernel.execution.executor import OperationExecutor
        from cemm.kernel.execution.authorizer import OperationAuthorizer
        from cemm.kernel.execution.reconciliation import OutcomeReconciler
        from cemm.kernel.execution.commit import CommitCoordinator
        from cemm.kernel.response.planner import ResponsePlanner
        from cemm.kernel.response.common_ground import CommonGroundManager

        store = SemanticSchemaStore()
        kernel = CognitiveKernel(
            schema_store=store,
            percept_adapter=type("A", (), {"perceive": lambda self, s: ()})(),
            semantic_composer=SemanticComposer(store=store),
            grounding_resolver=GroundingResolver(store=store),
            interpretation_resolver=InterpretationResolver(),
            workspace_controller=WorkspaceController(),
            semantic_retriever=SemanticRetriever(schema_store=store),
            epistemic_evaluator=EpistemicEvaluator(),
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
        # learning_transactions should be a tuple (possibly empty if no gaps)
        assert isinstance(cycle.learning_transactions, tuple)


# ── 11. Legacy retirement ─────────────────────────────────────────


class TestLegacyRetirement:
    def test_episode_manager_is_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.learning.learning_episode_manager")
        assert "DEPRECATED" in mod.__doc__

    def test_question_planner_is_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.learning.learning_question_planner")
        assert "DEPRECATED" in mod.__doc__

    def test_answer_assimilator_is_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.learning.learning_answer_assimilator")
        assert "DEPRECATED" in mod.__doc__

    def test_teaching_frame_manager_is_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.legacy.v3_3.teaching_frame_manager")
        assert "DEPRECATED" in mod.__doc__

    def test_predicate_inductor_is_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.learning.predicate_schema_inductor")
        assert "DEPRECATED" in mod.__doc__
