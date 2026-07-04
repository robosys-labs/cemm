from __future__ import annotations
import pytest

from cemm.types.concept_atom import (
    ConceptAtom, ConceptState, SemanticFingerprint, Counterexample,
    SourceSupport, TemporalPolicy, EvidencePolicy, PermissionPolicy,
    PredicateSignature, ExemplarRef,
)
from cemm.types.operational_port import OperationalPort, EdgePattern, ResolverPolicy
from cemm.types.predicate_schema import PredicateSchema, GraphPattern, GraphPatchTemplate
from cemm.types.causal_affordance import CausalAffordance, PortBindingPattern
from cemm.types.construction_atom import ConstructionAtom, FormSignature, PragmaticPattern, PortConstraint


class TestConceptAtom:
    def test_default_instantiation(self):
        atom = ConceptAtom(concept_id="c1", key="president", atom_kind="entity")
        assert atom.concept_id == "c1"
        assert atom.key == "president"
        assert atom.atom_kind == "entity"
        assert atom.state == ConceptState.unknown_surface
        assert atom.confidence == 0.5
        assert atom.stability == 0.0
        assert atom.aliases == []
        assert atom.parents == []
        assert atom.ports == []
        assert atom.acceptable_predicates == []
        assert atom.causal_affordances == []
        assert atom.fingerprint is None

    def test_state_transitions_valid_strings(self):
        assert ConceptState.unknown_surface.value == "unknown_surface"
        assert ConceptState.candidate_atom.value == "candidate_atom"
        assert ConceptState.typed_candidate.value == "typed_candidate"
        assert ConceptState.operational_atom.value == "operational_atom"
        assert ConceptState.consolidated_atom.value == "consolidated_atom"
        assert ConceptState.contested_atom.value == "contested_atom"
        assert ConceptState.stale_atom.value == "stale_atom"
        assert len(ConceptState) == 7

    def test_semantic_fingerprint_jaccard_overlapping(self):
        a = SemanticFingerprint(key_tokens={"cat", "dog"}, surface_tokens={"pet"}, role_tokens={"animal"})
        b = SemanticFingerprint(key_tokens={"cat", "bird"}, surface_tokens={"pet"}, role_tokens={"pet"})
        sim = a.jaccard(b)
        assert 0.0 < sim < 1.0

    def test_semantic_fingerprint_jaccard_identical(self):
        a = SemanticFingerprint(key_tokens={"cat"}, surface_tokens={"pet"}, role_tokens={"animal"})
        b = SemanticFingerprint(key_tokens={"cat"}, surface_tokens={"pet"}, role_tokens={"animal"})
        assert a.jaccard(b) == 1.0

    def test_semantic_fingerprint_jaccard_disjoint(self):
        a = SemanticFingerprint(key_tokens={"cat"}, surface_tokens={"pet"}, role_tokens={"animal"})
        b = SemanticFingerprint(key_tokens={"car"}, surface_tokens={"vehicle"}, role_tokens={"machine"})
        assert a.jaccard(b) == 0.0

    def test_semantic_fingerprint_empty_sets(self):
        a = SemanticFingerprint()
        b = SemanticFingerprint()
        assert a.jaccard(b) == 0.0

    def test_with_counters(self):
        atom = ConceptAtom(
            concept_id="c2",
            key="cold",
            atom_kind="quality",
            state=ConceptState.consolidated_atom,
            counterexamples=[Counterexample(pattern={"temp": "low"}, count=2)],
            source_support=[SourceSupport(source_id="s1", source_type="sensor", confidence=0.9)],
            fingerprint=SemanticFingerprint(key_tokens={"cold", "temperature"}),
        )
        assert len(atom.counterexamples) == 1
        assert atom.counterexamples[0].count == 2
        assert len(atom.source_support) == 1
        assert atom.fingerprint is not None


