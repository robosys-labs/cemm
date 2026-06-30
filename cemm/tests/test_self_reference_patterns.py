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


def test_common_words_do_not_trigger_self_reference():
    """A question containing 'you' as a normal pronoun should not be treated as a self-reference query."""
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    process_input("do you like pizza", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    kernel = recursive_loop._last_result.kernel
    assert "self_main" not in kernel.memory.working_entity_ids


def test_possessive_self_reference_is_not_triggered():
    """'what is your favorite color' is about the user, not the system."""
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    process_input("what is your favorite color", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    kernel = recursive_loop._last_result.kernel
    assert "self_main" not in kernel.memory.working_entity_ids


def test_explicit_self_reference_still_works():
    """A genuine self-reference query should still inject the self entity."""
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    process_input("what do you know about yourself", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    kernel = recursive_loop._last_result.kernel
    assert "self_main" in kernel.memory.working_entity_ids
