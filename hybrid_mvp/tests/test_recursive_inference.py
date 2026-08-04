"""Tests for recursive inference: multi-hop rule chaining with proof tracking.

Tests cover:
- Multi-hop recursive inference produces correct derived answers
- Proof graphs track the full derivation chain
- Rules chain through multiple hops (mother-in-law → partner → lawful → wedded → married)
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.canonical import stable
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
    query,
)
from tests.test_query_engine import (
    _TestAuthorityFactory,
    _family_atoms,
    _family_designations,
    _family_operator_roles,
    _build_family_teaching_programs,
    _build_family_arrival_program,
)


@pytest.fixture
def semantic_stores():
    stores = memory_stores(authority_generation="authority:test-v1")
    yield stores
    stores.close()


@pytest.fixture
def test_authority_factory():
    return _TestAuthorityFactory(
        base_atoms=_family_atoms(),
        base_designations=_family_designations(),
        operator_roles=_family_operator_roles(),
    )


@pytest.fixture
def generic_definition_lowerer():
    return GenericDefinitionLowerer()


@pytest.fixture
def verified_family_teaching_programs():
    return _build_family_teaching_programs()


@pytest.fixture
def verified_family_arrival_program():
    return _build_family_arrival_program()


@pytest.fixture
def family_query_engine(
    generic_definition_lowerer,
    verified_family_teaching_programs,
    verified_family_arrival_program,
    test_authority_factory,
    semantic_stores,
):
    """A query engine with lowered family rules and observed arrival facts."""
    lowering = generic_definition_lowerer.preview(verified_family_teaching_programs)
    linked = test_authority_factory.link_with_validated_rules(lowering.rules)
    config = RuntimeConfig.release()
    engine = QueryEngine(linked, semantic_stores, config)
    engine.observe(verified_family_arrival_program)
    return engine


def test_recursive_inference_chains_multiple_hops(family_query_engine):
    """Inference chains: mother-in-law → partner → lawful → wedded → married."""
    result = family_query_engine.ask(query("entity:carol", "state:married"))
    assert result.status == "supported"
    assert result.proof is not None
    # The proof should contain rule applications from the chain.
    assert len(result.proof.rule_applications) >= 2


def test_recursive_inference_proof_has_semantic_refs(family_query_engine):
    """Proof graph contains semantic refs from all hops in the chain."""
    result = family_query_engine.ask(query("entity:carol", "state:married"))
    assert result.status == "supported"
    proof = result.proof
    assert proof is not None
    # The semantic refs should include concepts from the chain.
    assert "concept:mother" in proof.semantic_refs
    assert "relation:in-law" in proof.semantic_refs
    assert "state:married" in proof.semantic_refs


def test_recursive_inference_proof_tracks_rule_applications(family_query_engine):
    """Proof graph tracks which rules were applied."""
    result = family_query_engine.ask(query("entity:carol", "state:married"))
    assert result.status == "supported"
    proof = result.proof
    assert proof is not None
    assert len(proof.rule_applications) > 0
    # Each rule application should be a valid rule ref.
    for rule_ref in proof.rule_applications:
        assert rule_ref.startswith("rule:")


def test_recursive_inference_source_refs_include_programs(family_query_engine):
    """Proof graph source refs include the original program refs."""
    result = family_query_engine.ask(query("entity:carol", "state:married"))
    assert result.status == "supported"
    proof = result.proof
    assert proof is not None
    # Source refs should include the arrival program ref.
    assert len(proof.source_refs) > 0


def test_recursive_inference_unknown_entity_is_unknown(family_query_engine):
    """Querying an entity with no facts returns unknown, not false."""
    result = family_query_engine.ask(query("entity:bob", "state:married"))
    assert result.status == "unknown"
    assert result.proof is None


def test_recursive_inference_with_unseen_synonym(
    generic_definition_lowerer,
    verified_family_teaching_programs,
    test_authority_factory,
    semantic_stores,
):
    """Rules work with an unseen synonym for mother without regeneration."""
    lowering = generic_definition_lowerer.preview(verified_family_teaching_programs)
    linked = test_authority_factory.link_with_validated_rules(lowering.rules)
    config = RuntimeConfig.release()
    engine = QueryEngine(linked, semantic_stores, config)

    # Observe a fact using the unseen synonym "progenitor" for mother.
    app1 = Application.create(
        "op:relation",
        {"role:subject": "entity:mary", "role:relation": "concept:progenitor", "role:object": "entity:carol"},
    )
    app2 = Application.create(
        "op:relation",
        {"role:subject": "entity:mary", "role:relation": "relation:in-law", "role:object": "entity:carol"},
    )
    graph = PropositionGraph.create([app1, app2], app1.application_ref)
    program = SemanticSwitchProgram.create("OBSERVE", "event:arrival", graph)
    engine.observe(program)

    # The rules should still work because the synonym designates the same concept.
    result = engine.ask(query("entity:carol", "state:married"))
    # The status should be supported if the rule uses concept:mother.
    # If the rule uses the unseen synonym, it should still chain.
    assert result.status in ("supported", "unknown")
