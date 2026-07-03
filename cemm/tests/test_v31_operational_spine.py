"""Tests for v3.1 operational meaning spine components.

Tests FrameBinder (atom-based role binding), EntityFactExtractor (pattern-based
fact extraction with clause segmentation), TopicState, CapabilityClassifier,
capitalized entity detection fix, and repair/frustration vocab.
"""

from __future__ import annotations

import time
import uuid

from cemm.types.meaning_percept import (
    MeaningPerceptPacket,
    ReferentAtom,
    ActionAtom,
    StateAtom,
    RelationAtom,
    SituationFrame,
)
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.context_kernel import ContextKernel, TopicState
from cemm.kernel.meaning_perceptor import MeaningPerceptor
from cemm.kernel.frame_binder import (
    FrameBinder,
    BoundSituationFrame,
    FrameBindingTrace,
)
from cemm.kernel.entity_fact_extractor import EntityFactExtractor, EntityFactCandidate
from cemm.kernel.act_resolution_planner import ActResolutionPlanner
from cemm.kernel.capability_classifier import CapabilityClassifier
from cemm.learning.surface_tagger import SurfaceTagger
from cemm.learning.ner_tagger import NERTagger


def _make_signal(text: str) -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id="test_ctx",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _make_kernel() -> ContextKernel:
    return ContextKernel(id="test_kernel")


def _make_perceptor() -> MeaningPerceptor:
    import json
    from pathlib import Path
    ner = NERTagger()
    vocab_path = Path(__file__).parent.parent / "data" / "vocab.json"
    known_words: set[str] = set()
    if vocab_path.exists():
        data = json.loads(vocab_path.read_text(encoding="utf-8"))
        known_words = set(data.get("known_words", []))
    tagger = SurfaceTagger(ner, known_words=known_words)
    return MeaningPerceptor(ner_tagger=ner, surface_tagger=tagger)


# ── Capitalized entity detection tests ──────────────────────────────────────


def test_capitalized_unknown_entity_detected() -> None:
    """Capitalized unknown words should be detected as entity candidates."""
    perceptor = _make_perceptor()
    signal = _make_signal("Tell me about Pawpaw")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    surfaces = [r.surface for r in packet.referents if r.source == "capitalization"]
    assert "Pawpaw" in surfaces


def test_capitalized_sentence_start_not_entity() -> None:
    """Sentence-initial common words should not be treated as entities."""
    perceptor = _make_perceptor()
    signal = _make_signal("Hello there")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    cap_refs = [r for r in packet.referents if r.source == "capitalization"]
    assert "Hello" not in [r.surface for r in cap_refs]


def test_capitalized_known_word_not_entity() -> None:
    """Known words in vocab should not be treated as entity candidates."""
    perceptor = _make_perceptor()
    signal = _make_signal("I like Mango")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    cap_refs = [r for r in packet.referents if r.source == "capitalization"]
    surfaces = [r.surface for r in cap_refs]
    assert "Mango" not in surfaces


def test_capitalized_entity_position_confidence() -> None:
    """Sentence-initial capitalized words should have lower confidence."""
    perceptor = _make_perceptor()
    signal = _make_signal("Pear is a fruit")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    cap_refs = [r for r in packet.referents if r.source == "capitalization"]
    pear_ref = [r for r in cap_refs if r.surface == "Pear"]
    assert len(pear_ref) == 1
    assert pear_ref[0].confidence == 0.4  # position 0, lower confidence


def test_capitalized_non_initial_higher_confidence() -> None:
    """Non-initial capitalized words should have higher confidence."""
    perceptor = _make_perceptor()
    signal = _make_signal("Tell me about Obidike")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    cap_refs = [r for r in packet.referents if r.source == "capitalization"]
    obidike_ref = [r for r in cap_refs if r.surface == "Obidike"]
    assert len(obidike_ref) == 1
    assert obidike_ref[0].confidence == 0.6  # not position 0


# ── Repair utterances and frustration vocab tests ───────────────────────────


