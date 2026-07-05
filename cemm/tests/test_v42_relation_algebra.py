"""Tests for RelationFrame, RelationFrameCompiler, PredicateSchemaStore,
and RelationAlgebra — the second PR of the v4.2 gap-fix plan.

Tests use arbitrary symbols (A, B, X, Y) to prevent domain hardcoding,
per the non-drift principle.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.types.relation_frame import RelationArgument, RelationFrame
from cemm.types.uol_graph import UOLGraph, UOLAtom, UOLEdge, ConceptResolution
from cemm.kernel.relation_frame_compiler import RelationFrameCompiler
from cemm.kernel.relation_algebra import RelationAlgebra
from cemm.memory.predicate_schema_store import PredicateSchemaStore


# ── RelationFrameCompiler ────────────────────────────────────────


def test_compiler_empty_graph():
    compiler = RelationFrameCompiler()
    frames = compiler.compile(UOLGraph(id="g1"))
    assert frames == []


def test_compiler_is_a_edge():
    graph = UOLGraph(id="g1", signal_id="s1")
    a = graph.add_atom("entity", "entity:A", surface="A", confidence=0.8)
    b = graph.add_atom("entity", "entity:B", surface="B", confidence=0.8)
    graph.add_edge("is_a", a.id, b.id, confidence=0.7)

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert len(frames) == 1
    assert frames[0].relation_key == "is_a"
    assert frames[0].relation_family == "taxonomy"
    assert frames[0].subject.surface == "A"
    assert frames[0].object.surface == "B"
    assert "sub_type_of" in frames[0].inverse_relation_keys


def test_compiler_causes_edge():
    graph = UOLGraph(id="g1", signal_id="s1")
    x = graph.add_atom("process", "process:X", surface="X")
    y = graph.add_atom("state", "state:Y", surface="Y")
    graph.add_edge("causes", x.id, y.id)

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert len(frames) == 1
    assert frames[0].relation_key == "causes"
    assert frames[0].relation_family == "causal"


def test_compiler_used_for_edge():
    graph = UOLGraph(id="g1", signal_id="s1")
    tool = graph.add_atom("entity", "entity:tool", surface="tool")
    purpose = graph.add_atom("process", "process:purpose", surface="purpose")
    graph.add_edge("used_for", tool.id, purpose.id)

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert len(frames) == 1
    assert frames[0].relation_family == "affordance"


def test_compiler_preserves_concept_resolution():
    graph = UOLGraph(id="g1", signal_id="s1")
    a = graph.add_atom("entity", "entity:A", surface="A")
    b = graph.add_atom("entity", "entity:B", surface="B")
    graph.add_edge("is_a", a.id, b.id)
    graph.concept_resolutions.append(ConceptResolution(atom_id=a.id, concept_id="concept:A", state="resolved"))

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert frames[0].subject.concept_id == "concept:A"


def test_compiler_preserves_source_lineage():
    graph = UOLGraph(id="g1", signal_id="s1")
    a = graph.add_atom("entity", "entity:A", surface="A")
    b = graph.add_atom("entity", "entity:B", surface="B")
    edge = graph.add_edge("is_a", a.id, b.id)

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert edge.id in frames[0].source_edge_ids
    assert a.id in frames[0].source_atom_ids
    assert b.id in frames[0].source_atom_ids


def test_compiler_part_of_edge():
    graph = UOLGraph(id="g1", signal_id="s1")
    part = graph.add_atom("entity", "entity:part", surface="part")
    whole = graph.add_atom("entity", "entity:whole", surface="whole")
    graph.add_edge("part_of", part.id, whole.id)

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert frames[0].relation_family == "membership"
    assert "has_part" in frames[0].inverse_relation_keys


def test_compiler_same_as_symmetric():
    graph = UOLGraph(id="g1", signal_id="s1")
    a = graph.add_atom("entity", "entity:A", surface="A")
    b = graph.add_atom("entity", "entity:B", surface="B")
    graph.add_edge("same_as", a.id, b.id)

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)
    assert frames[0].relation_family == "identity"
    assert "same_as" in frames[0].inverse_relation_keys


# ── PredicateSchemaStore ─────────────────────────────────────────


def test_schema_store_seeds():
    store = PredicateSchemaStore()
    assert store.get("is_a") is not None
    assert store.get("same_as") is not None
    assert store.get("part_of") is not None
    assert store.get("causes") is not None
    assert store.get("used_for") is not None
    assert store.get("has_property") is not None
    assert store.get("has_role") is not None


def test_schema_store_is_a_inherits():
    store = PredicateSchemaStore()
    schema = store.get("is_a")
    assert schema is not None
    assert schema.inheritance_behavior == "inherit"
    assert store.inherits("is_a") is True


def test_schema_store_causes_no_inherit():
    store = PredicateSchemaStore()
    assert store.inherits("causes") is False


def test_schema_store_inverse_of():
    store = PredicateSchemaStore()
    assert "sub_type_of" in store.inverse_of("is_a")
    assert "caused_by" in store.inverse_of("causes")
    assert "has_part" in store.inverse_of("part_of")


def test_schema_store_observe_candidate():
    store = PredicateSchemaStore()
    record = store.observe_candidate("leader_of", ["leader", "country"], "role")
    assert record.predicate_key == "leader_of"
    assert record.support_count == 1
    assert record.confidence < 0.5
    assert store.get("leader_of") is None
    assert store.get_candidate("leader_of") is not None


def test_schema_store_promote_after_support():
    store = PredicateSchemaStore()
    store.observe_candidate("leader_of", ["leader", "country"], "role")
    store.observe_candidate("leader_of", ["leader", "country"], "role")
    assert store.promote("leader_of") is True
    assert store.get("leader_of") is not None
    assert store.get_candidate("leader_of") is None


def test_schema_store_no_promote_with_counterexamples():
    store = PredicateSchemaStore()
    store.observe_candidate("leader_of", ["leader", "country"], "role")
    store.observe_candidate("leader_of", ["leader", "country"], "role")
    store.add_counterexample("leader_of", {"roles": ["leader", "planet"]})
    store.add_counterexample("leader_of", {"roles": ["leader", "planet"]})
    assert store.promote("leader_of") is False
    assert store.get("leader_of") is None


# ── RelationAlgebra ──────────────────────────────────────────────


def test_algebra_inverse():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    frame = RelationFrame(
        relation_id="f1",
        relation_key="is_a",
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id="A", surface="A"),
        object=RelationArgument(role="object", concept_id="B", surface="B"),
    )
    inv = algebra.inverse(frame)
    assert inv is not None
    assert inv.relation_key == "sub_type_of"
    assert inv.subject.concept_id == "B"
    assert inv.object.concept_id == "A"


def test_algebra_compose():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frame_a = RelationFrame(
        relation_id="f1",
        relation_key="is_a",
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="A", surface="A"),
    )
    frame_b = RelationFrame(
        relation_id="f2",
        relation_key="is_a",
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id="A", surface="A"),
        object=RelationArgument(role="object", concept_id="B", surface="B"),
    )
    composed = algebra.compose(frame_a, frame_b)
    assert composed is not None
    assert composed.subject.concept_id == "X"
    assert composed.object.concept_id == "B"
    assert "f1" in composed.inherited_from
    assert "f2" in composed.inherited_from


def test_algebra_compose_mismatch_returns_none():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frame_a = RelationFrame(
        relation_id="f1",
        relation_key="is_a",
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="A", surface="A"),
    )
    frame_b = RelationFrame(
        relation_id="f2",
        relation_key="is_a",
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id="Z", surface="Z"),
        object=RelationArgument(role="object", concept_id="B", surface="B"),
    )
    composed = algebra.compose(frame_a, frame_b)
    assert composed is None


def test_algebra_inherit():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    taxonomy_frames = [
        RelationFrame(
            relation_id="isa1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="A", surface="A"),
            object=RelationArgument(role="object", concept_id="B", surface="B"),
            confidence=0.8,
        ),
        RelationFrame(
            relation_id="role1",
            relation_key="has_role",
            relation_family="role",
            subject=RelationArgument(role="subject", concept_id="B", surface="B"),
            object=RelationArgument(role="object", concept_id="leader", surface="leader"),
            confidence=0.7,
        ),
    ]

    inherited = algebra.inherit("A", "B", taxonomy_frames)
    assert len(inherited) == 1
    assert inherited[0].relation_key == "has_role"
    assert inherited[0].subject.concept_id == "A"
    assert inherited[0].object.concept_id == "leader"


def test_algebra_query_subject():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="f1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="X", surface="X"),
            object=RelationArgument(role="object", concept_id="A", surface="A"),
        ),
        RelationFrame(
            relation_id="f2",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="Y", surface="Y"),
            object=RelationArgument(role="object", concept_id="B", surface="B"),
        ),
    ]
    results = algebra.query_subject("is_a", object_concept_id="A", frames=frames)
    assert len(results) == 1
    assert results[0].subject.concept_id == "X"


def test_algebra_query_subject_with_inheritance():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="isa1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="X", surface="X"),
            object=RelationArgument(role="object", concept_id="A", surface="A"),
        ),
        RelationFrame(
            relation_id="isa2",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="A", surface="A"),
            object=RelationArgument(role="object", concept_id="B", surface="B"),
        ),
        RelationFrame(
            relation_id="role1",
            relation_key="has_role",
            relation_family="role",
            subject=RelationArgument(role="subject", concept_id="B", surface="B"),
            object=RelationArgument(role="object", concept_id="leader", surface="leader"),
        ),
    ]
    results = algebra.query_subject("has_role", object_concept_id="leader", frames=frames, allow_inheritance=True)
    assert len(results) >= 1
    inherited = [f for f in results if f.inherited_from]
    assert len(inherited) >= 1


def test_algebra_query_subject_with_inverse():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="f1",
            relation_key="part_of",
            relation_family="membership",
            subject=RelationArgument(role="subject", concept_id="engine", surface="engine"),
            object=RelationArgument(role="object", concept_id="car", surface="car"),
        ),
    ]
    results = algebra.query_subject("has_part", object_concept_id="engine", frames=frames, allow_inverse=True)
    assert len(results) >= 1
    inv = [f for f in results if f.relation_key == "has_part"]
    assert len(inv) == 1
    assert inv[0].subject.concept_id == "car"
    assert inv[0].object.concept_id == "engine"


def test_algebra_query_subject_filters_by_subject():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="f1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="dog", surface="dog"),
            object=RelationArgument(role="object", concept_id="animal", surface="animal"),
        ),
        RelationFrame(
            relation_id="f2",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="cat", surface="cat"),
            object=RelationArgument(role="object", concept_id="animal", surface="animal"),
        ),
        RelationFrame(
            relation_id="f3",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="car", surface="car"),
            object=RelationArgument(role="object", concept_id="vehicle", surface="vehicle"),
        ),
    ]
    results = algebra.query_subject(
        "is_a", subject_concept_id="dog", frames=frames,
        allow_inheritance=False, allow_inverse=False,
    )
    assert len(results) == 1
    assert results[0].subject.concept_id == "dog"
    assert results[0].object.concept_id == "animal"


def test_algebra_query_subject_both_subject_and_object_filter():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="f1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="dog", surface="dog"),
            object=RelationArgument(role="object", concept_id="animal", surface="animal"),
        ),
        RelationFrame(
            relation_id="f2",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="dog", surface="dog"),
            object=RelationArgument(role="object", concept_id="mammal", surface="mammal"),
        ),
        RelationFrame(
            relation_id="f3",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="cat", surface="cat"),
            object=RelationArgument(role="object", concept_id="animal", surface="animal"),
        ),
    ]
    results = algebra.query_subject(
        "is_a", subject_concept_id="dog", object_concept_id="animal",
        frames=frames, allow_inheritance=False, allow_inverse=False,
    )
    assert len(results) == 1
    assert results[0].subject.concept_id == "dog"
    assert results[0].object.concept_id == "animal"


def test_algebra_query_subject_no_subject_filter_returns_all():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="f1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="dog", surface="dog"),
            object=RelationArgument(role="object", concept_id="animal", surface="animal"),
        ),
        RelationFrame(
            relation_id="f2",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="cat", surface="cat"),
            object=RelationArgument(role="object", concept_id="animal", surface="animal"),
        ),
    ]
    results = algebra.query_subject(
        "is_a", frames=frames, allow_inheritance=False, allow_inverse=False,
    )
    assert len(results) == 2


def test_algebra_explain_path():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    base = RelationFrame(
        relation_id="f1",
        relation_key="is_a",
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="A", surface="A"),
    )
    derived = RelationFrame(
        relation_id="f2",
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="leader", surface="leader"),
        inherited_from=["f1"],
    )
    path = algebra.explain_path(derived, [base, derived])
    assert len(path) >= 2
    assert "is_a" in path[0]
    assert "has_role" in path[1]


def test_algebra_golden_inherited_query():
    """Golden test: A is_a B, X has_role A => query has_role for X via inheritance.

    This is the symbolic equivalent of:
        president is_a leader
        Donald Trump president_of United States
        => Donald Trump leader_of United States
    """
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frames = [
        RelationFrame(
            relation_id="isa1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="subject", concept_id="A", surface="A"),
            object=RelationArgument(role="object", concept_id="B", surface="B"),
            confidence=0.8,
        ),
        RelationFrame(
            relation_id="rel1",
            relation_key="has_role",
            relation_family="role",
            subject=RelationArgument(role="subject", concept_id="X", surface="X"),
            object=RelationArgument(role="object", concept_id="A", surface="A"),
            confidence=0.7,
        ),
    ]

    results = algebra.query_subject("has_role", object_concept_id="B", frames=frames, allow_inheritance=True)
    inherited = [f for f in results if f.inherited_from]
    assert len(inherited) >= 1
    assert inherited[0].subject.concept_id == "X"
    assert inherited[0].object.concept_id == "B"
    path = algebra.explain_path(inherited[0], frames + results)
    assert len(path) >= 2


# ── SemanticKernelRuntime integration ────────────────────────────


# ── bind_role ─────────────────────────────────────────────────────


def test_bind_role_binds_subject():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frame = RelationFrame(
        relation_id="f1",
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="leader", surface="leader"),
    )
    new_subject = RelationArgument(
        role="subject", concept_id="Y", surface="Y", confidence=0.9,
    )
    bound = algebra.bind_role(new_subject, frame)
    assert bound.subject.concept_id == "Y"
    assert bound.subject.surface == "Y"
    assert bound.object.concept_id == "leader"
    assert bound.relation_key == "has_role"


def test_bind_role_preserves_fallback():
    """When the new subject argument has empty fields, originals are kept."""
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frame = RelationFrame(
        relation_id="f1",
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="leader", surface="leader"),
    )
    partial = RelationArgument(role="subject", entity_id="e1")
    bound = algebra.bind_role(partial, frame)
    assert bound.subject.entity_id == "e1"
    assert bound.subject.concept_id == "X"
    assert bound.subject.surface == "X"


# ── project_qualifier ─────────────────────────────────────────────


def test_project_qualifier_returns_frame_for_existing_key():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    qual_val = RelationArgument(role="object", concept_id="Z", surface="Z", confidence=0.6)
    frame = RelationFrame(
        relation_id="f1",
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="leader", surface="leader"),
        qualifiers={"location": qual_val},
    )
    projected = algebra.project_qualifier("location", frame)
    assert projected is not None
    assert projected.relation_key == "location"
    assert projected.subject.concept_id == "X"
    assert projected.object.concept_id == "Z"


def test_project_qualifier_returns_none_for_missing_key():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    frame = RelationFrame(
        relation_id="f1",
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", concept_id="X", surface="X"),
        object=RelationArgument(role="object", concept_id="leader", surface="leader"),
        qualifiers={"time": RelationArgument(role="object", concept_id="T1")},
    )
    projected = algebra.project_qualifier("missing_key", frame)
    assert projected is None


def test_project_qualifier_returns_same_source_lineage():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)

    qual_val = RelationArgument(role="object", atom_id="atom:loc1", confidence=0.5)
    frame = RelationFrame(
        relation_id="f1",
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", concept_id="X"),
        object=RelationArgument(role="object", concept_id="leader"),
        qualifiers={"location": qual_val},
        source_edge_ids=["e1"],
        source_atom_ids=["a1"],
        evidence_refs=["ev1"],
    )
    projected = algebra.project_qualifier("location", frame)
    assert projected is not None
    assert "e1" in projected.source_edge_ids
    assert "a1" in projected.source_atom_ids
    assert "ev1" in projected.evidence_refs


def test_runtime_exposes_relation_components():
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
    runtime = SemanticKernelRuntime()
    assert runtime.relation_frame_compiler is not None
    assert runtime.relation_algebra is not None
    assert runtime.predicate_schema_store is not None


def test_runtime_compiles_relation_frames():
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
    from cemm.types.context_kernel import ContextKernel
    from cemm.types.signal import Signal, SignalKind, SourceType
    from cemm.types.permission import Permission
    import time
    import uuid

    runtime = SemanticKernelRuntime()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="a president is a leader",
        observed_at=time.time(),
        context_id="test",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )
    kernel = ContextKernel(id="test")
    result = runtime.run_turn(signal, kernel)
    assert result.diagnostics is not None
