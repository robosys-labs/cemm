from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EntityRefUOLAtom:
    kind: str = "entity_ref"
    entity_id: str = ""
    role: str = "actor"  # actor | patient | target | source | location | instrument | topic
    confidence: float = 0.5


@dataclass
class ProcessUOLAtom:
    kind: str = "process"
    frame_key: str = ""
    process_model_id: str | None = None
    participants: list[dict] = field(default_factory=list)
    input_state_keys: list[str] = field(default_factory=list)
    output_state_keys: list[str] = field(default_factory=list)
    temporal_frame_id: str | None = None
    modality: str = "observed"
    polarity: str = "affirmed"
    intensity: float = 0.5
    confidence: float = 0.5


@dataclass
class StateUOLAtom:
    kind: str = "state"
    state_key: str = ""
    state_model_id: str | None = None
    holder_entity_id: str | None = None
    dimension: str = ""
    value: float = 0.0
    polarity: str = "neutral"
    intensity: float = 0.5
    confidence: float = 0.5
