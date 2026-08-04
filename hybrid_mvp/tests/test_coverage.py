"""Tests for the exact coverage ABI.

``CoverageVerifier`` proves the program already contains exactly one
assignment per source unit, valid contribution-to-port binding, explicit typed
residuals, and correct criticality.  It never repairs or synthesizes an
assignment.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from cemm_authoritative_hybrid.coverage import (
    CoverageReceipt,
    CriticalResidual,
    CoverageVerifier,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SourceAssignment,
    SemanticSwitchProgram,
)
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ModeSlot,
    ProposalContext,
    ResidualEvidence,
)


# ---------------------------------------------------------------------------
# Complete coverage
# ---------------------------------------------------------------------------


def test_every_source_unit_is_consumed_once_or_one_residual(
    coverage_verifier, proposal_context, case
):
    receipt = coverage_verifier.verify(proposal_context, case.program)
    assert receipt.duplicate_unit_refs == ()
    assert receipt.missing_unit_refs == ()
    assert set(receipt.assigned_unit_refs).isdisjoint(receipt.residual_unit_refs)


def test_complete_coverage_is_executable(coverage_verifier, proposal_context, case):
    receipt = coverage_verifier.verify(proposal_context, case.program)
    assert receipt.executable
    assert receipt.critical_residuals == ()


def test_coverage_receipt_has_stable_hash(coverage_verifier, proposal_context, case):
    a = coverage_verifier.verify(proposal_context, case.program)
    b = coverage_verifier.verify(proposal_context, case.program)
    assert a.coverage_hash == b.coverage_hash


# ---------------------------------------------------------------------------
# Missing / duplicate program assignments are rejected
# ---------------------------------------------------------------------------


def test_missing_or_duplicate_program_assignment_is_rejected(
    coverage_verifier, proposal_context, valid_program
):
    assert (
        coverage_verifier.verify(
            proposal_context, with_assignment_removed(valid_program)
        ).errors[0].code
        == "missing_source_assignment"
    )
    assert (
        coverage_verifier.verify(
            proposal_context, with_assignment_duplicated(valid_program)
        ).errors[0].code
        == "duplicate_source_assignment"
    )


def test_missing_assignment_populates_missing_unit_refs(
    coverage_verifier, proposal_context, valid_program
):
    receipt = coverage_verifier.verify(
        proposal_context, with_assignment_removed(valid_program)
    )
    assert len(receipt.missing_unit_refs) == 1
    assert not receipt.executable


def test_duplicate_assignment_populates_duplicate_unit_refs(
    coverage_verifier, proposal_context, valid_program
):
    receipt = coverage_verifier.verify(
        proposal_context, with_assignment_duplicated(valid_program)
    )
    assert len(receipt.duplicate_unit_refs) == 1
    assert not receipt.executable


def test_valid_program_has_no_assignment_errors(
    coverage_verifier, proposal_context, valid_program
):
    receipt = coverage_verifier.verify(proposal_context, valid_program)
    assert receipt.errors == ()
    assert receipt.missing_unit_refs == ()
    assert receipt.duplicate_unit_refs == ()


# ---------------------------------------------------------------------------
# Critical residuals reject execution
# ---------------------------------------------------------------------------


def test_critical_residual_rejects_execution(coverage_verifier, negated_effect_case):
    context, program = _critical_scope_case(negated_effect_case[0])
    receipt = coverage_verifier.verify(context, program)
    assert not receipt.executable
    assert receipt.critical_residuals[0].contribution_kind == "scope"


def test_critical_residual_records_source_unit(coverage_verifier, negated_effect_case):
    context, program = _critical_scope_case(negated_effect_case[0])
    receipt = coverage_verifier.verify(context, program)
    assert receipt.critical_residuals[0].source_unit_ref in {
        u.unit_ref for u in negated_effect_case[0].units
    }


def test_noncritical_residual_does_not_reject_execution(
    coverage_verifier, proposal_context, case
):
    receipt = coverage_verifier.verify(proposal_context, case.program)
    # Any residuals present must be noncritical for an executable program.
    for residual in receipt.residual_unit_refs:
        assert residual not in {cr.source_unit_ref for cr in receipt.critical_residuals}
    assert receipt.executable


# ---------------------------------------------------------------------------
# CoverageVerifier never repairs or synthesizes
# ---------------------------------------------------------------------------


def test_verifier_does_not_synthesize_assignments(
    coverage_verifier, proposal_context, valid_program
):
    """The verifier must not add assignments; it only validates the program."""
    receipt = coverage_verifier.verify(proposal_context, valid_program)
    # The program's own assignments are unchanged; the verifier reports gaps.
    assert receipt.missing_unit_refs == ()
    assert set(receipt.assigned_unit_refs) == {
        row.source_unit_ref
        for row in valid_program.source_assignments
        if row.assignment_kind != "residual"
    }


def test_verify_program_checks_internal_consistency(
    coverage_verifier, proposal_context, valid_program
):
    receipt = coverage_verifier.verify(proposal_context, valid_program)
    assert isinstance(receipt, CoverageReceipt)
    assert receipt.errors == ()


# ---------------------------------------------------------------------------
# Helpers — return modified copies of a program
# ---------------------------------------------------------------------------


def _alter_program(program: SemanticSwitchProgram, **updates) -> SemanticSwitchProgram:
    """Return a copy of ``program`` with the given fields replaced.

    ``SemanticSwitchProgram`` uses a content-addressed ``__init__`` guard, so
    ``dataclasses.replace`` cannot be used.  This helper bypasses the guard to
    forge deliberately modified copies for negative tests.
    """
    result = object.__new__(type(program))
    for field in fields(program):
        object.__setattr__(
            result, field.name, updates.get(field.name, getattr(program, field.name))
        )
    return result


def with_assignment_removed(program: SemanticSwitchProgram) -> SemanticSwitchProgram:
    """Return a copy of ``program`` with one source assignment removed."""
    if not program.source_assignments:
        return program
    return _alter_program(program, source_assignments=program.source_assignments[:-1])


def with_assignment_duplicated(
    program: SemanticSwitchProgram,
) -> SemanticSwitchProgram:
    """Return a copy of ``program`` with the first assignment duplicated."""
    if not program.source_assignments:
        return program
    first = program.source_assignments[0]
    return _alter_program(
        program, source_assignments=(first, *program.source_assignments)
    )


def _critical_scope_case(lattice):
    """Build a ``(ProposalContext, SemanticSwitchProgram)`` pair where one
    lattice content unit is retained as a critical scope residual.

    The context carries a ``scope`` ``ResidualEvidence`` for the first
    non-whitespace lattice unit, and the program carries a matching residual
    assignment.  Coverage must reject execution because ``scope`` is always
    critical.
    """
    scope_unit = next(u.unit_ref for u in lattice.units if u.source_text.strip())
    pin = RevisionPin(
        authority_generation="authority:test",
        world_revision=1,
        session_revision=2,
        episode_revision=3,
        effect_revision=4,
        model_identity="model:test",
    )

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
        kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:one",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
        provenance_refs=("designation:one",),
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
    residual = ResidualEvidence.create(
        source_unit_ref=scope_unit,
        contribution_kind="scope",
        critical=True,
        reason="unresolved scope evidence",
    )
    sources = ("unit:predicate", "unit:subject", scope_unit)
    context = ProposalContext.create(
        orientation_ref="orientation:test",
        evidence_packet_ref="evidence:test",
        form_lattice_ref="lattice:test",
        grounding_ref="grounding:test",
        designation_slots=(designation,),
        contribution_slots=(predicate, subject),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(residual,),
        context_refs=("turn:test",),
        source_unit_refs=sources,
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:subject", 4, 8),
            (scope_unit, 8, 9),
        ),
        revision_pin=pin,
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
            arguments=("application:main", context.application_frames[0].slot_ref),
            source_unit_refs=("unit:predicate",),
        ),
        ProgramAction.create(
            action_index=4,
            action_type="bind_role",
            arguments=(
                "application:main",
                "role:subject",
                context.contribution_slots[1].slot_ref,
            ),
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
            assignment_kind="role",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=False,
        ),
        SourceAssignment.create(
            source_unit_ref=scope_unit,
            contribution_slot_ref=residual.residual_ref,
            assignment_kind="residual",
            target_action_ref=None,
            target_role_ref=None,
            residual_kind="scope",
            critical=True,
        ),
    )
    program = SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=sources,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )
    return context, program
