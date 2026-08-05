"""R2 recursive Semantic Expression compiler tests.

Per R2 plan Task 5:
- Compile multi-application programs with multiple roots
- Compile proposition role nesting (bind_nested_application role)
- Compile expression links (bind_nested_application link)
- Compile scope operators (attach_scope)
- Compile variable binders (project_variable)
- Two programs that differ only in action order compile to same expression
- R2 actions are admitted (not rejected with action_shape_not_admitted)
"""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from cemm_authoritative_hybrid.expressions import (
    CompilationFailure,
    CompilationSuccess,
    SemanticExpressionCompiler,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)

__cemm_test_inventory__ = {
    "tests/test_r2_recursive_compiler.py::test_attach_scope_produces_scope_operator": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-attach-scope-produces-scope-operator",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "10fdc32c8650a5b785a51ab5410971a532b25f83696a9de8b964ed0939647357"
    },
    "tests/test_r2_recursive_compiler.py::test_bind_nested_application_link_produces_expression_link": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-bind-nested-application-link-produces-expression-link",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "c7d33dada8d168324f8555b61ef1dc2b58b5417e3df1441007495c17f4d4610b"
    },
    "tests/test_r2_recursive_compiler.py::test_bind_nested_application_role_produces_application_filler": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-bind-nested-application-role-produces-application-filler",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "65ee0608a26f2d9e8cb86dbb2cc135893aa405af2f1ffdff0fed304e27dd14ad"
    },
    "tests/test_r2_recursive_compiler.py::test_context_mismatch_fails_before_compilation": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-context-mismatch-fails-before-compilation",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "651525cc40c1fec0a593f888cf7791ed12b92b0b54f02be63a7940138143cfa8"
    },
    "tests/test_r2_recursive_compiler.py::test_r2_actions_are_admitted_not_rejected": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-actions-are-admitted-not-rejected",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "b0705c07f04383e50024374ccae45806aceda96421ff2d50dbb5239dcd18c163"
    },
    "tests/test_r2_recursive_compiler.py::test_single_application_compiles_correctly": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-single-application-compiles-correctly",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "f411b157dcc8412b35a643cbbb9c0e7a40e4a4d2bea7c12bd10105314650e769"
    },
    "tests/test_r2_recursive_compiler.py::test_two_applications_compile_with_multiple_roots": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-two-applications-compile-with-multiple-roots",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "c9c3bf74fb6481bc6136f2495843b5cf5ea614f09de11d62c05fc1081a138da7"
    },
    "tests/test_r2_recursive_compiler.py::test_two_derivations_compile_to_same_expression": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-two-derivations-compile-to-same-expression",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "c12d4ace83cfeee97af9f2bb154d23cf75c6a5f6895877b97a1f2a170b8dcc3c"
    },
    "tests/test_r2_recursive_compiler.py::test_zero_applications_fails": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-zero-applications-fails",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "67c106d768f6eda9d7684ac3b9f01b420bba55b8f7a8f181a17d0b9f61bb8301"
    },
}



def _pin() -> RevisionPin:
    return RevisionPin("authority:g1", 1, 2, 3, 4, "model:m1")


