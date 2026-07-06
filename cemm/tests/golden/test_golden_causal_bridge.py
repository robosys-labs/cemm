"""Golden test: CausalBridge adapter wiring.

Verifies that the CausalBridge is initialized in the runtime and
can produce predictions without errors when a store with causal
models is present.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.tests.harness import SeededSystem
from cemm.causal.causal_bridge import CausalBridge
from cemm.causal.inference import CausalInference
from cemm.store.store import Store


def test_causal_bridge_initialized_in_runtime():
    """Phase 7: The runtime should have a CausalBridge instance."""
    system = SeededSystem()
    bridge = system.runtime._causal_bridge
    assert bridge is not None, "CausalBridge should be initialized"
    assert isinstance(bridge, CausalBridge), \
        f"Expected CausalBridge, got {type(bridge)}"


def test_causal_bridge_has_causal_inference_when_store_present():
    """Phase 7: When a store with models is provided, bridge should wrap CausalInference."""
    system = SeededSystem()
    bridge = system.runtime._causal_bridge
    # The SeededSystem seeds causal models, so the bridge should have a CausalInference
    assert bridge._causal is not None, \
        "CausalBridge should have a CausalInference instance when store has models"
    assert isinstance(bridge._causal, CausalInference), \
        f"Expected CausalInference, got {type(bridge._causal)}"


def test_causal_bridge_predict_no_errors():
    """Phase 7: Running a turn should not produce causal bridge errors."""
    system = SeededSystem()
    result = system.run("What is water?")

    errors = result.get("errors", [])
    causal_errors = [e for e in errors if "causal" in e.lower()]
    assert len(causal_errors) == 0, \
        f"Should have no causal bridge errors, got: {causal_errors}"


def test_causal_bridge_empty_without_store():
    """Phase 7: CausalBridge without a store should return empty predictions."""
    bridge = CausalBridge()
    assert bridge._causal is None
    predictions = bridge.predict(graph=None, kernel=None)
    assert predictions == [], "Empty bridge should return no predictions"
