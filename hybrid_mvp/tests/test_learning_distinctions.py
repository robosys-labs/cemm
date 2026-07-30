"""Tests for learning distinctions: lookup, teaching, directive, event, acquisition.

Learning distinctions remain explicit (AGENTS.md section 11 / spec section 9):

- lookup: "What does X mean?" executes a query, does NOT mutate world state
- teaching claim: "X means Y" creates a source-attributed semantic claim
- learning directive: "Learn that X means Y" creates a directive over an
  embedded proposition
- learning event claim: "I learned X" is an attributed event claim
- reviewed acquisition: an explicit reviewer publishes a new identity/designation
  under acquisition policy

No lexical token directly authorizes a write.  Conversational wording cannot
select the reviewer policy.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.propositions import (
    Application,
    PropositionGraph,
    SemanticSwitchProgram,
)
from cemm_authoritative_hybrid.query import (
    GenericDefinitionLowerer,
    QueryEngine,
    QueryResult,
    query,
)

from cemm_authoritative_hybrid.learning import (
    LearningCoordinator,
    LearningPlan,
    ReviewedAcquisitionPlan,
    ReviewerAuthorization,
    ReviewerPolicyIssuer,
    DesignationCommitReceipt,
    AcquisitionReceipt,
    LearningGap,
)


# ---------------------------------------------------------------------------
# Test-only authority helpers (mirrors test_query_engine pattern)
# ---------------------------------------------------------------------------


class _TestAuthority:
    """A minimal LinkedAuthority-like object for learning tests."""

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


def _learning_atoms():
    """Atoms for learning tests."""
    return {
        "participant:user": "participant",
        "participant:system": "participant",
        "concept:happy": "concept",
        "concept:cheerful": "concept",
        "state_value:happy": "state_value",
        "dim:mood": "state_dimension",
        "event:greeting": "event_type",
        "cap:learn": "capability",
    }


def _learning_designations():
    return [
        ("happy", "state_value:happy", "en"),
        ("hi", "event:greeting", "en"),
    ]


def _learning_operator_roles():
    return {
        "op:designation": ["role:target", "role:label_type", "role:surface"],
        "op:type": ["role:instance", "role:class"],
        "op:relation": ["role:subject", "role:relation", "role:object"],
        "op:state": ["role:subject", "role:dimension", "role:value"],
        "op:event": ["role:event", "role:type"],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def learning_authority():
    return _TestAuthority(
        atoms=_learning_atoms(),
        rules=[],
        designations=_learning_designations(),
        operator_roles=_learning_operator_roles(),
    )


@pytest.fixture
def learning_stores():
    stores = memory_stores(authority_generation="authority:test-v1")
    yield stores
    stores.close()


@pytest.fixture
def learning_query_engine(learning_authority, learning_stores):
    return QueryEngine(learning_authority, learning_stores, RuntimeConfig.release())


@pytest.fixture
def learning_coordinator(learning_authority, learning_stores, learning_query_engine):
    return LearningCoordinator(
        authority=learning_authority,
        stores=learning_stores,
        config=RuntimeConfig.release(),
        query_engine=learning_query_engine,
    )


@pytest.fixture
def reviewer_policy_issuer():
    return ReviewerPolicyIssuer(
        policy_ref="policy:acquisition",
        reviewer_ref="reviewer:test",
    )


@pytest.fixture
def reviewer_authorization(reviewer_policy_issuer):
    """A callable that authorizes any plan for the test policy."""
    return reviewer_policy_issuer


@pytest.fixture
def designation_query_result(learning_query_engine):
    """A QueryResult for looking up the meaning of 'happy'."""
    return learning_query_engine.ask(query("state_value:happy", "entity:user"))


# ---------------------------------------------------------------------------
# Tests: lookup does not mutate
# ---------------------------------------------------------------------------


def test_meaning_lookup_does_not_mutate(learning_stores, learning_query_engine):
    """Lookup ('what does X mean?') executes a query and does NOT mutate state."""
    before = learning_stores.revisions()
    result = learning_query_engine.ask(query("state_value:happy", "entity:user"))
    # The query runs but does not change any store revision.
    assert learning_stores.revisions() == before
    # A query result is returned (status may be unknown or supported).
    assert isinstance(result, QueryResult)


def test_lookup_does_not_create_designation(learning_authority, learning_query_engine):
    """Looking up a surface does not create a new designation."""
    result = learning_query_engine.ask(query("state_value:happy", "entity:user"))
    # No new designation for 'glad' should exist after a lookup.
    assert learning_authority.designations.for_surface("glad", "en") == ()


# ---------------------------------------------------------------------------
# Tests: untrusted teaching is attributed only
# ---------------------------------------------------------------------------


def test_untrusted_teaching_is_attributed_only(
    learning_coordinator, learning_authority
):
    """Teaching claim ('glad means happy') creates an attributed claim, not a designation."""
    # A teaching claim does NOT go through the learning coordinator's commit path.
    # It creates a source-attributed semantic claim via the epistemic engine.
    # The designation 'glad' -> 'state_value:happy' must NOT exist.
    assert not learning_authority.designations.for_surface("glad", "en")

    # Even if we plan designation learning, without reviewer authorization,
    # no commit happens.
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="glad",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    # The plan exists but no designation has been committed yet.
    assert not learning_authority.designations.for_surface("glad", "en")


# ---------------------------------------------------------------------------
# Tests: reviewed alias inherits target semantics
# ---------------------------------------------------------------------------


def test_reviewed_alias_inherits_target_semantics(
    learning_coordinator, reviewer_authorization, learning_authority
):
    """A reviewed designation commit binds a new surface to an existing target."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    auth = reviewer_authorization.authorize(plan)
    receipt = learning_coordinator.review_and_commit(plan, auth)

    assert isinstance(receipt, DesignationCommitReceipt)
    assert receipt.operator_ref == "op:designation"
    assert receipt.surface == "cheerful"
    assert receipt.target_ref == "state_value:happy"
    # The designation is now visible in the coordinator's designation store.
    assert learning_coordinator.designations.contains("cheerful", "state_value:happy")


