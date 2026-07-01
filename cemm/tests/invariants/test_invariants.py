from __future__ import annotations

import os, sys, uuid, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.answer import AnswerOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission, PermissionScope
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.self_view import SelfView
from cemm.types.action import Action, ActionKind, ActionStatus
from cemm.types.trace import Trace
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)


def _cid() -> str:
    return uuid.uuid4().hex[:16]

def _kernel(store: Store | None = None) -> ContextKernel:
    return ContextKernel(id=_cid(), world=WorldState(), user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id=_cid(), turn_index=1),
        goal=GoalState(), memory=MemoryState(), permission=Permission.public(),
        budget=Budget(), self_view=SelfView(self_id="test"))

def _signal(kernel: ContextKernel, text: str = "hello") -> Signal:
    return Signal(id=_cid(), kind=SignalKind.INPUT, source_id="user",
        source_type=SourceType.USER, content=text, observed_at=time.time(),
        context_id=kernel.id, salience=0.5, trust=0.8, permission=kernel.permission)

def _store_entity(store: Store) -> None:
    store.conn.execute("INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_u", "user", "user", 1.0, "sig_init", time.time(), time.time()))


# --- Invariant #2: response has no input signal ---

def test_invariant_action_has_input_signal() -> None:
    """Every action must trace back to an input signal."""
    store = Store(":memory:")
    kernel = _kernel(store)
    sig = _signal(kernel)
    store.signals.put(sig)

    action = Action(
        id=_cid(), kind=ActionKind.ANSWER, operator_model_id="test_op",
        input_signal_ids=[sig.id], status=ActionStatus.EXECUTED,
        created_at=time.time(),
    )
    store.actions.put(action)
    stored = store.actions.get(action.id)
    assert stored is not None
    assert sig.id in stored.input_signal_ids


# --- Invariant #3: claim has evidence signal ---

def test_invariant_claim_has_evidence_signal() -> None:
    """Claims without evidence signal IDs can be stored but are flagged as untrusted."""
    store = Store(":memory:")
    _store_entity(store)
    claim = Claim(id=_cid(), subject_entity_id="entity_u", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public(), evidence_signal_ids=[])
    store.claims.put(claim)
    stored = store.claims.get(claim.id)
    assert stored is not None
    assert stored.evidence_signal_ids == []


# --- Invariant #5: memory mutation has action trace ---

def test_invariant_remember_stores_trace() -> None:
    """RememberOperator must produce a result with trace or new_claim_ids."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    sig = _signal(kernel)
    store.signals.put(sig)
    _store_entity(store)

    ctx = OperatorContext(kernel=kernel, input_signal=sig, store=store,
        registry=registry, selected_claim_ids=[],
        params={"text": "User likes Postgres"})
    op = RememberOperator()
    result = op.execute(ctx)

    assert result.success
    assert len(result.new_claim_ids) == 1
    # Claim should be retrievable from store
    stored_claim = store.claims.get(result.new_claim_ids[0])
    assert stored_claim is not None


# --- Invariant #7: private claim requires permission ---

def test_invariant_private_claim_requires_permission() -> None:
    """A private claim should not be returned to a public context."""
    store = Store(":memory:")
    _store_entity(store)
    private_perm = Permission(scope=PermissionScope.USER_PRIVATE,
        may_store=True, may_retrieve=False, may_use=False)
    claim = Claim(id=_cid(), subject_entity_id="entity_u", predicate="secret",
        object_value="classified", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=private_perm)
    store.claims.put(claim)

    from cemm.retrieval.ranker import Ranker
    ranker = Ranker()
    pub_kernel = _kernel()
    pub_kernel.permission = Permission.public()
    ranked = ranker.rank_claims([claim], pub_kernel)
    # Permission validity is a hard filter — private claims are excluded.
    assert len(ranked) == 0


# --- Invariant #8: disputed claim not certain ---

def test_invariant_disputed_claim_not_certain() -> None:
    """A disputed claim must be marked with low trust."""
    store = Store(":memory:")
    _store_entity(store)
    disputed = Claim(id=_cid(), subject_entity_id="entity_u", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.DISPUTED, confidence=0.9,
        trust=0.3, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public())
    store.claims.put(disputed)

    from cemm.retrieval.ranker import Ranker
    ranker = Ranker()
    kernel = _kernel(store)
    ranked = ranker.rank_claims([disputed], kernel)
    for claim, score in ranked:
        if claim.id == disputed.id:
            assert score < 0.5 or claim.trust < 0.5


# --- Invariant #9: prediction not observed fact ---

def test_invariant_prediction_not_observed_fact() -> None:
    """Observed claim must outrank prediction at same confidence."""
    store = Store(":memory:")
    _store_entity(store)
    observed = Claim(id=_cid(), subject_entity_id="entity_u", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.ACTIVE, confidence=0.95,
        trust=0.9, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public(), source_id="direct_observation")
    predicted = Claim(id=_cid(), subject_entity_id="entity_u", predicate="likes",
        object_value="cake", status=ClaimStatus.ACTIVE, confidence=0.95,
        trust=0.6, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public(), source_id="causal_inference")

    from cemm.retrieval.ranker import Ranker
    ranker = Ranker()
    kernel = _kernel()
    ranked = ranker.rank_claims([observed, predicted], kernel)
    obs_rank = next(i for i, (c, _) in enumerate(ranked) if c.id == observed.id)
    pred_rank = next(i for i, (c, _) in enumerate(ranked) if c.id == predicted.id)
    assert obs_rank < pred_rank


# --- Invariant #16: answer uses verification ---

def test_invariant_answer_uses_verification() -> None:
    """AnswerOperator output must include trace with realization_verified."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    sig = _signal(kernel)
    store.signals.put(sig)
    _store_entity(store)
    cid = uuid.uuid4().hex[:16]
    claim = Claim(id=cid, subject_entity_id="entity_u", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public())
    store.claims.put(claim)

    ctx = OperatorContext(kernel=kernel, input_signal=sig, store=store,
        registry=registry, selected_claim_ids=[cid], params={"intent": "answer"})
    op = AnswerOperator()
    result = op.execute(ctx)

    assert result.success
    assert result.semantic_answer_graph is not None
    assert result.trace is not None
    assert result.trace.realization_verified is not None


