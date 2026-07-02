from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pytest

from cemm.kernel.training_export import serialize_turn
from cemm.kernel.teaching_interpreter import TeachingInterpreter
from cemm.learning.surface_tagger import SurfaceTagger
from cemm.registry import Registry, RegistryEntry
from cemm.registry.uol_mapper import UOLMapper
from cemm.types.claim import Claim
from cemm.types.context_kernel import ContextKernel, UserState
from cemm.types.entity import Entity, EntityType
from cemm.types.permission import Permission
from cemm.types.semantic_answer_graph import SemanticAnswerGraph
from cemm.types.semantic_event_graph import SemanticEventGraph
from cemm.types.self_view import SelfView
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.trace import Trace
from cemm.kernel.context_kernel_builder import ContextKernelBuilder


def _make_signal(text: str) -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="test",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id=uuid.uuid4().hex[:16],
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _make_kernel() -> ContextKernel:
    signal = _make_signal("hello")
    kernel = ContextKernelBuilder.from_signal(signal, turn_index=1)
    kernel.self_view = SelfView(
        self_id="cemm",
        mode="assistant",
        uncertainty=0.0,
        coherence=1.0,
        recent_error_rate=0.0,
    )
    return kernel


# ── UOL semantics and predicates are loaded from JSON ─────────────────────


def test_uol_mapper_detects_self_query_from_data() -> None:
    mapper = UOLMapper(Registry())
    kernel = _make_kernel()
    atoms = mapper.map_signal("what are you", kernel)
    frame_keys = {atom.frame_key for atom in atoms if atom.kind == "process"}
    assert "self_identity_query" in frame_keys


def test_uol_mapper_detects_user_query_from_data() -> None:
    mapper = UOLMapper(Registry())
    kernel = _make_kernel()
    atoms = mapper.map_signal("what is my name", kernel)
    frame_keys = {atom.frame_key for atom in atoms if atom.kind == "process"}
    assert "user_name_query" in frame_keys


def test_uol_mapper_guards_command_on_question_mark() -> None:
    mapper = UOLMapper(Registry())
    kernel = _make_kernel()
    atoms = mapper.map_signal("remember me?", kernel)
    frame_keys = {atom.frame_key for atom in atoms if atom.kind == "process"}
    # Question mark should prevent command_remember emission.
    assert "command_remember" not in frame_keys


def test_uol_mapper_uses_data_driven_insults() -> None:
    registry = Registry()
    registry.register(RegistryEntry(
        model_id="uol_low_competence",
        canonical_key="low_competence",
        kind="uol_semantic",
        aliases=["dumb", "stupid", "fool", "idiot", "useless", "broken"],
    ))
    mapper = UOLMapper(registry)
    kernel = _make_kernel()
    atoms = mapper.map_signal("you are broken", kernel)
    state_keys = {atom.state_key for atom in atoms if atom.kind == "state"}
    assert "low_competence" in state_keys


def test_uol_mapper_uses_data_driven_pronouns() -> None:
    mapper = UOLMapper(Registry())
    kernel = _make_kernel()
    atoms = mapper.map_signal("i like rain", kernel)
    entity_ids = {atom.entity_id for atom in atoms if atom.kind == "entity_ref"}
    assert "user" in entity_ids


# ── Surface tagger uses JSON word lists ───────────────────────────────────


def test_surface_tagger_tags_process_word_from_data() -> None:
    tagger = SurfaceTagger()
    tags = tagger.tag(["remember", "this"])
    assert tags == ["B-PROCESS", "O"]


def test_surface_tagger_tags_modifier_word_from_data() -> None:
    tagger = SurfaceTagger()
    tags = tagger.tag(["quickly", "eat"])
    assert tags == ["B-MODIFIER", "O"]


def test_surface_tagger_tags_relation_word_from_data() -> None:
    tagger = SurfaceTagger()
    tags = tagger.tag(["before", "lunch"])
    assert tags == ["B-RELATION", "O"]


# ── Teaching interpreter uses JSON patterns ───────────────────────────────


def test_teaching_interpreter_definition_trigger_from_data() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter.interpret("zibble means save this")
    assert any(ev.kind == "definition" and ev.surface == "zibble" for ev in events)


def test_teaching_interpreter_correction_trigger_from_data() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter.interpret("no, zibble means save this")
    assert any(ev.kind == "correction" and ev.surface == "zibble" for ev in events)


def test_teaching_interpreter_command_trigger_from_data() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter.interpret("when i say zibble, remember this")
    assert any(ev.kind == "command_alias" and ev.surface == "zibble" for ev in events)


# ── Training export includes the SAG ───────────────────────────────────────