def test_repair_utterance_detected() -> None:
    """Repair utterances like 'huh' should be detected as affect markers."""
    perceptor = _make_perceptor()
    signal = _make_signal("huh?")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    repair_markers = [m for m in packet.affect_markers if m["type"] == "repair"]
    assert len(repair_markers) >= 1


def test_frustration_canned_responses_detected() -> None:
    """Frustration about canned responses should be detected."""
    perceptor = _make_perceptor()
    signal = _make_signal("you keep giving me canned responses")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    frustration_markers = [m for m in packet.affect_markers if m["type"] == "frustration"]
    assert len(frustration_markers) >= 1


def test_urghh_detected_as_frustration() -> None:
    """'urghh' should be detected as frustration."""
    perceptor = _make_perceptor()
    signal = _make_signal("urghh")
    kernel = _make_kernel()
    packet = perceptor.perceive(signal, kernel)
    frustration_markers = [m for m in packet.affect_markers if m["type"] == "frustration"]
    assert len(frustration_markers) >= 1


# ── TopicState tests ────────────────────────────────────────────────────────


def test_topic_state_default() -> None:
    """TopicState should have empty defaults."""
    topic = TopicState()
    assert topic.active_topic_entity_id == ""
    assert topic.active_topic_surface == ""
    assert topic.last_taught_entity_id == ""


def test_topic_state_in_kernel() -> None:
    """ContextKernel should have a topic field."""
    kernel = _make_kernel()
    assert hasattr(kernel, "topic")
    assert isinstance(kernel.topic, TopicState)


# ── FrameBinder tests (atom-based role binding) ─────────────────────────────


def test_frame_binder_binds_actor_from_referent() -> None:
    """FrameBinder should bind actor role from a referent with role='actor'."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="John went to the store",
        referents=[
            ReferentAtom(surface="John", entity_id="john", entity_type="person",
                        role="actor", known=False, source="ner", confidence=0.8),
        ],
        actions=[
            ActionAtom(surface="went", action_key="move_to", confidence=0.7),
        ],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    assert isinstance(result, BoundSituationFrame)
    assert result.frame.actor is not None
    assert result.frame.actor.surface == "John"
    assert result.trace.selected_action == "move_to"


def test_frame_binder_binds_object_and_target() -> None:
    """FrameBinder should bind object and target roles from referents."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="John pushed Mary a book",
        referents=[
            ReferentAtom(surface="John", entity_id="john", entity_type="person",
                        role="actor", confidence=0.8),
            ReferentAtom(surface="Mary", entity_id="mary", entity_type="person",
                        role="target", confidence=0.7),
            ReferentAtom(surface="book", entity_id="book", entity_type="object",
                        role="object", confidence=0.6),
        ],
        actions=[
            ActionAtom(surface="pushed", action_key="push", confidence=0.7),
        ],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    assert result.frame.actor is not None
    assert result.frame.actor.surface == "John"
    assert result.frame.target is not None
    assert result.frame.target.surface == "Mary"
    assert result.frame.object is not None
    assert result.frame.object.surface == "book"


def test_frame_binder_command_modality_listener_is_actor() -> None:
    """For commanded actions, the listener/self should be bound as actor."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Bring me water",
        referents=[
            ReferentAtom(surface="user", entity_id="user", entity_type="user",
                        role="speaker", confidence=0.9),
        ],
        actions=[
            ActionAtom(surface="bring", action_key="bring",
                      actor_role="listener", modality="commanded",
                      confidence=0.8),
        ],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    # For commands, self/listener should be the actor
    assert result.frame.actor is not None
    assert result.frame.actor.entity_type == "self"


def test_frame_binder_trace_records_missing_roles() -> None:
    """FrameBinder should record missing required roles in trace."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="John went",
        referents=[
            ReferentAtom(surface="John", entity_id="john", entity_type="person",
                        role="actor", confidence=0.8),
        ],
        actions=[
            ActionAtom(surface="went", action_key="move_to", confidence=0.7),
        ],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    # Trace should have role bindings
    assert len(result.trace.role_bindings) > 0
    # Actor should be bound
    assert result.trace.role_bindings["actor"].referent is not None


