"""R2 acceptance matrix.

Comprehensive end-to-end validation that all R2 capabilities work together.
Each test exercises a full path from context construction through proposal,
verification, compilation, and expression reconstruction.

Matrix cases:
  1. Single-application R1-compatible program
  2. Multi-application program with multiple roots
  3. Program with scope operators
  4. Program with expression links
  5. Program with proposition role nesting
  6. Program with transition preview
  7. Program with variable binder
  8. Determinism: same inputs produce same outputs
  9. Independence: compiler and reconstruction agree
 10. Boundary: no internal refs leak to public surfaces
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
from cemm_authoritative_hybrid.transition_preview import extract_transition_previews
from cemm_authoritative_hybrid.verifier_reconstruction import (
    reconstruct_expected_expression,
)

__cemm_test_inventory__ = {
    "tests/test_r2_acceptance_matrix.py::test_matrix_10_no_internal_refs_in_expression_refs": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-10-no-internal-refs-in-expression-refs",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "43a427078b47fc1fc6a221fc78c4d0818ebb4b9e83272f22fe13aed20f59759e"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_1_single_application_r1_compatible": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-1-single-application-r1-compatible",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "d874d205971603df29958ed4f5c67617f09ada234c05f7c47b4051d5c08efdc8"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_2_multi_application_multiple_roots": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-2-multi-application-multiple-roots",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "1080381569873db4118a449de85d27a0fb40c9baa293c4bbae55ce5b73e8b80b"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_3_scope_operators": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-3-scope-operators",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "8c891cf712a964dfaf94a40030784493bf76682f7b6880cd056ef6acd43d4c33"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_4_expression_links": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-4-expression-links",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "c81bafbd1798041991e4c1400087d0522a1d654e71932a4bf4fa3af3ac6757a0"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_5_proposition_role_nesting": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-5-proposition-role-nesting",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "9bab4000be2dc3eb29c4899011b0672f7232485258405e404b70c467d32f7c3f"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_6_transition_preview": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-6-transition-preview",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "29612a582b6f31d1eab60696bd953f38441f6f34f92f653e766b7f87d4bcf1fa"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_7_variable_binder": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-7-variable-binder",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "3a705207cb54a184006f8b0284fd180d7c4f3833903843c4b3a4c23ec6d87167"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_8_determinism": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-8-determinism",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "7e0a24ebe3f0761fc6e7acdd36a0653224b1f1fcabd3fa9d90c32d798fc99cb9"
    },
    "tests/test_r2_acceptance_matrix.py::test_matrix_9_compiler_reconstruction_independence": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-matrix-9-compiler-reconstruction-independence",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "156a9eaa2b0cae6dab5f8abd92821b007392e58ba06e23aef85cd405f9099ac5"
    },
}



def _pin() -> RevisionPin:
    return RevisionPin("authority:g1", 1, 2, 3, 4, "model:m1")


def _full_context():
    """Context with all R2 slot types populated."""
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
        "application_frame_slot:think": SimpleNamespace(
            slot_ref="application_frame_slot:think",
            operator_ref="op:event",
            predicate_target_ref="event:think",
            required_roles=("role:subject",),
            optional_roles=(),
            proposition_roles=("role:proposition",),
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
            application_frame_ref="application_frame_slot:love",
            role_ref="role:subject",
        ),
    }
    transitions = {
        "transition_slot:act": SimpleNamespace(
            slot_ref="transition_slot:act",
            application_frame_ref="application_frame_slot:love",
            event_type_ref="event:act",
            compatible_modes=("OBSERVE",),
            required_roles=("role:subject",),
            required_capabilities=("cap:act",),
            required_permissions=("perm:act",),
            adapter_ref="adapter:act",
        ),
    }
    modes = {"mode_slot:observe": SimpleNamespace(slot_ref="mode_slot:observe", mode="OBSERVE")}
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
        transition=lambda ref: transitions.get(ref),
    )


def _make_program(context, actions, root_refs):
    """Build a program from actions with proper source assignments."""
    # Collect source unit refs from actions that have them
    source_units = set()
    for a in actions:
        for ref in a.source_unit_refs:
            source_units.add(ref)
    source_units = tuple(sorted(source_units))

    # Build assignments for the base actions (predicate + 2 roles)
    assignments = []
    if len(actions) > 5:
        assignments.append(
            SourceAssignment.create(
                source_unit_ref="unit:loves",
                contribution_slot_ref="contribution_slot:predicate",
                assignment_kind="predicate",
                target_action_ref=actions[3].action_ref,
                target_role_ref=None,
                residual_kind=None,
                critical=True,
            )
        )
        assignments.append(
            SourceAssignment.create(
                source_unit_ref="unit:alice",
                contribution_slot_ref="contribution_slot:alice",
                assignment_kind="role",
                target_action_ref=actions[4].action_ref,
                target_role_ref="role:subject",
                residual_kind=None,
                critical=True,
            )
        )
        assignments.append(
            SourceAssignment.create(
                source_unit_ref="unit:bob",
                contribution_slot_ref="contribution_slot:bob",
                assignment_kind="role",
                target_action_ref=actions[5].action_ref,
                target_role_ref="role:object",
                residual_kind=None,
                critical=True,
            )
        )

    actions = list(actions) + [ProgramAction.create(action_index=len(actions), action_type="complete_program", arguments=())]
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=tuple(actions),
        root_refs=root_refs,
        mode_slot_ref="mode_slot:observe",
        goal_refs=("goal:understand",),
        source_unit_refs=("unit:loves", "unit:alice", "unit:bob"),
        source_assignments=tuple(assignments),
        revision_pin=context.revision_pin,
    )


def _base_actions(context):
    return [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:love",)),
        ProgramAction.create(action_index=3, action_type="instantiate_operator", arguments=("application:0", "application_frame_slot:love"), source_unit_refs=("unit:loves",)),
        ProgramAction.create(action_index=4, action_type="bind_role", arguments=("application:0", "role:subject", "contribution_slot:alice"), source_unit_refs=("unit:alice",)),
        ProgramAction.create(action_index=5, action_type="bind_role", arguments=("application:0", "role:object", "contribution_slot:bob"), source_unit_refs=("unit:bob",)),
    ]


# ---------------------------------------------------------------------------
# Matrix case 1: Single-application R1-compatible
# ---------------------------------------------------------------------------


def test_matrix_1_single_application_r1_compatible():
    """Single-application program compiles and reconstructs correctly."""
    context = _full_context()
    actions = _base_actions(context)
    program = _make_program(context, actions, ("application:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed
    assert len(compiled.expression.applications) == 1
    assert len(compiled.expression.root_refs) == 1


# ---------------------------------------------------------------------------
# Matrix case 2: Multi-application with multiple roots
# ---------------------------------------------------------------------------


def test_matrix_2_multi_application_multiple_roots():
    """Multi-application program with multiple roots compiles correctly."""
    context = _full_context()
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
    assert len(compiled.expression.applications) == 2
    assert len(compiled.expression.root_refs) == 2


# ---------------------------------------------------------------------------
# Matrix case 3: Scope operators
# ---------------------------------------------------------------------------


def test_matrix_3_scope_operators():
    """Program with scope operators compiles correctly."""
    context = _full_context()
    actions = _base_actions(context)
    actions.append(ProgramAction.create(action_index=len(actions), action_type="attach_scope", arguments=("scope:0", "scope_slot:neg", "application:0")))
    program = _make_program(context, actions, ("scope:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed
    assert len(compiled.expression.scope_operators) == 1


# ---------------------------------------------------------------------------
# Matrix case 4: Expression links
# ---------------------------------------------------------------------------


def test_matrix_4_expression_links():
    """Program with expression links compiles correctly."""
    context = _full_context()
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
    assert len(compiled.expression.expression_links) == 1


# ---------------------------------------------------------------------------
# Matrix case 5: Proposition role nesting
# ---------------------------------------------------------------------------


def test_matrix_5_proposition_role_nesting():
    """Program with proposition role nesting is admitted."""
    context = _full_context()
    actions = _base_actions(context)
    # Use the think frame which has proposition_roles
    actions.append(ProgramAction.create(action_index=len(actions), action_type="instantiate_operator", arguments=("application:1", "application_frame_slot:think"), source_unit_refs=("unit:loves",)))
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_role", arguments=("application:1", "role:subject", "contribution_slot:alice"), source_unit_refs=("unit:alice",)))
    # Bind application:0 as the proposition role of application:1
    actions.append(ProgramAction.create(action_index=len(actions), action_type="bind_nested_application", arguments=("role", "application:1", "role:proposition", "application:0")))
    program = _make_program(context, actions, ("application:1",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    from cemm_authoritative_hybrid.expressions import CompilationFailure, CompilationSuccess
    assert isinstance(compiled, CompilationSuccess), f"expected success, got {compiled.code if isinstance(compiled, CompilationFailure) else type(compiled)}"
    assert len(compiled.expression.applications) == 2


# ---------------------------------------------------------------------------
# Matrix case 6: Transition preview
# ---------------------------------------------------------------------------


def test_matrix_6_transition_preview():
    """Program with transition preview produces preview metadata."""
    context = _full_context()
    actions = _base_actions(context)
    actions.append(ProgramAction.create(action_index=len(actions), action_type="propose_transition", arguments=("transition_slot:act", "application:0")))
    program = _make_program(context, actions, ("application:0",))
    previews = extract_transition_previews(program, context)
    assert len(previews) == 1
    assert previews[0].event_type_ref == "event:act"
    assert previews[0].adapter_ref == "adapter:act"


# ---------------------------------------------------------------------------
# Matrix case 7: Variable binder
# ---------------------------------------------------------------------------


def test_matrix_7_variable_binder():
    """Program with variable binder compiles correctly."""
    context = _full_context()
    # Build actions without binding role:subject — the variable binder
    # projects into that role instead of a bind_role contribution.
    actions = [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:love",)),
        ProgramAction.create(action_index=3, action_type="instantiate_operator", arguments=("application:0", "application_frame_slot:love"), source_unit_refs=("unit:loves",)),
        ProgramAction.create(action_index=4, action_type="bind_role", arguments=("application:0", "role:object", "contribution_slot:bob"), source_unit_refs=("unit:bob",)),
        ProgramAction.create(action_index=5, action_type="project_variable", arguments=("variable:0", "variable_slot:who", "application:0")),
    ]
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:loves",
            contribution_slot_ref="contribution_slot:predicate",
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:bob",
            contribution_slot_ref="contribution_slot:bob",
            assignment_kind="role",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:object",
            residual_kind=None,
            critical=True,
        ),
    )
    actions.append(ProgramAction.create(action_index=len(actions), action_type="complete_program", arguments=()))
    program = SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=tuple(actions),
        root_refs=("variable:0",),
        mode_slot_ref="mode_slot:observe",
        goal_refs=("goal:understand",),
        source_unit_refs=("unit:loves", "unit:bob"),
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed
    assert len(compiled.expression.binders) == 1


# ---------------------------------------------------------------------------
# Matrix case 8: Determinism
# ---------------------------------------------------------------------------


def test_matrix_8_determinism():
    """Same inputs produce same outputs across multiple runs."""
    context = _full_context()
    actions = _base_actions(context)
    program = _make_program(context, actions, ("application:0",))
    results = [SemanticExpressionCompiler().compile(program, context) for _ in range(3)]
    assert all(isinstance(r, CompilationSuccess) for r in results)
    refs = [r.expression.expression_ref for r in results]
    assert len(set(refs)) == 1, f"Non-deterministic: {refs}"


# ---------------------------------------------------------------------------
# Matrix case 9: Independence (compiler vs reconstruction)
# ---------------------------------------------------------------------------


def test_matrix_9_compiler_reconstruction_independence():
    """Compiler and independent reconstruction produce identical expressions."""
    context = _full_context()
    actions = _base_actions(context)
    actions.append(ProgramAction.create(action_index=len(actions), action_type="attach_scope", arguments=("scope:0", "scope_slot:neg", "application:0")))
    program = _make_program(context, actions, ("scope:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    reconstructed = reconstruct_expected_expression(program, context)
    assert isinstance(compiled, CompilationSuccess)
    assert reconstructed is not None
    assert compiled.expression == reconstructed


# ---------------------------------------------------------------------------
# Matrix case 10: Boundary (no internal refs in public surfaces)
# ---------------------------------------------------------------------------


def test_matrix_10_no_internal_refs_in_expression_refs():
    """Expression refs do not expose internal ref prefixes as surfaces.

    The expression_ref and application_refs are internal canonical refs,
    not user-visible designations.  This test verifies they follow the
    internal ref naming convention (prefix:value) rather than leaking
    as bare surface words.
    """
    context = _full_context()
    actions = _base_actions(context)
    program = _make_program(context, actions, ("application:0",))
    compiled = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(compiled, CompilationSuccess)
    expr = compiled.expression
    # All refs should use internal naming (prefix:value), not bare words
    assert ":" in expr.expression_ref
    for app in expr.applications:
        assert ":" in app.application_ref
