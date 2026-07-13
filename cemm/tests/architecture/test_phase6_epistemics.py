"""Phase 6 gate tests: Epistemic admissibility and self-awareness.

Gates (from IMPLEMENTATION_PLAN.md Phase 6):
- structurally complete false definitions remain attributed theories;
- `understands` states exact supported competencies and limitations;
- static schema declarations cannot advertise capabilities;
- self-report clauses are evidence-bound.

Additional guardrail tests from AGENTS.md §10-11, UNDERSTANDING_PIPELINE.md §12:
- Four support states: supported, refuted, both, neither
- Absence is not falsity
- knows(self, p) requires ALL 7 conditions
- stored/remembers/has_access/knows/understands/believes are never interchangeable
- EpistemicEvaluator is the sole truth and knowledge authority
- CapabilityEvaluator is the only capability authority
- 8 capability conditions required
- Observed reliability and degradation qualify capability result
- Import boundaries: epistemics → model+schema, self_model → model+schema
- self_model cannot maintain independent truth facts
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cemm.kernel.epistemics.evaluator import (
    EpistemicEvaluator, SupportState, AdmissibilityLevel,
    CausalWarrantGrade, EvidenceRecord, KnowledgeAssessment,
)
from cemm.kernel.epistemics.truth_maintenance import (
    TruthMaintenance, LineageGraph, LineageNode, ContradictionRecord,
)
from cemm.kernel.epistemics.knowledge_derivation import (
    KnowledgeDeriver, UnderstandingAssessment, BeliefAssessment, SelfReport,
)
from cemm.kernel.self_model.capability_evaluator import (
    CapabilityEvaluator, ComponentHealthRecord, ResourceRecord,
    ChannelRecord, PermissionRecord, CompetenceRecord,
    ImplementationRecord, ContextualPrecondition,
)
from cemm.kernel.self_model.self_report import (
    SelfReportBuilder, OperationRelativeUnderstanding,
)
from cemm.kernel.model.epistemic import EpistemicAssessment
from cemm.kernel.model.capability import CapabilityAssessment
from cemm.kernel.model.proposition import Proposition
from cemm.kernel.model.context_frame import ContextFrame
from cemm.kernel.model.identity import TimeExtent, Provenance, Scope, ScopeLevel
from cemm.kernel.schema.use_profile import (
    SchemaUseProfile, UseProfileLevel, SemanticOperation,
    OPAQUE_OPERATIONS, PARTIAL_OPERATIONS, ACTIVE_OPERATIONS, CAUSAL_OPERATIONS,
)
from cemm.kernel.schema.closure import SchemaGroundingAssessment


# ── Helpers ────────────────────────────────────────────────────────


def make_context(context_id: str = "ctx:actual", kind: str = "actual") -> ContextFrame:
    return ContextFrame(
        id=context_id,
        context_kind=kind,
        provenance=Provenance(source_id="test"),
    )


def make_proposition(prop_id: str = "prop:test") -> Proposition:
    return Proposition(
        id=prop_id,
        predication_ref="pred:test",
        context_ref="ctx:actual",
    )


def make_evidence(
    eid: str,
    prop_ref: str,
    supports: bool = True,
    confidence: float = 0.8,
    independent: bool = True,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=eid,
        proposition_ref=prop_ref,
        supports=supports,
        confidence=confidence,
        is_independent=independent,
        source_ref="source:test",
    )


def make_use_profile(level: UseProfileLevel = UseProfileLevel.ACTIVE) -> SchemaUseProfile:
    ops = {
        UseProfileLevel.OPAQUE: OPAQUE_OPERATIONS,
        UseProfileLevel.PARTIAL: PARTIAL_OPERATIONS,
        UseProfileLevel.ACTIVE: ACTIVE_OPERATIONS,
        UseProfileLevel.CAUSAL: CAUSAL_OPERATIONS,
        UseProfileLevel.INADMISSIBLE: frozenset(),
    }
    return SchemaUseProfile(
        schema_record_ref="schema:test:v1",
        context_ref="ctx:actual",
        level=level,
        permitted_semantic_operations=frozenset(op.value for op in ops[level]),
    )


# ── Gate 1: structurally complete false definitions remain attributed theories ──


def test_false_definition_in_belief_context_stays_attributed():
    """A structurally complete but false definition in a belief context
    must remain attributed_only, not admitted as actual-world knowledge.
    """
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:false_def")
    ctx = make_context("ctx:belief", "believed")

    # Even with support evidence, belief context → attributed_only
    evidence = (make_evidence("ev1", "prop:false_def", supports=True),)
    profile = make_use_profile(UseProfileLevel.ACTIVE)

    assessment = evaluator.evaluate(
        proposition=prop,
        context=ctx,
        evidence=evidence,
        schema_use_profile=profile,
    )

    assert assessment.admissibility == AdmissibilityLevel.ATTRIBUTED_ONLY.value


def test_false_definition_in_actual_context_is_blocked():
    """A refuted definition in actual context must be blocked."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:refuted")
    ctx = make_context("ctx:actual", "actual")

    # Counterevidence refutes it
    evidence = (make_evidence("ev1", "prop:refuted", supports=False),)
    profile = make_use_profile(UseProfileLevel.ACTIVE)

    assessment = evaluator.evaluate(
        proposition=prop,
        context=ctx,
        evidence=evidence,
        schema_use_profile=profile,
    )

    assert assessment.support_state == SupportState.REFUTED.value
    assert assessment.admissibility == AdmissibilityLevel.BLOCKED.value


