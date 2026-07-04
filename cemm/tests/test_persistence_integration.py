"""Integration test: persistent concept lattice across sessions."""
import tempfile
import os
from cemm.store.store import Store
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.persistent_lattice_store import PersistentLatticeStore
from cemm.__main__ import seed_self_state, seed_causal_models


def test_persistence_across_restarts():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        pl1 = PersistentLatticeStore(db_path)
        lattice1 = ConceptLattice(persistent_store=pl1)
        store1 = Store(db_path)
        seed_self_state(store1, concept_lattice=lattice1)
        seed_causal_models(store1, concept_lattice=lattice1)
        store1.close()
        pl1.close()

        pl2 = PersistentLatticeStore(db_path)
        lattice2 = ConceptLattice(persistent_store=pl2)
        loaded = pl2.load_all()
        assert len(loaded) > 0, "No concepts survived restart!"
        self_concept = pl2.get_concept("concept:self_main")
        assert self_concept is not None
        affordance = pl2.get_concept("affordance:causal_rain_flooding")
        assert affordance is not None
        pl2.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
