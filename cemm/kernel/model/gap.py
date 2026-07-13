"""GapRecord — concrete blocked-competency detection.

Import boundary: standard library only → refs, identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProbePlan:
    """A plan for probing to resolve a gap."""
    probe_kind: str
    target_ref: str
    expected_evidence_kind: str
    budget_cost: int = 1
    idempotency_key: str = ""


@dataclass(frozen=True, slots=True)
class LearningBudget:
    """Budget for learning/probing activities."""
    probe_budget: int = 0
    replay_budget: int = 0
    probes_remaining: int = 0
    replays_remaining: int = 0


@dataclass(frozen=True, slots=True)
class GapRecord:
    """A concrete gap detected in the system's competence.

    A gap may be learnable — the system can attempt to resolve it
    through a learning transaction.
    """
    id: str
    gap_kind: str = "missing_competence"
    target_artifact_ref: str = ""
    missing_fields: tuple[str, ...] = ()
    conflicting_fields: tuple[str, ...] = ()
    blocked_stage: str = ""
    blocked_goal_refs: tuple[str, ...] = ()
    preserved_artifact_refs: tuple[str, ...] = ()
    hypothesis_refs: tuple[str, ...] = ()
    probe_options: tuple[ProbePlan, ...] = ()
    expected_evidence_schema_ref: str | None = None
    resume_checkpoint_ref: str = ""
    learnable: bool = False
    budget: LearningBudget = field(default_factory=LearningBudget)
