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
    for op in [
        AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator(),
    ]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_trace_records_semantic_event_graph_id_for_answer():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    captured = []
    original_execute = op_registry.execute
    def capture_execute(kind, ctx):
        result = original_execute(kind, ctx)
        captured.append(result)
        return result
    op_registry.execute = capture_execute
    process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert captured
    for result in captured:
        if result.trace and result.trace.semantic_event_graph_id:
            assert result.trace.semantic_event_graph_id
            return
    raise AssertionError("No operator result trace with semantic_event_graph_id found")


def test_trace_records_semantic_event_graph_id_for_remember():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    captured = []
    original_execute = op_registry.execute
    def capture_execute(kind, ctx):
        result = original_execute(kind, ctx)
        captured.append(result)
        return result
    op_registry.execute = capture_execute
    process_input("remember I like coffee", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert captured
    for result in captured:
        if result.trace and result.trace.semantic_event_graph_id:
            assert result.trace.semantic_event_graph_id
            return
    raise AssertionError("No operator result trace with semantic_event_graph_id found")
