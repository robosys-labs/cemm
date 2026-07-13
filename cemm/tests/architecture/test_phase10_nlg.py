"""Phase 10 gate tests: NLG, common ground, and repair.

Gates (from IMPLEMENTATION_PLAN.md Phase 10):
- every clause has semantic provenance;
- no internal IDs or open ports leak;
- generated content reparses compatibly;
- invalidated prior output can generate a repair obligation.

Additional guardrail tests from AGENTS.md §13, §19, §20,
ACCEPTANCE_TESTS.md §41-44, AUTHORITY_MATRIX:
- ResponsePlanner is the sole response-content authority
- Response content begins from propositions/assessments/ledger/commit outcomes
- Qualified language for reported/provisional/contested/hedged/stale
- CommonGroundManager records only dispatched communication
- Output common-ground mutation occurs only after dispatch success
- Intended text is not added to common ground
- Commit-before-claim: response does not say stored/learned when required write fails
- Import boundaries: response → model + epistemics only
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from cemm.kernel.response.planner import (
    ResponsePlanner, ContentSelectionInput, EpistemicStance, DiscourseFunction,
)
from cemm.kernel.response.provenance import (
    MessageProvenanceGuard, ProvenanceCheckResult, ProvenanceViolation,
)
from cemm.kernel.response.reparse_validator import (
    ReparseValidator, ReparseResult,
)
from cemm.kernel.response.common_ground import (
    CommonGroundManager, RepairObligationGenerator, RepairObligation,
    CommonGroundEntry, DiscourseStatus, DispatchStatus, DispatchResult,
)
from cemm.kernel.model.message import (
    SemanticMessagePlan, MessageContentItem, RhetoricalRelation,
)
from cemm.kernel.model.epistemic import EpistemicAssessment
from cemm.kernel.model.mutation import (
    MutationSet, MutationOperation, CommitOutcome, CommitOperationResult,
)
from cemm.kernel.model.execution import TypedFailure


# ── Helpers ────────────────────────────────────────────────────────


def make_assessment(
    prop_ref: str = "prop:1",
    admissibility: str = "admitted",
    support_state: str = "supported",
    confidence: float = 0.9,
    schema_use_valid: bool = True,
) -> EpistemicAssessment:
    return EpistemicAssessment(
        proposition_ref=prop_ref,
        context_ref="ctx:actual",
        admissibility=admissibility,
        support_state=support_state,
        confidence=confidence,
        schema_use_valid=schema_use_valid,
    )


def make_content_item(
    semantic_ref: str = "prop:1",
    provenance_refs: tuple[str, ...] = ("prop:1", "ev:1"),
    focus: str = "",
) -> MessageContentItem:
    return MessageContentItem(
        semantic_ref=semantic_ref,
        provenance_refs=provenance_refs,
        focus=focus,
    )


def make_commit_outcome(required_satisfied: bool = True) -> CommitOutcome:
    return CommitOutcome(
        mutation_set_ref="ms:1",
        results=(
            CommitOperationResult(mutation_ref="mut:1", status="committed"),
        ),
        required_satisfied=required_satisfied,
        committed_revision=1 if required_satisfied else None,
    )


# ── Gate 1: every clause has semantic provenance ──


def test_every_clause_has_semantic_provenance():
    """Every clause has semantic provenance."""
    planner = ResponsePlanner()
    guard = MessageProvenanceGuard()

    selection = ContentSelectionInput(
        proposition_refs=("prop:1", "prop:2"),
        assessments=(
            make_assessment("prop:1"),
            make_assessment("prop:2"),
        ),
    )

    plan = planner.plan_response(selection)

    # Every content item must have semantic_ref and provenance_refs
    for item in plan.content_items:
        assert item.semantic_ref, f"item has empty semantic_ref"
        assert item.provenance_refs, f"item {item.semantic_ref} has no provenance_refs"

    # Provenance guard confirms validity
    result = guard.check_plan(plan)
    assert result.is_valid, f"provenance violations: {result.violations}"


def test_missing_provenance_detected():
    """Content items without provenance are detected."""
    guard = MessageProvenanceGuard()

    plan = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=(),  # No provenance!
            ),
        ),
    )

    result = guard.check_plan(plan)
    assert not result.is_valid
    assert any(v.violation_kind == "missing_provenance" for v in result.violations)


def test_empty_semantic_ref_detected():
    """Content items with empty semantic_ref are detected."""
    guard = MessageProvenanceGuard()

    plan = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="",
                provenance_refs=("ev:1",),
            ),
        ),
    )

    result = guard.check_plan(plan)
    assert not result.is_valid
    assert any(v.violation_kind == "missing_provenance" for v in result.violations)


# ── Gate 2: no internal IDs or open ports leak ──


def test_no_opaque_id_leak_in_focus():
    """No internal IDs leak into public text (focus field)."""
    guard = MessageProvenanceGuard()

    plan = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=("prop:1",),
                focus="ref:schema:test:v1",  # Opaque ID!
            ),
        ),
    )

    result = guard.check_plan(plan)
    assert not result.is_valid
    assert any(v.violation_kind == "opaque_id" for v in result.violations)


def test_no_open_port_leak_in_focus():
    """No open ports leak into public text."""
    guard = MessageProvenanceGuard()

    plan = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=("prop:1",),
                focus="open_port unfilled",  # Open port!
            ),
        ),
    )

    result = guard.check_plan(plan)
    assert not result.is_valid
    assert any(v.violation_kind == "open_port" for v in result.violations)


def test_no_role_label_leak_in_focus():
    """No role labels leak into public text."""
    guard = MessageProvenanceGuard()

    plan = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=("prop:1",),
                focus="actor does something",  # Role label!
            ),
        ),
    )

    result = guard.check_plan(plan)
    assert not result.is_valid
    assert any(v.violation_kind == "role_label" for v in result.violations)


def test_clean_focus_passes():
    """Clean focus text passes the guard."""
    guard = MessageProvenanceGuard()

    plan = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=("prop:1", "ev:1"),
                focus="commit_success",
            ),
        ),
    )

    result = guard.check_plan(plan)
    assert result.is_valid


# ── Bug regression tests ──


def test_refuted_attributed_only_is_denied_not_reported():
    """Regression: a refuted reported claim should be DENIED, not REPORTED.
    Support state refutation must override attributed_only admissibility."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        admissibility="attributed_only",
        support_state="refuted",
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.DENIED.value


