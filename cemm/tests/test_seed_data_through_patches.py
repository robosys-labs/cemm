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


def test_seed_causal_models_registers_models():
    """seed_causal_models writes models to the model store, not concept lattice atoms."""
    from cemm.__main__ import seed_causal_models
    from cemm.store.store import Store
    from cemm.types.model import ModelKind, ModelStatus
    store = Store(":memory:")
    seed_causal_models(store)
    models = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    model_keys = {m.id for m in models}
    assert "causal_rain_flooding" in model_keys
