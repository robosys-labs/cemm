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


def test_runtime_exposes_core_components() -> None:
    runtime = SemanticKernelRuntime()
    assert runtime.graph_builder is not None
    assert runtime.perceptor is not None
    assert runtime.planner is not None
    assert runtime.patch_extractor is not None
    assert runtime.consolidator is not None
    assert runtime.program_compiler is not None
    assert runtime.obligation_scheduler is not None
    assert runtime.teaching_frame_manager is not None
    assert runtime.relation_frame_compiler is not None
    assert runtime.relation_algebra is not None
    assert runtime.predicate_schema_store is not None
    assert runtime.query_engine is not None
    assert runtime.realizer is not None


def test_run_semantic_stack_returns_cycle_result() -> None:
    runtime = SemanticKernelRuntime()
    sig = _signal("hello world")
    kernel = _kernel()
    full = runtime.run_turn(sig, kernel)
    result = runtime.run_semantic_stack(
        sig, kernel,
        uol_graph=full.uol_graph,
        percept=full.percept,
        working_set=full.working_set,
    )
    assert isinstance(result, RuntimeCycleResult)
    assert result.uol_graph is full.uol_graph
    assert result.percept is full.percept
    assert result.working_set is full.working_set


def test_run_semantic_stack_populates_v42_fields() -> None:
    runtime = SemanticKernelRuntime()
    sig = _signal("what is a dog?")
    kernel = _kernel()
    full = runtime.run_turn(sig, kernel)
    result = runtime.run_semantic_stack(
        sig, kernel,
        uol_graph=full.uol_graph,
        percept=full.percept,
        working_set=full.working_set,
    )
    assert result.semantic_program is not None
    assert result.obligation_frame is not None
    assert isinstance(result.relation_frames, list)


def test_run_semantic_stack_no_double_perception() -> None:
    runtime = SemanticKernelRuntime()
    sig = _signal("hello")
    kernel = _kernel()
    full = runtime.run_turn(sig, kernel)
    percept = full.percept
    result = runtime.run_semantic_stack(
        sig, kernel,
        uol_graph=full.uol_graph,
        percept=percept,
        working_set=full.working_set,
    )
    assert result.percept is percept
    assert result.consolidation == []
    assert result.patch_candidates == []


def test_run_semantic_stack_attends_when_no_working_set() -> None:
    runtime = SemanticKernelRuntime()
    sig = _signal("hello world")
    kernel = _kernel()
    full = runtime.run_turn(sig, kernel)
    result = runtime.run_semantic_stack(
        sig, kernel,
        uol_graph=full.uol_graph,
        percept=full.percept,
    )
    assert result.working_set is not None


def test_run_semantic_stack_produces_realized_output() -> None:
    runtime = SemanticKernelRuntime()
    sig = _signal("what is a dog?")
    kernel = _kernel()
    full = runtime.run_turn(sig, kernel)
    result = runtime.run_semantic_stack(
        sig, kernel,
        uol_graph=full.uol_graph,
        percept=full.percept,
        working_set=full.working_set,
    )
    if result.realization_contract is not None:
        assert isinstance(result.realized_output, str)
        assert len(result.realized_output) > 0