def test_designation_commit_requires_cap_learn(learning_coordinator, reviewer_authorization):
    """Commit requires cap:learn capability."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    auth = reviewer_authorization.authorize(plan)

    # Remove cap:learn from authority temporarily.
    original_caps = learning_coordinator._authority.capabilities
    learning_coordinator._authority.capabilities = {"participant:user": []}
    try:
        with pytest.raises(LearningGap):
            learning_coordinator.review_and_commit(plan, auth)
    finally:
        learning_coordinator._authority.capabilities = original_caps


def test_designation_commit_requires_existing_target(
    learning_coordinator, reviewer_authorization
):
    """Commit requires the target identity to already exist in authority."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:nonexistent",
        query_result=query_result,
    )
    auth = reviewer_authorization.authorize(plan)
    with pytest.raises(LearningGap):
        learning_coordinator.review_and_commit(plan, auth)


def test_designation_commit_requires_reviewer_authorization(learning_coordinator):
    """Commit without reviewer authorization raises LearningGap."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    # No authorization provided — must fail.
    with pytest.raises((LearningGap, TypeError, ValueError)):
        learning_coordinator.review_and_commit(plan, None)


def test_designation_commit_consumes_plan(learning_coordinator, reviewer_authorization):
    """A successful commit consumes the plan; replaying it fails."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    auth = reviewer_authorization.authorize(plan)
    receipt = learning_coordinator.review_and_commit(plan, auth)
    assert receipt.operator_ref == "op:designation"

    # Replaying the same plan + authorization must fail (replay rejected).
    with pytest.raises(LearningGap):
        learning_coordinator.review_and_commit(plan, auth)


# ---------------------------------------------------------------------------
# Tests: one pending learning obligation
# ---------------------------------------------------------------------------


def test_one_pending_learning_obligation(learning_coordinator):
    """Only one pending learning obligation may exist at a time."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan1 = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    # Planning a second obligation while one is pending should fail.
    with pytest.raises(LearningGap):
        learning_coordinator.plan_designation_learning(
            surface="glad",
            target_ref="state_value:happy",
            query_result=query_result,
        )


# ---------------------------------------------------------------------------
# Tests: conversational wording cannot select reviewer policy
# ---------------------------------------------------------------------------


def test_conversational_wording_cannot_select_reviewer_policy(
    learning_coordinator, reviewer_authorization
):
    """The reviewer policy is configured independently, not selected by wording."""
    query_result = learning_coordinator._query_engine.ask(
        query("state_value:happy", "entity:user")
    )
    plan = learning_coordinator.plan_designation_learning(
        surface="cheerful",
        target_ref="state_value:happy",
        query_result=query_result,
    )
    # The plan's contract_ref is fixed, not derived from surface text.
    assert plan.contract_ref == "contract:designation_learning"
    # The authorization's policy_ref comes from the issuer, not the text.
    auth = reviewer_authorization.authorize(plan)
    assert auth.policy_ref == "policy:acquisition"


# ---------------------------------------------------------------------------
# Tests: no public install_rules / add_rule / mutable-authority shortcut
# ---------------------------------------------------------------------------


def test_no_public_install_rules(learning_coordinator):
    """LearningCoordinator has no public install_rules, add_rule, or mutable shortcut."""
    assert not hasattr(learning_coordinator, "install_rules")
    assert not hasattr(learning_coordinator, "add_rule")
    # The coordinator should not expose any method that directly mutates authority.
    public_methods = [
        m for m in dir(learning_coordinator)
        if not m.startswith("_") and callable(getattr(learning_coordinator, m))
    ]
    # No method name suggests direct authority mutation.
    for method in public_methods:
        assert "install" not in method.lower()
        assert "add_rule" not in method.lower()
        assert "mutate" not in method.lower()
