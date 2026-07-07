"""Golden test: Semantic Schema Kernel drives the full pipeline end-to-end.

Verifies that:
1. Schema kernel loads all 7 schema registries from JSON files
2. Language adapter resolves action aliases via the kernel
3. Graph builder uses schema-driven emotional evaluations
4. Relation frame compiler uses schema-driven projection policies
5. Affordance predictor loads rules from the kernel's AffordanceRegistry
6. Safety detector uses schema-driven safety categories
7. Patch operations are validated against PatchOperationRegistry
8. SituationFrameBuilder generates EventSchemas from the kernel
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.semantic_schema_kernel import get_kernel
from cemm.kernel.language_adapter import get_adapter, SchemaBackedLanguageAdapter
from cemm.kernel.relation_frame_compiler import RelationFrameCompiler
from cemm.kernel.affordance_predictor import AffordancePredictor
from cemm.kernel.safety_frame_detector import SafetyFrameDetector
from cemm.kernel.situation_frame_builder import SituationFrameBuilder
from cemm.tests.harness import SeededSystem


def test_schema_kernel_loads_all_registries():
    """All 7 schema registries should be populated from JSON files."""
    kernel = get_kernel()
    assert len(kernel.action_operators.all_action_keys()) >= 20, \
        "ActionOperatorRegistry should have at least 20 action operators"
    assert len(kernel.state_dimensions.all_families()) >= 10, \
        "StateDimensionRegistry should have at least 10 state families"
    assert len(kernel.entity_kinds.all_kinds()) >= 10, \
        "EntityKindRegistry should have at least 10 entity kinds"
    assert len(kernel.affordances.all()) >= 5, \
        "AffordanceRegistry should have at least 5 affordance schemas"
    assert kernel.projection_policies.for_applies_to("structural_edge") is not None, \
        "ProjectionPolicyRegistry should have structural_edge policy"
    assert kernel.projection_policies.for_applies_to("evaluates_edge") is not None, \
        "ProjectionPolicyRegistry should have evaluates_edge policy"
    assert kernel.patch_operations.is_known("upsert_relation_candidate"), \
        "PatchOperationRegistry should know upsert_relation_candidate"
    assert kernel.patch_operations.is_known("upsert_concept_candidate"), \
        "PatchOperationRegistry should know upsert_concept_candidate"


def test_language_adapter_resolves_via_kernel():
    """SchemaBackedLanguageAdapter should resolve action aliases via the kernel."""
    adapter = get_adapter("en")
    assert isinstance(adapter, SchemaBackedLanguageAdapter)
    tokens = adapter.tokenize("I love music")
    actions = adapter.map_actions(tokens)
    assert len(actions) > 0, "Should find action for 'love'"
    assert actions[0].action_key == "evaluate_positive", \
        f"'love' should map to evaluate_positive, got {actions[0].action_key}"


def test_schema_driven_emotional_evaluation():
    """'I love music' should create evaluates edge with schema-driven valence."""
    system = SeededSystem()
    result = system.run("I love music")
    graph = result["cycle"].uol_graph

    evaluates_edges = [e for e in graph.edges if e.edge_type == "evaluates"]
    assert len(evaluates_edges) > 0, "Should have evaluates edge"
    edge = evaluates_edges[0]
    assert edge.features.get("predicate") == "likes"
    assert edge.features.get("valence") == "positive"


def test_schema_driven_negative_evaluation():
    """'I hate music' should create evaluates edge with negative valence."""
    system = SeededSystem()
    result = system.run("I hate music")
    graph = result["cycle"].uol_graph

    evaluates_edges = [e for e in graph.edges if e.edge_type == "evaluates"]
    assert len(evaluates_edges) > 0, "Should have evaluates edge"
    edge = evaluates_edges[0]
    assert edge.features.get("predicate") == "dislikes"
    assert edge.features.get("valence") == "negative"


def test_relation_frame_compiler_uses_schema_projections():
    """Structural edges should have projection='none' from schema, evaluates='object'."""
    system = SeededSystem()
    result = system.run("I love music")
    graph = result["cycle"].uol_graph

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)

    has_role_frames = [f for f in frames if f.relation_key == "has_role"]
    for f in has_role_frames:
        assert f.structural is True, "has_role should be structural"
        assert f.answerable is False, "has_role should not be answerable"
        assert f.projection_policy == "none", \
            f"has_role projection should be 'none', got {f.projection_policy}"

    evaluates_frames = [f for f in frames if f.relation_key in ("likes", "dislikes", "evaluates")]
    for f in evaluates_frames:
        assert f.structural is False, "evaluates should not be structural"
        assert f.answerable is True, "evaluates should be answerable"
        assert f.projection_policy == "object", \
            f"evaluates projection should be 'object', got {f.projection_policy}"


def test_affordance_predictor_loads_from_kernel():
    """AffordancePredictor should load rules from the kernel's AffordanceRegistry."""
    predictor = AffordancePredictor()
    kernel = get_kernel()
    kernel_rules = {r.affordance_id for r in predictor._rules}
    schema_keys = {s.affordance_key for s in kernel.affordances.all()}
    assert kernel_rules == schema_keys, \
        f"Predictor rules {kernel_rules} should match kernel schemas {schema_keys}"


