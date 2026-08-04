"""Focused Source Coverage ABI 2 tests."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from types import MappingProxyType, SimpleNamespace

import pytest

from cemm_authoritative_hybrid.coverage import (
    COVERAGE_ABI_VERSION,
    CoverageReceipt,
    CoverageVerifier,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ExpressionLinkSlot,
    ModeSlot,
    ProposalContext,
    ResidualEvidence,
    TransitionSlot,
    VariableSlot,
)
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)


def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 1, 2, 3, 4, "model:test")


def _alter(value, **updates):
    """Forge a deliberately non-canonical typed value for negative tests."""
    if is_dataclass(value):
        result = object.__new__(type(value))
        for field in fields(value):
            object.__setattr__(
                result, field.name, updates.get(field.name, getattr(value, field.name))
            )
        return result
    return SimpleNamespace(**(vars(value) | updates))


def _assignment(row: SourceAssignment, **updates) -> SourceAssignment:
    values = {
        "source_unit_ref": row.source_unit_ref,
        "contribution_slot_ref": row.contribution_slot_ref,
        "assignment_kind": row.assignment_kind,
        "target_action_ref": row.target_action_ref,
        "target_role_ref": row.target_role_ref,
        "residual_kind": row.residual_kind,
        "critical": row.critical,
    }
    return SourceAssignment.create(**(values | updates))


def _action(row: ProgramAction, **updates) -> ProgramAction:
    values = {
        "action_index": row.action_index,
        "action_type": row.action_type,
        "arguments": row.arguments,
        "source_unit_refs": row.source_unit_refs,
    }
    return ProgramAction.create(**(values | updates))


def _context(*, residual: bool = False, noncritical: bool = False) -> ProposalContext:
    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref="event:test",
        target_kind="event_type",
        score_q=900_000,
        designation_fact_ref="designation:test",
        provenance_refs=("authority:test",),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate",
        kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref="event:test",
        target_kind="event_type",
        input_ports=("role:subject",),
        output_ports=("role:event",),
        constraints=(),
    )
    subject = ContributionSlot.create(
        contribution_ref="contribution:subject",
        kind="discourse" if noncritical else "anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:test",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
    )
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref="event:test",
        predicate_kind="event_type",
        operator_ref="op:event",
        structural_role_ref="role:event",
        required_roles=("role:subject",),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=(),
        affordance_frame_ref="frame:event-test",
        provenance_refs=(designation.slot_ref, "authority:test", "frame:event-test"),
    )
    residuals = ()
    if residual:
        residuals = (
            ResidualEvidence.create(
                source_unit_ref="unit:subject",
                contribution_kind="discourse" if noncritical else "anchor",
                critical=not noncritical,
                reason=(
                    "reviewed punctuation"
                    if noncritical
                    else "unresolved open-class evidence"
                ),
            ),
        )
    return ProposalContext.create(
        orientation_ref="orientation:test",
        evidence_packet_ref="evidence:test",
        form_lattice_ref="lattice:test",
        grounding_ref="grounding:test",
        designation_slots=(designation,),
        contribution_slots=(predicate,) if residual else (predicate, subject),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=residuals,
        context_refs=("turn:test",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(("unit:predicate", 0, 5), ("unit:subject", 5, 9)),
        revision_pin=_pin(),
    )


def _rebuild_context(context: ProposalContext, **updates) -> ProposalContext:
    values = {
        "orientation_ref": context.orientation_ref,
        "evidence_packet_ref": context.evidence_packet_ref,
        "form_lattice_ref": context.form_lattice_ref,
        "grounding_ref": context.grounding_ref,
        "designation_slots": context.designation_slots,
        "contribution_slots": context.contribution_slots,
        "mode_slots": context.mode_slots,
        "application_frames": context.application_frames,
        "reference_slots": context.reference_slots,
        "scope_slots": context.scope_slots,
        "expression_link_slots": context.expression_link_slots,
        "variable_slots": context.variable_slots,
        "transition_slots": context.transition_slots,
        "residual_evidence": context.residual_evidence,
        "context_refs": context.context_refs,
        "source_unit_refs": context.source_unit_refs,
        "source_unit_spans": context.source_unit_spans,
        "revision_pin": context.revision_pin,
    }
    return ProposalContext.create(**(values | updates))


def _program(
    context: ProposalContext, *, residual: bool = False
) -> SemanticSwitchProgram:
    actions = [
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
            arguments=("application:0", context.application_frames[0].slot_ref),
            source_unit_refs=("unit:predicate",),
        ),
    ]
    if not residual:
        actions.append(
            ProgramAction.create(
                action_index=4,
                action_type="bind_role",
                arguments=(
                    "application:0",
                    "role:subject",
                    context.contribution_slots[1].slot_ref,
                ),
                source_unit_refs=("unit:subject",),
            )
        )
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="complete_program",
            arguments=(),
        )
    )
    assignments = [
        SourceAssignment.create(
            source_unit_ref="unit:predicate",
            contribution_slot_ref=context.contribution_slots[0].slot_ref,
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=False,
        )
    ]
    if residual:
        residual_evidence = context.residual_evidence[0]
        assignments.append(
            SourceAssignment.create(
                source_unit_ref="unit:subject",
                contribution_slot_ref=residual_evidence.residual_ref,
                assignment_kind="residual",
                target_action_ref=None,
                target_role_ref=None,
                residual_kind=residual_evidence.contribution_kind,
                critical=residual_evidence.critical,
            )
        )
    else:
        assignments.append(
            SourceAssignment.create(
                source_unit_ref="unit:subject",
                contribution_slot_ref=context.contribution_slots[1].slot_ref,
                assignment_kind="role",
                target_action_ref=actions[4].action_ref,
                target_role_ref="role:subject",
                residual_kind=None,
                critical=False,
            )
        )
    return SemanticSwitchProgram.create(
        orientation_ref="orientation:test",
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:0",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=(),
        source_unit_refs=context.source_unit_refs,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def _codes(receipt: CoverageReceipt) -> set[str]:
    return {error.code for error in receipt.errors}


def test_coverage_requires_the_exact_proposal_context_owner() -> None:
    context = _context()
    program = _program(context)
    impostor = SimpleNamespace(**vars(context))

    with pytest.raises(TypeError, match="ProposalContext"):
        CoverageVerifier().verify(impostor, program)


def test_conflicting_contribution_and_residual_metadata_fails_closed() -> None:
    context = _context(residual=True, noncritical=True)
    conflict = ContributionSlot.create(
        contribution_ref="contribution:conflicting-anchor",
        kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:test",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
    )
    by_ref = MappingProxyType(
        {
            **dict(context._contribution_by_ref),
            conflict.slot_ref: len(context.contribution_slots),
        }
    )
    updates: dict[str, object] = {
        "contribution_slots": (*context.contribution_slots, conflict),
        "_contribution_by_ref": by_ref,
    }
    if hasattr(context, "_contributions_by_source"):
        updates["_contributions_by_source"] = MappingProxyType(
            {"unit:predicate": (0,), "unit:subject": (1,)}
        )
    conflicting_context = _alter(context, **updates)

    receipt = CoverageVerifier().verify(
        conflicting_context, _program(context, residual=True)
    )

    assert "context_residual_contribution_conflict" in _codes(receipt)
    assert receipt.critical_residuals[0].contribution_kind == "anchor"
    assert not receipt.executable


def test_contribution_kind_cannot_masquerade_as_predicate() -> None:
    context = _context()
    predicate = context.contribution_slots[0]
    anchor = ContributionSlot.create(
        contribution_ref=predicate.contribution_ref,
        kind="anchor",
        source_unit_refs=predicate.source_unit_refs,
        target_ref=predicate.target_ref,
        target_kind=predicate.target_kind,
        input_ports=predicate.input_ports,
        output_ports=predicate.output_ports,
        constraints=predicate.constraints,
    )
    with pytest.raises(ValueError, match="roles are not proven"):
        _rebuild_context(
            context, contribution_slots=(anchor, context.contribution_slots[1])
        )


@pytest.mark.parametrize(
    "kind",
    (
        "predicate",
        "binder",
        "reference",
        "scope",
        "discourse",
        "connector",
        "qualifier",
        "open_variable",
    ),
    ids=(
        "predicate",
        "binder",
        "reference",
        "scope",
        "discourse",
        "connector",
        "qualifier",
        "open-variable",
    ),
)
def test_non_anchor_contribution_kinds_cannot_masquerade_as_role(kind: str) -> None:
    context = _context()
    original = context.contribution_slots[1]
    replacement = ContributionSlot.create(
        contribution_ref=f"contribution:{kind}",
        kind=kind,
        source_unit_refs=original.source_unit_refs,
        target_ref=original.target_ref,
        target_kind=original.target_kind,
        input_ports=original.input_ports,
        output_ports=original.output_ports,
        constraints=original.constraints,
    )
    context = _rebuild_context(
        context,
        contribution_slots=(context.contribution_slots[0], replacement),
    )

    receipt = CoverageVerifier().verify(context, _program(context))

    assert "contribution_assignment_kind_mismatch" in _codes(receipt)
    assert not receipt.executable


def test_select_designation_is_source_neutral() -> None:
    context = _context()
    program = _program(context)
    select = _action(program.actions[2], source_unit_refs=("unit:predicate",))
    instantiate = _action(program.actions[3], source_unit_refs=())
    assignment = _assignment(
        program.source_assignments[0], target_action_ref=select.action_ref
    )
    forged = _alter(
        program,
        actions=(*program.actions[:2], select, instantiate, *program.actions[4:]),
        source_assignments=(assignment, program.source_assignments[1]),
    )

    receipt = CoverageVerifier().verify(context, forged)

    assert "incompatible_target_action" in _codes(receipt)
    assert not receipt.executable


def test_non_role_assignment_rejects_irrelevant_target_role() -> None:
    context = _context()
    program = _program(context)
    assignment = _assignment(
        program.source_assignments[0], target_role_ref="role:irrelevant"
    )
    forged = _alter(
        program,
        source_assignments=(assignment, program.source_assignments[1]),
    )

    receipt = CoverageVerifier().verify(context, forged)

    assert "irrelevant_target_role" in _codes(receipt)


def test_program_source_order_mismatch_is_retained_and_fails_closed() -> None:
    context = _context()
    program = _alter(
        _program(context),
        source_unit_refs=("unit:subject", "unit:predicate"),
    )

    receipt = CoverageVerifier().verify(context, program)

    assert "program_source_order_mismatch" in _codes(receipt)
    assert not receipt.executable


def test_extra_assignment_is_not_a_successful_assignment_partition() -> None:
    context = _context()
    program = _program(context)
    instantiate = _alter(
        program.actions[3],
        source_unit_refs=("unit:predicate", "unit:extra"),
    )
    extra_assignment = SourceAssignment.create(
        source_unit_ref="unit:extra",
        contribution_slot_ref=context.contribution_slots[0].slot_ref,
        assignment_kind="predicate",
        target_action_ref=instantiate.action_ref,
        target_role_ref=None,
        residual_kind=None,
        critical=False,
    )
    forged = _alter(
        program,
        actions=(*program.actions[:3], instantiate, *program.actions[4:]),
        source_unit_refs=(*program.source_unit_refs, "unit:extra"),
        source_assignments=(*program.source_assignments, extra_assignment),
    )

    receipt = CoverageVerifier().verify(context, forged)

    assert "unit:extra" in receipt.extra_unit_refs
    assert "unit:extra" not in receipt.assigned_unit_refs
    assert not receipt.executable


def test_nested_role_requires_parent_proposition_role() -> None:
    context = _context()
    program = _program(context)
    child = ProgramAction.create(
        action_index=5,
        action_type="instantiate_operator",
        arguments=("application:1", context.application_frames[0].slot_ref),
    )
    nested = ProgramAction.create(
        action_index=6,
        action_type="bind_nested_application",
        arguments=("role", "application:0", "role:subject", "application:1"),
    )
    terminal = ProgramAction.create(
        action_index=7, action_type="complete_program", arguments=()
    )
    candidate = SemanticSwitchProgram.create(
        orientation_ref=program.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=(*program.actions[:-1], child, nested, terminal),
        root_refs=program.root_refs,
        mode_slot_ref=program.mode_slot_ref,
        goal_refs=program.goal_refs,
        source_unit_refs=program.source_unit_refs,
        source_assignments=program.source_assignments,
        revision_pin=program.revision_pin,
    )

    receipt = CoverageVerifier().verify(context, candidate)

    assert "nested_role_not_proposition_role" in _codes(receipt)


def test_expression_link_arity_is_checked_against_exact_context_slot() -> None:
    context = _context()
    link = ExpressionLinkSlot.create(
        link_type="link:sequence",
        commutative=False,
        min_arity=3,
        max_arity=3,
        source_unit_refs=(),
        construction_ref="construction:sequence",
    )
    context = _rebuild_context(context, expression_link_slots=(link,))
    program = _program(context)
    child = ProgramAction.create(
        action_index=5,
        action_type="instantiate_operator",
        arguments=("application:1", context.application_frames[0].slot_ref),
    )
    link_action = ProgramAction.create(
        action_index=6,
        action_type="bind_nested_application",
        arguments=("link", "link:0", link.slot_ref, "application:0", "application:1"),
    )
    terminal = ProgramAction.create(
        action_index=7, action_type="complete_program", arguments=()
    )
    candidate = SemanticSwitchProgram.create(
        orientation_ref=program.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=(*program.actions[:-1], child, link_action, terminal),
        root_refs=program.root_refs,
        mode_slot_ref=program.mode_slot_ref,
        goal_refs=program.goal_refs,
        source_unit_refs=program.source_unit_refs,
        source_assignments=program.source_assignments,
        revision_pin=program.revision_pin,
    )

    receipt = CoverageVerifier().verify(context, candidate)

    assert "expression_link_arity_mismatch" in _codes(receipt)


def test_variable_slot_role_must_belong_to_its_exact_body_frame() -> None:
    context = _context()
    variable = VariableSlot.create(
        application_frame_ref=context.application_frames[0].slot_ref,
        role_ref="role:object",
        required_kinds=("entity",),
        source_unit_refs=(),
        construction_ref="construction:query",
    )
    context = _rebuild_context(context, variable_slots=(variable,))
    program = _program(context)
    project = ProgramAction.create(
        action_index=5,
        action_type="project_variable",
        arguments=("binder:0", variable.slot_ref, "application:0"),
    )
    terminal = ProgramAction.create(
        action_index=6, action_type="complete_program", arguments=()
    )
    candidate = SemanticSwitchProgram.create(
        orientation_ref=program.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=(*program.actions[:-1], project, terminal),
        root_refs=program.root_refs,
        mode_slot_ref=program.mode_slot_ref,
        goal_refs=program.goal_refs,
        source_unit_refs=program.source_unit_refs,
        source_assignments=program.source_assignments,
        revision_pin=program.revision_pin,
    )

    receipt = CoverageVerifier().verify(context, candidate)

    assert "variable_role_incompatible" in _codes(receipt)


def test_transition_requires_exact_state_application_source() -> None:
    context = _context()
    transition = TransitionSlot.create(
        application_frame_ref=context.application_frames[0].slot_ref,
        event_type_ref="event:transition",
        compatible_modes=("REQUEST",),
        required_roles=("role:subject",),
        required_capabilities=(),
        required_permissions=(),
        adapter_ref=None,
        source_unit_refs=(),
    )
    context = _alter(
        context,
        transition_slots=(transition,),
        _transition_by_ref=MappingProxyType({transition.slot_ref: 0}),
    )
    program = _program(context)
    propose = ProgramAction.create(
        action_index=5,
        action_type="propose_transition",
        arguments=(transition.slot_ref, "application:0"),
    )
    terminal = ProgramAction.create(
        action_index=6, action_type="complete_program", arguments=()
    )
    candidate = SemanticSwitchProgram.create(
        orientation_ref=program.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=(*program.actions[:-1], propose, terminal),
        root_refs=program.root_refs,
        mode_slot_ref=program.mode_slot_ref,
        goal_refs=program.goal_refs,
        source_unit_refs=program.source_unit_refs,
        source_assignments=program.source_assignments,
        revision_pin=program.revision_pin,
    )

    receipt = CoverageVerifier().verify(context, candidate)

    assert "transition_source_not_state" in _codes(receipt)


def test_error_overflow_is_explicit_and_fails_closed(monkeypatch) -> None:
    from cemm_authoritative_hybrid import coverage as coverage_module

    context = _context()
    program = _alter(
        _program(context),
        proposal_context_ref="proposal_context:wrong",
        source_unit_refs=("unit:extra",),
    )
    monkeypatch.setattr(coverage_module, "_MAX_ERRORS", 1)

    receipt = CoverageVerifier().verify(context, program)

    assert tuple(error.code for error in receipt.errors) == ("coverage_error_overflow",)
    assert not receipt.executable


def test_exact_context_program_coverage_is_content_addressed_and_round_trips():
    context = _context()
    program = _program(context)

    receipt = CoverageVerifier().verify(context, program)

    assert receipt.abi_version == COVERAGE_ABI_VERSION == 2
    assert receipt.executable
    assert receipt.errors == ()
    assert receipt.assignments == program.source_assignments
    assert receipt.proposal_context_ref == context.context_ref
    assert receipt.revision_pin == context.revision_pin
    assert CoverageReceipt.from_dict(receipt.as_dict()) == receipt


def _receipt_fields(receipt: CoverageReceipt) -> dict[str, object]:
    return {
        "program_ref": receipt.program_ref,
        "proposal_context_ref": receipt.proposal_context_ref,
        "source_unit_refs": receipt.source_unit_refs,
        "program_source_unit_refs": receipt.program_source_unit_refs,
        "assignments": receipt.assignments,
        "assigned_unit_refs": receipt.assigned_unit_refs,
        "residual_unit_refs": receipt.residual_unit_refs,
        "duplicate_unit_refs": receipt.duplicate_unit_refs,
        "missing_unit_refs": receipt.missing_unit_refs,
        "extra_unit_refs": receipt.extra_unit_refs,
        "critical_residuals": receipt.critical_residuals,
        "errors": receipt.errors,
        "executable": receipt.executable,
        "revision_pin": receipt.revision_pin,
    }


def test_direct_coverage_receipt_construction_is_blocked() -> None:
    with pytest.raises(TypeError, match="CoverageReceipt.create"):
        CoverageReceipt()


@pytest.mark.parametrize(
    ("updates", "message"),
    (
        ({"assigned_unit_refs": ("unit:predicate", "unit:predicate")}, "duplicate"),
        ({"residual_unit_refs": ("unit:predicate",)}, "overlap"),
        ({"assigned_unit_refs": ()}, "assigned"),
        ({"residual_unit_refs": ("unit:subject",)}, "residual"),
        ({"duplicate_unit_refs": ("unit:predicate",)}, "duplicate"),
        ({"missing_unit_refs": ("unit:predicate",)}, "missing"),
        ({"extra_unit_refs": ("unit:predicate",)}, "extra"),
    ),
    ids=(
        "duplicate-partition-ref",
        "assigned-residual-overlap",
        "assigned-summary-mismatch",
        "residual-summary-mismatch",
        "duplicate-summary-mismatch",
        "missing-summary-mismatch",
        "extra-summary-mismatch",
    ),
)
def test_receipt_create_rejects_incoherent_partition_summaries(
    updates: dict[str, object], message: str
) -> None:
    context = _context()
    receipt = CoverageVerifier().verify(context, _program(context))

    with pytest.raises(ValueError, match=message):
        CoverageReceipt.create(**(_receipt_fields(receipt) | updates))


def test_receipt_rejects_executable_true_with_retained_failure_evidence() -> None:
    context = _context(residual=True)
    receipt = CoverageVerifier().verify(context, _program(context, residual=True))

    with pytest.raises(ValueError, match="executable"):
        CoverageReceipt.create(**(_receipt_fields(receipt) | {"executable": True}))


def test_context_owned_residual_ref_does_not_require_a_contribution_slot() -> None:
    original = _context(residual=True)
    context = ProposalContext.create(
        orientation_ref=original.orientation_ref,
        evidence_packet_ref=original.evidence_packet_ref,
        form_lattice_ref=original.form_lattice_ref,
        grounding_ref=original.grounding_ref,
        designation_slots=original.designation_slots,
        contribution_slots=(original.contribution_slots[0],),
        mode_slots=original.mode_slots,
        application_frames=original.application_frames,
        reference_slots=original.reference_slots,
        scope_slots=original.scope_slots,
        expression_link_slots=original.expression_link_slots,
        variable_slots=original.variable_slots,
        transition_slots=original.transition_slots,
        residual_evidence=original.residual_evidence,
        context_refs=original.context_refs,
        source_unit_refs=original.source_unit_refs,
        source_unit_spans=original.source_unit_spans,
        revision_pin=original.revision_pin,
    )
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
            arguments=("application:0", context.application_frames[0].slot_ref),
            source_unit_refs=("unit:predicate",),
        ),
        ProgramAction.create(
            action_index=4,
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
            contribution_slot_ref=context.residual_evidence[0].residual_ref,
            assignment_kind="residual",
            target_action_ref=None,
            target_role_ref=None,
            residual_kind="anchor",
            critical=True,
        ),
    )
    program = SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:0",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=(),
        source_unit_refs=context.source_unit_refs,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )

    receipt = CoverageVerifier().verify(context, program)

    assert receipt.errors == ()
    assert not receipt.executable
    assert receipt.critical_residuals[0].contribution_slot_ref == (
        context.residual_evidence[0].residual_ref
    )


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    (
        (
            lambda context, program: _alter(
                program, proposal_context_ref="proposal_context:other"
            ),
            "proposal_context_mismatch",
        ),
        (
            lambda context, program: _alter(
                program, source_unit_refs=("unit:predicate",)
            ),
            "missing_source_unit",
        ),
        (
            lambda context, program: _alter(
                program,
                source_unit_refs=(*program.source_unit_refs, "unit:extra"),
            ),
            "extra_source_unit",
        ),
        (
            lambda context, program: _alter(
                program,
                source_assignments=(
                    program.source_assignments[0],
                    program.source_assignments[0],
                ),
            ),
            "duplicate_source_assignment",
        ),
        (
            lambda context, program: _alter(
                program,
                source_assignments=(
                    _assignment(
                        program.source_assignments[0],
                        contribution_slot_ref="contribution:unknown",
                    ),
                    program.source_assignments[1],
                ),
            ),
            "unknown_contribution_slot",
        ),
    ),
    ids=(
        "wrong-context",
        "missing-source",
        "extra-source",
        "duplicate-source",
        "unknown-contribution",
    ),
)
def test_exact_source_and_context_failures_are_retained(mutator, expected_code):
    context = _context()
    program = mutator(context, _program(context))

    receipt = CoverageVerifier().verify(context, program)

    assert not receipt.executable
    assert expected_code in _codes(receipt)
    assert CoverageReceipt.from_dict(receipt.as_dict()) == receipt


@pytest.mark.parametrize(
    ("assignment_update", "expected_code"),
    (
        ({"target_action_ref": "program_action:unknown"}, "unknown_target_action"),
        ({"target_role_ref": "role:object"}, "incompatible_target_role"),
        ({"assignment_kind": "scope"}, "incompatible_target_action"),
    ),
    ids=("unknown-action", "wrong-role", "wrong-action-shape"),
)
def test_target_action_and_role_compatibility_is_independently_checked(
    assignment_update, expected_code
):
    context = _context()
    program = _program(context)
    altered = _assignment(program.source_assignments[1], **assignment_update)
    program = _alter(
        program,
        source_assignments=(program.source_assignments[0], altered),
    )

    receipt = CoverageVerifier().verify(context, program)

    assert expected_code in _codes(receipt)
    assert not receipt.executable


def test_action_source_geometry_must_match_its_exact_assignment_target():
    context = _context()
    program = _program(context)
    altered_action = _alter(program.actions[4], source_unit_refs=())
    program = _alter(
        program,
        actions=(*program.actions[:4], altered_action, program.actions[5]),
    )

    receipt = CoverageVerifier().verify(context, program)

    assert "action_source_assignment_mismatch" in _codes(receipt)
    assert not receipt.executable


def test_residual_kind_and_criticality_are_reconstructed_from_context():
    context = _context(residual=True)
    program = _program(context, residual=True)
    false_claim = _assignment(program.source_assignments[1], critical=False)
    program = _alter(
        program,
        source_assignments=(program.source_assignments[0], false_claim),
    )

    receipt = CoverageVerifier().verify(context, program)

    assert "false_residual_criticality" in _codes(receipt)
    assert receipt.critical_residuals[0].source_unit_ref == "unit:subject"
    assert receipt.critical_residuals[0].contribution_kind == "anchor"
    assert not receipt.executable


def test_typed_noncritical_residual_remains_non_executable_only_when_invalid():
    context = _context(residual=True, noncritical=True)
    program = _program(context, residual=True)
    row = _assignment(
        program.source_assignments[1], residual_kind="discourse", critical=False
    )
    program = _alter(program, source_assignments=(program.source_assignments[0], row))

    receipt = CoverageVerifier().verify(context, program)

    assert receipt.executable
    assert receipt.critical_residuals == ()


@pytest.mark.parametrize(
    "field",
    ("coverage_receipt_ref", "proposal_context_ref", "assignments", "revision_pin"),
    ids=("receipt-ref", "context-ref", "assignments", "revision-pin"),
)
def test_receipt_deserializer_rejects_nested_or_outer_tampering(field):
    context = _context()
    receipt = CoverageVerifier().verify(context, _program(context))
    payload = receipt.as_dict()
    if field == "assignments":
        payload[field][0]["target_role_ref"] = "role:tampered"
    elif field == "revision_pin":
        payload[field]["world_revision"] = True
    else:
        payload[field] = f"{payload[field]}:tampered"

    with pytest.raises((TypeError, ValueError)):
        CoverageReceipt.from_dict(payload)


@pytest.mark.parametrize(
    "field",
    (
        "source_unit_refs",
        "program_source_unit_refs",
        "assigned_unit_refs",
        "residual_unit_refs",
        "duplicate_unit_refs",
        "missing_unit_refs",
        "extra_unit_refs",
        "critical_residuals",
        "errors",
        "executable",
    ),
    ids=(
        "context-sources",
        "program-sources",
        "assigned-partition",
        "residual-partition",
        "duplicate-partition",
        "missing-partition",
        "extra-partition",
        "critical-residuals",
        "errors",
        "executable",
    ),
)
def test_every_receipt_field_family_is_identity_protected(field: str) -> None:
    if field == "critical_residuals":
        context = _context(residual=True)
        receipt = CoverageVerifier().verify(context, _program(context, residual=True))
    elif field == "errors":
        context = _context()
        program = _alter(_program(context), proposal_context_ref="context:wrong")
        receipt = CoverageVerifier().verify(context, program)
    else:
        context = _context()
        receipt = CoverageVerifier().verify(context, _program(context))
    payload = receipt.as_dict()
    if field == "source_unit_refs":
        payload[field].reverse()
    elif field == "program_source_unit_refs":
        payload[field].reverse()
    elif field == "assigned_unit_refs":
        payload[field] = payload[field][:-1]
    elif field == "residual_unit_refs":
        payload[field] = ["unit:predicate"]
    elif field == "duplicate_unit_refs":
        payload[field] = ["unit:predicate"]
    elif field == "missing_unit_refs":
        payload[field] = ["unit:predicate"]
    elif field == "extra_unit_refs":
        payload[field] = ["unit:predicate"]
    elif field == "critical_residuals":
        payload[field][0]["reason"] = "tampered reason"
    elif field == "errors":
        payload[field][0]["detail"] = "tampered detail"
    else:
        payload[field] = not payload[field]

    with pytest.raises((TypeError, ValueError)):
        CoverageReceipt.from_dict(payload)


@pytest.mark.parametrize(
    "field",
    (
        "source_unit_refs",
        "program_source_unit_refs",
        "assignments",
        "assigned_unit_refs",
        "residual_unit_refs",
        "duplicate_unit_refs",
        "missing_unit_refs",
        "extra_unit_refs",
        "critical_residuals",
        "errors",
    ),
    ids=(
        "context-sources",
        "program-sources",
        "assignments",
        "assigned-partition",
        "residual-partition",
        "duplicate-partition",
        "missing-partition",
        "extra-partition",
        "critical-residuals",
        "errors",
    ),
)
def test_receipt_wire_requires_canonical_arrays(field: str) -> None:
    context = _context()
    payload = CoverageVerifier().verify(context, _program(context)).as_dict()
    payload[field] = tuple(payload[field])

    with pytest.raises(ValueError, match="JSON array"):
        CoverageReceipt.from_dict(payload)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda payload: payload.pop("program_source_unit_refs"),
        lambda payload: payload.update({"unknown_field": []}),
    ),
    ids=("missing-field", "unknown-field"),
)
def test_receipt_wire_rejects_missing_and_unknown_fields(mutation) -> None:
    context = _context()
    payload = CoverageVerifier().verify(context, _program(context)).as_dict()
    mutation(payload)

    with pytest.raises(ValueError, match="schema exactly"):
        CoverageReceipt.from_dict(payload)

__cemm_test_inventory__ = {'tests/test_coverage_abi2.py::test_action_source_geometry_must_match_its_exact_assignment_target': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-coverage-abi2-test-action-source-geometry-must-match-its-exact-assignment-target',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '6d92332d4e353e2b4cf735e259e1cf908fb89c3e3b7a58203538c796f328d679'},
 'tests/test_coverage_abi2.py::test_conflicting_contribution_and_residual_metadata_fails_closed': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-coverage-abi2-test-conflicting-contribution-and-residual-metadata-fails-closed',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': '0a0420a04e035be7d560d47800f8324fcf5b025fb1f2be3b29f1f85994d161f3'},
 'tests/test_coverage_abi2.py::test_context_owned_residual_ref_does_not_require_a_contribution_slot': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-coverage-abi2-test-context-owned-residual-ref-does-not-require-a-contribution-slot',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': '28f2665fdb9918f7f11785dcaa417a4fb8c864a1e5c94f91e4e245f485540268'},
 'tests/test_coverage_abi2.py::test_contribution_kind_cannot_masquerade_as_predicate': {'activation_phase': 'R1',
                                                                                        'assertion_ref': 'assertion:r1-coverage-abi2-test-contribution-kind-cannot-masquerade-as-predicate',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                        'owner_ref': 'program-verifier',
                                                                                        'source_ast_sha256': '0386bd80939ef428f9d11d8bec42fb45a810c53b0114ee343bc37fa20b3fe43e'},
 'tests/test_coverage_abi2.py::test_coverage_requires_the_exact_proposal_context_owner': {'activation_phase': 'R1',
                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-coverage-requires-the-exact-proposal-context-owner',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                          'owner_ref': 'program-verifier',
                                                                                          'source_ast_sha256': 'e1865da3efa477310739b3029fdbef4cb0bd98b714da8b69027475fca1517263'},
 'tests/test_coverage_abi2.py::test_direct_coverage_receipt_construction_is_blocked': {'activation_phase': 'R1',
                                                                                       'assertion_ref': 'assertion:r1-coverage-abi2-test-direct-coverage-receipt-construction-is-blocked',
                                                                                       'diagnostic_role': 'owner',
                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                       'owner_ref': 'program-verifier',
                                                                                       'source_ast_sha256': '5d62abd66a746ecbd3d5351b065c9b9d962585fa737d44c223db23213dcc387f'},
 'tests/test_coverage_abi2.py::test_error_overflow_is_explicit_and_fails_closed': {'activation_phase': 'R1',
                                                                                   'assertion_ref': 'assertion:r1-coverage-abi2-test-error-overflow-is-explicit-and-fails-closed',
                                                                                   'diagnostic_role': 'owner',
                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                   'owner_ref': 'program-verifier',
                                                                                   'source_ast_sha256': '0017be33f071207b2dacbead46e48ab4c93ed04520349d8999f36061cde866b7'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[assigned-partition]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-assigned-partition',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[context-sources]': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-context-sources',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[critical-residuals]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-critical-residuals',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[duplicate-partition]': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-duplicate-partition',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[errors]': {'activation_phase': 'R1',
                                                                                                'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-errors',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                'owner_ref': 'program-verifier',
                                                                                                'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[executable]': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-executable',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[extra-partition]': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-extra-partition',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[missing-partition]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-missing-partition',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[program-sources]': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-program-sources',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_every_receipt_field_family_is_identity_protected[residual-partition]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-coverage-abi2-test-every-receipt-field-family-is-identity-protected-residual-partition',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': '38c78b3b2ba5b396b28cdde2d4ca7b7d95201ca1e0093ed5b98718efa8f5b77d'},
 'tests/test_coverage_abi2.py::test_exact_context_program_coverage_is_content_addressed_and_round_trips': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-exact-context-program-coverage-is-content-addressed-and-round-trips',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'd1b2a06835f844d9539e2ff3a18d8422fc1ac3918497e25807a50c4a1cd4b1d0'},
 'tests/test_coverage_abi2.py::test_exact_source_and_context_failures_are_retained[duplicate-source]': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-coverage-abi2-test-exact-source-and-context-failures-are-retained-duplicate-source',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': '941e6e977ac7c10b7ccfb19a7aa2c5fdcafeec0289a9c3ce1cb927b04170afae'},
 'tests/test_coverage_abi2.py::test_exact_source_and_context_failures_are_retained[extra-source]': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-coverage-abi2-test-exact-source-and-context-failures-are-retained-extra-source',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '941e6e977ac7c10b7ccfb19a7aa2c5fdcafeec0289a9c3ce1cb927b04170afae'},
 'tests/test_coverage_abi2.py::test_exact_source_and_context_failures_are_retained[missing-source]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-exact-source-and-context-failures-are-retained-missing-source',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': '941e6e977ac7c10b7ccfb19a7aa2c5fdcafeec0289a9c3ce1cb927b04170afae'},
 'tests/test_coverage_abi2.py::test_exact_source_and_context_failures_are_retained[unknown-contribution]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-coverage-abi2-test-exact-source-and-context-failures-are-retained-unknown-contribution',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': '941e6e977ac7c10b7ccfb19a7aa2c5fdcafeec0289a9c3ce1cb927b04170afae'},
 'tests/test_coverage_abi2.py::test_exact_source_and_context_failures_are_retained[wrong-context]': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-coverage-abi2-test-exact-source-and-context-failures-are-retained-wrong-context',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '941e6e977ac7c10b7ccfb19a7aa2c5fdcafeec0289a9c3ce1cb927b04170afae'},
 'tests/test_coverage_abi2.py::test_expression_link_arity_is_checked_against_exact_context_slot': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-coverage-abi2-test-expression-link-arity-is-checked-against-exact-context-slot',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': '087b3d5e41995967368cd439500d88a34c8ded9efe5f6f667af865e568920575'},
 'tests/test_coverage_abi2.py::test_extra_assignment_is_not_a_successful_assignment_partition': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-coverage-abi2-test-extra-assignment-is-not-a-successful-assignment-partition',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': '591f1460207e009ad8220c0d9263a1bf21ff3e8e10a7b9759d2e756c6ce98784'},
 'tests/test_coverage_abi2.py::test_nested_role_requires_parent_proposition_role': {'activation_phase': 'R1',
                                                                                    'assertion_ref': 'assertion:r1-coverage-abi2-test-nested-role-requires-parent-proposition-role',
                                                                                    'diagnostic_role': 'owner',
                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                    'owner_ref': 'program-verifier',
                                                                                    'source_ast_sha256': '20fa471e624f5844f5a5b3b666e0a5b910eaccbfe85f055e67b55dfd7f355765'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[binder]': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-binder',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[connector]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-connector',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[discourse]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-discourse',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[open-variable]': {'activation_phase': 'R1',
                                                                                                              'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-open-variable',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                              'owner_ref': 'program-verifier',
                                                                                                              'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[predicate]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-predicate',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[qualifier]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-qualifier',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[reference]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-reference',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_anchor_contribution_kinds_cannot_masquerade_as_role[scope]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-non-anchor-contribution-kinds-cannot-masquerade-as-role-scope',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': 'fe8f3bc6431fc35023ca71712578cf98e32b38e125519e2550f641f54523b161'},
 'tests/test_coverage_abi2.py::test_non_role_assignment_rejects_irrelevant_target_role': {'activation_phase': 'R1',
                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-non-role-assignment-rejects-irrelevant-target-role',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                          'owner_ref': 'program-verifier',
                                                                                          'source_ast_sha256': '133e3bf0b4f62671e4149aaad5947ab3e2adf36dd5e0d0bf325bfea156b75b11'},
 'tests/test_coverage_abi2.py::test_program_source_order_mismatch_is_retained_and_fails_closed': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-coverage-abi2-test-program-source-order-mismatch-is-retained-and-fails-closed',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '648684f76945f8fcc83955ca01974b693f82d2205e19ff291b72956c6902cf3e'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[assigned-residual-overlap]': {'activation_phase': 'R1',
                                                                                                                        'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-assigned-residual-overlap',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                                        'owner_ref': 'program-verifier',
                                                                                                                        'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[assigned-summary-mismatch]': {'activation_phase': 'R1',
                                                                                                                        'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-assigned-summary-mismatch',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                                        'owner_ref': 'program-verifier',
                                                                                                                        'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[duplicate-partition-ref]': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-duplicate-partition-ref',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                                      'owner_ref': 'program-verifier',
                                                                                                                      'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[duplicate-summary-mismatch]': {'activation_phase': 'R1',
                                                                                                                         'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-duplicate-summary-mismatch',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                                         'owner_ref': 'program-verifier',
                                                                                                                         'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[extra-summary-mismatch]': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-extra-summary-mismatch',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                                     'owner_ref': 'program-verifier',
                                                                                                                     'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[missing-summary-mismatch]': {'activation_phase': 'R1',
                                                                                                                       'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-missing-summary-mismatch',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                                       'owner_ref': 'program-verifier',
                                                                                                                       'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_create_rejects_incoherent_partition_summaries[residual-summary-mismatch]': {'activation_phase': 'R1',
                                                                                                                        'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-create-rejects-incoherent-partition-summaries-residual-summary-mismatch',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                                        'owner_ref': 'program-verifier',
                                                                                                                        'source_ast_sha256': '6553acea5c213520a398e597fb77d328ee8c60d517a88417488c2b5a4b516956'},
 'tests/test_coverage_abi2.py::test_receipt_deserializer_rejects_nested_or_outer_tampering[assignments]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-deserializer-rejects-nested-or-outer-tampering-assignments',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'c055646145d6cc6e243eab67b72ed7fa8bee715c1abf2bdb298e426a83c47e2b'},
 'tests/test_coverage_abi2.py::test_receipt_deserializer_rejects_nested_or_outer_tampering[context-ref]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-deserializer-rejects-nested-or-outer-tampering-context-ref',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'c055646145d6cc6e243eab67b72ed7fa8bee715c1abf2bdb298e426a83c47e2b'},
 'tests/test_coverage_abi2.py::test_receipt_deserializer_rejects_nested_or_outer_tampering[receipt-ref]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-deserializer-rejects-nested-or-outer-tampering-receipt-ref',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'c055646145d6cc6e243eab67b72ed7fa8bee715c1abf2bdb298e426a83c47e2b'},
 'tests/test_coverage_abi2.py::test_receipt_deserializer_rejects_nested_or_outer_tampering[revision-pin]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-deserializer-rejects-nested-or-outer-tampering-revision-pin',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': 'c055646145d6cc6e243eab67b72ed7fa8bee715c1abf2bdb298e426a83c47e2b'},
 'tests/test_coverage_abi2.py::test_receipt_rejects_executable_true_with_retained_failure_evidence': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-rejects-executable-true-with-retained-failure-evidence',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': '466ba0ee200eb1547c40b66843f5c5193f22766e919353fd716a8356714fb3d3'},
 'tests/test_coverage_abi2.py::test_receipt_wire_rejects_missing_and_unknown_fields[missing-field]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-rejects-missing-and-unknown-fields-missing-field',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': '8cfa30584c0d7ae2a1ed02077f731e86b148376441dd246384ca63da710b6642'},
 'tests/test_coverage_abi2.py::test_receipt_wire_rejects_missing_and_unknown_fields[unknown-field]': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-rejects-missing-and-unknown-fields-unknown-field',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': '8cfa30584c0d7ae2a1ed02077f731e86b148376441dd246384ca63da710b6642'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[assigned-partition]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-assigned-partition',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[assignments]': {'activation_phase': 'R1',
                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-assignments',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                           'owner_ref': 'program-verifier',
                                                                                           'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[context-sources]': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-context-sources',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                               'owner_ref': 'program-verifier',
                                                                                               'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[critical-residuals]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-critical-residuals',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[duplicate-partition]': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-duplicate-partition',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[errors]': {'activation_phase': 'R1',
                                                                                      'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-errors',
                                                                                      'diagnostic_role': 'owner',
                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                      'owner_ref': 'program-verifier',
                                                                                      'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[extra-partition]': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-extra-partition',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                               'owner_ref': 'program-verifier',
                                                                                               'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[missing-partition]': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-missing-partition',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[program-sources]': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-program-sources',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                               'owner_ref': 'program-verifier',
                                                                                               'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_receipt_wire_requires_canonical_arrays[residual-partition]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-coverage-abi2-test-receipt-wire-requires-canonical-arrays-residual-partition',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '17fb11f78adbbcde0fbc1f373dccba93b220778d57c4c085cf39355570703ce7'},
 'tests/test_coverage_abi2.py::test_residual_kind_and_criticality_are_reconstructed_from_context': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-coverage-abi2-test-residual-kind-and-criticality-are-reconstructed-from-context',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '7d580f9cb809d8d3139d99ecd91c974dc5cd589e6420465b71e6f83f4a58d89f'},
 'tests/test_coverage_abi2.py::test_select_designation_is_source_neutral': {'activation_phase': 'R1',
                                                                            'assertion_ref': 'assertion:r1-coverage-abi2-test-select-designation-is-source-neutral',
                                                                            'diagnostic_role': 'owner',
                                                                            'introduced_by_task': 'R1-Task-7',
                                                                            'owner_ref': 'program-verifier',
                                                                            'source_ast_sha256': 'f2b28e03c9d41b23ce369d6ee307ab36785f1c90fc25fc21d620ea2dd6cb3726'},
 'tests/test_coverage_abi2.py::test_target_action_and_role_compatibility_is_independently_checked[unknown-action]': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:r1-coverage-abi2-test-target-action-and-role-compatibility-is-independently-checked-unknown-action',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                                     'owner_ref': 'program-verifier',
                                                                                                                     'source_ast_sha256': '8ac0f5c7e61661fdd206c79c402b423eb854cd04fcc8646199283a42e1d0490f'},
 'tests/test_coverage_abi2.py::test_target_action_and_role_compatibility_is_independently_checked[wrong-action-shape]': {'activation_phase': 'R1',
                                                                                                                         'assertion_ref': 'assertion:r1-coverage-abi2-test-target-action-and-role-compatibility-is-independently-checked-wrong-action-shape',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                                         'owner_ref': 'program-verifier',
                                                                                                                         'source_ast_sha256': '8ac0f5c7e61661fdd206c79c402b423eb854cd04fcc8646199283a42e1d0490f'},
 'tests/test_coverage_abi2.py::test_target_action_and_role_compatibility_is_independently_checked[wrong-role]': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-coverage-abi2-test-target-action-and-role-compatibility-is-independently-checked-wrong-role',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                 'source_ast_sha256': '8ac0f5c7e61661fdd206c79c402b423eb854cd04fcc8646199283a42e1d0490f'},
 'tests/test_coverage_abi2.py::test_transition_requires_exact_state_application_source': {'activation_phase': 'R1',
                                                                                          'assertion_ref': 'assertion:r1-coverage-abi2-test-transition-requires-exact-state-application-source',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                          'owner_ref': 'program-verifier',
                                                                                          'source_ast_sha256': '19470b8bc6c900a03dc7df7847940cfd6e47fe6111d2ec6ec070ca94946a9286'},
 'tests/test_coverage_abi2.py::test_typed_noncritical_residual_remains_non_executable_only_when_invalid': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-coverage-abi2-test-typed-noncritical-residual-remains-non-executable-only-when-invalid',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': '60553d34e65b34d8a1ce716e6d0d70644700f2175eb146a93d7b960b54738937'},
 'tests/test_coverage_abi2.py::test_variable_slot_role_must_belong_to_its_exact_body_frame': {'activation_phase': 'R1',
                                                                                              'assertion_ref': 'assertion:r1-coverage-abi2-test-variable-slot-role-must-belong-to-its-exact-body-frame',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                              'owner_ref': 'program-verifier',
                                                                                              'source_ast_sha256': '1e991c413740ed34688494e1a0386f4d725ec20a06d836204c36220f8d5b1312'}}
