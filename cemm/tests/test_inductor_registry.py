from __future__ import annotations

import time
import uuid

from cemm.learning.inductor import Inductor
from cemm.registry import Registry
from cemm.store.store import Store
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.permission import Permission


def _store_claim(store: Store, predicate: str, domain: str = "test") -> str:
    store.conn.execute(
        "INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_test", "concept", "test", 1.0, "sig_init", time.time(), time.time()),
    )
    claim_id = uuid.uuid4().hex[:16]
    claim = Claim(
        id=claim_id,
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
    return claim_id


def test_induced_uol_semantic_is_registered_in_registry():
    store = Store(":memory:")
    registry = Registry()
    inductor = Inductor(store, feedback_threshold=3, registry=registry)
    for _ in range(3):
        _store_claim(store, "enjoys")
    inductor._find_uol_patterns()
    entry = registry.get_uol_semantic("enjoys")
    assert entry is not None
    assert entry.kind == "uol_semantic"
    assert "enjoys" in entry.aliases


def test_inductor_without_registry_keeps_backward_compatibility():
    store = Store(":memory:")
    inductor = Inductor(store, feedback_threshold=3)
    for _ in range(3):
        _store_claim(store, "likes")
    result = inductor._find_uol_patterns()
    assert len(result) >= 1
