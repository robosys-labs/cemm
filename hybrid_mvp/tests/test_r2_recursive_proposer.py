"""R2 recursive proposer tests.

Per R2 plan Task 4:
- Construct authentic recursive Program ABI 2 candidates from real context
- No valid recursive canary requires hand-injected programs
- Same context/config produces byte-identical proposal output
- Search stays within bounds
- Every candidate is canonical Program ABI 2
- PROPOSE never imports or invokes exact verification
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import SemanticSwitchProgram
from cemm_authoritative_hybrid.proposal import (
    BootstrapProposer,
    ProposalResult,
    RankedProgramCandidate,
)
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ExpressionLinkSlot,
    ModeSlot,
    ProposalContext,
    ReferenceSlot,
    ScopeSlot,
    TransitionSlot,
    VariableSlot,
)

__cemm_test_inventory__ = {
    "tests/test_r2_recursive_proposer.py::test_candidates_are_canonical_program_abi2": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-candidates-are-canonical-program-abi2",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "0a005949cb86683ee54380994371d77b8ab86e582332d7cab79246023eb1ae71"
    },
    "tests/test_r2_recursive_proposer.py::test_explored_states_is_bounded": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-explored-states-is-bounded",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "921fe9b9326d3e09b32cf118a6d1a561550cc6b01e785d4e83f10445e0f4accf"
    },
    "tests/test_r2_recursive_proposer.py::test_multi_app_candidate_has_multiple_roots": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-multi-app-candidate-has-multiple-roots",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "89df52dfc0bdd3c9f1c8ae668c84e17d3832eb8ee910906b74642d036e82b830"
    },
    "tests/test_r2_recursive_proposer.py::test_no_designation_abstains": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-no-designation-abstains",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "e37344db781147a5c5dc1fcbd54474553c096cc9c931b9b10301b6d8fdf7caa3"
    },
    "tests/test_r2_recursive_proposer.py::test_no_mode_abstains": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-no-mode-abstains",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "73e2275cafd1c41c5b893a6d260654c1a09f6f50b3afb114693a44445e5303e9"
    },
    "tests/test_r2_recursive_proposer.py::test_propose_does_not_invoke_verify": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-propose-does-not-invoke-verify",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "a73cb45e4a468a32cdf6f8d31f0dd3ceb2d1d77acc4de23f3fdf6172ed5bedd0"
    },
    "tests/test_r2_recursive_proposer.py::test_proposer_rank_order_preserved": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-proposer-rank-order-preserved",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "1e4834866dc5961bef3d5a36b79a7d2dc0355b661948b47c539f2e3d24eb2e53"
    },
    "tests/test_r2_recursive_proposer.py::test_same_context_produces_byte_identical_output": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-same-context-produces-byte-identical-output",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "60ac474c899514ce3958d44acdca89ea8e5b065b743bbd98f50f0d2ee5320ef3"
    },
    "tests/test_r2_recursive_proposer.py::test_search_stays_within_candidate_bound": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-search-stays-within-candidate-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "cac678e34412394849ac1f02710ee1d8b00ed1a4387b81259ba3e5e7e9a9c639"
    },
    "tests/test_r2_recursive_proposer.py::test_single_application_program_has_one_root": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-single-application-program-has-one-root",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "8e4fbf5c82cbd8fe3f3ab4581bb33358c3067467b0f58b4e22fdb07e973668df"
    },
    "tests/test_r2_recursive_proposer.py::test_truncated_when_more_candidates_exist": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-truncated-when-more-candidates-exist",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "135aca4818dc392511de156894f3b14ff71196a3b5c3db58c87fb9a0f7c308ac"
    },
    "tests/test_r2_recursive_proposer.py::test_two_designations_produce_multi_app_candidates": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-two-designations-produce-multi-app-candidates",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "11cf645429aaf3ce110e76bd9bc902bde967f3fbd92aefd8213f9d1ffabd59ef"
    },
}



# ---------------------------------------------------------------------------
# Test context builders
# ---------------------------------------------------------------------------


def _pin() -> RevisionPin:
    return RevisionPin(
        "authority:bootstrap", 1, 2, 3, 4, BootstrapProposer.model_identity
    )


def _simple_context() -> ProposalContext:
    """Context with one designation, one frame, one subject contribution."""
    pin = _pin()
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    designations = (
        DesignationSlot.create(
            source_unit_refs=("unit:predicate",),
            target_ref="event:test-0",
            target_kind="event_type",
            score_q=900_000,
            designation_fact_ref="designation:test-0",
            provenance_refs=("designation:test-0",),
        ),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate-0",
        kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref="event:test-0",
        target_kind="event_type",
        input_ports=("role:subject",),
        output_ports=("role:event",),
        constraints=(),
        provenance_refs=("designation:test-0",),
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
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designations[0].slot_ref,
        predicate_target_ref=designations[0].target_ref,
        predicate_kind=designations[0].target_kind,
        operator_ref="op:event",
        structural_role_ref="role:event",
        required_roles=("role:subject",),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=(),
        affordance_frame_ref="frame:test-0",
        provenance_refs=(designations[0].slot_ref, "frame:test-0"),
    )
    return ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=designations,
        contribution_slots=(predicate, subject),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:bootstrap",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:subject", 4, 8),
        ),
        revision_pin=pin,
    )


def _two_designation_context() -> ProposalContext:
    """Context with two designations and two frames for multi-app programs."""
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
        for i in range(2)
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
        for i in range(2)
    )
    subjects = tuple(
        ContributionSlot.create(
            contribution_ref=f"contribution:subject-{i}",
            kind="anchor",
            source_unit_refs=(f"unit:subject-{i}",),
            target_ref="entity:test",
            target_kind="entity",
            input_ports=(),
            output_ports=("role:subject",),
            constraints=(),
            provenance_refs=("designation:subject",),
        )
        for i in range(2)
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
        for i in range(2)
    )
    source_refs = ("unit:predicate-0", "unit:predicate-1", "unit:subject-0", "unit:subject-1")
    return ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=designations,
        contribution_slots=(*predicates, *subjects),
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
        source_unit_spans=(
            ("unit:predicate-0", 0, 4),
            ("unit:predicate-1", 4, 8),
            ("unit:subject-0", 8, 12),
            ("unit:subject-1", 12, 16),
        ),
        revision_pin=pin,
    )


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


def test_same_context_produces_byte_identical_output():
    """Same context/config produces byte-identical proposal output."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _simple_context()
    first = proposer.propose(context)
    second = proposer.propose(context)
    assert first == second
    assert ProposalResult.from_dict(first.as_dict()) == first


