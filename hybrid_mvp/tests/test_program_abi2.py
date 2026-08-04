"""Program ABI 2 exact action grammar and content identity tests."""

from __future__ import annotations

from dataclasses import fields

import pytest

from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ACTION_ABI_HASH,
    ACTION_ABI_SCHEMAS,
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
    SWITCH_ACTION_TYPES,
)


def _pin(**changes: object) -> RevisionPin:
    values = {
        "authority_generation": "authority:generation-1",
        "world_revision": 1,
        "session_revision": 2,
        "episode_revision": 3,
        "effect_revision": 4,
        "model_identity": "model:one",
    }
    values.update(changes)
    return RevisionPin(**values)  # type: ignore[arg-type]


def _action(
    action_index: int,
    action_type: str,
    arguments: tuple[str, ...],
    source_unit_refs: tuple[str, ...] = (),
) -> ProgramAction:
    return ProgramAction.create(
        action_index=action_index,
        action_type=action_type,
        arguments=arguments,
        source_unit_refs=source_unit_refs,
    )


def _assignment(
    *,
    source_unit_ref: str,
    contribution_slot_ref: str,
    assignment_kind: str,
    target_action_ref: str | None,
    target_role_ref: str | None,
    residual_kind: str | None = None,
    critical: bool,
) -> SourceAssignment:
    return SourceAssignment.create(
        source_unit_ref=source_unit_ref,
        contribution_slot_ref=contribution_slot_ref,
        assignment_kind=assignment_kind,
        target_action_ref=target_action_ref,
        target_role_ref=target_role_ref,
        residual_kind=residual_kind,
        critical=critical,
    )


def _program(
    *,
    orientation_ref: str = "orientation:one",
    proposal_context_ref: str = "proposal_context:one",
    mode_slot_ref: str = "mode_slot:observe",
    revision_pin: RevisionPin | None = None,
    designation_slot_ref: str = "designation_slot:alice",
) -> SemanticSwitchProgram:
    actions = (
        _action(0, "select_context", (proposal_context_ref,)),
        _action(1, "select_mode", (mode_slot_ref,)),
        _action(
            2,
            "select_designation",
            (designation_slot_ref,),
            ("unit:alice",),
        ),
        _action(
            3,
            "instantiate_operator",
            ("application:main", "application_frame_slot:main"),
            ("unit:teaches",),
        ),
        _action(
            4,
            "bind_role",
            ("application:main", "role:actor", "contribution_slot:alice"),
            ("unit:alice",),
        ),
        _action(5, "complete_program", ()),
    )
    assignments = (
        _assignment(
            source_unit_ref="unit:alice",
            contribution_slot_ref="contribution_slot:alice",
            assignment_kind="role",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:actor",
            critical=True,
        ),
        _assignment(
            source_unit_ref="unit:teaches",
            contribution_slot_ref="contribution_slot:teaches",
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            critical=True,
        ),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=orientation_ref,
        proposal_context_ref=proposal_context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=mode_slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=("unit:alice", "unit:teaches"),
        source_assignments=assignments,
        revision_pin=revision_pin or _pin(),
    )


def test_action_abi_hash_covers_one_frozen_schema_for_all_twelve_actions() -> None:
    assert tuple(ACTION_ABI_SCHEMAS) == SWITCH_ACTION_TYPES
    assert ACTION_ABI_HASH.startswith("action_abi:")
    assert len(ACTION_ABI_HASH) == len("action_abi:") + 24


@pytest.mark.parametrize(
    ("action_type", "arguments"),
    (
        ("select_context", ("proposal_context:1",)),
        ("select_mode", ("mode_slot:1",)),
        ("select_designation", ("designation_slot:1",)),
        ("instantiate_operator", ("application:1", "application_frame_slot:1")),
        ("bind_role", ("application:1", "role:actor", "contribution_slot:1")),
        ("bind_reference", ("application:1", "role:actor", "reference_slot:1")),
        ("bind_nested_application", ("role", "application:1", "role:content", "application:2")),
        ("bind_nested_application", ("link", "link:1", "expression_link_slot:1", "application:1", "application:2")),
        ("attach_scope", ("scope:1", "scope_slot:1", "application:1")),
        ("project_variable", ("binder:1", "variable_slot:1", "application:1")),
        ("propose_transition", ("transition_slot:1", "application:1")),
        ("complete_program", ()),
        ("abstain", ()),
    ),
    ids=(
        "context", "mode", "designation", "application", "role", "reference",
        "nested-role", "nested-link", "scope", "variable", "transition",
        "complete", "abstain",
    ),
)
def test_frozen_action_schemas_accept_each_registered_shape(
    action_type: str, arguments: tuple[str, ...]
) -> None:
    action = _action(0, action_type, arguments)
    assert ProgramAction.from_dict(action.as_dict()) == action


