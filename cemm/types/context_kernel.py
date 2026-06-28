from __future__ import annotations
from dataclasses import dataclass, field
from .permission import Permission
from .self_state import SelfState


@dataclass
class WorldState:
    active_entity_ids: list[str] = field(default_factory=list)
    active_claim_ids: list[str] = field(default_factory=list)
    active_model_ids: list[str] = field(default_factory=list)
    causal_graph_model_ids: list[str] = field(default_factory=list)
    active_frame_model_ids: list[str] = field(default_factory=list)
    current_constraints: list[str] = field(default_factory=list)
    predicted_outcome_ids: list[str] = field(default_factory=list)


@dataclass
class UserState:
    user_id: str | None = None
    known: bool = False
    active_preference_claim_ids: list[str] = field(default_factory=list)
    trusted_domains: list[str] = field(default_factory=list)
    session_affect: PragmaticState | None = None


@dataclass
class TimeState:
    now: float = 0.0
    bucket: str = "unknown"
    recency_window_ms: float = 300000.0


@dataclass
class ConversationState:
    session_id: str = ""
    turn_index: int = 0
    recent_signal_ids: list[str] = field(default_factory=list)
    active_entity_ids: list[str] = field(default_factory=list)
    active_claim_ids: list[str] = field(default_factory=list)
    active_repetition_group_ids: list[str] = field(default_factory=list)
    repetition_counts: dict[str, int] = field(default_factory=dict)
    pragmatic_state: PragmaticState | None = None


@dataclass
class GoalState:
    active_goal: str | None = None
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)


@dataclass
class MemoryState:
    working_signal_ids: list[str] = field(default_factory=list)
    working_entity_ids: list[str] = field(default_factory=list)
    working_claim_ids: list[str] = field(default_factory=list)
    candidate_claim_ids: list[str] = field(default_factory=list)
    candidate_model_ids: list[str] = field(default_factory=list)
    registry_model_ids: list[str] = field(default_factory=list)
    active_frame_ids: list[str] = field(default_factory=list)
    disputed_claim_ids: list[str] = field(default_factory=list)
    source_trust_keys: list[str] = field(default_factory=list)


@dataclass
class Budget:
    latency_target_ms: float = 50.0
    max_entities: int = 16
    max_claims: int = 128
    max_models: int = 16
    max_ranked: int = 64
    max_actions: int = 3
    max_recursive_steps: int = 1
    allow_dense_fallback: bool = False
    allow_simulation: bool = True

    def clone(self) -> "Budget":
        return Budget(
            latency_target_ms=self.latency_target_ms,
            max_entities=self.max_entities,
            max_claims=self.max_claims,
            max_models=self.max_models,
            max_ranked=self.max_ranked,
            max_actions=self.max_actions,
            max_recursive_steps=self.max_recursive_steps,
            allow_dense_fallback=self.allow_dense_fallback,
            allow_simulation=self.allow_simulation,
        )


@dataclass
class PragmaticState:
    current_stance: str = "cooperative"
    target_entity_id: str = ""
    frustration: float = 0.0
    hostility: float = 0.0
    playfulness: float = 0.0
    repetition_pressure: float = 0.0
    likely_cause_claim_ids: list[str] = field(default_factory=list)
    last_updated_signal_id: str = ""
    last_updated_at: float = 0.0
    decay_half_life_ms: float = 900000.0


@dataclass
class ContextKernel:
    id: str
    world: WorldState = field(default_factory=WorldState)
    user: UserState = field(default_factory=UserState)
    time: TimeState = field(default_factory=TimeState)
    conversation: ConversationState = field(default_factory=ConversationState)
    goal: GoalState = field(default_factory=GoalState)
    memory: MemoryState = field(default_factory=MemoryState)
    self_state: SelfState | None = None
    permission: Permission = field(default_factory=Permission.public)
    budget: Budget = field(default_factory=Budget)
    version: str = "erca.context_kernel.v1"
