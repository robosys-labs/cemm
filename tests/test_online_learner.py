from __future__ import annotations
from cemm.learning.online import OnlineLearner
from cemm.store.store import Store
from cemm.types.model import Model, ModelKind, ModelStatus
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.permission import Permission
import time


class TestCausalModelConfidenceUpdate:
    def _make_model(self, store: Store, model_id: str, confidence: float = 0.7) -> Model:
        model = Model(
            id=model_id, kind=ModelKind.CAUSAL_RULE, name="test_rule",
            confidence=confidence, trust=0.8, status=ModelStatus.ACTIVE,
            created_at=time.time(), updated_at=time.time(),
        )
        store.models.put(model)
        return model

    def test_update_increases_on_match(self):
        store = Store(":memory:")
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        model = self._make_model(store, "m1", confidence=0.5)
        learner.update_causal_model_confidence("m1", prediction_matched=True)
        updated = store.models.get("m1")
        assert updated is not None
        assert updated.confidence > 0.5

    def test_update_decreases_on_mismatch(self):
        store = Store(":memory:")
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        model = self._make_model(store, "m2", confidence=0.9)
        learner.update_causal_model_confidence("m2", prediction_matched=False)
        updated = store.models.get("m2")
        assert updated is not None
        assert updated.confidence < 0.9

    def test_trust_increases_on_match(self):
        store = Store(":memory:")
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        self._make_model(store, "m3", confidence=0.7)
        learner.update_causal_model_confidence("m3", prediction_matched=True)
        updated = store.models.get("m3")
        assert updated is not None
        assert updated.trust > 0.8

    def test_trust_decreases_on_mismatch(self):
        store = Store(":memory:")
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        self._make_model(store, "m4", confidence=0.7)
        learner.update_causal_model_confidence("m4", prediction_matched=False)
        updated = store.models.get("m4")
        assert updated is not None
        assert updated.trust < 0.8

    def test_noop_without_model_store(self):
        store = Store(":memory:")
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
        learner.update_causal_model_confidence("m1", True)

    def test_noop_for_nonexistent_model(self):
        store = Store(":memory:")
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        learner.update_causal_model_confidence("nonexistent", True)
