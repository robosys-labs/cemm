"""Trace records for diagnostics.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .refs import FrozenMap


@dataclass(frozen=True, slots=True)
class CycleTrace:
    """Trace of a single cognitive cycle."""
    cycle_id: str
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    finished_at: datetime | None = None
    trigger_kind: str = ""
    stages: tuple[str, ...] = ()
    stage_timings: dict[str, float] = field(default_factory=dict)
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticTrace:
    """Trace of semantic processing for a signal."""
    signal_ref: str
    stages: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    features: FrozenMap = field(default_factory=FrozenMap)
