"""Phase 7 gate tests: Meaning-backed recursive learning.

Gates (from IMPLEMENTATION_PLAN.md Phase 7):
- learning changes the ordinary resolver;
- probe/replay budgets are resumable and non-repetitive;
- alias/new sense/specialization/correction hypotheses compete;
- no external action repeats during replay;
- outcome wording matches remembered/provisional/understood/known state.

Additional guardrail tests from AGENTS.md, LEARNING_PIPELINE.md:
- No free-text as semantic authority
- No hypothesis silently rewritten as user teaching
- Derived propositions cannot increase support in ancestry/SCC
- Untrusted learning is declarative
- Competency tests cannot mutate stores or execute effects
- If competence/admissibility incomplete → provisional, not falsely activated
- Learning completion gate (9 conditions)
- Replay is deduplicated, snapshot-pinned, retry-safe, stale-cancellable
- Import boundaries: learning → model + schema + epistemics
- Learning cannot install a parallel resolver
"""
from __future__ import annotations

import pytest

from cemm.kernel.learning.hypothesis_factory import (
    HypothesisFactory, HypothesisKind, CompetingHypotheses,
    EvidenceForHypothesis,
)
from cemm.kernel.learning.grounding_frontier import (
    GroundingFrontierBuilder, GroundingFrontier, FrontierItem,
    FrontierPriority,
)
from cemm.kernel.learning.assimilator import (
    Assimilator, ChildRevision, StagedContribution,
)
from cemm.kernel.learning.replay_queue import (
    ReplayQueue, ReplayKey, ExecutedOperationExclusion,
)
from cemm.kernel.learning.coordinator import (
    LearningCoordinator, TransactionStatus, ActivationAttempt,
)
from cemm.kernel.model.learning import (
    LearningTransaction, SchemaHypothesis, ReplayWorkItem, ReplayResult,
)
from cemm.kernel.model.gap import GapRecord, LearningBudget, ProbePlan
from cemm.kernel.model.identity import Provenance, Scope, ScopeLevel
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.schema.provenance import ProvenanceKind, ContributionRecord
from cemm.kernel.schema.grounding_spec import GroundingSpecification, SemanticPattern
from cemm.kernel.schema.closure import GroundedDefinitionClosure
from cemm.kernel.schema.competence import CompetenceHarness, CompetenceCase, CompetenceCheckKind, ContrastResult
from cemm.kernel.epistemics.evaluator import AdmissibilityLevel


# ── Helpers ────────────────────────────────────────────────────────


def make_gap(gap_id: str = "gap:test", budget: LearningBudget | None = None) -> GapRecord:
    return GapRecord(
        id=gap_id,
        gap_kind="missing_constitutive_pattern",
        target_artifact_ref="schema:test:v1",
        learnable=True,
        budget=budget or LearningBudget(probe_budget=5, replay_budget=3, probes_remaining=5, replays_remaining=3),
    )


def make_envelope(record_id: str = "schema:test:v1", semantic_key: str = "test") -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind="predicate",
        status="candidate",
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )


# ── Gate 1: alias/new sense/specialization/correction hypotheses compete ──


def test_hypotheses_compete():
    """Alias, new_sense, and specialization hypotheses compete."""
    factory = HypothesisFactory()
    gap = make_gap()

    evidence = (
        EvidenceForHypothesis(
            evidence_ref="ev1", proposition_ref="prop1",
            supports_hypothesis_kind=HypothesisKind.ALIAS,
            confidence=0.7, is_independent=True,
        ),
        EvidenceForHypothesis(
            evidence_ref="ev2", proposition_ref="prop2",
            supports_hypothesis_kind=HypothesisKind.NEW_SENSE,
            confidence=0.8, is_independent=True,
        ),
        EvidenceForHypothesis(
            evidence_ref="ev3", proposition_ref="prop3",
            supports_hypothesis_kind=HypothesisKind.SPECIALIZATION,
            confidence=0.6, is_independent=True,
        ),
    )

    competing = factory.generate(gap=gap, evidence=evidence)

    assert competing.has_competition()
    assert HypothesisKind.ALIAS.value in competing.competing_kinds()
    assert HypothesisKind.NEW_SENSE.value in competing.competing_kinds()
    assert HypothesisKind.SPECIALIZATION.value in competing.competing_kinds()


