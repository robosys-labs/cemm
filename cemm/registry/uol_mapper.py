from __future__ import annotations
from ..types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from ..types.signal import ObservationSemantics
from ..types.context_kernel import ContextKernel
from .registry import Registry

class UOLMapper:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def map_signal(self, content: str, kernel: ContextKernel) -> list:
        atoms: list = []
        content_lower = content.lower()

        if kernel.self_view.self_id and any(w in content_lower for w in ("you", "your")):
            atoms.append(EntityRefUOLAtom(
                entity_id=kernel.self_view.self_id,
                role="target",
                confidence=0.8,
            ))

        if any(w in content_lower for w in ("is", "are", "was", "were")):
            atoms.append(ProcessUOLAtom(
                frame_key="assert_evaluation",
                modality="observed",
                polarity="negated" if any(n in content_lower for n in ("not", "n't", "never")) else "affirmed",
                intensity=0.7,
                confidence=0.6,
            ))

        if any(w in content_lower for w in ("dumb", "stupid", "fool", "idiot", "useless", "broken")):
            atoms.append(StateUOLAtom(
                state_key="low_competence",
                polarity="negative",
                intensity=0.7,
                confidence=0.7,
            ))
        elif any(w in content_lower for w in ("great", "awesome", "excellent", "amazing", "helpful")):
            atoms.append(StateUOLAtom(
                state_key="high_quality",
                polarity="positive",
                intensity=0.6,
                confidence=0.7,
            ))

        return atoms

    def compile_to_pragmatic_keys(self, atoms: list) -> tuple[list[str], list[str]]:
        quality_keys = []
        process_keys = []
        for atom in atoms:
            if atom.kind == "state":
                quality_keys.append(atom.state_key)
            elif atom.kind == "process":
                process_keys.append(atom.frame_key)
        return quality_keys, process_keys
