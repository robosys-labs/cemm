"""ContextSchema — accessibility policy for context frames.

Import boundary: standard library only → model.refs, model.identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.identity import TimeExtent


@dataclass(frozen=True, slots=True)
class ContextSchema:
    """Executable definition of a context accessibility policy."""
    semantic_key: str
    allows_parent_access: bool = True
    allows_sibling_access: bool = False
    allows_actual_world_access: bool = True
    valid_time: TimeExtent | None = None
    assumptions_required: bool = False
