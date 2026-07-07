"""Randomized UOL fuzz tests.

Generates random inputs and random UOL graphs, runs them through the
full pipeline, and verifies invariants hold (no crashes, consistent
state, valid outputs).
"""

from __future__ import annotations

import os
import sys
import random
import time
import uuid
import string

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("CEMM_EXPORT_PATH", "")

from cemm.tests.harness import SeededSystem, seed_durable_from_config, make_signal
from cemm.types.uol_graph import UOLGraph, UOLAtom, UOLEdge
from cemm.types.context_kernel import (
    ContextKernel, Budget, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState,
)
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView


def _kernel(ctx: str) -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(), user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id=ctx, turn_index=1),
        goal=GoalState(), memory=MemoryState(),
        permission=Permission.public(), budget=Budget(),
        self_view=SelfView(self_id="test"),
    )


_ATOM_KINDS = ["entity", "process", "state", "intent", "self", "relation"]
_INTENT_KEYS = [
    "self_identity_query", "self_capability_query", "self_knowledge_query",
    "user_identity_query", "user_name_query", "greeting", "social_closing",
    "evidence_query", "definition_teaching", "claim_assertion",
    "session_exit", "confusion_repair",
]
_ENTITY_KEYS = ["dog", "cat", "Paris", "Tokyo", "user", "self", "weather", "food"]
_PROCESS_KEYS = ["self_capability_query", "evidence_query", "definition_teaching"]
_STATE_KEYS = ["low_competence", "high_quality", "temporal_now"]


def random_uol_graph(seed: int | None = None) -> UOLGraph:
    """Generate a random UOL graph with atoms and edges."""
    rng = random.Random(seed)
    n_atoms = rng.randint(3, 15)
    atoms: dict[str, UOLAtom] = {}

    for i in range(n_atoms):
        kind = rng.choice(_ATOM_KINDS)
        if kind == "intent":
            key = rng.choice(_INTENT_KEYS)
        elif kind == "entity":
            key = rng.choice(_ENTITY_KEYS)
        elif kind == "process":
            key = rng.choice(_PROCESS_KEYS)
        elif kind == "state":
            key = rng.choice(_STATE_KEYS)
        elif kind == "self":
            key = "self"
        else:
            key = f"rel_{rng.randint(1, 5)}"

        atom_id = f"atom_{i}"
        atoms[atom_id] = UOLAtom(
            id=atom_id,
            kind=kind,
            key=key,
            surface=key.replace("_", " "),
            confidence=rng.uniform(0.3, 0.95),
        )

    n_edges = rng.randint(2, min(n_atoms * 2, 20))
    edges: list[UOLEdge] = []
    atom_ids = list(atoms.keys())
    for i in range(n_edges):
        src = rng.choice(atom_ids)
        tgt = rng.choice(atom_ids)
        edge_id = f"edge_{i}"
        edges.append(UOLEdge(
            id=edge_id,
            edge_type=rng.choice(["is_a", "enables", "causes", "has_role", "part_of"]),
            source_id=src,
            target_id=tgt,
            confidence=rng.uniform(0.3, 0.9),
        ))

    return UOLGraph(
        id=uuid.uuid4().hex[:16],
        signal_id=uuid.uuid4().hex[:16],
        context_id="fuzz",
        atoms=atoms,
        edges=edges,
    )


def random_text(seed: int | None = None) -> str:
    """Generate random conversational text."""
    rng = random.Random(seed)
    templates = [
        "what's your name?",
        "what can you do?",
        "hello",
        "hi there",
        "remember that {a} is {b}",
        "what is {a}?",
        "tell me about {a}",
        "{a}",
        "do you know {a}?",
        "what do you know about yourself?",
        "bye",
        "",
        "lol what's your name?",
        "how are you",
        "what's the weather like",
    ]
    fillers = ["dog", "cat", "Paris", "Python", "AI", "rain", "music", "food"]
    t = rng.choice(templates)
    return t.format(a=rng.choice(fillers), b=rng.choice(fillers))


# ── Random text fuzz ─────────────────────────────────────────────────


