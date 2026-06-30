import sys; sys.path.insert(0, "C:\\dev\\cemm")
import pytest
import uuid
import time
from unittest.mock import Mock, MagicMock

from cemm.types.packets import (
    GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket,
    ActionPlan, RankingTraceEntry,
)
from cemm.types.semantic_event_graph import SemanticEventGraph, SemanticEdge
from cemm.types.context_kernel import ContextKernel, TimeState, GoalState, MemoryState, Budget, Permission as KernelPermission
from cemm.types.permission import Permission
from cemm.kernel.grounding import GroundingPipeline
from cemm.kernel.entity_resolver import EntityResolver
from cemm.kernel.frame_engine import FrameEngine
from cemm.kernel.decision_router import DecisionRouter
from cemm.causal.inference import CausalInference
from cemm.store.store import Store


# ── fixtures ────────────────────────────────────────────────────


@pytest.fixture
def kernel():
    kernel = ContextKernel(
        id="test_kernel",
        self_state_id="self_main",
        time=TimeState(now=time.time()),
        goal=GoalState(required_slots=["subject"], missing_slots=["subject"]),
        memory=MemoryState(),
        budget=Budget(),
        permission=Permission.public(),
    )
    kernel.user.known = True
    kernel.conversation.session_id = "sess_1"
    return kernel


@pytest.fixture
def seg():
    return SemanticEventGraph(
        id="seg_1",
        source_signal_ids=["sig_1"],
        context_id="ctx_1",
        entity_refs=[{"name": "test_entity"}],
        processes=[{"frame_key": "request_clarification", "confidence": 0.8}],
        states=[],
        temporal_edges=[SemanticEdge(source_id="a", target_id="b", relation="before")],
        causal_edges=[SemanticEdge(source_id="a", target_id="b", relation="causes")],
        confidence=0.7,
    )


# ── canonical type instantiation ──────────────────────────────


def test_canonical_types_instantiate():
    gg = GroundedGraph(semantic_event_graph_id="gg1")
    mp = MemoryPacket(selected_claim_ids=["c1"])
    ip = InferencePacket(predictions=[{"predicate": "p", "confidence": 0.9}])
    ap = ActionPlan(action_kind="answer", execution_allowed=True)
    dp = DecisionPacket(action_kind="answer", action_plan=ap)
    assert dp.action_plan is not None
    assert dp.action_plan.execution_allowed
    assert dp.action_kind == "answer"
    assert gg.semantic_event_graph_id == "gg1"
    assert "c1" in mp.selected_claim_ids
    assert ip.predictions[0]["predicate"] == "p"


# ── GroundingPipeline produces GroundedGraph ─────────────────


def test_grounding_produces_grounded_graph(kernel, seg):
    resolver = Mock(spec=EntityResolver)
    frames = Mock(spec=FrameEngine)
    resolver.resolve_self.return_value = None
    mock_entity = Mock()
    mock_entity.id = "ent_1"
    mock_entity.type = Mock(value="CONCEPT")
    resolver.resolve_by_name.return_value = [mock_entity]
    frames.apply_frame_rules.return_value = []

    pipeline = GroundingPipeline(resolver, frames)
    gg = pipeline.run(seg, kernel)

    assert isinstance(gg, GroundedGraph)
    assert gg.semantic_event_graph_id == "seg_1"
    assert len(gg.entity_ids) > 0
    assert gg.entity_ids[0] == "ent_1"


def test_grounding_no_entities_still_returns_packet(kernel):
    seg2 = SemanticEventGraph(
        id="seg_empty",
        source_signal_ids=["sig_1"],
        context_id="ctx_1",
        entity_refs=[],
        processes=[],
        states=[],
        confidence=0.5,
    )
    resolver = Mock(spec=EntityResolver)
    frames = Mock(spec=FrameEngine)
    resolver.resolve_self.return_value = None
    resolver.resolve_by_name.return_value = None
    frames.apply_frame_rules.return_value = []

    pipeline = GroundingPipeline(resolver, frames)
    gg = pipeline.run(seg2, kernel)

    assert isinstance(gg, GroundedGraph)
    assert gg.entity_ids == []


# ── CausalInference produces InferencePacket ──────────────────


def test_causal_inference_produces_inference_packet():
    store = MagicMock()
    store.models.find_by_kind.return_value = []
    ci = CausalInference(store)
    k = ContextKernel(
        id="test",
        self_state_id="self",
        time=TimeState(now=time.time()),
        budget=Budget(),
        permission=Permission.public(),
    )
    k.goal = GoalState()

    result = ci.predict("test event", [], k)
    assert isinstance(result, InferencePacket)
    assert hasattr(result, "predictions")
    assert isinstance(result.predictions, list)