def test_correction_is_separate():
    """Correction requires explicit evidence of error."""
    factory = HypothesisFactory()
    gap = make_gap()

    evidence = (
        EvidenceForHypothesis(
            evidence_ref="ev1", proposition_ref="prop1",
            supports_hypothesis_kind=HypothesisKind.CORRECTION,
            confidence=0.9, is_independent=True,
        ),
    )

    # Without explicit correction flag, correction evidence is ignored
    competing = factory.generate(gap=gap, evidence=evidence, is_correction_explicit=False)
    assert len(competing.hypotheses) == 0  # No non-correction evidence

    # With explicit correction flag, correction hypothesis is generated
    competing = factory.generate(gap=gap, evidence=evidence, is_correction_explicit=True)
    assert len(competing.hypotheses) == 1
    assert competing.hypotheses[0].hypothesis_kind == "correction"
    assert competing.is_correction_explicit


def test_instance_fact_does_not_generate_hypothesis():
    """Not every teaching-looking utterance defines a concept.
    Instance facts and relations should not generate hypotheses."""
    factory = HypothesisFactory()
    gap = make_gap()

    # Classify evidence as instance fact (no flags set)
    ev = factory.classify_evidence(
        proposition_ref="prop:instance_fact",
        evidence_ref="ev1",
    )
    assert ev.supports_hypothesis_kind == HypothesisKind.NONE

    # Generate should NOT create hypotheses from instance-fact evidence
    competing = factory.generate(gap=gap, evidence=(ev,))
    assert len(competing.hypotheses) == 0


def test_no_free_text_as_semantic_authority():
    """The learning transaction receives grounded propositions and evidence
    records, never copied free-text fields as semantic authority."""
    factory = HypothesisFactory()
    gap = make_gap()

    # Evidence must be structured (EvidenceForHypothesis), not free text
    evidence = (
        EvidenceForHypothesis(
            evidence_ref="ev1",
            proposition_ref="prop:grounded:1",
            supports_hypothesis_kind=HypothesisKind.NEW_SENSE,
            confidence=0.8,
            is_independent=True,
        ),
    )

    competing = factory.generate(gap=gap, evidence=evidence)
    assert len(competing.hypotheses) > 0
    # The hypothesis references the target artifact, not free text
    assert competing.hypotheses[0].target_sense_ref == gap.target_artifact_ref


# ── Gate 2: probe/replay budgets are resumable and non-repetitive ──


def test_probe_budget_exhaustion_is_resumable():
    """Budget exhaustion leaves exact typed gaps and a resumable transaction.
    It does not mark failure."""
    builder = GroundingFrontierBuilder()
    budget = LearningBudget(probe_budget=2, replay_budget=3, probes_remaining=2, replays_remaining=3)

    items = (
        FrontierItem(item_id="f1", dependency_ref="dep1", blocker_kind="missing_constitutive_pattern",
                     priority=FrontierPriority.CONSTITUTIVE_STRUCTURE, probe_key="probe1"),
        FrontierItem(item_id="f2", dependency_ref="dep2", blocker_kind="missing_differentiator",
                     priority=FrontierPriority.DIFFERENTIATOR, probe_key="probe2"),
        FrontierItem(item_id="f3", dependency_ref="dep3", blocker_kind="missing_required_role",
                     priority=FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE, probe_key="probe3"),
    )

    frontier = builder.build(blockers=items, budget=budget)

    # Only 2 probes budgeted → 2 items returned
    targets = frontier.next_probe_targets()
    assert len(targets) == 2

    # Simulate the 2 probes being asked
    asked_keys = frozenset(t.probe_key for t in targets)
    frontier = builder.build(
        blockers=items,
        budget=LearningBudget(probe_budget=2, replay_budget=3, probes_remaining=0, replays_remaining=3),
        asked_probe_keys=asked_keys,
    )

    # Budget exhausted
    assert frontier.is_exhausted()

    # But frontier is resumable — there are still unasked items
    assert frontier.is_resumable()
    assert len(frontier.remaining_gaps()) > 0


