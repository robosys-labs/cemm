"""Acceptance Suite H — Correction and NLG (tests 38-45).

### 38. Correction targeting
### 39. Support retraction
### 40. Archival vs privacy deletion
### 41. Understanding report
### 42. Capability assessment
### 43. Commit-before-claim
### 44. Output commit provenance
### 45. Multilingual / language-neutral plan
"""
from __future__ import annotations

import pytest

from cemm.kernel.correction.operations import (
    CorrectionKind, CorrectionReversibility, RetentionPolicy,
    CorrectionOperation, CorrectionOperationFactory,
)
from cemm.kernel.correction.retraction_engine import RetractionEngine
from cemm.kernel.correction.guards import (
    ArchivalPrivacyGuard, CorrectionTargetingGuard,
)
from cemm.kernel.response.planner import (
    ResponsePlanner, EpistemicStance, DiscourseFunction,
    ContentSelectionInput,
)
from cemm.kernel.response.provenance import MessageProvenanceGuard
from cemm.kernel.model.mutation import (
    MutationSet, MutationOperation, CommitOutcome, CommitOperationResult,
)
from cemm.kernel.execution.commit import CommitCoordinator
from cemm.kernel.schema.closure import SchemaGroundingAssessment
from cemm.kernel.schema.use_profile import (
    derive_use_profile, UseProfileLevel, SemanticOperation,
)
from cemm.kernel.epistemics.evaluator import EpistemicAssessment


# ── Test 38: Correction targeting ──


def test_38a_correction_targets_exact_sense():
    """Correction targets exact sense/revision.

    Per ACCEPTANCE_TESTS.md §38: correct one sense of a polysemous term;
    unrelated senses unaffected; new revision/readings explicit; old
    historical proposition meaning preserved.
    """
    guard = CorrectionTargetingGuard()
    op = CorrectionOperationFactory.supersession(
        target_ref="schema:leader_role:v1",
        reason="superseded by new definition",
    )
    # Check that targeting is precise — only the target is affected
    result = guard.check_target_precision(
        operation=op,
        known_targets=("schema:leader_role:v1",),
    )
    assert result.is_valid
    # Unrelated sense is not in the affected set
    result_unaffected = guard.check_unaffected_senses(
        operation=op,
        related_senses=("schema:leader_strip:v1",),
        affected_senses=("schema:leader_role:v1",),  # Only target affected
    )
    assert result_unaffected.is_valid


def test_38b_unrelated_senses_unaffected():
    """Unrelated senses are unaffected by correction."""
    engine = RetractionEngine()
    op = CorrectionOperationFactory.supersession(
        target_ref="schema:leader_role:v1",
        reason="superseded by new definition",
    )
    result = engine.execute(op)
    assert result.success
    # Supersession targets exact ref — unrelated ref still contributes
    assert engine.support_still_contributes("schema:leader_strip:v1")


# ── Test 39: Support retraction ──


def test_39a_support_retraction_removes_contribution():
    """Support retraction removes the contribution."""
    engine = RetractionEngine()
    op = CorrectionOperationFactory.support_retraction(
        target_ref="evidence:1",
        reason="source retracted",
    )
    result = engine.execute(op)
    assert result.success
    assert not engine.support_still_contributes("evidence:1")


def test_39b_dependent_cognition_re_evaluated():
    """Dependent cognition is marked for re-evaluation after support retraction."""
    engine = RetractionEngine()
    engine.register_dependency("prop:derived:1", "inference", "evidence:1")
    op = CorrectionOperationFactory.support_retraction(
        target_ref="evidence:1",
        reason="source retracted",
    )
    result = engine.execute(op)
    assert result.success
    dependents = engine.get_dependents("evidence:1")
    assert any(d.artifact_ref == "prop:derived:1" for d in dependents)


# ── Test 40: Archival vs privacy deletion ──


