from __future__ import annotations
import time
import uuid
from collections import defaultdict
from cemm.store.store import Store
from cemm.learning.inductor import Inductor
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.entity import Entity, EntityType
from cemm.types.permission import Permission
from cemm.types.model import ModelKind, ModelStatus


ALICE_ID = "alice"
BOB_ID = "bob"


def _seed(store: Store, actor_id: str, actor_name: str) -> str:
    sid = uuid.uuid4().hex[:16]
    sig = Signal(
        id=sid, kind=SignalKind.SYSTEM,
        source_id="test", source_type=SourceType.SYSTEM,
        content=f"seed {actor_name}", observed_at=time.time(),
        context_id="test", salience=0.0, trust=1.0,
        permission=Permission.public(),
    )
    store.signals.put(sig)
    ent = Entity(
        id=actor_id, type=EntityType.PERSON, name=actor_name,
        aliases=[actor_name.lower()], confidence=1.0,
        created_from_signal_id=sid, created_at=time.time(),
        updated_at=time.time(),
    )
    store.entities.put(ent)
    return actor_id


def _make_claim(
    store: Store, subj_id: str, predicate: str, obj_id: str,
    outcome: str, domain: str = "causal", trust: float = 0.7,
    observed_at: float | None = None,
) -> Claim:
    now = observed_at or time.time()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="test",
        source_type=SourceType.USER,
        content=f"test {predicate}",
        observed_at=now,
        context_id="test",
        salience=0.5,
        trust=trust,
        permission=Permission.public(),
    )
    store.signals.put(signal)
    claim = Claim(
        id=uuid.uuid4().hex[:16],
        subject_entity_id=subj_id,
        predicate=predicate,
        object_entity_id=obj_id,
        object_value=obj_id,
        qualifiers={"outcome": outcome},
        evidence_signal_ids=[signal.id],
        source_id="test",
        domain=domain,
        confidence=0.7,
        trust=trust,
        salience=0.3,
        status=ClaimStatus.ACTIVE,
        observed_at=now,
        updated_at=now,
        permission=Permission.public(),
    )
    store.claims.put(claim)
    return claim


class TestCausalExpansion_TimeDecay:
    def test_old_claims_count_less(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        old = now - 60 * 24 * 3600
        for _ in range(4):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=old)
        _make_claim(store, ALICE_ID, "query", "postgres", "failure", observed_at=now)
        weighted, total_weight, total_trust, _, _ = inductor._weighted_outcomes(
            store.claims.find_active(200), now,
        )
        assert total_weight < 5.0
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_recent_claims_pass_threshold(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for i in range(7):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now - i * 60)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 1
        assert candidates[0].name == "query"
        assert "object:postgres" in candidates[0].preconditions

    def test_mixed_ages_still_detects_strong_pattern(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(3):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now - 30 * 24 * 3600)
        for _ in range(7):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
        weighted, total_weight, _, _, _ = inductor._weighted_outcomes(
            store.claims.find_active(200), now,
        )
        assert total_weight >= 5.0
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) >= 1


