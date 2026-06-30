from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.abstain import AbstainOperator
from cemm.__main__ import seed_registry, seed_self_state, seed_causal_models, process_input


def _setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    seed_causal_models(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), AbstainOperator()]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_causal_inference_seeds_active_model():
    store = Store(":memory:")
    from cemm.types.model import ModelKind, ModelStatus
    seed_causal_models(store)
    models = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    assert models
    assert any(m.id == "causal_rain_flooding" for m in models)


def test_causal_inference_populates_predictions():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    # A causal input should trigger CausalInference and populate predictions
    output = process_input("rain causes flooding", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    result = recursive_loop._last_result
    assert result is not None
    assert result.inference_packet is not None
    assert any("flood" in p.get("predicate", "").lower() for p in result.inference_packet.predictions), result.inference_packet.predictions