def test_serialize_turn_includes_semantic_answer_graph() -> None:
    kernel = _make_kernel()
    seg = SemanticEventGraph(
        id="seg_1",
        source_signal_ids=["sig_1"],
        context_id=kernel.id,
    )
    sag = SemanticAnswerGraph(
        id="sag_1",
        intent="answer",
        source_signal_ids=["sig_1"],
        context_id=kernel.id,
        selected_claim_ids=["claim_1"],
    )
    records = serialize_turn(
        input_text="hello",
        output_text="hi there",
        kernel=kernel,
        input_signal=_make_signal("hello"),
        semantic_event_graph=seg,
        semantic_answer_graph=sag,
    )
    assert any(r["task_type"] == "semantic_text_realization" for r in records)
    realization_record = next(r for r in records if r["task_type"] == "semantic_text_realization")
    assert realization_record["payload"]["semantic_answer_graph"]["id"] == "sag_1"


def test_serialize_turn_includes_trace() -> None:
    kernel = _make_kernel()
    trace = Trace(
        context_id=kernel.id,
        input_signal_ids=["sig_1"],
        semantic_answer_graph_id="sag_1",
        realization_strategy="template",
        realization_verified=True,
    )
    records = serialize_turn(
        input_text="hello",
        output_text="hi there",
        kernel=kernel,
        input_signal=_make_signal("hello"),
        trace=trace,
    )
    full_turn = next(r for r in records if r["task_type"] == "full_turn_export")
    assert full_turn["payload"]["trace"]["semantic_answer_graph_id"] == "sag_1"
    assert full_turn["payload"]["realization_metadata"]["verified"] is True


def test_teaching_interpreter_uses_data_driven_meaning_stop_words() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter.interpret("zibble means save this but not that")
    assert any(ev.kind == "definition" and ev.meaning == "save this" for ev in events)


def test_teaching_interpreter_does_not_learn_copular_judgment() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter.interpret("wow you are just a pattern matcher aren't you")
    assert events == []


def test_teaching_interpreter_does_not_treat_pronoun_as_surface() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter.interpret("you means remember this")
    assert events == []


def test_uol_mapper_loads_speech_act_to_frame_from_data() -> None:
    mapper = UOLMapper(Registry())
    assert mapper._speech_act_to_frame.get("greeting") == "greeting"
    assert mapper._speech_act_to_frame.get("command") == "command_remember"


def test_operator_seed_data_loaded_from_json() -> None:
    from cemm.__main__ import _load_seed_data
    operators = _load_seed_data("operators")
    keys = {op["canonical_key"] for op in operators}
    assert "answer" in keys
    assert "remember" in keys
    assert "learn" in keys


def test_semantic_interpreter_loads_data_driven_words() -> None:
    from cemm.kernel.semantic_interpreter import SemanticInterpreter
    interpreter = SemanticInterpreter(UOLMapper(Registry()))
    assert "the" in interpreter._stop_words
    assert "remember" in interpreter._command_words
    assert interpreter._causal_edge_relations.get("causal_causes") == "causes"
    assert "before" in interpreter._temporal_relations.get("temporal_before", ())


def test_semantic_interpreter_entity_expansion_uses_data_driven_stop_words() -> None:
    from cemm.kernel.semantic_interpreter import SemanticInterpreter
    interpreter = SemanticInterpreter(UOLMapper(Registry()))
    words = ["remember", "the", "blue", "house", "and", "garden"]
    assert interpreter._expand_entity_phrase(words, 3, 1) == "house"
    assert interpreter._expand_entity_phrase(words, 3, -1) == "blue house"


def test_inductor_loads_data_driven_causal_connectors() -> None:
    from cemm.learning.inductor import Inductor
    from cemm.store.store import Store
    store = Store()
    inductor = Inductor(store)
    assert " causes " in inductor._causal_connectors
    assert "cause" in inductor._causal_phrase_connectors
    assert "the" in inductor._stop_words


def test_teaching_interpreter_loads_data_driven_role_cues() -> None:
    from cemm.kernel.teaching_interpreter import TeachingInterpreter
    interpreter = TeachingInterpreter()
    assert "remember" in interpreter._process_cues
    assert "is" in interpreter._state_cues
    assert "quietly" in interpreter._modifier_cues


def test_teaching_interpreter_role_inference_uses_data_driven_cues() -> None:
    from cemm.kernel.teaching_interpreter import TeachingInterpreter
    interpreter = TeachingInterpreter()
    assert interpreter._infer_role("x", "quickly") == "modifier"
    assert interpreter._infer_role("x", "is good") == "state"
    assert interpreter._infer_role("x", "remember") == "process"


def test_semantic_interpreter_loads_data_driven_target_prepositions() -> None:
    from cemm.kernel.semantic_interpreter import SemanticInterpreter
    interpreter = SemanticInterpreter(UOLMapper(Registry()))
    assert {"by", "to", "with"}.issubset(interpreter._target_prepositions)


def test_uol_semantics_includes_conversation_intent_frames() -> None:
    data = json.loads(Path("cemm/data/uol_semantics.json").read_text(encoding="utf-8"))
    keys = {entry["canonical_key"] for entry in data.get("uol_semantics", [])}
    assert "story_request" in keys
    assert "food_recommendation_request" in keys
    assert "recommendation_request" in keys


