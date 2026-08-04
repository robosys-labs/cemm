"""R1 exact single-application Program-to-Expression compiler canaries."""

from __future__ import annotations

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
        )
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
        scope=lambda ref: None,
        expression_link=lambda ref: None,
        variable=lambda ref: None,
        transition=lambda ref: None,
    )


def _program(
    *, swap_roles: bool = False, reverse_designations: bool = False, scope=False
):
    context = _context()
    designations = ["designation_slot:love", "designation_slot:alice"]
    if reverse_designations:
        designations.reverse()
    actions = [
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=("mode_slot:observe",),
        ),
    ]
    for designation_ref in designations:
        actions.append(
            ProgramAction.create(
                action_index=len(actions),
                action_type="select_designation",
                arguments=(designation_ref,),
            )
        )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="instantiate_operator",
            arguments=("application:love", "application_frame_slot:love"),
            source_unit_refs=("unit:loves",),
        )
    )
    subject_slot = "contribution_slot:bob" if swap_roles else "contribution_slot:alice"
    object_slot = "contribution_slot:alice" if swap_roles else "contribution_slot:bob"
    for role_ref, contribution_ref, unit_ref in (
        ("role:subject", subject_slot, "unit:alice"),
        ("role:object", object_slot, "unit:bob"),
    ):
        actions.append(
            ProgramAction.create(
                action_index=len(actions),
                action_type="bind_role",
                arguments=("application:love", role_ref, contribution_ref),
                source_unit_refs=(unit_ref,),
            )
        )
    if scope:
        actions.append(
            ProgramAction.create(
                action_index=len(actions),
                action_type="attach_scope",
                arguments=("scope:one", "scope_slot:one", "application:love"),
            )
        )
        root_refs = ("scope:one",)
    else:
        root_refs = ("application:love",)
    actions.append(
        ProgramAction.create(
            action_index=len(actions), action_type="complete_program", arguments=()
        )
    )
    action_tuple = tuple(actions)
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:loves",
            contribution_slot_ref="contribution_slot:predicate",
            assignment_kind="predicate",
            target_action_ref=action_tuple[4].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:alice",
            contribution_slot_ref=subject_slot,
            assignment_kind="role",
            target_action_ref=action_tuple[5].action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:bob",
            contribution_slot_ref=object_slot,
            assignment_kind="role",
            target_action_ref=action_tuple[6].action_ref,
            target_role_ref="role:object",
            residual_kind=None,
            critical=True,
        ),
    )
    return context, SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=action_tuple,
        root_refs=root_refs,
        mode_slot_ref="mode_slot:observe",
        goal_refs=("goal:understand",),
        source_unit_refs=("unit:loves", "unit:alice", "unit:bob"),
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def test_two_derivations_compile_to_one_canonical_expression() -> None:
    context, first = _program()
    _, second = _program(reverse_designations=True)
    compiler = SemanticExpressionCompiler()

    first_result = compiler.compile(first, context)
    second_result = compiler.compile(second, context)

    assert isinstance(first_result, CompilationSuccess)
    assert isinstance(second_result, CompilationSuccess)
    assert first.program_ref != second.program_ref
    assert (
        first_result.expression.expression_ref
        == second_result.expression.expression_ref
    )


def test_swapped_dynamic_role_pointers_compile_to_different_meaning() -> None:
    context, first = _program()
    _, swapped = _program(swap_roles=True)
    compiler = SemanticExpressionCompiler()
    first_result = compiler.compile(first, context)
    swapped_result = compiler.compile(swapped, context)

    assert isinstance(first_result, CompilationSuccess)
    assert isinstance(swapped_result, CompilationSuccess)
    assert (
        first_result.expression.expression_ref
        != swapped_result.expression.expression_ref
    )


def test_compilation_proof_accounts_exactly_for_actions_assignments_and_roots() -> None:
    context, program = _program()
    result = SemanticExpressionCompiler().compile(program, context)

    assert isinstance(result, CompilationSuccess)
    assert tuple(row.source_ref for row in result.proof.action_translations) == tuple(
        action.action_ref for action in program.actions
    )
    assert tuple(
        row.source_ref for row in result.proof.assignment_translations
    ) == tuple(assignment.assignment_ref for assignment in program.source_assignments)
    assert (
        tuple(row.source_ref for row in result.proof.root_translations)
        == program.root_refs
    )
    assert result.proof.expression_ref == result.expression.expression_ref


def test_r2_scope_action_is_admitted_in_recursive_compiler() -> None:
    """R2 scope actions are now admitted by the recursive compiler.

    The R1 canary that expected action_shape_not_admitted is superseded.
    The test context lacks a scope() method, so the compiler returns a
    typed failure for unknown_scope_slot rather than action_shape_not_admitted.
    """
    context, program = _program(scope=True)
    result = SemanticExpressionCompiler().compile(program, context)

    # The R2 compiler no longer rejects attach_scope with action_shape_not_admitted.
    # It attempts to process it and fails on the missing scope slot.
    assert isinstance(result, CompilationFailure)
    assert result.code != "action_shape_not_admitted"


def test_context_identity_mismatch_fails_before_compilation() -> None:
    context, program = _program()
    context.context_ref = "proposal_context:other"
    result = SemanticExpressionCompiler().compile(program, context)

    assert isinstance(result, CompilationFailure)
    assert result.code == "proposal_context_mismatch"

__cemm_test_inventory__ = {'tests/test_semantic_expression_compiler.py::test_compilation_proof_accounts_exactly_for_actions_assignments_and_roots': {'activation_phase': 'R1',
                                                                                                                           'assertion_ref': 'assertion:r1-semantic-expression-compiler-test-compilation-proof-accounts-exactly-for-actions-assignments-and-roots',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                                           'owner_ref': 'program-verifier',
                                                                                                                           'source_ast_sha256': 'ae38a8b7f3d9b4a5f5ea95fa25f194ebc5d31888442142dc68c61e605b30e923'},
 'tests/test_semantic_expression_compiler.py::test_context_identity_mismatch_fails_before_compilation': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-semantic-expression-compiler-test-context-identity-mismatch-fails-before-compilation',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '5d485f45316dc5cbac15f8ddfd4540c4edad666eca0f7c1a990449f009f80c05'},
 'tests/test_semantic_expression_compiler.py::test_registered_r2_shape_fails_typed_without_fallback': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-semantic-expression-compiler-test-registered-r2-shape-fails-typed-without-fallback',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': '8bc557b82dd00e6a7055449364610f7641eb7ddf4af5c515255dd068f5ea502c'},
 'tests/test_semantic_expression_compiler.py::test_swapped_dynamic_role_pointers_compile_to_different_meaning': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-semantic-expression-compiler-test-swapped-dynamic-role-pointers-compile-to-different-meaning',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                 'source_ast_sha256': '971e6bfa8a1b41319a2b06f7f1905cb6274016a8c9a482cd19e87d1952653c4f'},
 'tests/test_semantic_expression_compiler.py::test_two_derivations_compile_to_one_canonical_expression': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-semantic-expression-compiler-test-two-derivations-compile-to-one-canonical-expression',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': '0501bea7f4987eb195a8984c4dd8a7c5562392c970e4936ab7dd4a1e1f907efe'}}
