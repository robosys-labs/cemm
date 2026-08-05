"""Focused canonical BootstrapProposer / ProposalOwner cutover tests."""

from __future__ import annotations

import inspect

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import SemanticSwitchProgram
from cemm_authoritative_hybrid.proposal import (
    BootstrapProposer,
    ProposalOwner,
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
    ResidualEvidence,
)


def _context(
    *,
    frame_count: int = 1,
    critical_residual: bool = False,
    subject_kind: str = "anchor",
    include_reference: bool = False,
    unbound_qualifier: bool = False,
) -> ProposalContext:
    pin = RevisionPin(
        "authority:bootstrap",
        1,
        2,
        3,
        4,
        BootstrapProposer.model_identity,
    )
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    designations = tuple(
        DesignationSlot.create(
            source_unit_refs=("unit:predicate",),
            target_ref=f"event:test-{index}",
            target_kind="event_type",
            score_q=900_000 - (index * 100_000),
            designation_fact_ref=f"designation:test-{index}",
            provenance_refs=(f"designation:test-{index}",),
        )
        for index in range(frame_count)
    )
    predicates = tuple(
        ContributionSlot.create(
            contribution_ref=f"contribution:predicate-{index}",
            kind="predicate",
            source_unit_refs=("unit:predicate",),
            target_ref=f"event:test-{index}",
            target_kind="event_type",
            input_ports=("role:subject",),
            output_ports=("role:event",),
            constraints=(),
            provenance_refs=(f"designation:test-{index}",),
        )
        for index in range(frame_count)
    )
    subject = ContributionSlot.create(
        contribution_ref="contribution:subject",
        kind=subject_kind,
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
            affordance_frame_ref=f"frame:test-{index}",
            provenance_refs=(designation.slot_ref, f"frame:test-{index}"),
        )
        for index, designation in enumerate(designations)
    )
    residuals = ()
    contributions = (*predicates, subject)
    if critical_residual:
        residuals = (
            ResidualEvidence.create(
                source_unit_ref="unit:subject",
                contribution_kind="anchor",
                critical=True,
                reason="unresolved open-class evidence",
            ),
        )
        contributions = predicates
    source_refs = ("unit:predicate", "unit:subject")
    source_spans = (("unit:predicate", 0, 4), ("unit:subject", 4, 8))
    if unbound_qualifier:
        qualifier = ContributionSlot.create(
            contribution_ref="contribution:unbound-qualifier",
            kind="qualifier",
            source_unit_refs=("unit:qualifier",),
            target_ref="value:qualifier",
            target_kind="value",
            input_ports=(),
            output_ports=("role:modifier",),
            constraints=(),
            provenance_refs=("designation:qualifier",),
        )
        contributions = (*contributions, qualifier)
        source_refs = (*source_refs, "unit:qualifier")
        source_spans = (*source_spans, ("unit:qualifier", 8, 12))
    reference_slots = ()
    if include_reference:
        reference_slots = (
            ReferenceSlot.create(
                target_ref="entity:test",
                target_kind="entity",
                source_unit_refs=("unit:subject",),
                resolution_kind="designation",
                compatible_roles=("role:subject",),
                score_q=750_000,
                provenance_refs=("designation:subject",),
            ),
        )
    return ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=designations,
        contribution_slots=contributions,
        mode_slots=(mode,),
        application_frames=frames,
        reference_slots=reference_slots,
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=residuals,
        context_refs=("turn:bootstrap",),
        source_unit_refs=source_refs,
        source_unit_spans=source_spans,
        revision_pin=pin,
    )
def test_proposal_owner_and_bootstrap_accept_exact_proposal_context_only() -> None:
    owner_signature = inspect.signature(ProposalOwner.propose)
    bootstrap_signature = inspect.signature(BootstrapProposer.propose)

    assert tuple(owner_signature.parameters) == ("self", "context")
    assert tuple(bootstrap_signature.parameters) == ("self", "context")
    with pytest.raises(TypeError, match="exact ProposalContext"):
        BootstrapProposer(RuntimeConfig.release()).propose(object())


def test_bootstrap_propose_does_not_repeat_or_verify_orient_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("PROPOSE repeated an ORIENT or VERIFY owner")

    monkeypatch.setattr(FormResolver, "resolve", forbidden)
    monkeypatch.setattr(Grounder, "ground_text", forbidden)
    monkeypatch.setattr(ContributionExpander, "expand", forbidden)
    monkeypatch.setattr(ExactProgramVerifier, "verify_candidates", forbidden)

    result = BootstrapProposer(RuntimeConfig.release()).propose(_context())

    assert result.status == "candidates"
    assert len(result.candidates) >= 1