def test_structurally_complete_but_no_evidence_is_blocked():
    """Structural completeness alone does not establish truth.

    A proposition with no evidence in actual context is blocked,
    not admitted. Absence is not falsity, but it's not truth either.
    """
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:no_evidence")
    ctx = make_context("ctx:actual", "actual")

    assessment = evaluator.evaluate(
        proposition=prop,
        context=ctx,
        evidence=(),
        schema_use_profile=make_use_profile(UseProfileLevel.ACTIVE),
    )

    assert assessment.support_state == SupportState.NEITHER.value
    assert assessment.admissibility == AdmissibilityLevel.BLOCKED.value


def test_hypothetical_context_is_attributed():
    """Hypothetical context propositions are attributed_only."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:hyp")
    ctx = make_context("ctx:hyp", "hypothetical")

    assessment = evaluator.evaluate(
        proposition=prop,
        context=ctx,
        schema_use_profile=make_use_profile(UseProfileLevel.ACTIVE),
    )

    assert assessment.admissibility == AdmissibilityLevel.ATTRIBUTED_ONLY.value


# ── Gate 2: understands states exact supported competencies and limitations ──


def test_understands_states_exact_competencies():
    """understands must state exact supported competencies."""
    deriver = KnowledgeDeriver()
    profile = make_use_profile(UseProfileLevel.ACTIVE)

    understanding = deriver.derive_understanding(
        schema_record_ref="schema:test:v1",
        use_profile=profile,
    )

    assert understanding.is_understood
    assert len(understanding.exact_competencies) > 0
    assert "recognize" in understanding.exact_competencies
    assert "classify" in understanding.exact_competencies


def test_understands_states_exact_limitations():
    """understands must state exact limitations."""
    deriver = KnowledgeDeriver()
    profile = make_use_profile(UseProfileLevel.OPAQUE)

    understanding = deriver.derive_understanding(
        schema_record_ref="schema:opaque:v1",
        use_profile=profile,
        blocker_reasons=("No constitutive pattern",),
    )

    assert not understanding.is_understood
    assert len(understanding.exact_limitations) > 0
    assert any("opaque" in lim for lim in understanding.exact_limitations)


def test_understands_partial_states_limitations():
    """Partial understanding states what it can and cannot do."""
    deriver = KnowledgeDeriver()
    profile = make_use_profile(UseProfileLevel.PARTIAL)

    understanding = deriver.derive_understanding(
        schema_record_ref="schema:partial:v1",
        use_profile=profile,
    )

    assert understanding.is_understood
    assert "typed reference" in understanding.exact_competencies
    assert any("classify" in lim for lim in understanding.exact_limitations)


def test_understands_is_operation_relative():
    """understands is operation-relative — same schema, different operations."""
    builder = SelfReportBuilder()
    profile = make_use_profile(UseProfileLevel.PARTIAL)

    # Can do typed_reference (partial permits it)
    understanding_yes = builder.derive_operation_relative_understanding(
        schema_record_ref="schema:test:v1",
        use_profile=profile,
        requested_operation=SemanticOperation.TYPED_REFERENCE,
    )
    assert understanding_yes.can_perform

    # Cannot do classify (partial does not permit it)
    understanding_no = builder.derive_operation_relative_understanding(
        schema_record_ref="schema:test:v1",
        use_profile=profile,
        requested_operation=SemanticOperation.CLASSIFY,
    )
    assert not understanding_no.can_perform


# ── Gate 3: static schema declarations cannot advertise capabilities ──


def test_static_schema_cannot_advertise_capability():
    """A static schema declaration cannot override live capability evidence.

    CapabilityEvaluator requires ALL 8 conditions from live records.
    """
    evaluator = CapabilityEvaluator()

    # Even with competence, if implementation is not registered → incapable
    assessment = evaluator.evaluate(
        subject_ref="ref:self",
        operation_schema_ref="op:test",
        competence=CompetenceRecord(
            schema_ref="op:test",
            is_competent=True,
            competence_score=0.9,
        ),
        implementation=ImplementationRecord(
            operation_ref="op:test",
            is_registered=False,  # Not registered!
        ),
        component_health=ComponentHealthRecord(component_id="comp1", health="healthy"),
        input_channel=ChannelRecord(channel_kind="input", channel_id="ch1", is_available=True),
        output_channel=ChannelRecord(channel_kind="output", channel_id="ch2", is_available=True),
        resources=(ResourceRecord(resource_kind="tokens", status="available", available_amount=100, required_amount=10),),
        permission=PermissionRecord(operation_ref="op:test", is_allowed=True),
        preconditions=(ContextualPrecondition(precondition_id="pre1", is_satisfied=True),),
    )

    assert assessment.status == "incapable"
    assert "no registered implementation" in assessment.limitations


def test_capability_requires_all_8_conditions():
    """Capability requires all 8 conditions to be met."""
    evaluator = CapabilityEvaluator()

    # All 8 conditions met → capable
    assessment = evaluator.evaluate(
        subject_ref="ref:self",
        operation_schema_ref="op:test",
        competence=CompetenceRecord(schema_ref="op:test", is_competent=True, competence_score=0.9),
        implementation=ImplementationRecord(operation_ref="op:test", is_registered=True, implementation_id="impl1"),
        component_health=ComponentHealthRecord(component_id="comp1", health="healthy"),
        input_channel=ChannelRecord(channel_kind="input", channel_id="ch1", is_available=True),
        output_channel=ChannelRecord(channel_kind="output", channel_id="ch2", is_available=True),
        resources=(ResourceRecord(resource_kind="tokens", status="available", available_amount=100, required_amount=10),),
        permission=PermissionRecord(operation_ref="op:test", is_allowed=True),
        preconditions=(ContextualPrecondition(precondition_id="pre1", is_satisfied=True),),
    )

    assert assessment.status == "capable"
    assert len(assessment.condition_results) == 8
    assert all(c.satisfied for c in assessment.condition_results)


def test_capability_with_degraded_component():
    """Degraded component qualifies the capability result."""
    evaluator = CapabilityEvaluator()

    assessment = evaluator.evaluate(
        subject_ref="ref:self",
        operation_schema_ref="op:test",
        competence=CompetenceRecord(schema_ref="op:test", is_competent=True, competence_score=0.9),
        implementation=ImplementationRecord(operation_ref="op:test", is_registered=True, implementation_id="impl1"),
        component_health=ComponentHealthRecord(component_id="comp1", health="degraded"),
        input_channel=ChannelRecord(channel_kind="input", channel_id="ch1", is_available=True),
        output_channel=ChannelRecord(channel_kind="output", channel_id="ch2", is_available=True),
        resources=(ResourceRecord(resource_kind="tokens", status="available", available_amount=100, required_amount=10),),
        permission=PermissionRecord(operation_ref="op:test", is_allowed=True),
        preconditions=(ContextualPrecondition(precondition_id="pre1", is_satisfied=True),),
    )

    # Degraded but all conditions met → degraded
    assert assessment.status == "degraded"
    assert "component degraded" in assessment.limitations


def test_capability_with_exhausted_resources():
    """Exhausted resources make capability incapable."""
    evaluator = CapabilityEvaluator()

    assessment = evaluator.evaluate(
        subject_ref="ref:self",
        operation_schema_ref="op:test",
        competence=CompetenceRecord(schema_ref="op:test", is_competent=True, competence_score=0.9),
        implementation=ImplementationRecord(operation_ref="op:test", is_registered=True, implementation_id="impl1"),
        component_health=ComponentHealthRecord(component_id="comp1", health="healthy"),
        input_channel=ChannelRecord(channel_kind="input", channel_id="ch1", is_available=True),
        output_channel=ChannelRecord(channel_kind="output", channel_id="ch2", is_available=True),
        resources=(ResourceRecord(resource_kind="tokens", status="exhausted", available_amount=0, required_amount=10),),
        permission=PermissionRecord(operation_ref="op:test", is_allowed=True),
        preconditions=(ContextualPrecondition(precondition_id="pre1", is_satisfied=True),),
    )

    assert assessment.status == "incapable"
    assert "resource tokens exhausted" in assessment.limitations


# ── Gate 4: self-report clauses are evidence-bound ──


def test_unbacked_self_report_is_realization_error():
    """An unbacked epistemic clause is a realization error."""
    deriver = KnowledgeDeriver()

    with pytest.raises(AssertionError, match="Unbacked"):
        deriver.create_self_report(
            report_kind="knows",
            is_true=True,
            evidence_refs=(),  # No evidence!
        )


def test_backed_self_report_succeeds():
    """A backed self-report succeeds."""
    deriver = KnowledgeDeriver()

    report = deriver.create_self_report(
        report_kind="knows",
        is_true=True,
        evidence_refs=("prop:test",),
    )

    assert report.is_backed
    assert report.is_true


def test_self_report_knows_with_limitations():
    """Self-report for knows states specific limitations when not known."""
    builder = SelfReportBuilder()
    knowledge = KnowledgeAssessment(
        proposition_ref="prop:test",
        is_known=False,
        is_grounded=False,
        limitations=["proposition not grounded"],
    )

    report = builder.report_knows("prop:test", knowledge)

    assert not report.is_true
    assert "proposition not grounded" in report.limitations


def test_self_report_describes_understanding():
    """Self-report for understands describes exact state."""
    builder = SelfReportBuilder()
    understanding = UnderstandingAssessment(
        schema_record_ref="schema:test:v1",
        is_understood=True,
        competence_level="active",
        exact_competencies=("recognize", "classify"),
        exact_limitations=(),
    )

    report = builder.report_understands("schema:test:v1", understanding)

    assert report.is_true
    assert report.is_backed


# ── Four-state support tests ──


def test_supported_state():
    """Supported: evidence for, none against."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:sup")
    ctx = make_context()
    evidence = (make_evidence("ev1", "prop:sup", supports=True),)

    assessment = evaluator.evaluate(prop, ctx, evidence, make_use_profile())
    assert assessment.support_state == SupportState.SUPPORTED.value


