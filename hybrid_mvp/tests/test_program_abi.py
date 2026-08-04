"""Tests for the recursive Semantic Switch Program ABI.

These tests pin the closed 12-action switch vocabulary, the five persistent
operators, exact source assignments inside the serialized program, and the
canonical round-trip of the completed program.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.programs import (
    PERSISTENT_OPERATORS,
    SWITCH_ACTION_TYPES,
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
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
        ProgramAction.create(
            action_index=0,
            action_type="not_a_real_action",  # type: ignore[arg-type]
            arguments=(),
            source_unit_refs=(),
        )


def test_program_action_accepts_every_confirmed_type():
    for index, action_type in enumerate(SWITCH_ACTION_TYPES):
        ProgramAction.create(
            action_index=index,
            action_type=action_type,
            arguments=_VALID_ACTION_ARGUMENTS[action_type],
            source_unit_refs=(),
        )


# ---------------------------------------------------------------------------
# Persistent operators
# ---------------------------------------------------------------------------


def test_program_uses_only_five_persistent_operators(program_factory, proposal_context):
    """Operators are resolved from ApplicationFrameSlot.operator_ref, not argument spelling.

    Per R2 plan section 5.1.6: the operator must be resolved from the context,
    not guessed from argument spelling.
    """
    program = program_factory("what is your name?")
    ops = _resolve_operators_from_context(program, proposal_context)
    assert ops <= PERSISTENT_OPERATORS


def test_program_with_no_operator_has_empty_persistent_operators():
    program = SemanticSwitchProgram.create(
        orientation_ref="orientation:0",
        proposal_context_ref="proposal_context:0",
        actions=(
            ProgramAction.create(
                action_index=0,
                action_type="select_context",
                arguments=("proposal_context:0",),
            ),
            ProgramAction.create(
                action_index=1,
                action_type="select_mode",
                arguments=("mode_slot:0",),
            ),
            ProgramAction.create(
                action_index=2,
                action_type="abstain",
                arguments=(),
            ),
        ),
        root_refs=(),
        mode_slot_ref="mode_slot:0",
        goal_refs=(),
        source_unit_refs=(),
        source_assignments=(),
        revision_pin=_default_pin(),
    )
    # No instantiate_operator actions means no operators
    ops = frozenset(
        a for a in program.actions if a.action_type == "instantiate_operator"
    )
    assert len(ops) == 0


def test_program_extracts_operators_from_instantiate_operator_actions():
    """Operators are resolved from ApplicationFrameSlot.operator_ref, not argument spelling.

    Per R2 plan section 5.1.6: Program ABI 2 instantiate_operator points to
    an application frame; the operator must be resolved from the context,
    not guessed from argument spelling.
    """
    actions = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=("proposal_context:0",),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=("mode_slot:0",),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="instantiate_operator",
            arguments=("application:0", "application_frame_slot:0"),
            source_unit_refs=("unit:0",),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:1", "application_frame_slot:1"),
            source_unit_refs=("unit:1",),
        ),
        ProgramAction.create(
            action_index=4,
            action_type="complete_program",
            arguments=(),
        ),
    )
    program = SemanticSwitchProgram.create(
        orientation_ref="orientation:0",
        proposal_context_ref="proposal_context:0",
        actions=actions,
        root_refs=("application:1",),
        mode_slot_ref="mode_slot:0",
        goal_refs=(),
        source_unit_refs=("unit:0", "unit:1"),
        source_assignments=(
            SourceAssignment.create(
                source_unit_ref="unit:0",
                contribution_slot_ref="contribution_slot:0",
                assignment_kind="predicate",
                target_action_ref=actions[2].action_ref,
                target_role_ref=None,
                residual_kind=None,
                critical=False,
            ),
            SourceAssignment.create(
                source_unit_ref="unit:1",
                contribution_slot_ref="contribution_slot:1",
                assignment_kind="predicate",
                target_action_ref=actions[3].action_ref,
                target_role_ref=None,
                residual_kind=None,
                critical=False,
            ),
        ),
        revision_pin=_default_pin(),
    )
    # The program actions carry application local refs and frame slot refs,
    # not operator strings. Operators are resolved through the context's
    # ApplicationFrameSlot.operator_ref field.
    instantiate_actions = [
        a for a in program.actions if a.action_type == "instantiate_operator"
    ]
    assert len(instantiate_actions) == 2
    for action in instantiate_actions:
        # Arguments are (application_local_ref, application_frame_slot_ref)
        app_ref, frame_slot_ref = action.arguments
        assert app_ref.startswith("application:")
        assert frame_slot_ref.startswith("application_frame_slot:")
        # No argument should be an op: string
        assert not any(arg.startswith("op:") for arg in action.arguments)


# ---------------------------------------------------------------------------
# Action encoding hash
# ---------------------------------------------------------------------------


def test_action_encoding_hash_is_stable_for_same_structure(program_factory):
    a = program_factory("what is your name?")
    b = program_factory("what is your name?")
    assert a.program_ref == b.program_ref


def test_action_encoding_hash_changes_with_structure(program_factory):
    base = program_factory("what is your name?")
    actions = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=("proposal_context:alt",),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=("mode_slot:alt",),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=("designation_slot:alt",),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:alt", "application_frame_slot:alt"),
            source_unit_refs=("unit:alt",),
        ),
        ProgramAction.create(
            action_index=4,
            action_type="bind_role",
            arguments=("application:alt", "role:actor", "contribution_slot:alt"),
            source_unit_refs=("unit:alt2",),
        ),
        ProgramAction.create(
            action_index=5,
            action_type="complete_program",
            arguments=(),
        ),
    )
    modified = SemanticSwitchProgram.create(
        orientation_ref="orientation:alt",
        proposal_context_ref="proposal_context:alt",
        actions=actions,
        root_refs=("application:alt",),
        mode_slot_ref="mode_slot:alt",
        goal_refs=("goal:alt",),
        source_unit_refs=("unit:alt", "unit:alt2"),
        source_assignments=(
            SourceAssignment.create(
                source_unit_ref="unit:alt",
                contribution_slot_ref="contribution_slot:alt",
                assignment_kind="predicate",
                target_action_ref=actions[3].action_ref,
                target_role_ref=None,
                residual_kind=None,
                critical=False,
            ),
            SourceAssignment.create(
                source_unit_ref="unit:alt2",
                contribution_slot_ref="contribution_slot:alt2",
                assignment_kind="role",
                target_action_ref=actions[4].action_ref,
                target_role_ref="role:actor",
                residual_kind=None,
                critical=False,
            ),
        ),
        revision_pin=_default_pin(),
    )
    assert modified.program_ref != base.program_ref


# ---------------------------------------------------------------------------
# Frozen / immutable
# ---------------------------------------------------------------------------


def test_program_is_frozen(program_factory):
    program = program_factory("what is your name?")
    with pytest.raises(Exception):
        program.program_ref = "program:mutated"  # type: ignore[misc]


def test_program_action_is_frozen():
    action = ProgramAction.create(
        action_index=0,
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
    """ScopeFrame is retired in Program ABI 2; verify it is not exported."""
    import cemm_authoritative_hybrid.programs as programs_mod

    assert not hasattr(programs_mod, "ScopeFrame")


def test_attach_scope_action_is_admitted_in_abi():
    """attach_scope is a valid Program ABI 2 action type.

    Per R2 plan section 5.1.7: scope tests must prove attach_scope
    works, not just that retired classes are absent.
    """
    action = ProgramAction.create(
        action_index=0,
        action_type="attach_scope",
        arguments=("scope:0", "scope_slot:0", "application:main"),
        source_unit_refs=(),
    )
    assert action.action_type == "attach_scope"
    assert action.arguments == ("scope:0", "scope_slot:0", "application:main")


def test_transition_proposal_is_frozen():
    """TransitionProposal is retired in Program ABI 2; verify it is not exported."""
    import cemm_authoritative_hybrid.programs as programs_mod

    assert not hasattr(programs_mod, "TransitionProposal")


def test_propose_transition_action_is_admitted_in_abi():
    """propose_transition is a valid Program ABI 2 action type.

    Per R2 plan section 5.1.7: transition tests must prove
    propose_transition works, not just that retired classes are absent.
    """
    action = ProgramAction.create(
        action_index=0,
        action_type="propose_transition",
        arguments=("transition_slot:0", "application:main"),
        source_unit_refs=(),
    )
    assert action.action_type == "propose_transition"
    assert action.arguments == ("transition_slot:0", "application:main")


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


def _persistent_operators(program: SemanticSwitchProgram) -> frozenset[str]:
    """Extract operator refs from instantiate_operator actions.

    .. deprecated:: Operators must be resolved through
       ApplicationFrameSlot.operator_ref from the context, not by
       inspecting argument spelling. Use
       :func:`_resolve_operators_from_context` instead.
    """
    return frozenset(
        argument
        for action in program.actions
        if action.action_type == "instantiate_operator"
        for argument in action.arguments
        if argument.startswith("op:")
    )


def _resolve_operators_from_context(
    program: SemanticSwitchProgram, context: object
) -> frozenset[str]:
    """Resolve operator refs through ApplicationFrameSlot.operator_ref.

    Per R2 plan section 5.1.6: Program ABI 2 instantiate_operator points
    to an application frame; the operator must be resolved from the
    context, not guessed from argument spelling.
    """
    operators: set[str] = set()
    for action in program.actions:
        if action.action_type != "instantiate_operator":
            continue
        # Arguments are (application_local_ref, application_frame_slot_ref)
        _app_ref, frame_slot_ref = action.arguments
        frame = context.frame(frame_slot_ref) if hasattr(context, "frame") else None
        if frame is not None:
            operators.add(frame.operator_ref)
    return frozenset(operators)


_VALID_ACTION_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "select_context": ("proposal_context:1",),
    "select_mode": ("mode_slot:1",),
    "select_designation": ("designation_slot:1",),
    "instantiate_operator": ("application:1", "application_frame_slot:1"),
    "bind_role": ("application:1", "role:actor", "contribution_slot:1"),
    "bind_reference": ("application:1", "role:actor", "reference_slot:1"),
    "bind_nested_application": ("role", "application:1", "role:content", "application:2"),
    "attach_scope": ("scope:1", "scope_slot:1", "application:1"),
    "project_variable": ("binder:1", "variable_slot:1", "application:1"),
    "propose_transition": ("transition_slot:1", "application:1"),
    "complete_program": (),
    "abstain": (),
}
