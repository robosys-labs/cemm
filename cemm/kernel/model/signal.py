"""Signal envelope — raw input signal metadata.

Import boundary: standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .refs import FrozenMap


@dataclass(frozen=True, slots=True)
class SignalEnvelope:
    """Envelope for a raw input signal before semantic processing."""
    id: str
    signal_kind: str  # text, audio, sensor, event, etc.
    language_tag: str = "und"
    received_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    channel: str = "text"
    source_ref: str | None = None
    raw_data_ref: str | None = None
    features: FrozenMap = field(default_factory=FrozenMap)
