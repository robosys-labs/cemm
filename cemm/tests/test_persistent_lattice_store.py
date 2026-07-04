"""Tests for PersistentLatticeStore SQLite-backed concept persistence."""
import tempfile
import os
from cemm.memory.persistent_lattice_store import PersistentLatticeStore
from cemm.types.graph_patch import GraphPatch, PatchOperation


def _store():
    return PersistentLatticeStore(":memory:")


def test_upsert_and_get_concept():
    store = _store()
    store.upsert_concept("concept:president", {
        "key": "president",
        "atom_kind": "entity",
        "state": "candidate_atom",
        "confidence": 0.8,
    })
    got = store.get_concept("concept:president")
    assert got is not None
    assert got["key"] == "president"
    assert got["atom_kind"] == "entity"


def test_get_missing_concept():
    store = _store()
    assert store.get_concept("concept:nonexistent") is None


def test_update_existing_concept():
    store = _store()
    store.upsert_concept("concept:president", {"key": "president", "state": "candidate_atom"})
    store.upsert_concept("concept:president", {"key": "president", "state": "consolidated_atom"})
    got = store.get_concept("concept:president")
    assert got["state"] == "consolidated_atom"


def test_load_all_empty():
    store = _store()
    assert store.load_all() == {}


def test_load_all_with_data():
    store = _store()
    store.upsert_concept("c:a", {"key": "a", "atom_kind": "entity"})
    store.upsert_concept("c:b", {"key": "b", "atom_kind": "state"})
    all_concepts = store.load_all()
    assert len(all_concepts) == 2
    assert all_concepts["c:a"]["key"] == "a"


def test_persistence_across_reopens():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        store1 = PersistentLatticeStore(db_path)
        store1.upsert_concept("c:a", {"key": "a", "atom_kind": "entity", "state": "candidate"})
        store1.close()
        store2 = PersistentLatticeStore(db_path)
        got = store2.get_concept("c:a")
        assert got is not None
        assert got["key"] == "a"
        store2.close()
    finally:
        os.unlink(db_path)


def test_journal_patch_with_real_store():
    store = _store()
    patch = GraphPatch(
        id="patch_test1",
        source_graph_id="g1",
        target="concept_lattice",
        operations=[PatchOperation(operation="upsert_concept_candidate", target_id="c:a")],
    )
    store.journal_patch(patch, accepted=True)
    cursor = store._conn.execute(
        "SELECT count(*) FROM patch_journal WHERE patch_id = ?", ("patch_test1",)
    )
    count = cursor.fetchone()[0]
    assert count == 1


def test_close_reopen_journal():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        store1 = PersistentLatticeStore(db_path)
        patch = GraphPatch(id="pj_test", source_graph_id="g1", target="concept_lattice")
        store1.journal_patch(patch, accepted=True)
        store1.close()
        store2 = PersistentLatticeStore(db_path)
        cursor = store2._conn.execute(
            "SELECT count(*) FROM patch_journal WHERE patch_id = ?", ("pj_test",)
        )
        assert cursor.fetchone()[0] == 1
        store2.close()
    finally:
        os.unlink(db_path)


def test_journal_rejected_patch():
    store = _store()
    patch = GraphPatch(id="rejected1", target="concept_lattice")
    store.journal_patch(patch, accepted=False)
    cursor = store._conn.execute(
        "SELECT accepted FROM patch_journal WHERE patch_id = ?", ("rejected1",)
    )
    assert cursor.fetchone()[0] == 0