def test_both_support_with_attributed_only_is_contested():
    """Regression: both support+opposition with attributed_only should be
    CONTESTED, not REPORTED."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        admissibility="attributed_only",
        support_state="both",
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.CONTESTED.value


def test_commit_provenance_does_not_pollute_other_items():
    """Regression: commit_outcome provenance should not appear on
    unrelated proposition content items."""
    planner = ResponsePlanner()

    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(make_assessment("prop:1"),),
        commit_outcome=make_commit_outcome(required_satisfied=True),
    )

    plan = planner.plan_response(selection)

    # Find the proposition content item (not the commit one)
    prop_items = [
        item for item in plan.content_items
        if item.semantic_ref == "prop:1"
    ]
    assert len(prop_items) == 1

    # The proposition item should NOT have the commit's mutation_set_ref
    assert "ms:1" not in prop_items[0].provenance_refs


# ── Gate 3: generated content reparses compatibly ──


def test_reparse_compatible():
    """Generated content reparses compatibly."""
    validator = ReparseValidator()

    original = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            make_content_item("prop:1"),
            make_content_item("prop:2"),
        ),
    )

    reparsed = SemanticMessagePlan(
        id="plan:1_reparse",
        content_items=(
            make_content_item("prop:1"),
            make_content_item("prop:2"),
        ),
    )

    result = validator.validate_reparse(original, reparsed)
    assert result.is_compatible


def test_reparse_missing_refs_detected():
    """Reparse missing original refs is detected."""
    validator = ReparseValidator()

    original = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            make_content_item("prop:1"),
            make_content_item("prop:2"),
        ),
    )

    reparsed = SemanticMessagePlan(
        id="plan:1_reparse",
        content_items=(
            make_content_item("prop:1"),  # Missing prop:2
        ),
    )

    result = validator.validate_reparse(original, reparsed)
    assert not result.is_compatible
    assert "prop:2" in result.mismatched_refs


def test_reparse_discourse_function_mismatch():
    """Reparse with different discourse functions is detected."""
    validator = ReparseValidator()

    original = SemanticMessagePlan(
        id="plan:1",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="inform",
                provenance_refs=("prop:1",),
            ),
        ),
    )

    reparsed = SemanticMessagePlan(
        id="plan:1_reparse",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="query",  # Different!
                provenance_refs=("prop:1",),
            ),
        ),
    )

    result = validator.validate_reparse(original, reparsed)
    assert not result.is_compatible


def test_reparse_round_trip():
    """Round-trip reparse via a function."""
    validator = ReparseValidator()

    original = SemanticMessagePlan(
        id="plan:1",
        content_items=(make_content_item("prop:1"),),
    )

    # Simple reparse function that returns a compatible plan
    def reparse_fn(text: str) -> SemanticMessagePlan:
        return SemanticMessagePlan(
            id="reparse",
            content_items=(make_content_item("prop:1"),),
        )

    result = validator.check_round_trip(original, "some text", reparse_fn)
    assert result.is_compatible


# ── Gate 4: invalidated prior output generates repair obligation ──


def test_invalidated_output_generates_repair_obligation():
    """Invalidated prior output can generate a repair obligation."""
    generator = RepairObligationGenerator()

    obligation = generator.generate_from_invalidation(
        invalidated_message_ref="msg:1",
        reason="schema downgraded",
        original_proposition_ref="prop:1",
    )

    assert obligation.obligation_id == "repair:msg:1"
    assert obligation.invalidated_message_ref == "msg:1"
    assert not obligation.is_fulfilled


def test_repair_obligation_can_be_fulfilled():
    """Repair obligations can be fulfilled."""
    generator = RepairObligationGenerator()

    obligation = generator.generate_from_invalidation(
        invalidated_message_ref="msg:1",
    )

    assert generator.fulfill(obligation.obligation_id)
    assert len(generator.get_pending_repairs()) == 0


def test_repair_obligation_in_response_plan():
    """Repair obligations appear in response plan as repair content."""
    planner = ResponsePlanner()

    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(make_assessment("prop:1"),),
        repair_obligation_refs=("repair:msg:1",),
    )

    plan = planner.plan_response(selection)

    # Should have a repair content item
    repair_items = [
        item for item in plan.content_items
        if item.discourse_function == DiscourseFunction.REPAIR.value
    ]
    assert len(repair_items) == 1
    assert repair_items[0].stance == EpistemicStance.STALE.value


# ── Qualified language tests ──


def test_qualified_language_reported_theory():
    """Reported theory produces REPORTED stance."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        admissibility="attributed_only",
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.REPORTED.value


