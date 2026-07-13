"""WorkspaceEntry — bounded global semantic workspace entry.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    """An entry in the bounded global semantic workspace."""
    item_ref: str
    item_kind: str
    relevance: float = 0.0
    novelty: float = 0.0
    uncertainty: float = 0.0
    urgency: float = 0.0
    goal_impact: float = 0.0
    causal_consequence: float = 0.0
    activation_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    decay_policy: str = "linear"
    protected_by_goal_refs: tuple[str, ...] = ()
