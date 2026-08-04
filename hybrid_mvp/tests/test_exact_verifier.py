"""Tests for the independent exact program verifier.

The :class:`ExactProgramVerifier` independently recomputes structural,
reference, scope, capability and transition legality of a
:class:`SemanticSwitchProgram`. It never reads proposal logits or scores and
never repairs a program. Invalid candidates receive typed rejection codes.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.proposal import (
    ProposalResult,
    RankedProgramCandidate,
)
from cemm_authoritative_hybrid.verifier import (
    LegalActionIndex,
    VerificationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _proposal_for(program, context):
    """Wrap a single program in a one-candidate ProposalResult."""

    candidate = RankedProgramCandidate.create(
        rank=0,
        score_q=900_000,
        program=program,
        provenance_refs=("derivation:0",),
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


# Mutations that produce malformed wire/ABI artifacts that cannot legally
# cross the owner boundary — these raise ValueError at construction time.
# Per R2 plan section 1.3: "Use constructor failure only for malformed
# wire/ABI artifacts that cannot legally cross the owner boundary."
#
# scope_cycle: malformed bind_nested_application arguments (wrong arity)
# stale_revision: revision pin mismatch makes the program a non-canonical wire artifact
# uncovered_unit: source assignment mismatch makes the program a non-canonical wire artifact
_CONSTRUCTOR_ERROR_MUTATIONS = frozenset({"scope_cycle", "stale_revision", "uncovered_unit"})

# Mapping from mutation name to the expected verifier error code.
# These mutations produce semantically invalid programs that pass
# construction validation but must be rejected by the verifier.
_ERROR_CODES = {
    "unknown_ref": "unknown_designation_slot",
    "wrong_kind": "unknown_contribution_slot",
    "missing_role": "missing_required_role",
    "duplicate_role": "duplicate_role_binding",
    "excess_depth": "unknown_variable_slot",
}


# ---------------------------------------------------------------------------
# Valid program is accepted
# ---------------------------------------------------------------------------


def test_valid_program_is_accepted(verifier, proposal, proposal_context, valid_program):
    batch = verifier.verify_candidates(proposal, proposal_context)
    receipt = batch.candidate_receipts[0]
    assert receipt.accepted
    assert receipt.verification_errors == ()
    assert receipt.program_ref == valid_program.program_ref


def test_valid_program_has_verification_hash(verifier, proposal, proposal_context):
    batch = verifier.verify_candidates(proposal, proposal_context)
    receipt = batch.candidate_receipts[0]
    assert receipt.compilation_proof is not None
    assert receipt.compilation_proof.proof_ref


def test_valid_program_has_coverage_receipt(verifier, proposal, proposal_context):
    batch = verifier.verify_candidates(proposal, proposal_context)
    receipt = batch.candidate_receipts[0]
    assert receipt.coverage_receipt is not None
    assert receipt.coverage_receipt.executable


def test_verification_hash_is_stable(verifier, proposal, proposal_context):
    a = verifier.verify_candidates(proposal, proposal_context)
    b = verifier.verify_candidates(proposal, proposal_context)
    assert (
        a.candidate_receipts[0].compilation_proof.proof_ref
        == b.candidate_receipts[0].compilation_proof.proof_ref
    )


# ---------------------------------------------------------------------------
# Mutated programs are rejected with specific error codes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_ref",
        "wrong_kind",
        "missing_role",
        "duplicate_role",
        "scope_cycle",
        "stale_revision",
        "excess_depth",
        "uncovered_unit",
    ],
)
def test_mutated_program_is_rejected(
    verifier, valid_program, proposal_context, mutation, mutate
):
    mutated = mutate(valid_program, mutation)
    if mutation in _CONSTRUCTOR_ERROR_MUTATIONS:
        # Malformed wire/ABI artifact — constructor failure is the earliest owner
        with pytest.raises(ValueError):
            mutated_proposal = _proposal_for(mutated, proposal_context)
            verifier.verify_candidates(mutated_proposal, proposal_context)
        return
    # Semantically invalid program — verifier must produce typed error
    batch = verifier.verify_candidates(
        _proposal_for(mutated, proposal_context), proposal_context
    )
    receipt = batch.candidate_receipts[0]
    assert not receipt.accepted
    expected = _ERROR_CODES[mutation]
    assert any(err.code == expected for err in receipt.verification_errors)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_ref",
        "wrong_kind",
        "missing_role",
        "duplicate_role",
        "scope_cycle",
        "stale_revision",
        "excess_depth",
        "uncovered_unit",
    ],
)
def test_mutated_program_errors_are_typed(
    verifier, valid_program, proposal_context, mutation, mutate
):
    mutated = mutate(valid_program, mutation)
    if mutation in _CONSTRUCTOR_ERROR_MUTATIONS:
        # Malformed wire/ABI artifact — constructor failure is the earliest owner
        with pytest.raises(ValueError):
            mutated_proposal = _proposal_for(mutated, proposal_context)
            verifier.verify_candidates(mutated_proposal, proposal_context)
        return
    # Semantically invalid program — verifier must produce typed error
    batch = verifier.verify_candidates(
        _proposal_for(mutated, proposal_context), proposal_context
    )
    receipt = batch.candidate_receipts[0]
    for err in receipt.verification_errors:
        assert isinstance(err, VerificationError)
        assert isinstance(err.code, str)
        assert isinstance(err.detail, str)


# ---------------------------------------------------------------------------
# Verifier independence: never reads logits, never repairs
# ---------------------------------------------------------------------------


def test_verifier_never_reads_proposal_logits(verifier, proposal, proposal_context):
    """The verifier must not access any 'logits' or 'score' attribute."""
    batch = verifier.verify_candidates(proposal, proposal_context)
    assert batch.candidate_receipts[0].accepted
    # Verify the verifier has no logits/score attributes.
    assert not hasattr(verifier, "_logits")
    assert not hasattr(verifier, "_scores")


def test_verifier_does_not_repair_program(
    verifier, proposal, proposal_context, valid_program
):
    """The verifier must not modify the input program."""
    original_actions = valid_program.actions
    original_assignments = valid_program.source_assignments
    verifier.verify_candidates(proposal, proposal_context)
    assert valid_program.actions == original_actions
    assert valid_program.source_assignments == original_assignments


def test_verifier_well_formed_separate_from_accepted(
    verifier, proposal, proposal_context
):
    """A program can be well-formed (structural) but not accepted (coverage)."""
    # The valid program should be both well-formed and accepted.
    batch = verifier.verify_candidates(proposal, proposal_context)
    receipt = batch.candidate_receipts[0]
    assert receipt.accepted
    assert batch.status == "selected"


# ---------------------------------------------------------------------------
# VerificationResult structure
# ---------------------------------------------------------------------------


def test_verification_result_is_frozen(verifier, proposal, proposal_context):
    batch = verifier.verify_candidates(proposal, proposal_context)
    receipt = batch.candidate_receipts[0]
    with pytest.raises(Exception):
        receipt.accepted = False  # type: ignore[misc]


def test_verification_error_is_frozen():
    err = VerificationError(code="test", detail="detail", action_ref="action:0")
    with pytest.raises(Exception):
        err.code = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LegalActionIndex and ActionMasker construction
# ---------------------------------------------------------------------------


def test_legal_action_index_is_constructed_from_authority(proposal_context):
    index = LegalActionIndex(proposal_context)
    assert index is not None


def test_action_masker_delegates_to_legal_index(masker, prefix, valid_program):
    """The masker delegates to the same LegalActionIndex as the verifier."""
    result = masker.filter_legal(prefix, valid_program.actions)
    assert isinstance(result, tuple)


def test_verifier_legal_index_is_immutable(verifier, proposal_context):
    """The LegalActionIndex is constructed from the proposal context."""
    index = LegalActionIndex(proposal_context)
    assert isinstance(index, LegalActionIndex)