def _context(*, proposition_roles=(), derived_role_targets=()):
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
        "designation_slot:bob": SimpleNamespace(
            slot_ref="designation_slot:bob",
            target_ref="entity:bob",
            designation_fact_ref="designation:bob",
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
            proposition_roles=proposition_roles,
            derived_role_targets=derived_role_targets,
        ),
        "application_frame_slot:think": SimpleNamespace(
            slot_ref="application_frame_slot:think",
            operator_ref="op:event",
            predicate_target_ref="event:think",
            required_roles=("role:subject",),
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
    variables = {
        "variable_slot:who": SimpleNamespace(
            slot_ref="variable_slot:who",
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
        variable=lambda ref: variables.get(ref),
        transition=lambda ref: None,
    )


def _base_actions(context, *, app_ref="application:0", frame_ref="application_frame_slot:love"):
    return [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:love",)),
        ProgramAction.create(action_index=3, action_type="select_designation", arguments=("designation_slot:alice",)),
        ProgramAction.create(action_index=4, action_type="instantiate_operator", arguments=(app_ref, frame_ref), source_unit_refs=("unit:loves",)),
        ProgramAction.create(action_index=5, action_type="bind_role", arguments=(app_ref, "role:subject", "contribution_slot:alice"), source_unit_refs=("unit:alice",)),
        ProgramAction.create(action_index=6, action_type="bind_role", arguments=(app_ref, "role:object", "contribution_slot:bob"), source_unit_refs=("unit:bob",)),
    ]


def _make_program(context, actions, root_refs):
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:loves",
            contribution_slot_ref="contribution_slot:predicate",
            assignment_kind="predicate",
            target_action_ref=actions[4].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:alice",
            contribution_slot_ref="contribution_slot:alice",
            assignment_kind="role",
            target_action_ref=actions[5].action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:bob",
            contribution_slot_ref="contribution_slot:bob",
            assignment_kind="role",
            target_action_ref=actions[6].action_ref,
            target_role_ref="role:object",
            residual_kind=None,
            critical=True,
        ),
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


# ---------------------------------------------------------------------------
# R1 compatibility tests
# ---------------------------------------------------------------------------


def test_single_application_compiles_correctly():
    """R1-style single application program still compiles."""
    context = _context()
    actions = _base_actions(context)
    program = _make_program(context, actions, ("application:0",))
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess)
    assert len(result.expression.applications) == 1
    assert len(result.expression.root_refs) == 1


def test_two_derivations_compile_to_same_expression():
    """Two programs with same semantics compile to same expression."""
    context = _context()
    actions1 = _base_actions(context)
    # Reverse designation order
    actions2 = _base_actions(context)
    actions2[2] = ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:alice",))
    actions2[3] = ProgramAction.create(action_index=3, action_type="select_designation", arguments=("designation_slot:love",))
    program1 = _make_program(context, actions1, ("application:0",))
    program2 = _make_program(context, actions2, ("application:0",))
    r1 = SemanticExpressionCompiler().compile(program1, context)
    r2 = SemanticExpressionCompiler().compile(program2, context)
    assert isinstance(r1, CompilationSuccess)
    assert isinstance(r2, CompilationSuccess)
    assert r1.expression.expression_ref == r2.expression.expression_ref


# ---------------------------------------------------------------------------
# R2 multi-application tests
# ---------------------------------------------------------------------------


def test_two_applications_compile_with_multiple_roots():
    """Two applications produce an expression with two roots."""
    context = _context()
    actions = _base_actions(context)
    # Add second application
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="instantiate_operator",
            arguments=("application:1", "application_frame_slot:love"),
            source_unit_refs=("unit:loves",),
        )
    )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_role",
            arguments=("application:1", "role:subject", "contribution_slot:bob"),
            source_unit_refs=("unit:bob",),
        )
    )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_role",
            arguments=("application:1", "role:object", "contribution_slot:alice"),
            source_unit_refs=("unit:alice",),
        )
    )
    program = _make_program(context, actions, ("application:0", "application:1"))
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess)
    assert len(result.expression.applications) == 2
    assert len(result.expression.root_refs) == 2


# ---------------------------------------------------------------------------
# R2 scope tests
# ---------------------------------------------------------------------------


def test_attach_scope_produces_scope_operator():
    """attach_scope produces a ScopeOperator in the expression."""
    context = _context()
    actions = _base_actions(context)
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="attach_scope",
            arguments=("scope:0", "scope_slot:neg", "application:0"),
        )
    )
    program = _make_program(context, actions, ("scope:0",))
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess)
    assert len(result.expression.scope_operators) == 1
    scope = result.expression.scope_operators[0]
    assert scope.operator_type == "scope:polarity"
    assert scope.value_ref == "polarity:negative"
    assert result.expression.root_refs == (scope.scope_ref,)