def test_safety_detector_uses_schema_categories():
    """SafetyFrameDetector should use safety_category from action operator schemas."""
    detector = SafetyFrameDetector()
    sf = detector.detect(input_text="should I beat him?")
    assert sf is not None, "Should detect safety concern"
    assert sf.category == "interpersonal_violence"
    assert sf.severity == "high"
    assert sf.allowed_response_mode == "deescalate"


def test_situation_frame_builder_uses_kernel_schemas():
    """SituationFrameBuilder should generate EventSchemas from the kernel."""
    builder = SituationFrameBuilder()
    kernel = get_kernel()
    for action_key in kernel.action_operators.all_action_keys():
        schema = builder.get_schema(action_key)
        assert schema is not None, f"Should have EventSchema for {action_key}"
        assert schema.source == "schema_kernel", \
            f"Schema for {action_key} should come from schema_kernel, got {schema.source}"


def test_remember_uses_schema_relation_lookup():
    """'remember I like coffee' should produce a relation patch with schema-driven relation_key."""
    system = SeededSystem()
    result = system.run("remember I like coffee")
    graph = result["cycle"].uol_graph

    relation_patches = []
    for p in graph.patch_candidates:
        for op in p.operations:
            if op.operation == "upsert_relation_candidate":
                relation_patches.append(op)

    assert len(relation_patches) > 0, "Should have relation candidate patches"
    likes_patches = [op for op in relation_patches if op.fields.get("relation_key") == "likes"]
    assert len(likes_patches) > 0, \
        "Should have a 'likes' relation patch from schema-driven verb lookup"


def test_patch_operations_all_known_to_kernel():
    """All patch operations produced by the graph builder should be known to the kernel."""
    system = SeededSystem()
    result = system.run("I love music")
    graph = result["cycle"].uol_graph
    kernel = get_kernel()

    for patch in graph.patch_candidates:
        for op in patch.operations:
            assert kernel.patch_operations.is_known(op.operation), \
                f"Patch operation '{op.operation}' should be known to the kernel"


def test_end_to_end_pipeline_no_errors():
    """Full pipeline should run without errors for various inputs."""
    system = SeededSystem()
    for text in ["I love music", "I hate coffee", "remember I like tea", "eat food", "come here"]:
        result = system.run(text)
        assert result.get("errors") == [], \
            f"Pipeline should have no errors for '{text}', got {result.get('errors')}"


def test_schema_state_deltas():
    """Graph builder creates state atoms + causes edges from schema state_deltas.

    'eat food' should produce:
    - action atom for consume_food
    - state atom for vital.hunger:decrease (actor)
    - causes edge from action to state atom
    - has_property edge from actor entity to state atom
    - upsert_state patch candidate
    """
    system = SeededSystem()
    result = system.run("eat food")
    graph = result["cycle"].uol_graph

    action_atoms = [a for a in graph.atoms.values() if a.kind == "action" and a.key == "consume_food"]
    assert len(action_atoms) > 0, "Should have consume_food action atom"

    schema_state_atoms = [
        a for a in graph.atoms.values()
        if a.kind == "state" and a.source == "schema_state_delta"
    ]
    assert len(schema_state_atoms) > 0, "Should have schema-driven state delta atoms"

    hunger_states = [a for a in schema_state_atoms if "hunger" in a.features.get("dimension", "")]
    assert len(hunger_states) > 0, "Should have hunger state delta atom"
    assert hunger_states[0].features.get("direction") == "decrease", \
        f"Hunger direction should be 'decrease', got {hunger_states[0].features.get('direction')}"

    causes_edges = [e for e in graph.edges if e.edge_type == "causes" and e.features.get("schema_source") == "state_delta"]
    assert len(causes_edges) > 0, "Should have causes edges from schema state deltas"

    has_property_edges = [
        e for e in graph.edges
        if e.edge_type == "has_property" and e.features.get("schema_source") == "state_delta"
    ]
    assert len(has_property_edges) > 0, "Should have has_property edges from schema state deltas"

    state_patches = [
        op for p in graph.patch_candidates for op in p.operations
        if op.operation == "upsert_state"
    ]
    assert len(state_patches) > 0, "Should have upsert_state patch candidates"
    hunger_patches = [op for op in state_patches if "hunger" in op.fields.get("dimension", "")]
    assert len(hunger_patches) > 0, "Should have hunger upsert_state patch"
    assert hunger_patches[0].fields.get("direction") == "decrease"


