"""Tests for learning security: poisoning, replay, ambiguity, and expiry.

Each adversarial case must produce a learning or permission gap without
mutation.  No lexical token directly authorizes a write.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.query import (
    GenericDefinitionLowerer,
    QueryEngine,
    query,
)

from cemm_authoritative_hybrid.learning import (
    LearningCoordinator,
    LearningPlan,
    ReviewerAuthorization,
    ReviewerPolicyIssuer,
    DesignationCommitReceipt,
    LearningGap,
)


# ---------------------------------------------------------------------------
# Test-only authority helper
# ---------------------------------------------------------------------------


class _TestAuthority:
    """A minimal LinkedAuthority-like object for learning security tests."""

    def __init__(self, atoms, rules, designations, operator_roles=None):
        from cemm_authoritative_hybrid.authority import (
            DesignationIndex,
            AtomRecord,
            RuleRecord,
        )

        self.atoms = {
            ref: AtomRecord(ref=ref, kind=kind) for ref, kind in atoms.items()
        }
        self.rules = {r.rule_ref: r for r in rules}
        self.generation = "authority:test-v1"
        self.content_hash = "test-content-hash"
        self.model_compatibility_hash = "test-compat-hash"
        self.capabilities = {"participant:user": ["cap:learn"]}
        self.permissions = ()
        self.adapters = ()
        self.value_dimensions = {}
        self.operator_roles = operator_roles or {
            "op:designation": ["role:target", "role:label_type", "role:surface"],
            "op:type": ["role:instance", "role:class"],
            "op:relation": ["role:subject", "role:relation", "role:object"],
            "op:state": ["role:subject", "role:dimension", "role:value"],
            "op:event": ["role:event", "role:type"],
        }
        self.event_signatures = {}

        by_surface = {}
        by_target = {}
        for surface, target, lang in designations:
            by_surface.setdefault((surface, lang), []).append(target)
            by_target.setdefault((target, lang), []).append(surface)
        self.designations = DesignationIndex(
            {k: tuple(v) for k, v in by_surface.items()},
            {k: tuple(v) for k, v in by_target.items()},
        )

    def by_kind(self, kind):
        return frozenset(
            ref for ref, atom in self.atoms.items() if atom.kind == kind
        )

    def by_rule_signature(self, rule_ref):
        return None

    def by_state_dimension(self, dim):
        return frozenset()

    def by_event_signature(self, et):
        return None

    def by_transition(self, key):
        return None

    def by_frame(self, frame):
        return frozenset()


def _security_atoms():
    return {
        "participant:user": "participant",
        "participant:system": "participant",
        "state_value:happy": "state_value",
        "state_value:sad": "state_value",
        "concept:person": "concept",
        "dim:mood": "state_dimension",
        "cap:learn": "capability",
    }


def _security_designations():
    return [
        ("happy", "state_value:happy", "en"),
        ("sad", "state_value:sad", "en"),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def security_authority():
    return _TestAuthority(
        atoms=_security_atoms(),
        rules=[],
        designations=_security_designations(),
    )


@pytest.fixture
def security_stores():
    stores = memory_stores(authority_generation="authority:test-v1")
    yield stores
    stores.close()


@pytest.fixture
def security_query_engine(security_authority, security_stores):
    return QueryEngine(security_authority, security_stores, RuntimeConfig.release())


@pytest.fixture
def security_coordinator(security_authority, security_stores, security_query_engine):
    return LearningCoordinator(
        authority=security_authority,
        stores=security_stores,
        config=RuntimeConfig.release(),
        query_engine=security_query_engine,
    )


@pytest.fixture
def security_issuer():
    return ReviewerPolicyIssuer(
        policy_ref="policy:acquisition",
        reviewer_ref="reviewer:security",
    )


# ---------------------------------------------------------------------------
# Tests: target-kind mismatch
# ---------------------------------------------------------------------------


def test_target_kind_mismatch_rejected(security_coordinator, security_issuer):
    """A target-kind mismatch produces a learning gap without mutation."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="concept:person",  # wrong kind for a state_value designation
        query_result=query_result,
        expected_target_kinds=("state_value",),
    )
    auth = security_issuer.authorize(plan)
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)
    assert not security_coordinator.designations.contains("cheerful", "concept:person")