@pytest.mark.parametrize(
    ("action_type", "arguments"),
    (
        ("select_context", ()),
        ("complete_program", ("extra",)),
        ("bind_role", ("application:1", "role:actor")),
        ("bind_nested_application", ("banana", "a", "b", "c")),
        ("bind_nested_application", ("link", "link:1", "slot:1", "application:1")),
    ),
    ids=("missing-context", "extra-complete", "short-role", "unknown-variant", "short-link"),
)
def test_frozen_action_schemas_reject_invalid_shapes(
    action_type: str, arguments: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError, match="action schema"):
        _action(0, action_type, arguments)


def test_action_ref_covers_index_type_arguments_and_source_order() -> None:
    base = _action(0, "select_designation", ("designation_slot:alice",), ("unit:a", "unit:b"))
    variants = (
        _action(1, "select_designation", ("designation_slot:alice",), ("unit:a", "unit:b")),
        _action(0, "select_mode", ("designation_slot:alice",), ("unit:a", "unit:b")),
        _action(0, "select_designation", ("designation_slot:bob",), ("unit:a", "unit:b")),
        _action(0, "select_designation", ("designation_slot:alice",), ("unit:b", "unit:a")),
    )
    assert all(item.action_ref != base.action_ref for item in variants)


def test_program_ref_covers_context_pointers_and_complete_revision() -> None:
    base = _program()
    variants = (
        _program(orientation_ref="orientation:two"),
        _program(proposal_context_ref="proposal_context:two"),
        _program(mode_slot_ref="mode_slot:query"),
        _program(designation_slot_ref="designation_slot:bob"),
        _program(revision_pin=_pin(world_revision=9)),
    )
    assert all(item.program_ref != base.program_ref for item in variants)
    assert all(item.action_abi_hash == ACTION_ABI_HASH for item in (base, *variants))


def test_program_contains_derivation_only_and_no_resolved_expression() -> None:
    names = {field.name for field in fields(SemanticSwitchProgram)}
    assert "proposal_context_ref" in names
    assert "resolved_applications" not in names
    assert "semantic_expression" not in names
    assert "expression_ref" not in names
    assert "action_encoding_hash" not in names


def test_canonical_program_round_trip_and_nested_pin_tamper_fail_closed() -> None:
    program = _program()
    assert SemanticSwitchProgram.from_dict(program.as_dict()) == program

    payload = program.as_dict()
    payload["revision_pin"]["world_revision"] = True
    with pytest.raises((TypeError, ValueError), match="world_revision"):
        SemanticSwitchProgram.from_dict(payload)


def test_direct_container_construction_and_nested_ref_tamper_are_rejected() -> None:
    with pytest.raises(TypeError):
        ProgramAction()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        SourceAssignment()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        SemanticSwitchProgram()  # type: ignore[call-arg]
    program = _program()
    with pytest.raises(TypeError):
        SemanticSwitchProgram(  # type: ignore[call-arg]
            "program:forged", program.orientation_ref, program.proposal_context_ref,
            program.actions, program.root_refs, program.mode_slot_ref, program.goal_refs,
            program.source_unit_refs, program.source_assignments, program.revision_pin,
        )

    payload = program.as_dict()
    payload["actions"][4]["arguments"][1] = "role:affected"
    with pytest.raises(ValueError, match="ref mismatch"):
        SemanticSwitchProgram.from_dict(payload)


def test_program_rejects_noncontiguous_actions_unknown_roots_and_bad_assignment_targets() -> None:
    program = _program()
    actions = list(program.actions)
    actions[4] = _action(
        9,
        "bind_role",
        ("application:main", "role:actor", "contribution_slot:alice"),
        ("unit:alice",),
    )
    with pytest.raises(ValueError, match="contiguous"):
        SemanticSwitchProgram.create(
            orientation_ref=program.orientation_ref,
            proposal_context_ref=program.proposal_context_ref,
            actions=tuple(actions),
            root_refs=program.root_refs,
            mode_slot_ref=program.mode_slot_ref,
            goal_refs=program.goal_refs,
            source_unit_refs=program.source_unit_refs,
            source_assignments=program.source_assignments,
            revision_pin=program.revision_pin,
        )

    with pytest.raises(ValueError, match="root"):
        SemanticSwitchProgram.create(
            orientation_ref=program.orientation_ref,
            proposal_context_ref=program.proposal_context_ref,
            actions=program.actions,
            root_refs=("application:missing",),
            mode_slot_ref=program.mode_slot_ref,
            goal_refs=program.goal_refs,
            source_unit_refs=program.source_unit_refs,
            source_assignments=program.source_assignments,
            revision_pin=program.revision_pin,
        )

    bad_assignment = _assignment(
        source_unit_ref="unit:alice",
        contribution_slot_ref="contribution_slot:alice",
        assignment_kind="role",
        target_action_ref="program_action:missing",
        target_role_ref="role:actor",
        critical=True,
    )
    with pytest.raises(ValueError, match="assignment target"):
        SemanticSwitchProgram.create(
            orientation_ref=program.orientation_ref,
            proposal_context_ref=program.proposal_context_ref,
            actions=program.actions,
            root_refs=program.root_refs,
            mode_slot_ref=program.mode_slot_ref,
            goal_refs=program.goal_refs,
            source_unit_refs=program.source_unit_refs,
            source_assignments=(bad_assignment, program.source_assignments[1]),
            revision_pin=program.revision_pin,
        )

