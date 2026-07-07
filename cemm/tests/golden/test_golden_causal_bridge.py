"""Golden test: CausalBridge adapter wiring.

Verifies that the CausalBridge is initialized in the runtime and
can produce predictions without errors when a DurableSemanticStore
with causal relations is present.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.tests.harness import SeededSystem
from cemm.causal.causal_bridge import CausalBridge
from cemm.memory.durable_semantic_store import DurableSemanticStore


def test_causal_bridge_initialized_in_runtime():
    """The runtime should have a CausalBridge instance."""
    system = SeededSystem()
    bridge = system.runtime._causal_bridge
    assert bridge is not None, "CausalBridge should be initialized"
    assert isinstance(bridge, CausalBridge), \
        f"Expected CausalBridge, got {type(bridge)}"


def test_causal_bridge_has_durable_store():
    """CausalBridge should be wired with a DurableSemanticStore."""
    system = SeededSystem()
    bridge = system.runtime._causal_bridge
    assert bridge._store is not None, \
        "CausalBridge should have a DurableSemanticStore instance"
    assert isinstance(bridge._store, DurableSemanticStore), \
        f"Expected DurableSemanticStore, got {type(bridge._store)}"


def test_causal_bridge_predict_no_errors():
    """Running a turn should not produce causal bridge errors."""
    system = SeededSystem()
    result = system.run("What is water?")

    errors = result.get("errors", [])
    causal_errors = [e for e in errors if "causal" in e.lower()]
    assert len(causal_errors) == 0, \
        f"Should have no causal bridge errors, got: {causal_errors}"


def test_causal_bridge_empty_without_store():
    """CausalBridge without a store should return empty predictions."""
    bridge = CausalBridge()
    assert bridge._store is None
    predictions = bridge.predict(graph=None, kernel=None)
    assert predictions == [], "Empty bridge should return no predictions"