def test_schema_entity_kind_validation():
    """Entity kind validation marks has_role edges with allowed_entity_kinds and kind_valid.

    'eat food' should produce has_role edges with:
    - allowed_entity_kinds from schema slots
    - entity_kind inferred from the atom
    - kind_valid flag
    """
    system = SeededSystem()
    result = system.run("eat food")
    graph = result["cycle"].uol_graph

    action_atoms = [a for a in graph.atoms.values() if a.kind == "action" and a.key == "consume_food"]
    assert len(action_atoms) > 0, "Should have consume_food action atom"
    action_atom = action_atoms[0]

    has_role_edges = [
        e for e in graph.edges
        if e.edge_type == "has_role" and e.source_id == action_atom.id
    ]
    assert len(has_role_edges) > 0, "Should have has_role edges from action"

    for edge in has_role_edges:
        assert "allowed_entity_kinds" in edge.features, \
            f"has_role edge should have allowed_entity_kinds, got {edge.features}"
        assert "entity_kind" in edge.features, \
            f"has_role edge should have entity_kind, got {edge.features}"
        assert "kind_valid" in edge.features, \
            f"has_role edge should have kind_valid, got {edge.features}"

    actor_edges = [e for e in has_role_edges if e.features.get("role") == "actor"]
    if actor_edges:
        actor_edge = actor_edges[0]
        allowed = actor_edge.features.get("allowed_entity_kinds", [])
        assert "person" in allowed or "self" in allowed or "autonomous_agent" in allowed, \
            f"Actor slot should allow person/self/autonomous_agent, got {allowed}"


def test_schema_multilingual():
    """Igbo 'rie' resolves to same schema as English 'eat' — both map to consume_food."""
    kernel = get_kernel()

    en_action_key = kernel.action_operators.lookup_alias("eat", "en")
    ig_action_key = kernel.action_operators.lookup_alias("rie", "ig")

    assert en_action_key == "consume_food", \
        f"English 'eat' should map to consume_food, got {en_action_key}"
    assert ig_action_key == "consume_food", \
        f"Igbo 'rie' should map to consume_food, got {ig_action_key}"
    assert en_action_key == ig_action_key, \
        "English 'eat' and Igbo 'rie' should resolve to the same action schema"

    en_schema = kernel.action_operators.get(en_action_key)
    ig_schema = kernel.action_operators.get(ig_action_key)
    assert en_schema is ig_schema, \
        "Both should resolve to the same ActionOperatorSchema object"

    en_aliases = en_schema.aliases.get("en", [])
    ig_aliases = ig_schema.aliases.get("ig", [])
    assert "eat" in en_aliases, "English aliases should contain 'eat'"
    assert "rie" in ig_aliases, "Igbo aliases should contain 'rie'"


def test_schema_full_pipeline():
    """'eat food' end-to-end with schema-driven everything.

    Verifies the full chain:
    surface verb → language alias → canonical schema → graph atoms with typed slots
    → state delta atoms + causes edges → upsert_state patch candidates
    """
    system = SeededSystem()
    result = system.run("eat food")

    assert result.get("errors") == [], \
        f"Pipeline should have no errors for 'eat food', got {result.get('errors')}"

    graph = result["cycle"].uol_graph
    kernel = get_kernel()

    action_atoms = [a for a in graph.atoms.values() if a.kind == "action" and a.key == "consume_food"]
    assert len(action_atoms) > 0, "Should have consume_food action atom"

    action_atom = action_atoms[0]
    schema_slots = action_atom.features.get("schema_slots", {})
    assert schema_slots, "Action atom should carry schema_slots from the language adapter"
    assert "actor" in schema_slots, "Schema slots should contain actor slot"
    assert "object" in schema_slots, "Schema slots should contain object slot"

    schema = kernel.action_operators.get("consume_food")
    assert schema is not None, "consume_food schema should exist in kernel"
    assert len(schema.state_deltas) >= 2, \
        f"consume_food should have at least 2 state deltas, got {len(schema.state_deltas)}"

    state_atoms = [
        a for a in graph.atoms.values()
        if a.kind == "state" and a.source == "schema_state_delta"
    ]
    assert len(state_atoms) >= 2, \
        f"Should have at least 2 state delta atoms, got {len(state_atoms)}"

    causes_edges = [
        e for e in graph.edges
        if e.edge_type == "causes" and e.features.get("schema_source") == "state_delta"
    ]
    assert len(causes_edges) >= 2, \
        f"Should have at least 2 causes edges from state deltas, got {len(causes_edges)}"

    state_patches = [
        op for p in graph.patch_candidates for op in p.operations
        if op.operation == "upsert_state"
    ]
    assert len(state_patches) >= 2, \
        f"Should have at least 2 upsert_state patches, got {len(state_patches)}"

    for op in state_patches:
        assert kernel.patch_operations.is_known("upsert_state"), \
            "upsert_state should be a known patch operation"
        assert op.fields.get("dimension"), "Patch should have a dimension"
        assert op.fields.get("direction"), "Patch should have a direction"
        assert op.fields.get("entity_id"), "Patch should have an entity_id"