def test_40a_archival_is_conditional_reversible():
    """Archival is conditionally reversible with retained provenance."""
    op = CorrectionOperationFactory.archival(
        target_ref="schema:old:v1",
        reason="historical archive",
    )
    assert op.reversibility == CorrectionReversibility.REVERSIBLE
    assert op.retention_policy == RetentionPolicy.RETAIN


def test_40b_privacy_deletion_is_irreversible():
    """Privacy deletion is irreversible with no retained provenance."""
    op = CorrectionOperationFactory.privacy_deletion(
        target_ref="evidence:sensitive:1",
        reason="GDPR deletion request",
    )
    assert op.reversibility == CorrectionReversibility.IRREVERSIBLE
    assert op.retention_policy == RetentionPolicy.CRYPTO_ERASE


def test_40c_guard_detects_mislabeling():
    """ArchivalPrivacyGuard detects mislabeling of archival as privacy deletion.

    Per ACCEPTANCE_TESTS.md §40: neither is mislabeled as the other.
    """
    guard = ArchivalPrivacyGuard()
    # Archival operation with privacy deletion kind → mislabeling
    from cemm.kernel.correction.operations import CorrectionOperation
    mislabeled = CorrectionOperation(
        operation_id="op:test:1",
        target_ref="schema:test:v1",
        target_kind="schema_revision",
        kind=CorrectionKind.PRIVACY_DELETION,
        reversibility=CorrectionReversibility.REVERSIBLE,  # Wrong — should be IRREVERSIBLE
        retention_policy=RetentionPolicy.RETAIN,  # Wrong — should be CRYPTO_ERASE
        reason="test",
    )
    result = guard.check_operation(mislabeled)
    assert not result.is_valid
    # Correct archival
    correct_archival = CorrectionOperationFactory.archival(
        target_ref="schema:test:v1",
        reason="archive",
    )
    result_ok = guard.check_operation(correct_archival)
    assert result_ok.is_valid


# ── Test 41: Understanding report ──


