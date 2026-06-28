from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .permission import Permission


class ModelKind(str, Enum):
    SCHEMA = "schema"
    PREDICATE = "predicate"
    ENTITY_TYPE = "entity_type"
    OPERATOR = "operator"
    CAUSAL_RULE = "causal_rule"
    PROCESS = "process"
    SIMULATOR = "simulator"
    RANKING_RULE = "ranking_rule"
    FRAME_RULE = "frame_rule"
    CONTEXT_RULE = "context_rule"
    SYNTHESIS_STRATEGY = "synthesis_strategy"
    VERIFIER = "verifier"
    INDUCTOR = "inductor"
    UOL_SEMANTIC = "uol_semantic"


class ModelStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


@dataclass
class Model:
    id: str
    kind: ModelKind
    name: str
    description: str
    input_types: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    evidence_signal_ids: list[str] = field(default_factory=list)
    related_entity_ids: list[str] = field(default_factory=list)
    related_claim_ids: list[str] = field(default_factory=list)
    registry_key: str | None = None
    confidence: float = 0.5
    trust: float = 0.5
    utility: float = 0.0
    cost_estimate_ms: float = 0.0
    risk: float = 0.0
    status: ModelStatus = ModelStatus.CANDIDATE
    created_at: float = 0.0
    updated_at: float = 0.0
    permission: Permission | None = None
    version: str = "erca.model.v1"
