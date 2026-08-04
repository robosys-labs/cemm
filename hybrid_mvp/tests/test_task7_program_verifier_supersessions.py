"""New-ID Task 7 successors for frozen Program ABI 1 assertions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ACTION_ABI_HASH,
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)
from cemm_authoritative_hybrid.proposal import (
    ProposalResult,
    RankedProgramCandidate,
)
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ModeSlot,
    ProposalContext,
    ReferenceSlot,
)
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier


def _pin() -> RevisionPin:
    return RevisionPin(
        "authority:task7",
        1,
        2,
        3,
        4,
        "model:task7",
    )


def _context() -> ProposalContext:
    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref="event:task7",
        target_kind="event_type",
        score_q=900_000,
        designation_fact_ref="designation:task7",
        provenance_refs=("authority:task7",),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate",
        kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref="event:task7",
        target_kind="event_type",
        input_ports=("role:subject",),
        output_ports=("role:event",),
        constraints=(),
        provenance_refs=("designation:task7",),
    )
    reference_contribution = ContributionSlot.create(
        contribution_ref="contribution:reference",
        kind="reference",
        source_unit_refs=("unit:subject",),
        target_ref="entity:alice",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
        provenance_refs=("designation:alice",),
    )
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref=designation.target_ref,
        predicate_kind=designation.target_kind,
        operator_ref="op:event",
        structural_role_ref="role:event",
        required_roles=("role:subject",),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=(),
        affordance_frame_ref="frame:task7",
        provenance_refs=(designation.slot_ref, "frame:task7"),
    )
    references = tuple(
        ReferenceSlot.create(
            target_ref=target_ref,
            target_kind="entity",
            source_unit_refs=("unit:subject",),
            resolution_kind="designation",
            compatible_roles=("role:subject",),
            score_q=score_q,
            provenance_refs=(designation_ref,),
        )
        for target_ref, score_q, designation_ref in (
            ("entity:alice", 900_000, "designation:alice"),
            ("entity:bob", 800_000, "designation:bob"),
        )
    )
    return ProposalContext.create(
        orientation_ref="orientation:task7",
        evidence_packet_ref="evidence:task7",
        form_lattice_ref="lattice:task7",
        grounding_ref="grounding:task7",
        designation_slots=(designation,),
        contribution_slots=(predicate, reference_contribution),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=references,
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:task7",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:subject", 4, 8),
        ),
        revision_pin=_pin(),
    )


def _program(
    context: ProposalContext,
    *,
    reference_slot_ref: str | None = None,
) -> SemanticSwitchProgram:
    selected_reference = reference_slot_ref or context.reference_slots[0].slot_ref
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
            arguments=("application:main", context.application_frames[0].slot_ref),
            source_unit_refs=("unit:predicate",),
        ),
        ProgramAction.create(
            action_index=4,
            action_type="bind_reference",
            arguments=("application:main", "role:subject", selected_reference),
            source_unit_refs=("unit:subject",),
        ),
        ProgramAction.create(
            action_index=5,
            action_type="complete_program",
            arguments=(),
        ),
    )
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:predicate",
            contribution_slot_ref=context.contribution_slots[0].slot_ref,
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=False,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:subject",
            contribution_slot_ref=context.contribution_slots[1].slot_ref,
            assignment_kind="reference",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=False,
        ),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=context.source_unit_refs,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def _abstain_program(context: ProposalContext) -> SemanticSwitchProgram:
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
            action_type="abstain",
            arguments=(),
        ),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=(),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=(),
        source_unit_refs=(),
        source_assignments=(),
        revision_pin=context.revision_pin,
    )


def _proposal(
    context: ProposalContext,
    program: SemanticSwitchProgram,
) -> ProposalResult:
    candidate = RankedProgramCandidate.create(
        rank=0,
        score_q=900_000,
        program=program,
        provenance_refs=("derivation:task7",),
    )
    return ProposalResult.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        candidates=(candidate,),
        status="candidates",
        abstention_code=None,
        explored_states=1,
        truncated=False,
        model_identity=context.revision_pin.model_identity,
        revision_pin=context.revision_pin,
    )


def _valid_action_shapes() -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("select_context", ("proposal_context:one",)),
        ("select_mode", ("mode_slot:one",)),
        ("select_designation", ("designation_slot:one",)),
        (
            "instantiate_operator",
            ("application:one", "application_frame_slot:one"),
        ),
        (
            "bind_role",
            ("application:one", "role:subject", "contribution_slot:one"),
        ),
        (
            "bind_reference",
            ("application:one", "role:subject", "reference_slot:one"),
        ),
        (
            "bind_nested_application",
            ("role", "application:one", "role:content", "application:two"),
        ),
        (
            "attach_scope",
            ("scope:one", "scope_slot:one", "application:one"),
        ),
        (
            "project_variable",
            ("binder:one", "variable_slot:one", "application:one"),
        ),
        (
            "propose_transition",
            ("transition_slot:one", "application:one"),
        ),
        ("complete_program", ()),
        ("abstain", ()),
    )


def test_program_abi2_successor_rejects_unknown_action_type() -> None:
    valid = ProgramAction.create(
        action_index=0,
        action_type="abstain",
        arguments=(),
    )
    assert ProgramAction.from_dict(valid.as_dict()) == valid
    payload = valid.as_dict()
    payload["action_type"] = "not_a_real_action"
    with pytest.raises(ValueError, match="invalid switch action type"):
        ProgramAction.from_dict(payload)


def test_program_abi2_successor_accepts_every_confirmed_action_shape() -> None:
    actions = tuple(
        ProgramAction.create(
            action_index=index,
            action_type=action_type,
            arguments=arguments,
        )
        for index, (action_type, arguments) in enumerate(_valid_action_shapes())
    )
    assert len(actions) == 12
    assert all(ProgramAction.from_dict(row.as_dict()) == row for row in actions)


def test_program_abi2_abstain_has_no_program_owned_operator_semantics() -> None:
    program = _abstain_program(_context())
    assert SemanticSwitchProgram.from_dict(program.as_dict()) == program
    assert not hasattr(program, "persistent_operators")
    assert all(
        not argument.startswith("op:")
        for action in program.actions
        for argument in action.arguments
    )


def test_program_abi2_operator_semantics_reside_in_context_not_program() -> None:
    context = _context()
    program = _program(context)
    assert context.application_frames[0].operator_ref == "op:event"
    assert not hasattr(program, "persistent_operators")
    assert all(
        not argument.startswith("op:")
        for action in program.actions
        for argument in action.arguments
    )


def test_program_abi2_identity_changes_while_action_abi_stays_fixed() -> None:
    context = _context()
    first = _program(context, reference_slot_ref=context.reference_slots[0].slot_ref)
    second = _program(context, reference_slot_ref=context.reference_slots[1].slot_ref)
    assert first.program_ref != second.program_ref
    assert first.action_abi_hash == second.action_abi_hash == ACTION_ABI_HASH


def test_program_abi2_program_action_is_frozen() -> None:
    action = ProgramAction.create(
        action_index=0,
        action_type="abstain",
        arguments=(),
    )
    with pytest.raises(FrozenInstanceError):
        action.action_ref = "program_action:forged"  # type: ignore[misc]


def test_program_abi2_fabricated_reference_slot_is_rejected_by_verifier() -> None:
    context = _context()
    valid = _program(context)
    valid_batch = ExactProgramVerifier().verify_candidates(
        _proposal(context, valid),
        context,
    )
    assert valid_batch.status == "selected"

    fabricated = _program(
        context,
        reference_slot_ref="reference_slot:fabricated",
    )
    assert SemanticSwitchProgram.from_dict(fabricated.as_dict()) == fabricated
    batch = ExactProgramVerifier().verify_candidates(
        _proposal(context, fabricated),
        context,
    )
    codes = tuple(
        error.code
        for receipt in batch.candidate_receipts
        for error in receipt.verification_errors
    )
    assert "unknown_reference_slot" in codes
    assert "action_identity_mismatch" not in codes


def test_program_abi2_adversarial_unknown_action_fails_at_schema() -> None:
    program = _program(_context())
    assert SemanticSwitchProgram.from_dict(program.as_dict()) == program
    payload = program.actions[-1].as_dict()
    payload["action_type"] = "unknown_action"
    with pytest.raises(ValueError, match="invalid switch action type"):
        ProgramAction.from_dict(payload)


def test_program_abi2_invalid_operator_is_rejected_at_frame_owner() -> None:
    context = _context()
    program = _program(context)
    assert SemanticSwitchProgram.from_dict(program.as_dict()) == program
    payload = context.application_frames[0].as_dict()
    payload["operator_ref"] = "op:fabricated"
    with pytest.raises(ValueError, match="invalid persistent operator"):
        ApplicationFrameSlot.from_dict(payload)


__cemm_test_inventory__ = {
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_successor_rejects_unknown_action_type": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:program-abi-program-action-rejects-unknown-action-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "4db5a0dc2e29f7e235f9927aea26b5bb38a84fffc4b38c6bdd0fc6ee359ee008",
        "supersedes_node_id": "tests/test_program_abi.py::test_program_action_rejects_unknown_action_type",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_successor_accepts_every_confirmed_action_shape": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:program-abi-program-action-accepts-every-confirmed-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "9ac304fc929ab06b14162a3c34e0251cf9146b8a0d23bc66f5a87cd3263e53d4",
        "supersedes_node_id": "tests/test_program_abi.py::test_program_action_accepts_every_confirmed_type",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_abstain_has_no_program_owned_operator_semantics": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:program-abi-program-with-no-operator-has-empty-persistent-operators",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "9253e45998368042bba1e6273ce9c3644a470cf01b3997ee06625ff223cf5e4a",
        "supersedes_node_id": "tests/test_program_abi.py::test_program_with_no_operator_has_empty_persistent_operators",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_operator_semantics_reside_in_context_not_program": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:program-abi-program-extracts-operators-from-instantiate-operator-actions",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "23f3550a1dd32905bd98ebc68c1520df0436ecda13b5569bc625eb7ac64c7f16",
        "supersedes_node_id": "tests/test_program_abi.py::test_program_extracts_operators_from_instantiate_operator_actions",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_identity_changes_while_action_abi_stays_fixed": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:program-abi-action-encoding-hash-changes-with-structure",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "d2088b0e7c92c0ba1c340a4b443558f441bd3474e22d4fe10015dac189828343",
        "supersedes_node_id": "tests/test_program_abi.py::test_action_encoding_hash_changes_with_structure",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_program_action_is_frozen": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:program-abi-program-action-is-frozen",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "551615bb83e6705bb0f4831c761aca94675be3e4cc5d2feb39c0e013e899bb7e",
        "supersedes_node_id": "tests/test_program_abi.py::test_program_action_is_frozen",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_fabricated_reference_slot_is_rejected_by_verifier": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:adversarial-programs-fabricated-atom-in-bind-reference-rejected",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "580b636e81474f7498d33adf8f7eea8dcbc3c3f9cc997f8c3a2e5d20532c2aad",
        "supersedes_node_id": "tests/test_adversarial_programs.py::test_fabricated_atom_in_bind_reference_rejected",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_adversarial_unknown_action_fails_at_schema": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:adversarial-programs-unknown-action-type-rejected-by-constructor",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "a968e504c815d0d0cb0d9a694fa15bce9b39c6d9dfc5d38d5c5b429cfd1bbb51",
        "supersedes_node_id": "tests/test_adversarial_programs.py::test_unknown_action_type_rejected_by_constructor",
    },
    "tests/test_task7_program_verifier_supersessions.py::test_program_abi2_invalid_operator_is_rejected_at_frame_owner": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:adversarial-programs-unknown-operator-rejected",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "7fcf3ed3f6456cb9a81043b35e2eb8fb5d36b1747a1e572a0feefbaf64bfd7d7",
        "supersedes_node_id": "tests/test_adversarial_programs.py::test_unknown_operator_rejected",
    },
}