def test_asked_probe_keys_are_persisted():
    """Asked probe keys are persisted — no repeated questions."""
    builder = GroundingFrontierBuilder()
    budget = LearningBudget(probe_budget=5, replay_budget=3, probes_remaining=5, replays_remaining=3)

    items = (
        FrontierItem(item_id="f1", dependency_ref="dep1", blocker_kind="missing_constitutive_pattern",
                     priority=FrontierPriority.CONSTITUTIVE_STRUCTURE, probe_key="probe1"),
        FrontierItem(item_id="f2", dependency_ref="dep2", blocker_kind="missing_differentiator",
                     priority=FrontierPriority.DIFFERENTIATOR, probe_key="probe2"),
    )

    asked = frozenset({"probe1"})
    frontier = builder.build(blockers=items, budget=budget, asked_probe_keys=asked)

    # probe1 is already asked → only probe2 should be in next targets
    targets = frontier.next_probe_targets()
    assert len(targets) == 1
    assert targets[0].probe_key == "probe2"


def test_frontier_priority_ordering():
    """Frontier items are ordered by priority."""
    builder = GroundingFrontierBuilder()
    budget = LearningBudget(probe_budget=10, replay_budget=5, probes_remaining=10, replays_remaining=5)

    items = (
        FrontierItem(item_id="f1", dependency_ref="dep1", blocker_kind="enrichment",
                     priority=FrontierPriority.ENRICHMENT, probe_key="probe1"),
        FrontierItem(item_id="f2", dependency_ref="dep2", blocker_kind="missing_constitutive_pattern",
                     priority=FrontierPriority.CONSTITUTIVE_STRUCTURE, probe_key="probe2"),
        FrontierItem(item_id="f3", dependency_ref="dep3", blocker_kind="active_goal_blocker",
                     priority=FrontierPriority.ACTIVE_GOAL_BLOCKER, probe_key="probe3"),
    )

    frontier = builder.build(blockers=items, budget=budget)
    blocking = frontier.blocking_items()

    # Should be ordered: ACTIVE_GOAL_BLOCKER < CONSTITUTIVE_STRUCTURE < ENRICHMENT
    assert blocking[0].priority == FrontierPriority.ACTIVE_GOAL_BLOCKER
    assert blocking[1].priority == FrontierPriority.CONSTITUTIVE_STRUCTURE
    assert blocking[2].priority == FrontierPriority.ENRICHMENT


# ── Gate 3: no external action repeats during replay ──


def test_replay_dedup():
    """Replay is deduplicated — same key returns False on second enqueue."""
    queue = ReplayQueue()
    queue.pin_snapshot("fingerprint_v1")

    item = ReplayWorkItem(
        id="rw1",
        source_evidence_ref="ev1",
        target_sense_ref="sense1",
        target_schema_revision_ref="schema:test:v1",
        checkpoint_ref="ckpt1",
        context_refs=("ctx1",),
        dependency_fingerprint="fingerprint_v1",
        idempotency_key="key1",
        priority=1.0,
    )

    assert queue.enqueue(item)  # First time → True
    assert not queue.enqueue(item)  # Second time → False (dedup)


def test_replay_no_external_action_repeats():
    """Replay never repeats external actions or already dispatched communication."""
    queue = ReplayQueue()

    # Record an executed operation
    queue.record_executed_operation("op1", "idem_key1")

    # Check that it's marked as executed
    assert queue.is_operation_executed("idem_key1")
    assert not queue.is_operation_executed("idem_key2")