class TestCausalExpansion_NegativeBoost:
    def test_failure_gets_extra_weight(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(4):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
        _make_claim(store, ALICE_ID, "query", "postgres", "failure", observed_at=now)
        weighted, total_weight, _, _, _ = inductor._weighted_outcomes(
            store.claims.find_active(200), now,
        )
        assert weighted.get("failure", 0) == 2.0
        assert total_weight == 6.0
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_negative_boost_preserves_borderline(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(9):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
        _make_claim(store, ALICE_ID, "query", "postgres", "failure", observed_at=now)
        weighted, total_weight, _, _, _ = inductor._weighted_outcomes(
            store.claims.find_active(200), now,
        )
        consistency = weighted["success"] / total_weight
        assert consistency >= 0.8
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 1

    def test_all_failures_boosted_correctly(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "delete", "k8s", "failure", observed_at=now)
        weighted, total_weight, _, _, _ = inductor._weighted_outcomes(
            store.claims.find_active(200), now,
        )
        assert weighted.get("failure", 0) == 10.0
        assert total_weight == 10.0
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 1
        assert "outcome:failure" in candidates[0].effects


class TestCausalExpansion_ActorSpecific:
    def test_actor_specific_rule_when_general_inconsistent(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        _seed(store, BOB_ID, "Bob")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
            _make_claim(store, BOB_ID, "query", "postgres", "failure", observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 2
        alice_rules = [c for c in candidates if "actor:alice" in c.preconditions]
        bob_rules = [c for c in candidates if "actor:bob" in c.preconditions]
        assert len(alice_rules) == 1
        assert len(bob_rules) == 1
        assert "outcome:success" in alice_rules[0].effects
        assert "outcome:failure" in bob_rules[0].effects

    def test_general_rule_when_all_actors_agree(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        _seed(store, BOB_ID, "Bob")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
            _make_claim(store, BOB_ID, "query", "postgres", "success", observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 1
        assert "object:postgres" in candidates[0].preconditions
        has_actor = any(p.startswith("actor:") for p in candidates[0].preconditions)
        assert not has_actor

    def test_actor_only_for_actor_driven_pattern(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        _seed(store, BOB_ID, "Bob")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
            _make_claim(store, BOB_ID, "delete", "k8s", "failure", observed_at=now)
            _make_claim(store, BOB_ID, "query", "postgres", "failure", observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 3
        delete_rule = [c for c in candidates if c.name == "delete"]
        query_actor = [c for c in candidates if c.name == "query"]
        assert len(delete_rule) == 1
        assert len(query_actor) == 2
        has_actor = any(p.startswith("actor:") for p in delete_rule[0].preconditions)
        assert not has_actor
        for qr in query_actor:
            assert any(p.startswith("actor:") for p in qr.preconditions)

    def test_actor_specific_respects_existing_rule(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        _seed(store, BOB_ID, "Bob")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        from cemm.types.model import Model
        existing = Model(
            id="existing", kind=ModelKind.CAUSAL_RULE, name="query",
            description="Existing", preconditions=["object:postgres"],
            effects=["outcome:success"], confidence=0.9, trust=0.7,
            status=ModelStatus.ACTIVE, created_at=now, updated_at=now,
        )
        store.models.put(existing)
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success", observed_at=now)
            _make_claim(store, BOB_ID, "query", "postgres", "failure", observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0


class TestCausalExpansion_ConfidenceTrust:
    def test_higher_trust_gives_higher_confidence(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success",
                        trust=0.9, observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        high_trust_conf = candidates[0].confidence

        store2 = Store(":memory:")
        _seed(store2, ALICE_ID, "Alice")
        inductor2 = Inductor(store2, feedback_threshold=5)
        for _ in range(5):
            _make_claim(store2, ALICE_ID, "query", "postgres", "success",
                        trust=0.3, observed_at=now)
        candidates2 = inductor2._find_causal_patterns(domain="causal")
        low_trust_conf = candidates2[0].confidence

        assert high_trust_conf > low_trust_conf

    def test_confidence_within_bounds(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success",
                        trust=0.7, observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert 0.0 <= candidates[0].confidence <= 1.0

    def test_more_claims_increase_confidence(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(5):
            _make_claim(store, ALICE_ID, "query", "postgres", "success",
                        trust=0.7, observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        conf5 = candidates[0].confidence

        store2 = Store(":memory:")
        _seed(store2, ALICE_ID, "Alice")
        inductor2 = Inductor(store2, feedback_threshold=5)
        for _ in range(20):
            _make_claim(store2, ALICE_ID, "query", "postgres", "success",
                        trust=0.7, observed_at=now)
        candidates2 = inductor2._find_causal_patterns(domain="causal")
        conf20 = candidates2[0].confidence

        assert conf20 >= conf5

    def test_candidate_trust_matches_mean_trust(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        trusts = [0.5, 0.6, 0.7, 0.8, 0.9]
        for t in trusts:
            _make_claim(store, ALICE_ID, "query", "postgres", "success",
                        trust=t, observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        mean_trust = sum(trusts) / len(trusts)
        assert abs(candidates[0].trust - mean_trust) < 0.01

    def test_low_trust_still_promotable(self):
        store = Store(":memory:")
        _seed(store, ALICE_ID, "Alice")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for _ in range(10):
            _make_claim(store, ALICE_ID, "query", "postgres", "success",
                        trust=0.5, observed_at=now)
        candidates = inductor._find_causal_patterns(domain="causal")
        from cemm.learning.promotion import ModelPromoter
        promoter = ModelPromoter(store)
        ok, _ = promoter.can_promote(candidates[0])
        assert ok