def test_refuted_state():
    """Refuted: evidence against, none for."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:ref")
    ctx = make_context()
    evidence = (make_evidence("ev1", "prop:ref", supports=False),)

    assessment = evaluator.evaluate(prop, ctx, evidence, make_use_profile())
    assert assessment.support_state == SupportState.REFUTED.value


def test_both_state():
    """Both: evidence for and against."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:both")
    ctx = make_context()
    evidence = (
        make_evidence("ev1", "prop:both", supports=True),
        make_evidence("ev2", "prop:both", supports=False),
    )

    assessment = evaluator.evaluate(prop, ctx, evidence, make_use_profile())
    assert assessment.support_state == SupportState.BOTH.value
    assert assessment.admissibility == AdmissibilityLevel.CONTESTED.value


def test_neither_state():
    """Neither: no evidence for or against. Absence is not falsity."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:neither")
    ctx = make_context()

    assessment = evaluator.evaluate(prop, ctx, (), make_use_profile())
    assert assessment.support_state == SupportState.NEITHER.value
    # Absence is not falsity, but not admitted either
    assert assessment.admissibility == AdmissibilityLevel.BLOCKED.value


# ── knows(self, p) requires ALL 7 conditions ──


def test_knows_requires_all_7_conditions():
    """knows(self, p) requires all 7 conditions to be met."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:know")
    ctx = make_context()
    evidence = (make_evidence("ev1", "prop:know", supports=True),)
    profile = make_use_profile(UseProfileLevel.ACTIVE)

    assessment = evaluator.evaluate(prop, ctx, evidence, profile)

    # All conditions met → knows
    knowledge = evaluator.derive_knowledge(
        proposition=prop,
        context=ctx,
        assessment=assessment,
        is_grounded=True,
        schema_use_profile=profile,
    )
    assert knowledge.is_known


