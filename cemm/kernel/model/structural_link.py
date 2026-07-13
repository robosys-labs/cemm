"""StructuralLink — graph structure edges only.

Import boundary: standard library only → refs.

StructuralLink expresses graph structure only. Semantic relations
(is_a, same_as, part_of, causes, knows, etc.) are always Predication
instances, never StructuralLinks.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .refs import FrozenMap


# Canonical structural link types — fixed vocabulary only.
STRUCTURAL_LINK_TYPES = frozenset({
    "has_role",
    "instantiates",
    "refers_to",
    "grounded_by",
    "scoped_by",
    "supported_by",
    "opposed_by",
    "derived_from",
    "depends_on",
    "co_refers_with",
})


@dataclass(frozen=True, slots=True)
class StructuralLink:
    """A structural edge in the semantic graph.

    link_type must be one of the STRUCTURAL_LINK_TYPES vocabulary.
    Semantic relations are never encoded as StructuralLinks.
    """
    id: str
    link_type: str
    source_ref: str
    target_ref: str
    features: FrozenMap = field(default_factory=FrozenMap)

    def __post_init__(self) -> None:
        if self.link_type not in STRUCTURAL_LINK_TYPES:
            raise ValueError(
                f"StructuralLink link_type must be one of {STRUCTURAL_LINK_TYPES}, "
                f"got {self.link_type!r}. "
                "Semantic relations must be Predication instances."
            )
