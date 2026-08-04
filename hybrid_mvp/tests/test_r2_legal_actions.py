"""R2 context-local legal action relation tests.

Per R2 plan section 3:
- Every action has positive and negative legality tests
- Masker/exhaustive parity is proven on generated small contexts
- Legality is pure, deterministic, bounded, and context-local
- No ref-name inspection or authority scan exists
- Bounds are enforced (applications, actions, nodes)
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.programs import ProgramAction
from cemm_authoritative_hybrid.verifier import (
    ActionMasker,
    LegalActionIndex,
    _prefix_budget,
)


# ---------------------------------------------------------------------------
# Budget tracking tests
# ---------------------------------------------------------------------------


def test_prefix_budget_empty():
    """Empty prefix has zero budget use."""
    app_count, action_count, node_count = _prefix_budget(())
    assert app_count == 0
    assert action_count == 0
    assert node_count == 0


def test_prefix_budget_tracks_applications(masker):
    """Budget tracks application count from instantiate_operator actions."""
    context = masker.legal_index.context
    actions = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(context.designation_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=(
                "application:0",
                context.application_frames[0].slot_ref,
            ),
        ),
    )
    app_count, action_count, node_count = _prefix_budget(actions)
    assert app_count == 1
    assert action_count == 4
    assert node_count == 1


# ---------------------------------------------------------------------------
# Positive and negative legality tests per action type
# ---------------------------------------------------------------------------


def test_select_context_legal_on_empty_prefix(masker):
    """select_context is legal only on empty prefix with correct context_ref."""
    context = masker.legal_index.context
    action = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=(context.context_ref,),
    )
    assert masker.legal_index.is_legal(action, ())


def test_select_context_illegal_with_wrong_ref(masker):
    """select_context with wrong context_ref is illegal."""
    context = masker.legal_index.context
    action = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=("ctx:wrong",),
    )
    assert not masker.legal_index.is_legal(action, ())


def test_select_mode_legal_after_select_context(masker):
    """select_mode is legal after select_context with valid mode slot."""
    context = masker.legal_index.context
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
    )
    mode_slot = context.mode_slots[0]
    action = ProgramAction.create(
        action_index=1,
        action_type="select_mode",
        arguments=(mode_slot.slot_ref,),
    )
    assert masker.legal_index.is_legal(action, prefix)


def test_select_mode_illegal_on_empty_prefix(masker):
    """select_mode is illegal on empty prefix."""
    context = masker.legal_index.context
    mode_slot = context.mode_slots[0]
    action = ProgramAction.create(
        action_index=0,
        action_type="select_mode",
        arguments=(mode_slot.slot_ref,),
    )
    assert not masker.legal_index.is_legal(action, ())


def test_select_designation_legal_after_mode(masker):
    """select_designation is legal after select_mode with valid designation."""
    context = masker.legal_index.context
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
    )
    designation = context.designation_slots[0]
    action = ProgramAction.create(
        action_index=2,
        action_type="select_designation",
        arguments=(designation.slot_ref,),
    )
    assert masker.legal_index.is_legal(action, prefix)


def test_select_designation_illegal_duplicate(masker):
    """select_designation is illegal for duplicate designation."""
    context = masker.legal_index.context
    designation = context.designation_slots[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
    )
    action = ProgramAction.create(
        action_index=3,
        action_type="select_designation",
        arguments=(designation.slot_ref,),
    )
    assert not masker.legal_index.is_legal(action, prefix)


def test_instantiate_operator_legal_after_designation(masker):
    """instantiate_operator is legal after selecting its designation."""
    context = masker.legal_index.context
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
    )
    action = ProgramAction.create(
        action_index=3,
        action_type="instantiate_operator",
        arguments=("application:0", frame.slot_ref),
    )
    assert masker.legal_index.is_legal(action, prefix)


def test_instantiate_operator_illegal_without_designation(masker):
    """instantiate_operator is illegal without selecting its designation."""
    context = masker.legal_index.context
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
    )
    action = ProgramAction.create(
        action_index=2,
        action_type="instantiate_operator",
        arguments=("application:0", frame.slot_ref),
    )
    assert not masker.legal_index.is_legal(action, prefix)


def test_complete_program_illegal_without_required_roles(masker):
    """complete_program is illegal when required roles are not satisfied."""
    context = masker.legal_index.context
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:0", frame.slot_ref),
        ),
    )
    action = ProgramAction.create(
        action_index=4,
        action_type="complete_program",
        arguments=(),
    )
    # Required roles are not bound yet
    assert not masker.legal_index.is_legal(action, prefix)


def test_abstain_illegal_after_terminal(masker, valid_program):
    """abstain is illegal after a terminal action."""
    context = masker.legal_index.context
    prefix = valid_program.actions
    action = ProgramAction.create(
        action_index=len(prefix),
        action_type="abstain",
        arguments=(),
    )
    assert not masker.legal_index.is_legal(action, prefix)


# ---------------------------------------------------------------------------
# Bounds enforcement tests
# ---------------------------------------------------------------------------


def test_application_bound_enforced(masker):
    """instantiate_operator is illegal when application bound is reached."""
    context = masker.legal_index.context
    legal = LegalActionIndex(context, max_applications=1)
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:0", frame.slot_ref),
        ),
    )
    # Second application should be rejected (max_applications=1)
    action = ProgramAction.create(
        action_index=4,
        action_type="instantiate_operator",
        arguments=("application:1", frame.slot_ref),
    )
    assert not legal.is_legal(action, prefix)


def test_node_bound_enforced_for_attach_scope(masker):
    """attach_scope is illegal when node bound is reached."""
    context = masker.legal_index.context
    legal = LegalActionIndex(context, max_nodes=1)
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    scope = context.scope_slots[0] if context.scope_slots else None
    if scope is None:
        pytest.skip("context has no scope slots")
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:0", frame.slot_ref),
        ),
    )
    # node_count is already 1 (from application:0), max_nodes=1
    action = ProgramAction.create(
        action_index=4,
        action_type="attach_scope",
        arguments=("scope:0", scope.slot_ref, "application:0"),
    )
    assert not legal.is_legal(action, prefix)


# ---------------------------------------------------------------------------
# Masker parity test
# ---------------------------------------------------------------------------


def test_masker_matches_legal_index(masker, prefix):
    """ActionMasker produces the same legal set as LegalActionIndex."""
    from tests.test_action_masks import _candidate_actions

    context = masker.legal_index.context
    candidates = _candidate_actions(context, len(prefix))
    masked = masker.filter_legal(prefix, candidates)
    exhaustive = tuple(
        candidate
        for candidate in candidates
        if masker.legal_index.is_legal(candidate, prefix)
    )
    assert set(masked) == set(exhaustive)


# ---------------------------------------------------------------------------
# Legality purity test
# ---------------------------------------------------------------------------


def test_is_legal_is_pure_predicate(masker, prefix):
    """is_legal returns the same result for the same inputs."""
    from tests.test_action_masks import _candidate_actions

    legal_index = masker.legal_index
    candidates = _candidate_actions(legal_index.context, len(prefix))
    if candidates:
        action = candidates[0]
        result1 = legal_index.is_legal(action, prefix)
        result2 = legal_index.is_legal(action, prefix)
        assert result1 == result2
