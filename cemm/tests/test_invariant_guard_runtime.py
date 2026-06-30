from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import process_input
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop


def _setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    from cemm.__main__ import seed_registry, seed_self_state
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_invariant_guard_runs_after_operator_execution():
    """InvariantGuard checks should be invoked after operator execution."""
    from cemm.kernel.invariant_guard import InvariantGuard
    calls = []
    original_reset = InvariantGuard.reset
    original_check = InvariantGuard.check_action_has_trace

    def capture_reset(cls):
        calls.append("reset")
        return original_reset.__func__(cls)

    def capture_check(cls, action):
        calls.append("check_action_has_trace")
        return original_check.__func__(cls, action)

    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()

    InvariantGuard.reset = classmethod(capture_reset)
    InvariantGuard.check_action_has_trace = classmethod(capture_check)
    try:
        process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    finally:
        InvariantGuard.reset = original_reset
        InvariantGuard.check_action_has_trace = original_check

    assert "reset" in calls
    assert "check_action_has_trace" in calls
