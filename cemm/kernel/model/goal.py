"""GoalRecord — desired propositions and arbitration.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class GoalRecord:
    """A goal — a desired state of the world or information state.

    goal_kind: world_state, information_state, discourse, maintenance
    """
    id: str
    owner_ref: str  # Ref[Referent]
    desired_pattern_ref: str = ""  # Ref[SemanticPattern]
    goal_kind: str = "information_state"
    priority: float = 0.0
    urgency: float = 0.0
    policy_priority: int = 0
    success_condition_refs: tuple[str, ...] = ()  # Ref[SemanticPattern]
    failure_condition_refs: tuple[str, ...] = ()  # Ref[SemanticPattern]
    dependencies: tuple[str, ...] = ()  # Ref[GoalRecord]
    conflicts: tuple[str, ...] = ()  # Ref[GoalRecord]
    status: str = "active"  # active, satisfied, abandoned, blocked, suspended
    expires_at: datetime | None = None
