from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .permission import Permission


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