def test_bootstrap_output_is_deterministic_bounded_and_canonical() -> None:
    config = RuntimeConfig(max_complete_candidates=1)
    proposer = BootstrapProposer(config)
    context = _context(frame_count=2)

    first = proposer.propose(context)
    second = proposer.propose(context)

    assert first == second
    assert first.status == "candidates"
    assert first.truncated is True
    assert len(first.candidates) == config.max_complete_candidates
    assert tuple(candidate.rank for candidate in first.candidates) == (0,)
    assert all(type(candidate.score_q) is int for candidate in first.candidates)
    assert first.orientation_ref == context.orientation_ref
    assert first.proposal_context_ref == context.context_ref
    assert first.revision_pin == context.revision_pin
    assert first.model_identity == BootstrapProposer.model_identity
    assert ProposalResult.from_dict(first.as_dict()) == first
    for candidate in first.candidates:
        assert type(candidate) is RankedProgramCandidate
        assert SemanticSwitchProgram.from_dict(candidate.program.as_dict()) == candidate.program


def test_bootstrap_returns_typed_abstention_for_critical_unresolved_input() -> None:
    result = BootstrapProposer(RuntimeConfig.release()).propose(
        _context(critical_residual=True)
    )

    assert result.status == "abstained"
    assert result.candidates == ()
    assert result.abstention_code == "proposal:critical_residual"
    assert result.truncated is False


def test_bootstrap_candidate_reaches_exact_verification_without_repair() -> None:
    from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

    context = _context()
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)

    batch = ExactProgramVerifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    assert batch.selected_meaning is not None
    assert batch.selected_meaning.program_ref == proposal.candidates[0].program.program_ref

def test_reference_binding_uses_supporting_contribution_lineage() -> None:
    from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

    context = _context(subject_kind="reference", include_reference=True)
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)

    batch = ExactProgramVerifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    program = proposal.candidates[0].program
    reference_action = next(
        action for action in program.actions if action.action_type == "bind_reference"
    )
    assignment = next(
        row for row in program.source_assignments if row.source_unit_ref == "unit:subject"
    )
    assert assignment.target_action_ref == reference_action.action_ref
    assert context.contribution(assignment.contribution_slot_ref).kind == "reference"


def test_bound_qualifier_uses_qualifier_assignment_kind() -> None:
    from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

    context = _context(subject_kind="qualifier")
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)

    batch = ExactProgramVerifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    assignment = next(
        row
        for row in proposal.candidates[0].program.source_assignments
        if row.source_unit_ref == "unit:subject"
    )
    assert assignment.assignment_kind == "qualifier"
    assert assignment.critical is False


def test_unrepresentable_qualifier_abstains_without_inventing_residual() -> None:
    context = _context(unbound_qualifier=True)

    result = BootstrapProposer(RuntimeConfig.release()).propose(context)

    assert result.status == "abstained"
    assert result.candidates == ()
    assert result.abstention_code == "proposal:no_complete_candidate"

__cemm_test_inventory__ = {
    "tests/test_bootstrap_proposer_abi2.py::test_bootstrap_candidate_reaches_exact_verification_without_repair": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-candidate-verifies-without-repair",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "595674cecbeeda575ad8e13d7c28588470ab6c389f071602a9c8f1d3e83721a8"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_bootstrap_output_is_deterministic_bounded_and_canonical": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-bounded-canonical-output",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "b4e25484f2710045e2f2837dc1a4fcf6cf350de5e5d55732c1b066868fa43f88"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_bootstrap_propose_does_not_repeat_or_verify_orient_work": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-no-repeat-orient-or-verify",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "bc12073adf1c63d873df54b97a90ff14345da480714cd6f068ada09e32ebb568"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_bootstrap_returns_typed_abstention_for_critical_unresolved_input": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-critical-residual-abstention",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "76825b94ca5154549eb164728481821a8d41335db17fd5217493b6f28a35357c"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_bound_qualifier_uses_qualifier_assignment_kind": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-qualifier-assignment-kind",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "22439f1f7b8bd7bc5c956798dec98517b3cf378ba09a658a6b23f95650461a5c"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_proposal_owner_and_bootstrap_accept_exact_proposal_context_only": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-proposal-context-signature",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "9d44ff265a5f5923dab8b70dd5c7fb178881f57942d26e51a2d50560601bf5ca"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_reference_binding_uses_supporting_contribution_lineage": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-reference-supporting-contribution",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "7ae3d33a4b6fbf5e3e51a2b702a908989ae84c6fbe276b3fd61212259dff2c22"
    },
    "tests/test_bootstrap_proposer_abi2.py::test_unrepresentable_qualifier_abstains_without_inventing_residual": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-unrepresentable-qualifier-abstains",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-7",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "cc1e0665938b33b683be81d609c1b09df174686409859816e3c2b040ba0b3ac3"
    },
}
