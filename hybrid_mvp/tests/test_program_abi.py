"""Tests for the recursive Semantic Switch Program ABI.

These tests pin the closed 12-action switch vocabulary, the five persistent
operators, exact source assignments inside the serialized program, and the
canonical round-trip of the completed program.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.programs import (
    SWITCH_ACTION_TYPES,
    ProgramAction,
    SourceAssignment,
    SemanticSwitchProgram,
    ScopeFrame,
    TransitionProposal,
)

PERSISTENT_OPERATORS = frozenset(
    {"op:designation", "op:type", "op:relation", "op:state", "op:event"}
)


# ---------------------------------------------------------------------------
# Closed action vocabulary
# ---------------------------------------------------------------------------


def test_switch_action_vocabulary_matches_confirmed_abi_exactly():
    assert SWITCH_ACTION_TYPES == (
        "select_context",
        "select_mode",
        "select_designation",
        "instantiate_operator",
        "bind_role",
        "bind_reference",
        "bind_nested_application",
        "attach_scope",
        "project_variable",
        "propose_transition",
        "complete_program",
        "abstain",
    )


def test_switch_action_vocabulary_is_closed_at_twelve():
    assert len(SWITCH_ACTION_TYPES) == 12
    assert len(set(SWITCH_ACTION_TYPES)) == 12


def test_program_action_rejects_unknown_action_type():
    with pytest.raises(ValueError):
        ProgramAction(
            action_ref="action:bad",
            action_type="not_a_real_action",  # type: ignore[arg-type]
            arguments=(),
            source_unit_refs=(),
        )


def test_program_action_accepts_every_confirmed_type():
    for index, action_type in enumerate(SWITCH_ACTION_TYPES):
        ProgramAction(
            action_ref=f"action:{index}",
            action_type=action_type,
            arguments=(),
            source_unit_refs=(),
        )


# ---------------------------------------------------------------------------
# Persistent operators
# ---------------------------------------------------------------------------


def test_program_uses_only_five_persistent_operators(program_factory):
    program = program_factory("what is your name?")
    assert set(program.persistent_operators) <= PERSISTENT_OPERATORS


def test_program_with_no_operator_has_empty_persistent_operators():
    program = SemanticSwitchProgram(
        program_ref="program:empty",
        orientation_ref="orientation:0",
        actions=(
            ProgramAction(
                action_ref="action:0",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            ),
        ),
        root_graph_refs=(),
        mode_ref="mode:OBSERVE",
        goal_refs=(),
        source_unit_refs=(),
        source_assignments=(),
        revision_pin=_default_pin(),
    )
    assert program.persistent_operators == frozenset()


def test_program_extracts_operators_from_instantiate_operator_actions():
    program = SemanticSwitchProgram(
        program_ref="program:ops",
        orientation_ref="orientation:0",
        actions=(
            ProgramAction(
                action_ref="action:0",
                action_type="instantiate_operator",
                arguments=("op:designation", "designation:0"),
                source_unit_refs=("unit:0",),
            ),
            ProgramAction(
                action_ref="action:1",
                action_type="instantiate_operator",
                arguments=("op:relation", "application:0"),
                source_unit_refs=("unit:1",),
            ),
        ),
        root_graph_refs=("application:0",),
        mode_ref="mode:OBSERVE",
        goal_refs=(),
        source_unit_refs=("unit:0", "unit:1"),
        source_assignments=(),
        revision_pin=_default_pin(),
    )
    assert program.persistent_operators == frozenset({"op:designation", "op:relation"})


# ---------------------------------------------------------------------------
# Action encoding hash
# ---------------------------------------------------------------------------


def test_action_encoding_hash_is_stable_for_same_structure(program_factory):
    a = program_factory("what is your name?")
    b = program_factory("what is your name?")
    assert a.action_encoding_hash == b.action_encoding_hash


def test_action_encoding_hash_changes_with_structure(program_factory):
    base = program_factory("what is your name?")
    extra_action = ProgramAction(
        action_ref="action:extra",
        action_type="abstain",
        arguments=(),
        source_unit_refs=(),
    )
    modified = SemanticSwitchProgram(
        program_ref=base.program_ref,
        orientation_ref=base.orientation_ref,
        actions=base.actions + (extra_action,),
        root_graph_refs=base.root_graph_refs,
        mode_ref=base.mode_ref,
        goal_refs=base.goal_refs,
        source_unit_refs=base.source_unit_refs,
        source_assignments=base.source_assignments,
        revision_pin=base.revision_pin,
    )
    assert modified.action_encoding_hash != base.action_encoding_hash


# ---------------------------------------------------------------------------
# Frozen / immutable
# ---------------------------------------------------------------------------


def test_program_is_frozen(program_factory):
    program = program_factory("what is your name?")
    with pytest.raises(Exception):
        program.program_ref = "program:mutated"  # type: ignore[misc]


def test_program_action_is_frozen():
    action = ProgramAction(
        action_ref="action:0",
        action_type="abstain",
        arguments=(),
        source_unit_refs=(),
    )
    with pytest.raises(Exception):
        action.action_ref = "action:1"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Canonical round-trip preserves source assignments
# ---------------------------------------------------------------------------


def test_source_assignments_are_inside_serialized_program(
    valid_program, canonical_round_trip
):
    restored = canonical_round_trip(valid_program, SemanticSwitchProgram)
    assert restored.source_assignments == valid_program.source_assignments
    assert {row.source_unit_ref for row in restored.source_assignments} == set(
        valid_program.source_unit_refs
    )


def test_canonical_round_trip_preserves_actions(valid_program, canonical_round_trip):
    restored = canonical_round_trip(valid_program, SemanticSwitchProgram)
    assert restored.actions == valid_program.actions
    assert restored.program_ref == valid_program.program_ref


def test_canonical_round_trip_preserves_revision_pin(valid_program, canonical_round_trip):
    restored = canonical_round_trip(valid_program, SemanticSwitchProgram)
    assert restored.revision_pin == valid_program.revision_pin


# ---------------------------------------------------------------------------
# Scope and transition types
# ---------------------------------------------------------------------------


def test_scope_frame_is_frozen_with_typed_kind():
    frame = ScopeFrame(
        scope_ref="scope:0",
        kind="negation",
        target_application_ref="application:0",
        source_unit_refs=("unit:0",),
    )
    assert frame.kind == "negation"
    with pytest.raises(Exception):
        frame.scope_ref = "scope:1"  # type: ignore[misc]


def test_transition_proposal_is_frozen():
    transition = TransitionProposal(
        transition_ref="transition:0",
        event_type_ref="event:open",
        subject_ref="entity:door",
        target_state_ref="state:open",
        dimension_ref="dimension:status",
        preconditions=(),
        source_unit_refs=("unit:0",),
    )
    assert transition.event_type_ref == "event:open"
    with pytest.raises(Exception):
        transition.transition_ref = "transition:1"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_pin():
    from cemm_authoritative_hybrid.persistence import RevisionPin

    return RevisionPin(
        authority_generation="authority:generation-1",
        world_revision=0,
        session_revision=0,
        episode_revision=0,
        effect_revision=0,
        model_identity=None,
    )
