"""Tests for neural realizer weight use and ablation.

Verifies that:
- Normal realization invokes the loaded weights (forward is called)
- Zero-weight realizer loses domain generation accuracy
- Normal answer cannot fall back when network fails
- Every normal realization receipt records model identity and decoder count
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.realization import (
    NeuralConstrainedRealizer,
    RealizationVerifier,
)
from cemm_authoritative_hybrid.response import ResponseMeaning


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


ROOT = Path(__file__).resolve().parents[1]


def _make_response_meaning(
    *,
    discourse_action="answer",
    polarity="positive",
    modality="actual",
    epistemic_status="supported",
    status="resolved",
    mode="QUERY",
    proposition_ref="prop:test",
) -> ResponseMeaning:
    """Create a ResponseMeaning for testing."""
    from cemm_authoritative_hybrid.canonical import stable_ref

    response_ref = stable_ref(
        "response",
        {
            "mode": mode,
            "status": status,
            "proposition_ref": proposition_ref,
            "polarity": polarity,
            "modality": modality,
            "epistemic_status": epistemic_status,
            "discourse_action": discourse_action,
        },
    )
    return ResponseMeaning(
        response_ref=response_ref,
        mode=mode,
        status=status,
        proposition_ref=proposition_ref,
        requested_bindings=(("participant:system", "query"),),
        polarity=polarity,
        modality=modality,
        epistemic_status=epistemic_status,
        source_refs=("participant:system",),
        proof_refs=("effect:proof",),
        discourse_action=discourse_action,
        permitted_omissions=(),
    )


def normal_answer_meaning() -> ResponseMeaning:
    """Create a normal answer ResponseMeaning (positive, supported)."""
    return _make_response_meaning(
        discourse_action="answer",
        polarity="positive",
        epistemic_status="supported",
        status="resolved",
    )


def _holdout_meanings() -> list[tuple[ResponseMeaning, str]]:
    """Return a holdout set of (response_meaning, expected_surface) pairs."""
    return [
        (
            _make_response_meaning(
                discourse_action="answer",
                polarity="positive",
                epistemic_status="supported",
                proposition_ref="prop:name_holdout",
            ),
            "My name is CEMM.",
        ),
        (
            _make_response_meaning(
                discourse_action="answer",
                polarity="negative",
                epistemic_status="supported",
                proposition_ref="prop:neg_holdout",
            ),
            "No, that is not supported.",
        ),
        (
            _make_response_meaning(
                discourse_action="acknowledge",
                polarity="positive",
                epistemic_status="supported",
                proposition_ref="prop:ack_holdout",
            ),
            "Understood.",
        ),
        (
            _make_response_meaning(
                discourse_action="unknown",
                polarity="positive",
                epistemic_status="unknown",
                status="unknown",
                proposition_ref="prop:unknown_holdout",
            ),
            "I do not know.",
        ),
        (
            _make_response_meaning(
                discourse_action="deny",
                polarity="negative",
                epistemic_status="denied",
                status="denied",
                mode="REQUEST",
                proposition_ref="prop:deny_holdout",
            ),
            "That is not permitted.",
        ),
        (
            _make_response_meaning(
                discourse_action="ambiguous",
                polarity="positive",
                epistemic_status="unknown",
                status="ambiguous",
                proposition_ref="prop:ambig_holdout",
            ),
            "The request is ambiguous.",
        ),
    ]


def verified_realization_accuracy(
    realizer: NeuralConstrainedRealizer,
    holdout: list[tuple[ResponseMeaning, str]],
) -> float:
    """Compute the fraction of holdout pairs that pass equivalence verification.

    A pair passes if the realizer produces a surface that the verifier
    accepts as equivalent to the response meaning.
    """
    verifier = realizer._verifier
    correct = 0
    total = len(holdout)
    for rm, _expected in holdout:
        receipt = realizer.realize(rm)
        if receipt.status == "realized" and receipt.equivalence_receipt is not None:
            if receipt.equivalence_receipt.equivalent:
                correct += 1
        elif receipt.status == "safe" and receipt.equivalence_receipt is not None:
            if receipt.equivalence_receipt.equivalent:
                correct += 1
    return correct / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def release_realizer():
    """Load the trained realizer from artifacts/realizer_dev/."""
    from cemm_authoritative_hybrid.canonical import sha256_file
    from cemm_authoritative_hybrid.model import load_realizer_from_artifact

    artifact_dir = ROOT / "artifacts" / "realizer_dev"
    manifest_path = artifact_dir / "model_manifest.json"
    manifest_sha256 = sha256_file(manifest_path)

    return load_realizer_from_artifact(
        artifact_dir,
        manifest_sha256,
        verifier=RealizationVerifier(),
    )


@pytest.fixture
def realization_holdout():
    """A holdout set of (response_meaning, expected_surface) pairs."""
    return _holdout_meanings()


@pytest.fixture
def normal_answer_meaning():
    """A normal answer ResponseMeaning (positive, supported)."""
    return _make_response_meaning(
        discourse_action="answer",
        polarity="positive",
        epistemic_status="supported",
        status="resolved",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNeuralRealizerWeightUse:
    def test_normal_realization_invokes_loaded_weights(
        self, monkeypatch, release_realizer, normal_answer_meaning
    ):
        """The network's forward method is called during realization."""
        calls = 0
        original = release_realizer.network.forward

        def observed_forward(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(release_realizer.network, "forward", observed_forward)
        receipt = release_realizer.realize(normal_answer_meaning)
        assert calls > 0
        assert receipt.model_identity == release_realizer.model_identity

    def test_zero_weight_realizer_loses_domain_generation_accuracy(
        self, release_realizer, realization_holdout
    ):
        """Full accuracy == 1.0, ablated <= 0.50, drop >= 0.30."""
        full = verified_realization_accuracy(release_realizer, realization_holdout)
        ablated = verified_realization_accuracy(
            release_realizer.with_zeroed_weights(), realization_holdout
        )
        assert full == 1.0, f"Full accuracy too low: {full}"
        assert ablated <= 0.50, f"Ablated accuracy too high: {ablated}"
        assert full - ablated >= 0.30, f"Accuracy drop too small: {full - ablated}"

    def test_normal_answer_cannot_fall_back_when_network_fails(
        self, monkeypatch, release_realizer, normal_answer_meaning
    ):
        """When the network fails, normal answers get realization_failed, not safe."""
        monkeypatch.setattr(
            release_realizer.network,
            "forward",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("sentinel")),
        )
        receipt = release_realizer.realize(normal_answer_meaning)
        assert receipt.status == "realization_failed"
        assert receipt.surface is None

    def test_normal_realization_records_decoder_invocations(
        self, release_realizer, normal_answer_meaning
    ):
        """Every normal realization receipt records decoder invocation count."""
        receipt = release_realizer.realize(normal_answer_meaning)
        assert receipt.decoder_invocations > 0

    def test_normal_realization_records_model_identity(
        self, release_realizer, normal_answer_meaning
    ):
        """Every normal realization receipt records the loaded model identity."""
        receipt = release_realizer.realize(normal_answer_meaning)
        assert receipt.model_identity == release_realizer.model_identity

    def test_failure_meaning_uses_safe_fallback(self, release_realizer):
        """Failure meanings can fall back to SafeRealizer when neural fails."""
        monkeypatch_meaning = _make_response_meaning(
            discourse_action="unknown",
            epistemic_status="unknown",
            status="unknown",
        )
        receipt = release_realizer.realize(monkeypatch_meaning)
        # Should either realize or fall back to safe.
        assert receipt.status in ("realized", "safe")

    def test_with_zeroed_weights_preserves_model_identity(
        self, release_realizer
    ):
        """Zero-weight clone preserves the model identity for comparison."""
        ablated = release_realizer.with_zeroed_weights()
        assert ablated.model_identity == release_realizer.model_identity
