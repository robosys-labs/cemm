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
from cemm.types.permission import Permission
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.conversation_act_classifier import ConversationActClassifier
from cemm.types.conversation_act import ConversationAct


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


class TestConversationActClassification:
    def test_greeting_classified_as_greeting(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Hello!")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "greeting"
        assert result.conversation_act.is_social

    def test_how_are_you_classified_as_phatic_checkin(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("How are you?")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "phatic_checkin"
        assert result.conversation_act.is_social

    def test_tell_me_a_story_classified_as_story_request(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Tell me a story")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "story_request"
        assert result.conversation_act.is_creative

    def test_okay_classified_as_acknowledgment(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Okay")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "acknowledgment"

    def test_you_are_dumb_classified_as_frustration(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("You are dumb")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "frustration_signal"
        assert result.conversation_act.is_repair or result.conversation_act.response_mode == "repair_response"

    def test_substring_does_not_trigger_greeting(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Nothing just chatting")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type != "greeting"

    def test_discourse_marker_i_mean_does_not_force_self_correction(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("I mean can you help me grow my career?")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type != "self_correction"
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "answer"
        assert decision.action_plan is not None
        assert decision.action_plan.params.get("response_mode") == "general_conversation"

    def test_whats_going_on_is_not_confusion_repair(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("what's going on")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type != "confusion_repair"
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "answer"

    def test_what_does_that_mean_is_clarification_not_evidence_query(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("what does that mean?")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "confusion_repair"

    def test_weather_question_is_not_treated_as_unknown_entity(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("what is the weather today?")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "evidence_query"
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "abstain"

    def test_recent_match_question_is_not_routed_as_general_chat(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("who won the last match?")
        assert result.conversation_act is not None
        assert result.conversation_act.act_type == "evidence_query"
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "abstain"


class TestRetrievalGating:
    def test_social_turn_does_not_retrieve(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Hello!")
        assert result.conversation_act is not None
        assert not result.conversation_act.requires_evidence
        assert result.ranked_claim_ids == []

    def test_creative_turn_does_not_retrieve(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Tell me a story")
        assert result.conversation_act is not None
        assert not result.conversation_act.requires_evidence
        assert result.ranked_claim_ids == []

    def test_evidence_query_does_retrieve(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("What is my favorite database?")
        assert result.conversation_act is not None
        assert result.conversation_act.requires_evidence or result.conversation_act.act_type == "unknown"


class TestNoFallbackRawRemember:
    def test_social_text_not_stored_as_claim(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Hello!")
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind != "remember", (
            f"Greeting should not route to remember, got: {decision.action_kind} ({decision.reason})"
        )

    def test_creative_text_not_stored_as_claim(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Tell me a story")
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind != "remember", (
            f"Story request should not route to remember, got: {decision.action_kind} ({decision.reason})"
        )

    def test_frustration_not_stored_as_claim(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("You are dumb")
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind != "remember", (
            f"Frustration should not route to remember, got: {decision.action_kind} ({decision.reason})"
        )


class TestDecisionPacketAuthority:
    def test_greeting_response_mode_is_social(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Hello!")
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "answer"
        ap = decision.action_plan
        assert ap is not None
        assert ap.params.get("response_mode") == "social_response"

    def test_story_request_response_mode_is_creative(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Tell me a story")
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "answer"
        ap = decision.action_plan
        assert ap is not None
        assert ap.params.get("response_mode") == "creative_response"

    def test_capability_query_uses_capability_summary(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("What can you do?")
        decision = result.decision_packet
        assert decision is not None
        assert decision.action_kind == "answer"
        ap = decision.action_plan
        assert ap is not None
        assert ap.params.get("response_mode") == "capability_summary"


class TestKernelLatestSignal:
    def test_kernel_latest_signal_is_set(self) -> None:
        store = _make_store()
        registry = _make_registry()
        pipeline = Pipeline(store, registry)
        result = pipeline.run("Hello!")
        assert result.kernel.latest_signal is not None
        assert result.kernel.latest_signal.content == "Hello!"


class TestExportIncludesConversationAct:
    def test_serialize_turn_includes_conversation_act(self) -> None:
        from cemm.kernel.training_export import serialize_turn
        from cemm.types.context_kernel import ContextKernel, UserState
        from cemm.types.conversation_act import ConversationAct

        signal = _make_signal("Hello!")
        kernel = ContextKernel(id=uuid.uuid4().hex[:16], user=UserState())
        act = ConversationAct(act_type="greeting", confidence=0.9)
        records = serialize_turn(
            input_text="Hello!",
            output_text="Hi there!",
            kernel=kernel,
            input_signal=signal,
            conversation_act=act,
        )
        full_export = records[0]
        assert full_export["payload"]["conversation_act"]["act_type"] == "greeting"
