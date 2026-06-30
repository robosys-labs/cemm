from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.answer import AnswerOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)


def _store_claim(store: Store, text: str, cid: str | None = None) -> str:
    store.conn.execute(
        "INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_user", "user", "user", 1.0, "sig_init", time.time(), time.time()),
    )
    claim_id = cid or uuid.uuid4().hex[:16]
    claim = Claim(
        id=claim_id,
        subject_entity_id="entity_user",
        predicate="test_predicate",
        object_value=text,
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


def test_answer_operator_creates_semantic_answer_graph() -> None:
    """AnswerOperator must produce a SemanticAnswerGraph before text."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)
    cid = _store_claim(store, "Postgres is the best database")

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        selected_claim_ids=[cid],
        selected_model_ids=[],
        params={"intent": "answer"},
    )
    op = AnswerOperator()
    result = op.execute(ctx)

    assert result.success
    assert result.semantic_answer_graph is not None
    assert result.semantic_answer_graph.intent == "answer"
    assert cid in result.semantic_answer_graph.selected_claim_ids
    assert result.output_text
    assert result.trace is not None
    assert result.trace.semantic_answer_graph_id == result.semantic_answer_graph.id


def test_answer_operator_rejects_without_claims() -> None:
    """AnswerOperator must reject when no claims are selected (no evidence to synthesize from)."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        selected_claim_ids=[],
        selected_model_ids=[],
        params={"intent": "answer"},
    )
    op = AnswerOperator()
    result = op.execute(ctx)

    assert not result.success
    assert "No evidence" in result.output_text
