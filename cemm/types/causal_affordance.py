from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .predicate_schema import GraphPattern, GraphPatchTemplate


@dataclass
class PortBindingPattern:
    port_id: str
    filler_kind: str | None = None
    filler_concept: str | None = None
    required: bool = True


@dataclass
class CausalAffordance:
    affordance_id: str
    trigger_pattern: GraphPattern | None = None
    required_bindings: list[PortBindingPattern] = field(default_factory=list)
    predicted_effect: GraphPatchTemplate | None = None
    effect_type: str = "state_change"
    source_support: list[Any] = field(default_factory=list)
    counterexamples: list[Any] = field(default_factory=list)
    confidence: float = 0.5
