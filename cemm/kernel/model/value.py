"""Value — canonical semantic graph node for literal values.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Value:
    """A literal value in the semantic graph."""
    id: str
    value_type: str  # boolean, enum, text, quantity, set, coordinate, etc.
    data: Any
    unit: str | None = None
    normalization: str | None = None
    public_surface_hint: str | None = None
