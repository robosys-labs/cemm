"""Reviewer authorization is independent of conversational content."""
from dataclasses import replace
import pytest

from cemm_authoritative_hybrid.reviewed_learning import (
    ReviewerIssuer, ReviewerVerifier,
)


KEY = b"reviewer-local-only-32-byte-key-and-more!"


def _approved():
    return ReviewerIssuer("reviewer:alice", KEY).approve(
        plan_ref="learning_plan:p",
        obligation_ref="learning_obligation:o",
        source_effect_ref="no_effect_receipt:r",
        session_ref="session:s",
        issued_at=1_000_000,
    )


def test_policy_signature_and_bounded_expiry():
    reviewer = ReviewerVerifier({"reviewer:alice": KEY})
    original = _approved()
    reviewer.verify(original, now=1_000_100)
    for altered in (
        replace(original, plan_ref="learning_plan:forged"),
        replace(original, source_effect_ref="no_effect_receipt:forged"),
        replace(original, obligation_ref="learning_obligation:forged"),
        replace(original, reviewer_ref="reviewer:mallory"),
        replace(original, policy_ref="policy:unauthorized"),
        replace(original, session_ref="session:other"),
    ):
        with pytest.raises(PermissionError):
            reviewer.verify(altered, now=1_000_100)
    with pytest.raises(PermissionError):
        reviewer.verify(original, now=1_001_000)


def test_nonsecret_and_unknown_reviewers_are_rejected():
    with pytest.raises(ValueError):
        ReviewerIssuer("reviewer:alice", b"short")
    with pytest.raises(ValueError):
        ReviewerVerifier({"reviewer:alice": b"weak"})
    with pytest.raises(PermissionError):
        ReviewerVerifier({"reviewer:alice": b"unrelated-reviewer-signing-key-12345"}).verify(
            _approved(), now=1_000_100
        )
