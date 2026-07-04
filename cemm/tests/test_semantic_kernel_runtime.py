"""Tests for Phase 5: SemanticKernelRuntime — the single authoritative entrypoint."""

from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
from cemm.types.runtime_cycle import RuntimeCycleResult
from cemm.types.context_kernel import ContextKernel
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission


def _signal(text: str = "hello") -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id="runtime_test",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _kernel() -> ContextKernel:
    return ContextKernel(id=uuid.uuid4().hex[:16])


def test_runtime_returns_cycle_result() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal(), _kernel())
    assert isinstance(result, RuntimeCycleResult)
    assert result.signal is not None
    assert result.context_kernel is not None


def test_runtime_perceives_signal() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello world"), _kernel())
    assert result.percept is not None
    assert result.percept.uol_graph is not None


def test_runtime_produces_working_graph() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.uol_graph is not None
    assert len(result.uol_graph.atoms) >= 1


def test_runtime_attention_controller_produces_working_set() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.working_set is not None


def test_runtime_plans_act() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.act_plan is not None


def test_runtime_extracts_patch_candidates() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.patch_candidates is not None


def test_runtime_validates_patches() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.validation is not None


def test_runtime_measures_cost() -> None:
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.cost_ms > 0.0


def test_runtime_accepts_existing_percept() -> None:
    runtime = SemanticKernelRuntime()
    signal = _signal("hello")
    kernel = _kernel()
    first = runtime.run_turn(signal, kernel)
    second = runtime.run_turn(signal, kernel, percept=first.percept)
    assert second.percept is first.percept


def test_runtime_exposes_backward_compat_attributes() -> None:
    runtime = SemanticKernelRuntime()
    assert runtime.graph_builder is not None
    assert runtime.perceptor is not None
    assert runtime.planner is not None
    assert runtime.patch_extractor is not None
    assert runtime.consolidator is not None
