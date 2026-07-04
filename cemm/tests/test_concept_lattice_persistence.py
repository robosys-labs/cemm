"""Tests for ConceptLattice persistent backing via PersistentLatticeStore."""
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.persistent_lattice_store import PersistentLatticeStore
from cemm.types.graph_patch import GraphPatch, PatchOperation


def _store():
    return PersistentLatticeStore(":memory:")


def test_apply_patch_writes_to_store():
    store = _store()
    lattice = ConceptLattice(persistent_store=store)
    patch = GraphPatch(
        target="concept_lattice",
        operations=[PatchOperation(
            operation="upsert_concept_candidate",
            target_id="concept:test",
            fields={"key": "test", "atom_kind": "entity", "state": "candidate_atom"},
            confidence=0.8,
        )],
        confidence=0.8,
        reason="test",
    )
    lattice.apply_patch(patch)
    # Patch is applied in-memory; flush to persist
    lattice.flush_to_store()
    got = store.get_concept("concept:test")
    assert got is not None
    assert got["key"] == "test"


def test_load_from_store_restores_state():
    store = _store()
    store.upsert_concept("concept:existing", {
        "key": "existing",
        "atom_kind": "entity",
        "state": "consolidated_atom",
        "confidence": 0.9,
    })
    lattice = ConceptLattice(persistent_store=store)
    record = lattice.lookup("existing")
    assert record is not None


def test_apply_patch_updates_existing_store_row():
    store = _store()
    store.upsert_concept("concept:x", {"key": "x", "atom_kind": "entity", "state": "candidate_atom"})
    lattice = ConceptLattice(persistent_store=store)
    patch = GraphPatch(
        target="concept_lattice",
        operations=[PatchOperation(
            operation="upsert_concept_candidate",
            target_id="concept:x",
            fields={"state": "consolidated_atom"},
        )],
        confidence=0.9,
    )
    lattice.apply_patch(patch)
    lattice.flush_to_store()
    got = store.get_concept("concept:x")
    assert got["state"] == "consolidated_atom"


def test_no_persistent_store_works_as_before():
    lattice = ConceptLattice()
    patch = GraphPatch(
        target="concept_lattice",
        operations=[PatchOperation(
            operation="upsert_concept_candidate",
            target_id="concept:test",
            fields={"key": "test", "atom_kind": "entity"},
        )],
        confidence=0.8,
    )
    lattice.apply_patch(patch)