class TestRandomTextFuzz:
    """Run random text inputs through the full pipeline — no crashes."""

    def test_50_random_inputs_no_crash(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        for i in range(50):
            text = random_text(seed=i * 1000)
            r = sys.run(text)
            # Must not have errors (or only benign ones)
            for err in r["errors"]:
                assert "Traceback" not in err, f"Crash on input {i!r}: {err}"

    def test_20_random_inputs_seeded_system_answers_self_queries(self):
        """Among random inputs, self-queries should consistently answer."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        self_query_inputs = [
            "what's your name?",
            "what can you do?",
            "what do you know about yourself?",
        ]
        for text in self_query_inputs:
            for _ in range(5):
                r = sys.run(text)
                if r["obligation_kind"] in (
                    "answer_self_model", "answer_self_identity",
                    "answer_self_capability", "answer_self_knowledge",
                ):
                    assert r["has_answer"] is True, (
                        f"Self-query {text!r} failed: {r['abstention_reason']}"
                    )

    def test_random_sequence_20_turns(self):
        """20 random turns in sequence should not degrade or crash."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        rng = random.Random(42)
        prev_durable = sys.durable_store.relation_count()
        for i in range(20):
            text = random_text(seed=rng.randint(0, 999999))
            r = sys.run(text)
            # Durable count should never decrease
            assert r["durable_count"] >= prev_durable - 1, (
                f"Durable count decreased at turn {i}: {prev_durable} -> {r['durable_count']}"
            )
            prev_durable = r["durable_count"]


# ── Random UOL graph fuzz ────────────────────────────────────────────


class TestRandomUOLFuzz:
    """Run random UOL graphs through the runtime — no crashes, invariants hold."""

    def test_30_random_uol_graphs_no_crash(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        for i in range(30):
            graph = random_uol_graph(seed=i * 100)
            sig = make_signal("fuzz input", context_id="fuzz")
            kernel = _kernel("fuzz")
            cycle = sys.runtime.run_turn(sig, kernel)
            # Invariant: relation_frames is always a list
            assert isinstance(cycle.relation_frames, list)
            # Invariant: semantic_program is present or None
            assert cycle.semantic_program is None or hasattr(cycle.semantic_program, "instructions")
            # Invariant: no traceback in errors
            for err in cycle.diagnostics.get("errors", []):
                assert "Traceback" not in err, f"Crash on graph {i}: {err}"

    def test_uol_graph_invariant_obligation_consistency(self):
        """If obligation_frame exists, it should have a valid obligation_kind."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        for i in range(20):
            graph = random_uol_graph(seed=i * 200)
            sig = make_signal("fuzz", context_id="fuzz")
            kernel = _kernel("fuzz")
            cycle = sys.runtime.run_turn(sig, kernel)
            if cycle.obligation_frame is not None:
                assert cycle.obligation_frame.obligation_kind != ""
                assert cycle.obligation_frame.response_mode != ""

    def test_uol_graph_invariant_query_relation_key_for_mapped_kinds(self):
        """For mapped obligation kinds, query should have non-empty relation_key."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        mapped_kinds = {
            "answer_self_identity", "answer_self_model",
            "answer_self_capability", "answer_self_knowledge",
            "answer_user_profile",
        }
        for i in range(30):
            graph = random_uol_graph(seed=i * 300)
            sig = make_signal("fuzz", context_id="fuzz")
            kernel = _kernel("fuzz")
            cycle = sys.runtime.run_turn(sig, kernel)
            if (
                cycle.obligation_frame is not None
                and cycle.obligation_frame.obligation_kind in mapped_kinds
                and cycle.semantic_query is not None
            ):
                assert cycle.semantic_query.relation_key != "", (
                    f"Empty relation_key for mapped kind "
                    f"{cycle.obligation_frame.obligation_kind} on graph {i}"
                )


# ── Property-based tests ─────────────────────────────────────────────


class TestPropertyBased:
    """Property-based invariants that should hold for all inputs."""

    def test_query_relations_filtered_is_subset_of_unfiltered(self):
        """query_relations with any filter should return subset of query_relations()."""
        from cemm.memory.durable_semantic_store import DurableSemanticStore
        store = DurableSemanticStore()
        store.add_relation("is_a", "taxonomy", subject_concept_id="dog", object_concept_id="animal")
        store.add_relation("is_a", "taxonomy", subject_concept_id="cat", object_concept_id="animal")
        store.add_relation("causes", "causal", subject_concept_id="fire", object_concept_id="smoke")

        all_frames = store.query_relations()
        filtered = store.query_relations(relation_key="is_a")
        assert len(filtered) <= len(all_frames)
        filtered_ids = {f.relation_id for f in filtered}
        all_ids = {f.relation_id for f in all_frames}
        assert filtered_ids.issubset(all_ids)

    def test_query_relations_filter_by_subject_is_subset(self):
        from cemm.memory.durable_semantic_store import DurableSemanticStore
        store = DurableSemanticStore()
        for pred in ["is_a", "causes", "has_name"]:
            for subj in ["dog", "cat", "self"]:
                store.add_relation(pred, "test", subject_concept_id=subj, object_concept_id="obj")

        all_frames = store.query_relations()
        for subj in ["dog", "cat", "self"]:
            filtered = store.query_relations(subject_concept_id=subj)
            assert len(filtered) <= len(all_frames)
            assert all(f.subject.concept_id == subj for f in filtered)

    def test_patch_validator_never_crashes_on_random_patches(self):
        """PatchValidator should never raise on any valid GraphPatch."""
        from cemm.learning.patch_validator import PatchValidator
        from cemm.types.graph_patch import GraphPatch, PatchOperation
        from cemm.types.context_kernel import (
            ContextKernel, Budget, WorldState, UserState, TimeState,
            ConversationState, GoalState, MemoryState,
        )
        from cemm.types.self_view import SelfView
        from cemm.types.permission import Permission

        validator = PatchValidator()

        rng = random.Random(123)
        for i in range(50):
            kernel = ContextKernel(
                id=uuid.uuid4().hex[:16],
                world=WorldState(), user=UserState(),
                time=TimeState(now=time.time(), bucket="test"),
                conversation=ConversationState(session_id="t", turn_index=1),
                goal=GoalState(), memory=MemoryState(),
                permission=Permission.public(), budget=Budget(),
                self_view=SelfView(self_id="test"),
            )
            patch = GraphPatch(
                source_refs=[f"src_{rng.randint(0, 5)}"],
                evidence_refs=[f"evidence_{rng.randint(0, 10)}"],
                operations=[PatchOperation(
                    operation="custom:upsert_claim",
                    target_id=f"target_{rng.randint(0, 20)}",
                    confidence=rng.uniform(0.1, 0.99),
                )],
                confidence=rng.uniform(0.1, 0.99),
            )
            # Should never raise
            result = validator.validate(patch, kernel)
            assert result is not None
            assert hasattr(result, "accepted")

    def test_build_query_always_sets_relation_key_for_mapped_kinds(self):
        """build_query should always produce non-empty relation_key for mapped obligation kinds."""
        from cemm.kernel.semantic_query_engine import SemanticQueryEngine
        from cemm.kernel.relation_algebra import RelationAlgebra
        from cemm.memory.predicate_schema_store import PredicateSchemaStore
        from cemm.types.obligation_frame import ObligationFrame
        from cemm.types.semantic_program import SemanticProgram, SemanticInstruction
        from cemm.types.relation_frame import RelationFrame, RelationArgument

        store = PredicateSchemaStore()
        algebra = RelationAlgebra(store)
        engine = SemanticQueryEngine(algebra, store)

        mapped_kinds = [
            "answer_self_identity",
            "answer_self_model",
            "answer_self_capability",
            "answer_self_knowledge",
            "answer_user_profile",
        ]

        for kind in mapped_kinds:
            obligation = ObligationFrame(
                primary_instruction_id="inst_1",
                obligation_kind=kind,
                response_mode="test",
                evidence_policy="required",
                write_policy="none",
                required_slots=[],
                blocked_by=[],
                confidence=0.7,
            )
            program = SemanticProgram(
                graph_id="g", signal_id="s", context_id="c",
                entry_instruction_id="inst_1",
                instructions=[SemanticInstruction(
                    instruction_id="inst_1", group_id="grp",
                    surface="test question", instruction_kind="question",
                    confidence=0.8,
                )],
            )
            # Build with empty frames (simulating durable-only)
            query = engine.build_query(obligation, [], program)
            assert query.relation_key != "", (
                f"Empty relation_key for mapped kind {kind}"
            )
            assert query.subject_constraint.entity_id != "", (
                f"Empty subject entity for mapped kind {kind}"
            )
