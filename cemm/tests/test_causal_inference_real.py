from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.causal.inference import CausalInference
from cemm.types.model import Model, ModelKind, ModelStatus
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.permission import Permission
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from cemm.types.self_view import SelfView


def _kernel() -> ContextKernel:
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


def test_causal_inference_finds_matching_rules() -> None:
    """CausalInference.predict() must find active CAUSAL_RULE models
    whose preconditions match the input action."""
    store = Store(":memory:")
    ci = CausalInference(store)
    kernel = _kernel()

    store.conn.execute(
        "INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_test", "concept", "test", 1.0, "sig_init", time.time(), time.time()),
    )
    claim = Claim(
        id="c1", subject_entity_id="entity_test", predicate="rain",
        object_value="true", status=ClaimStatus.ACTIVE, confidence=0.9,
        trust=0.8, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public(),
    )
    store.claims.put(claim)

    model = Model(
        id=uuid.uuid4().hex[:16],
        kind=ModelKind.CAUSAL_RULE,
        name="rain_causes_wet_ground",
        description="Rain causes wet ground",
        preconditions=["rain"],
        effects=["wet_ground"],
        confidence=0.9,
        trust=0.8,
        status=ModelStatus.ACTIVE,
        created_at=time.time(),
        updated_at=time.time(),
    )
    store.models.put(model)

    result = ci.predict("it is raining", ["c1"], kernel)
    # Should find the rain rule via predicate matching
    assert len(result.predictions) >= 1
    preds = [p["predicate"] for p in result.predictions]
    assert "wet_ground" in preds
    assert result.confidence > 0.5


def test_causal_inference_skips_non_matching_rules() -> None:
    """CausalInference.predict() must skip models whose preconditions
    don't match the input action."""
    store = Store(":memory:")
    ci = CausalInference(store)
    kernel = _kernel()

    model = Model(
        id=uuid.uuid4().hex[:16],
        kind=ModelKind.CAUSAL_RULE,
        name="sun_causes_dry",
        description="Sun causes dry ground",
        preconditions=["sun"],
        effects=["dry_ground"],
        confidence=0.9,
        trust=0.8,
        status=ModelStatus.ACTIVE,
        created_at=time.time(),
        updated_at=time.time(),
    )
    store.models.put(model)

    # "rain" doesn't match precondition "sun"
    result = ci.predict("it is raining", ["c1"], kernel)
    assert len(result.predictions) == 0
