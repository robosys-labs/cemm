"""Canonical input signals for the v3.4 cognitive cycle.

Raw content is carried by an InputSignal. ``signal_ids`` remain references and
must never be overloaded with user text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .refs import FrozenMap


@dataclass(frozen=True, slots=True)
class SignalEnvelope:
    """Immutable transport envelope for an observed input signal."""

    id: str
    signal_kind: str
    language_tag: str = "und"
    received_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    channel: str = "text"
    source_ref: str | None = None
    raw_data_ref: str | None = None
    features: FrozenMap = field(default_factory=FrozenMap)


@dataclass(frozen=True, slots=True)
class InputSignal:
    """An observed input delivered to a cognitive cycle."""

    id: str
    content: str
    context_id: str = "default"
    source_ref: str = "user"
    language_hint: str = "en"
    channel: str = "text"
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
