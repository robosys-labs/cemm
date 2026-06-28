from __future__ import annotations
import time
import pytest
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.semantic_clusters import SemanticClusterRegistry
from cemm.kernel.pragmatic_interpreter import interpret_signal, update_pragmatic_state
from cemm.types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from cemm.types.context_kernel import ContextKernel, PragmaticState
from cemm.types.permission import Permission
from cemm.types.self_state import SelfState


def _make_store() -> Store:
    s = Store(":memory:")
    s.self_store.put(SelfState(id="self_main", name="cemm", created_at=time.time(), updated_at=time.time()))
    return s


def _make_kernel(context_id: str = "test_ctx") -> ContextKernel:
    k = ContextKernel(id=context_id, permission=Permission.public())
    k.time.now = time.time()
    k.conversation.pragmatic_state = PragmaticState(last_updated_at=k.time.now)
    k.user.session_affect = PragmaticState(last_updated_at=k.time.now)
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
        kernel.self_state = self_state

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
            kernel.conversation.repetition_counts[semantics.semantic_cluster_key] = semantics.repetition_count
            kernel.conversation.pragmatic_state = update_pragmatic_state(
                kernel.conversation.pragmatic_state, semantics, kernel
            )

        assert counts == [1, 2, 3], f"Expected [1, 2, 3], got {counts}"

    def test_frustration_grows_with_repetition(self):
        kernel = _make_kernel()
        store = _make_store()
        self_state = _make_self_state()
        kernel.self_state = self_state

        for i in range(3):
            signal = _make_signal("you are dumb", observed_at=time.time() + i)
            semantics = interpret_signal(signal, kernel, store)
            assert semantics is not None
            if semantics.semantic_cluster_key not in kernel.conversation.active_repetition_group_ids:
                kernel.conversation.active_repetition_group_ids.append(semantics.semantic_cluster_key)
            kernel.conversation.repetition_counts[semantics.semantic_cluster_key] = semantics.repetition_count
            kernel.conversation.pragmatic_state = update_pragmatic_state(
                kernel.conversation.pragmatic_state, semantics, kernel
            )

        assert kernel.conversation.pragmatic_state.frustration > 0.5
        assert kernel.conversation.pragmatic_state.hostility > 0.2
        assert kernel.conversation.pragmatic_state.current_stance in ("frustrated", "hostile")

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
        kernel.self_state = self_state

        s1 = _make_signal("you are dumb")
        sem1 = interpret_signal(s1, kernel, store)
        assert sem1 is not None
        kernel.conversation.active_repetition_group_ids.append(sem1.semantic_cluster_key)
        kernel.conversation.repetition_counts[sem1.semantic_cluster_key] = sem1.repetition_count

        s2 = _make_signal("you are useless")
        sem2 = interpret_signal(s2, kernel, store)
        assert sem2 is not None
        assert sem2.semantic_cluster_key == "assistant_insult_useless"
        assert sem2.repetition_count == 1
        kernel.conversation.active_repetition_group_ids.append(sem2.semantic_cluster_key)
        kernel.conversation.repetition_counts[sem2.semantic_cluster_key] = sem2.repetition_count

        assert kernel.conversation.repetition_counts.get("assistant_insult_low_competence") == 1
        assert kernel.conversation.repetition_counts.get("assistant_insult_useless") == 1


class TestPragmaticDecay:
    def test_repetition_pressure_decays_by_half_after_half_life(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.conversation.pragmatic_state = PragmaticState(last_updated_at=now)
        pragmatic = kernel.conversation.pragmatic_state
        pragmatic.repetition_pressure = 0.8
        pragmatic.last_updated_at = now

        semantics = ObservationSemantics(
            speech_act="unknown",
            repetition_count=0,
            affect={"frustration": 0.0, "hostility": 0.0, "playfulness": 0.0,
                    "valence": 0.0, "arousal": 0.0},
            confidence=0.0,
        )

        half_life_ms = 300000.0
        kernel.time.now = now + (half_life_ms / 1000.0)
        updated = update_pragmatic_state(pragmatic, semantics, kernel)
        assert updated.repetition_pressure <= 0.41, (
            f"Expected ~0.4, got {updated.repetition_pressure}"
        )
        assert updated.repetition_pressure > 0.35

    def test_frustration_decays_by_three_quarters_after_two_half_lives(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.conversation.pragmatic_state = PragmaticState(last_updated_at=now)
        pragmatic = kernel.conversation.pragmatic_state
        pragmatic.frustration = 1.0
        pragmatic.last_updated_at = now

        semantics = ObservationSemantics(
            speech_act="unknown",
            repetition_count=0,
            affect={"frustration": 0.0, "hostility": 0.0, "playfulness": 0.0,
                    "valence": 0.0, "arousal": 0.0},
            confidence=0.0,
        )

        half_life_ms = 900000.0
        kernel.time.now = now + (2.0 * half_life_ms / 1000.0)
        updated = update_pragmatic_state(pragmatic, semantics, kernel)
        assert updated.frustration <= 0.26, (
            f"Expected ~0.25, got {updated.frustration}"
        )
        assert updated.frustration > 0.2

    def test_no_decay_with_zero_elapsed_time(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.conversation.pragmatic_state = PragmaticState(last_updated_at=now)
        pragmatic = kernel.conversation.pragmatic_state
        pragmatic.frustration = 0.7
        pragmatic.last_updated_at = now

        semantics = ObservationSemantics(
            speech_act="unknown",
            repetition_count=0,
            affect={"frustration": 0.0, "hostility": 0.0, "playfulness": 0.0,
                    "valence": 0.0, "arousal": 0.0},
            confidence=0.0,
        )

        updated = update_pragmatic_state(pragmatic, semantics, kernel)
        assert updated.frustration == 0.7

    def test_affect_merge_clamps_to_range(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.conversation.pragmatic_state = PragmaticState(last_updated_at=now)
        pragmatic = kernel.conversation.pragmatic_state
        pragmatic.frustration = 0.9

        semantics = ObservationSemantics(
            speech_act="insult",
            repetition_count=0,
            affect={"frustration": 0.5, "hostility": 0.0, "playfulness": 0.0,
                    "valence": -0.4, "arousal": 0.5},
            confidence=0.8,
            semantic_cluster_key="assistant_insult_low_competence",
        )

        updated = update_pragmatic_state(pragmatic, semantics, kernel)
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
        kernel.conversation.pragmatic_state = PragmaticState(last_updated_at=kernel.time.now)
        pragmatic = kernel.conversation.pragmatic_state

        signal = _make_signal("What is my favorite database?")
        semantics = interpret_signal(signal, kernel, store)
        assert semantics is not None
        updated = update_pragmatic_state(pragmatic, semantics, kernel)
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
