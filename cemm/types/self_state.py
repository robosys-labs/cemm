from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class InternalMode(str, Enum):
    ASSISTANT = "assistant"
    RESEARCHER = "researcher"
    PLANNER = "planner"
    EXECUTOR = "executor"
    TEACHER = "teacher"
    REFLECTOR = "reflector"


@dataclass
class SelfMetacognition:
    known_limits: list[str] = field(default_factory=list)
    active_assumptions: list[str] = field(default_factory=list)
    reliability_by_domain: dict[str, float] = field(default_factory=dict)
    preferred_strategies: list[str] = field(default_factory=list)


@dataclass
class SelfEpistemic:
    open_contradiction_claim_ids: list[str] = field(default_factory=list)
    low_confidence_domain_keys: list[str] = field(default_factory=list)
    calibration_error_by_domain: dict[str, float] = field(default_factory=dict)
    coverage_gap_claim_ids: list[str] = field(default_factory=list)


@dataclass
class SelfMetaMemory:
    recently_written_claim_ids: list[str] = field(default_factory=list)
    recently_superseded_claim_ids: list[str] = field(default_factory=list)
    frequently_used_model_ids: list[str] = field(default_factory=list)
    failed_retrieval_patterns: list[str] = field(default_factory=list)


@dataclass
class SelfState:
    id: str
    name: str = "cemm"
    identity_claim_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0
    milestone_signal_ids: list[str] = field(default_factory=list)
    active_project_ids: list[str] = field(default_factory=list)
    learned_model_ids: list[str] = field(default_factory=list)
    mode: InternalMode = InternalMode.ASSISTANT
    load: float = 0.0
    uncertainty: float = 0.0
    coherence: float = 1.0
    recent_error_rate: float = 0.0
    current_budget_pressure: float = 0.0
    metacognition: SelfMetacognition = field(default_factory=SelfMetacognition)
    epistemic: SelfEpistemic = field(default_factory=SelfEpistemic)
    meta_memory: SelfMetaMemory = field(default_factory=SelfMetaMemory)
    current_context_id: str | None = None
    last_reflection_signal_id: str | None = None
    updated_at: float = 0.0
    version: str = "cemm.self.v1"
