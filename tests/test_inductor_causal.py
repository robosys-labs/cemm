from __future__ import annotations
from cemm.store.store import Store
from cemm.learning.inductor import Inductor
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.entity import Entity, EntityType
from cemm.types.permission import Permission
from cemm.types.model import ModelKind, ModelStatus
import time, uuid

ALICE_ENTITY_ID = "alice"


def _seed_alice(store: Store) -> str:
    sid = uuid.uuid4().hex[:16]
    sig = Signal(
        id=sid, kind=SignalKind.SYSTEM,
        source_id="test", source_type=SourceType.SYSTEM,
        content="seed alice", observed_at=time.time(),
        context_id="test", salience=0.0, trust=1.0,
        permission=Permission.public(),
    )
    store.signals.put(sig)
    ent = Entity(
        id=ALICE_ENTITY_ID, type=EntityType.PERSON, name="Alice",
        aliases=["alice"], confidence=1.0,
        created_from_signal_id=sid, created_at=time.time(), updated_at=time.time(),
    )
    store.entities.put(ent)
    return ALICE_ENTITY_ID


def _make_claim(store: Store, predicate: str, obj_id: str, outcome: str, domain: str = "causal") -> Claim:
    now = time.time()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="test",
        source_type=SourceType.USER,
        content=f"test {predicate}",
        observed_at=now,
        context_id="test",
        salience=0.5,
        trust=0.5,
        permission=Permission.public(),
    )
    store.signals.put(signal)
    claim = Claim(
        id=uuid.uuid4().hex[:16],
        subject_entity_id=ALICE_ENTITY_ID,
        predicate=predicate,
        object_entity_id=obj_id,
        object_value=obj_id,
        qualifiers={"outcome": outcome},
        evidence_signal_ids=[signal.id],
        source_id="test",
        domain=domain,
        confidence=0.7,
        trust=0.7,
        salience=0.3,
        status=ClaimStatus.ACTIVE,
        observed_at=now,
        updated_at=now,
        permission=Permission.public(),
    )
    store.claims.put(claim)
    return claim


class TestCausalPatternInduction:
    def test_detects_repeated_consistent_pattern(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 1
        model = candidates[0]
        assert model.kind == ModelKind.CAUSAL_RULE
        assert model.name == "query"
        assert "object:postgres" in model.preconditions
        assert "outcome:success" in model.effects

    def test_skips_below_threshold(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=5)
        for _ in range(3):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_skips_inconsistent_pattern(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(3):
            _make_claim(store, "query", "postgres", "success")
        _make_claim(store, "query", "postgres", "failure")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_skips_without_outcome_qualifier(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        sig_id = uuid.uuid4().hex[:16]
        sig = Signal(
            id=sig_id, kind=SignalKind.SYSTEM,
            source_id="test", source_type=SourceType.SYSTEM,
            content="seed", observed_at=now,
            context_id="test", salience=0.0, trust=1.0,
            permission=Permission.public(),
        )
        store.signals.put(sig)
        for _ in range(5):
            claim = Claim(
                id=uuid.uuid4().hex[:16],
                subject_entity_id=ALICE_ENTITY_ID,
                predicate="query",
                object_entity_id="postgres",
                object_value="postgres",
                evidence_signal_ids=[sig_id],
                source_id="test",
                domain="causal",
                confidence=0.7,
                trust=0.7,
                salience=0.3,
                status=ClaimStatus.ACTIVE,
                observed_at=now,
                updated_at=now,
                permission=Permission.public(),
            )
            store.claims.put(claim)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_respects_domain_filter(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success", domain="other")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0
        candidates_all = inductor._find_causal_patterns(domain=None)
        assert len(candidates_all) == 1

    def test_skips_already_active_rule(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=3)
        from cemm.types.model import Model
        existing = Model(
            id="existing_causal",
            kind=ModelKind.CAUSAL_RULE,
            name="query",
            description="Existing",
            preconditions=["object:postgres"],
            effects=["outcome:success"],
            confidence=0.9,
            trust=0.7,
            status=ModelStatus.ACTIVE,
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.models.put(existing)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_wired_into_maybe_induct(self):
        store = Store(":memory:")
        _seed_alice(store)
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor.maybe_induct(domain="causal")
        causal_candidates = [m for m in candidates if m.kind == ModelKind.CAUSAL_RULE]
        assert len(causal_candidates) == 1
