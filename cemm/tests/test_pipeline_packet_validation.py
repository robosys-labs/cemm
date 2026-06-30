from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def test_pipeline_result_packets_are_valid():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    assert result.kernel is not None
    assert result.semantic_event_graph is not None
    assert result.grounded_graph is not None
    assert result.memory_packet is not None
    assert result.context_inference is not None
    assert result.inference_packet is not None
    assert result.decision_packet is not None

    from dataclasses import asdict
    from cemm.kernel.packet_validator import validate_packet

    errors = validate_packet(asdict(result.semantic_event_graph), "semantic_event_graph")
    assert errors == [], errors
    errors = validate_packet(asdict(result.grounded_graph), "grounded_graph")
    assert errors == [], errors
    errors = validate_packet(asdict(result.memory_packet), "memory_packet")
    assert errors == [], errors
    errors = validate_packet(asdict(result.inference_packet), "inference_packet")
    assert errors == [], errors
    errors = validate_packet(asdict(result.decision_packet), "decision_packet")
    assert errors == [], errors


def test_pipeline_result_decision_packet_action_kind_is_valid():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    assert result.decision_packet is not None
    assert result.decision_packet.action_kind in ("answer", "ask", "remember", "update", "act", "abstain")
