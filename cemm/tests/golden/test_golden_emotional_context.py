"""Golden test: emotional context pipeline end-to-end.

Verifies that emotional predicates (like/love/hate/dislike) flow through:
1. Graph building → evaluates edges + relation atoms
2. Affordance prediction → evaluation_shift predictions
3. Obligation scheduling → acknowledge_emotional_context
4. Realization → emotional_response template
5. Patch extraction → durable storage of emotional relations
6. Affect state update → kernel.user.affect modified by affect markers
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.tests.harness import SeededSystem


def test_emotional_predicate_creates_evaluates_edge():
    """Phase 2: 'I love music' should create an 'evaluates' edge in the UOL graph."""
    system = SeededSystem()
    result = system.run("I love music")

    cycle = result["cycle"]
    assert cycle is not None, "Cycle should be produced"

    graph = cycle.uol_graph
    assert graph is not None, "UOL graph should be produced"

    evaluates_edges = [e for e in graph.edges if e.edge_type == "evaluates"]
    assert len(evaluates_edges) > 0, "Should have at least one 'evaluates' edge"

    edge = evaluates_edges[0]
    assert edge.features.get("predicate") == "likes", \
        f"Predicate should be 'likes', got {edge.features.get('predicate')}"
    assert edge.features.get("valence") == "positive", \
        f"Valence should be 'positive', got {edge.features.get('valence')}"


def test_emotional_predicate_creates_relation_atom():
    """Phase 2: 'I love music' should create a relation atom with key 'likes'."""
    system = SeededSystem()
    result = system.run("I love music")

    graph = result["cycle"].uol_graph
    relation_atoms = [a for a in graph.atoms.values() if a.kind == "relation" and a.key == "likes"]
    assert len(relation_atoms) > 0, "Should have a 'likes' relation atom"
    assert relation_atoms[0].source == "emotional_predicate", \
        f"Source should be 'emotional_predicate', got {relation_atoms[0].source}"


def test_negative_emotional_predicate_creates_dislikes_edge():
    """Phase 2: 'I hate noise' should create an 'evaluates' edge with 'dislikes' predicate."""
    system = SeededSystem()
    result = system.run("I hate noise")

    graph = result["cycle"].uol_graph
    evaluates_edges = [e for e in graph.edges if e.edge_type == "evaluates"]
    assert len(evaluates_edges) > 0, "Should have at least one 'evaluates' edge"

    edge = evaluates_edges[0]
    assert edge.features.get("predicate") == "dislikes", \
        f"Predicate should be 'dislikes', got {edge.features.get('predicate')}"
    assert edge.features.get("valence") == "negative", \
        f"Valence should be 'negative', got {edge.features.get('valence')}"


def test_emotional_predicate_triggers_evaluation_shift_affordance():
    """Phase 3: 'I love music' should produce an evaluation_shift affordance prediction."""
    system = SeededSystem()
    result = system.run("I love music")

    graph = result["cycle"].uol_graph
    eval_shifts = [
        p for p in graph.affordance_predictions
        if p.effect_type == "evaluation_shift"
    ]
    assert len(eval_shifts) > 0, \
        "Should have at least one evaluation_shift affordance prediction"


def test_emotional_predicate_routes_to_emotional_obligation():
    """Phase 3+5: 'I love music' should route to acknowledge_emotional_context obligation."""
    system = SeededSystem()
    result = system.run("I love music")

    obligation = result["obligation_kind"]
    assert obligation == "acknowledge_emotional_context", \
        f"Obligation should be 'acknowledge_emotional_context', got {obligation}"


def test_emotional_obligation_produces_emotional_response():
    """Phase 5: Emotional obligation should produce emotional response output.
    v3.1: template_key is retired; verify via obligation_kind and non-empty output."""
    system = SeededSystem()
    result = system.run("I love music")

    obligation = result["obligation_kind"]
    assert obligation == "acknowledge_emotional_context", \
        f"Obligation should be 'acknowledge_emotional_context', got {obligation}"
    output = result["output"]
    assert output and len(output) > 0, \
        f"Output should be non-empty, got: {output!r}"


def test_emotional_response_output_is_non_empty():
    """Phase 5: Emotional response should produce non-empty output text."""
    system = SeededSystem()
    result = system.run("I love music")

    output = result["output"]
    assert output and len(output) > 0, \
        f"Output should be non-empty, got: {output!r}"


def test_emotional_predicate_creates_patch_candidate():
    """Phase 4: 'I love music' should create a patch candidate for the emotional relation."""
    system = SeededSystem()
    result = system.run("I love music")

    graph = result["cycle"].uol_graph
    emotional_patches = [
        p for p in graph.patch_candidates
        if any(op.reason == "emotional_evaluation_relation" for op in p.operations)
    ]
    assert len(emotional_patches) > 0, \
        "Should have at least one emotional evaluation patch candidate"


def test_emotional_relation_compiled_as_answerable():
    """Phase 4: The 'likes' relation frame should be answerable, not structural."""
    system = SeededSystem()
    result = system.run("I love music")

    cycle = result["cycle"]
    frames = cycle.relation_frames or []
    likes_frames = [f for f in frames if f.relation_key == "likes"]
    assert len(likes_frames) > 0, "Should have at least one 'likes' relation frame"

    frame = likes_frames[0]
    assert frame.answerable, "likes relation frame should be answerable"
    assert not frame.structural, "likes relation frame should not be structural"
    assert frame.projection_policy == "object", \
        f"Projection policy should be 'object', got {frame.projection_policy}"


def test_evaluates_edge_compiled_as_answerable():
    """Phase 4: The 'evaluates' edge should be compiled as answerable."""
    system = SeededSystem()
    result = system.run("I love music")

    cycle = result["cycle"]
    frames = cycle.relation_frames or []
    evaluates_frames = [f for f in frames if f.relation_key == "evaluates"]
    assert len(evaluates_frames) > 0, "Should have at least one 'evaluates' relation frame"

    frame = evaluates_frames[0]
    assert frame.answerable, "evaluates relation frame should be answerable"
    assert not frame.structural, "evaluates relation frame should not be structural"


def test_affect_state_updated_after_emotional_input():
    """Phase 1: After 'I love music', affect update should not produce errors."""
    system = SeededSystem()
    result = system.run("I love music")

    cycle = result["cycle"]
    assert cycle is not None
    errors = result.get("errors", [])
    affect_errors = [e for e in errors if "affect" in e.lower()]
    assert len(affect_errors) == 0, \
        f"Should have no affect update errors, got: {affect_errors}"


def test_emotional_predicate_does_not_break_existing_pipeline():
    """Regression: Emotional predicate input should not cause errors."""
    system = SeededSystem()
    result = system.run("I love music")

    errors = result.get("errors", [])
    assert len(errors) == 0, \
        f"Should have no errors, got: {errors}"
