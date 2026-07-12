"""Core response formation types.

These types intentionally keep semantic composition separate from English
surface realization. Response goals and moves are language-agnostic; only
the realization executor is allowed to choose English wording.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRIMITIVE_GOALS = frozenset({
    "assert",
    "query",
    "clarify",
    "acknowledge",
    "negate",
    "refuse",
    "instruct",
    "greet",
    "farewell",
    "repair_self",
    "reciprocate",
    "deescalate",
    "hedge",
    "confirm_write",
    "explain_evidence",
    "set_expectation",
})

RESPONSE_MOVES = frozenset({
    "answer",
    "acknowledge_heard",
    "confirm_memory_write",
    "clarify",
    "repair_prior_response",
    "safety_refusal",
    "deescalate",
    "social_greet",
    "social_farewell",
    "phatic_response",
    "set_expectation",
    "honest_abstain",
    "evidence_explanation",
})


@dataclass
class BudgetFrame:
    total_time_ms: float = 5000.0
    remaining_time_ms: float = 5000.0
    latency_target_ms: float = 50.0
    max_recursive_steps: int = 1
    max_candidate_plans: int = 8
    max_realized_candidates: int = 3
    risk_level: str = "normal"
    required_confidence: float = 0.5
    coverage_target: float = 0.5
    allow_partial_answer: bool = True
    allow_recursive_distillation: bool = False




@dataclass
class StageBudget:
    """Per-stage spend plan derived from BudgetFrame.

    This is language-agnostic and controls computational effort, not wording.
    """

    attention_focus_limit: int = 16
    query_result_limit: int = 16
    candidate_plan_limit: int = 4
    realized_candidate_limit: int = 2
    explanation_depth: int = 1
    selector_mode: str = "score"  # score, first_good_enough, deterministic_strict
    allow_inverse_query: bool = True
    allow_inheritance_query: bool = True
    allow_recursive_distillation: bool = False
    allow_composition_query: bool = False
    max_query_inference_depth: int = 1
    stop_on_first_sufficient_query: bool = True
    query_min_confidence: float = 0.5
    detail_level: float = 0.5
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetDecision:
    """Budget arbitration result for one response cycle."""

    input_budget: BudgetFrame = field(default_factory=BudgetFrame)
    stage_budget: StageBudget = field(default_factory=StageBudget)
    pressure: float = 0.0
    task_size: float = 0.0
    risk_level: str = "normal"
    reasons: list[str] = field(default_factory=list)

@dataclass
class WriteOutcome:
    """Validated write/patch status for the current turn."""

    patch_count: int = 0
    committed_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    commit_status: str = "none"  # none, proposed, validated, committed, rejected, conflict, quarantined
    committed_record_ids: list[str] = field(default_factory=list)
    committed_patch_ids: list[str] = field(default_factory=list)
    rejected_patch_ids: list[str] = field(default_factory=list)
    conflict_ids: list[str] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)
    required_target_ids: list[str] = field(default_factory=list)
    committed_target_ids: list[str] = field(default_factory=list)
    operation_results: dict[str, str] = field(default_factory=dict)

    @property
    def satisfied(self) -> bool:
        if self.required_target_ids:
            return set(self.required_target_ids) <= set(self.committed_target_ids)
        return self.commit_status == "committed" and self.committed_count > 0

    @property
    def committed(self) -> bool:
        return self.satisfied


@dataclass
class ResponseEvidencePacket:
    """Semantic evidence bound by SemanticQueryEngine."""

    answer_binding: Any | None = None
    relation_frames: list[Any] = field(default_factory=list)
    semantic_query: Any | None = None
    selected_slots: dict[str, Any] = field(default_factory=dict)
    explanation_paths: list[list[str]] = field(default_factory=list)
    answer_kind: str = ""
    answer_status: str = "unavailable"
    abstention_reason: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @classmethod
    def from_runtime(
        cls,
        *,
        semantic_query: Any | None = None,
        answer_binding: Any | None = None,
        relation_frames: list[Any] | None = None,
    ) -> "ResponseEvidencePacket":
        explanation_paths = list(getattr(answer_binding, "explanation_paths", []) or [])
        evidence_refs: list[str] = []
        for fill in getattr(answer_binding, "slot_fills", []) or []:
            for ref in [*getattr(fill, "source_frame_ids", []), *getattr(fill, "evidence_refs", [])]:
                if ref and ref not in evidence_refs:
                    evidence_refs.append(ref)
        has_answer = bool(getattr(answer_binding, "has_answer", False))
        return cls(
            answer_binding=answer_binding,
            relation_frames=list(relation_frames or []),
            semantic_query=semantic_query,
            explanation_paths=explanation_paths,
            answer_kind=getattr(semantic_query, "query_kind", "") or "",
            answer_status="answered" if has_answer else "no_answer",
            abstention_reason=getattr(answer_binding, "abstention_reason", "") or "",
            evidence_refs=evidence_refs,
            confidence=float(getattr(answer_binding, "confidence", 0.0) or 0.0),
        )


@dataclass
class StyleVector:
    terseness: float = 0.5
    formality: float = 0.5
    warmth: float = 0.5
    detail: float = 0.5
    directness: float = 0.5
    uncertainty: float = 0.0
    repair_energy: float = 0.0


@dataclass
class TemperatureState:
    user_urgency: float = 0.0
    user_detail_appetite: float = 0.5
    user_frustration: float = 0.0
    user_hostility: float = 0.0
    user_playfulness: float = 0.0
    self_uncertainty: float = 0.0
    self_recent_error_rate: float = 0.0
    self_warmth_throttle: float = 0.0
    conversation_repair_debt: float = 0.0


@dataclass
class PrimitiveResponseGoal:
    goal_type: str
    confidence: float = 0.8
    required: bool = False
    priority: int = 5
    target_refs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    constraints: set[str] = field(default_factory=set)
    slots: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class ResponseMove:
    move_type: str
    primitive_goals: list[PrimitiveResponseGoal] = field(default_factory=list)
    confidence: float = 0.8
    priority: int = 5
    required_components: set[str] = field(default_factory=set)
    satisfied_components: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    safety_required: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class InternalActionProposal:
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    reversible: bool = True
    authorized: bool = False
    source_refs: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class ResponseCandidatePlan:
    plan_id: str = ""
    moves: list[ResponseMove] = field(default_factory=list)
    style: StyleVector = field(default_factory=StyleVector)
    framing_variant: str = "direct"
    evidence_refs: list[str] = field(default_factory=list)
    safety_tags: list[str] = field(default_factory=list)
    required_components: set[str] = field(default_factory=set)
    satisfied_components: set[str] = field(default_factory=set)
    blocked_reason: str = ""
    score_parts: dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    estimated_cost_ms: float = 0.0
    rank: int = 0


@dataclass
class RealizedCandidate:
    plan: ResponseCandidatePlan = field(default_factory=ResponseCandidatePlan)
    text: str = ""
    language: str = "en"
    grammar_trace: dict[str, Any] = field(default_factory=dict)
    internal_actions: list[InternalActionProposal] = field(default_factory=list)


@dataclass
class ResponseBundle:
    text: str = ""
    language: str = "en"
    moves: list[ResponseMove] = field(default_factory=list)
    internal_actions: list[InternalActionProposal] = field(default_factory=list)
    proposed_internal_actions: list[InternalActionProposal] = field(default_factory=list)
    rejected_internal_actions: list[InternalActionProposal] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    safety_tags: list[str] = field(default_factory=list)
    style: StyleVector = field(default_factory=StyleVector)
    selected_plan_id: str = ""
    rejected_plans: list[ResponseCandidatePlan] = field(default_factory=list)
    write_outcome: WriteOutcome | None = None
    obligation_kind: str = ""
    confidence: float = 0.5
    diagnostics: dict[str, Any] = field(default_factory=dict)
    budget_decision: BudgetDecision | None = None
    deliberation_plan: Any | None = None
    distillation_result: Any | None = None
    action_authorization: Any | None = None
    learning_result: Any | None = None
    learning_patch_candidates: list[Any] = field(default_factory=list)


@dataclass
class ResponseSituation:
    obligation_frame: Any | None = None
    answer_binding: Any | None = None
    evidence: ResponseEvidencePacket | None = None
    semantic_program: Any | None = None
    relation_frames: list[Any] = field(default_factory=list)
    semantic_query: Any | None = None
    uol_graph: Any | None = None
    safety_frame: Any | None = None
    reaction_signal: Any | None = None
    write_outcome: WriteOutcome | None = None
    deliberation_plan: Any | None = None
    distillation_result: Any | None = None
    budget_frame: BudgetFrame = field(default_factory=BudgetFrame)
    budget_decision: BudgetDecision | None = None
    style: StyleVector = field(default_factory=StyleVector)
    temperature: TemperatureState = field(default_factory=TemperatureState)
    signal: Any | None = None
    kernel: Any | None = None
    percept: Any | None = None
    language: str = "en"
    is_first_turn: bool = False
    conversation_turn_index: int = 0
