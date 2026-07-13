"""RoleBinding and OpenPort — typed role fillers and unfilled ports.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .refs import Ref, FrozenMap


@dataclass(frozen=True, slots=True)
class Constraint:
    """A typed constraint on a role filler."""
    constraint_kind: str  # type, kind, value_range, pattern, cardinality, etc.
    expression: Any
    negated: bool = False


@dataclass(frozen=True, slots=True)
class Preference:
    """A selectional preference for a role."""
    preference_kind: str
    target: str
    weight: float = 0.5


@dataclass(frozen=True, slots=True)
class RoleBinding:
    """A binding from a predication role to a real filler."""
    role_schema_ref: str  # Ref[RoleSchema] as opaque string
    filler_ref: str  # Ref to Referent | Value | Predication | Proposition | ContextFrame
    confidence: float = 0.0
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpenPort:
    """An unfilled typed role requirement.

    An open port is metadata on a candidate predication or query pattern.
    It is never:
    - a placeholder entity;
    - a concept named ``topic``, ``object``, or ``target``;
    - a public response value;
    - a durable memory candidate.
    """
    role_schema_ref: str  # Ref[RoleSchema] as opaque string
    required: bool = True
    cardinality: str = "one"  # one, optional_one, many, ordered_many
    constraints: tuple[Constraint, ...] = ()
    source_span_refs: tuple[str, ...] = ()
