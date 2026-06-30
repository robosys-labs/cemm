from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import seed_registry, seed_self_state


def _setup():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    return pipeline


def test_remember_input_populates_action_ref():
    pipeline = _setup()
    result = pipeline.run("remember I like coffee", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.action_refs
    assert any("remember" in ref.lower() for ref in seg.action_refs)


def test_greeting_populates_action_ref():
    pipeline = _setup()
    result = pipeline.run("hello", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.action_refs
    assert any("greeting" in ref.lower() for ref in seg.action_refs)


def test_model_refs_populated_for_known_processes():
    pipeline = _setup()
    result = pipeline.run("rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    # The causal_causes process should map to a model if one exists
    assert seg.model_refs is not None
