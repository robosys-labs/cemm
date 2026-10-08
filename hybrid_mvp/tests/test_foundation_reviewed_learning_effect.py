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
import sqlite3

from cemm_authoritative_hybrid.foundation import FoundationTurn, load_foundation
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.persistence import StaleRevisionError
from cemm_authoritative_hybrid.reviewed_learning import (
    ReviewerIssuer, ReviewerVerifier,
)
from cemm_authoritative_hybrid.r3_effects import EffectStatus, NoEffectReason
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

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
        audit = runtime.stores.r3_effect_journal_get(effect.idempotency_key)
        assert audit is not None
        signed = audit["entry"]["request_payload"]["signed_review"]
        assert signed == {**approval.signing_fields(), "signature": approval.signature}
        assert "foundation-test-reviewer-key" not in str(audit)
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
        assert response.learning_plan.expires_at_turn == 6
        approval = _approval(requested)
        for _ in range(4):
            runtime.process(session, "hello")  # Turn 6: pending plan expired.
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


def test_signed_novel_entity_designation_transfers_to_evidence_query(tmp_path):
    """No new parse rule, corpus rebuild or meaning owner for the novel word."""
    runtime = _runtime(tmp_path)
    session = "session:compositional-new-designation"
    try:
        unknown = runtime.process(session, "Who owns the tome?")
        assert unknown.verify()
        assert unknown.cycle.verification.status != "selected"
        turn = runtime.process(session, "learn tome means book")
        assert turn.verify()
        response = turn.cycle.response_meaning
        assert response is not None and response.learning_plan is not None
        assert response.learning_plan.target_ref == "entity:book"
        effect = runtime.approve_reviewed_learning(
            turn, _approval(turn), ReviewerVerifier({REVIEWER: KEY}),
            now=NOW + 2,
        )
        assert effect.status is EffectStatus.COMMITTED
        fact = Fact(
            fact_ref="fact:independent-reviewed-ownership",
            operator="op:relation",
            args={
                "predicate_ref": "rel:owns",
                "role:subject": "entity:alice",
                "role:object": "entity:book",
            },
            proof={
                "source": "source:independent-reviewed-ownership",
                "placement": "observed",
            },
        )
        install_reviewed_world_facts(runtime.stores, facts=(fact,))
        verified = runtime.process(session, "Who owns the tome?")
        assert verified.verify()
        answer = verified.cycle.response_meaning
        assert answer is not None and answer.discourse_action == "answer"
        assert ("?v0", "entity:alice") in answer.bindings
        assert "source:independent-reviewed-ownership" in answer.source_refs
    finally:
        runtime.close()

    restarted = _runtime(tmp_path)
    try:
        followup = restarted.process(session, "Who owns the tome?")
        assert followup.verify()
        assert ("?v0", "entity:alice") in followup.cycle.response_meaning.bindings
    finally:
        restarted.close()


def test_second_pending_learning_request_must_not_create_another_obligation(tmp_path):
    runtime = _runtime(tmp_path)
    session = "session:one-learning-obligation"
    try:
        original = runtime.process(session, "learn lumo means hello")
        response = original.cycle.response_meaning
        assert response is not None and response.learning_plan is not None
        assert runtime.stores.obligations.get(response.obligation_ref)["resolved"] is False
        second = runtime.process(session, "learn zora means hello")
        assert second.verify()
        second_response = second.cycle.response_meaning
        assert second_response is not None
        assert second_response.learning_plan is None
        assert "learning:pending_obligation_exists" in second_response.blocker_refs
    finally:
        runtime.close()


def test_expired_learning_does_not_block_later_review_requests(tmp_path):
    runtime = _runtime(tmp_path)
    session = "session:expired-learning-followup"
    try:
        first = runtime.process(session, "learn lumo means hello")
        plan = first.cycle.response_meaning.learning_plan
        assert plan is not None and plan.expires_at_turn == 5
        for _ in range(3):
            runtime.process(session, "hello")
        replacement = runtime.process(session, "learn zora means hello")
        assert replacement.verify()
        response = replacement.cycle.response_meaning
        assert response is not None and response.learning_plan is not None
        assert response.learning_plan.surface_literal == "zora"
        assert response.learning_plan.plan_ref != plan.plan_ref
    finally:
        runtime.close()


