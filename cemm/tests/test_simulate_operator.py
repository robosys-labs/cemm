from __future__ import annotations

import os
import sys
import uuid
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.simulate import SimulateOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from cemm.types.action import ActionKind


def _kernel(store: Store | None = None) -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(active_claim_ids=["c1", "c2"]),
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


@patch("cemm.operators.simulate.CausalInference")
def test_simulate_operator_action_kind(MockCausal: MagicMock) -> None:
    op = SimulateOperator()
    assert op.action_kind == ActionKind.SIMULATE


@patch("cemm.operators.simulate.CausalInference")
def test_simulate_operator_success(MockCausal: MagicMock) -> None:
    mock_instance = MockCausal.return_value
    mock_packet = MagicMock()
    mock_packet.predictions = [
        {"predicate": "likes", "object_value": "ice_cream", "confidence": 0.85},
        {"predicate": "location", "object_entity_id": "home", "confidence": 0.72},
    ]
    mock_instance.predict.return_value = mock_packet

    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=["c1"],
        params={"action_or_event": "ask_about_hobbies"},
    )
    op = SimulateOperator()
    result = op.execute(ctx)

    assert result.success
    assert "ask_about_hobbies" in result.output_text
    assert "likes" in result.output_text
    assert "ice_cream" in result.output_text
    assert "0.85" in result.output_text
    assert result.result_signal is not None
    assert result.result_signal.kind == SignalKind.SIMULATION_RESULT
    assert result.cost_ms == 2.0
    stored = store.signals.get(result.result_signal.id)
    assert stored is not None
    mock_instance.predict.assert_called_once()


@patch("cemm.operators.simulate.CausalInference")
def test_simulate_operator_falls_back_to_world_active_claims(MockCausal: MagicMock) -> None:
    mock_instance = MockCausal.return_value
    mock_packet = MagicMock()
    mock_packet.predictions = []
    mock_instance.predict.return_value = mock_packet

    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],  # empty, should fall back to kernel.world.active_claim_ids
        params={"action_or_event": "test"},
    )
    op = SimulateOperator()
    result = op.execute(ctx)

    assert result.success
    # predict should have been called with the world's active_claim_ids
    _, active_ids, _ = mock_instance.predict.call_args[0]
    assert active_ids == ["c1", "c2"]


@patch("cemm.operators.simulate.CausalInference")
def test_simulate_operator_denies_without_permission(MockCausal: MagicMock) -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    kernel.permission.may_execute = False
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={"action_or_event": "test"},
    )
    op = SimulateOperator()
    result = op.execute(ctx)

    assert not result.success
    assert "Permission denied" in result.output_text
    MockCausal.assert_not_called()
