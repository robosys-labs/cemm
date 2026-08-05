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
    RankedProgramCandidate,
)

__cemm_test_inventory__ = {
    "tests/test_bootstrap_proposer.py::test_candidates_preserve_proposer_rank_order": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-candidates-preserve-proposer-rank-order",
        "contributes_to_rewrite_refs": [
            "rewrite_obligation:d9845bfb158bf7f79e57376f"
        ],
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "a3ce802f20be5b8572958d9c366801524b73cbf974e59ad172a35f970810c2d2"
    },
}



def _proposal(program, context):
    """Wrap a single program in a one-candidate ProposalResult for verification."""
    return ProposalResult.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        candidates=(
            RankedProgramCandidate.create(
                rank=0,
                score_q=0,
                program=program,
                provenance_refs=("derivation:0",),
            ),
        ),
        status="candidates",
        abstention_code=None,
        explored_states=1,
        truncated=False,
        model_identity=context.revision_pin.model_identity or "model:test",
        revision_pin=context.revision_pin,
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
    bootstrap_proposer,
    exact_verifier,
    form_resolver,
    linked_authority,
    surface,
):
    """Each paraphrase produces at least one accepted program.

    No candidate has a ``.family`` attribute — the bootstrap proposer has no
    phrase inventory and no word/regex branch.
    """
    from cemm_authoritative_hybrid.proposal import BootstrapProposer
    from tests.conftest import _build_context_and_program_from_lattice, _default_revision_pin

    lattice = form_resolver.resolve(surface)
    pin = _default_revision_pin(authority_generation=linked_authority.generation)
    pin = type(pin)(
        authority_generation=pin.authority_generation,
        world_revision=pin.world_revision,
        session_revision=pin.session_revision,
        episode_revision=pin.episode_revision,
        effect_revision=pin.effect_revision,
        model_identity=BootstrapProposer.model_identity,
    )
    context, _program = _build_context_and_program_from_lattice(
        lattice, revision_pin=pin
    )
    result = bootstrap_proposer.propose(context)
    assert isinstance(result, ProposalResult)
    assert any(
        any(
            r.accepted
            for r in exact_verifier.verify_candidates(
                _proposal(p.program, context), context
            ).candidate_receipts
        )
        for p in result.candidates
    )
    assert all(not hasattr(p, "family") for p in result.candidates)


# ---------------------------------------------------------------------------
# ProposalResult structure
# ---------------------------------------------------------------------------


def test_proposal_result_has_required_fields(bootstrap_proposer, proposal_context):
    result = bootstrap_proposer.propose(proposal_context)
    assert isinstance(result, ProposalResult)
    assert isinstance(result.candidates, tuple)
    assert isinstance(result.explored_states, int)
    assert isinstance(result.truncated, bool)
    assert result.model_identity == "bootstrap-proposer"


def test_proposal_result_is_frozen(bootstrap_proposer, proposal_context):
    result = bootstrap_proposer.propose(proposal_context)
    with pytest.raises(Exception):
        result.truncated = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Determinism: same input produces same output
# ---------------------------------------------------------------------------


def test_deterministic_same_input_same_output(bootstrap_proposer, proposal_context):
    result1 = bootstrap_proposer.propose(proposal_context)
    result2 = bootstrap_proposer.propose(proposal_context)
    assert result1.explored_states == result2.explored_states
    assert result1.truncated == result2.truncated
    assert len(result1.candidates) == len(result2.candidates)
    for p1, p2 in zip(result1.candidates, result2.candidates):
        assert p1.candidate_ref == p2.candidate_ref


def test_candidates_preserve_proposer_rank_order(bootstrap_proposer, proposal_context):
    """Candidates must preserve proposer rank/order, not be sorted by ref.

    Per R2 plan section 10.6: preserve proposer rank/order; do not sort
    candidates by program ref. Expression grouping occurs in VERIFY.
    """
    result = bootstrap_proposer.propose(proposal_context)
    ranks = [p.rank for p in result.candidates]
    # Ranks must be contiguous starting from 0
    assert ranks == list(range(len(ranks)))
    # Scores must be non-increasing (proposer rank order)
    scores = [p.score_q for p in result.candidates]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


# ---------------------------------------------------------------------------
# No phrase inventory or regex branch
# ---------------------------------------------------------------------------


def test_no_phrase_inventory_attribute(bootstrap_proposer):
    """The BootstrapProposer must not have a phrase inventory."""
    assert not hasattr(bootstrap_proposer, "_phrase_inventory")
    assert not hasattr(bootstrap_proposer, "_phrases")
    assert not hasattr(bootstrap_proposer, "_regex")
    assert not hasattr(bootstrap_proposer, "_word_branch")


def test_no_family_attribute_on_candidates(bootstrap_proposer, proposal_context):
    result = bootstrap_proposer.propose(proposal_context)
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


def test_release_only_raises(bootstrap_proposer, proposal_context):
    """BootstrapProposer raises if release_only is set."""
    bootstrap_proposer._release_only = True
    with pytest.raises(RuntimeError, match="cannot be used in release runtime"):
        bootstrap_proposer.propose(proposal_context)
    bootstrap_proposer._release_only = False


# ---------------------------------------------------------------------------
# Typed-gap surface produces abstain or gap
# ---------------------------------------------------------------------------


def test_typed_gap_surface_produces_candidates(bootstrap_proposer, proposal_context):
    """An unknown surface still produces a typed proposal result.

    The proposer must either produce at least one candidate or explicitly
    abstain with a typed abstention code. A vacuous bound is not accepted.
    """
    result = bootstrap_proposer.propose(proposal_context)
    assert isinstance(result, ProposalResult)
    # The proposer must either produce candidates or abstain with a code.
    if result.status == "abstained":
        assert result.abstention_code is not None
        assert len(result.candidates) == 0
    else:
        assert len(result.candidates) >= 1