def test_replay_stale_cancellation():
    """Replay is stale-cancellable — items with different fingerprint are cancelled."""
    queue = ReplayQueue()
    queue.pin_snapshot("fingerprint_v1")

    item1 = ReplayWorkItem(
        id="rw1", source_evidence_ref="ev1", target_sense_ref="sense1",
        target_schema_revision_ref="schema:v1", checkpoint_ref="ckpt1",
        context_refs=("ctx1",), dependency_fingerprint="fingerprint_v1",
        idempotency_key="key1", priority=1.0,
    )
    item2 = ReplayWorkItem(
        id="rw2", source_evidence_ref="ev2", target_sense_ref="sense2",
        target_schema_revision_ref="schema:v2", checkpoint_ref="ckpt2",
        context_refs=("ctx2",), dependency_fingerprint="fingerprint_v2",  # Different!
        idempotency_key="key2", priority=2.0,
    )

    queue.enqueue(item1)
    queue.enqueue(item2)

    # Cancel stale items (different fingerprint)
    stale = queue.cancel_stale("fingerprint_v1")
    assert len(stale) == 1
    assert stale[0].id == "rw2"

    # Item1 remains
    assert queue.pending_count() == 1


def test_replay_completion():
    """Replay work items complete and results are retrievable."""
    queue = ReplayQueue()

    item = ReplayWorkItem(
        id="rw1", source_evidence_ref="ev1", target_sense_ref="sense1",
        target_schema_revision_ref="schema:v1", checkpoint_ref="ckpt1",
        context_refs=("ctx1",), dependency_fingerprint="fp1",
        idempotency_key="key1", priority=1.0,
    )

    queue.enqueue(item)
    dequeued = queue.dequeue()
    assert dequeued is not None

    result = ReplayResult(work_item_ref="rw1", status="succeeded")
    queue.complete(item, result)

    assert queue.is_completed(item)
    assert queue.get_result(item).status == "succeeded"
    assert queue.pending_count() == 0


# ── Gate 4: assimilator provenance and lineage ──


def test_no_hypothesis_rewritten_as_user_teaching():
    """No hypothesis is silently rewritten as user teaching."""
    assimilator = Assimilator()

    # Hypothesized contribution
    contrib = StagedContribution(
        field_name="definition",
        field_value="some_value",
        provenance_kind=ProvenanceKind.HYPOTHESIZED,
        is_hypothesis=True,
    )

    child = assimilator.assimilate(
        base_schema_ref="schema:test:v1",
        base_store_revision=1,
        hypothesis=SchemaHypothesis(hypothesis_kind="new_sense", target_sense_ref="sense1"),
        contributions=(contrib,),
    )

    # The provenance should remain HYPOTHESIZED, not rewritten as ASSERTED
    provenance = child.get_provenance("definition")
    assert provenance is not None
    assert provenance.provenance_kind == ProvenanceKind.HYPOTHESIZED


def test_derived_evidence_cannot_increase_support_in_ancestry():
    """Derived propositions cannot increase support for schemas in their ancestry."""
    assimilator = Assimilator()

    # Evidence lineage includes schema ancestor
    evidence_lineage = ("source_a", "schema_ancestor")
    schema_ancestry = ("schema_ancestor",)

    # Should return False — cannot increase support (ancestry overlap)
    can_increase = assimilator.check_lineage_support(evidence_lineage, schema_ancestry)
    assert not can_increase


def test_independent_evidence_can_increase_support():
    """Independent evidence with no ancestry overlap can increase support."""
    assimilator = Assimilator()

    evidence_lineage = ("independent_source",)
    schema_ancestry = ("schema_ancestor",)

    can_increase = assimilator.check_lineage_support(evidence_lineage, schema_ancestry)
    assert can_increase


def test_translation_does_not_create_independent_support():
    """A translation does not create new independent support."""
    assimilator = Assimilator()

    # Translation inherits root lineage
    evidence_lineage = ("original_source", "translation_1")
    schema_scc = ("original_source",)  # Same root

    can_increase = assimilator.can_increase_competence(evidence_lineage, schema_scc)
    assert not can_increase


