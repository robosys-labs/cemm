from cemm.types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from cemm.types.signal import ObservationSemantics

def test_entity_ref_creation():
    atom = EntityRefUOLAtom(entity_id="self_1", role="target", confidence=0.9)
    assert atom.kind == "entity_ref"
    assert atom.entity_id == "self_1"

def test_process_atom_creation():
    atom = ProcessUOLAtom(frame_key="assert_evaluation", modality="observed", polarity="negated")
    assert atom.kind == "process"
    assert atom.modality == "observed"

def test_state_atom_creation():
    atom = StateUOLAtom(state_key="low_competence", holder_entity_id="self_1", polarity="negative")
    assert atom.kind == "state"
    assert atom.polarity == "negative"

def test_semantics_accepts_uol_atoms():
    sem = ObservationSemantics(
        speech_act="insult",
        uol_atoms=[
            EntityRefUOLAtom(entity_id="self_1", role="target"),
            StateUOLAtom(state_key="low_competence", holder_entity_id="self_1", polarity="negative"),
        ],
    )
    assert len(sem.uol_atoms) == 2

def test_uol_mapper():
    from cemm.registry.uol_mapper import UOLMapper
    from cemm.registry import Registry
    from cemm.types.context_kernel import ContextKernel, SelfState
    mapper = UOLMapper(Registry())
    kernel = ContextKernel(id="test_uol")
    kernel.self_state = SelfState(id="self_main", name="cemm")
    atoms = mapper.map_signal("you are dumb", kernel)
    entity_refs = [a for a in atoms if a.kind == "entity_ref"]
    states = [a for a in atoms if a.kind == "state"]
    assert any(a.role == "target" for a in entity_refs)
    assert any(a.state_key == "low_competence" for a in states)
