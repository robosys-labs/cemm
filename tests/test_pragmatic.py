from __future__ import annotations
import time
import pytest
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.semantic_clusters import SemanticClusterRegistry
from cemm.kernel.pragmatic_interpreter import interpret_signal, update_user_affect, update_conversation_dynamics
from cemm.types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from cemm.types.context_kernel import ContextKernel, UserAffectState, ConversationDynamics
from cemm.types.permission import Permission
from cemm.types.self_state import SelfState


def _make_store() -> Store:
    s = Store(":memory:")
    s.self_store.put(SelfState(id="self_main", name="cemm", created_at=time.time(), updated_at=time.time()))
    return s


def _make_kernel(context_id: str = "test_ctx") -> ContextKernel:
    k = ContextKernel(id=context_id, permission=Permission.public())
    k.time.now = time.time()
    k.conversation.dynamics = ConversationDynamics(last_updated_at=k.time.now)
    k.user.affect = UserAffectState(last_updated_at=k.time.now)
    return k


def _make_signal(content: str, observed_at: float | None = None) -> Signal:
    now = observed_at or time.time()
    return Signal(
        id=f"sig_{abs(hash(content)) % 10**8}",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=content,
        observed_at=now,
        context_id="test_ctx",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _make_self_state() -> SelfState:
    return SelfState(id="self_main", name="cemm", created_at=time.time(), updated_at=time.time())


class TestPragmaticRepetition:
    def test_three_insults_increment_repetition_count(self):
        kernel = _make_kernel()
        store = _make_store()
        self_state = _make_self_state()
        kernel.self_view = kernel.self_view.from_self_state(self_state)

        contents = ["you are dumb", "you are daft", "you are a fool"]
        counts = []
        for i, content in enumerate(contents):
            signal = _make_signal(content, observed_at=time.time() + i)
            semantics = interpret_signal(signal, kernel, store)
            assert semantics is not None, f"No semantics for '{content}'"
            assert semantics.semantic_cluster_key == "assistant_insult_low_competence", (
                f"Expected insult cluster, got '{semantics.semantic_cluster_key}'"
            )
            counts.append(semantics.repetition_count)
            if semantics.semantic_cluster_key not in kernel.conversation.active_repetition_group_ids:
                kernel.conversation.active_repetition_group_ids.append(semantics.semantic_cluster_key)
            kernel.conversation.dynamics = update_conversation_dynamics(
                kernel.conversation.dynamics, semantics, kernel
            )

        assert counts == [1, 2, 3], f"Expected [1, 2, 3], got {counts}"

    def test_frustration_grows_with_repetition(self):
        kernel = _make_kernel()
        store = _make_store()
        self_state = _make_self_state()
        kernel.self_view = kernel.self_view.from_self_state(self_state)

        for i in range(3):
            signal = _make_signal("you are dumb", observed_at=time.time() + i)
            semantics = interpret_signal(signal, kernel, store)
            assert semantics is not None
            if semantics.semantic_cluster_key not in kernel.conversation.active_repetition_group_ids:
                kernel.conversation.active_repetition_group_ids.append(semantics.semantic_cluster_key)
            kernel.user.affect = update_user_affect(
                kernel.user.affect, semantics, kernel
            )

        assert kernel.user.affect.frustration > 0.5
        assert kernel.user.affect.hostility > 0.2
        assert kernel.user.affect.current_stance in ("frustrated", "hostile")

    def test_pipeline_single_signal_has_semantics(self):
        store = _make_store()
        reg = Registry()
        pipeline = Pipeline(store, reg)

        result = pipeline.run("you are dumb")
        s = result.signals[0]
        assert s.observation_semantics is not None
        assert s.observation_semantics.speech_act == "insult"
        assert s.observation_semantics.repetition_count == 1
        assert s.observation_semantics.semantic_cluster_key == "assistant_insult_low_competence"

    def test_different_clusters_dont_cross_count(self):
        kernel = _make_kernel()
        store = _make_store()
        self_state = _make_self_state()
        kernel.self_view = kernel.self_view.from_self_state(self_state)

        s1 = _make_signal("you are dumb")
        sem1 = interpret_signal(s1, kernel, store)
        assert sem1 is not None
        kernel.conversation.active_repetition_group_ids.append(sem1.semantic_cluster_key)

        s2 = _make_signal("you are useless")
        sem2 = interpret_signal(s2, kernel, store)
        assert sem2 is not None
        assert sem2.semantic_cluster_key == "assistant_insult_useless"
        assert sem2.repetition_count == 1
        kernel.conversation.active_repetition_group_ids.append(sem2.semantic_cluster_key)

        assert "assistant_insult_low_competence" in kernel.conversation.active_repetition_group_ids
        assert "assistant_insult_useless" in kernel.conversation.active_repetition_group_ids


class TestPragmaticDecay:
    def test_repetition_pressure_decays_by_half_after_half_life(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.conversation.dynamics = ConversationDynamics(last_updated_at=now)
        dynamics = kernel.conversation.dynamics
        dynamics.repetition_pressure = 0.8
        dynamics.last_updated_at = now

        semantics = ObservationSemantics(
            speech_act="unknown",
            repetition_count=0,
            affect={"frustration": 0.0, "hostility": 0.0, "playfulness": 0.0,
                    "valence": 0.0, "arousal": 0.0},
            confidence=0.0,
        )

        half_life_ms = 300000.0
        kernel.time.now = now + (half_life_ms / 1000.0)
        updated = update_conversation_dynamics(dynamics, semantics, kernel)
        assert updated.repetition_pressure <= 0.41, (
            f"Expected ~0.4, got {updated.repetition_pressure}"
        )
        assert updated.repetition_pressure > 0.35

    def test_frustration_decays_by_three_quarters_after_two_half_lives(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.user.affect = UserAffectState(last_updated_at=now)
        affect = kernel.user.affect
        affect.frustration = 1.0
        affect.last_updated_at = now

        semantics = ObservationSemantics(
            speech_act="unknown",
            repetition_count=0,
            affect={"frustration": 0.0, "hostility": 0.0, "playfulness": 0.0,
                    "valence": 0.0, "arousal": 0.0},
            confidence=0.0,
        )

        half_life_ms = 900000.0
        kernel.time.now = now + (2.0 * half_life_ms / 1000.0)
        updated = update_user_affect(affect, semantics, kernel)
        assert updated.frustration <= 0.26, (
            f"Expected ~0.25, got {updated.frustration}"
        )
        assert updated.frustration > 0.2

    def test_no_decay_with_zero_elapsed_time(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.user.affect = UserAffectState(last_updated_at=now)
        affect = kernel.user.affect
        affect.frustration = 0.7
        affect.last_updated_at = now

        semantics = ObservationSemantics(
            speech_act="unknown",
            repetition_count=0,
            affect={"frustration": 0.0, "hostility": 0.0, "playfulness": 0.0,
                    "valence": 0.0, "arousal": 0.0},
            confidence=0.0,
        )

        updated = update_user_affect(affect, semantics, kernel)
        assert updated.frustration == 0.7

    def test_affect_merge_clamps_to_range(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.user.affect = UserAffectState(last_updated_at=now)
        affect = kernel.user.affect
        affect.frustration = 0.9

        semantics = ObservationSemantics(
            speech_act="insult",
            repetition_count=0,
            affect={"frustration": 0.5, "hostility": 0.0, "playfulness": 0.0,
                    "valence": -0.4, "arousal": 0.5},
            confidence=0.8,
            semantic_cluster_key="assistant_insult_low_competence",
        )

        updated = update_user_affect(affect, semantics, kernel)
        assert updated.frustration == 1.0
        assert updated.frustration <= 1.0


class TestPragmaticCauseTracing:
    def test_insult_does_not_create_claims(self):
        store = _make_store()
        from cemm.registry import Registry
        from cemm.kernel.pipeline import Pipeline
        pipeline = Pipeline(store, Registry())

        pipeline.run("you are dumb")
        pipeline.run("you are daft")
        pipeline.run("you are a fool")

        all_claims = store.claims.find_active(limit=9999)
        for claim in all_claims:
            assert "dumb" not in claim.object_value.lower(), (
                f"Claim object_value contains insult content: {claim.object_value}"
            )
            assert claim.subject_entity_id != "self_main" or claim.domain != "insult", (
                "Self entity must not have insult claims"
            )

    def test_insult_not_stored_as_factual_self_claim(self):
        store = _make_store()
        from cemm.registry import Registry
        from cemm.kernel.pipeline import Pipeline
        pipeline = Pipeline(store, Registry())

        pipeline.run("you are dumb")

        all_claims = store.claims.find_active(limit=9999)
        for claim in all_claims:
            assert "dumb" not in claim.object_value.lower(), (
                f"Insult text leaked into claim: {claim.id} / {claim.object_value}"
            )


class TestPragmaticNonInsult:
    def test_question_returns_low_confidence(self):
        kernel = _make_kernel()
        store = _make_store()
        signal = _make_signal("What is my favorite database?")
        semantics = interpret_signal(signal, kernel, store)
        assert semantics is not None
        assert semantics.speech_act == "unknown"
        assert semantics.confidence == 0.0

    def test_question_does_not_change_affect(self):
        kernel = _make_kernel()
        store = _make_store()
        kernel.user.affect = UserAffectState(last_updated_at=kernel.time.now)
        affect = kernel.user.affect

        signal = _make_signal("What is my favorite database?")
        semantics = interpret_signal(signal, kernel, store)
        assert semantics is not None
        updated = update_user_affect(affect, semantics, kernel)
        assert updated.frustration == 0.0
        assert updated.hostility == 0.0
        assert updated.playfulness == 0.0
        assert updated.current_stance == "cooperative"

    def test_gratitude_detected(self):
        kernel = _make_kernel()
        store = _make_store()
        signal = _make_signal("thanks for your help")
        semantics = interpret_signal(signal, kernel, store)
        assert semantics is not None
        assert semantics.speech_act == "gratitude"
        assert semantics.stance == "positive"

    def test_praise_detected(self):
        kernel = _make_kernel()
        store = _make_store()
        signal = _make_signal("that is great")
        semantics = interpret_signal(signal, kernel, store)
        assert semantics is not None
        assert semantics.speech_act in ("claim", "gratitude")
        assert semantics.stance == "positive"
