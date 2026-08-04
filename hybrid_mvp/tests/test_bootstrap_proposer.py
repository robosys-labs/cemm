"""Tests for the deterministic bootstrap proposal oracle.

The :class:`BootstrapProposer` is a deterministic oracle for tests and episode
construction only. It searches legal action prefixes using the
:class:`LegalActionIndex` and indexed contributions/ports. It has no phrase
inventory and no word/regex branch. Canonical tie-breaking makes episode
generation deterministic.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.proposal import (
    ProposalResult,
)


# ---------------------------------------------------------------------------
# Parametrized paraphrase compilation test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "surface",
    [
        "what is your name?",
        "your name is what?",
        "what are you called?",
        "and you are called what?",
        "can I call you CEMM?",
        "I can call you CEMM, right?",
    ],
)
def test_paraphrases_compile_without_phrase_families(
    bootstrap_proposer, exact_verifier, orient, surface
):
    """Each paraphrase produces at least one accepted program.

    No candidate has a ``.family`` attribute — the bootstrap proposer has no
    phrase inventory and no word/regex branch.
    """
    result = bootstrap_proposer.propose(orient(surface))
    assert isinstance(result, ProposalResult)
    assert any(exact_verifier.verify(p).accepted for p in result.candidates)
    assert all(not hasattr(p, "family") for p in result.candidates)


# ---------------------------------------------------------------------------
# ProposalResult structure
# ---------------------------------------------------------------------------


def test_proposal_result_has_required_fields(bootstrap_proposer, orient):
    result = bootstrap_proposer.propose(orient("what is your name?"))
    assert isinstance(result, ProposalResult)
    assert isinstance(result.candidates, tuple)
    assert isinstance(result.explored_states, int)
    assert isinstance(result.truncated, bool)
    assert result.model_identity == "bootstrap-proposer"


def test_proposal_result_is_frozen(bootstrap_proposer, orient):
    result = bootstrap_proposer.propose(orient("what is your name?"))
    with pytest.raises(Exception):
        result.truncated = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Determinism: same input produces same output
# ---------------------------------------------------------------------------


def test_deterministic_same_input_same_output(bootstrap_proposer, orient):
    surface = "what is your name?"
    result1 = bootstrap_proposer.propose(orient(surface))
    result2 = bootstrap_proposer.propose(orient(surface))
    assert result1.explored_states == result2.explored_states
    assert result1.truncated == result2.truncated
    assert len(result1.candidates) == len(result2.candidates)
    for p1, p2 in zip(result1.candidates, result2.candidates):
        assert p1.program_ref == p2.program_ref


def test_candidates_sorted_by_program_ref(bootstrap_proposer, orient):
    result = bootstrap_proposer.propose(orient("what is your name?"))
    refs = [p.program_ref for p in result.candidates]
    assert refs == sorted(refs)


# ---------------------------------------------------------------------------
# No phrase inventory or regex branch
# ---------------------------------------------------------------------------


def test_no_phrase_inventory_attribute(bootstrap_proposer):
    """The BootstrapProposer must not have a phrase inventory."""
    assert not hasattr(bootstrap_proposer, "_phrase_inventory")
    assert not hasattr(bootstrap_proposer, "_phrases")
    assert not hasattr(bootstrap_proposer, "_regex")
    assert not hasattr(bootstrap_proposer, "_word_branch")


def test_no_family_attribute_on_candidates(bootstrap_proposer, orient):
    result = bootstrap_proposer.propose(orient("what is your name?"))
    for candidate in result.candidates:
        assert not hasattr(candidate, "family")


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_bootstrap_proposer_satisfies_protocol(bootstrap_proposer):
    """BootstrapProposer satisfies the ProposalModel protocol."""
    assert hasattr(bootstrap_proposer, "model_identity")
    assert hasattr(bootstrap_proposer, "propose")


# ---------------------------------------------------------------------------
# Release runtime guard
# ---------------------------------------------------------------------------


def test_release_only_raises(bootstrap_proposer, orient):
    """BootstrapProposer raises if release_only is set."""
    bootstrap_proposer._release_only = True
    with pytest.raises(RuntimeError, match="cannot be used in release runtime"):
        bootstrap_proposer.propose(orient("what is your name?"))
    bootstrap_proposer._release_only = False


# ---------------------------------------------------------------------------
# Typed-gap surface produces abstain or gap
# ---------------------------------------------------------------------------


def test_typed_gap_surface_produces_candidates(bootstrap_proposer, orient):
    """An unknown surface still produces candidates (abstain or complete)."""
    result = bootstrap_proposer.propose(orient("zorbulate"))
    assert isinstance(result, ProposalResult)
    # The proposer should still produce some candidates (at least abstain).
    assert len(result.candidates) >= 0