def test_candidates_are_canonical_program_abi2():
    """Every candidate is canonical Program ABI 2."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _simple_context()
    result = proposer.propose(context)
    assert result.status == "candidates"
    assert len(result.candidates) >= 1
    for candidate in result.candidates:
        assert type(candidate) is RankedProgramCandidate
        assert SemanticSwitchProgram.from_dict(candidate.program.as_dict()) == candidate.program


def test_proposer_rank_order_preserved():
    """Candidates preserve proposer rank/order, not sorted by ref."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _simple_context()
    result = proposer.propose(context)
    ranks = [c.rank for c in result.candidates]
    assert ranks == list(range(len(ranks)))
    scores = [c.score_q for c in result.candidates]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


# ---------------------------------------------------------------------------
# Bounds tests
# ---------------------------------------------------------------------------


def test_search_stays_within_candidate_bound():
    """Search respects max_candidates bound."""
    config = RuntimeConfig(max_complete_candidates=2)
    proposer = BootstrapProposer(config)
    context = _simple_context()
    result = proposer.propose(context)
    assert len(result.candidates) <= 2


def test_truncated_when_more_candidates_exist():
    """Truncated is True when search bound prevents exhaustive completion."""
    config = RuntimeConfig(max_complete_candidates=1)
    proposer = BootstrapProposer(config)
    context = _two_designation_context()
    result = proposer.propose(context)
    assert result.status == "candidates"
    assert len(result.candidates) == 1
    assert result.truncated is True