def test_knows_fails_without_grounded():
    """knows fails if proposition is not grounded."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:ungrounded")
    ctx = make_context()
    evidence = (make_evidence("ev1", "prop:ungrounded", supports=True),)
    profile = make_use_profile(UseProfileLevel.ACTIVE)

    assessment = evaluator.evaluate(prop, ctx, evidence, profile)

    knowledge = evaluator.derive_knowledge(
        proposition=prop,
        context=ctx,
        assessment=assessment,
        is_grounded=False,  # Not grounded!
        schema_use_profile=profile,
    )
    assert not knowledge.is_known
    assert "proposition not grounded" in knowledge.limitations


def test_knows_fails_without_accessible():
    """knows fails if record is not accessible."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:inaccessible")
    ctx = make_context()
    evidence = (make_evidence("ev1", "prop:inaccessible", supports=True),)
    profile = make_use_profile(UseProfileLevel.ACTIVE)

    assessment = evaluator.evaluate(
        prop, ctx, evidence, profile,
        accessible=False,  # Not accessible!
    )

    knowledge = evaluator.derive_knowledge(
        proposition=prop,
        context=ctx,
        assessment=assessment,
        is_grounded=True,
        schema_use_profile=profile,
    )
    assert not knowledge.is_known
    assert "record not accessible" in knowledge.limitations