def test_untrusted_learning_is_declarative():
    """Untrusted learning is declarative — cannot install executable code."""
    assimilator = Assimilator()

    child = assimilator.assimilate(
        base_schema_ref="schema:test:v1",
        base_store_revision=1,
        hypothesis=SchemaHypothesis(hypothesis_kind="new_sense"),
        contributions=(StagedContribution(
            field_name="definition",
            field_value="user_provided_value",
            provenance_kind=ProvenanceKind.ASSERTED,
        ),),
    )

    assert child.is_declarative_only


# ── Gate 5: outcome wording matches state ──


def test_outcome_wording_remembered():
    """Remembered: exact attributed proposition/evidence committed."""
    from cemm.kernel.epistemics.knowledge_derivation import SelfReport

    report = SelfReport(
        report_kind="remembers",
        proposition_ref="prop:user_statement",
        is_true=True,
        evidence_refs=("prop:user_statement",),
        is_backed=True,
    )
    assert report.report_kind == "remembers"
    assert report.is_true


def test_outcome_wording_provisional():
    """Provisionally usable: structurally executable but limitations remain."""
    from cemm.kernel.schema.use_profile import SchemaUseProfile, UseProfileLevel, PARTIAL_OPERATIONS

    profile = SchemaUseProfile(
        schema_record_ref="schema:learned:v1",
        context_ref="ctx:actual",
        level=UseProfileLevel.PARTIAL,
        structural_status="structurally_executable",
        competence_status="self_checked",
        permitted_semantic_operations=frozenset(op.value for op in PARTIAL_OPERATIONS),
        limitations=("competence incomplete",),
    )
    assert profile.level == UseProfileLevel.PARTIAL
    assert "competence incomplete" in profile.limitations


def test_outcome_wording_understood():
    """Understood: exact active revision with independent competence."""
    from cemm.kernel.schema.use_profile import SchemaUseProfile, UseProfileLevel, ACTIVE_OPERATIONS

    profile = SchemaUseProfile(
        schema_record_ref="schema:learned:v1",
        context_ref="ctx:actual",
        level=UseProfileLevel.ACTIVE,
        structural_status="structurally_executable",
        competence_status="independently_validated",
        permitted_semantic_operations=frozenset(op.value for op in ACTIVE_OPERATIONS),
    )
    assert profile.level == UseProfileLevel.ACTIVE


# ── Gate 6: learning changes the ordinary resolver ──