# ---------------------------------------------------------------------------
# R2 expression link tests
# ---------------------------------------------------------------------------


def test_bind_nested_application_link_produces_expression_link():
    """bind_nested_application (link) produces an ExpressionLink."""
    context = _context()
    actions = _base_actions(context)
    # Add second application
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="instantiate_operator",
            arguments=("application:1", "application_frame_slot:love"),
            source_unit_refs=("unit:loves",),
        )
    )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_role",
            arguments=("application:1", "role:subject", "contribution_slot:bob"),
            source_unit_refs=("unit:bob",),
        )
    )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_role",
            arguments=("application:1", "role:object", "contribution_slot:alice"),
            source_unit_refs=("unit:alice",),
        )
    )
    # Link the two applications
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_nested_application",
            arguments=("link", "link:0", "link_slot:coord", "application:0", "application:1"),
        )
    )
    program = _make_program(context, actions, ("link:0",))
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess)
    assert len(result.expression.expression_links) == 1
    link = result.expression.expression_links[0]
    assert link.link_type == "link:coordination"
    assert len(link.operand_refs) == 2


# ---------------------------------------------------------------------------
# R2 proposition role nesting tests
# ---------------------------------------------------------------------------


def test_bind_nested_application_role_produces_application_filler():
    """bind_nested_application (role) produces an ApplicationFiller."""
    context = _context(proposition_roles=("role:proposition",))
    actions = _base_actions(context)
    # Add second application (the nested one) using same frame
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="instantiate_operator",
            arguments=("application:1", "application_frame_slot:love"),
            source_unit_refs=("unit:loves",),
        )
    )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_role",
            arguments=("application:1", "role:subject", "contribution_slot:bob"),
            source_unit_refs=("unit:bob",),
        )
    )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_role",
            arguments=("application:1", "role:object", "contribution_slot:alice"),
            source_unit_refs=("unit:alice",),
        )
    )
    # Bind the nested application as a proposition role
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="bind_nested_application",
            arguments=("role", "application:0", "role:proposition", "application:1"),
        )
    )
    program = _make_program(context, actions, ("application:0",))
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess), f"expected success, got {result.code if isinstance(result, CompilationFailure) else type(result)}"
    assert len(result.expression.applications) == 2


# ---------------------------------------------------------------------------
# R2 admission tests
# ---------------------------------------------------------------------------


def test_r2_actions_are_admitted_not_rejected():
    """R2 actions are admitted by the recursive compiler."""
    context = _context()
    actions = _base_actions(context)
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="attach_scope",
            arguments=("scope:0", "scope_slot:neg", "application:0"),
        )
    )
    program = _make_program(context, actions, ("scope:0",))
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess), f"expected success, got {result.code if isinstance(result, CompilationFailure) else type(result)}"


def test_zero_applications_fails():
    """Program with no instantiate_operator actions cannot be created.

    SemanticSwitchProgram.create validates that completed programs have
    non-empty root_refs referencing declared application nodes.  Without
    instantiate_operator actions, no nodes are declared, so no valid
    root set exists.  This test verifies the program-level guard.
    """
    context = _context()
    actions = [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="complete_program", arguments=()),
    ]
    with pytest.raises(ValueError, match="unknown or empty root set"):
        SemanticSwitchProgram.create(
            proposal_context_ref=context.context_ref,
            orientation_ref=context.orientation_ref,
            mode_slot_ref="mode_slot:observe",
            actions=tuple(actions),
            root_refs=("application:0",),
            goal_refs=(),
            source_unit_refs=(),
            source_assignments=(),
            revision_pin=context.revision_pin,
        )


def test_context_mismatch_fails_before_compilation():
    """Context identity mismatch fails before compilation."""
    context = _context()
    actions = _base_actions(context)
    program = _make_program(context, actions, ("application:0",))
    context.context_ref = "proposal_context:other"
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationFailure)
    assert result.code == "proposal_context_mismatch"