def test_qualified_language_provisional():
    """Provisional understanding produces PROVISIONAL stance."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        schema_use_valid=False,
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.PROVISIONAL.value


def test_qualified_language_contested():
    """Contested evidence produces CONTESTED stance."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        admissibility="contested",
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.CONTESTED.value


def test_qualified_language_hedged():
    """Known limitations produce HEDGED stance."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        confidence=0.3,  # Low confidence
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.HEDGED.value


def test_qualified_language_denied():
    """Refuted/blocked propositions produce DENIED stance."""
    planner = ResponsePlanner()

    assessment = make_assessment(
        admissibility="blocked",
    )
    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(assessment,),
    )

    plan = planner.plan_response(selection)
    assert plan.content_items[0].stance == EpistemicStance.DENIED.value


# ── CommonGroundManager tests ──


def test_common_ground_records_dispatched_only():
    """CommonGroundManager records only dispatched communication."""
    manager = CommonGroundManager()

    dispatch = DispatchResult(
        message_plan_ref="plan:1",
        status=DispatchStatus.DISPATCHED,
        dispatched_at=datetime.now(timezone.utc).isoformat(),
    )

    entry = manager.record_dispatch(
        proposition_ref="prop:1",
        participant_ref="user:1",
        discourse_status=DiscourseStatus.ASSERTED,
        dispatch_result=dispatch,
    )

    assert entry.dispatch_status == DispatchStatus.DISPATCHED
    assert manager.is_dispatched("prop:1")


def test_common_ground_rejects_non_dispatched():
    """CommonGroundManager rejects non-dispatched communication."""
    manager = CommonGroundManager()

    dispatch = DispatchResult(
        message_plan_ref="plan:1",
        status=DispatchStatus.FAILED,  # Not dispatched!
    )

    with pytest.raises(ValueError, match="dispatched communication"):
        manager.record_dispatch(
            proposition_ref="prop:1",
            participant_ref="user:1",
            discourse_status=DiscourseStatus.ASSERTED,
            dispatch_result=dispatch,
        )


def test_intended_text_not_recorded():
    """Intended text is not added to common ground."""
    manager = CommonGroundManager()

    # try_record_intended always returns False
    result = manager.try_record_intended(
        proposition_ref="prop:1",
        participant_ref="user:1",
        discourse_status=DiscourseStatus.ASSERTED,
    )
    assert not result
    assert not manager.is_dispatched("prop:1")


def test_common_ground_tracks_asked_and_answered():
    """CommonGroundManager tracks asked and answered propositions."""
    manager = CommonGroundManager()

    # User asks a question
    dispatch_ask = DispatchResult(
        message_plan_ref="plan:1",
        status=DispatchStatus.DISPATCHED,
        dispatched_at="2026-01-01T00:00:00Z",
    )
    manager.record_dispatch(
        proposition_ref="prop:question:1",
        participant_ref="user:1",
        discourse_status=DiscourseStatus.ASKED,
        dispatch_result=dispatch_ask,
    )

    # System answers
    dispatch_answer = DispatchResult(
        message_plan_ref="plan:2",
        status=DispatchStatus.DISPATCHED,
        dispatched_at="2026-01-01T00:01:00Z",
    )
    manager.record_dispatch(
        proposition_ref="prop:question:1",
        participant_ref="system:1",
        discourse_status=DiscourseStatus.ANSWERED,
        dispatch_result=dispatch_answer,
    )

    # No open questions
    open_qs = manager.get_open_questions()
    assert len(open_qs) == 0


def test_common_ground_open_question():
    """Open questions (asked but not answered) are tracked."""
    manager = CommonGroundManager()

    dispatch = DispatchResult(
        message_plan_ref="plan:1",
        status=DispatchStatus.DISPATCHED,
        dispatched_at="2026-01-01T00:00:00Z",
    )
    manager.record_dispatch(
        proposition_ref="prop:question:1",
        participant_ref="user:1",
        discourse_status=DiscourseStatus.ASKED,
        dispatch_result=dispatch,
    )

    open_qs = manager.get_open_questions()
    assert len(open_qs) == 1


def test_common_ground_correction():
    """CommonGroundManager tracks corrections."""
    manager = CommonGroundManager()

    # Original assertion
    dispatch1 = DispatchResult(
        message_plan_ref="plan:1",
        status=DispatchStatus.DISPATCHED,
        dispatched_at="2026-01-01T00:00:00Z",
    )
    entry1 = manager.record_dispatch(
        proposition_ref="prop:1",
        participant_ref="system:1",
        discourse_status=DiscourseStatus.ASSERTED,
        dispatch_result=dispatch1,
    )

    # Correction
    dispatch2 = DispatchResult(
        message_plan_ref="plan:2",
        status=DispatchStatus.DISPATCHED,
        dispatched_at="2026-01-01T00:01:00Z",
    )
    manager.record_dispatch(
        proposition_ref="prop:1",
        participant_ref="system:1",
        discourse_status=DiscourseStatus.CORRECTED,
        dispatch_result=dispatch2,
        corrects_entry_id=entry1.entry_id,
    )

    # Original entry should be marked as corrected
    entries = manager.get_entries_for_proposition("prop:1")
    corrected = [e for e in entries if e.discourse_status == DiscourseStatus.CORRECTED]
    assert len(corrected) >= 1


# ── Commit-before-claim tests ──


def test_commit_before_claim_success():
    """Response says stored/learned only when required commits succeed."""
    planner = ResponsePlanner()

    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(make_assessment("prop:1"),),
        commit_outcome=make_commit_outcome(required_satisfied=True),
    )

    plan = planner.plan_response(selection)

    # Find the commit content item
    commit_items = [
        item for item in plan.content_items
        if item.focus == "commit_success"
    ]
    assert len(commit_items) == 1
    assert commit_items[0].stance == EpistemicStance.ASSERTED.value


def test_commit_before_claim_failure():
    """Response does not say stored/learned when required write fails."""
    planner = ResponsePlanner()

    selection = ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(make_assessment("prop:1"),),
        commit_outcome=make_commit_outcome(required_satisfied=False),
    )

    plan = planner.plan_response(selection)

    # Find the commit content item
    commit_items = [
        item for item in plan.content_items
        if item.focus == "commit_failure"
    ]
    assert len(commit_items) == 1
    assert commit_items[0].stance == EpistemicStance.DENIED.value


# ── Import boundary tests ──


def test_phase10_imports_no_engine():
    """Phase 10 response modules must not import any engine module."""
    import cemm.kernel.response.planner as pl_mod
    import cemm.kernel.response.provenance as pr_mod
    import cemm.kernel.response.reparse_validator as rv_mod
    import cemm.kernel.response.common_ground as cg_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    for mod in [pl_mod, pr_mod, rv_mod, cg_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_response_does_not_import_schema():
    """Response modules must not import schema submodules.

    Response is downstream of schema — it uses model records only.
    """
    import cemm.kernel.response.planner as pl_mod
    import cemm.kernel.response.provenance as pr_mod
    import cemm.kernel.response.reparse_validator as rv_mod
    import cemm.kernel.response.common_ground as cg_mod

    forbidden_schema = [
        "from ..schema.",
        "from cemm.kernel.schema.",
    ]
    for mod in [pl_mod, pr_mod, rv_mod, cg_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden_schema:
            assert f not in source, f"{mod.__file__} imports forbidden schema module {f}"


def test_response_planner_does_not_invent_truth():
    """ResponsePlanner must not invent truth or decide capability."""
    planner = ResponsePlanner()

    # ResponsePlanner has no methods for truth decisions
    assert not hasattr(planner, "evaluate_truth")
    assert not hasattr(planner, "assess_capability")
    assert not hasattr(planner, "activate_schema")
    assert not hasattr(planner, "authorize")
    assert not hasattr(planner, "execute")
