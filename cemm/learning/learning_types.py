"""Graph-patch-only learning types for CEMM Phase 9.

The learning layer observes structured runtime outcomes and produces patch
candidates. It does not commit patches, mutate stores, or persist raw user or
assistant text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_ALLOWED_LEARNING_TARGETS = frozenset({
    "response_construction_stats",
    "framing_success_stats",
    "budget_allocation_stats",
    "distillation_strategy_stats",
    "repair_failure_trace",
    "safety_response_trace",
})


@dataclass
class StructuralObservation:
    """Structural proposition emitted by the graph builder.

    The builder emits observations about the input, not authorized mutations.
    The LearningPatchCompiler converts these to GraphPatch objects after
    LearningContract authorization. Full provenance is tracked for each
    observation.
    """

    obs_type: str = ""
    target: str = "discard"
    operation: str = ""
    target_id: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    reason: str = ""

    source_frame_id: str = ""
    source_group_id: str = ""
    source_branch_id: str = ""
    episode_id: str = ""
    gap_id: str = ""

    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    permission_refs: list[str] = field(default_factory=list)


@dataclass
class OutcomeSignal:
    """Structured outcome evidence for one response turn."""

    outcome_type: str = "unknown"
    confidence: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningObservation:
    """Sanitized observation extracted from a response cycle."""

    selected_plan_id: str = ""
    framing_variant: str = ""
    move_types: list[str] = field(default_factory=list)
    obligation_kind: str = ""
    budget_pressure: float = 0.0
    selector_mode: str = ""
    candidate_count: int = 0
    rejected_count: int = 0
    realized_language: str = ""
    evidence_ref_count: int = 0
    coverage_estimate: float | None = None
    partial_coverage: bool = False
    safety_categories: list[str] = field(default_factory=list)
    write_commit_status: str = ""
    outcome: OutcomeSignal = field(default_factory=OutcomeSignal)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class LearningPatchCandidate:
    """Patch candidate produced by learning, awaiting normal validation.

    The payload is deliberately statistical and semantic. It must not carry raw
    natural-language transcript text.
    """

    patch_id: str = ""
    target: str = ""
    operation: str = "increment_stat"
    key: tuple[str, ...] = field(default_factory=tuple)
    delta: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5
    reversible: bool = True
    source_refs: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def is_allowed_target(self) -> bool:
        return self.target in _ALLOWED_LEARNING_TARGETS


@dataclass
class LearningExtractionResult:
    """Phase 9 output: patch candidates plus diagnostics only."""

    observation: LearningObservation = field(default_factory=LearningObservation)
    patch_candidates: list[LearningPatchCandidate] = field(default_factory=list)
    rejected_candidates: list[LearningPatchCandidate] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def all_candidates(self) -> list[LearningPatchCandidate]:
        return [*self.patch_candidates, *self.rejected_candidates]
