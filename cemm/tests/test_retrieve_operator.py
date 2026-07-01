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


@patch("cemm.operators.retrieve_op.StructuralRetriever")
@patch("cemm.operators.retrieve_op.Ranker")
def test_retrieve_operator_success(MockRanker: MagicMock, MockRetriever: MagicMock) -> None:
    mock_retriever_instance = MockRetriever.return_value
    mock_result = MagicMock()
    mock_retriever_instance.retrieve.return_value = mock_result

    claim = Claim(
        id="c1", subject_entity_id="entity_user", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.ACTIVE,
        confidence=0.9, trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public(),
    )
    mock_result.claims = [claim]

    mock_ranker_instance = MockRanker.return_value
    mock_ranker_instance.rank_claims.return_value = [(claim, 0.95)]

    store = Store(":memory:")
    registry = Registry()
    store.entities.put(Entity(
        id="entity_user", type=EntityType.PERSON, name="entity_user", aliases=[],
        confidence=0.9, created_from_signal_id="sig0", created_at=time.time(), updated_at=time.time(),
    ))
    store.claims.put(claim)
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={"subject_entity_id": "entity_user", "predicate": "likes"},
    )
    op = RetrieveOperator()
    result = op.execute(ctx)

    assert result.success
    assert "likes" in result.output_text
    assert "ice_cream" in result.output_text
    mock_retriever_instance.retrieve.assert_called_once()
    mock_ranker_instance.rank_claims.assert_called_once()


@patch("cemm.operators.retrieve_op.StructuralRetriever")
@patch("cemm.operators.retrieve_op.Ranker")
def test_retrieve_operator_default_limit(MockRanker: MagicMock, MockRetriever: MagicMock) -> None:
    mock_retriever_instance = MockRetriever.return_value
    mock_result = MagicMock()
    mock_retriever_instance.retrieve.return_value = mock_result
    mock_result.claims = []

    mock_ranker_instance = MockRanker.return_value
    mock_ranker_instance.rank_claims.return_value = []

    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    signal = _signal(kernel)

    ctx = OperatorContext(
        kernel=kernel, input_signal=signal, store=store, registry=registry,
        selected_claim_ids=[],
        params={},
    )
    op = RetrieveOperator()
    result = op.execute(ctx)

    assert result.success
    assert "did not find" in result.output_text.lower()
    # Default limit should be 64
    assert mock_retriever_instance.retrieve.call_args[0][0].limit == 64


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
    assert "Permission denied" in result.output_text


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
    assert "retrieval not allowed" in result.output_text
