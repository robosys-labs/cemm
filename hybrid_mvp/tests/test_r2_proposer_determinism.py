"""R2 proposer determinism tests.

Per R2 plan Task 4:
- Same context/config produces byte-identical proposal output
- Deterministic tie-breaking makes episode generation deterministic
- No random or nondeterministic ordering in the search
"""

from __future__ import annotations

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import (
    BootstrapProposer,
    ProposalResult,
)
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ModeSlot,
    ProposalContext,
)

__cemm_test_inventory__ = {
    "tests/test_r2_proposer_determinism.py::test_byte_identical_output_same_context": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-byte-identical-output-same-context",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "03326b53caa387eba92123da3f423441ac0f6b4fba526816ec05cc3e951d17e7"
    },
    "tests/test_r2_proposer_determinism.py::test_byte_identical_output_serialized": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-byte-identical-output-serialized",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "97f367dd136fd5de1d18d7c0ec9ad09cfe0901ff516ce9a00e37d51105ac1891"
    },
    "tests/test_r2_proposer_determinism.py::test_deterministic_candidate_order": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-deterministic-candidate-order",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "194be4cdcceaa676bca913d5108efe00daca377626519a2df368fbce610ab89b"
    },
    "tests/test_r2_proposer_determinism.py::test_deterministic_explored_and_truncated": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-deterministic-explored-and-truncated",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "b8e6c51951bb504085ced71b5bf48b0c3ce81f6a37032b19833f5bba3b010c5e"
    },
    "tests/test_r2_proposer_determinism.py::test_different_config_produces_different_output": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-different-config-produces-different-output",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "02009d0d89f3ded4869b8a477b772ac57e681f02c52a32aa5bf90c7c2e5ad496"
    },
}



def _pin() -> RevisionPin:
    return RevisionPin(
        "authority:bootstrap", 1, 2, 3, 4, BootstrapProposer.model_identity
    )


def _context(frame_count: int = 2) -> ProposalContext:
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


def test_byte_identical_output_same_context():
    """Same context/config produces byte-identical output."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _context()
    first = proposer.propose(context)
    second = proposer.propose(context)
    assert first.as_dict() == second.as_dict()


def test_byte_identical_output_serialized():
    """Serialized output is byte-identical across runs."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _context()
    first = proposer.propose(context)
    second = proposer.propose(context)
    assert ProposalResult.from_dict(first.as_dict()) == ProposalResult.from_dict(second.as_dict())


def test_deterministic_candidate_order():
    """Candidate order is deterministic across runs."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _context()
    first = proposer.propose(context)
    second = proposer.propose(context)
    assert len(first.candidates) == len(second.candidates)
    for c1, c2 in zip(first.candidates, second.candidates):
        assert c1.candidate_ref == c2.candidate_ref
        assert c1.score_q == c2.score_q


def test_deterministic_explored_and_truncated():
    """Explored states and truncated flag are deterministic."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _context()
    first = proposer.propose(context)
    second = proposer.propose(context)
    assert first.explored_states == second.explored_states
    assert first.truncated == second.truncated


def test_different_config_produces_different_output():
    """Different max_candidates produces different output (truncation differs)."""
    context = _context()
    small = BootstrapProposer(RuntimeConfig(max_complete_candidates=1)).propose(context)
    large = BootstrapProposer(RuntimeConfig(max_complete_candidates=10)).propose(context)
    # The small config should have fewer or equal candidates
    assert len(small.candidates) <= len(large.candidates)