def test_uol_mapper_emits_conversation_intent_atoms() -> None:
    from cemm.registry.uol_mapper import UOLMapper
    from cemm.types.context_kernel import ContextKernel
    registry = Registry()
    registry.register(RegistryEntry(
        model_id="story_request_1",
        canonical_key="story_request",
        kind="uol_semantic",
        aliases=["story", "stories", "tell me a story"],
    ))
    mapper = UOLMapper(registry)
    kernel = ContextKernel(id="ctx-1", user=UserState())
    atoms = mapper.map_signal("story", kernel)
    frame_keys = {a.frame_key for a in atoms if hasattr(a, "frame_key")}
    assert "story_request" in frame_keys


def test_decision_router_classifies_intent_from_graph_frames() -> None:
    from cemm.kernel.decision_router import DecisionRouter
    from cemm.types.semantic_event_graph import SemanticEventGraph
    from cemm.types.context_kernel import ContextKernel
    router = DecisionRouter(uol_mapper=UOLMapper(Registry()))
    graph = SemanticEventGraph(
        id="g1", context_id="ctx-1", source_signal_ids=["s1"],
        processes=[{"frame_key": "story_request", "confidence": 0.8}],
    )
    kernel = ContextKernel(id="ctx-1", user=UserState())
    intent = router._classify_general_question("tell me a story", graph, kernel)
    assert intent == "story_request"


def test_context_inference_engine_loads_data_driven_fallback_words() -> None:
    from cemm.kernel.context_inference import ContextInferenceEngine
    from cemm.store.store import Store
    engine = ContextInferenceEngine(Store(), Registry())
    assert "hello" in engine._fallback_words["greeting"]
    assert "ok" in engine._fallback_words["acknowledgment"]
    assert "what do you mean" in engine._fallback_words["clarification"]
    assert "bye" in engine._fallback_words["exit"]
    assert "weather" in engine._fallback_words["weather"]


def test_context_inference_engine_data_driven_fallback_detects_greeting() -> None:
    from cemm.kernel.context_inference import ContextInferenceEngine
    from cemm.store.store import Store
    engine = ContextInferenceEngine(Store(), Registry())
    signal = _make_signal("hello")
    kernel = ContextKernel(id="ctx-1", user=UserState())
    kernel.conversation.turn_index = 1
    inference = engine.infer(signal, kernel)
    assert inference.frame_id == "session_opening"


def test_decision_router_pure_acknowledgment_phrases_loaded_from_data() -> None:
    from cemm.kernel.decision_router import DecisionRouter
    router = DecisionRouter()
    assert "ok" in router._pure_acknowledgment_phrases
    assert "got it" in router._pure_acknowledgment_phrases
    assert router._is_pure_acknowledgment("OK")
    assert not router._is_pure_acknowledgment("OK tell me a story")


def test_realizer_joins_capabilities_from_claim_atoms() -> None:
    from cemm.synthesis.realizer import _capability_variables
    atoms = [
        {"predicate": "does", "object_value": "answer questions"},
        {"predicate": "does", "object_value": "remember facts"},
    ]
    variables = _capability_variables(atoms)
    assert "answer questions" in variables["capabilities"]
    assert "remember facts" in variables["capabilities"]


def test_response_templates_include_self_capability_template() -> None:
    data = json.loads(Path("cemm/data/response_templates.json").read_text(encoding="utf-8"))
    en_templates = data.get("en", {})
    assert "self_capability" in en_templates
    assert "{capabilities}" in en_templates["self_capability"]


def test_teaching_interpreter_loads_command_alias_delimiters() -> None:
    interpreter = TeachingInterpreter()
    assert " do " in interpreter._command_alias_delimiters


def test_teaching_interpreter_extracts_command_alias_with_data_driven_delimiter() -> None:
    interpreter = TeachingInterpreter()
    events = interpreter._extract_command_alias("when i say zibble, remember this", "when i say")
    assert len(events) == 1
    assert events[0].surface == "zibble"
    assert events[0].meaning == "remember this"


def test_operator_messages_data_file_exists() -> None:
    data = json.loads(Path("cemm/data/operator_messages.json").read_text(encoding="utf-8"))
    en_remember = data.get("en", {}).get("remember", {})
    assert "permission_denied_execute" in en_remember
    assert "permission_denied_storage" in en_remember
    assert "insufficient_information" in en_remember
    assert "question_not_stored" in en_remember
    assert "predicate_missing" in en_remember


def test_remember_operator_uses_data_driven_messages() -> None:
    from cemm.operators.remember import RememberOperator
    from cemm.types.context_kernel import ContextKernel, UserState
    operator = RememberOperator()
    ctx = type("Ctx", (), {"kernel": ContextKernel(id="ctx-1", user=UserState())})()
    operator._ctx = ctx
    assert operator._message("insufficient_information") == "I don't have enough information to store."
