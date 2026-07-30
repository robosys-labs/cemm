"""Tests for reviewed generic definition acquisition and synonym acquisition.

Reviewed acquisition publishes one linked authority generation from verified
semantic programs.  One invalid definition rejects the entire acquisition
(atomic).  Authority compatibility hash is preserved across compatible
acquisitions.
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
    query,
)

from cemm_authoritative_hybrid.learning import (
    LearningCoordinator,
    ReviewedAcquisitionPlan,
    ReviewerAuthorization,
    ReviewerPolicyIssuer,
    AcquisitionReceipt,
    LearningGap,
)
from cemm_authoritative_hybrid.authority import AuthorityLinkError


# ---------------------------------------------------------------------------
# Test-only authority helper
# ---------------------------------------------------------------------------


class _TestAuthority:
    """A minimal LinkedAuthority-like object for acquisition tests."""

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


def _family_atoms():
    """Atoms for the family example: independently designated atoms."""
    return {
        "participant:user": "participant",
        "participant:system": "participant",
        "entity:alice": "entity",
        "entity:bob": "entity",
        "entity:carol": "entity",
        "entity:mary": "entity",
        "concept:mother": "concept",
        "concept:progenitor": "concept",
        "relation:in-law": "relation_type",
        "relation:partner": "relation_type",
        "relation:lawful": "relation_type",
        "relation:wedded": "relation_type",
        "relation:wife": "relation_type",
        "relation:husband": "relation_type",
        "state:married": "state_value",
        "dim:marital_status": "state_dimension",
        "event:arrival": "event_type",
        "event:teach": "event_type",
        "cap:learn": "capability",
    }


def _family_designations():
    return [
        ("alice", "entity:alice", "en"),
        ("bob", "entity:bob", "en"),
        ("carol", "entity:carol", "en"),
        ("mary", "entity:mary", "en"),
        ("mother", "concept:mother", "en"),
        ("progenitor", "concept:progenitor", "en"),
        ("mother-in-law", "relation:in-law", "en"),
        ("partner", "relation:partner", "en"),
        ("lawful", "relation:lawful", "en"),
        ("wedded", "relation:wedded", "en"),
        ("wife", "relation:wife", "en"),
        ("husband", "relation:husband", "en"),
        ("married", "state:married", "en"),
    ]


def _family_operator_roles():
    return {
        "op:designation": ["role:target", "role:label_type", "role:surface"],
        "op:type": ["role:instance", "role:class"],
        "op:relation": ["role:subject", "role:relation", "role:object"],
        "op:state": ["role:subject", "role:dimension", "role:value"],
        "op:event": ["role:event", "role:type"],
    }


def _build_family_teaching_programs():
    """Build five family teaching programs that derive partner/marriage structure."""
    programs = []

    # Lesson 1: mother-in-law → has partner
    ant1 = Application.create(
        "op:relation",
        {"role:subject": "?mother", "role:relation": "concept:mother", "role:object": "?person"},
    )
    ant2 = Application.create(
        "op:relation",
        {"role:subject": "?mother", "role:relation": "relation:in-law", "role:object": "?person"},
    )
    cons = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:partner", "role:object": "$partner"},
    )
    graph = PropositionGraph.create([ant1, ant2, cons], cons.application_ref)
    programs.append(SemanticSwitchProgram.create("OBSERVE", "event:teach", graph))

    # Lesson 2: partner → lawful
    ant1 = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:partner", "role:object": "?partner"},
    )
    cons = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:lawful", "role:object": "?partner"},
    )
    graph = PropositionGraph.create([ant1, cons], cons.application_ref)
    programs.append(SemanticSwitchProgram.create("OBSERVE", "event:teach", graph))

    # Lesson 3: lawful → wedded
    ant1 = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:lawful", "role:object": "?partner"},
    )
    cons = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:wedded", "role:object": "?partner"},
    )
    graph = PropositionGraph.create([ant1, cons], cons.application_ref)
    programs.append(SemanticSwitchProgram.create("OBSERVE", "event:teach", graph))

    # Lesson 4: wedded → married state
    ant1 = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:wedded", "role:object": "?partner"},
    )
    cons = Application.create(
        "op:state",
        {"role:subject": "?person", "role:dimension": "dim:marital_status", "role:value": "state:married"},
    )
    graph = PropositionGraph.create([ant1, cons], cons.application_ref)
    programs.append(SemanticSwitchProgram.create("OBSERVE", "event:teach", graph))

    # Lesson 5: wife/husband → partner
    ant1 = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:wife", "role:object": "?partner"},
    )
    ant2 = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:husband", "role:object": "?partner"},
    )
    cons = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:partner", "role:object": "?partner"},
    )
    graph = PropositionGraph.create([ant1, ant2, cons], cons.application_ref)
    programs.append(SemanticSwitchProgram.create("OBSERVE", "event:teach", graph))

    return programs


def _build_family_programs_with_one_invalid():
    """Build five programs where one has an invalid structure (too few applications)."""
    programs = _build_family_teaching_programs()
    # Replace the third program with an invalid one (only 1 application).
    invalid_app = Application.create(
        "op:relation",
        {"role:subject": "?person", "role:relation": "relation:lawful", "role:object": "?partner"},
    )
    invalid_graph = PropositionGraph.create([invalid_app], invalid_app.application_ref)
    invalid_program = SemanticSwitchProgram.create("OBSERVE", "event:teach", invalid_graph)
    programs[2] = invalid_program
    return programs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def acquisition_authority():
    return _TestAuthority(
        atoms=_family_atoms(),
        rules=[],
        designations=_family_designations(),
        operator_roles=_family_operator_roles(),
    )


@pytest.fixture
def acquisition_stores():
    stores = memory_stores(authority_generation="authority:test-v1")
    yield stores
    stores.close()


@pytest.fixture
def acquisition_query_engine(acquisition_authority, acquisition_stores):
    return QueryEngine(acquisition_authority, acquisition_stores, RuntimeConfig.release())


@pytest.fixture
def learning_coordinator(acquisition_authority, acquisition_stores, acquisition_query_engine):
    return LearningCoordinator(
        authority=acquisition_authority,
        stores=acquisition_stores,
        config=RuntimeConfig.release(),
        query_engine=acquisition_query_engine,
    )


@pytest.fixture
def reviewed_family_programs():
    return tuple(_build_family_teaching_programs())


@pytest.fixture
def family_programs_with_one_invalid():
    return tuple(_build_family_programs_with_one_invalid())


@pytest.fixture
def reviewer_authorization():
    return ReviewerPolicyIssuer(
        policy_ref="policy:acquisition",
        reviewer_ref="reviewer:test",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_reviewed_generic_definitions_publish_one_linked_generation(
    learning_coordinator, reviewed_family_programs, reviewer_authorization
):
    """Reviewed acquisition publishes one linked generation with >= 5 rules."""
    before_compat = learning_coordinator._authority.model_compatibility_hash
    before_gen = learning_coordinator._authority.generation

    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    assert isinstance(plan, ReviewedAcquisitionPlan)
    assert plan.acquisition_kind == "rule"
    assert len(plan.verified_program_refs) >= 5

    receipt = learning_coordinator.review_and_commit_acquisition(
        plan, reviewer_authorization.for_plan(plan)
    )

    assert isinstance(receipt, AcquisitionReceipt)
    assert receipt.parent_generation == before_gen
    assert receipt.new_generation != before_gen
    # Compatibility hash preserved (rules are compatible additions).
    assert receipt.authority_compatibility_hash == before_compat
    assert len(receipt.created_rule_refs) >= 5


def test_one_invalid_definition_rejects_entire_acquisition(
    learning_coordinator, family_programs_with_one_invalid, reviewer_authorization
):
    """One invalid definition rejects the entire acquisition (atomic)."""
    before_gen = learning_coordinator._authority.generation

    plan = learning_coordinator.plan_reviewed_acquisition(
        family_programs_with_one_invalid,
        acquisition_kind="rule",
    )

    with pytest.raises((AuthorityLinkError, LearningGap)):
        learning_coordinator.review_and_commit_acquisition(
            plan,
            reviewer_authorization.for_plan(plan),
        )

    # Generation must not have changed.
    assert learning_coordinator._authority.generation == before_gen


def test_acquisition_requires_reviewer_authorization(
    learning_coordinator, reviewed_family_programs
):
    """Acquisition without reviewer authorization fails."""
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    with pytest.raises((LearningGap, TypeError, ValueError)):
        learning_coordinator.review_and_commit_acquisition(plan, None)


def test_acquisition_requires_cap_learn(
    learning_coordinator, reviewed_family_programs, reviewer_authorization
):
    """Acquisition requires cap:learn capability."""
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    auth = reviewer_authorization.for_plan(plan)

    original_caps = learning_coordinator._authority.capabilities
    learning_coordinator._authority.capabilities = {"participant:user": []}
    try:
        with pytest.raises(LearningGap):
            learning_coordinator.review_and_commit_acquisition(plan, auth)
    finally:
        learning_coordinator._authority.capabilities = original_caps


def test_acquisition_consumes_plan(
    learning_coordinator, reviewed_family_programs, reviewer_authorization
):
    """A successful acquisition consumes the plan; replaying fails."""
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    auth = reviewer_authorization.for_plan(plan)
    receipt = learning_coordinator.review_and_commit_acquisition(plan, auth)
    assert receipt.created_rule_refs

    # Replay must fail.
    with pytest.raises(LearningGap):
        learning_coordinator.review_and_commit_acquisition(plan, auth)


def test_acquisition_plan_mismatch_rejected(
    learning_coordinator, reviewed_family_programs, reviewer_authorization
):
    """An authorization bound to a different plan_ref is rejected."""
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    wrong_auth = ReviewerAuthorization(
        reviewer_ref="reviewer:test",
        policy_ref="policy:acquisition",
        plan_ref="plan:different",
        decision="approve",
        nonce="nonce-wrong",
        expires_at=999,
    )
    with pytest.raises(LearningGap):
        learning_coordinator.review_and_commit_acquisition(plan, wrong_auth)


def test_acquisition_preserves_compatibility_hash(
    learning_coordinator, reviewed_family_programs, reviewer_authorization
):
    """Authority compatibility hash is preserved across compatible acquisitions."""
    before = learning_coordinator._authority.model_compatibility_hash
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    receipt = learning_coordinator.review_and_commit_acquisition(
        plan, reviewer_authorization.for_plan(plan)
    )
    assert receipt.authority_compatibility_hash == before


def test_acquisition_conversational_wording_cannot_select_policy(
    learning_coordinator, reviewed_family_programs
):
    """The acquisition plan's policy ref is fixed, not derived from wording."""
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs,
        acquisition_kind="rule",
    )
    assert plan.reviewer_policy_ref == "policy:acquisition"
    assert plan.contract_ref == "contract:generic_definition_acquisition"
