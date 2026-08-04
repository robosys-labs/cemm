"""Tests for production proposer cutover (M2 Task 6 Step 1).

These tests verify that:
- A compatible new designation keeps the model active
- The neural profile loads correctly from the artifact
- The development profile still works
"""

from __future__ import annotations

from cemm_authoritative_hybrid.model import NeuralSwitchProposer


def test_compatible_new_designation_keeps_model_active(release_factory, designation_store):
    """A new designation doesn't invalidate the model."""
    runtime = release_factory()
    model_identity = runtime.proposal_model.model_identity
    designation_store.commit_reviewed("cheerful", "state_value:happy")
    runtime.refresh_compatible_generation()
    assert runtime.proposal_model.model_identity == model_identity
    result = runtime.propose_and_verify("s", "I am cheerful")
    assert result.accepted


def test_neural_profile_loads_from_artifact(release_factory):
    """The neural profile loads correctly from the safetensors artifact."""
    runtime = release_factory()
    assert runtime.profile == "neural"
    assert isinstance(runtime.proposal_model, NeuralSwitchProposer)
    assert runtime.proposal_model.model_identity
    assert runtime.action_encoding_hash


def test_development_profile_still_works(runtime_factory):
    """The development profile with fixture owners still works."""
    runtime = runtime_factory()
    assert runtime.profile == "development"
    result = runtime.propose_and_verify("s", "hello")
    # The fixture proposal owner returns a fixed program; verification passes
    assert result.proposal is not None
