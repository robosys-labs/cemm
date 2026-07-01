from __future__ import annotations
import os
import sys
from contextlib import contextmanager

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
from cemm.kernel.invariant_guard import InvariantGuard


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


@contextmanager
def _capture_call(method_name: str):
    original = getattr(InvariantGuard, method_name)
    calls = []

    def wrapper(cls, *args, **kwargs):
        calls.append(method_name)
        return original.__func__(cls, *args, **kwargs)

    setattr(InvariantGuard, method_name, classmethod(wrapper))
    try:
        yield calls
    finally:
        setattr(InvariantGuard, method_name, original)


def test_recursive_budget_check_is_called():
    with _capture_call("check_recursive_budget") as calls:
        store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
        process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert "check_recursive_budget" in calls


def test_uol_not_bypassing_registry_check_is_called():
    with _capture_call("check_uol_not_bypassing_registry") as calls:
        store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
        process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert "check_uol_not_bypassing_registry" in calls


def test_context_not_override_explicit_check_is_called():
    with _capture_call("check_context_not_override_explicit") as calls:
        store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
        process_input("remember I like coffee", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
        process_input("what do I like", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert "check_context_not_override_explicit" in calls


def test_prediction_not_fact_check_is_called():
    with _capture_call("check_prediction_not_fact") as calls:
        store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
        process_input("rain causes flooding", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert "check_prediction_not_fact" in calls