# ---------------------------------------------------------------------------
# Tests: expired plan
# ---------------------------------------------------------------------------


def test_expired_plan_rejected(security_coordinator, security_issuer):
    """An expired plan cannot be committed."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
        expires_at_turn=0,  # already expired
    )
    auth = security_issuer.authorize(plan)
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)
    assert not security_coordinator.designations.contains("cheerful", "state_value:happy")


# ---------------------------------------------------------------------------
# Tests: replayed authorization
# ---------------------------------------------------------------------------


def test_replayed_authorization_rejected(security_coordinator, security_issuer):
    """Replaying the same authorization for a second commit fails."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    auth = security_issuer.authorize(plan)
    receipt = security_coordinator.review_and_commit(plan, auth)
    assert receipt.operator_ref == "op:designation"

    # Replaying the same authorization must fail.
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)


# ---------------------------------------------------------------------------
# Tests: authorization from another session / plan mismatch
# ---------------------------------------------------------------------------


def test_authorization_plan_mismatch_rejected(security_coordinator, security_issuer):
    """An authorization bound to a different plan_ref is rejected."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    # Create an authorization for a different plan_ref.
    auth = ReviewerAuthorization(
        reviewer_ref="reviewer:security",
        policy_ref="policy:acquisition",
        plan_ref="plan:different",
        decision="approve",
        nonce="nonce-different",
        expires_at=999,
    )
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)
    assert not security_coordinator.designations.contains("cheerful", "state_value:happy")


# ---------------------------------------------------------------------------
# Tests: internal-ref lexicalization rejected
# ---------------------------------------------------------------------------


def test_internal_ref_lexicalization_rejected(security_coordinator, security_issuer):
    """Attempting to lexicalize an internal ref as a surface is rejected."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    # The surface is an internal ref spelling — this must be rejected at
    # plan time, before any authorization is even issued.
    with pytest.raises(LearningGap):
        security_coordinator.plan_designation_learning(
            surface="state_value:happy",
            target_ref="state_value:happy",
            query_result=query_result,
        )
    # No designation was committed.
    assert not security_coordinator.designations.contains("state_value:happy", "state_value:happy")


# ---------------------------------------------------------------------------
# Tests: direct "trust me" escalation rejected
# ---------------------------------------------------------------------------


def test_trust_me_escalation_rejected(security_coordinator):
    """A direct 'trust me' (no typed authorization) cannot commit."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    # No authorization at all — must fail.
    with pytest.raises((LearningGap, TypeError, ValueError)):
        security_coordinator.review_and_commit(plan, None)


# ---------------------------------------------------------------------------
# Tests: wrong decision in authorization
# ---------------------------------------------------------------------------


def test_wrong_decision_rejected(security_coordinator, security_issuer):
    """An authorization with decision != 'approve' is rejected."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    auth = ReviewerAuthorization(
        reviewer_ref="reviewer:security",
        policy_ref="policy:acquisition",
        plan_ref=plan.plan_ref,
        decision="deny",
        nonce="nonce-deny",
        expires_at=999,
    )
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)


# ---------------------------------------------------------------------------
# Tests: expired authorization
# ---------------------------------------------------------------------------


def test_expired_authorization_rejected(security_coordinator, security_issuer):
    """An authorization that has expired is rejected."""
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    auth = ReviewerAuthorization(
        reviewer_ref="reviewer:security",
        policy_ref="policy:acquisition",
        plan_ref=plan.plan_ref,
        decision="approve",
        nonce="nonce-expired",
        expires_at=0,  # expired
    )
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)


# ---------------------------------------------------------------------------
# Tests: no mutation on failure
# ---------------------------------------------------------------------------


def test_failed_commit_does_not_mutate(security_coordinator, security_issuer):
    """A failed commit does not change any store revision."""
    before = security_coordinator._stores.revisions()
    query_result = security_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = security_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:nonexistent",
        query_result=query_result,
    )
    auth = security_issuer.authorize(plan)
    with pytest.raises(LearningGap):
        security_coordinator.review_and_commit(plan, auth)
    assert security_coordinator._stores.revisions() == before
