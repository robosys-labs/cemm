from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeCycleResult:
    signal: Any
    context_kernel: Any
    percept: Any | None = None
    uol_graph: Any | None = None
    working_set: Any | None = None
    retrieval: Any | None = None
    resolution: Any | None = None
    act_plan: Any | None = None
    patch_candidates: list[Any] = field(default_factory=list)
    validation: list[Any] = field(default_factory=list)
    consolidation: list[Any] = field(default_factory=list)
    realized_output: str = ""
    diagnostics: Any | None = None
    cost_ms: float = 0.0
    # v4.2 first-class outputs
    semantic_program: Any | None = None
    obligation_frame: Any | None = None
    relation_frames: list[Any] = field(default_factory=list)
    semantic_query: Any | None = None
    answer_binding: Any | None = None
    response_bundle: Any | None = None
    # v3.2 operational spine outputs
    operational_meaning_frames: list[Any] = field(default_factory=list)
    meaning_arbitration: Any | None = None
    state_transmutations: list[Any] = field(default_factory=list)
    operational_effects: list[Any] = field(default_factory=list)
    obligation_contract: Any | None = None
    situation_frame: Any | None = None
    # 3.3 shadow trace fields — populated by shadow components; do not affect behavior
    semantic_gaps: list[Any] = field(default_factory=list)
    lexical_candidates: list[Any] = field(default_factory=list)
    interpretation_lattice: Any | None = None
    interpretation_resolution: dict[str, Any] = field(default_factory=dict)
    predicate_activations: list[Any] = field(default_factory=list)
    entity_groundings: list[Any] = field(default_factory=list)
    obligation_graph: Any | None = None
    active_learning_episodes: list[Any] = field(default_factory=list)
    learning_questions: list[Any] = field(default_factory=list)
    execution_ledger: Any | None = None
    learning_use_outcomes: list[Any] = field(default_factory=list)
    transmutation_authorizations: list[Any] = field(default_factory=list)
    learning_answer_fields: list[Any] = field(default_factory=list)
    activated_frame_ids: list[str] = field(default_factory=list)
    # v3.4 cognitive cycle fields — hybrid migration; v3.4 components are
    # wired with single-writer enforcement but legacy authorities still
    # control key operational spine outputs.
    surface_evidence: Any | None = None
    candidate_graph: Any | None = None
    grounding_assessments: list[Any] = field(default_factory=list)
    epistemic_assessments: list[Any] = field(default_factory=list)
    capability_assessment: Any | None = None
    self_report: Any | None = None
    learning_transaction: Any | None = None
    commit_outcome: Any | None = None
    common_ground_entries: list[Any] = field(default_factory=list)
    # v3.4 ORIENT — pinned environment snapshot
    kernel_snapshot: Any | None = None
    # v3.4 RESOLVE — typed interpretation result
    v34_interpretation: Any | None = None
    # v3.4 GAPS — typed gap list from GapDetector
    v34_gaps: list[Any] = field(default_factory=list)
    # v3.4 DECIDE — goals, plan, authorization
    v34_goals: Any | None = None
    v34_plan: Any | None = None
    v34_authorization: Any | None = None
    # v3.4 ACT — execution result and reconciliation
    v34_execution: Any | None = None
    v34_reconciliation: Any | None = None
    # v3.4 COMMUNICATE — message plan from ResponsePlanner
    v34_message_plan: Any | None = None
