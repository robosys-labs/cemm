from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def test_pipeline_result_carries_inference_packet():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("rain causes flooding", context_id="ctx_test")
    assert result.inference_packet is not None
    assert result.inference_packet.id
    assert result.inference_packet.inference_graph_input_signal_ids


def test_pipeline_result_carries_decision_packet():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    assert result.decision_packet is not None
    assert result.decision_packet.action_kind in ("answer", "ask", "abstain", "remember")


def test_pipeline_result_includes_context_inference():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("ok", context_id="ctx_test")
    assert result.context_inference is not None
    assert result.context_inference.frame_id == "acknowledgment"
