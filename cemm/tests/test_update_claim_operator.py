from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.update_claim import UpdateClaimOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from cemm.types.action import ActionKind


def _store_claim(store: Store, cid: str | None = None) -> str:
    store.conn.execute(
        "INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_user", "user", "user", 1.0, "sig_init", time.time(), time.time()),
    )
    claim_id = cid or uuid.uuid4().hex[:16]
    claim = Claim(
        id=claim_id,
        subject_entity_id="entity_user",
        predicate="test_predicate",
        object_value="test_value",
        status=ClaimStatus.ACTIVE,
        confidence=0.9,
        trust=0.8,
        observed_at=time.time(),
        updated_at=time.time(),
        permission=Permission.public(),
    )
    store.claims.put(claim)
    return claim_id


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


def test_update_claim_operator_action_kind() -> None:
    op = UpdateClaimOperator()
    assert op.action_kind == ActionKind.UPDATE_CLAIM


def test_update_claim_operator_supersedes() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    cid = _store_claim(store)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[cid],
        params={"claim_id": cid, "status": "superseded"},
    )
    op = UpdateClaimOperator()
    result = op.execute(ctx)

    assert result.success
    assert "superseded" in result.output_text
    updated = store.claims.get(cid)
    assert updated is not None
    assert updated.status == ClaimStatus.SUPERSEDED


def test_update_claim_operator_disputes_adds_to_contradictions() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    cid = _store_claim(store)
    # Create a self state to test contradiction tracking
    from cemm.types.self_state import SelfState, SelfEpistemic
    self_state = SelfState(
        id="self_test",
        uncertainty=0.3,
        epistemic=SelfEpistemic(),
        updated_at=time.time(),
        created_at=time.time(),
    )
    store.self_store.put(self_state)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[cid],
        params={"claim_id": cid, "status": "disputed"},
    )
    op = UpdateClaimOperator()
    result = op.execute(ctx)

    assert result.success
    assert "disputed" in result.output_text
    updated = store.claims.get(cid)
    assert updated is not None
    assert updated.status == ClaimStatus.DISPUTED
    # Contradiction should be tracked in self state
    ss = store.self_store.latest()
    assert ss is not None
    assert cid in ss.epistemic.open_contradiction_claim_ids


def test_update_claim_operator_retracted_adds_to_contradictions() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    cid = _store_claim(store)
    from cemm.types.self_state import SelfState, SelfEpistemic
    self_state = SelfState(
        id="self_test",
        uncertainty=0.3,
        epistemic=SelfEpistemic(),
        updated_at=time.time(),
        created_at=time.time(),
    )
    store.self_store.put(self_state)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[cid],
        params={"claim_id": cid, "status": "retracted"},
    )
    op = UpdateClaimOperator()
    result = op.execute(ctx)

    assert result.success
    updated = store.claims.get(cid)
    assert updated is not None
    assert updated.status == ClaimStatus.RETRACTED
    ss = store.self_store.latest()
    assert ss is not None
    assert cid in ss.epistemic.open_contradiction_claim_ids


def test_update_claim_operator_not_found() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={"claim_id": "nonexistent", "status": "superseded"},
    )
    op = UpdateClaimOperator()
    result = op.execute(ctx)

    assert not result.success
    assert "not found" in result.output_text


def test_update_claim_operator_denies_without_permission() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    kernel.permission.may_execute = False
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={"claim_id": "test", "status": "superseded"},
    )
    op = UpdateClaimOperator()
    result = op.execute(ctx)

    assert not result.success
    assert "Permission denied" in result.output_text
