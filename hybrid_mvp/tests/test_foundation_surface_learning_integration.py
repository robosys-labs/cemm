"""End-to-end proof: reviewed learning -> cross-surface meaning -> read-only verification.

No template matching, legacy phrase dispatch or generated gold. The expected
relation is independently established by reviewed world evidence, while two
different source surfaces must independently reparse to its same canonical
expression and leave durable memory untouched.
"""
from pathlib import Path

from cemm_authoritative_hybrid.foundation import FoundationTurn, load_foundation
from cemm_authoritative_hybrid.reviewed_learning import ReviewerIssuer, ReviewerVerifier
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = "reviewer:roundtrip"
KEY = b"independently-provisioned-reviewer-key-for-tests-2026"
NOW = 1_700_000_000


def _runtime(tmp_path):
    return load_foundation(
        ROOT, store_path=tmp_path / "semantic-roundtrip",
        reviewer_verifier=ReviewerVerifier({REVIEWER: KEY}),
        review_clock=lambda: NOW + 10,
    )


def test_live_approved_alias_is_semantically_equivalent_on_different_answer_surfaces(tmp_path):
    foundation = _runtime(tmp_path)
    try:
        request = foundation.process("session:meaning-learning", "learn tome means book")
        response = request.cycle.response_meaning
        assert response.learning_plan is not None
        assert response.learning_plan.target_ref == "entity:book"
        signature = ReviewerIssuer(REVIEWER, KEY).approve(
            plan_ref=response.learning_plan.plan_ref,
            obligation_ref=response.obligation_ref,
            source_effect_ref=request.cycle.effect_receipt.receipt_ref,
            session_ref=response.obligation.session_ref,
            issued_at=NOW,
        )
        effect = foundation.approve_reviewed_learning(
            request, signature,
        )
        assert effect.status.value == "committed"
        install_reviewed_world_facts(
            foundation.stores,
            facts=(Fact(
                fact_ref="fact:independent-ownership",
                operator="op:relation",
                args={
                    "predicate_ref": "rel:owns",
                    "role:subject": "entity:alice",
                    "role:object": "entity:book",
                },
                proof={
                    "source": "source:reviewed-independent-ownership",
                    "placement": "observed",
                },
            ),),
        )
        query = foundation.process(
            "session:meaning-learning", "Who owns the tome?",
        )
        assert query.verify()
        assert query.cycle.response_meaning.discourse_action == "answer"
        old = foundation.stores.revision_pin()
        generated = foundation.generate_reference_english(query)
        assert generated.status == "verified"
        assert generated.surface == "Alice owns the book."
        assert generated.proof_refs == query.cycle.response_meaning.proof_refs
        assert generated.assessment is not None and generated.assessment.equivalent
        learned = foundation.assess_english_surface(query, "Alice owns the tome.")
        original = foundation.assess_english_surface(query, "Alice owns the book.")
        assert learned.equivalent, learned
        assert original.equivalent, original
        assert learned.parsed_expression_ref == original.parsed_expression_ref
        assert foundation.stores.revision_pin() == old
        assert not foundation.assess_english_surface(
            query, "Bob owns the tome."
        ).equivalent
        handoff = query.to_wire()
    finally:
        foundation.close()

    reopened = _runtime(tmp_path)
    try:
        recovered = FoundationTurn.from_wire(handoff)
        assert recovered.verify()
        old = reopened.stores.revision_pin()
        result = reopened.assess_english_surface(
            recovered, "Alice owns the tome.",
        )
        assert result.equivalent, result
        regenerated = reopened.generate_reference_english(recovered)
        assert regenerated.status == "verified"
        assert regenerated.surface == generated.surface
        assert regenerated.proof_refs == generated.proof_refs
        assert reopened.stores.revision_pin() == old
    finally:
        reopened.close()
