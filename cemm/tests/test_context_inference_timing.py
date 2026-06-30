from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def test_context_inference_runs_before_interpret():
    """Context inference should be applied to the kernel before
    UOL/semantic interpretation, so the inferred frame can bias
    interpretation."""
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    kernel = result.kernel
    assert kernel is not None
    # The kernel should have the inferred frame in active frames
    assert "session_opening" in kernel.memory.active_frame_ids or "greeting" in kernel.memory.active_frame_ids
    assert result.context_inference is not None
    assert result.context_inference.frame_id in ("session_opening", "greeting")


def test_context_inference_frame_available_before_interpret():
    """The inferred frame should be present in the kernel when the semantic
    interpreter runs. We verify this by checking the active frame exists and
    that the observation_semantics reflect the same speech act."""
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test", budget_override={"max_entities": 10})
    kernel = result.kernel
    seg = result.semantic_event_graph
    assert seg is not None
    assert result.context_inference is not None
    assert result.context_inference.frame_id in ("session_opening", "greeting")
    # The kernel should have the inferred frame active
    assert result.context_inference.frame_id in kernel.memory.active_frame_ids
    # The observation semantics should match the context inference
    assert result.signals[0].observation_semantics is not None
    assert result.signals[0].observation_semantics.speech_act == "greeting"


def test_context_inference_runs_before_semantic_interpreter_monkeypatch():
    """Use a monkeypatch to capture kernel.active_frame_ids at the moment the
    semantic interpreter starts. The inferred frame must already be active."""
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)

    observed_frame_ids: list[list[str]] = []

    original_run = pipeline._semantic_interpreter.run

    def _capture_run(signal, kernel):
        observed_frame_ids.append(list(kernel.memory.active_frame_ids))
        return original_run(signal, kernel)

    pipeline._semantic_interpreter.run = _capture_run
    result = pipeline.run("hello", context_id="ctx_test", budget_override={"max_entities": 10})

    assert result.context_inference is not None
    assert result.context_inference.frame_id in ("session_opening", "greeting")
    assert observed_frame_ids
    assert result.context_inference.frame_id in observed_frame_ids[0]