__cemm_test_inventory__ = {'tests/test_program_abi2.py::test_action_abi_hash_covers_one_frozen_schema_for_all_twelve_actions': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-program-abi2-test-action-abi-hash-covers-one-frozen-schema-for-all-twelve-actions',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': '00ea3c419d400f48f7c587fd330ac1a505a53f729c60b08908d79ab996eae85c'},
 'tests/test_program_abi2.py::test_action_ref_covers_index_type_arguments_and_source_order': {'activation_phase': 'R1',
                                                                                              'assertion_ref': 'assertion:r1-program-abi2-test-action-ref-covers-index-type-arguments-and-source-order',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                              'owner_ref': 'program-verifier',
                                                                                              'source_ast_sha256': 'ef5cbfebda4dd171ddc3c874dca109d100ce0299ae92d76d826db4cd7b192ec5'},
 'tests/test_program_abi2.py::test_canonical_program_round_trip_and_nested_pin_tamper_fail_closed': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-program-abi2-test-canonical-program-round-trip-and-nested-pin-tamper-fail-closed',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '320668a12740f453b0d818946aafd80916f39ab419391d5c07023bb84fa19b35'},
 'tests/test_program_abi2.py::test_direct_container_construction_and_nested_ref_tamper_are_rejected': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-program-abi2-test-direct-container-construction-and-nested-ref-tamper-are-rejected',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': '67cba5c2e65243f0e264970ae186fb9353634a167e1ea2a74831549395189ccd'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[abstain]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-abstain',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[application]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-application',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[complete]': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-complete',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[context]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-context',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[designation]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-designation',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[mode]': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-mode',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                               'owner_ref': 'program-verifier',
                                                                                               'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[nested-link]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-nested-link',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[nested-role]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-nested-role',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[reference]': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-reference',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[role]': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-role',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                               'owner_ref': 'program-verifier',
                                                                                               'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[scope]': {'activation_phase': 'R1',
                                                                                                'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-scope',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                'owner_ref': 'program-verifier',
                                                                                                'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[transition]': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-transition',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_accept_each_registered_shape[variable]': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-accept-each-registered-shape-variable',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': 'd4f0f12d50bd0882c7116ccbeb1e4ead960fbaef833750ef4a70df7ae7090dd3'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_reject_invalid_shapes[extra-complete]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-reject-invalid-shapes-extra-complete',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '4653769e2c91b47c9f82ab65ac7b0dc9f31688b8347c16e648117ff49f0fb446'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_reject_invalid_shapes[missing-context]': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-reject-invalid-shapes-missing-context',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': '4653769e2c91b47c9f82ab65ac7b0dc9f31688b8347c16e648117ff49f0fb446'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_reject_invalid_shapes[short-link]': {'activation_phase': 'R1',
                                                                                              'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-reject-invalid-shapes-short-link',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                              'owner_ref': 'program-verifier',
                                                                                              'source_ast_sha256': '4653769e2c91b47c9f82ab65ac7b0dc9f31688b8347c16e648117ff49f0fb446'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_reject_invalid_shapes[short-role]': {'activation_phase': 'R1',
                                                                                              'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-reject-invalid-shapes-short-role',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                              'owner_ref': 'program-verifier',
                                                                                              'source_ast_sha256': '4653769e2c91b47c9f82ab65ac7b0dc9f31688b8347c16e648117ff49f0fb446'},
 'tests/test_program_abi2.py::test_frozen_action_schemas_reject_invalid_shapes[unknown-variant]': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-program-abi2-test-frozen-action-schemas-reject-invalid-shapes-unknown-variant',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': '4653769e2c91b47c9f82ab65ac7b0dc9f31688b8347c16e648117ff49f0fb446'},
 'tests/test_program_abi2.py::test_program_contains_derivation_only_and_no_resolved_expression': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-program-abi2-test-program-contains-derivation-only-and-no-resolved-expression',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '73857fcb11166f728539e52135e61e715f2e9b530a463086cbe978744a38c5ea'},
 'tests/test_program_abi2.py::test_program_ref_covers_context_pointers_and_complete_revision': {'activation_phase': 'R1',
                                                                                                'assertion_ref': 'assertion:r1-program-abi2-test-program-ref-covers-context-pointers-and-complete-revision',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                'owner_ref': 'program-verifier',
                                                                                                'source_ast_sha256': 'b2564178e99c6f59abba968795fa983b5053179aa50cbc91a570646031a77df2'},
 'tests/test_program_abi2.py::test_program_rejects_noncontiguous_actions_unknown_roots_and_bad_assignment_targets': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:r1-program-abi2-test-program-rejects-noncontiguous-actions-unknown-roots-and-bad-assignment-targets',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                                     'owner_ref': 'program-verifier',
                                                                                                                     'source_ast_sha256': '11b2daf08ac60b1a8a554ff706c521e6f5d3237750c41d84720e54b01cea4ac6'}}
