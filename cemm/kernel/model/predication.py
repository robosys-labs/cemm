"""Predication — semantic content: predicate + role bindings + open ports.

Import boundary: standard library only → refs, role_binding, surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .refs import FrozenMap
from .role_binding import RoleBinding, OpenPort


@dataclass(frozen=True, slots=True)
class AspectProfile:
    """Aspectual information for a predication."""
    tense: str = "unspecified"  # past, present, future, unspecified
    aspect: str = "unspecified"  # perfective, imperfective, progressive, habitual, etc.
    is_stative: bool = False


@dataclass(frozen=True, slots=True)
class Predication:
    """Semantic content: predicate schema + typed role bindings + open ports.

    A Predication is *content* — it is not yet truth-bearing.
    A Proposition makes content truth-bearing by adding context, polarity,
    modality, attribution, and valid time.
    """
    id: str
    predicate_schema_ref: str  # Ref[PredicateSchema] as opaque string
    bindings: tuple[RoleBinding, ...] = ()
    open_ports: tuple[OpenPort, ...] = ()
    occurrence_kind: str = "relation"  # relation, state, event
    aspect: AspectProfile | None = None
    source_span_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    confidence: float = 0.0
