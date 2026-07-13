"""RealizationSchema — executable definition of a surface realization.

Import boundary: standard library only → model.refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RealizationSchema:
    """Executable definition of how to realize a predicate in language."""
    semantic_key: str
    predicate_schema_ref: str = ""  # Ref[PredicateSchema]
    language_tag: str = "und"
    template: str = ""
    role_to_surface_mapping: dict[str, str] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
