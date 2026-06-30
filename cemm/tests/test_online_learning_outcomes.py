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
from cemm.types.action import ActionKind


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


def test_online_learner_records_failure():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    recorded = []
    original_record = online_learner.record_outcome
    def capture_record(source_id, domain, success):
        recorded.append((source_id, domain, success))
        return original_record(source_id, domain, success)
    online_learner.record_outcome = capture_record

    # Deregister the answer operator so the greeting decision triggers an unknown operator failure
    if ActionKind.ANSWER in op_registry._operators:
        del op_registry._operators[ActionKind.ANSWER]
    process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert recorded
    assert any(success is False for _, _, success in recorded), "Expected at least one failure outcome"


def test_online_learner_records_success():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    recorded = []
    original_record = online_learner.record_outcome
    def capture_record(source_id, domain, success):
        recorded.append((source_id, domain, success))
        return original_record(source_id, domain, success)
    online_learner.record_outcome = capture_record

    process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert recorded
    assert any(success is True for _, _, success in recorded), "Expected at least one success outcome"