class TestOperationalPort:
    def test_default_instantiation(self):
        port = OperationalPort(port_id="p1", owner_concept_id="c1", key="subject")
        assert port.port_id == "p1"
        assert port.owner_concept_id == "c1"
        assert port.key == "subject"
        assert port.required is False
        assert port.resolver_policy.strategy == "score"
        assert port.resolver_policy.min_score == 0.3
        assert port.confidence == 0.5

    def test_key_is_not_empty(self):
        port = OperationalPort(port_id="p1", owner_concept_id="c1", key="subject")
        assert port.key != ""

    def test_with_edge_patterns(self):
        port = OperationalPort(
            port_id="p2",
            owner_concept_id="c2",
            key="object",
            required=True,
            required_edges=[EdgePattern(edge_type="has_role", direction="incoming")],
            forbidden_edges=[EdgePattern(edge_type="modifies")],
        )
        assert len(port.required_edges) == 1
        assert port.required_edges[0].direction == "incoming"
        assert len(port.forbidden_edges) == 1


class TestPredicateSchema:
    def test_default_instantiation(self):
        ps = PredicateSchema(predicate_id="pr1", key="teaches")
        assert ps.predicate_id == "pr1"
        assert ps.key == "teaches"
        assert ps.preconditions == []
        assert ps.effects == []
        assert ps.confidence == 0.5

    def test_round_trip_preconditions_and_effects(self):
        pre = [GraphPattern(atom_patterns=[{"kind": "entity"}], edge_patterns=[{"type": "causes"}])]
        eff = [GraphPatchTemplate(operations=[{"op": "add", "target": "concept_lattice"}])]
        ps = PredicateSchema(
            predicate_id="pr2",
            key="causes",
            preconditions=pre,
            effects=eff,
        )
        assert len(ps.preconditions) == 1
        assert ps.preconditions[0].atom_patterns[0]["kind"] == "entity"
        assert len(ps.effects) == 1
        assert ps.effects[0].operations[0]["op"] == "add"


class TestCausalAffordance:
    def test_default_instantiation(self):
        ca = CausalAffordance(affordance_id="a1")
        assert ca.affordance_id == "a1"
        assert ca.trigger_pattern is None
        assert ca.predicted_effect is None
        assert ca.effect_type == "state_change"
        assert ca.confidence == 0.5

    def test_pattern_matching(self):
        ca = CausalAffordance(
            affordance_id="a2",
            trigger_pattern={"atom_patterns": [{"kind": "state"}]},
            predicted_effect={"operations": [{"op": "add"}]},
            required_bindings=[PortBindingPattern(port_id="p1", filler_kind="entity")],
            effect_type="state_change",
        )
        assert ca.trigger_pattern["atom_patterns"][0]["kind"] == "state"
        assert len(ca.required_bindings) == 1
        assert ca.required_bindings[0].port_id == "p1"
        assert ca.required_bindings[0].required is True


class TestConstructionAtom:
    def test_default_instantiation(self):
        ca = ConstructionAtom(construction_id="co1")
        assert ca.construction_id == "co1"
        assert ca.form_signature.surface_pattern == ""
        assert ca.graph_signature is None
        assert ca.pragmatic_signature is None
        assert ca.support_count == 0
        assert ca.confidence == 0.5

    def test_signature_construction(self):
        ca = ConstructionAtom(
            construction_id="co2",
            form_signature=FormSignature(
                surface_pattern="X causes Y",
                pos_pattern="NOUN VERB NOUN",
                dependency_pattern="nsubj(causes, X) obj(causes, Y)",
            ),
            graph_signature={"atom_patterns": [{"kind": "process"}]},
            pragmatic_signature=PragmaticPattern(
                expected_acts=["explain"],
                expected_modes=["declarative"],
            ),
            port_constraints=[PortConstraint(port_key="cause", source_concept="entity", edge_type="causes")],
            support_count=5,
        )
        assert ca.form_signature.surface_pattern == "X causes Y"
        assert ca.graph_signature is not None
        assert ca.pragmatic_signature is not None
        assert ca.pragmatic_signature.expected_acts == ["explain"]
        assert len(ca.port_constraints) == 1
        assert ca.port_constraints[0].edge_type == "causes"
        assert ca.support_count == 5
