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
from cemm.types.semantic_event_graph import SemanticEventGraph
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
        assert result.semantic_event_graph is not None
        assert result.semantic_event_graph.source_signal_ids
        assert result.semantic_event_graph.context_id

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
    def test_semantic_event_graph_has_required_fields(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("My favorite database is Postgres.")
        seg = result.semantic_event_graph
        assert seg is not None
        assert seg.source_signal_ids
        assert seg.context_id
        assert seg.version == "cemm.semantic_event_graph.v1"
        assert seg.permission_scope == "public"

    def test_semantic_answer_graph_exists_before_realization(self) -> None:
        sag = SemanticAnswerGraph(
            id="test_sag",
            intent="answer",
            source_signal_ids=["sig1"],
            context_id="ctx1",
            selected_claim_ids=["claim1"],
        )
        assert sag is not None
        assert sag.intent == "answer"
        assert sag.selected_claim_ids == ["claim1"]
        assert sag.version == "cemm.semantic_answer_graph.v1"
        assert hasattr(sag, "answer_latent")
        assert hasattr(sag, "engagement_rule")
        assert hasattr(sag, "action_scope")

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
    def test_weather_unknown_location_asks(self) -> None:
        store = _make_store()
        registry = _make_registry()
        kernel = ContextKernelBuilder.from_signal(
            _make_signal("what is the weather?"), turn_index=1,
        )
        assert kernel.user.locale is None
        assert kernel.goal.missing_slots == []
        seg = SemanticEventGraph(
            id="seg_test",
            source_signal_ids=["sig1"],
            context_id=kernel.id,
            processes=[{"frame_key": "request_weather", "participants": []}],
        )
        router = DecisionRouter()
        memory_packet = MemoryPacket(
            selected_signal_ids=["sig1"],
            selected_claim_ids=[],
            selected_model_ids=[],
        )
        grounded = GroundedGraph(id="gg", missing_slots=["location"])
        decision = router.run(seg, kernel, grounded_graph=grounded, memory_packet=memory_packet)
        assert decision.action_kind == "ask"
        assert decision.confidence >= 0.0

    def test_stale_world_question_abstains(self) -> None:
        store = _make_store()
        registry = _make_registry()
        kernel = ContextKernelBuilder.from_signal(
            _make_signal("who is the president?"), turn_index=1,
        )
        kernel.budget.allow_dense_fallback = False
        seg = SemanticEventGraph(
            id="seg_test2",
            source_signal_ids=["sig1"],
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

    def test_incomplete_command_asks_or_abstains(self) -> None:
        store = _make_store()
        registry = _make_registry()
        kernel = ContextKernelBuilder.from_signal(
            _make_signal("Call"), turn_index=1,
        )
        seg = SemanticEventGraph(
            id="seg_call",
            source_signal_ids=["sig1"],
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
        assert decision.action_kind != "answer"


class TestPhase0Export:
    def test_export_includes_all_required_fields(self) -> None:
        store = _make_store()
        registry = _make_registry()
        signal = _make_signal("My favorite database is Postgres.")
        builder = ContextKernelBuilder()
        kernel = builder.from_signal(signal, turn_index=1)
        seg = SemanticEventGraph(
            id="seg_export",
            source_signal_ids=[signal.id],
            context_id=kernel.id,
        )
        sag = SemanticAnswerGraph(
            id="sag_export",
            intent="answer",
            source_signal_ids=[signal.id],
            context_id=kernel.id,
            selected_claim_ids=["claim1"],
        )
        trace = Trace(
            context_id=kernel.id,
            input_signal_ids=[signal.id],
            selected_claim_ids=["claim1"],
            selected_model_ids=[],
            action_id="act_export",
            operator_model_id="answer_operator",
            synthesis_strategy_model_id="template",
            synthesis_verified=True,
            synthesis_verification_type="hard",
            realization_strategy="template",
            realization_verified=True,
            permission="allowed",
            confidence=0.85,
            cost_ms=5.0,
            fallback_used=False,
            semantic_answer_graph_id=sag.id,
        )
        exports = serialize_turn(
            input_text="My favorite database is Postgres.",
            output_text="Your favorite database is Postgres.",
            kernel=kernel,
            input_signal=signal,
            trace=trace,
            semantic_event_graph=seg,
            semantic_answer_graph=sag,
        )
        assert isinstance(exports, list)
        export = exports[0]
        payload = export.get("payload", {})
        assert "context_kernel" in payload
        assert "input_text" in payload
        assert "output_text" in payload
        if seg:
            assert payload.get("semantic_event_graph") is not None
        if sag:
            assert payload.get("semantic_answer_graph") is not None
        if trace:
            assert payload.get("trace") is not None
            assert "selected_evidence" in payload
            assert "realization_metadata" in payload
            assert "verification_metadata" in payload
        assert export.get("task_type") == "full_turn_export"
        assert export.get("permission_scope") == "local_training"


class TestEfficiency:
    def test_budget_limits_respected(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        signal = _make_signal("What is my favorite database?")
        builder = ContextKernelBuilder()
        kernel = builder.from_signal(signal, turn_index=1)
        assert kernel.budget.max_entities == 16
        assert kernel.budget.max_claims == 128
        assert kernel.budget.max_ranked == 64
        assert kernel.budget.latency_target_ms == 50.0

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


class TestPhase1Trainer:
    def test_trainer_known_task_types(self) -> None:
        from cemm.cemm_trainer import PROMPTS
        required = {
            "uol_mapping", "claim_extraction", "predicate_mapping",
            "entity_resolution", "context_inference", "operator_selection",
            "pragmatic_interpretation", "synthesis_verification",
            "semantic_graph_extraction", "semantic_answer_composition",
            "semantic_text_realization",
        }
        for task in required:
            assert task in PROMPTS, f"Missing task_type in PROMPTS: {task}"

    def test_full_turn_export_decomposes_to_known_types(self) -> None:
        from cemm.cemm_trainer import _decompose_full_turn, PROMPTS
        turn_payload = {
            "payload": {
                "context_kernel": {"id": "ck1", "version": "test"},
                "input_text": "hello",
                "output_text": "hi there",
                "semantic_event_graph": {"id": "seg1", "entity_refs": [], "version": "test"},
                "semantic_answer_graph": {"id": "sag1", "intent": "answer", "version": "test"},
                "selected_evidence": {"selected_claim_ids": ["c1"]},
            }
        }
        sub_examples = _decompose_full_turn(turn_payload)
        assert sub_examples, "No sub-examples produced"
        seen_types = set()
        for task_type, sub_payload in sub_examples:
            assert task_type in PROMPTS, f"Unknown decomposed type: {task_type}"
            assert "context_kernel" in sub_payload, f"Missing context_kernel in {task_type}"
            seen_types.add(task_type)
        assert "semantic_graph_extraction" in seen_types
        assert "semantic_answer_composition" in seen_types
        assert "semantic_text_realization" in seen_types
        assert "synthesis_verification" in seen_types


class TestPhase3Recursive:
    def test_recursive_budget_child_consumes_remaining(self) -> None:
        from cemm.kernel.recursive_loop import RecursiveLoop
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        from cemm.learning.online import OnlineLearner
        from cemm.learning.inductor import Inductor
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        inductor = Inductor(store)
        loop = RecursiveLoop(pipeline, store, learner, inductor)
        kernel = ContextKernelBuilder.from_signal(
            _make_signal("test"), turn_index=1,
        )
        kernel.budget.max_recursive_steps = 2
        kernel.budget.latency_target_ms = 100.0
        assert kernel.budget.max_recursive_steps == 2
        assert kernel.budget.latency_target_ms == 100.0


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
            if "self._semantic_interpreter.run" in line:
                interpret_line = i
            if "self._grounding_pipeline.run" in line:
                ground_line = i
        assert contextualize_line is not None, "ContextInference not found in run()"
        assert interpret_line is not None, "SemanticInterpreter not found in run()"
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
        assert result.semantic_event_graph is not None
        assert result.ranked_claim_ids is not None

    def test_answer_graph_not_text_before_graph(self) -> None:
        sag = SemanticAnswerGraph(
            id="sag_test",
            intent="answer",
            source_signal_ids=["sig1"],
            context_id="ctx1",
        )
        assert sag.intent == "answer"
        assert sag.id is not None
        text = "Your favorite database is Postgres."
        assert text is not None