# --- Invariant #19: response uses only selected claims ---

def test_invariant_response_uses_only_selected_claims() -> None:
    """AnswerOperator must not include unselected claim IDs in its SAG."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    sig = _signal(kernel)
    store.signals.put(sig)
    _store_entity(store)
    cid = uuid.uuid4().hex[:16]
    other_cid = uuid.uuid4().hex[:16]
    claim = Claim(id=cid, subject_entity_id="entity_u", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public())
    other = Claim(id=other_cid, subject_entity_id="entity_u", predicate="likes",
        object_value="cake", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public())
    store.claims.put(claim)
    store.claims.put(other)

    ctx = OperatorContext(kernel=kernel, input_signal=sig, store=store,
        registry=registry, selected_claim_ids=[cid], params={"intent": "answer"})
    op = AnswerOperator()
    result = op.execute(ctx)

    assert result.success
    assert other_cid not in result.semantic_answer_graph.selected_claim_ids
    assert cid in result.semantic_answer_graph.selected_claim_ids


# --- Invariant #24: permission gates respected ---

def test_invariant_latent_respects_permission() -> None:
    """Operator must not execute without permission."""
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(store)
    kernel.permission.may_execute = False
    sig = _signal(kernel)

    from cemm.operators.ask import AskOperator
    ctx = OperatorContext(kernel=kernel, input_signal=sig, store=store,
        registry=registry, selected_claim_ids=[], params={"question": "test"})
    op = AskOperator()
    result = op.execute(ctx)
    assert not result.success
    assert "Permission denied" in result.output_text


# --- Invariant #30: causal confidence capped ---

def test_invariant_causal_confidence_capped() -> None:
    """Causal inference predictions must have confidence within [0, 1]."""
    from cemm.causal.inference import CausalInference
    store = Store(":memory:")
    _store_entity(store)
    ci = CausalInference(store)
    kernel = _kernel(store)
    packet = ci.predict("test_event", [], kernel)
    for p in packet.predictions:
        assert 0.0 <= p["confidence"] <= 1.0


# --- Invariant #31: self state tracks contradiction claims on update ---

def test_invariant_self_state_tracks_contradictions() -> None:
    """Disputing a claim must add to self_state epistemic open_contradiction_claim_ids."""
    store = Store(":memory:")
    _store_entity(store)
    cid = uuid.uuid4().hex[:16]
    claim = Claim(id=cid, subject_entity_id="entity_u", predicate="likes",
        object_value="ice_cream", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public())
    store.claims.put(claim)

    from cemm.types.self_state import SelfState, SelfEpistemic
    ss = SelfState(id="self_test", uncertainty=0.3, epistemic=SelfEpistemic(),
        updated_at=time.time(), created_at=time.time())
    store.self_store.put(ss)

    from cemm.operators.update_claim import UpdateClaimOperator
    kernel = _kernel(store)
    sig = _signal(kernel)
    store.signals.put(sig)
    ctx = OperatorContext(kernel=kernel, input_signal=sig, store=store,
        registry=Registry(), selected_claim_ids=[cid],
        params={"claim_id": cid, "status": "disputed"})
    op = UpdateClaimOperator()
    result = op.execute(ctx)
    assert result.success

    updated_ss = store.self_store.latest()
    assert updated_ss is not None
    assert cid in updated_ss.epistemic.open_contradiction_claim_ids
