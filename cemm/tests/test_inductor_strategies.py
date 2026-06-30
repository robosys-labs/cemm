from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.learning.inductor import Inductor
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.permission import Permission


def _store_claim(store: Store, predicate: str, domain: str = "test") -> str:
    store.conn.execute(
        "INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_test", "concept", "test", 1.0, "sig_init", time.time(), time.time()),
    )
    cid = uuid.uuid4().hex[:16]
    claim = Claim(
        id=cid,
        subject_entity_id="entity_test",
        predicate=predicate,
        object_value="true",
        domain=domain,
        status=ClaimStatus.ACTIVE,
        confidence=0.7,
        trust=0.6,
        observed_at=time.time(),
        updated_at=time.time(),
        permission=Permission.public(),
    )
    store.claims.put(claim)
    return cid


def test_find_repeated_predicates_creates_model() -> None:
    """When a predicate appears >= threshold times, Inductor should
    produce a candidate model via _find_repeated_predicates."""
    store = Store(":memory:")
    inductor = Inductor(store, feedback_threshold=3)
    # Insert 3 claims with the same predicate
    for _ in range(3):
        _store_claim(store, "favorite_database")
    result = inductor._find_repeated_predicates()
    assert len(result) >= 1
    names = [m.name for m in result]
    assert "favorite_database" in names


def test_find_repeated_predicates_below_threshold() -> None:
    """Below threshold, no model should be created."""
    store = Store(":memory:")
    inductor = Inductor(store, feedback_threshold=5)
    for _ in range(2):
        _store_claim(store, "rare_predicate")
    result = inductor._find_repeated_predicates()
    assert len(result) == 0


def test_find_failed_retrieval_no_data() -> None:
    """With no failed retrieval data, no candidates."""
    store = Store(":memory:")
    inductor = Inductor(store)
    result = inductor._find_failed_retrieval_patterns()
    assert result == []