def test_knows_fails_without_executable_schemas():
    """knows fails if schemas are not executable."""
    evaluator = EpistemicEvaluator()
    prop = make_proposition("prop:no_schema")
    ctx = make_context()
    evidence = (make_evidence("ev1", "prop:no_schema", supports=True),)
    profile = make_use_profile(UseProfileLevel.OPAQUE)  # Opaque = not executable

    assessment = evaluator.evaluate(prop, ctx, evidence, profile)

    knowledge = evaluator.derive_knowledge(
        proposition=prop,
        context=ctx,
        assessment=assessment,
        is_grounded=True,
        schema_use_profile=profile,
    )
    assert not knowledge.is_known
    assert "schemas not executable" in knowledge.limitations


# ── stored/remembers/has_access/knows/understands/believes are distinct ──


def test_believes_is_distinct_from_knows():
    """believes(self, p) is distinct from knows(self, p)."""
    deriver = KnowledgeDeriver()
    evaluator = EpistemicEvaluator()

    prop = make_proposition("prop:belief")
    ctx = make_context("ctx:belief", "believed")
    evidence = (make_evidence("ev1", "prop:belief", supports=True),)

    assessment = evaluator.evaluate(prop, ctx, evidence, make_use_profile())
    belief = deriver.derive_belief(prop, ctx, assessment)

    # Can believe in belief context
    assert belief.is_believed

    # But cannot know in belief context (admissibility is attributed_only)
    knowledge = evaluator.derive_knowledge(
        proposition=prop,
        context=ctx,
        assessment=assessment,
        is_grounded=True,
        schema_use_profile=make_use_profile(),
    )
    # knows requires admissibility == admitted, but belief context gives attributed_only
    assert not knowledge.is_known


def test_remembers_is_distinct_from_knows():
    """remembers(self, p) is distinct from knows(self, p)."""
    builder = SelfReportBuilder()

    # Can remember without knowing
    report_remembers = builder.report_remembers("prop:remembered", was_retrieved=True)
    assert report_remembers.is_true  # Remembers
    assert report_remembers.report_kind == "remembers"

    # But knowing requires full epistemic conditions
    knowledge = KnowledgeAssessment(
        proposition_ref="prop:remembered",
        is_known=False,
        is_grounded=False,
        limitations=["proposition not grounded"],
    )
    report_knows = builder.report_knows("prop:remembered", knowledge)
    assert not report_knows.is_true  # Does not know
    assert report_knows.report_kind == "knows"


# ── Truth maintenance tests ──


