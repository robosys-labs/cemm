from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.__main__ import seed_registry, seed_self_state
from cemm.kernel.training_export import serialize_turn
from cemm.operators.answer import AnswerOperator
from cemm.operators.base import OperatorContext
from cemm.registry import Registry
from cemm.store.store import Store
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.signal import Signal, SignalKind, SourceType


def test_answer_trace_exports_realization_strategy_and_verified_flag() -> None:
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    kernel = ContextKernel(id="ctx_meta", permission=Permission.public())
    kernel.time.now = time.time()
    signal = Signal(
        id="sig_meta",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="hello",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=Permission.public(),
    )
    result = AnswerOperator().execute(OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        params={"intent": "greeting"},
    ))
    assert result.trace is not None
    records = serialize_turn(
        "hello",
        result.output_text,
        kernel,
        signal,
        trace=result.trace,
        semantic_answer_graph=result.semantic_answer_graph,
    )
    full = records[0]["payload"]
    assert full["realization_metadata"]["strategy"] == "template"
    assert full["realization_metadata"]["verified"] is True
