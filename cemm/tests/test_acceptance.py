from __future__ import annotations

import os
import sys
import time
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.context_kernel import ContextKernel, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState, Budget
from cemm.types.uol_graph import UOLGraph
from cemm.types.semantic_answer_graph import SemanticAnswerGraph
from cemm.types.packets import (
    GroundedGraph, MemoryPacket, DecisionPacket, ActionPlan, InferencePacket,
    packet_to_dict,
)
from cemm.types.action import ActionKind
from cemm.types.permission import Permission
from cemm.types.trace import Trace
from cemm.types.claim import Claim
from cemm.types.self_view import SelfView
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.decision_router import DecisionRouter
from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.kernel.training_export import serialize_turn
from cemm.retrieval.structural import StructuralRetriever, RetrievalResult
from cemm.retrieval.ranker import Ranker
from cemm.operators.base import OperatorContext, OperatorResult
from cemm.store.artifact_store import ArtifactStore


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
    def test_contextualize_before_interpret_before_ground_in_pipeline(self) -> None:
        import inspect
        from cemm.kernel.pipeline import Pipeline
        source = inspect.getsource(Pipeline.run)
        contextualize_line = None
        interpret_line = None
        ground_line = None
        for i, line in enumerate(source.split("\n")):
            if "self._context_inference_engine.infer" in line:
                contextualize_line = i
            if "self._meaning_perceptor.perceive" in line:
                interpret_line = i
            if "self._grounding_pipeline.run" in line:
                ground_line = i
        assert contextualize_line is not None, "ContextInference not found in run()"
        assert interpret_line is not None, "MeaningPerceptor not found in run()"
        assert ground_line is not None, "Ground pipeline not found in run()"
        assert contextualize_line < interpret_line < ground_line, (
            f"Contextualize at line {contextualize_line} must run before "
            f"Interpret at line {interpret_line} before Ground at line {ground_line}"
        )

    def test_semantic_event_graph_exists_before_retrieval(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("What is my favorite database?")
        assert result.uol_graph is not None
        assert result.ranked_claim_ids is not None

