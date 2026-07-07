"""Language-agnostic response framing variants.

A framing variant is not wording. It is an abstract rhetorical policy that
selects which already-composed semantic moves to include and how much detail,
warmth, directness, or uncertainty the downstream language renderer may use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class FramingVariant:
    key: str
    priority: int = 5
    include_tags: FrozenSet[str] = frozenset()
    exclude_tags: FrozenSet[str] = frozenset()
    required_tags: FrozenSet[str] = frozenset()
    required_components: FrozenSet[str] = frozenset()
    style_overrides: dict[str, float] = field(default_factory=dict)
    realization_cost_bias: float = 1.0
    deterministic_only: bool = False


VARIANTS: dict[str, FramingVariant] = {
    "minimal": FramingVariant(
        key="minimal",
        priority=1,
        style_overrides={"terseness": 0.9, "directness": 0.85, "detail": 0.2},
        realization_cost_bias=0.65,
    ),
    "direct": FramingVariant(
        key="direct",
        priority=2,
        style_overrides={"directness": 0.75},
        realization_cost_bias=1.0,
    ),
    "with_evidence": FramingVariant(
        key="with_evidence",
        priority=3,
        include_tags=frozenset({"evidence"}),
        required_tags=frozenset({"answer"}),
        style_overrides={"detail": 0.75, "directness": 0.65},
        realization_cost_bias=1.35,
    ),
    "repair": FramingVariant(
        key="repair",
        priority=1,
        include_tags=frozenset({"repair"}),
        required_tags=frozenset({"repair"}),
        required_components=frozenset({"acknowledge_prior_failure"}),
        style_overrides={"repair_energy": 0.85, "warmth": 0.65, "directness": 0.7},
        realization_cost_bias=1.15,
    ),
    "hedged": FramingVariant(
        key="hedged",
        priority=4,
        style_overrides={"uncertainty": 0.65, "directness": 0.4},
        realization_cost_bias=1.1,
    ),
    "warm_followup": FramingVariant(
        key="warm_followup",
        priority=4,
        style_overrides={"warmth": 0.8, "detail": 0.55},
        realization_cost_bias=1.2,
    ),
    "sharp_refusal": FramingVariant(
        key="sharp_refusal",
        priority=0,
        required_tags=frozenset({"safety"}),
        required_components=frozenset({"explicit_negative", "no_instruction", "no_endorsement"}),
        style_overrides={"terseness": 0.95, "directness": 0.95, "detail": 0.1},
        realization_cost_bias=0.55,
        deterministic_only=True,
    ),
    "deescalating_refusal": FramingVariant(
        key="deescalating_refusal",
        priority=0,
        required_tags=frozenset({"safety"}),
        required_components=frozenset({"explicit_negative", "no_instruction", "no_endorsement"}),
        style_overrides={"terseness": 0.85, "directness": 0.9, "warmth": 0.55, "detail": 0.2},
        realization_cost_bias=0.75,
        deterministic_only=True,
    ),
}


def get_variant(key: str) -> FramingVariant:
    return VARIANTS.get(key, VARIANTS["direct"])
