"""Physical retrieval bounds and exact keyed query evidence."""
import pytest

__cemm_test_inventory__ = {
    "tests/test_foundation_query_retrieval.py::test_predicate_argument_index_tracks_replacement[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-predicate-argument-index-tracks-replacement-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "6b8f8fa144756897a054cf89d21824371f4a20dd0b899611426ff210be5ae9f3"
    },
    "tests/test_foundation_query_retrieval.py::test_predicate_argument_index_tracks_replacement[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-predicate-argument-index-tracks-replacement-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "6b8f8fa144756897a054cf89d21824371f4a20dd0b899611426ff210be5ae9f3"
    },
    "tests/test_foundation_query_retrieval.py::test_indexed_read_preserves_duplicate_constraints_and_sentinel[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-indexed-read-preserves-duplicate-constraints-and-sentinel-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32c75c4ceafe4566cae5a9e375fd85df93994c9f026fac95fc8eaf1756e32ed8"
    },
    "tests/test_foundation_query_retrieval.py::test_indexed_read_preserves_duplicate_constraints_and_sentinel[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-indexed-read-preserves-duplicate-constraints-and-sentinel-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32c75c4ceafe4566cae5a9e375fd85df93994c9f026fac95fc8eaf1756e32ed8"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[memory-subject-10]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-memory-subject-10",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[memory-subject-2000]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-memory-subject-2000",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[memory-object-10]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-memory-object-10",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[memory-object-2000]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-memory-object-2000",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[sqlite-subject-10]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-sqlite-subject-10",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[sqlite-subject-2000]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-sqlite-subject-2000",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[sqlite-object-10]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-sqlite-object-10",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_decoding_and_sqlite_work_are_bounded[sqlite-object-2000]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-decoding-and-sqlite-work-are-bounded-sqlite-object-2000",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2991d7742bebc8a4965ae6919abfceecbcfec0bbb95035804b897fb837d479b1"
    },
    "tests/test_foundation_query_retrieval.py::test_query_indexes_persist_across_sqlite_restart": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-indexes-persist-across-sqlite-restart",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9f6cec168bcce39f2a2595b5dc857d570f68927991aa68d1221a634051d63da4"
    },
    "tests/test_foundation_query_retrieval.py::test_query_index_damage_fails_activation[index-rows]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-index-damage-fails-activation-index-rows",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "63cf72153bd202d98e67ccc1e72940fd3fc934b84d391b8c5e60ffa8fbaf88cc"
    },
    "tests/test_foundation_query_retrieval.py::test_query_index_damage_fails_activation[trigger]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-index-damage-fails-activation-trigger",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "63cf72153bd202d98e67ccc1e72940fd3fc934b84d391b8c5e60ffa8fbaf88cc"
    },
    "tests/test_foundation_query_retrieval.py::test_query_index_damage_fails_activation[table]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-index-damage-fails-activation-table",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "63cf72153bd202d98e67ccc1e72940fd3fc934b84d391b8c5e60ffa8fbaf88cc"
    },
    "tests/test_foundation_query_retrieval.py::test_query_index_damage_fails_activation[marker]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-index-damage-fails-activation-marker",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "63cf72153bd202d98e67ccc1e72940fd3fc934b84d391b8c5e60ffa8fbaf88cc"
    },
    "tests/test_foundation_query_retrieval.py::test_query_physical_index_migrates_old_database_once": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-query-physical-index-migrates-old-database-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "44ae226ce8dc7edefe2e5b4e8242f88e6493dd48fbfb0f13c0459741928a5489"
    }
}
import sqlite3

import cemm_authoritative_hybrid.persistence as persistence
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from tests.test_foundation_query_integrity import stores, fact, query


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_predicate_argument_index_tracks_replacement(stores):
    stores.world.commit((fact("fact:one"),), expected_revision=0)
    read = getattr(stores, "r3_query_facts", None)
    assert callable(read), "QUERY needs a bounded indexed predicate/argument port"
    args = (("role:subject", "entity:alice"),)
    assert len(read("op:relation", "rel:likes", args, maximum=256)) == 1
    stores.world.commit((fact("fact:one", predicate="rel:changed"),), expected_revision=1)
    assert read("op:relation", "rel:likes", args, maximum=256) == ()
    assert len(read("op:relation", "rel:changed", args, maximum=256)) == 1


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_indexed_read_preserves_duplicate_constraints_and_sentinel(stores):
    stores.world.commit(tuple(fact(f"fact:{i}") for i in range(3)), expected_revision=0)
    read = getattr(stores, "r3_query_facts", None)
    assert callable(read), "QUERY needs a bounded indexed predicate/argument port"
    assert len(read("op:relation", "rel:likes", (), maximum=2)) == 3
    assert read("op:relation", "rel:likes", (("role:subject", "entity:alice"),
        ("role:subject", "entity:bob")), maximum=2) == ()


