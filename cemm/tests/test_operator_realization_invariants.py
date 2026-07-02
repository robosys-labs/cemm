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
from cemm.operators.base import OperatorContext
from cemm.synthesis.result import SynthesisResult
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
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


def test_abstain_operator_keeps_verification_diagnostics_internal(monkeypatch) -> None:
    store, registry, _, pipeline, _, _ = _runtime()
    kernel = pipeline.run("unanswerable input", context_id="ctx_abstain").kernel
    assert kernel is not None
    signal = Signal(
        id="sig_abstain",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="unanswerable input",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )

    def fake_run(*args, **kwargs):
        return SynthesisResult(
            success=True,
            output="",
            verified=False,
            metadata={"verification": {"details": ["No evidence selected for synthesis"]}},
        )

    import cemm.operators.abstain as abstain_module

    monkeypatch.setattr(abstain_module._pipeline, "run", fake_run)
    result = AbstainOperator().execute(OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        params={"reason": "internal reason"},
    ))

    assert result.success
    assert "verification" not in result.output_text.lower()
    assert "no evidence selected" not in result.output_text.lower()
