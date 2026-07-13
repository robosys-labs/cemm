"""RoleSchema — executable definition of a predicate role.

Import boundary: standard library only → model.refs, model.role_binding.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.role_binding import Constraint, Preference


@dataclass(frozen=True, slots=True)
class RoleSchema:
    """Executable definition of a role in a predicate schema.

    Roles belong to PredicateSchema. Role resolution is schema-generic.
    No engine may hard-code a universal role list.
    """
    role_key: str
    required: bool = True
    cardinality: str = "one"  # one, optional_one, many, ordered_many
    accepted_object_families: frozenset[str] = field(default_factory=frozenset)
    accepted_entity_kinds: frozenset[str] = field(default_factory=frozenset)
    accepted_value_types: frozenset[str] = field(default_factory=frozenset)
    allows_open_port: bool = False
    allows_embedded_predication: bool = False
    allows_embedded_proposition: bool = False
    co_reference_constraints: tuple[Constraint, ...] = ()
    selectional_preferences: tuple[Preference, ...] = ()
