"""Tests for inference bounds: explicit budget exhaustion.

Tests cover:
- Inference exhaustion is explicit (status "budget_exhausted")
- Budget exhaustion records the max rounds in the receipt
- A tight budget with recursive rules triggers exhaustion
"""

from __future__ import annotations

from collections import namedtuple

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import memory_stores
from legacy_propositions import (
    Application,
    PropositionGraph,
    SemanticSwitchProgram,
)
from cemm_authoritative_hybrid.query import (
    QueryEngine,
    GenericDefinitionLowerer,
    InferenceLimits,
    query,
)
from tests.test_query_engine import (
    _TestAuthority,
    _TestAuthorityFactory,
    _family_atoms,
    _family_designations,
    _family_operator_roles,
)


@pytest.fixture
def semantic_stores():
    stores = memory_stores(authority_generation="authority:test-v1")
    yield stores
    stores.close()


def _build_recursive_rules():
    """Build a set of recursive rules that chain indefinitely without converging.

    Rule 1: if X is related to Y via rel:chain, then Y is related to $new via rel:chain.
    Rule 2: if X has rel:reached to Y, then X has state:linked.

    Rule 1 creates an infinite chain because each application produces a new
    existential witness, so the forward chaining never converges.  The query
    asks about state:linked which is only derivable via Rule 2, but Rule 2
    requires a rel:reached fact which is never produced.  So the inference
    keeps running (Rule 1 keeps generating new facts) without ever finding
    support, and the round budget is exhausted.
    """
    from cemm_authoritative_hybrid.authority import RuleRecord

    rules = []

    # Recursive rule: chain relation extends with existential (never converges).
    rule1 = RuleRecord(
        rule_ref="rule:chain-extend",
        antecedent=(
            {
                "operator": "op:relation",
                "args": {"role:subject": "?x", "role:relation": "rel:chain", "role:object": "?y"},
            },
        ),
        consequent=(
            {
                "operator": "op:relation",
                "args": {"role:subject": "?y", "role:relation": "rel:chain", "role:object": "$z"},
            },
        ),
        confidence=1.0,
        reviewed=True,
    )
    rules.append(rule1)

    # Rule: reached relation implies linked state (never fires — no rel:reached facts).
    rule2 = RuleRecord(
        rule_ref="rule:reached-implies-linked",
        antecedent=(
            {
                "operator": "op:relation",
                "args": {"role:subject": "?x", "role:relation": "rel:reached", "role:object": "?y"},
            },
        ),
        consequent=(
            {
                "operator": "op:state",
                "args": {"role:subject": "?x", "role:dimension": "dim:linkage", "role:value": "state:linked"},
            },
        ),
        confidence=1.0,
        reviewed=True,
    )
    rules.append(rule2)

    return rules


def _build_cyclic_arrival_program():
    """Build a program that observes a cyclic chain: A→B, B→A."""
    app1 = Application.create(
        "op:relation",
        {"role:subject": "entity:a", "role:relation": "rel:chain", "role:object": "entity:b"},
    )
    app2 = Application.create(
        "op:relation",
        {"role:subject": "entity:b", "role:relation": "rel:chain", "role:object": "entity:a"},
    )
    graph = PropositionGraph.create([app1, app2], app1.application_ref)
    return SemanticSwitchProgram.create("OBSERVE", "event:arrival", graph)


@pytest.fixture
def recursive_rules():
    """A namedtuple with recursive rules and a query that triggers them."""
    rules = _build_recursive_rules()
    RecursiveFixture = namedtuple("RecursiveFixture", ["rules", "query"])
    return RecursiveFixture(rules=rules, query=query("entity:a", "state:linked"))


@pytest.fixture
def bounded_query_engine(semantic_stores, recursive_rules):
    """A query engine with a tight round budget and recursive rules."""
    atoms = _family_atoms()
    atoms["entity:a"] = "entity"
    atoms["entity:b"] = "entity"
    atoms["rel:chain"] = "relation_type"
    atoms["dim:linkage"] = "state_dimension"
    atoms["state:linked"] = "state_value"

    factory = _TestAuthorityFactory(
        base_atoms=atoms,
        base_designations=_family_designations(),
        operator_roles=_family_operator_roles(),
    )
    linked = factory.link_with_validated_rules(recursive_rules.rules)
    config = RuntimeConfig.release()
    limits = InferenceLimits(max_rounds=2, max_facts=256, max_rules=64)
    engine = QueryEngine(linked, semantic_stores, config, limits=limits)
    engine.observe(_build_cyclic_arrival_program())
    return engine


def test_inference_exhaustion_is_explicit(bounded_query_engine, recursive_rules):
    """When the round budget is exhausted, status is 'budget_exhausted'."""
    result = bounded_query_engine.ask(recursive_rules.query)
    assert result.status == "budget_exhausted"
    assert result.retrieval_receipt.rounds == bounded_query_engine.limits.max_rounds


def test_inference_exhaustion_has_no_proof(bounded_query_engine, recursive_rules):
    """Budget exhaustion result has no proof graph."""
    result = bounded_query_engine.ask(recursive_rules.query)
    assert result.proof is None


def test_inference_exhaustion_receipt_records_rounds(bounded_query_engine, recursive_rules):
    """The retrieval receipt records the number of rounds executed."""
    result = bounded_query_engine.ask(recursive_rules.query)
    assert result.retrieval_receipt.rounds == bounded_query_engine.limits.max_rounds


def test_inference_within_bounds_succeeds(semantic_stores):
    """When the budget is sufficient and rules converge, inference succeeds."""
    from cemm_authoritative_hybrid.authority import RuleRecord

    atoms = _family_atoms()
    atoms["entity:a"] = "entity"
    atoms["entity:b"] = "entity"
    atoms["rel:chain"] = "relation_type"
    atoms["dim:linkage"] = "state_dimension"
    atoms["state:linked"] = "state_value"

    factory = _TestAuthorityFactory(
        base_atoms=atoms,
        base_designations=_family_designations(),
        operator_roles=_family_operator_roles(),
    )

    # Use a simple non-recursive rule that converges.
    rules = [
        RuleRecord(
            rule_ref="rule:chain-implies-linked",
            antecedent=(
                {
                    "operator": "op:relation",
                    "args": {"role:subject": "?x", "role:relation": "rel:chain", "role:object": "?y"},
                },
            ),
            consequent=(
                {
                    "operator": "op:state",
                    "args": {"role:subject": "?x", "role:dimension": "dim:linkage", "role:value": "state:linked"},
                },
            ),
            confidence=1.0,
            reviewed=True,
        ),
    ]
    linked = factory.link_with_validated_rules(rules)
    config = RuntimeConfig.release()
    limits = InferenceLimits(max_rounds=6, max_facts=256, max_rules=64)
    engine = QueryEngine(linked, semantic_stores, config, limits=limits)
    engine.observe(_build_cyclic_arrival_program())

    result = engine.ask(query("entity:a", "state:linked"))
    # With sufficient budget, the chain-implies-linked rule should fire.
    assert result.status == "supported"
    assert result.proof is not None