def test_frame_binder_state_binding() -> None:
    """FrameBinder should bind state holders to frame actor."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="I am hungry",
        referents=[
            ReferentAtom(surface="user", entity_id="user", entity_type="user",
                        role="speaker", confidence=0.9),
        ],
        actions=[],
        states=[
            StateAtom(surface="hungry", state_key="hungry", dimension="hunger",
                     polarity="negative", confidence=0.8),
        ],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    assert len(result.frame.state_reports) == 1
    assert result.frame.state_reports[0].holder_role is not None


def test_frame_binder_uncertainty_from_unknown_lexemes() -> None:
    """FrameBinder should add uncertainty reasons for unknown lexemes."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="The xyzzy is broken",
        referents=[],
        actions=[],
        unknown_lexemes=[{"surface": "xyzzy"}],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    assert any("unknown_lexeme" in r for r in result.trace.uncertainty_reasons)


def test_frame_binder_confidence_in_frame() -> None:
    """FrameBinder should compute a confidence score for the frame."""
    binder = FrameBinder()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="John went to the store",
        referents=[
            ReferentAtom(surface="John", entity_id="john", entity_type="person",
                        role="actor", confidence=0.8),
        ],
        actions=[
            ActionAtom(surface="went", action_key="move_to", confidence=0.7),
        ],
    )
    kernel = _make_kernel()
    result = binder.bind(percept, kernel)
    assert 0.0 < result.frame.confidence <= 0.95
    assert result.trace.confidence == result.frame.confidence


# ── EntityFactExtractor tests (pattern-based fact extraction) ───────────────


def test_entity_fact_extractor_is_a() -> None:
    """EntityFactExtractor should produce claim candidates for 'is_a'."""
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Pear is a type of fruit",
        tokens=["pear", "is", "a", "type", "of", "fruit"],
    )
    kernel = _make_kernel()
    result = extractor.extract(percept, kernel=kernel)
    candidates = result.candidates
    assert len(candidates) >= 1
    is_a = [c for c in candidates if c.predicate == "is_a"]
    assert len(is_a) >= 1
    assert is_a[0].subject_entity_id == "pear"
    assert is_a[0].object_value == "fruit"


def test_entity_fact_extractor_coreference() -> None:
    """EntityFactExtractor should resolve 'it' to active topic."""
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="It is usually green",
        tokens=["it", "is", "usually", "green"],
    )
    kernel = _make_kernel()
    kernel.topic.active_topic_surface = "pear"
    kernel.topic.active_topic_entity_id = "pear"
    result = extractor.extract(percept, kernel=kernel)
    color_candidates = [c for c in result.candidates if c.predicate == "typical_color"]
    assert len(color_candidates) >= 1
    assert color_candidates[0].subject_entity_id == "pear"
    assert color_candidates[0].object_value == "green"


def test_entity_fact_extractor_edible() -> None:
    """EntityFactExtractor should extract 'edible' flag."""
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Pear is something you eat",
        tokens=["pear", "is", "something", "you", "eat"],
    )
    kernel = _make_kernel()
    result = extractor.extract(percept, kernel=kernel)
    edible = [c for c in result.candidates if c.predicate == "edible"]
    assert len(edible) >= 1
    assert edible[0].object_value == "true"


def test_entity_fact_extractor_complex_sentence() -> None:
    """EntityFactExtractor should extract multiple predicates from complex sentence.

    Acceptance test from v3.1 doc:
    'Pear is a type of fruit that you eat and is shaped like a curvy triangle'
    should produce: is_a->fruit, edible->true, shape->curvy_triangle
    """
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Pear is a type of fruit that you eat and is shaped like a curvy triangle",
        tokens=["pear", "is", "a", "type", "of", "fruit", "that", "you", "eat",
                "and", "is", "shaped", "like", "a", "curvy", "triangle"],
    )
    kernel = _make_kernel()
    result = extractor.extract(percept, kernel=kernel)
    pred_names = [c.predicate for c in result.candidates]
    assert "is_a" in pred_names
    is_a = [c for c in result.candidates if c.predicate == "is_a"][0]
    assert is_a.object_value == "fruit"
    assert "curvy" not in str(is_a.object_value)
    assert "edible" in pred_names
    assert "shape" in pred_names
    shape = [c for c in result.candidates if c.predicate == "shape"][0]
    assert "curvy_triangle" in str(shape.object_value)


