from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.__main__ import seed_registry, seed_self_state, process_input
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.learning.inductor import Inductor
from cemm.learning.online import OnlineLearner
from cemm.operators.abstain import AbstainOperator
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.registry import OperatorRegistry
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.store.store import Store
from cemm.registry import Registry


def _runtime():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), RetrieveOperator(), AbstainOperator()]:
        op_registry.register(op)
    pipeline = Pipeline(store, registry)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    loop = RecursiveLoop(pipeline, store, learner, Inductor(store, registry=registry))
    return store, registry, op_registry, pipeline, learner, loop


def _turn(text: str):
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    output = process_input(text, store, registry, op_registry, pipeline, learner, loop, f"ctx_{int(time.time())}", [0])
    return output, loop


def test_ask_output_has_sag_and_realization_metadata() -> None:
    output, loop = _turn("what is the weather?")
    assert output
    result = loop._last_result
    decision = result.decision_packet
    assert decision is not None
    assert decision.action_kind in {"ask", "abstain", "remember"}
    assert decision.action_plan is not None


def test_remember_output_is_realized_from_sag_not_manual_text() -> None:
    output, loop = _turn("remember I like coffee")
    assert output
    trace = loop._last_result.kernel.memory.working_signal_ids
    assert trace


def test_retrieve_output_is_realized_from_sag_not_manual_text() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("remember I like coffee", store, registry, op_registry, pipeline, learner, loop, "ctx_retrieve", [0])
    output = process_input("what do I like?", store, registry, op_registry, pipeline, learner, loop, "ctx_retrieve", [1])
    assert output
