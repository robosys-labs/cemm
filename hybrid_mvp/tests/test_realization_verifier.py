"""Tests for the independent realization equivalence verifier.

Verifies that the RealizationVerifier:
- Rejects flipped polarity with mismatch_codes == ("polarity",)
- Accepts correct surfaces
- Rejects internal semantic refs in surface
- Rejects empty output for authorized response actions
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.realization import (
    EquivalenceReceipt,
    RealizationVerifier,
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def realization_verifier():
    """A RealizationVerifier for testing."""
    return RealizationVerifier()


@pytest.fixture
def supported_answer():
    """A ResponseMeaning for a supported positive answer."""
    return _make_response_meaning(
        discourse_action="answer",
        polarity="positive",
        epistemic_status="supported",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRealizationVerifier:
    def test_flipped_polarity_is_rejected(self, realization_verifier, supported_answer):
        """A negative surface for a positive response contract is rejected."""
        result = realization_verifier.verify(
            supported_answer, "No, that is not supported."
        )
        assert not result.equivalent
        assert result.mismatch_codes == ("polarity",)

    def test_correct_positive_answer_is_accepted(self, realization_verifier, supported_answer):
        """A correct positive surface passes verification."""
        result = realization_verifier.verify(supported_answer, "My name is CEMM.")
        assert result.equivalent
        assert result.mismatch_codes == ()

    def test_internal_refs_are_rejected(self, realization_verifier, supported_answer):
        """Internal semantic refs in surface are rejected."""
        result = realization_verifier.verify(
            supported_answer, "My name is concept:system."
        )
        assert not result.equivalent
        assert "internal_refs" in result.mismatch_codes

    def test_empty_output_is_rejected_for_answer(self, realization_verifier, supported_answer):
        """Empty output is rejected for authorized response actions."""
        result = realization_verifier.verify(supported_answer, "")
        assert not result.equivalent
        assert "empty_output" in result.mismatch_codes

    def test_negative_answer_is_accepted(self, realization_verifier):
        """A negative surface for a negative response contract is accepted."""
        rm = _make_response_meaning(
            discourse_action="answer",
            polarity="negative",
            epistemic_status="supported",
        )
        result = realization_verifier.verify(rm, "No, that is not supported.")
        assert result.equivalent

    def test_unknown_discourse_action_matches(self, realization_verifier):
        """Unknown discourse action requires unknown surface markers."""
        rm = _make_response_meaning(
            discourse_action="unknown",
            epistemic_status="unknown",
            status="unknown",
        )
        result = realization_verifier.verify(rm, "I do not know.")
        assert result.equivalent

    def test_deny_discourse_action_matches(self, realization_verifier):
        """Deny discourse action requires denial surface markers."""
        rm = _make_response_meaning(
            discourse_action="deny",
            polarity="negative",
            epistemic_status="denied",
            status="denied",
            mode="REQUEST",
        )
        result = realization_verifier.verify(rm, "That is not permitted.")
        assert result.equivalent

    def test_equivalence_receipt_is_frozen(self):
        """EquivalenceReceipt is a frozen dataclass."""
        receipt = EquivalenceReceipt(equivalent=True, mismatch_codes=())
        with pytest.raises((AttributeError, Exception)):
            receipt.equivalent = False
