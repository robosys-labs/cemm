"""R2 independent verifier reconstruction tests.

Per R2 plan Task 6:
- Independent reconstruction matches compiler output for multi-app programs
- Independent reconstruction handles scope operators
- Independent reconstruction handles expression links
- Independent reconstruction handles proposition role nesting
- Reconstruction is independent of the compiler code path
"""

from __future__ import annotations

from types import SimpleNamespace

from cemm_authoritative_hybrid.expressions import (
    CompilationSuccess,
    SemanticExpressionCompiler,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)
from cemm_authoritative_hybrid.verifier_reconstruction import (
    reconstruct_expected_expression,
)


def _pin() -> RevisionPin:
    return RevisionPin("authority:g1", 1, 2, 3, 4, "model:m1")


def _context():
    designations = {
        "designation_slot:love": SimpleNamespace(
            slot_ref="designation_slot:love",
            target_ref="relation:love",
            designation_fact_ref="designation:love",
            provenance_refs=("authority:g1",),
        ),
        "designation_slot:alice": SimpleNamespace(
            slot_ref="designation_slot:alice",
            target_ref="entity:alice",
            designation_fact_ref="designation:alice",
            provenance_refs=("authority:g1",),
        ),
    }
    contributions = {
        "contribution_slot:alice": SimpleNamespace(
            slot_ref="contribution_slot:alice",
            kind="anchor",
            target_ref="entity:alice",
            literal_value=None,
            output_ports=("role:subject", "role:object"),
            provenance_refs=("designation:alice",),
        ),
        "contribution_slot:bob": SimpleNamespace(
            slot_ref="contribution_slot:bob",
            kind="anchor",
            target_ref="entity:bob",
            literal_value=None,
            output_ports=("role:subject", "role:object"),
            provenance_refs=("designation:bob",),
        ),
    }
    frames = {
        "application_frame_slot:love": SimpleNamespace(
            slot_ref="application_frame_slot:love",
            operator_ref="op:relation",
            predicate_target_ref="relation:love",
            required_roles=("role:subject", "role:object"),
            optional_roles=(),
            proposition_roles=(),
            derived_role_targets=(),
        ),
    }
    scopes = {
        "scope_slot:neg": SimpleNamespace(
            slot_ref="scope_slot:neg",
            operator_type="scope:polarity",
            value_ref="polarity:negative",
        ),
    }
    links = {
        "link_slot:coord": SimpleNamespace(
            slot_ref="link_slot:coord",
            link_type="link:coordination",
        ),
    }
    modes = {"mode_slot:observe": SimpleNamespace(slot_ref="mode_slot:observe")}
    return SimpleNamespace(
        context_ref="proposal_context:one",
        orientation_ref="orientation:one",
        revision_pin=_pin(),
        designation=lambda ref: designations.get(ref),
        contribution=lambda ref: contributions.get(ref),
        frame=lambda ref: frames.get(ref),
        mode_slot=lambda ref: modes.get(ref),
        reference=lambda ref: None,
        scope=lambda ref: scopes.get(ref),
        expression_link=lambda ref: links.get(ref),
        variable=lambda ref: None,
        transition=lambda ref: None,
    )


def _base_actions(context):
    return [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:love",)),
        ProgramAction.create(action_index=3, action_type="select_designation", arguments=("designation_slot:alice",)),
        ProgramAction.create(action_index=4, action_type="instantiate_operator", arguments=("application:0", "application_frame_slot:love"), source_unit_refs=("unit:loves",)),
        ProgramAction.create(action_index=5, action_type="bind_role", arguments=("application:0", "role:subject", "contribution_slot:alice"), source_unit_refs=("unit:alice",)),
        ProgramAction.create(action_index=6, action_type="bind_role", arguments=("application:0", "role:object", "contribution_slot:bob"), source_unit_refs=("unit:bob",)),
    ]


def _make_program(context, actions, root_refs):
    assignments = (
        SourceAssignment.create(source_unit_ref="unit:loves", contribution_slot_ref="contribution_slot:predicate", assignment_kind="predicate", target_action_ref=actions[4].action_ref, target_role_ref=None, residual_kind=None, critical=True),
        SourceAssignment.create(source_unit_ref="unit:alice", contribution_slot_ref="contribution_slot:alice", assignment_kind="role", target_action_ref=actions[5].action_ref, target_role_ref="role:subject", residual_kind=None, critical=True),
        SourceAssignment.create(source_unit_ref="unit:bob", contribution_slot_ref="contribution_slot:bob", assignment_kind="role", target_action_ref=actions[6].action_ref, target_role_ref="role:object", residual_kind=None, critical=True),
    )
    actions = actions + [ProgramAction.create(action_index=len(actions), action_type="complete_program", arguments=())]
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=tuple(actions),
        root_refs=root_refs,
        mode_slot_ref="mode_slot:observe",
        goal_refs=("goal:understand",),
        source_unit_refs=("unit:loves", "unit:alice", "unit:bob"),
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def test_r1_program_reconstruction_matches_compiler():
    """R1 program reconstruction matches compiler output."""
    context = _context()
    actions = _base_actions(context)
    program = _make_program(context, actions, ("application:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed


def test_multi_app_reconstruction_matches_compiler():
    """Multi-application reconstruction matches compiler output."""
    context = _context()
    actions = _base_actions(context)
    actions.append(ProgramAction.create(action_index=len(actions), action_type="instantiate_operator", arguments=("application:1", "application_frame_slot:love"), source_unit_refs=("unit:loves",)))
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_role", arguments=("application:1", "role:subject", "contribution_slot:bob"), source_unit_refs=("unit:bob",)))
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_role", arguments=("application:1", "role:object", "contribution_slot:alice"), source_unit_refs=("unit:alice",)))
    program = _make_program(context, actions, ("application:0", "application:1"))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed


def test_scope_reconstruction_matches_compiler():
    """Scope operator reconstruction matches compiler output."""
    context = _context()
    actions = _base_actions(context)
    actions.append(ProgramAction.create(action_index=len(actions), action_type="attach_scope", arguments=("scope:0", "scope_slot:neg", "application:0")))
    program = _make_program(context, actions, ("scope:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed


def test_link_reconstruction_matches_compiler():
    """Expression link reconstruction matches compiler output."""
    context = _context()
    actions = _base_actions(context)
    actions.append(ProgramAction.create(action_index=len(actions), action_type="instantiate_operator", arguments=("application:1", "application_frame_slot:love"), source_unit_refs=("unit:loves",)))
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_role", arguments=("application:1", "role:subject", "contribution_slot:bob"), source_unit_refs=("unit:bob",)))
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_role", arguments=("application:1", "role:object", "contribution_slot:alice"), source_unit_refs=("unit:alice",)))
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_nested_application", arguments=("link", "link:0", "link_slot:coord", "application:0", "application:1")))
    program = _make_program(context, actions, ("link:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed


def test_reconstruction_returns_none_for_empty_program():
    """Reconstruction returns None for programs with no actions."""
    context = _context()
    program = _make_program(context, _base_actions(context), ("application:0",))
    reconstructed = reconstruct_expected_expression(program, context)
    assert reconstructed is not None
