"""EntityKindSchema — executable definition of an entity kind.

Import boundary: standard library only → model.refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EntityKindSchema:
    """Executable definition of an entity kind."""
    semantic_key: str
    parent_kind_refs: tuple[str, ...] = ()  # Ref[EntityKindSchema]
    state_dimension_refs: tuple[str, ...] = ()  # Ref[StateDimensionSchema]
    predicate_refs: tuple[str, ...] = ()  # Ref[PredicateSchema]
    typical_features: tuple[str, ...] = ()
    identity_criteria: tuple[str, ...] = ()
