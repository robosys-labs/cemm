from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.reflect import ReflectOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.self_state import SelfState, SelfEpistemic
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from cemm.types.action import ActionKind


def _kernel(store: Store | None = None) -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id=uuid.uuid4().hex[:16], turn_index=1),
        goal=GoalState(),
        memory=MemoryState(),
        permission=Permission.public(),
        budget=Budget(),
        self_view=SelfView(self_id="test"),
    )


def _signal(kernel: ContextKernel, text: str = "hello") -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )


def test_reflect_operator_action_kind() -> None:
    op = ReflectOperator()
    assert op.action_kind == ActionKind.REFLECT


def test_reflect_operator_no_issues() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    ss = SelfState(id="self_test", uncertainty=0.1, recent_error_rate=0.0,
                   epistemic=SelfEpistemic(), updated_at=time.time(), created_at=time.time())
    store.self_store.put(ss)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
    )
    op = ReflectOperator()
    result = op.execute(ctx)

    assert result.success
    assert result.output_text == "No issues detected"
    assert result.result_signal is not None
    assert result.result_signal.kind == SignalKind.REFLECTION


def test_reflect_operator_high_uncertainty() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    ss = SelfState(id="self_test", uncertainty=0.85, recent_error_rate=0.0,
                   epistemic=SelfEpistemic(), updated_at=time.time(), created_at=time.time())
    store.self_store.put(ss)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
    )
    op = ReflectOperator()
    result = op.execute(ctx)

    assert result.success
    assert "High uncertainty" in result.output_text


def test_reflect_operator_elevated_error_rate() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    ss = SelfState(id="self_test", uncertainty=0.1, recent_error_rate=0.5,
                   epistemic=SelfEpistemic(), updated_at=time.time(), created_at=time.time())
    store.self_store.put(ss)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
    )
    op = ReflectOperator()
    result = op.execute(ctx)

    assert result.success
    assert "Elevated error rate" in result.output_text


def test_reflect_operator_open_contradictions() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    ss = SelfState(id="self_test", uncertainty=0.1, recent_error_rate=0.0,
                   epistemic=SelfEpistemic(open_contradiction_claim_ids=["c1", "c2"]),
                   updated_at=time.time(), created_at=time.time())
    store.self_store.put(ss)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
    )
    op = ReflectOperator()
    result = op.execute(ctx)

    assert result.success
    assert "Open contradictions: 2" in result.output_text


def test_reflect_operator_no_self_state() -> None:
    """When no self state exists, should report no issues."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
    )
    op = ReflectOperator()
    result = op.execute(ctx)

    assert result.success
    assert result.output_text == "No issues detected"


def test_reflect_operator_denies_without_permission() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    kernel.permission.may_execute = False
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
    )
    op = ReflectOperator()
    result = op.execute(ctx)

    assert not result.success
    assert "Permission denied" in result.output_text
