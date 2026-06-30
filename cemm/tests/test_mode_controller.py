from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.mode_controller import ModeController
from cemm.types.self_view import SelfView


def test_mode_controller_triggers_researcher_when_uncertain() -> None:
    """ModeController should suggest researcher mode when uncertainty is high."""
    controller = ModeController()
    sv = SelfView(uncertainty=0.8, coherence=0.9, recent_error_rate=0.0)
    new_mode = controller.evaluate(sv)
    assert new_mode == "researcher"


def test_mode_controller_no_change_when_assistant() -> None:
    """When all metrics are healthy, assistant mode is correct — no transition."""
    controller = ModeController()
    sv = SelfView(uncertainty=0.1, coherence=0.9, recent_error_rate=0.0)
    new_mode = controller.evaluate(sv)
    assert new_mode is None


def test_pipeline_sets_uncertainty_for_empty_state() -> None:
    """Pipeline.run() must update self_view.uncertainty so ModeController
    can detect bootstrapped (no-data) state and recommend researcher mode."""
    import uuid
    from cemm.store.store import Store
    from cemm.registry import Registry
    from cemm.kernel.pipeline import Pipeline

    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id=uuid.uuid4().hex[:16])
    assert result.kernel is not None
    # With no stored claims, uncertainty should be > 0.2
    assert result.kernel.self_view.uncertainty > 0.2, (
        f"Bootstrapped system should have >0.2 uncertainty, got {result.kernel.self_view.uncertainty}"
    )

    controller = ModeController()
    new_mode = controller.evaluate(result.kernel.self_view)
    # If uncertainty >= 0.7, should trigger researcher mode
    if result.kernel.self_view.uncertainty >= 0.7:
        assert new_mode is not None, "ModeController should trigger mode change when uncertainty is high"
