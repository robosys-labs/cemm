from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.types.context_kernel import ContextKernel
from cemm.types.semantic_answer_graph import SemanticAnswerGraph
from cemm.types.permission import Permission
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.self_view import SelfView
from cemm.synthesis.realizer import RealizationPipeline


def _make_kernel(store: Store) -> ContextKernel:
    import time
    from cemm.types.context_kernel import (
        ContextKernel, WorldState, UserState, TimeState,
        ConversationState, GoalState, MemoryState, Budget,
    )
    kernel = ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(
            session_id=uuid.uuid4().hex[:16], turn_index=1,
        ),
        goal=GoalState(),
        memory=MemoryState(),
        permission=Permission.public(),
        budget=Budget(),
        self_view=SelfView(self_id="test"),
    )
    return kernel


def _store_claim(store: Store, text: str) -> str:
    import time
    entity_id = "entity_user"
    store.conn.execute(
        """INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (entity_id, "user", "user", 1.0, "sig_init", time.time(), time.time()),
    )
    cid = uuid.uuid4().hex[:16]
    claim = Claim(
        id=cid,
        subject_entity_id=entity_id,
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
    return cid


def test_claim_text_map_includes_actual_text() -> None:
    """RealizationPipeline must look up claim objects from store
    to build claim_text_map, not rely on kernel.claims (which doesn't exist)
    or use raw IDs as text."""
    store = Store(":memory:")
    kernel = _make_kernel(store)

    claim_text = "Postgres is my favorite database"
    cid = _store_claim(store, claim_text)

    sag = SemanticAnswerGraph(
        id=uuid.uuid4().hex[:16],
        intent="answer",
        source_signal_ids=["sig1"],
        context_id=kernel.id,
        selected_claim_ids=[cid],
        selected_model_ids=[],
    )

    pipeline = RealizationPipeline()
    from cemm.registry import Registry
    result = pipeline.run(sag, kernel, store, Registry())

    detail = result.metadata.get("verification", {})
    coverage = detail.get("claim_coverage", 0.0)
    assert coverage > 0.0, (
        f"claim_coverage=0.0 means claim_text_map was empty. "
        "RealizationPipeline likely fell back to raw IDs instead of looking up claims from store. "
        f"Details: {detail}"
    )
