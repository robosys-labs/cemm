from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .permission import Permission
from .self_view import SelfView


@dataclass
class UserAffectState:
    current_stance: str = "cooperative"
    frustration: float = 0.0
    hostility: float = 0.0
    playfulness: float = 0.0
    active_quality_atom_keys: list[str] = field(default_factory=list)
    last_updated_signal_id: str = ""
    last_updated_at: float = 0.0
    decay_half_life_ms: float = 900000.0


@dataclass
class ConversationDynamics:
    repetition_pressure: float = 0.0
    active_repetition_group_ids: list[str] = field(default_factory=list)
    active_process_atom_keys: list[str] = field(default_factory=list)
    likely_cause_claim_ids: list[str] = field(default_factory=list)
    last_updated_signal_id: str = ""
    last_updated_at: float = 0.0
    decay_half_life_ms: float = 300000.0


@dataclass
class WorldState:
    active_entity_ids: list[str] = field(default_factory=list)
    active_claim_ids: list[str] = field(default_factory=list)
    active_model_ids: list[str] = field(default_factory=list)
    causal_graph_model_ids: list[str] = field(default_factory=list)
    active_frame_model_ids: list[str] = field(default_factory=list)
    current_constraints: list[str] = field(default_factory=list)
    predicted_outcome_ids: list[str] = field(default_factory=list)
    assistant_locale: dict | None = None
    world_event_claim_ids: list[str] = field(default_factory=list)
    active_context_rule_model_ids: list[str] = field(default_factory=list)
    persistence: bool = True


@dataclass
class UserState:
    user_id: str | None = None
    known: bool = False
    active_preference_claim_ids: list[str] = field(default_factory=list)
    trusted_domains: list[str] = field(default_factory=list)
    affect: UserAffectState = field(default_factory=UserAffectState)
    locale: dict | None = None


@dataclass
class TimeState:
    now: float = 0.0
    bucket: str = "unknown"
    recency_window_ms: float = 300000.0
    session_elapsed_ms: float = 0.0
    time_since_last_user_signal_ms: float | None = None
    time_since_last_assistant_action_ms: float | None = None


@dataclass
class DiscourseEntry:
    """Records one turn's actual realized output for discourse repair tracking."""
    turn_id: str = ""
    input_signal_id: str = ""
    output_signal_id: str = ""
    user_text: str = ""
    assistant_text: str = ""
    assistant_intent: str = ""
    assistant_response_mode: str = ""
    assistant_decision_reason: str = ""
    act_types: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    status: str = "completed"  # completed, failed, repaired
    error_type: str = ""
    repair_target_turn_id: str = ""


@dataclass
class DiscourseStateStack:
    """Tracks actual assistant outputs so future repair can target failed turns."""
    entries: list[DiscourseEntry] = field(default_factory=list)
    max_depth: int = 12

    def push(self, entry: DiscourseEntry) -> None:
        self.entries.append(entry)
        if len(self.entries) > self.max_depth:
            self.entries = self.entries[-self.max_depth:]

    @property
    def last_entry(self) -> DiscourseEntry | None:
        return self.entries[-1] if self.entries else None

    @property
    def last_failed_entry(self) -> DiscourseEntry | None:
        for entry in reversed(self.entries):
            if entry.status == "failed":
                return entry
        return None


@dataclass
class ConversationState:
    session_id: str = ""
    turn_index: int = 0
    recent_signal_ids: list[str] = field(default_factory=list)
    active_entity_ids: list[str] = field(default_factory=list)
    active_claim_ids: list[str] = field(default_factory=list)
    active_repetition_group_ids: list[str] = field(default_factory=list)
    dynamics: ConversationDynamics = field(default_factory=ConversationDynamics)
    first_user_signal_id: str | None = None
    inferred_context_claim_ids: list[str] = field(default_factory=list)
    # Pending-question state: set when the assistant asks the user a question,
    # cleared when the user responds or the topic shifts. Enables contextual
    # interpretation of short answers like "I'm good" after "How are you?".
    pending_assistant_question: str = ""
    expected_user_answer_type: str = ""  # e.g. "social_status", "entity_name", "yes_no", "preference"
    last_assistant_response_mode: str = ""  # e.g. "social_response", "evidence_answer", "capability_summary"
    # v3.3: Discourse state stack for tracking actual realized outputs
    discourse_stack: DiscourseStateStack = field(default_factory=DiscourseStateStack)
    repair_target_turn_id: str = ""
    active_teaching_target: str = ""
    active_unknown_concept: str = ""


@dataclass
class GoalState:
    active_goal: str | None = None
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)


@dataclass
class TopicState:
    """Tracks the active conversation topic for pronoun coreference and multi-turn learning."""
    active_topic_entity_id: str = ""
    active_topic_surface: str = ""
    active_topic_type: str = ""  # e.g. "person", "place", "object", "concept"
    last_taught_entity_id: str = ""
    last_taught_entity_surface: str = ""
    last_questioned_attribute: str = ""  # e.g. "shape", "color", "is_a"
    last_updated_signal_id: str = ""
    last_updated_at: float = 0.0


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
    allow_simulation: bool = False

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
class ContextKernel:
    id: str
    self_state_id: str | None = None
    world: WorldState = field(default_factory=WorldState)
    user: UserState = field(default_factory=UserState)
    time: TimeState = field(default_factory=TimeState)
    conversation: ConversationState = field(default_factory=ConversationState)
    goal: GoalState = field(default_factory=GoalState)
    topic: TopicState = field(default_factory=TopicState)
    memory: MemoryState = field(default_factory=MemoryState)
    self_view: SelfView = field(default_factory=SelfView)
    permission: Permission = field(default_factory=Permission.public)
    budget: Budget = field(default_factory=Budget)
    latest_signal: Any | None = None
    version: str = "cemm.context_kernel.v1"

    @property
    def self(self) -> SelfView:
        return self.self_view