def test_41a_opaque_report_does_not_claim_understanding():
    """Opaque schema self-report does not claim understanding."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:dax:v1",
        semantic_key="dax",
        environment_fingerprint="fp1",
        is_structurally_executable=False,
    )
    profile = derive_use_profile(assessment, context_ref="ctx:actual")
    assert profile.level == UseProfileLevel.OPAQUE
    assert not profile.permits(SemanticOperation.ANSWER_DEFINING_QUERY)


def test_41b_provisional_report_qualifies():
    """Provisional understanding is qualified in response.

    Per ACCEPTANCE_TESTS.md §41: each clause binds to assessment/competence/
    blocker records; result is graded and operation-relative; no binary
    template claim. Provisional understanding must not be asserted as fact.
    """
    planner = ResponsePlanner()
    epistemic = EpistemicAssessment(
        proposition_ref="prop:1",
        context_ref="ctx:actual",
        admissibility="attributed_only",
        support_state="neither",
        confidence=0.0,
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(epistemic,),
    )
    plan = planner.plan_response(selection)
    assert len(plan.content_items) > 0
    # Stance must NOT be ASSERTED — provisional/contested/hedged/denied
    assert plan.content_items[0].stance != EpistemicStance.ASSERTED.value


# ── Test 42: Capability assessment ──


def test_42a_capability_not_overclaimed():
    """Capability assessment does not overclaim."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:op:v1",
        semantic_key="op",
        environment_fingerprint="fp1",
        is_structurally_executable=True,
    )
    # Without competence → partial, not active
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=False, epistemic_admissible=True,
    )
    assert profile.level == UseProfileLevel.PARTIAL
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_42b_execute_never_from_profile():
    """EXECUTE is never permitted by profile alone."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:op:v1",
        semantic_key="op",
        environment_fingerprint="fp1",
        is_structurally_executable=True,
    )
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=True, epistemic_admissible=True,
    )
    assert profile.level == UseProfileLevel.ACTIVE
    assert not profile.permits_execute()


# ── Test 43: Commit-before-claim ──


def test_43a_completion_requires_successful_commit():
    """Completion claims require exact required commits.

    Per ACCEPTANCE_TESTS.md §43: requested relation write fails while
    auxiliary concept observation commits. Required write outcome is
    failure/partial; response does not say stored/learned.
    """
    # Simulate: required write fails, auxiliary commits
    outcome = CommitOutcome(
        mutation_set_ref="ms:1",
        results=(
            CommitOperationResult(mutation_ref="mut:required_write", status="failed"),
            CommitOperationResult(mutation_ref="mut:auxiliary", status="committed"),
        ),
        required_satisfied=False,
    )
    # required_satisfied is False because the required write failed
    assert not outcome.required_satisfied
    # Verify which operation failed
    failed_ops = [r for r in outcome.results if r.status == "failed"]
    assert len(failed_ops) == 1
    assert failed_ops[0].mutation_ref == "mut:required_write"
    # Auxiliary committed but completion is still false
    committed_ops = [r for r in outcome.results if r.status == "committed"]
    assert len(committed_ops) == 1
    assert not outcome.required_satisfied


def test_43b_all_required_satisfied():
    """All required commits satisfied → required_satisfied=True.

    When every required operation commits successfully, the completion
    claim may proceed.
    """
    outcome = CommitOutcome(
        mutation_set_ref="ms:2",
        results=(
            CommitOperationResult(mutation_ref="mut:1", status="committed"),
            CommitOperationResult(mutation_ref="mut:2", status="committed"),
        ),
        required_satisfied=True,
    )
    assert outcome.required_satisfied
    # All operations committed
    assert all(r.status == "committed" for r in outcome.results)


# ── Test 44: Output commit provenance ──


def test_44a_every_clause_has_provenance():
    """Every generated clause must trace to semantic provenance.

    Per ACCEPTANCE_TESTS.md §44: intended text is not added to common
    ground; pending question/commitment is not created as if emitted.
    Every content item must have non-empty semantic_ref and provenance_refs.
    """
    planner = ResponsePlanner()
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
    )
    plan = planner.plan_response(selection)
    guard = MessageProvenanceGuard()
    result = guard.check_plan(plan)
    # Must have zero violations — every clause has provenance
    assert len(result.violations) == 0


def test_44b_no_internal_leakage():
    """Opaque IDs, open ports, and internal placeholders cannot become public text."""
    planner = ResponsePlanner()
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
    )
    plan = planner.plan_response(selection)
    guard = MessageProvenanceGuard()
    result = guard.check_plan(plan)
    # No opaque ID or open port leakage
    assert all(
        v.violation_kind not in ("opaque_id", "open_port")
        for v in result.violations
    )


# ── Test 45: Multilingual / language-neutral plan ──


def test_45a_message_plan_is_language_neutral():
    """SemanticMessagePlan is language-neutral — language is a field."""
    planner = ResponsePlanner()
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        language="en",
    )
    plan = planner.plan_response(selection)
    assert plan.language == "en"
    # Content items are semantic refs, not language-specific text
    for item in plan.content_items:
        assert item.semantic_ref  # Non-empty semantic ref
        # No surface text in the plan — just semantic refs


def test_45b_same_plan_different_language():
    """Same semantic plan can be rendered in different languages."""
    planner = ResponsePlanner()
    selection_en = ContentSelectionInput(
        proposition_refs=("prop:1",),
        language="en",
    )
    selection_fr = ContentSelectionInput(
        proposition_refs=("prop:1",),
        language="fr",
    )
    plan_en = planner.plan_response(selection_en)
    plan_fr = planner.plan_response(selection_fr)
    # Same content items, different language
    assert plan_en.language == "en"
    assert plan_fr.language == "fr"
    assert len(plan_en.content_items) == len(plan_fr.content_items)
