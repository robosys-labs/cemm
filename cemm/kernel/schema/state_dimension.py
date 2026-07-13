"""StateDimensionSchema — executable definition of a state dimension.

Import boundary: standard library only → model.refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class StateDimensionSchema:
    """Executable definition of a state dimension.

    temporal_policy: instantaneous, interval, persistent_until_changed, event_derived
    contradiction_policy: latest_wins, coexist, block
    """
    semantic_key: str
    holder_kinds: frozenset[str] = field(default_factory=frozenset)
    value_type: str = "text"
    unit: str | None = None
    cardinality: str = "one"  # one, many
    temporal_policy: str = "persistent_until_changed"
    contradiction_policy: str = "latest_wins"
    transition_predicate_refs: tuple[str, ...] = ()  # Ref[PredicateSchema]
