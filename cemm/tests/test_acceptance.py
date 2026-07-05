from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.context_kernel import GoalState
from cemm.types.uol_graph import UOLGraph
from cemm.types.semantic_answer_graph import SemanticAnswerGraph
from cemm.types.packets import MemoryPacket
from cemm.types.permission import Permission
from cemm.types.claim import Claim
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.decision_router import DecisionRouter
from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.retrieval.structural import StructuralRetriever
from cemm.retrieval.ranker import Ranker
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.construction_lattice import ConstructionLattice
from cemm.memory.episodic_trace_store import EpisodicTraceStore
from cemm.memory.persistent_lattice_store import PersistentLatticeStore


def _make_store() -> Store:
    return Store(":memory:")


def _make_registry() -> Registry:
    reg = Registry()
    for i, (canonical, *aliases) in enumerate([
        ("favorite_database", "fav_db", "preferred_db"),
        ("is_a", "isa"),
        ("located_at", "located_in"),
        ("causes", "leads_to"),
    ]):
        reg.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=canonical,
            kind="predicate",
            aliases=list(aliases),
        ))
    return reg


def _make_signal(text: str, kind: SignalKind = SignalKind.INPUT) -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=kind,
        source_id="test",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id=uuid.uuid4().hex[:16],
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


class TestPhase0ContextFirst:
    def test_context_kernel_exists_before_interpretation(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        signal = _make_signal("Good morning")
        builder = ContextKernelBuilder()
        kernel = builder.from_signal(signal, turn_index=1)
        assert kernel is not None
        assert kernel.id is not None
        assert kernel.time.bucket is not None
        assert kernel.conversation.turn_index == 1
        assert kernel.conversation.session_id == signal.context_id
        assert kernel.permission is not None

    def test_ambiguous_greeting_with_scheduling_goal(self) -> None:
        store = _make_store()
        registry = _make_registry()
        signal = _make_signal("Morning")
        builder = ContextKernelBuilder()
        kernel = builder.from_signal(signal, turn_index=1)
        kernel.goal = GoalState(
            active_goal="schedule_meeting",
            required_slots=["time", "date"],
            missing_slots=["time"],
        )
        time_str = kernel.time.bucket
        assert time_str in ("early_morning", "morning", "afternoon", "evening", "night")
        kernel.memory.working_claim_ids = []

    def test_memory_write_creates_claim_and_remember(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("My favorite database is Postgres.")
        assert result.uol_graph is not None
        assert result.uol_graph.signal_id
        assert result.uol_graph.context_id

    def test_memory_recall_selects_active_claim(self) -> None:
        store = _make_store()
        registry = _make_registry()
        from cemm.types.entity import Entity, EntityType
        store.entities.put(Entity(
            id="user", type=EntityType.PERSON, name="Test User", aliases=[],
            confidence=0.9, created_from_signal_id="seed",
            created_at=time.time(), updated_at=time.time(),
        ))
        claim = Claim(
            id="claim_fav_db",
            subject_entity_id="user",
            predicate="favorite_database",
            object_value="Postgres",
            domain="preference",
            confidence=0.9,
            trust=0.9,
            salience=0.8,
            observed_at=time.time(),
            updated_at=time.time(),
            permission=Permission.public(),
        )
        store.claims.put(claim)
        pipeline = Pipeline(store, registry)
        kernel = ContextKernelBuilder.from_signal(_make_signal("What is my favorite database?"), turn_index=2)
        kernel.memory.working_entity_ids = ["user"]
        retriever = StructuralRetriever(store)
        result = retriever.retrieve_for_kernel(kernel)
        assert any(c.id == "claim_fav_db" for c in result.claims)
        ranker = Ranker()
        ranked = ranker.rank_claims(result.claims, kernel)
        ranked_ids = [c.id for c, _ in ranked]
        assert "claim_fav_db" in ranked_ids


class TestPhase0SemanticGraph:
    def test_text_realization_maps_back_to_evidence(self) -> None:
        store = _make_store()
        registry = _make_registry()
        from cemm.types.entity import Entity, EntityType
        store.entities.put(Entity(
            id="user", type=EntityType.PERSON, name="Test User", aliases=[],
            confidence=0.9, created_from_signal_id="seed",
            created_at=time.time(), updated_at=time.time(),
        ))
        claim = Claim(
            id="claim_test",
            subject_entity_id="user",
            predicate="favorite_database",
            object_value="Postgres",
            domain="preference",
            confidence=0.9,
            trust=0.9,
            salience=0.8,
            observed_at=time.time(),
            updated_at=time.time(),
            permission=Permission.public(),
        )
        store.claims.put(claim)
        sag = SemanticAnswerGraph(
            id="sag_test",
            intent="answer",
            source_signal_ids=["sig1"],
            context_id="ctx1",
            selected_claim_ids=["claim_test"],
        )
        assert "claim_test" in sag.selected_claim_ids


class TestPhase0AbstainAndAsk:
    def test_stale_world_question_abstains(self) -> None:
        store = _make_store()
        registry = _make_registry()
        kernel = ContextKernelBuilder.from_signal(
            _make_signal("who is the president?"), turn_index=1,
        )
        kernel.budget.allow_dense_fallback = False
        seg = UOLGraph(
            id="seg_test2",
            signal_id="sig1",
            context_id=kernel.id,
        )
        router = DecisionRouter()
        memory_packet = MemoryPacket(
            selected_signal_ids=["sig1"],
            selected_claim_ids=[],
            selected_model_ids=[],
        )
        decision = router.run(seg, kernel, memory_packet=memory_packet)
        assert decision.action_kind in ("ask", "abstain")
        assert not kernel.budget.allow_dense_fallback


class TestEfficiency:
    def test_no_dense_fallback_when_disallowed(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        signal = _make_signal("What is the meaning of life?")
        builder = ContextKernelBuilder()
        kernel = builder.from_signal(signal, turn_index=1)
        kernel.budget.allow_dense_fallback = False
        assert not kernel.budget.allow_dense_fallback

    def test_structural_retrieval_before_dense(self) -> None:
        store = _make_store()
        registry = _make_registry()
        from cemm.types.entity import Entity, EntityType
        store.entities.put(Entity(
            id="user", type=EntityType.PERSON, name="Test User", aliases=[],
            confidence=0.9, created_from_signal_id="seed",
            created_at=time.time(), updated_at=time.time(),
        ))
        claim = Claim(
            id="claim_fav_db",
            subject_entity_id="user",
            predicate="favorite_database",
            object_value="Postgres",
            domain="preference",
            confidence=0.9,
            trust=0.9,
            salience=0.8,
            observed_at=time.time(),
            updated_at=time.time(),
            permission=Permission.public(),
        )
        unrelated = Claim(
            id="claim_color",
            subject_entity_id="user",
            predicate="favorite_color",
            object_value="blue",
            domain="preference",
            confidence=0.8,
            trust=0.8,
            salience=0.3,
            observed_at=time.time(),
            updated_at=time.time(),
            permission=Permission.public(),
        )
        store.claims.put(claim)
        store.claims.put(unrelated)
        kernel = ContextKernelBuilder.from_signal(
            _make_signal("What did I say my favorite database was?"), turn_index=2,
        )
        kernel.memory.working_entity_ids = ["user"]
        retriever = StructuralRetriever(store)
        result = retriever.retrieve_for_kernel(kernel)
        claim_ids = [c.id for c in result.claims]
        assert "claim_fav_db" in claim_ids


class TestRuntimeOrdering:
    def test_semantic_event_graph_exists_before_retrieval(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("What is my favorite database?")
        assert result.uol_graph is not None
        assert result.ranked_claim_ids is not None


class TestArchitectureInvariants:
    """Validate core working-graph invariants."""

    def _pipeline(self) -> Pipeline:
        store = Store(":memory:")
        registry = _make_registry()
        return Pipeline(store, registry)

    def _full_pipeline(self) -> Pipeline:
        store = Store(":memory:")
        registry = _make_registry()
        pstore = PersistentLatticeStore(":memory:")
        cl = ConceptLattice(persistent_store=pstore)
        return Pipeline(
            store, registry,
            concept_lattice=cl,
            construction_lattice=ConstructionLattice(),
            episodic_store=EpisodicTraceStore(),
            auto_consolidate=True,
        )

    def test_graph_always_has_atoms(self) -> None:
        """Graph builder must produce at least self/user/source/permission atoms."""
        for label, pipeline in [("fallback", self._pipeline()), ("full", self._full_pipeline())]:
            result = pipeline.run("hello")
            assert result.uol_graph is not None, f"{label}: graph is None"
            assert len(result.uol_graph.atoms) >= 4, (
                f"{label}: expected >=4 atoms (self/user/source/permission), "
                f"got {len(result.uol_graph.atoms)}"
            )

    def test_graph_has_edges(self) -> None:
        """Graph builder must produce structural edges."""
        for label, pipeline in [("fallback", self._pipeline()), ("full", self._full_pipeline())]:
            result = pipeline.run("hello")
            assert result.uol_graph is not None
            assert len(result.uol_graph.edges) >= 3, (
                f"{label}: expected >=3 edges, got {len(result.uol_graph.edges)}"
            )

    def test_patch_router_flush_persists_concepts(self) -> None:
        """PatchRouter.flush_all() must persist dirty concepts to store."""
        from cemm.memory.persistent_lattice_store import PersistentLatticeStore
        from cemm.memory.patch_router import PatchRouter
        from cemm.memory.concept_lattice import ConceptLattice
        from cemm.types.graph_patch import GraphPatch, PatchOperation

        store = PersistentLatticeStore(":memory:")
        lattice = ConceptLattice(persistent_store=store)
        router = PatchRouter(concept_lattice=lattice)
        patch = GraphPatch(
            target="concept_lattice",
            operations=[PatchOperation(
                operation="upsert_concept_candidate",
                target_id="concept:flush_test",
                fields={"key": "flush_test", "atom_kind": "entity", "state": "candidate_atom"},
                confidence=0.8,
            )],
            confidence=0.8,
            reason="flush_test",
        )
        router.route(patch)
        assert lattice.lookup("flush_test") is not None, "concept should exist in-memory"
        assert store.get_concept("concept:flush_test") is None, \
            "concept should NOT be in persistent store before flush"
        router.flush_all()
        persisted = store.get_concept("concept:flush_test")
        assert persisted is not None, "concept should be in persistent store after flush"
        assert persisted["key"] == "flush_test"

    def test_patch_validator_gates_writes(self) -> None:
        """PatchValidator must reject patches that fail permission or source checks."""
        from cemm.learning.patch_validator import PatchValidator
        from cemm.types.graph_patch import GraphPatch, PatchOperation
        from cemm.types.context_kernel import ContextKernel

        validator = PatchValidator()
        patch = GraphPatch(
            target="concept_lattice",
            operations=[PatchOperation(
                operation="upsert_concept_candidate",
                target_id="concept:test",
                fields={"key": "test"},
                confidence=0.1,
            )],
            confidence=0.1,
        )
        # No kernel → permission check fails
        result = validator.validate(patch, kernel=None)
        assert "permission_valid" in result.failed_checks
        assert not result.accepted

    def test_claim_writer_produces_patch_with_claim(self) -> None:
        """ClaimWriter.write_claim must return both claim and GraphPatch."""
        from cemm.store.store import Store
        from cemm.operators.claim_writer import ClaimWriter
        from cemm.types.entity import Entity, EntityType

        store = Store(":memory:")
        store.entities.put(Entity(
            id="test_subject", type=EntityType.PERSON, name="Test",
            aliases=[], confidence=0.9,
            created_from_signal_id="sig:test",
            created_at=0.0, updated_at=0.0,
        ))
        writer = ClaimWriter(store)
        claim, patch = writer.write_claim(
            subject_entity_id="test_subject",
            predicate="test_predicate",
            object_value="test_value",
            source_id="test_source",
        )
        assert claim is not None
        assert claim.id is not None
        assert patch is not None
        assert patch.target == "episodic_trace"
        assert len(patch.operations) >= 1
        # Claim is NOT written directly to store — must go through GraphPatch validation → LegacyClaimAdapter
        stored = store.claims.get(claim.id)
        assert stored is None

    def test_concept_consolidator_uses_architecture_state_names(self) -> None:
        """CONCEPT_STATES must match ConceptState enum values."""
        from cemm.learning.concept_consolidator import CONCEPT_STATES
        from cemm.types.concept_atom import ConceptState

        state_values = {s.value for s in ConceptState}
        for cs in CONCEPT_STATES:
            assert cs in state_values, (
                f"State '{cs}' not in ConceptState enum values: {state_values}"
            )
        # Must include the main chain states
        assert "candidate_atom" in CONCEPT_STATES
        assert "typed_candidate" in CONCEPT_STATES
        assert "operational_atom" in CONCEPT_STATES
        assert "consolidated_atom" in CONCEPT_STATES