def test_entity_fact_extractor_multi_clause_color() -> None:
    """EntityFactExtractor should extract shape and color from multi-clause sentence."""
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Pear is a type of fruit that is shaped like a curvy triangle and is usually green",
        tokens=["pear", "is", "a", "type", "of", "fruit", "that", "is", "shaped",
                "like", "a", "curvy", "triangle", "and", "is", "usually", "green"],
    )
    kernel = _make_kernel()
    result = extractor.extract(percept, kernel=kernel)
    pred_names = [c.predicate for c in result.candidates]
    assert "is_a" in pred_names
    assert "shape" in pred_names
    assert "typical_color" in pred_names


def test_entity_fact_extractor_updates_topic_state() -> None:
    """EntityFactExtractor.update_topic_state should update kernel.topic."""
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Pear is a type of fruit",
        tokens=["pear", "is", "a", "type", "of", "fruit"],
        referents=[ReferentAtom(surface="Pear", entity_type="person", role="topic",
                                known=False, source="capitalization", confidence=0.4)],
    )
    kernel = _make_kernel()
    result = extractor.extract(percept, kernel=kernel)
    extractor.update_topic_state(kernel, percept, result.candidates, "s1", time.time())
    assert kernel.topic.active_topic_surface == "Pear"
    assert kernel.topic.last_taught_entity_surface == "pear"


def test_entity_fact_extractor_detects_new_topic() -> None:
    """EntityFactExtractor should detect new topic from referents."""
    extractor = EntityFactExtractor()
    percept = MeaningPerceptPacket(
        id="test",
        signal_id="s1",
        context_id="c1",
        raw_text="Tell me about Pawpaw",
        tokens=["tell", "me", "about", "pawpaw"],
        referents=[ReferentAtom(surface="Pawpaw", entity_type="person", role="topic",
                                known=False, source="capitalization", confidence=0.6)],
    )
    kernel = _make_kernel()
    result = extractor.extract(percept, kernel=kernel)
    extractor.update_topic_state(kernel, percept, result.candidates, "s1", time.time())
    assert kernel.topic.active_topic_surface == "Pawpaw"


# ── CapabilityClassifier tests ──────────────────────────────────────────────


def test_capability_browse_web_unsupported() -> None:
    """CapabilityClassifier should identify 'browse web' as unsupported."""
    classifier = CapabilityClassifier()
    result = classifier.classify("can you browse the web?")
    assert result is not None
    assert result.matched
    assert result.capability_key == "browse_web"
    assert result.supported is False


def test_capability_play_music_unsupported() -> None:
    """CapabilityClassifier should identify 'play music' as unsupported."""
    classifier = CapabilityClassifier()
    result = classifier.classify("can you play music?")
    assert result is not None
    assert result.matched
    assert result.capability_key == "play_music"
    assert result.supported is False


def test_capability_remember_facts_supported() -> None:
    """CapabilityClassifier should identify 'remember' as supported."""
    classifier = CapabilityClassifier()
    result = classifier.classify("can you remember facts?")
    assert result is not None
    assert result.matched
    assert result.capability_key == "remember_facts"
    assert result.supported is True


def test_capability_learn_commands_supported() -> None:
    """CapabilityClassifier should identify 'learn commands' as supported."""
    classifier = CapabilityClassifier()
    result = classifier.classify("can you learn new commands?")
    assert result is not None
    assert result.matched
    assert result.capability_key == "learn_words"
    assert result.supported is True


def test_capability_tell_story_supported() -> None:
    """CapabilityClassifier should identify 'tell story' as supported."""
    classifier = CapabilityClassifier()
    result = classifier.classify("can you tell a story?")
    assert result is not None
    assert result.matched
    assert result.capability_key == "tell_story"
    assert result.supported is True


