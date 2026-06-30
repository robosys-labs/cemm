from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.remember import RememberOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)


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


def test_remember_operator_stores_claim() -> None:
    """RememberOperator must store a claim and return its ID."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="remember this",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )

    store.signals.put(signal)

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        params={
            "subject_entity_id": "entity_user",
            "predicate": "favorite_database",
            "object_value": "Postgres",
            "domain": "personal",
        },
    )
    op = RememberOperator()
    result = op.execute(ctx)

    assert result.success
    assert len(result.new_claim_ids) == 1
    cid = result.new_claim_ids[0]

    stored = store.claims.get(cid)
    assert stored is not None
    assert stored.subject_entity_id == "entity_user"
    assert stored.predicate == "favorite_database"
    assert stored.object_value == "Postgres"