def test_truth_maintenance_aggregates_evidence():
    """Truth maintenance aggregates support and opposition."""
    tm = TruthMaintenance()
    tm.add_evidence(make_evidence("ev1", "prop:tm", supports=True, confidence=0.7))
    tm.add_evidence(make_evidence("ev2", "prop:tm", supports=True, confidence=0.5))
    tm.add_evidence(make_evidence("ev3", "prop:tm", supports=False, confidence=0.3))

    support, opposition, independent = tm.aggregate_support("prop:tm")
    assert support == pytest.approx(1.2)
    assert opposition == pytest.approx(0.3)
    assert independent == 2  # ev1 and ev2 are independent


def test_truth_maintenance_detects_contradiction():
    """Truth maintenance detects contradictions."""
    tm = TruthMaintenance()
    tm.add_evidence(make_evidence("ev1", "prop:a", supports=True))
    tm.add_evidence(make_evidence("ev2", "prop:b", supports=False))

    contradiction = tm.detect_contradiction("prop:a", "prop:b")
    assert contradiction is not None
    assert contradiction.contradiction_kind == "direct"


def test_truth_maintenance_invalidation():
    """Truth maintenance tracks invalidation."""
    tm = TruthMaintenance()
    tm.invalidate("prop:stale")
    assert tm.is_invalidated("prop:stale")

    tm.clear_invalidation("prop:stale")
    assert not tm.is_invalidated("prop:stale")


def test_lineage_independence():
    """Lineage independence follows derivation lineage."""
    nodes = (
        LineageNode(node_id="n1", is_independent=True, independence_key="src_a"),
        LineageNode(node_id="n2", parent_refs=("n1",), derivation_kind="translated"),
        LineageNode(node_id="n3", is_independent=True, independence_key="src_b"),
    )
    graph = LineageGraph(nodes=nodes)

    # n1 and n3 are independent roots
    roots = graph.independent_roots()
    assert "n1" in roots
    assert "n3" in roots

    # n2's lineage goes through n1
    lineage = graph.lineage_of("n2")
    assert lineage[0] == "n1"  # Root is n1

    # Independence count: n1 and n3 are independent, n2 inherits from n1
    assert graph.independence_count(("n1", "n2", "n3")) == 2


# ── Import boundary tests ──


def test_epistemics_imports_no_engine():
    """Epistemics modules must not import any engine module."""
    import cemm.kernel.epistemics.evaluator as eval_mod
    import cemm.kernel.epistemics.truth_maintenance as tm_mod
    import cemm.kernel.epistemics.knowledge_derivation as kd_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
        "cemm.kernel.commit",
    ]
    for mod in [eval_mod, tm_mod, kd_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_self_model_imports_no_engine():
    """Self model modules must not import any engine module."""
    import cemm.kernel.self_model.capability_evaluator as cap_mod
    import cemm.kernel.self_model.self_report as sr_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
        "cemm.kernel.commit",
    ]
    for mod in [cap_mod, sr_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_self_model_does_not_maintain_truth_facts():
    """self_model cannot maintain independent truth facts.

    self_model modules must not define truth maintenance or epistemic
    evaluation — those belong to epistemics.
    """
    import cemm.kernel.self_model.capability_evaluator as cap_mod
    import cemm.kernel.self_model.self_report as sr_mod

    forbidden_classes = [
        "TruthMaintenance",
        "EpistemicEvaluator",
        "class EpistemicAssessment",
    ]
    for mod in [cap_mod, sr_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for fc in forbidden_classes:
            assert f"class {fc}" not in source, (
                f"{mod.__file__} defines forbidden class {fc}"
            )


def test_epistemic_evaluator_is_sole_truth_authority():
    """EpistemicEvaluator must not have activation or mutation methods."""
    evaluator = EpistemicEvaluator()

    assert not hasattr(evaluator, "activate")
    assert not hasattr(evaluator, "set_status")
    assert not hasattr(evaluator, "commit")
    assert not hasattr(evaluator, "register")
    assert not hasattr(evaluator, "mutate")


def test_capability_evaluator_is_sole_capability_authority():
    """CapabilityEvaluator must not have activation or mutation methods."""
    evaluator = CapabilityEvaluator()

    assert not hasattr(evaluator, "activate")
    assert not hasattr(evaluator, "set_status")
    assert not hasattr(evaluator, "commit")
    assert not hasattr(evaluator, "register")
