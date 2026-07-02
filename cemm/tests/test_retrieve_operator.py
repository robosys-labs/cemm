from __future__ import annotations

import os
import sys
import uuid
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.entity import Entity, EntityType
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


def test_retrieve_operator_action_kind() -> None:
    op = RetrieveOperator()
    assert op.action_kind == ActionKind.RETRIEVE



def test_retrieve_operator_denies_without_execute_permission() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    kernel.permission.may_execute = False
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={},
    )
    op = RetrieveOperator()
    result = op.execute(ctx)

    assert not result.success
    assert result.result_signal is None


def test_retrieve_operator_denies_without_retrieve_permission() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    kernel.permission.may_retrieve = False
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={},
    )
    op = RetrieveOperator()
    result = op.execute(ctx)

    assert not result.success
    assert result.result_signal is None