@pytest.mark.parametrize(("stores", "different_role", "irrelevant_count"), (
    ("memory", "subject", 10), ("memory", "subject", 2000),
    ("memory", "object", 10), ("memory", "object", 2000),
    ("sqlite", "subject", 10), ("sqlite", "subject", 2000),
    ("sqlite", "object", 10), ("sqlite", "object", 2000)),
    indirect=("stores",), ids=("memory-subject-10", "memory-subject-2000",
        "memory-object-10", "memory-object-2000", "sqlite-subject-10",
        "sqlite-subject-2000", "sqlite-object-10", "sqlite-object-2000"))
def test_query_decoding_and_sqlite_work_are_bounded(stores, monkeypatch, irrelevant_count, different_role):
    kwargs = lambda i: {"subject" if different_role == "subject" else "object_ref": f"entity:other{i}"}
    stores.world.commit(tuple(fact(f"fact:a{i:06}", **kwargs(i)) for i in range(irrelevant_count))
        + (fact("fact:z"),), expected_revision=0)
    decoded = []
    real = persistence._row_to_fact
    def count(row):
        decoded.append(1)
        return real(row)
    monkeypatch.setattr(persistence, "_row_to_fact", count)
    conn = getattr(stores._backend, "_conn", None)
    steps = []
    if conn is not None:
        conn.set_progress_handler(lambda: steps.append(1) or 0, 1)
    try:
        assert query(stores).query_results[0].status is QueryStatus.SUPPORTED
    finally:
        if conn is not None:
            conn.set_progress_handler(None, 0)
    assert len(decoded) <= 2
    assert len(steps) < 15000


def test_query_indexes_persist_across_sqlite_restart(tmp_path):
    path = tmp_path / "restart.sqlite"
    stores = persistence.open_stores(path, authority_generation="authority:test", model_identity="model:test")
    stores.world.commit(tuple(fact(f"fact:a{i}", subject=f"entity:other{i}") for i in range(300))
        + (fact("fact:z"),), expected_revision=0)
    stores.close()
    reopened = persistence.open_stores(path, authority_generation="authority:test", model_identity="model:test")
    try:
        assert query(reopened).query_results[0].status is QueryStatus.SUPPORTED
    finally:
        reopened.close()


@pytest.mark.parametrize("damage", ("index_rows", "trigger", "table", "marker"),
                         ids=("index-rows", "trigger", "table", "marker"))
def test_query_index_damage_fails_activation(tmp_path, damage):
    path = tmp_path / "corrupt.sqlite"
    store = persistence.open_stores(path, authority_generation="authority:test", model_identity="model:test")
    store.world.commit((fact("fact:one"),), expected_revision=0)
    database = store.learning_store_binding
    store.close()
    with sqlite3.connect(database) as conn:
        conn.execute({"index_rows": "DELETE FROM world_query_keys", "trigger": "DROP TRIGGER world_query_update",
            "table": "DROP TABLE world_query_keys", "marker": "UPDATE metadata SET value='invalid' WHERE key='query_index_v1'"}[damage])
    with pytest.raises(persistence.StoreActivationError):
        persistence.open_stores(path, authority_generation="authority:test", model_identity="model:test")


def test_query_physical_index_migrates_old_database_once(tmp_path):
    path = tmp_path / "old.sqlite"
    store = persistence.open_stores(path, authority_generation="authority:test", model_identity="model:test")
    store.world.commit((fact("fact:one"),), expected_revision=0)
    pin = store.revision_pin()
    database = store.learning_store_binding
    store.close()
    with sqlite3.connect(database) as conn:
        for name in ("insert", "update", "delete"):
            conn.execute(f"DROP TRIGGER world_query_{name}")
        conn.execute("DROP TABLE world_query_keys")
        conn.execute("DELETE FROM metadata WHERE key='query_index_v1'")
    migrated = persistence.open_stores(path, authority_generation="authority:test", model_identity="model:test")
    try:
        assert migrated.revision_pin() == pin
        assert query(migrated).query_results[0].status is QueryStatus.SUPPORTED
    finally:
        migrated.close()
