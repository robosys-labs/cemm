from __future__ import annotations

import time

from cemm.kernel.context_inference import ContextInferenceEngine
from cemm.kernel.decision_router import DecisionRouter
from cemm.kernel.pragmatic_interpreter import interpret_signal
from cemm.kernel.semantic_clusters import SemanticClusterRegistry
from cemm.registry import Registry
from cemm.registry.uol_mapper import UOLMapper
from cemm.store.store import Store
from cemm.types.context_kernel import ContextKernel
from cemm.types.packets import MemoryPacket
from cemm.types.permission import Permission
from cemm.types.semantic_event_graph import SemanticEventGraph
from cemm.types.signal import ObservationSemantics, Signal, SignalKind, SourceType


def _make_kernel(turn_index: int = 1) -> ContextKernel:
    kernel = ContextKernel(id="ctx_test", permission=Permission.public())
    kernel.time.now = time.time()
    kernel.conversation.session_id = "s1"
    kernel.conversation.turn_index = turn_index
    return kernel


def _make_signal(text: str) -> Signal:
    return Signal(
        id="s1",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id="ctx_test",
        salience=0.5,
        trust=0.5,
        permission=Permission.public(),
    )


def _make_empty_seg() -> SemanticEventGraph:
    return SemanticEventGraph(
        id="seg1",
        source_signal_ids=["s1"],
        context_id="ctx_test",
        entity_refs=[],
        processes=[],
        states=[],
        claim_refs=[],
        model_refs=[],
        action_refs=[],
        temporal_edges=[],
        causal_edges=[],
        permission_scope="public",
        confidence=0.5,
    )


def test_conversational_clusters_detect_common_speech_acts():
    registry = SemanticClusterRegistry()
    cases = [
        ("hello", "greeting"),
        ("hi there", "greeting"),
        ("ok", "acknowledgment"),
        ("got it", "acknowledgment"),
        ("huh?", "clarification"),
        ("what in the world?", "clarification"),
        ("bye", "exit"),
        ("remember I like coffee", "command"),
    ]
    for text, expected in cases:
        speech_act, _, confidence = registry.match(text)
        assert speech_act == expected
        assert confidence >= 0.5


def test_interpret_signal_sets_frame_key():
    kernel = _make_kernel()
    cases = [
        ("hello", "greeting", "greeting"),
        ("ok", "acknowledgment", "acknowledgment"),
        ("huh?", "clarification", "request_clarification"),
        ("bye", "exit", "session_exit"),
        ("remember I like coffee", "command", "command_remember"),
    ]
    for text, speech_act, frame_key in cases:
        semantics = interpret_signal(_make_signal(text), kernel)
        assert semantics is not None
        assert semantics.speech_act == speech_act
        assert semantics.frame_key == frame_key


def test_context_inference_infers_conversational_frames():
    store = Store(":memory:")
    registry = Registry()
    engine = ContextInferenceEngine(store, registry)
    cases = [
        ("hi", 1, "session_opening"),
        ("ok", 3, "acknowledgment"),
        ("huh?", 3, "clarification"),
        ("bye", 3, "session_exit"),
    ]
    for text, turn_index, frame_id in cases:
        result = engine.infer(_make_signal(text), _make_kernel(turn_index=turn_index))
        assert result.frame_id == frame_id
        assert result.confidence >= 0.4


def test_decision_router_uses_pragmatic_fallback_when_graph_has_no_actionable_frame():
    kernel = _make_kernel()
    graph = _make_empty_seg()
    router = DecisionRouter()
    semantics = ObservationSemantics(speech_act="greeting", frame_key="greeting", confidence=0.8)
    decision = router.run(graph=graph, kernel=kernel, input_text="hello", observation_semantics=semantics)
    assert decision.action_kind == "answer"
    assert "speech_act" in decision.reason


def test_decision_router_does_not_override_graph_command_with_pragmatic_fallback():
    kernel = _make_kernel()
    graph = _make_empty_seg()
    graph.processes = [{"frame_key": "command_remember", "confidence": 0.85}]
    router = DecisionRouter()
    semantics = ObservationSemantics(speech_act="greeting", frame_key="greeting", confidence=0.8)
    decision = router.run(graph=graph, kernel=kernel, input_text="remember I like tea", observation_semantics=semantics)
    assert decision.action_kind == "remember"


def test_uol_mapper_cluster_fallback_emits_conversational_process_atoms():
    mapper = UOLMapper(Registry())
    kernel = _make_kernel()
    cases = [
        ("lol hello", "greeting"),
        ("what in the world?", "request_clarification"),
        ("got it", "acknowledgment"),
        ("bye", "session_exit"),
    ]
    for text, frame_key in cases:
        atoms = mapper.map_signal(text, kernel)
        frame_keys = [atom.frame_key for atom in atoms if atom.kind == "process"]
        assert frame_key in frame_keys
