from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .permission import Permission
from .uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom


class SignalKind(str, Enum):
    INPUT = "input"
    TOOL_RESULT = "tool_result"
    ENVIRONMENT = "environment"
    FEEDBACK = "feedback"
    TRACE = "trace"
    ACTION_RESULT = "action_result"
    MEMORY_UPDATE = "memory_update"
    SIMULATION_RESULT = "simulation_result"
    REFLECTION = "reflection"
    SYSTEM = "system"


class SourceType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"
    WEB = "web"
    FILE = "file"
    SENSOR = "sensor"
    SIMULATOR = "simulator"


@dataclass
class ObservationSemantics:
    speech_act: str = "unknown"
    target_entity_id: str = ""
    semantic_cluster_key: str = ""
    stance: str = "unknown"
    affect: dict[str, float] = field(default_factory=lambda: {
        "valence": 0.0, "arousal": 0.0, "frustration": 0.0,
        "hostility": 0.0, "playfulness": 0.0,
    })
    repetition_group_id: str = ""
    repetition_count: int = 0
    cause_hypothesis_claim_ids: list[str] = field(default_factory=list)
    decay_half_life_ms: float = 900000.0
    confidence: float = 0.0
    uol_atoms: list = field(default_factory=list)  # list of EntityRefUOLAtom | ProcessUOLAtom | StateUOLAtom


@dataclass
class Signal:
    id: str
    kind: SignalKind
    source_id: str
    source_type: SourceType
    content: str
    observed_at: float
    context_id: str
    salience: float
    trust: float
    permission: Permission
    parent_signal_id: str | None = None
    version: str = "erca.signal.v1"
    observation_semantics: ObservationSemantics | None = None
