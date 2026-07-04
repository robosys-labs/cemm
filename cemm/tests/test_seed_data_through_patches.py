"""Tests that seed data flows through GraphPatches into the concept lattice."""
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.persistent_lattice_store import PersistentLatticeStore


def test_seed_self_state_creates_concepts():
    pl_store = PersistentLatticeStore(":memory:")
    lattice = ConceptLattice(persistent_store=pl_store)
    from cemm.__main__ import seed_self_state
    from cemm.store.store import Store
    store = Store(":memory:")
    seed_self_state(store, concept_lattice=lattice)
    concept = pl_store.get_concept("concept:self_main")
    assert concept is not None


def test_seed_causal_models_creates_concepts():
    pl_store = PersistentLatticeStore(":memory:")
    lattice = ConceptLattice(persistent_store=pl_store)
    from cemm.__main__ import seed_causal_models
    from cemm.store.store import Store
    store = Store(":memory:")
    seed_causal_models(store, concept_lattice=lattice)
    concept = pl_store.get_concept("affordance:causal_rain_flooding")
    assert concept is not None
