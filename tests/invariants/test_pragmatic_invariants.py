from __future__ import annotations
import time
import pytest
from cemm.kernel.semantic_clusters import SemanticClusterRegistry
from cemm.kernel.pragmatic_interpreter import interpret_signal, update_pragmatic_state
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.context_kernel import ContextKernel, PragmaticState
from cemm.types.permission import Permission
from cemm.types.self_state import SelfState
from cemm.store.store import Store


def _make_kernel() -> ContextKernel:
    k = ContextKernel(id="invariant_test", permission=Permission.public())
    k.time.now = time.time()
    k.conversation.pragmatic_state = PragmaticState(last_updated_at=k.time.now)
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
        context_id="invariant_ctx",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


class TestPragmaticInvariant_RepetitionByMeaning:
    def test_paraphrased_insults_same_cluster(self):
        reg = SemanticClusterRegistry()
        _, c1, _ = reg.match("you are dumb")
        _, c2, _ = reg.match("you are daft")
        _, c3, _ = reg.match("you are a fool")
        assert c1 == c2 == c3 == "assistant_insult_low_competence"

    def test_paraphrased_insults_increment_repetition(self):
        kernel = _make_kernel()
        store = Store(":memory:")
        store.self_store.put(SelfState(
            id="self_main", name="cemm", created_at=time.time(), updated_at=time.time()
        ))
        kernel.self_state = SelfState(id="self_main", name="cemm", created_at=0.0, updated_at=0.0)

        texts = ["you are dumb", "you are daft", "you are a fool"]
        counts = []
        for i, text in enumerate(texts):
            sig = _make_signal(text, observed_at=time.time() + i)
            sem = interpret_signal(sig, kernel, store)
            assert sem is not None
            counts.append(sem.repetition_count)
            if sem.semantic_cluster_key and sem.semantic_cluster_key not in kernel.conversation.active_repetition_group_ids:
                kernel.conversation.active_repetition_group_ids.append(sem.semantic_cluster_key)
            kernel.conversation.repetition_counts[sem.semantic_cluster_key] = sem.repetition_count

        assert counts == [1, 2, 3], (
            f"Paraphrased insults must increment repetition_count: {counts}"
        )


class TestPragmaticInvariant_FrustrationNotPersistedAsIdentity:
    def test_frustration_in_pragmatic_state_not_claims(self):
        kernel = _make_kernel()
        store = Store(":memory:")
        store.self_store.put(SelfState(
            id="self_main", name="cemm", created_at=time.time(), updated_at=time.time()
        ))
        kernel.self_state = SelfState(id="self_main", name="cemm", created_at=0.0, updated_at=0.0)

        for i in range(3):
            sig = _make_signal("you are dumb", observed_at=time.time() + i)
            sem = interpret_signal(sig, kernel, store)
            assert sem is not None
            if sem.semantic_cluster_key and sem.semantic_cluster_key not in kernel.conversation.active_repetition_group_ids:
                kernel.conversation.active_repetition_group_ids.append(sem.semantic_cluster_key)
            kernel.conversation.repetition_counts[sem.semantic_cluster_key] = sem.repetition_count
            kernel.conversation.pragmatic_state = update_pragmatic_state(
                kernel.conversation.pragmatic_state, sem, kernel
            )

        assert kernel.conversation.pragmatic_state.frustration > 0.5

        all_claims = store.claims.find_active(limit=9999)
        for claim in all_claims:
            assert "frustrated" not in claim.object_value.lower()
            assert "dumb" not in claim.object_value.lower()

    def test_stance_resets_to_cooperative_after_decay(self):
        kernel = _make_kernel()
        now = time.time()
        kernel.time.now = now
        kernel.conversation.pragmatic_state = PragmaticState(last_updated_at=now)
        pragmatic = kernel.conversation.pragmatic_state
        pragmatic.frustration = 0.9
        pragmatic.current_stance = "frustrated"
        pragmatic.last_updated_at = now

        null_sem = type('NullSem', (), {
            'speech_act': 'unknown', 'repetition_count': 0,
            'affect': {'frustration': 0.0, 'hostility': 0.0, 'playfulness': 0.0,
                       'valence': 0.0, 'arousal': 0.0},
            'semantic_cluster_key': '', 'target_entity_id': '',
            'repetition_group_id': '', 'stance': 'unknown',
            'cause_hypothesis_claim_ids': [], 'decay_half_life_ms': 900000.0,
            'confidence': 0.0,
        })()

        kernel.time.now = now + 7200.0
        updated = update_pragmatic_state(pragmatic, null_sem, kernel)
        assert updated.current_stance == "cooperative", (
            f"Stance should reset to cooperative after 2h of silence, got {updated.current_stance}"
        )
        assert updated.frustration < 0.01


class TestPragmaticInvariant_InsultsNotSelfClaims:
    def test_insult_no_factual_claim_created(self):
        store = Store(":memory:")
        store.self_store.put(SelfState(
            id="self_main", name="cemm", created_at=time.time(), updated_at=time.time()
        ))
        from cemm.registry import Registry
        from cemm.kernel.pipeline import Pipeline
        pipeline = Pipeline(store, Registry())

        pipeline.run("you are dumb")

        all_claims = store.claims.find_active(limit=9999)
        for claim in all_claims:
            tokens = ["dumb", "daft", "stupid", "fool", "idiot", "useless", "worthless", "broken"]
            assert not any(t in claim.object_value.lower() for t in tokens), (
                f"Insult token found in claim object_value: '{claim.object_value}'"
            )
            assert not any(t in claim.predicate.lower() for t in tokens), (
                f"Insult token found in claim predicate: '{claim.predicate}'"
            )
