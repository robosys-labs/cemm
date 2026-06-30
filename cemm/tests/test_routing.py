from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

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
from cemm.operators.update_claim import UpdateClaimOperator
from cemm.operators.create_model import CreateModelOperator
from cemm.operators.synthesize import SynthesizeOperator
from cemm.operators.simulate import SimulateOperator
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.operators.reflect import ReflectOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.call_tool import CallToolOperator
from cemm.__main__ import seed_registry


def test_decision_router_abstain_is_respected() -> None:
    """When DecisionRouter returns abstain at confidence >= threshold,
    process_input must route through AbstainOperator (producing a SemanticAnswerGraph
    before text) rather than falling through to AnswerOperator with empty claims."""
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)

    for op in [
        AnswerOperator(), AskOperator(), RememberOperator(),
        UpdateClaimOperator(), CreateModelOperator(), SynthesizeOperator(),
        SimulateOperator(), RetrieveOperator(), ReflectOperator(),
        AbstainOperator(), CallToolOperator(),
    ]:
        op_registry.register(op)

    from cemm.__main__ import process_input

    output = process_input(
        "xyzzy nonsense input", store, registry, op_registry, pipeline,
        online_learner, recursive_loop, "test_session", [0],
    )

    # Phase 2/4 fallback produces "I don't have enough information to answer."
    # Phase 0 DecisionRouter abstain produces a reason-grounded abstain message.
    assert "I don't have enough information" not in output, (
        f"Expected DecisionRouter abstain, got Phase 2/4 fallback: {output!r}"
    )
    assert output, "Output must be non-empty"


def test_self_reference_injection_still_answers() -> None:
    """Self-referential queries like 'who are you?' should still produce
    an answer via memory_packet update -> DecisionRouter answer path,
    not fall through to Phase 2 hardcoded routing."""
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)

    for op in [
        AnswerOperator(), AskOperator(), RememberOperator(),
        UpdateClaimOperator(), CreateModelOperator(), SynthesizeOperator(),
        SimulateOperator(), RetrieveOperator(), ReflectOperator(),
        AbstainOperator(), CallToolOperator(),
    ]:
        op_registry.register(op)

    from cemm.__main__ import seed_self_state, process_input

    seed_self_state(store)

    output = process_input(
        "who are you?", store, registry, op_registry, pipeline,
        online_learner, recursive_loop, "test_session", [0],
    )

    assert output, "Self-referential query must produce non-empty output"
    assert "do not have enough" not in output, (
        f"Expected answer, got abstain: {output!r}"
    )
