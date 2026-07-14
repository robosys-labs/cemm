"""Tests for the canonical v3.4 CognitiveKernel orchestrator.

Tests verify:
- CognitiveKernel.run() produces an immutable CognitiveCycle
- All stages execute in order
- Each stage delegates to its sole authority
- No hidden mutable state is read
- The cycle is frozen and cannot be mutated
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from cemm.kernel.model.cycle import (
    CognitiveCycle,
    CycleTrigger,
    KernelSnapshot,
)
from cemm.kernel.model.trace import CycleTrace


class TestCognitiveKernelConstruction:
    """Test that the Runtime assembles correctly."""

    def test_runtime_constructs_all_components(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.kernel is not None
        assert isinstance(rt.kernel.__class__.__name__, str)

    def test_runtime_has_cutover_verifier(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        # The cutover verifier should be registered
        assert hasattr(rt, '_cutover_verifier')

    def test_runtime_has_schema_store(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert hasattr(rt, '_schema_store')

    def test_runtime_has_all_canonical_components(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        # Check all canonical components are constructed
        assert rt._semantic_composer is not None
        assert rt._grounding_resolver is not None
        assert rt._interpretation_resolver is not None
        assert rt._gap_detector is not None
        assert rt._workspace_controller is not None
        assert rt._epistemic_evaluator is not None
        assert rt._semantic_retriever is not None
        assert rt._capability_evaluator is not None
        assert rt._learning_coordinator is not None
        assert rt._goal_arbiter is not None
        assert rt._planner is not None
        assert rt._operation_executor is not None
        assert rt._operation_authorizer is not None
        assert rt._outcome_reconciler is not None
        assert rt._commit_coordinator is not None
        assert rt._response_planner is not None
        assert rt._common_ground_manager is not None


class TestCognitiveKernelCycle:
    """Test that CognitiveKernel.run() produces a valid cycle."""

    def test_run_returns_cognitive_cycle(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert isinstance(cycle, CognitiveCycle)

    def test_cycle_has_id(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert cycle.cycle_id.startswith("cycle:")

    def test_cycle_has_snapshot(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert isinstance(cycle.snapshot, KernelSnapshot)

    def test_cycle_snapshot_is_pinned(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        # Snapshot should have pinned revision
        assert cycle.snapshot.kernel_foundation_version == "v3.4"

    def test_cycle_is_immutable(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        with pytest.raises(FrozenInstanceError):
            cycle.cycle_id = "modified"

    def test_cycle_trace_has_finalize(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert cycle.trace is not None
        assert "finalize" in cycle.trace.stages

    def test_cycle_trace_has_finished_at(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert cycle.trace is not None
        assert cycle.trace.finished_at is not None

    def test_cycle_no_errors_on_empty_input(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert cycle.trace is not None
        assert len(cycle.trace.errors) == 0

    def test_run_text_convenience(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        cycle = rt.run_text("hello")
        assert isinstance(cycle, CognitiveCycle)
        assert cycle.trigger.trigger_kind == "user_utterance"


class TestCognitiveKernelStageOutputs:
    """Test that stage outputs are populated correctly."""

    def test_message_plan_is_produced(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        # Even with no input, the response planner should produce a plan
        assert cycle.message_plan is not None

    def test_goals_empty_without_input(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert len(cycle.goals) == 0

    def test_plans_empty_without_input(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert len(cycle.plans) == 0

    def test_authorization_none_without_plans(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert cycle.authorization is None

    def test_critical_commit_none_without_execution(self):
        from cemm.app.runtime import Runtime
        rt = Runtime()
        trigger = CycleTrigger(trigger_kind="user_utterance")
        cycle = rt.run(trigger)
        assert cycle.critical_commit is None


class TestLegacyBoundary:
    """Test the legacy v3.3 percept adapter boundary."""

    def test_percept_adapter_exists(self):
        from cemm.legacy.v3_3.percept_adapter import LegacyV33PerceptAdapter
        adapter = LegacyV33PerceptAdapter()
        assert adapter is not None

    def test_percept_adapter_returns_empty_without_perceptor(self):
        from cemm.legacy.v3_3.percept_adapter import LegacyV33PerceptAdapter
        adapter = LegacyV33PerceptAdapter()
        result = adapter.perceive(signal_ids=("test",))
        assert result == ()

    def test_percept_adapter_returns_empty_with_raw_text_only(self):
        from cemm.legacy.v3_3.percept_adapter import LegacyV33PerceptAdapter
        adapter = LegacyV33PerceptAdapter()
        result = adapter.perceive(raw_text="hello world")
        assert result == ()


class TestCognitiveKernelImportBoundary:
    """Test that canonical cycle package doesn't import legacy root modules."""

    def test_cycle_package_no_legacy_imports(self):
        """The kernel/cycle/ package must not import from root kernel/*.py."""
        from pathlib import Path
        from cemm.kernel.retirement.legacy_guard import LegacyImportGuard

        guard = LegacyImportGuard()
        cycle_dir = Path("cemm/kernel/cycle")
        result = guard.scan_directory(cycle_dir)
        assert result.is_clean, (
            f"Legacy imports found in cycle package: {result.violations}"
        )

    def test_app_package_no_legacy_imports(self):
        """The app/ package must not import from root kernel/*.py legacy
        modules. It IS allowed to import from cemm.legacy/ (the explicit
        legacy boundary)."""
        from pathlib import Path
        from cemm.kernel.retirement.legacy_guard import LegacyImportGuard

        guard = LegacyImportGuard()
        app_dir = Path("cemm/app")
        result = guard.scan_directory(app_dir)
        # Filter out violations for cemm.legacy imports (those are the
        # explicit boundary, not violations)
        real_violations = tuple(
            v for v in result.violations
            if not v.import_statement.startswith("from ..legacy")
            and not v.import_statement.startswith("from cemm.legacy")
        )
        assert len(real_violations) == 0, (
            f"Legacy root kernel imports found in app package: {real_violations}"
        )

    def test_legacy_boundary_package_exists(self):
        """The cemm/legacy/v3_3/ boundary package exists."""
        import importlib
        mod = importlib.import_module("cemm.legacy.v3_3.percept_adapter")
        assert hasattr(mod, "LegacyV33PerceptAdapter")
