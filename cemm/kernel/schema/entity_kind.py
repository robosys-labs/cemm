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
    grounding_anchor_refs: tuple[str, ...] = ()
    constitutive_rule_refs: tuple[str, ...] = ()
    default_rule_refs: tuple[str, ...] = ()
    event_pattern_refs: tuple[str, ...] = ()
    place_pattern_refs: tuple[str, ...] = ()
    sensitivity: str = "ordinary"
