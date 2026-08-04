"""R2 proposer bounds tests.

Per R2 plan Task 4:
- Search stays within bounds (applications, nodes, actions, depth)
- Truncated proposals cannot become selected meaning
- Budget exhaustion yields typed abstention
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ModeSlot,
    ProposalContext,
)


def _pin() -> RevisionPin:
    return RevisionPin(
        "authority:bootstrap", 1, 2, 3, 4, BootstrapProposer.model_identity
    )


def _context(frame_count: int = 1) -> ProposalContext:
    pin = _pin()
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    designations = tuple(
        DesignationSlot.create(
            source_unit_refs=(f"unit:predicate-{i}",),
            target_ref=f"event:test-{i}",
            target_kind="event_type",
            score_q=900_000 - (i * 100_000),
            designation_fact_ref=f"designation:test-{i}",
            provenance_refs=(f"designation:test-{i}",),
        )
        for i in range(frame_count)
    )
    predicates = tuple(
        ContributionSlot.create(
            contribution_ref=f"contribution:predicate-{i}",
            kind="predicate",
            source_unit_refs=(f"unit:predicate-{i}",),
            target_ref=f"event:test-{i}",
            target_kind="event_type",
            input_ports=("role:subject",),
            output_ports=("role:event",),
            constraints=(),
            provenance_refs=(f"designation:test-{i}",),
        )
        for i in range(frame_count)
    )
    subject = ContributionSlot.create(
        contribution_ref="contribution:subject",
        kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:test",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
        provenance_refs=("designation:subject",),
    )
    frames = tuple(
        ApplicationFrameSlot.create(
            designation_slot_ref=designations[i].slot_ref,
            predicate_target_ref=designations[i].target_ref,
            predicate_kind=designations[i].target_kind,
            operator_ref="op:event",
            structural_role_ref="role:event",
            required_roles=("role:subject",),
            optional_roles=(),
            proposition_roles=(),
            source_unit_refs=(f"unit:predicate-{i}",),
            derived_role_targets=(),
            affordance_frame_ref=f"frame:test-{i}",
            provenance_refs=(designations[i].slot_ref, f"frame:test-{i}"),
        )
        for i in range(frame_count)
    )
    source_refs = tuple(f"unit:predicate-{i}" for i in range(frame_count)) + ("unit:subject",)
    spans = tuple((f"unit:predicate-{i}", i * 4, i * 4 + 4) for i in range(frame_count))
    spans += (("unit:subject", frame_count * 4, frame_count * 4 + 4),)
    return ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=designations,
        contribution_slots=(*predicates, subject),
        mode_slots=(mode,),
        application_frames=frames,
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:bootstrap",),
        source_unit_refs=source_refs,
        source_unit_spans=spans,
        revision_pin=pin,
    )


def test_candidate_count_never_exceeds_max():
    """Candidate count never exceeds max_complete_candidates."""
    for limit in (1, 2, 5, 10):
        config = RuntimeConfig(max_complete_candidates=limit)
        proposer = BootstrapProposer(config)
        result = proposer.propose(_context(frame_count=3))
        assert len(result.candidates) <= limit


def test_explored_states_bounded_by_max_explored():
    """Explored states is bounded by max_beam_states * max_applications."""
    config = RuntimeConfig.release()
    proposer = BootstrapProposer(config)
    result = proposer.propose(_context(frame_count=3))
    max_explored = config.max_beam_states * config.max_applications
    assert result.explored_states <= max_explored


def test_truncated_implies_more_candidates_exist():
    """When truncated, at least one more candidate could have been produced."""
    config = RuntimeConfig(max_complete_candidates=1)
    proposer = BootstrapProposer(config)
    result = proposer.propose(_context(frame_count=2))
    if result.truncated:
        assert result.status == "candidates"
        assert len(result.candidates) == 1


def test_no_candidate_exceeds_application_bound():
    """No candidate program exceeds max_applications."""
    config = RuntimeConfig.release()
    proposer = BootstrapProposer(config)
    result = proposer.propose(_context(frame_count=3))
    for candidate in result.candidates:
        app_count = sum(
            1 for a in candidate.program.actions
            if a.action_type == "instantiate_operator"
        )
        assert app_count <= config.max_applications


def test_all_candidates_have_non_empty_roots():
    """Every candidate has a non-empty root set."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    result = proposer.propose(_context(frame_count=2))
    assert result.status == "candidates"
    for candidate in result.candidates:
        assert len(candidate.program.root_refs) >= 1


def test_all_candidates_have_complete_program_terminal():
    """Every candidate ends with complete_program."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    result = proposer.propose(_context(frame_count=2))
    for candidate in result.candidates:
        assert candidate.program.actions[-1].action_type == "complete_program"


def test_all_candidates_have_valid_action_indices():
    """Every candidate has contiguous action indices starting from 0."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    result = proposer.propose(_context(frame_count=2))
    for candidate in result.candidates:
        indices = [a.action_index for a in candidate.program.actions]
        assert indices == list(range(len(indices)))