def test_explored_states_is_bounded():
    """Explored states never exceeds max_explored."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _simple_context()
    result = proposer.propose(context)
    max_explored = RuntimeConfig.release().max_beam_states * RuntimeConfig.release().max_applications
    assert result.explored_states <= max_explored


# ---------------------------------------------------------------------------
# Recursive composition tests
# ---------------------------------------------------------------------------


def test_single_application_program_has_one_root():
    """A simple context produces a single-application, single-root program."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _simple_context()
    result = proposer.propose(context)
    assert result.status == "candidates"
    # First candidate should be the simplest (1 application)
    program = result.candidates[0].program
    instantiate_count = sum(
        1 for a in program.actions if a.action_type == "instantiate_operator"
    )
    assert instantiate_count == 1
    assert len(program.root_refs) == 1


def test_two_designations_produce_multi_app_candidates():
    """Two designations allow multiple-application candidates."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _two_designation_context()
    result = proposer.propose(context)
    assert result.status == "candidates"
    assert len(result.candidates) >= 1
    # At least one candidate should have 2+ applications
    max_apps = max(
        sum(1 for a in c.program.actions if a.action_type == "instantiate_operator")
        for c in result.candidates
    )
    assert max_apps >= 2


def test_multi_app_candidate_has_multiple_roots():
    """Multi-application candidates have multiple roots (no nesting)."""
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _two_designation_context()
    result = proposer.propose(context)
    multi_root = [
        c for c in result.candidates if len(c.program.root_refs) >= 2
    ]
    assert len(multi_root) >= 1


# ---------------------------------------------------------------------------
# Abstention tests
# ---------------------------------------------------------------------------


def test_no_mode_abstains():
    """No mode slots is rejected by ProposalContext.create validation.

    The proposer never receives an empty-mode context because context
    construction fails first.  This test verifies the guard.
    """
    import pytest as _pytest
    pin = _pin()
    with _pytest.raises(ValueError, match="at least one mode slot"):
        ProposalContext.create(
            orientation_ref="orientation:bootstrap",
            evidence_packet_ref="evidence:bootstrap",
            form_lattice_ref="lattice:bootstrap",
            grounding_ref="grounding:bootstrap",
            designation_slots=(),
            contribution_slots=(),
            mode_slots=(),
            application_frames=(),
            reference_slots=(),
            scope_slots=(),
            expression_link_slots=(),
            variable_slots=(),
            transition_slots=(),
            residual_evidence=(),
            context_refs=("turn:bootstrap",),
            source_unit_refs=("unit:dummy",),
            source_unit_spans=(("unit:dummy", 0, 4),),
            revision_pin=pin,
        )


def test_no_designation_abstains():
    """No designation slots produces typed abstention from the proposer."""
    from cemm_authoritative_hybrid.proposal_context import ResidualEvidence

    pin = _pin()
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    residual = ResidualEvidence.create(
        source_unit_ref="unit:dummy",
        contribution_kind="qualifier",
        critical=False,
        reason="no designation available",
    )
    context = ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=(),
        contribution_slots=(),
        mode_slots=(mode,),
        application_frames=(),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(residual,),
        context_refs=("turn:bootstrap",),
        source_unit_refs=("unit:dummy",),
        source_unit_spans=(("unit:dummy", 0, 4),),
        revision_pin=pin,
    )
    proposer = BootstrapProposer(RuntimeConfig.release())
    result = proposer.propose(context)
    assert result.status == "abstained"


# ---------------------------------------------------------------------------
# PROPOSE-VERIFY isolation test
# ---------------------------------------------------------------------------


def test_propose_does_not_invoke_verify(monkeypatch: pytest.MonkeyPatch):
    """PROPOSE never imports or invokes exact verification."""
    from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

    def forbidden(*_a, **_kw):
        raise AssertionError("PROPOSE invoked VERIFY")

    monkeypatch.setattr(ExactProgramVerifier, "verify_candidates", forbidden)
    proposer = BootstrapProposer(RuntimeConfig.release())
    context = _simple_context()
    result = proposer.propose(context)
    assert result.status == "candidates"
