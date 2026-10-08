"""Real text -> reviewed R3 learning plan -> signed effect -> reusable knowledge.

Reviewer signatures are supplied by an independent trusted issuer and bound
to the source R3 NoEffectReceipt. This does not use any autonomous authority,
chat-generated credentials, fixtures injected into decision owners, or legacy
Stage 0-22 learning.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.reviewed_learning import (
    ReviewerIssuer, ReviewerVerifier,
)
from cemm_authoritative_hybrid.r3_effects import EffectStatus, NoEffectReason

ROOT = Path(__file__).resolve().parents[1]
KEY = b"foundation-test-reviewer-key-keep-out-of-repository"
REVIEWER = "reviewer:independent-approver"
NOW = 1_700_000_000


def _approval(turn, *, reviewer=REVIEWER, key=KEY):
    response = turn.cycle.response_meaning
    assert response is not None and response.learning_plan is not None
    plan = response.learning_plan
    source_receipt = turn.cycle.effect_receipt
    assert source_receipt.reason is NoEffectReason.LEARNING_OBLIGATION_ONLY
    issuer = ReviewerIssuer(reviewer, key)
    return issuer.approve(
        plan_ref=plan.plan_ref,
        obligation_ref=response.obligation_ref,
        source_effect_ref=source_receipt.receipt_ref,
        session_ref=response.obligation.session_ref,
        issued_at=NOW,
    )


def _runtime(tmp_path):
    return load_foundation(ROOT, store_path=tmp_path / "reviewed-learning")


def test_real_request_review_commit_new_lexical_meaning_and_restart(tmp_path):
    runtime = _runtime(tmp_path)
    session = "session:reviewed-cognition"
    try:
        unknown = runtime.process(session, "yoz")
        assert unknown.verify()
        assert unknown.cycle.verification.status != "selected"
        before = runtime.stores.revision_pin()
        requested = runtime.process(session, "learn yoz means hello")
        assert requested.verify()
        response = requested.cycle.response_meaning
        assert response is not None and response.learning_plan is not None
        assert response.learning_plan.surface_literal == "yoz"
        assert response.learning_plan.target_ref == "event:greeting"
        assert requested.cycle.evaluation.decision.action.value == "create_learning_obligation"
        assert runtime.stores.obligations.get(response.obligation_ref)["resolved"] is False
        pending_world = runtime.stores.revision_pin().world_revision
        assert pending_world == before.world_revision

        approval = _approval(requested)
        verifier = ReviewerVerifier({REVIEWER: KEY})
        effect = runtime.approve_reviewed_learning(
            requested, approval, verifier, now=NOW + 10,
        )
        assert effect.status is EffectStatus.COMMITTED
        assert effect.committed_fact_refs
        assert effect.operation_receipt_ref == approval.approval_ref
        assert runtime.stores.revision_pin() == effect.output_revision_pin
        assert runtime.stores.obligations.get(response.obligation_ref)["resolved"] is True
        assert runtime.stores.r3_reviewed_designation_for_surface("yoz") == {
            "surface": "yoz", "target_ref": "event:greeting", "language": "en",
        }
        actual = runtime.process(session, "yoz")
        assert actual.verify()
        assert actual.cycle.verification.status == "selected"
        assert any(
            app.predicate_ref == "event:greeting"
            for app in actual.cycle.verification.selected_meaning.expression.applications
        )
        with pytest.raises((ValueError, PermissionError)):
            runtime.approve_reviewed_learning(
                requested, approval, verifier, now=NOW + 11,
            )
    finally:
        runtime.close()

    restarted = _runtime(tmp_path)
    try:
        result = restarted.process(session, "yoz")
        assert result.verify()
        assert result.cycle.verification.status == "selected"
        assert restarted.stores.r3_reviewed_designation_for_surface("YOZ")["target_ref"] == "event:greeting"
    finally:
        restarted.close()


def test_forged_reviewer_or_changed_plan_cannot_write_or_resolve_obligation(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        requested = runtime.process(
            "session:untrusted-reviewer", "learn luminous means hello"
        )
        assert requested.verify()
        response = requested.cycle.response_meaning
        assert response is not None and response.learning_plan is not None
        approval = _approval(requested)
        verifier = ReviewerVerifier({REVIEWER: KEY})
        baseline = runtime.stores.revision_pin()
        bad_review = replace(
            approval, plan_ref="learning_plan:forged",
        )
        with pytest.raises(PermissionError):
            runtime.approve_reviewed_learning(
                requested, bad_review, verifier, now=NOW + 5,
            )
        with pytest.raises(PermissionError):
            runtime.approve_reviewed_learning(
                requested, approval, ReviewerVerifier({
                    REVIEWER: b"unrelated-deployment-signing-key-value-12345"
                }), now=NOW + 5,
            )
        with pytest.raises(PermissionError):
            runtime.approve_reviewed_learning(
                requested, approval, verifier, now=NOW + 1000,
            )
        assert runtime.stores.revision_pin() == baseline
        assert runtime.stores.obligations.get(response.obligation_ref)["resolved"] is False
        assert runtime.stores.r3_reviewed_designation_for_surface("luminous") is None
    finally:
        runtime.close()


def test_unsigned_conversational_teaching_never_reaches_approval_effect(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        fact = runtime.process("session:ordinary-speech", "yoz means hello")
        assert fact.verify()
        assert fact.cycle.response_meaning is not None
        assert fact.cycle.response_meaning.learning_plan is None
        assert runtime.stores.r3_reviewed_designation_for_surface("yoz") is None
        with pytest.raises(ValueError):
            runtime.approve_reviewed_learning(
                fact, _approval_like_other_turn(runtime), ReviewerVerifier({
                    REVIEWER: KEY
                }), now=NOW + 5,
            )
    finally:
        runtime.close()


def _approval_like_other_turn(runtime):
    # A valid signature issued for another session still cannot authorize
    # an ordinary attributed sentence without a REQUEST-learning plan.
    request = runtime.process("session:separate-request", "learn lumo means hello")
    return _approval(request)


def test_session_turn_expiry_stops_pending_review_without_partial_write(tmp_path):
    runtime = _runtime(tmp_path)
    session = "session:learning-expiry"
    try:
        runtime.process(session, "hello")
        requested = runtime.process(session, "learn lumo means hello")
        response = requested.cycle.response_meaning
        assert response.learning_plan.expires_at_turn == 3
        approval = _approval(requested)
        runtime.process(session, "hello")  # Now at turn 3, pending plan expired.
        baseline = runtime.stores.revision_pin()
        with pytest.raises(PermissionError, match="expired"):
            runtime.approve_reviewed_learning(
                requested, approval, ReviewerVerifier({REVIEWER: KEY}),
                now=NOW + 5,
            )
        assert runtime.stores.revision_pin() == baseline
        assert runtime.stores.r3_reviewed_designation_for_surface("lumo") is None
    finally:
        runtime.close()
