from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .trace import Trace


class ActionKind(str, Enum):
    ANSWER = "answer"
    ASK = "ask"
    REMEMBER = "remember"
    UPDATE_CLAIM = "update_claim"
    CREATE_MODEL_CANDIDATE = "create_model_candidate"
    SYNTHESIZE = "synthesize"
    SIMULATE = "simulate"
    RETRIEVE = "retrieve"
    CALL_TOOL = "call_tool"
    REFLECT = "reflect"
    ABSTAIN = "abstain"


class ActionStatus(str, Enum):
    PLANNED = "planned"
    EXECUTED = "executed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class Action:
    id: str
    kind: ActionKind
    operator_model_id: str
    input_signal_ids: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    risk: float = 0.0
    cost_ms: float = 0.0
    status: ActionStatus = ActionStatus.PLANNED
    result_signal_id: str | None = None
    trace: Trace | None = None
    created_at: float = 0.0
    version: str = "cemm.action.v1"