def test_capability_non_capability_question() -> None:
    """CapabilityClassifier should return None for non-capability questions."""
    classifier = CapabilityClassifier()
    result = classifier.classify("what is a pear?")
    assert result is None


def test_capability_do_you_know_not_capability() -> None:
    """'do you know...' should not be treated as a capability question."""
    classifier = CapabilityClassifier()
    result = classifier.classify("do you know what a pear is?")
    assert result is None


def test_capability_unknown_capability() -> None:
    """CapabilityClassifier should return unknown for unrecognized capabilities."""
    classifier = CapabilityClassifier()
    result = classifier.classify("can you fly?")
    assert result is not None
    assert result.matched
    assert result.capability_key == "unknown"


# ── ActResolutionPlanner tests ───────────────────────────────────────────────


def test_act_resolution_memory_and_answer_separate() -> None:
    """Multi-act packet should produce separate memory updates and answer tasks."""
    from cemm.types.conversation_act import ConversationAct, ConversationActPacket
    from cemm.types.meaning_percept import RetrievalPlan

    planner = ActResolutionPlanner()
    acts = ConversationActPacket(
        primary=ConversationAct(act_type="phatic_checkin", confidence=0.7),
        secondary=[ConversationAct(act_type="self_capability_query", confidence=0.8)],
    )

    plan = planner.plan(acts, retrieval_plan=RetrievalPlan(mode="self_knowledge"))

    assert plan.selected_response_mode == "capability_summary"
    assert plan.requires_retrieval
    assert plan.retrieval_mode == "self_knowledge"
    assert any(task.selected_act_type == "self_capability_query" for task in plan.answer_tasks)


def test_act_resolution_memory_act_with_facts() -> None:
    """Claim assertion with fact candidates should produce a MemoryUpdatePlan."""
    from cemm.types.conversation_act import ConversationAct, ConversationActPacket

    planner = ActResolutionPlanner()
    acts = ConversationActPacket(
        primary=ConversationAct(act_type="claim_assertion", confidence=0.8),
    )
    facts = [EntityFactCandidate(
        subject_entity_id="pear",
        predicate="is_a",
        object_value="fruit",
        confidence=0.7,
    )]

    plan = planner.plan(acts, fact_candidates=facts)

    assert len(plan.memory_updates) == 1
    assert plan.memory_updates[0].write_kind == "claim"
    assert len(plan.memory_updates[0].candidates) == 1


def test_act_resolution_safety_override() -> None:
    """SafetyFrame should produce a SafetyTask and override other obligations."""
    from cemm.types.conversation_act import ConversationAct, ConversationActPacket
    from cemm.types.meaning_percept import SafetyFrame

    planner = ActResolutionPlanner()
    acts = ConversationActPacket(
        primary=ConversationAct(act_type="unknown", confidence=0.5),
    )
    safety = SafetyFrame(
        category="self_harm",
        severity="high",
        allowed_response_mode="safe_info",
        must_not_do=["provide_methods"],
        confidence=0.9,
    )

    plan = planner.plan(acts, safety_frame=safety)

    assert len(plan.safety_tasks) == 1
    assert plan.safety_tasks[0].category == "self_harm"
    assert plan.selected_response_mode == "safe_info"


# ── RetrievalExecutor tests ──────────────────────────────────────────────────


def test_retrieval_executor_none_mode_returns_empty() -> None:
    """RetrievalExecutor with mode=none should return empty result with trace."""
    from types import SimpleNamespace
    from cemm.retrieval.retrieval_executor import RetrievalExecutor
    from cemm.types.meaning_percept import RetrievalPlan

    store = SimpleNamespace()
    kernel = _make_kernel()
    executor = RetrievalExecutor.__new__(RetrievalExecutor)
    executor._store = store
    executor._structural = None

    result = RetrievalExecutor.execute(executor, RetrievalPlan(mode="none"), kernel)

    assert result.result.total_count == 0
    assert result.trace.skipped == ["mode=none"]
