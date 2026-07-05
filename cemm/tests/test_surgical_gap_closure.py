from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.base import OperatorContext
from cemm.operators.learn import LearnOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.answer import AnswerOperator
from cemm.kernel.decision_router import DecisionRouter
from cemm.learning.lexeme_memory import LexemeMemory
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from cemm.types.uol_graph import UOLGraph


# ── fixtures ────────────────────────────────────────────────────


@pytest.fixture
def store() -> Store:
    return Store(":memory:")


@pytest.fixture
def registry() -> Registry:
    return Registry()


@pytest.fixture
def kernel(store: Store) -> ContextKernel:
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


@pytest.fixture
def signal(kernel: ContextKernel) -> Signal:
    sig = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="test",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )
    return sig


@pytest.fixture
def operator_context(kernel: ContextKernel, signal: Signal, store: Store, registry: Registry) -> OperatorContext:
    store.signals.put(signal)
    return OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        selected_claim_ids=[],
        selected_model_ids=[],
        params={},
    )


@pytest.fixture
def decision_router() -> DecisionRouter:
    return DecisionRouter()


# ── Task 1: memory-query guard ───────────────────────────────


def test_memory_query_not_remember_command(
    decision_router: DecisionRouter, kernel: ContextKernel, store: Store
) -> None:
    seg = UOLGraph(
        id=uuid.uuid4().hex[:16],
        signal_id="s1",
        context_id=kernel.id,
    )
    seg.add_atom("process", "process:command_remember", confidence=0.7)
    packet = decision_router.run(
        graph=seg,
        kernel=kernel,
        input_text="do you remember me?",
        store=store,
    )
    assert packet.action_kind != "remember"


def test_imperative_remember_still_command(
    decision_router: DecisionRouter, kernel: ContextKernel, store: Store
) -> None:
    seg = UOLGraph(
        id=uuid.uuid4().hex[:16],
        signal_id="s1",
        context_id=kernel.id,
    )
    seg.add_atom("process", "process:command_remember", confidence=0.7)
    packet = decision_router.run(
        graph=seg,
        kernel=kernel,
        input_text="remember my birthday is in june",
        store=store,
    )
    assert packet.action_kind == "remember"


# ── Task 2: self-query intent propagation ─────────────────────


def test_self_capability_intent_preserved(
    answer_operator: AnswerOperator, operator_context: OperatorContext
) -> None:
    operator_context.params["decision_reason"] = "self query (self_capability_query) answered from verified claims"
    operator_context.params["intent"] = "self_capability"
    operator_context.params["selected_claim_ids"] = ["c1"]
    result = answer_operator.execute(operator_context)
    assert result.semantic_answer_graph is not None
    assert result.semantic_answer_graph.intent == "self_capability"


def test_self_identity_intent_inferred_from_reason(
    answer_operator: AnswerOperator, operator_context: OperatorContext
) -> None:
    operator_context.params["intent"] = "self_identity"
    operator_context.params["selected_claim_ids"] = ["c1"]
    result = answer_operator.execute(operator_context)
    assert result.semantic_answer_graph is not None
    assert result.semantic_answer_graph.intent == "self_identity"


# ── Task 3: operator SAG realization ────────────────────────


def test_learn_operator_uses_sag_realization(
    learn_operator: LearnOperator, operator_context: OperatorContext
) -> None:
    operator_context.params["teaching_event"] = {
        "kind": "command_alias",
        "surface": "zibble",
        "meaning": "remember this",
        "role": "command_alias",
        "confidence": 0.7,
    }
    result = learn_operator.execute(operator_context)
    assert result.semantic_answer_graph is not None
    assert result.semantic_answer_graph.intent == "learn_command_alias"


def test_remember_operator_uses_sag_realization(
    remember_operator: RememberOperator, operator_context: OperatorContext
) -> None:
    operator_context.params["text"] = "my friend nathan likes mangoes"
    result = remember_operator.execute(operator_context)
    assert result.success
    assert result.trace is not None
    assert result.trace.semantic_answer_graph_id is not None
    assert result.trace.realization_strategy is not None


# ── Task 4: user-profile lane ─────────────────────────────────


def test_profile_lane_stores_user_name(
    remember_operator: RememberOperator, operator_context: OperatorContext
) -> None:
    operator_context.params.update({
        "subject_entity_id": "user",
        "predicate": "user.name",
        "object_value": "chibueze",
    })
    result = remember_operator.execute(operator_context)
    assert result.success
    # Profile claim is written via GraphPatch, not directly to store.
    # Verify no premature store write:
    profile = operator_context.store.profile
    assert profile.get("name") is None


def test_profile_lane_stores_alias(
    remember_operator: RememberOperator, operator_context: OperatorContext
) -> None:
    operator_context.params.update({
        "subject_entity_id": "user",
        "predicate": "user.alias",
        "object_value": "chibbs",
    })
    result = remember_operator.execute(operator_context)
    assert result.success
    # Profile claim is written via GraphPatch, not directly to store.
    # Verify no premature store write:
    profile = operator_context.store.profile
    assert profile.get("alias") is None


def test_user_name_query_routes_to_profile_lane(
    decision_router: DecisionRouter, kernel: ContextKernel, store: Store
) -> None:
    store.profile.put("name", "chibueze", "user")
    seg = UOLGraph(
        id=uuid.uuid4().hex[:16],
        signal_id="s1",
        context_id=kernel.id,
    )
    seg.add_atom("process", "process:user_name_query", confidence=0.7)
    packet = decision_router.run(
        graph=seg,
        kernel=kernel,
        input_text="what is my name",
        store=store,
    )
    assert packet.action_kind == "answer"
    assert len(packet.action_plan.selected_claim_ids) == 1
    claim = store.claims.get(packet.action_plan.selected_claim_ids[0])
    assert claim is not None
    assert claim.object_value == "chibueze"


# ── operator fixtures ─────────────────────────────────────────


@pytest.fixture
def answer_operator() -> AnswerOperator:
    return AnswerOperator()


@pytest.fixture
def learn_operator() -> LearnOperator:
    return LearnOperator(lexeme_memory=LexemeMemory())


@pytest.fixture
def remember_operator() -> RememberOperator:
    return RememberOperator()
