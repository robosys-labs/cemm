"""MetalanguageSchema — executable definition for metalinguistic predicates.

Import boundary: standard library only → model.refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MetalanguageSchema:
    """Executable definition for metalinguistic operations.

    Supports predicates like ``means(lexical_form, schema)`` and
    ``knows(self, proposition_pattern)``.
    """
    semantic_key: str
    target_predicate_ref: str = ""  # Ref[PredicateSchema]
    quoted_form_handling: str = "preserve"  # preserve, normalise, evaluate
    supports_nested_queries: bool = True
