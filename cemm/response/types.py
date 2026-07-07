"""Core types for the v3.1 response formation engine.

All types are pure dataclasses — no logic. The engine stages
(SituationBuilder, PrimitiveGoalComposer, etc.) operate on these.

Architecture: Response formation first, NLG last.
The runtime produces a ResponseBundle, not a bare string.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Budget ─────────────────────────────────────────────────────────────


@dataclass
class BudgetFrame:
    """Time/resource budget for one response cycle.

    Known before expensive cognition so the system can decide
    how many candidates to generate, how deep to query, etc.
    """
    total_time_ms: float = 5000.0
    remaining_time_ms: float = 5000.0
    latency_target_ms: float = 50.0
    max_recursive_steps: int = 1
    max_candidate_plans: int = 8
    max_realized_candidates: int = 3
    risk_level: str = "low"  # low, medium, high
    required_confidence: float = 0.3
    coverage_target: float = 0.8
    allow_partial_answer: bool = True
    allow_recursive_distillation: bool = False


# ── Write Outcome ──────────────────────────────────────────────────────


@dataclass
class WriteOutcome:
    """Result of patch validation + commit for this turn.

    Controls memory truthfulness: the response layer must not
    claim durable storage before commit_status == "committed".
    """
    patch_count: int = 0
    committed_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    commit_status: str = "none"  # none, proposed, committed, rejected, quarantined
    committed_record_ids: list[str] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)


# ── Evidence ───────────────────────────────────────────────────────────


@dataclass
class ResponseEvidencePacket:
    """Evidence gathered by the query engine for response formation.

    The query engine binds evidence; it does not choose final wording.
    """
    answer_binding: Any | None = None
    relation_frames: list[Any] = field(default_factory=list)
    semantic_query: Any | None = None
    explanation_paths: list[list[str]] = field(default_factory=list)


# ── Style & Temperature ────────────────────────────────────────────────


@dataclass
class StyleVector:
    """7 style axes that modulate surface realization."""
    terseness: float = 0.5      # 0=verbose, 1=terse
    formality: float = 0.5      # 0=casual, 1=formal
    warmth: float = 0.5         # 0=cold, 1=warm
    detail: float = 0.5         # 0=minimal, 1=detailed
    directness: float = 0.5     # 0=hedged, 1=direct
    uncertainty: float = 0.0    # 0=confident, 1=hedged
    repair_energy: float = 0.0  # 0=none, 1=maximum repair effort


@dataclass
class TemperatureState:
    """9 temperature dimensions derived from user state and self state."""
    user_urgency: float = 0.0
    user_detail_appetite: float = 0.5
    user_frustration: float = 0.0
    user_hostility: float = 0.0
    user_playfulness: float = 0.0
    self_uncertainty: float = 0.0
    self_recent_error_rate: float = 0.0
    self_warmth_throttle: float = 1.0
    conversation_repair_debt: float = 0.0


# ── Primitive Goals & Moves ────────────────────────────────────────────


# Primitive goal types — composable semantic forces
PRIMITIVE_GOALS = frozenset({
    "assert",       # state a fact
    "query",        # ask a question
    "acknowledge",  # confirm hearing/receiving
    "negate",       # deny or refuse
    "refuse",       # explicitly decline
    "instruct",     # give direction or guidance
    "greet",        # open social contact
    "farewell",     # close social contact
    "repair_self",  # acknowledge own prior error
    "reciprocate",  # mirror back (e.g. "how are you?" → "I'm fine, you?")
    "deescalate",   # reduce tension
    "hedge",        # express uncertainty
    "confirm_write", # confirm durable memory write
})


@dataclass
class PrimitiveResponseGoal:
    """One composable primitive goal."""
    goal_type: str  # one of PRIMITIVE_GOALS
    confidence: float = 0.8
    slots: dict[str, Any] = field(default_factory=dict)


# Response move types — communicative acts
RESPONSE_MOVES = frozenset({
    "answer",                 # provide information
    "acknowledge_heard",      # confirm hearing without storage claim
    "confirm_memory_write",   # confirm durable storage
    "clarify",                # ask for clarification
    "repair_prior_response",  # fix previous bad output
    "refuse",                 # decline a request
    "deescalate",             # reduce tension in safety context
    "safety_refusal",         # refuse + deescalate for harm
    "check_hearing",          # "did you hear me?" / "you still there?"
    "social_greet",           # greeting move
    "social_farewell",        # farewell move
    "phatic_response",        # check-in reciprocation
    "set_expectation",        # tell user what to expect
    "honest_abstain",         # no answer, honest about it
})


@dataclass
class ResponseMove:
    """One communicative move in a response."""
    move_type: str  # one of RESPONSE_MOVES
    primitive_goals: list[PrimitiveResponseGoal] = field(default_factory=list)
    confidence: float = 0.8
    safety_required: bool = False
    evidence_refs: list[str] = field(default_factory=list)


# ── Internal Actions ───────────────────────────────────────────────────


@dataclass
class InternalActionProposal:
    """A proposed internal action (not user-facing text).

    First-class proposals with authorization, not afterthoughts.
    """
    action_type: str  # set_locale_hint, mark_previous_response_failed, etc.
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    reversible: bool = True
    authorized: bool = False
    source_refs: list[str] = field(default_factory=list)
    reason: str = ""


# ── Candidates ─────────────────────────────────────────────────────────


@dataclass
class ResponseCandidatePlan:
    """A candidate response plan before surface realization.

    Contains moves, goals, style, and safety tags but no text yet.
    Ranking happens on plans before expensive realization.
    """
    plan_id: str = ""
    moves: list[ResponseMove] = field(default_factory=list)
    style: StyleVector = field(default_factory=StyleVector)
    framing_variant: str = "direct"  # minimal, direct, echo, hedged, etc.
    evidence_refs: list[str] = field(default_factory=list)
    safety_tags: list[str] = field(default_factory=list)
    required_components: list[str] = field(default_factory=list)
    satisfied_components: list[str] = field(default_factory=list)
    blocked_reason: str = ""
    score_parts: dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0


@dataclass
class RealizedCandidate:
    """A candidate plan with surface text realized."""
    plan: ResponseCandidatePlan = field(default_factory=ResponseCandidatePlan)
    text: str = ""
    language: str = "en"
    internal_actions: list[InternalActionProposal] = field(default_factory=list)


# ── Response Bundle ────────────────────────────────────────────────────


@dataclass
class ResponseBundle:
    """The final output of the response formation engine.

    Replaces SemanticRealizer's bare string output. Carries
    full traceability: moves, evidence, safety, internal actions.
    """
    text: str = ""
    language: str = "en"
    moves: list[ResponseMove] = field(default_factory=list)
    internal_actions: list[InternalActionProposal] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    safety_tags: list[str] = field(default_factory=list)
    style: StyleVector = field(default_factory=StyleVector)
    selected_plan_id: str = ""
    rejected_plans: list[ResponseCandidatePlan] = field(default_factory=list)
    write_outcome: WriteOutcome | None = None
    obligation_kind: str = ""
    confidence: float = 0.5
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ── Response Situation ─────────────────────────────────────────────────


@dataclass
class ResponseSituation:
    """Full runtime context for response formation.

    Assembled from all prior pipeline stages. This is the input
    to the response formation engine — not just RelationFrame + Slots
    but the full semantic runtime snapshot.
    """
    obligation_frame: Any | None = None
    answer_binding: Any | None = None
    semantic_program: Any | None = None
    relation_frames: list[Any] = field(default_factory=list)
    semantic_query: Any | None = None
    uol_graph: Any | None = None
    safety_frame: Any | None = None
    write_outcome: WriteOutcome | None = None
    budget_frame: BudgetFrame = field(default_factory=BudgetFrame)
    style: StyleVector = field(default_factory=StyleVector)
    temperature: TemperatureState = field(default_factory=TemperatureState)
    signal: Any | None = None
    kernel: Any | None = None
    percept: Any | None = None
    is_first_turn: bool = False
    conversation_turn_index: int = 0
