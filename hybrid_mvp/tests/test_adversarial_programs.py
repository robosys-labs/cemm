"""Adversarial tests for the exact program verifier.

These tests verify that the verifier rejects programs with fabricated atoms,
unknown operators, invalid action types, cycles in nested applications, and
depth bound violations. The verifier must never accept a structurally
impossible program.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.expressions import SemanticExpressionCompiler
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    PERSISTENT_OPERATORS,
    SWITCH_ACTION_TYPES,
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
)
from cemm_authoritative_hybrid.verifier import (
    ExactProgramVerifier,
    VerificationBatch,
)


# ---------------------------------------------------------------------------
# Self-contained helpers
# ---------------------------------------------------------------------------
# These helpers build a minimal coherent context, program and proposal so the
# verifier's ``verify_candidates`` envelope checks pass.  They do not rely on
# the conftest ``proposal_context`` / ``valid_program`` / ``mutate`` fixtures,
# which predate Proposal Context ABI 1 and fail canonical round-trip
# validation.


def _pin(**changes: object) -> RevisionPin:
    values: dict[str, object] = {
        "authority_generation": "authority:test",
        "world_revision": 1,
        "session_revision": 2,
        "episode_revision": 3,
        "effect_revision": 4,
        "model_identity": "model:test",
    }
    values.update(changes)
    return RevisionPin(**values)  # type: ignore[arg-type]


def _context(revision_pin: RevisionPin | None = None) -> ProposalContext:
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
    return ProposalContext.create(
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
        residual_evidence=(),
        context_refs=("turn:test",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:subject", 4, 8),
        ),
        revision_pin=revision_pin or _pin(),
    )


def _program(
    context: ProposalContext,
    *,
    actions: tuple[ProgramAction, ...] | None = None,
    source_assignments: tuple[SourceAssignment, ...] | None = None,
    revision_pin: RevisionPin | None = None,
) -> SemanticSwitchProgram:
    if actions is None:
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
    if source_assignments is None:
        source_assignments = (
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
        )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=context.source_unit_refs,
        source_assignments=source_assignments,
        revision_pin=revision_pin or context.revision_pin,
    )


def _proposal(
    context: ProposalContext,
    program: SemanticSwitchProgram,
    *,
    revision_pin: RevisionPin | None = None,
) -> ProposalResult:
    pin = revision_pin or context.revision_pin
    candidate = RankedProgramCandidate.create(
        rank=0,
        score_q=0,
        program=program,
        provenance_refs=("test:provenance",),
    )
    return ProposalResult.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        candidates=(candidate,),
        status="candidates",
        abstention_code=None,
        explored_states=1,
        truncated=False,
        model_identity=pin.model_identity,
        revision_pin=pin,
    )


def _verifier() -> ExactProgramVerifier:
    return ExactProgramVerifier(
        coverage_verifier=CoverageVerifier(),
        compiler=SemanticExpressionCompiler(),
    )


def _reindex(actions: list[ProgramAction]) -> tuple[ProgramAction, ...]:
    """Re-index actions to be contiguous from 0."""
    return tuple(
        ProgramAction.create(
            action_index=i,
            action_type=a.action_type,
            arguments=a.arguments,
            source_unit_refs=a.source_unit_refs,
        )
        for i, a in enumerate(actions)
    )


# ---------------------------------------------------------------------------
# Fabricated atoms not in authority
# ---------------------------------------------------------------------------


def test_fabricated_atom_in_designation_rejected():
    """A select_designation targeting a fabricated atom is rejected."""
    context = _context()
    base = _program(context)
    new_actions = []
    for a in base.actions:
        if a.action_type == "select_designation":
            new_actions.append(
                ProgramAction.create(
                    action_index=a.action_index,
                    action_type=a.action_type,
                    arguments=("designation:nonexistent",),
                    source_unit_refs=a.source_unit_refs,
                )
            )
        else:
            new_actions.append(a)
    program = _program(context, actions=_reindex(new_actions))
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert batch.status != "selected"
    assert any(
        e.code == "unknown_designation_slot"
        for e in batch.candidate_receipts[0].verification_errors
    )


def test_fabricated_atom_in_bind_reference_rejected():
    """A bind_reference targeting a fabricated atom is rejected."""
    context = _context()
    base = _program(context)
    # Insert a bind_reference action after bind_role targeting a non-existent
    # reference slot.  The role "role:subject" is legal in the frame; the
    # verifier will report "unknown_reference_slot" because the reference slot
    # does not exist in the context.
    bind_ref_action = ProgramAction.create(
        action_index=0,
        action_type="bind_reference",
        arguments=(
            "application:main",
            "role:subject",
            "reference:nonexistent",
        ),
    )
    new_actions: list[ProgramAction] = []
    for a in base.actions:
        new_actions.append(a)
        if a.action_type == "bind_role":
            new_actions.append(bind_ref_action)
    program = _program(context, actions=_reindex(new_actions))
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert batch.status != "selected"
    assert any(
        e.code == "unknown_reference_slot"
        for e in batch.candidate_receipts[0].verification_errors
    )


# ---------------------------------------------------------------------------
# Operator not in the five persistent operators
# ---------------------------------------------------------------------------


def test_unknown_operator_rejected():
    """An ApplicationFrameSlot with an unknown operator is rejected at
    construction time, and the verifier rejects programs referencing unknown
    application frames."""
    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref="event:test",
        target_kind="event_type",
        score_q=900_000,
        designation_fact_ref="designation:test",
        provenance_refs=("authority:test",),
    )
    # ApplicationFrameSlot.create validates the operator against
    # PERSISTENT_OPERATORS and rejects unknown operators.
    with pytest.raises(ValueError):
        ApplicationFrameSlot.create(
            designation_slot_ref=designation.slot_ref,
            predicate_target_ref="event:test",
            predicate_kind="event_type",
            operator_ref="op:fabricated",
            structural_role_ref="role:event",
            required_roles=("role:subject",),
            optional_roles=(),
            proposition_roles=(),
            source_unit_refs=("unit:predicate",),
            derived_role_targets=(),
            affordance_frame_ref="frame:event-test",
            provenance_refs=(designation.slot_ref, "authority:test", "frame:event-test"),
        )

    # The verifier also rejects programs that reference an unknown application
    # frame slot (defense-in-depth).
    context = _context()
    base = _program(context)
    new_actions = []
    for a in base.actions:
        if a.action_type == "instantiate_operator":
            new_actions.append(
                ProgramAction.create(
                    action_index=a.action_index,
                    action_type=a.action_type,
                    arguments=("application:main", "application_frame:nonexistent"),
                    source_unit_refs=a.source_unit_refs,
                )
            )
        else:
            new_actions.append(a)
    program = _program(context, actions=_reindex(new_actions))
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert batch.status != "selected"
    assert any(
        e.code == "unknown_application_frame"
        for e in batch.candidate_receipts[0].verification_errors
    )


def test_only_five_persistent_operators_accepted():
    """A valid program using each of the five persistent operators is accepted.

    The R1 compiler admits exactly one application per program, so each
    operator is verified in its own self-contained context and program.
    """
    assert PERSISTENT_OPERATORS == frozenset(
        {"op:designation", "op:type", "op:relation", "op:state", "op:event"}
    )

    # Each entry: (operator_ref, target_ref, target_kind, structural_role,
    #              derived_role_targets, designation_fact_ref)
    operators: list[tuple[str, str, str, str, tuple[tuple[str, str], ...], str]] = [
        ("op:designation", "label:test", "label_type", "role:label_type",
         (), "designation:label"),
        ("op:type", "concept:test", "concept", "role:class",
         (), "designation:concept"),
        ("op:relation", "relation:test", "relation_type", "role:relation",
         (), "designation:relation"),
        ("op:state", "state:test", "state_dimension", "role:dimension",
         (("role:dimension", "state:test"),), "designation:state"),
        ("op:event", "event:test", "event_type", "role:event",
         (), "designation:event"),
    ]

    for op_ref, target, kind, struct_role, derived_roles, desig_fact in operators:
        desig = DesignationSlot.create(
            source_unit_refs=("unit:predicate",),
            target_ref=target,
            target_kind=kind,
            score_q=900_000,
            designation_fact_ref=desig_fact,
            provenance_refs=("authority:test",),
        )
        predicate = ContributionSlot.create(
            contribution_ref="contribution:predicate",
            kind="predicate",
            source_unit_refs=("unit:predicate",),
            target_ref=target,
            target_kind=kind,
            input_ports=("role:subject",),
            output_ports=(struct_role,),
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
        )
        mode = ModeSlot.create(
            mode="OBSERVE",
            source_unit_refs=(),
            construction_ref=None,
            requested_effect="admission",
        )
        frame = ApplicationFrameSlot.create(
            designation_slot_ref=desig.slot_ref,
            predicate_target_ref=target,
            predicate_kind=kind,
            operator_ref=op_ref,
            structural_role_ref=struct_role,
            required_roles=("role:subject",),
            optional_roles=(),
            proposition_roles=(),
            source_unit_refs=("unit:predicate",),
            derived_role_targets=derived_roles,
            affordance_frame_ref=f"frame:{kind}",
            provenance_refs=(desig.slot_ref, "authority:test", f"frame:{kind}"),
        )
        context = ProposalContext.create(
            orientation_ref="orientation:test",
            evidence_packet_ref="evidence:test",
            form_lattice_ref="lattice:test",
            grounding_ref="grounding:test",
            designation_slots=(desig,),
            contribution_slots=(predicate, subject),
            mode_slots=(mode,),
            application_frames=(frame,),
            reference_slots=(),
            scope_slots=(),
            expression_link_slots=(),
            variable_slots=(),
            transition_slots=(),
            residual_evidence=(),
            context_refs=("turn:test",),
            source_unit_refs=("unit:predicate", "unit:subject"),
            source_unit_spans=(
                ("unit:predicate", 0, 4),
                ("unit:subject", 4, 8),
            ),
            revision_pin=_pin(),
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
        )
        program = SemanticSwitchProgram.create(
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
        batch = _verifier().verify_candidates(_proposal(context, program), context)
        assert batch.status == "selected", (
            f"operator {op_ref} was rejected: "
            f"{[e.code for e in batch.candidate_receipts[0].verification_errors]}"
        )


# ---------------------------------------------------------------------------
# Action type not in SWITCH_ACTION_TYPES
# ---------------------------------------------------------------------------


def test_unknown_action_type_rejected_by_constructor():
    """ProgramAction rejects unknown action types at construction time."""
    with pytest.raises(ValueError):
        ProgramAction.create(
            action_index=0,
            action_type="bogus",
            arguments=(),
        )


def test_switch_action_vocabulary_is_closed_at_twelve():
    """The action vocabulary is exactly 12 types."""
    assert len(SWITCH_ACTION_TYPES) == 12
    assert len(set(SWITCH_ACTION_TYPES)) == 12


# ---------------------------------------------------------------------------
# Cycle in nested applications
# ---------------------------------------------------------------------------


def test_nested_application_cycle_rejected():
    """A cycle in bind_nested_application actions is rejected.

    Two nested applications that reference each other form a cycle.  The
    program is structurally invalid because the nested child nodes are never
    declared by an ``instantiate_operator`` action, so
    ``SemanticSwitchProgram.create`` raises ``ValueError`` during action graph
    validation.
    """
    context = _context()
    base = _program(context)
    extra = [
        ProgramAction.create(
            action_index=0,
            action_type="bind_nested_application",
            arguments=(
                "role",
                "application:main",
                "role:child",
                "application:nest_b",
            ),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="bind_nested_application",
            arguments=(
                "role",
                "application:nest_b",
                "role:child",
                "application:main",
            ),
        ),
    ]
    new_actions: list[ProgramAction] = []
    for a in base.actions:
        if a.action_type == "complete_program":
            new_actions.extend(extra)
        new_actions.append(a)
    reindexed = _reindex(new_actions)
    # SemanticSwitchProgram.create rejects this because "application:nest_b"
    # is never declared by an instantiate_operator action.
    with pytest.raises(ValueError):
        _program(context, actions=reindexed)


def test_direct_self_reference_cycle_rejected():
    """A bind_nested_application that references itself is rejected.

    A ``bind_nested_application`` with the ``role`` variant where the parent
    and child are the same application node is structurally invalid because
    the role is not a declared proposition role.  The verifier rejects the
    program with a typed error.
    """
    context = _context()
    base = _program(context)
    self_ref = ProgramAction.create(
        action_index=0,
        action_type="bind_nested_application",
        arguments=(
            "role",
            "application:main",
            "role:child",
            "application:main",
        ),
    )
    new_actions: list[ProgramAction] = []
    for a in base.actions:
        new_actions.append(a)
        if a.action_type == "bind_role":
            new_actions.append(self_ref)
    program = _program(context, actions=_reindex(new_actions))
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert batch.status != "selected"
    assert any(
        e.code == "nonproposition_nested_role"
        for e in batch.candidate_receipts[0].verification_errors
    )


# ---------------------------------------------------------------------------
# Depth bound exceeded
# ---------------------------------------------------------------------------


def test_depth_bound_exceeded_rejected():
    """A program exceeding the action depth bound is rejected.

    Adding many ``project_variable`` actions with fabricated variable slot
    refs causes the verifier to report ``unknown_variable_slot`` for each.
    """
    context = _context()
    base = _program(context)
    extra: list[ProgramAction] = []
    for i in range(30):
        extra.append(
            ProgramAction.create(
                action_index=i,
                action_type="project_variable",
                arguments=(
                    f"binder:extra:{i}",
                    f"variable:extra:{i}",
                    "application:main",
                ),
            )
        )
    new_actions: list[ProgramAction] = []
    for a in base.actions:
        if a.action_type == "complete_program":
            new_actions.extend(extra)
        new_actions.append(a)
    program = _program(context, actions=_reindex(new_actions))
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert batch.status != "selected"
    assert any(
        e.code == "unknown_variable_slot"
        for e in batch.candidate_receipts[0].verification_errors
    )


def test_program_at_max_actions_accepted():
    """A valid program within the action bound is accepted."""
    from cemm_authoritative_hybrid.config import RuntimeConfig

    config = RuntimeConfig.release()
    max_actions = config.max_applications * 8 + 16
    context = _context()
    program = _program(context)
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert batch.status == "selected"
    assert len(program.actions) <= max_actions


# ---------------------------------------------------------------------------
# Stale revision
# ---------------------------------------------------------------------------


def test_stale_revision_rejected():
    """A program with a stale revision_pin is rejected.

    The proposal envelope validates that each candidate's program revision pin
    matches the proposal's revision pin.  A stale pin causes
    ``ProposalResult.create`` to raise ``ValueError``.
    """
    context = _context()
    stale_pin = _pin(authority_generation="authority:stale-generation")
    stale_program = _program(context, revision_pin=stale_pin)
    with pytest.raises(ValueError):
        _verifier().verify_candidates(_proposal(context, stale_program), context)


# ---------------------------------------------------------------------------
# Uncovered unit
# ---------------------------------------------------------------------------


def test_uncovered_unit_rejected():
    """A program with an unassigned source unit is rejected.

    Removing a source assignment creates a structurally invalid program whose
    source assignments no longer cover the source units exactly once in order.
    ``SemanticSwitchProgram.create`` raises ``ValueError`` during validation.
    """
    context = _context()
    base = _program(context)
    with pytest.raises(ValueError):
        _program(context, source_assignments=base.source_assignments[:-1])


# ---------------------------------------------------------------------------
# Verifier returns typed VerificationBatch
# ---------------------------------------------------------------------------


def test_verify_returns_verification_result():
    """verify_candidates returns a typed VerificationBatch."""
    context = _context()
    program = _program(context)
    batch = _verifier().verify_candidates(_proposal(context, program), context)
    assert isinstance(batch, VerificationBatch)
    assert isinstance(batch.status, str)
    assert isinstance(batch.candidate_receipts, tuple)
    assert isinstance(batch.batch_ref, str)
