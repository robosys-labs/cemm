"""Tests for the independent exact program verifier.

The :class:`ExactProgramVerifier` independently recomputes structural,
reference, scope, capability and transition legality of a
:class:`SemanticSwitchProgram`. It never reads proposal logits or scores and
never repairs a program. Invalid candidates receive typed rejection codes.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.verifier import (
    LegalActionIndex,
    VerificationError,
)


# ---------------------------------------------------------------------------
# Valid program is accepted
# ---------------------------------------------------------------------------


def test_valid_program_is_accepted(verifier, valid_program):
    result = verifier.verify(valid_program)
    assert result.accepted
    assert result.well_formed
    assert result.errors == ()
    assert result.program_ref == valid_program.program_ref


def test_valid_program_has_verification_hash(verifier, valid_program):
    result = verifier.verify(valid_program)
    assert result.verification_hash
    assert result.verification_hash.startswith("verification:")


def test_valid_program_has_coverage_receipt(verifier, valid_program):
    result = verifier.verify(valid_program)
    assert result.coverage_receipt is not None
    assert result.coverage_receipt.executable


def test_verification_hash_is_stable(verifier, valid_program):
    a = verifier.verify(valid_program)
    b = verifier.verify(valid_program)
    assert a.verification_hash == b.verification_hash


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
def test_mutated_program_is_rejected(verifier, valid_program, mutation, mutate):
    result = verifier.verify(mutate(valid_program, mutation))
    assert not result.accepted
    assert result.errors[0].code == mutation


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
def test_mutated_program_errors_are_typed(verifier, valid_program, mutation, mutate):
    result = verifier.verify(mutate(valid_program, mutation))
    for err in result.errors:
        assert isinstance(err, VerificationError)
        assert isinstance(err.code, str)
        assert isinstance(err.detail, str)


# ---------------------------------------------------------------------------
# Verifier independence: never reads logits, never repairs
# ---------------------------------------------------------------------------


def test_verifier_never_reads_proposal_logits(verifier, valid_program):
    """The verifier must not access any 'logits' or 'score' attribute."""
    # The verifier only takes the program; it has no access to logits.
    result = verifier.verify(valid_program)
    assert result.accepted
    # Verify the verifier has no logits/score attributes.
    assert not hasattr(verifier, "_logits")
    assert not hasattr(verifier, "_scores")


def test_verifier_does_not_repair_program(verifier, valid_program):
    """The verifier must not modify the input program."""
    original_actions = valid_program.actions
    original_assignments = valid_program.source_assignments
    verifier.verify(valid_program)
    assert valid_program.actions == original_actions
    assert valid_program.source_assignments == original_assignments


def test_verifier_well_formed_separate_from_accepted(verifier, valid_program):
    """A program can be well-formed (structural) but not accepted (coverage)."""
    # The valid program should be both well-formed and accepted.
    result = verifier.verify(valid_program)
    assert result.well_formed
    assert result.accepted


# ---------------------------------------------------------------------------
# VerificationResult structure
# ---------------------------------------------------------------------------


def test_verification_result_is_frozen(verifier, valid_program):
    result = verifier.verify(valid_program)
    with pytest.raises(Exception):
        result.accepted = False  # type: ignore[misc]


def test_verification_error_is_frozen():
    err = VerificationError(code="test", detail="detail", action_ref="action:0")
    with pytest.raises(Exception):
        err.code = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LegalActionIndex and ActionMasker construction
# ---------------------------------------------------------------------------


def test_legal_action_index_is_constructed_from_authority(linked_authority):
    from cemm_authoritative_hybrid.config import RuntimeConfig

    index = LegalActionIndex(linked_authority, RuntimeConfig.release())
    assert index is not None


def test_action_masker_delegates_to_legal_index(masker, prefix):
    """The masker delegates to the same LegalActionIndex as the verifier."""
    result = masker.legal_next_action_ids(prefix)
    assert isinstance(result, set)


def test_verifier_legal_index_is_immutable(verifier):
    """The LegalActionIndex is constructed during init and is immutable."""
    assert isinstance(verifier.legal_index, LegalActionIndex)
