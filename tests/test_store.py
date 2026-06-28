import pytest
from cemm.store.store import Store
from cemm.store.schema import create_schema, get_required_indexes
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.entity import Entity, EntityType
from cemm.types.claim import Claim
from cemm.types.model import Model, ModelKind
from cemm.types.action import Action, ActionKind
from cemm.types.self_state import SelfState
from cemm.types.permission import Permission
import sqlite3


class TestStoreSchema:
    def test_create_schema_in_memory(self):
        conn = sqlite3.connect(":memory:")
        create_schema(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [r[0] for r in tables]
        assert "signals" in names
        assert "entities" in names
        assert "claims" in names
        assert "models" in names
        assert "actions" in names
        assert "self_states" in names
        assert "source_trust" in names
        assert len(names) >= 10
        conn.close()

    def test_indexes_defined(self):
        indexes = get_required_indexes()
        assert len(indexes) >= 15


class TestSignalStore:
    def test_put_and_get(self):
        store = Store(":memory:")
        s = Signal(
            id="sig_test", kind=SignalKind.INPUT,
            source_id="u1", source_type=SourceType.USER,
            content="hello", observed_at=0.0,
            context_id="ctx1", salience=0.5, trust=0.8,
            permission=Permission.public(),
        )
        store.signals.put(s)
        retrieved = store.signals.get("sig_test")
        assert retrieved is not None
        assert retrieved.content == "hello"
        assert retrieved.kind == SignalKind.INPUT

    def test_recent(self):
        store = Store(":memory:")
        s = Signal(
            id="sig_r1", kind=SignalKind.INPUT,
            source_id="u1", source_type=SourceType.USER,
            content="test", observed_at=0.0,
            context_id="ctx1", salience=0.5, trust=0.8,
            permission=Permission.public(),
        )
        store.signals.put(s)
        recent = store.signals.recent(10)
        assert len(recent) >= 1


class TestEntityStore:
    def test_put_and_get(self):
        store = Store(":memory:")
        e = Entity(
            id="ent_test", type=EntityType.PERSON, name="Alice",
            aliases=["alice"], confidence=0.9,
            created_from_signal_id="s1", created_at=0.0, updated_at=0.0,
        )
        store.entities.put(e)
        retrieved = store.entities.get("ent_test")
        assert retrieved is not None
        assert retrieved.name == "Alice"
        assert "alice" in retrieved.aliases

    def test_find_by_name(self):
        store = Store(":memory:")
        e = Entity(
            id="ent_find", type=EntityType.PERSON, name="Bob",
            aliases=["bobby"], confidence=0.9,
            created_from_signal_id="s1", created_at=0.0, updated_at=0.0,
        )
        store.entities.put(e)
        found = store.entities.find_by_name("Bob")
        assert len(found) == 1


class TestClaimStore:
    def _seed_entity(self, store):
        from cemm.types.entity import Entity, EntityType
        e = Entity(
            id="ent_1", type=EntityType.PERSON, name="Test",
            aliases=[], confidence=0.9,
            created_from_signal_id="sig_seed", created_at=0.0, updated_at=0.0,
        )
        store.entities.put(e)
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.permission import Permission
        s = Signal(
            id="sig_seed", kind=SignalKind.INPUT,
            source_id="user", source_type=SourceType.USER,
            content="seed", observed_at=0.0,
            context_id="ctx", salience=0.5, trust=0.8,
            permission=Permission.public(),
        )
        store.signals.put(s)
        return store

    def test_put_and_get(self):
        store = self._seed_entity(Store(":memory:"))
        c = Claim(
            id="cl_test", subject_entity_id="ent_1", predicate="likes",
            object_value="cats", evidence_signal_ids=["sig_seed"],
            source_id="user", domain="preference",
        )
        store.claims.put(c)
        retrieved = store.claims.get("cl_test")
        assert retrieved is not None
        assert retrieved.predicate == "likes"

    def test_find_by_subject(self):
        store = self._seed_entity(Store(":memory:"))
        c = Claim(
            id="cl_subj", subject_entity_id="ent_1", predicate="test",
            evidence_signal_ids=["sig_seed"],
            source_id="s", domain="d",
        )
        store.claims.put(c)
        found = store.claims.find_by_subject("ent_1")
        assert len(found) == 1

    def test_claim_object_value_type_preserved(self):
        import time
        store = self._seed_entity(Store(":memory:"))
        c_bool = Claim(
            id="cl_type_bool", subject_entity_id="ent_1", predicate="is_active",
            object_value=True, evidence_signal_ids=["sig_seed"],
            source_id="t", domain="test",
        )
        store.claims.put(c_bool)
        loaded = store.claims.get("cl_type_bool")
        assert loaded is not None
        assert loaded.object_value is True

        c_int = Claim(
            id="cl_type_int", subject_entity_id="ent_1", predicate="count",
            object_value=42, evidence_signal_ids=["sig_seed"],
            source_id="t", domain="test",
        )
        store.claims.put(c_int)
        loaded = store.claims.get("cl_type_int")
        assert loaded is not None
        assert loaded.object_value == 42

        c_str = Claim(
            id="cl_type_str", subject_entity_id="ent_1", predicate="name",
            object_value="hello", evidence_signal_ids=["sig_seed"],
            source_id="t", domain="test",
        )
        store.claims.put(c_str)
        loaded = store.claims.get("cl_type_str")
        assert loaded is not None
        assert loaded.object_value == "hello"


class TestModelStore:
    def test_put_and_get(self):
        store = Store(":memory:")
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.permission import Permission
        s = Signal(
            id="sig_mod", kind=SignalKind.INPUT,
            source_id="user", source_type=SourceType.USER,
            content="seed", observed_at=0.0,
            context_id="ctx", salience=0.5, trust=0.8,
            permission=Permission.public(),
        )
        store.signals.put(s)
        m = Model(
            id="mod_test", kind=ModelKind.PREDICATE, name="test_model",
            description="desc", evidence_signal_ids=["sig_mod"],
        )
        store.models.put(m)
        retrieved = store.models.get("mod_test")
        assert retrieved is not None
        assert retrieved.name == "test_model"


class TestActionStore:
    def test_put_and_get(self):
        store = Store(":memory:")
        a = Action(id="act_test", kind=ActionKind.ANSWER, operator_model_id="op1")
        store.actions.put(a)
        retrieved = store.actions.get("act_test")
        assert retrieved is not None
        assert retrieved.kind == ActionKind.ANSWER


class TestSelfStore:
    def test_put_and_get(self):
        store = Store(":memory:")
        s = SelfState(id="self_store_test")
        store.self_store.put(s)
        retrieved = store.self_store.get("self_store_test")
        assert retrieved is not None

    def test_latest(self):
        store = Store(":memory:")
        s1 = SelfState(id="self1")
        store.self_store.put(s1)
        s2 = SelfState(id="self2")
        s2.created_at = 100.0
        s2.updated_at = 200.0
        store.self_store.put(s2)
        latest = store.self_store.latest()
        assert latest is not None
        assert latest.id == "self2"


class TestSourceTrustStore:
    def test_record_outcome(self):
        store = Store(":memory:")
        entry = store.source_trust.record_outcome("src1", "qa", success=True)
        assert entry.evidence_count == 1
        assert entry.success_count == 1
        assert entry.trust > 0.5

    def test_get_returns_none_for_missing(self):
        store = Store(":memory:")
        entry = store.source_trust.get("unknown", "domain")
        assert entry is None