def test_causal_inference_empty_confidence(kernel):
    store = MagicMock()
    store.models.find_by_kind.return_value = []
    ci = CausalInference(store)
    result = ci.predict("nothing", [], kernel)
    assert result.confidence == 0.5


# ── DecisionRouter produces canonical DecisionPacket ──────────


def test_decision_router_abstains_on_no_data():
    k = ContextKernel(
        id="tk_abstain", self_state_id="self",
        time=TimeState(now=time.time()),
        goal=GoalState(),
        memory=MemoryState(),
        budget=Budget(),
        permission=Permission.public(),
    )
    k.user.known = True
    empty_seg = SemanticEventGraph(
        id="seg_empty", source_signal_ids=["s1"], context_id="c1",
        entity_refs=[], processes=[], states=[], confidence=0.3,
    )
    router = DecisionRouter()
    mp = MemoryPacket()
    gg = GroundedGraph(semantic_event_graph_id="seg_empty")
    ip = InferencePacket()

    dp = router.run(empty_seg, k, grounded_graph=gg, memory_packet=mp, inference_packet=ip)
    assert isinstance(dp, DecisionPacket)
    assert dp.action_kind == "abstain"
    assert dp.action_plan is not None
    assert dp.action_plan.execution_allowed is False


def test_decision_router_asks_on_missing_slots(kernel, seg):
    router = DecisionRouter()
    mp = MemoryPacket(selected_claim_ids=["c1"], selected_model_ids=["m1"])
    gg = GroundedGraph(semantic_event_graph_id="seg_1", missing_slots=["subject"])
    ip = InferencePacket(predictions=[{"predicate": "effect", "confidence": 0.8}])

    dp = router.run(seg, kernel, grounded_graph=gg, memory_packet=mp, inference_packet=ip)
    assert dp.action_kind == "ask"


def test_decision_router_answers_on_selected_claims(kernel):
    seg2 = SemanticEventGraph(
        id="seg_2",
        source_signal_ids=["sig_1"],
        context_id="ctx_1",
        entity_refs=[],
        processes=[],
        states=[],
        confidence=0.7,
    )
    kernel2 = ContextKernel(
        id="tk2", self_state_id="self",
        time=TimeState(now=time.time()),
        goal=GoalState(),
        memory=MemoryState(),
        budget=Budget(),
        permission=Permission.public(),
    )
    kernel2.user.known = True

    router = DecisionRouter()
    mp = MemoryPacket(selected_claim_ids=["c1"], selected_model_ids=["m1"])
    gg = GroundedGraph(semantic_event_graph_id="seg_2")
    ip = InferencePacket(predictions=[{"predicate": "effect", "confidence": 0.8}])

    dp = router.run(seg2, kernel2, grounded_graph=gg, memory_packet=mp, inference_packet=ip)
    assert dp.action_kind == "answer"
    assert dp.action_plan.selected_claim_ids == ["c1"]
    assert dp.action_plan.selected_model_ids == ["m1"]


# ── packet schema validation ──────────────────────────────────


def test_packet_validator_passes_valid():
    from cemm.types.packet_schemas import PACKET_SCHEMAS
    from cemm.kernel.packet_validator import validate_packet
    dp = {"action_kind": "answer", "version": "cemm.decision_packet.v1"}
    errs = validate_packet(dp, "decision_packet")
    assert errs == [], f"expected no errors, got {errs}"


def test_packet_validator_rejects_bad_action_kind():
    from cemm.kernel.packet_validator import validate_packet
    dp = {"action_kind": "invalid", "version": "cemm.decision_packet.v1"}
    errs = validate_packet(dp, "decision_packet")
    assert errs, "expected validation errors for invalid action_kind"


# ── Trace packet fields ──────────────────────────────────────


def test_trace_packet_id_fields():
    from cemm.types.trace import Trace
    t = Trace(
        context_id="t1",
        grounded_graph_id="gg1",
        memory_packet_id="mp1",
        inference_packet_id="ip1",
    )
    assert t.grounded_graph_id == "gg1"
    assert t.memory_packet_id == "mp1"
    assert t.inference_packet_id == "ip1"


# ── PipelineResult packet fields ─────────────────────────────


def test_pipeline_result_packet_fields():
    from cemm.kernel.pipeline import PipelineResult
    result = PipelineResult(
        grounded_graph=GroundedGraph(semantic_event_graph_id="gg1"),
        memory_packet=MemoryPacket(selected_claim_ids=["c1"]),
    )
    assert result.grounded_graph is not None
    assert result.grounded_graph.semantic_event_graph_id == "gg1"
    assert result.memory_packet is not None
    assert "c1" in result.memory_packet.selected_claim_ids
