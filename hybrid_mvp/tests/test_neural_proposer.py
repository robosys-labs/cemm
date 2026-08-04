"""Tests for the neural switch proposer (M2 Task 6 Step 1).

These tests verify that:
- The release runtime requires a NeuralSwitchProposer
- The neural decoder never emits a masked action
- Internal ref spelling does not affect model logits (alpha-equivalence)
- The proposal model capacity is bounded (≤25M parameters)
- The legacy candidate API is absent
"""

from __future__ import annotations

import torch

from cemm_authoritative_hybrid.model import NeuralSwitchProposer


def test_release_runtime_requires_neural_switch_proposer(release_factory):
    """The neural profile returns a NeuralSwitchProposer."""
    runtime = release_factory()
    assert isinstance(runtime.proposal_model, NeuralSwitchProposer)
    assert runtime.proposal_model.metadata.action_encoding_hash == runtime.action_encoding_hash


def test_neural_decoder_never_emits_masked_action(trained_proposer, orientations, exact_verifier):
    """All candidates produced by the neural proposer are well-formed."""
    for orientation in orientations:
        result = trained_proposer.propose(orientation)
        assert result.candidates
        for program in result.candidates:
            verification = exact_verifier.verify(program)
            assert verification.well_formed, (
                f"Program {program.program_ref} is not well-formed: "
                f"{[e.code for e in verification.errors]}"
            )


def test_internal_ref_spelling_does_not_affect_model_logits(
    trained_proposer, alpha_equivalent_orientations
):
    """Structural logits are identical for alpha-equivalent orientations."""
    original, renamed = alpha_equivalent_orientations
    logits1 = trained_proposer.structural_logits(original)
    logits2 = trained_proposer.structural_logits(renamed)
    assert torch.equal(logits1, logits2), (
        "Structural logits differ for alpha-equivalent orientations"
    )


def test_proposal_model_capacity_is_bounded(trained_proposer):
    """The trainable parameter count is ≤ 25,000,000."""
    assert trained_proposer.trainable_parameter_count <= 25_000_000


def test_legacy_candidate_api_is_absent():
    """The package must not export CandidateGenerator."""
    import cemm_authoritative_hybrid as package
    assert not hasattr(package, "CandidateGenerator")
