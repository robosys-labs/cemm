"""ConstructionSchema — a learned pattern for mapping surface constructions
to UOL graph structures.

Induced from repeated aligned UOL graphs, not raw sentence templates.
Requires diverse lexical fillers before generalization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ConstructionSlot:
    """A slot in a construction schema."""
    name: str
    required_kind: str = ""  # entity, concept, operator, state, etc.
    optional: bool = False
    default_value: str = ""


@dataclass(frozen=True, slots=True)
class ConstructionSchema:
    """A learned construction mapping surface patterns to UOL graph rewrites."""
    schema_id: str
    language_tag: str
    name: str = ""
    
    # Slot pattern
    slots: tuple[ConstructionSlot, ...] = ()
    slot_order: tuple[str, ...] = ()
    
    # UOL graph rewrite template
    graph_rewrite: dict[str, Any] = field(default_factory=dict)
    
    # Context
    domain: str = ""
    register: str = ""
    
    # Learning metadata
    confidence: float = 0.5
    observed_fillers: int = 0
    diverse_filler_count: int = 0
    success_rate: float = 0.0
    scope: str = "language"
    
    def is_generalizable(self, min_diverse_fillers: int = 3) -> bool:
        return self.diverse_filler_count >= min_diverse_fillers and self.success_rate >= 0.6
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "language_tag": self.language_tag,
            "name": self.name,
            "slot_count": len(self.slots),
            "confidence": self.confidence,
            "scope": self.scope,
        }