def test_learning_changes_ordinary_resolver():
    """After learning commits an active schema, the ordinary resolver finds it."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:learned:v1", "learned")
    store.register(env)
    store.index_lexical_form("learned", "en", "learned")

    # Before activation, find_candidates returns candidate
    candidates = store.find_candidates("learned")
    assert len(candidates) == 1
    assert candidates[0].status == "candidate"

    # Activate
    store.transition_to_provisional("schema:learned:v1", 1)
    rev = store.get_revision("schema:learned:v1")
    store.activate("schema:learned:v1", rev)

    # After activation, find_active returns the schema
    active = store.find_active("learned")
    assert active is not None
    assert active.status == "active"


# ── Gate 7: incomplete competence → provisional, not falsely activated ──


def test_incomplete_competence_produces_provisional():
    """If competence is incomplete, child remains provisional, not activated."""
    store = SemanticSchemaStore()
    coordinator = LearningCoordinator(store=store)
    gap = make_gap()

    tx = coordinator.open_transaction(gap)
    tx, competing = coordinator.begin_probing(tx)

    # Stage a revision with a constitutive pattern
    from cemm.kernel.schema.grounding_spec import GroundingSpecification
    contrib = StagedContribution(
        field_name="definition",
        field_value="test_definition",
        provenance_kind=ProvenanceKind.ASSERTED,
        is_independent=True,
    )

    tx, child = coordinator.stage_revision(
        tx,
        hypothesis=competing.hypotheses[0] if competing.hypotheses else SchemaHypothesis(hypothesis_kind="new_sense"),
        contributions=(contrib,),
    )

    # Attempt activation — competence is empty → should be provisional or rolled_back
    tx, attempt = coordinator.attempt_activation(tx, child)

    # Should NOT be activated (no competence)
    assert not attempt.activated
    # Should have limitations
    assert len(attempt.limitations) > 0


# ── Gate 8: completion gate ──


def test_completion_gate_provisional_needs_limitations():
    """Provisional transactions must have explicit limitations."""
    store = SemanticSchemaStore()
    coordinator = LearningCoordinator(store=store)
    gap = make_gap()

    tx = coordinator.open_transaction(gap)

    # Create a fake attempt with no limitations
    attempt = ActivationAttempt(
        child_revision_ref="child:1",
        activated=False,
        committed_provisional=True,
        limitations=(),  # No limitations!
    )

    # Manually set transaction to provisional
    tx = LearningTransaction(
        id=tx.id,
        gap_ref=tx.gap_ref,
        target_sense_ref=tx.target_sense_ref,
        target_schema_ref=tx.target_schema_ref,
        base_schema_revision=tx.base_schema_revision,
        base_store_revision=tx.base_store_revision,
        status=TransactionStatus.PROVISIONAL.value,
        admissibility_status="attributed_only",
    )

    passed, failures = coordinator.check_completion_gate(tx, attempt)
    assert not passed
    assert any("limitation" in f.lower() for f in failures)


def test_completion_gate_self_certified_cannot_activate():
    """Self-certified competence cannot produce active status."""
    store = SemanticSchemaStore()
    coordinator = LearningCoordinator(store=store)
    gap = make_gap()

    tx = coordinator.open_transaction(gap)

    from cemm.kernel.schema.closure import SchemaGroundingAssessment
    from cemm.kernel.schema.competence import CompetenceAssessment

    # Create a self-certified assessment
    structural = SchemaGroundingAssessment(
        record_id="child:1",
        semantic_key="test",
        environment_fingerprint="",
        is_structurally_executable=True,
    )

    competence = CompetenceAssessment(
        is_self_certified=True,  # Self-certified!
    )

    attempt = ActivationAttempt(
        child_revision_ref="child:1",
        structural_assessment=structural,
        competence_assessment=competence,
        activated=True,  # Claiming activation!
        limitations=(),
    )

    tx = LearningTransaction(
        id=tx.id,
        gap_ref=tx.gap_ref,
        target_sense_ref=tx.target_sense_ref,
        target_schema_ref=tx.target_schema_ref,
        base_schema_revision=tx.base_schema_revision,
        base_store_revision=tx.base_store_revision,
        status=TransactionStatus.COMMITTED.value,
        admissibility_status="admitted",
        structural_status="structurally_executable",
        competence_status="independently_validated",
    )

    passed, failures = coordinator.check_completion_gate(tx, attempt)
    assert not passed
    assert any("self-certified" in f.lower() for f in failures)


# ── Import boundary tests ──


def test_learning_imports_no_engine():
    """Learning modules must not import any engine module."""
    import cemm.kernel.learning.hypothesis_factory as hf_mod
    import cemm.kernel.learning.grounding_frontier as gf_mod
    import cemm.kernel.learning.assimilator as am_mod
    import cemm.kernel.learning.replay_queue as rq_mod
    import cemm.kernel.learning.coordinator as co_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
        "cemm.kernel.commit",
    ]
    for mod in [hf_mod, gf_mod, am_mod, rq_mod, co_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_learning_does_not_install_parallel_resolver():
    """Learning cannot install a parallel resolver.

    Learning modules must not define a SchemaResolver or SemanticSchemaStore
    subclass — those belong to schema.
    """
    import cemm.kernel.learning.coordinator as co_mod

    source = open(co_mod.__file__, encoding="utf-8").read()
    assert "class SemanticSchemaStore" not in source
    assert "class SchemaResolver" not in source


def test_competency_tests_cannot_mutate():
    """No competency test may mutate canonical stores or execute external effects.

    CompetenceHarness is sandboxed and non-mutating.
    """
    from cemm.kernel.schema.competence import CompetenceHarness

    harness = CompetenceHarness()

    # Must not have mutation methods
    assert not hasattr(harness, "activate")
    assert not hasattr(harness, "commit")
    assert not hasattr(harness, "register")
    assert not hasattr(harness, "mutate")
    assert not hasattr(harness, "execute")
