"""ConstructionSchema — executable definition of a grammatical construction.

Import boundary: standard library only → model.refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ConstructionSchema:
    """Executable definition of a grammatical construction.

    Constructions map surface patterns to predications. They are
    candidate-only evidence — surface evidence never directly becomes
    authority.
    """
    semantic_key: str
    pattern: str = ""
    predicate_schema_ref: str = ""  # Ref[PredicateSchema]
    role_mappings: dict[str, str] = field(default_factory=dict)
    open_role_refs: tuple[str, ...] = ()
    communicative_force: str = ""
    language_tag: str = "und"
    constraints: tuple[str, ...] = ()
