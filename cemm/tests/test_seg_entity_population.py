from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import seed_registry, seed_self_state


def test_causal_input_populates_entity_refs():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    result = pipeline.run("rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg is not None
    assert seg.causal_edges
    edge = seg.causal_edges[0]
    assert edge["cause_id"] != "unknown"
    assert edge["effect_id"] != "unknown"
    assert any(e.get("entity_id") == edge["cause_id"] for e in seg.entity_refs)
    assert any(e.get("entity_id") == edge["effect_id"] for e in seg.entity_refs)


def test_causal_input_populates_claim_candidates():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    result = pipeline.run("rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.claim_candidates
    candidate = seg.claim_candidates[0]
    assert candidate["subject"] != "user" or candidate["predicate"] != "causes"
