"""Tests for the SafeRealizer safety channel.

Verifies that SafeRealizer:
- Realizes ONLY reviewed failure meanings (unknown, ambiguous, denied,
  operation_failed, realization_failed)
- Raises UnsafeFallbackError for normal answer meanings
- Produces "safe" status receipts
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.realization import (
    RealizationReceipt,
    RealizationVerifier,
    SafeRealizer,
    UnsafeFallbackError,
)
from cemm_authoritative_hybrid.response import ResponseMeaning


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def failure_meaning(status: str) -> ResponseMeaning:
    """Create a failure ResponseMeaning for the given status."""
    polarity = "negative" if status in ("denied", "operation_failed", "realization_failed") else "positive"
    epistemic = "denied" if status == "denied" else "unknown"
    mode = "REQUEST" if status in ("denied", "operation_failed") else "QUERY"
    return _make_response_meaning(
        discourse_action=status,
        polarity=polarity,
        epistemic_status=epistemic,
        status=status,
        mode=mode,
    )


def normal_answer_meaning() -> ResponseMeaning:
    """Create a normal answer ResponseMeaning."""
    return _make_response_meaning(
        discourse_action="answer",
        polarity="positive",
        epistemic_status="supported",
        status="resolved",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def safe_realizer():
    """A SafeRealizer for testing."""
    return SafeRealizer(RealizationVerifier())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSafeRealizer:
    @pytest.mark.parametrize(
        "status",
        ["unknown", "ambiguous", "denied", "operation_failed", "realization_failed"],
    )
    def test_safe_realizer_is_limited_to_failure_actions(
        self, safe_realizer, status
    ):
        """SafeRealizer realizes failure meanings with status 'safe'."""
        receipt = safe_realizer.realize(failure_meaning(status))
        assert receipt.status == "safe"
        assert receipt.surface is not None
        assert receipt.model_identity is None

    def test_safe_realizer_rejects_normal_answer(self, safe_realizer):
        """SafeRealizer raises UnsafeFallbackError for normal answers."""
        with pytest.raises(UnsafeFallbackError):
            safe_realizer.realize(normal_answer_meaning())

    def test_safe_realizer_rejects_acknowledge(self, safe_realizer):
        """SafeRealizer raises UnsafeFallbackError for acknowledge actions."""
        rm = _make_response_meaning(discourse_action="acknowledge")
        with pytest.raises(UnsafeFallbackError):
            safe_realizer.realize(rm)

    def test_safe_realizer_receipt_is_frozen(self, safe_realizer):
        """SafeRealizer receipts are frozen."""
        receipt = safe_realizer.realize(failure_meaning("unknown"))
        with pytest.raises((AttributeError, Exception)):
            receipt.status = "realized"

    def test_safe_realizer_has_equivalence_receipt(self, safe_realizer):
        """SafeRealizer receipts carry equivalence receipts."""
        receipt = safe_realizer.realize(failure_meaning("unknown"))
        assert receipt.equivalence_receipt is not None
        assert receipt.equivalence_receipt.equivalent
