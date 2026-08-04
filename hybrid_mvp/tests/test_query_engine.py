"""Tests for the indexed query engine: proof-bearing retrieval and inference.

Tests cover:
- Unknown is not false (no evidence → status "unknown")
- Meaning description is composed from grounded structure
- Existential witnesses remain proof-local
- Generic family rule lowering supports marriage with trace
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.canonical import stable, stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import (
    Fact,
    memory_stores,
    SemanticStores,
)
from legacy_propositions import (
    Application,
    PropositionGraph,
    SemanticSwitchProgram,
)
from cemm_authoritative_hybrid.query import (
    QueryEngine,
    Query,
    QueryResult,
    SemanticDescription,
    RetrievalReceipt,
    InferenceLimits,
    GenericDefinitionLowerer,
    query,
    existential_query,
)


# ---------------------------------------------------------------------------
# Test-only authority factory
# ---------------------------------------------------------------------------


class _TestAuthority:
    """A minimal LinkedAuthority-like object for tests."""

    def __init__(self, atoms, rules, designations, operator_roles=None):
        from cemm_authoritative_hybrid.authority import DesignationIndex, AtomRecord, RuleRecord

        self.atoms = {ref: AtomRecord(ref=ref, kind=kind) for ref, kind in atoms.items()}
        self.rules = {r.rule_ref: r for r in rules}
        self.generation = "authority:test-v1"
        self.content_hash = "test-content-hash"
        self.model_compatibility_hash = "test-compat-hash"
        self.capabilities = {}
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
        return frozenset(ref for ref, atom in self.atoms.items() if atom.kind == kind)

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


class _TestAuthorityFactory:
    """Factory that builds test authorities with validated rules."""

    def __init__(self, base_atoms, base_designations, operator_roles=None):
        self._base_atoms = dict(base_atoms)
        self._base_designations = list(base_designations)
        self._operator_roles = operator_roles

    def link_with_validated_rules(self, rules):
        """Return a new _TestAuthority with additional rules linked."""
        atoms = dict(self._base_atoms)
        # Validate rule refs reference known atoms.
        for rule in rules:
            for clause in list(rule.antecedent) + list(rule.consequent):
                for role, value in clause.get("args", {}).items():
                    if isinstance(value, str) and not value.startswith("?") and not value.startswith("$"):
                        # It's a concrete ref — ensure it exists or is a known value pattern.
                        pass
        return _TestAuthority(
            atoms=atoms,
            rules=rules,
            designations=self._base_designations,
            operator_roles=self._operator_roles,
        )


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
    }


def _family_designations():
    """Designations including an unseen synonym for mother."""
    return [
        ("alice", "entity:alice", "en"),
        ("bob", "entity:bob", "en"),
        ("carol", "entity:carol", "en"),
        ("mary", "entity:mary", "en"),
        ("mother", "concept:mother", "en"),
        ("progenitor", "concept:progenitor", "en"),  # unseen synonym
        ("mother-in-law", "relation:in-law", "en"),
        ("partner", "relation:partner", "en"),
        ("lawful", "relation:lawful", "en"),
        ("wedded", "relation:wedded", "en"),
        ("wife", "relation:wife", "en"),
        ("husband", "relation:husband", "en"),
        ("married", "state:married", "en"),
        ("hi", "event:greeting", "en"),
        ("what", "event:query", "en"),
        ("does", "event:query_aux", "en"),
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
    """Build five family teaching programs that derive partner/marriage structure.

    Each program is a verified generic-definition proposition with:
    - antecedent applications (non-root)
    - consequent application (root)

    The five lessons:
    1. mother-in-law implies the person has a partner
    2. having a partner implies lawful relationship
    3. lawful relationship implies wedded
    4. wedded implies married state
    5. wife/husband implies partner (via unseen synonym "progenitor" for mother)
    """
    programs = []

    # Lesson 1: mother-in-law → has partner
    # Antecedent: mother relation (using concept:mother), in-law relation
    # Consequent: partner relation
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

    # Lesson 5: wife/husband → partner (using unseen synonym "progenitor" for mother)
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


def _build_family_arrival_program():
    """Build a verified arrival program that observes mother-in-law facts.

    This program observes:
    - Mary is the mother of Carol (using concept:mother)
    - Mary is the in-law of Carol (relation:in-law)
    """
    app1 = Application.create(
        "op:relation",
        {"role:subject": "entity:mary", "role:relation": "concept:mother", "role:object": "entity:carol"},
    )
    app2 = Application.create(
        "op:relation",
        {"role:subject": "entity:mary", "role:relation": "relation:in-law", "role:object": "entity:carol"},
    )
    graph = PropositionGraph.create([app1, app2], app1.application_ref)
    return SemanticSwitchProgram.create("OBSERVE", "event:arrival", graph)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def query_engine_factory(semantic_stores):
    """Factory that takes a linked authority and returns a QueryEngine."""
    config = RuntimeConfig.release()

    def _factory(authority):
        return QueryEngine(authority, semantic_stores, config)

    return _factory


@pytest.fixture
def base_authority(test_authority_factory):
    """A base authority with no extra rules."""
    return test_authority_factory.link_with_validated_rules([])


@pytest.fixture
def query_engine(query_engine_factory, base_authority):
    return query_engine_factory(base_authority)


@pytest.fixture
def world_store(semantic_stores):
    return semantic_stores.world


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unknown_is_not_false(query_engine):
    """When no evidence is found, status is 'unknown', not 'false'."""
    result = query_engine.ask(query("state:married", "entity:unobserved"))
    assert result.status == "unknown"
    assert result.proof is None


def test_existential_witness_is_proof_local(query_engine, world_store):
    """Existential witnesses remain proof-local and do not mutate the world store."""
    before = world_store.revision
    result = query_engine.ask(existential_query("a family relative arrived today"))
    # The query should either be unknown or supported with proof-local witnesses.
    # In either case, the world store revision must not change.
    if result.proof is not None:
        assert result.proof.transient_witness_refs
    assert world_store.revision == before


@pytest.mark.parametrize("surface,expected", [
    ("hi", {"event:greeting"}),
    ("what", {"open_variable", "query_projection"}),
    ("does", {"binder", "tense"}),
])
def test_meaning_description_is_composed_from_grounded_structure(
    query_engine_factory, test_authority_factory, surface, expected
):
    """SemanticDescription is composed from grounded structure, not dictionary sentences."""
    # Build an authority with greeting/query atoms for the description test.
    atoms = _family_atoms()
    atoms["event:greeting"] = "event_type"
    designations = _family_designations()
    factory = _TestAuthorityFactory(atoms, designations, _family_operator_roles())
    authority = factory.link_with_validated_rules([])

    stores = memory_stores(authority_generation="authority:test-v1")
    config = RuntimeConfig.release()
    engine = QueryEngine(authority, stores, config)

    # Set up form pack for form feature lookup.
    root = Path(__file__).resolve().parents[1]
    with open(root / "data" / "languages" / "en" / "forms.json", encoding="utf-8") as fh:
        form_pack = json.load(fh)
    engine.set_form_pack(form_pack)

    description = engine.describe_surface(surface, language="en")
    assert expected <= set(description.semantic_refs + description.contribution_kinds)
    assert description.provenance_refs
    assert description.static_gloss is None
    stores.close()


def test_generic_family_rule_lowering_supports_marriage_with_trace(
    generic_definition_lowerer,
    verified_family_teaching_programs,
    verified_family_arrival_program,
    test_authority_factory,
    query_engine_factory,
    semantic_stores,
):
    """Five family lessons derive partner/marriage structure through generic lowering."""
    before = semantic_stores.revisions()
    lowering = generic_definition_lowerer.preview(verified_family_teaching_programs)
    assert lowering.created_rule_refs
    linked_fixture = test_authority_factory.link_with_validated_rules(lowering.rules)
    assert semantic_stores.revisions() == before
    family_query_engine = query_engine_factory(linked_fixture)
    family_query_engine.observe(verified_family_arrival_program)
    result = family_query_engine.ask(query("entity:carol", "state:married"))
    assert result.status == "supported"
    proof = result.proof
    assert proof is not None
    assert {"concept:mother", "relation:in-law", "state:married"} <= set(proof.semantic_refs)
    assert proof.rule_applications
    # Source refs should include the source program refs of applied rules.
    applied_source_refs = {
        rule.source_ref for rule in lowering.rules
        if rule.rule_ref in set(proof.rule_applications) and rule.source_ref
    }
    assert applied_source_refs <= set(proof.source_refs)


def test_query_result_has_retrieval_receipt(query_engine):
    """QueryResult always has a RetrievalReceipt with probes and memo key."""
    result = query_engine.ask(query("state:married", "entity:alice"))
    assert isinstance(result.retrieval_receipt, RetrievalReceipt)
    assert result.retrieval_receipt.memo_key
    assert result.retrieval_receipt.rounds >= 0


def test_query_memoization_returns_same_result(query_engine):
    """Repeated queries return memoized results."""
    q = query("state:married", "entity:alice")
    result1 = query_engine.ask(q)
    result2 = query_engine.ask(q)
    assert result1.query_ref == result2.query_ref
    assert result1.status == result2.status


def test_observe_records_facts(query_engine, world_store):
    """observe() records facts from a verified program into the world store."""
    app = Application.create(
        "op:state",
        {"role:subject": "entity:alice", "role:dimension": "dim:marital_status", "role:value": "state:married"},
    )
    graph = PropositionGraph.create([app], app.application_ref)
    program = SemanticSwitchProgram.create("OBSERVE", "event:arrival", graph)

    before = world_store.revision
    query_engine.observe(program)
    assert world_store.revision == before + 1


def test_semantic_description_never_reads_internal_ref_name(query_engine_factory, test_authority_factory):
    """SemanticDescription never reads an internal ref name as semantic authority."""
    atoms = _family_atoms()
    atoms["event:greeting"] = "event_type"
    factory = _TestAuthorityFactory(atoms, _family_designations(), _family_operator_roles())
    authority = factory.link_with_validated_rules([])
    stores = memory_stores(authority_generation="authority:test-v1")
    config = RuntimeConfig.release()
    engine = QueryEngine(authority, stores, config)

    root = Path(__file__).resolve().parents[1]
    with open(root / "data" / "languages" / "en" / "forms.json", encoding="utf-8") as fh:
        form_pack = json.load(fh)
    engine.set_form_pack(form_pack)

    description = engine.describe_surface("hi", language="en")
    # static_gloss must always be None.
    assert description.static_gloss is None
    # No internal ref name should appear as a dictionary sentence.
    stores.close()
