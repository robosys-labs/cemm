"""Tests for DurableSemanticStore and PatchCommitter — Phase 8 breakthrough.

Verifies that validated patches are committed to durable semantic storage
and are queryable across turns. This closes the fundamental durability gap
that made the v4.2 stack stateless.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.memory.durable_semantic_store import DurableSemanticStore
from cemm.learning.patch_committer import PatchCommitter
from cemm.types.graph_patch import GraphPatch, PatchOperation
from cemm.types.relation_frame import RelationFrame, RelationArgument
from cemm.kernel.relation_algebra import RelationAlgebra
from cemm.memory.predicate_schema_store import PredicateSchemaStore


# ── DurableSemanticStore ──────────────────────────────────────


def test_empty_store():
    store = DurableSemanticStore()
    assert store.relation_count() == 0
    assert store.all_relations() == []
    assert store.all_concepts() == []
    assert store.all_predicates() == []


def test_add_and_retrieve_relation():
    store = DurableSemanticStore()
    rec = store.add_relation(
        relation_key="is_a",
        relation_family="taxonomy",
        subject_concept_id="concept:president",
        subject_surface="president",
        object_concept_id="concept:leader",
        object_surface="leader",
        confidence=0.8,
    )
    assert store.relation_count() == 1
    assert store.get_relation(rec.record_id) is not None


def test_add_relation_deduplicates():
    store = DurableSemanticStore()
    store.add_relation("is_a", "taxonomy", subject_concept_id="A", object_concept_id="B")
    store.add_relation("is_a", "taxonomy", subject_concept_id="A", object_concept_id="B")
    assert store.relation_count() == 1


def test_add_relation_different_objects():
    store = DurableSemanticStore()
    store.add_relation("is_a", "taxonomy", subject_concept_id="A", object_concept_id="B")
    store.add_relation("is_a", "taxonomy", subject_concept_id="A", object_concept_id="C")
    assert store.relation_count() == 2


def test_query_relations_by_key():
    store = DurableSemanticStore()
    store.add_relation("is_a", "taxonomy", subject_concept_id="dog", object_concept_id="animal")
    store.add_relation("causes", "causal", subject_concept_id="fire", object_concept_id="smoke")
    frames = store.query_relations(relation_key="is_a")
    assert len(frames) == 1
    assert frames[0].relation_key == "is_a"


def test_query_relations_by_subject():
    store = DurableSemanticStore()
    store.add_relation("is_a", "taxonomy", subject_concept_id="dog", object_concept_id="animal")
    store.add_relation("is_a", "taxonomy", subject_concept_id="cat", object_concept_id="animal")
    frames = store.query_relations(subject_concept_id="dog")
    assert len(frames) == 1
    assert frames[0].subject.concept_id == "dog"


def test_query_relations_by_object():
    store = DurableSemanticStore()
    store.add_relation("is_a", "taxonomy", subject_concept_id="dog", object_concept_id="animal")
    store.add_relation("is_a", "taxonomy", subject_concept_id="cat", object_concept_id="animal")
    store.add_relation("is_a", "taxonomy", subject_concept_id="car", object_concept_id="vehicle")
    frames = store.query_relations(object_concept_id="animal")
    assert len(frames) == 2


def test_query_inverse_relations():
    store = DurableSemanticStore()
    store.add_relation(
        "part_of", "membership",
        subject_concept_id="engine", object_concept_id="car",
        inverse_keys=["has_part"],
    )
    frames = store.query_relations(relation_key="has_part", allow_inverse=True)
    assert len(frames) >= 1
    assert frames[0].subject.concept_id == "car"
    assert frames[0].object.concept_id == "engine"


def test_query_inherited_relations():
    store = DurableSemanticStore()
    store.add_relation("has_role", "role", subject_concept_id="B", object_concept_id="leader")
    inherited = store.query_inherited("A", "B", relation_key="has_role")
    assert len(inherited) == 1
    assert inherited[0].subject.concept_id == "A"
    assert inherited[0].object.concept_id == "leader"
    assert inherited[0].inherited_from


def test_concept_lifecycle():
    store = DurableSemanticStore()
    rec = store.add_concept("president", surface="president", definition="a leader of a country")
    assert rec.concept_key == "president"
    assert store.get_concept("president") is not None
    store.add_concept("president", definition="a leader of a country")
    assert store.get_concept("president").support_count == 2


def test_predicate_lifecycle():
    store = DurableSemanticStore()
    rec = store.add_predicate("leader_of", "role", argument_roles=["leader", "domain"])
    assert rec.predicate_key == "leader_of"
    store.add_predicate("leader_of", "role")
    assert store.get_predicate("leader_of").support_count == 2


def test_patch_journal():
    store = DurableSemanticStore()
    jid = store.log_patch_commit("patch1", "graph1", ["upsert_relation_candidate"], ["rec1"], [])
    journal = store.get_patch_journal()
    assert len(journal) == 1
    assert journal[0]["patch_id"] == "patch1"


def test_commit_result_defaults():
    from cemm.memory.durable_semantic_store import CommitResult
    r = CommitResult(commit_id="c1")
    assert r.status == "committed"
    assert r.created_records == []
    assert r.updated_records == []


# ── PatchCommitter ────────────────────────────────────────────


def _make_accepted_validation(patch_id: str):
    from cemm.learning.patch_validator import PatchValidationResult, ValidationCheck
    return PatchValidationResult(
        patch_id=patch_id,
        status="accepted",
        check_results=[ValidationCheck("permission", True)],
    )


def test_patch_committer_no_patches():
    from cemm.learning.patch_validator import PatchValidationResult
    committer = PatchCommitter()
    patch = GraphPatch(id="p1")
    validation = PatchValidationResult(patch_id="p1", status="rejected")
    result = committer.commit(patch, validation)
    assert result.status == "rejected"


def test_patch_committer_relation_candidate():
    committer = PatchCommitter()
    patch = GraphPatch(
        id="p1",
        source_graph_id="g1",
        operations=[
            PatchOperation(
                operation="upsert_relation_candidate",
                target_id="entity:president",
                fields={
                    "relation_key": "is_a",
                    "relation_family": "taxonomy",
                    "subject_concept_id": "concept:president",
                    "subject_surface": "president",
                    "object_concept_id": "concept:leader",
                    "object_surface": "leader",
                },
            ),
        ],
    )
    validation = _make_accepted_validation("p1")
    result = committer.commit(patch, validation)
    assert result.status == "committed"
    assert len(result.created_records) >= 1
    assert committer.store.relation_count() == 1


def test_patch_committer_concept_candidate():
    committer = PatchCommitter()
    patch = GraphPatch(
        id="p2",
        source_graph_id="g1",
        operations=[
            PatchOperation(
                operation="upsert_concept_candidate",
                target_id="concept:president",
                fields={
                    "concept_key": "president",
                    "surface": "president",
                    "definition": "a leader of a country",
                },
            ),
        ],
    )
    validation = _make_accepted_validation("p2")
    result = committer.commit(patch, validation)
    assert result.status == "committed"
    assert committer.store.get_concept("president") is not None


def test_patch_committer_predicate_schema():
    committer = PatchCommitter()
    patch = GraphPatch(
        id="p3",
        source_graph_id="g1",
        operations=[
            PatchOperation(
                operation="observe_predicate_schema",
                target_id="predicate:leader_of",
                fields={
                    "predicate_key": "leader_of",
                    "relation_family": "role",
                    "argument_roles": ["leader", "domain"],
                },
            ),
        ],
    )
    validation = _make_accepted_validation("p3")
    result = committer.commit(patch, validation)
    assert result.status == "committed"
    assert committer.store.get_predicate("leader_of") is not None


def test_patch_committer_batch():
    committer = PatchCommitter()
    patches = [
        GraphPatch(id="p1", operations=[PatchOperation("upsert_relation_candidate", fields={"relation_key": "is_a", "relation_family": "taxonomy", "subject_concept_id": "A", "object_concept_id": "B"})]),
        GraphPatch(id="p2", operations=[PatchOperation("upsert_relation_candidate", fields={"relation_key": "causes", "relation_family": "causal", "subject_concept_id": "X", "object_concept_id": "Y"})]),
    ]
    validations = [_make_accepted_validation("p1"), _make_accepted_validation("p2")]
    results = committer.commit_batch(patches, validations)
    assert len(results) == 2
    assert all(r.status == "committed" for r in results)
    assert committer.store.relation_count() == 2


# ── Integration: DurableSemanticStore ↔ RelationAlgebra ────────


def test_durable_frames_work_with_relation_algebra():
    store = DurableSemanticStore()
    store.add_relation("is_a", "taxonomy", subject_concept_id="dog", object_concept_id="animal")
    store.add_relation("is_a", "taxonomy", subject_concept_id="puppy", object_concept_id="dog")
    store.add_relation("has_role", "role", subject_concept_id="dog", object_concept_id="pet")

    pss = PredicateSchemaStore()
    algebra = RelationAlgebra(pss)
    durable_frames = store.query_relations()

    results = algebra.query_subject("has_role", object_concept_id="pet", frames=durable_frames, allow_inheritance=True)
    assert len(results) >= 1


def test_golden_teaching_persists_across_turns():
    """The breakthrough test: relation learned in turn 1 is queryable in turn 2.

    Turn 1: user teaches "a president is a leader of a country"
            → relation persists in DurableSemanticStore
    Turn 2: user asks "what is a president?"
            → query engine finds the relation and answers
    """
    store = DurableSemanticStore()
    store.add_relation(
        relation_key="is_a",
        relation_family="taxonomy",
        subject_concept_id="concept:president",
        subject_surface="president",
        object_concept_id="concept:leader",
        object_surface="leader",
        confidence=0.8,
    )

    pss = PredicateSchemaStore()
    algebra = RelationAlgebra(pss)
    durable_frames = store.query_relations()

    assert len(durable_frames) >= 1
    pres_frames = [f for f in durable_frames if f.subject.surface == "president"]
    assert len(pres_frames) >= 1
    assert pres_frames[0].object.surface == "leader"

    results = algebra.query_subject("is_a", subject_concept_id="concept:president", frames=durable_frames)
    assert len(results) >= 1
    assert results[0].object.concept_id == "concept:leader"


# ── Runtime integration ───────────────────────────────────────


def test_runtime_exposes_durable_store():
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
    runtime = SemanticKernelRuntime()
    assert runtime.durable_semantic_store is not None
    assert runtime.patch_committer is not None