def test_transaction_rollback_leaves_no_nonce_alias_or_effect(tmp_path):
    """A SQLite failure after nonce and index insertion must roll back ALL work."""
    runtime = _runtime(tmp_path)
    try:
        request = runtime.process("session:rollback", "learn veza means hello")
        response = request.cycle.response_meaning
        assert response is not None and response.learning_plan is not None
        approval = _approval(request)
        verifier = ReviewerVerifier({REVIEWER: KEY})
        before = runtime.stores.revision_pin()
        conn = runtime.stores._backend._conn
        conn.execute(
            "CREATE TRIGGER fail_reviewed_alias BEFORE INSERT ON world_facts "
            "BEGIN SELECT RAISE(ABORT, 'simulated atomic write failure'); END"
        )
        with pytest.raises(sqlite3.DatabaseError, match="simulated atomic"):
            runtime.approve_reviewed_learning(
                request, approval, verifier, now=NOW + 4,
            )
        conn.execute("DROP TRIGGER fail_reviewed_alias")
        assert runtime.stores.revision_pin() == before
        assert runtime.stores.obligations.get(response.obligation_ref)["resolved"] is False
        assert runtime.stores.r3_reviewed_designation_for_surface("veza") is None
        pending_effect_key = stable_ref(
            "reviewed_learning_effect_key",
            {"plan_ref": response.learning_plan.plan_ref},
        )
        assert runtime.stores.r3_effect_journal_get(pending_effect_key) is None

        # A failed transaction does not burn the signed nonce or the plan.
        accepted = runtime.approve_reviewed_learning(
            request, approval, verifier, now=NOW + 5,
        )
        assert accepted.status is EffectStatus.COMMITTED
    finally:
        runtime.close()


def test_two_open_store_connections_cannot_commit_one_review_twice(tmp_path):
    primary = _runtime(tmp_path)
    try:
        request = primary.process("session:concurrent", "learn kiyo means hello")
        approval = _approval(request)
        verifier = ReviewerVerifier({REVIEWER: KEY})
        secondary = _runtime(tmp_path)
        try:
            accepted = primary.approve_reviewed_learning(
                request, approval, verifier, now=NOW + 3,
            )
            assert accepted.status is EffectStatus.COMMITTED
            with pytest.raises((StaleRevisionError, ValueError)):
                secondary.approve_reviewed_learning(
                    request, approval, verifier, now=NOW + 4,
                )
        finally:
            secondary.close()
        assert primary.stores.r3_reviewed_designation_for_surface("kiyo") is not None
    finally:
        primary.close()


def test_signed_review_handoff_recovers_after_process_restart(tmp_path):
    """A lost application process must not lose its pending learning proof."""
    import json

    first = _runtime(tmp_path)
    try:
        original = first.process(
            "session:durable-review-handoff", "learn zuno means hello"
        )
        pending = json.dumps(original.to_wire(), sort_keys=True)
        approval = _approval(original)
        assert first.stores.obligations.get(
            original.cycle.response_meaning.obligation_ref
        )["resolved"] is False
    finally:
        first.close()

    second = _runtime(tmp_path)
    try:
        recovered = FoundationTurn.from_wire(json.loads(pending))
        assert recovered.verify()
        completed = second.approve_reviewed_learning(
            recovered, approval, ReviewerVerifier({REVIEWER: KEY}),
            now=NOW + 5,
        )
        assert completed.status is EffectStatus.COMMITTED
        assert second.process(
            "session:durable-review-handoff", "zuno",
        ).cycle.verification.status == "selected"
    finally:
        second.close()
