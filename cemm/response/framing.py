"""Framing variants for candidate generation.

Framing variants are language-agnostic. They modify the style vector and move
selection, not surface text. Each variant produces a different candidate plan
that the ranker and selector can evaluate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import ResponseMove, StyleVector


@dataclass(frozen=True)
class FramingVariant:
    """A language-agnostic framing strategy."""

    name: str
    style: StyleVector
    move_types_to_drop: frozenset[str] = frozenset()
    score_weights: dict[str, float] = field(default_factory=dict)

    def apply(self, moves: list[ResponseMove]) -> list[ResponseMove]:
        if not self.move_types_to_drop:
            return list(moves)
        return [m for m in moves if m.move_type not in self.move_types_to_drop]


# ── Variant definitions ────────────────────────────────────────────────

MINIMAL = FramingVariant(
    name="minimal",
    style=StyleVector(terseness=0.9, formality=0.5, warmth=0.3, detail=0.1, directness=0.8),
    move_types_to_drop=frozenset({"evidence_explanation", "phatic_response"}),
    score_weights={"terseness": 1.2, "detail": 0.5},
)

DIRECT = FramingVariant(
    name="direct",
    style=StyleVector(terseness=0.5, formality=0.5, warmth=0.5, detail=0.5, directness=0.8),
    score_weights={"directness": 1.0, "confidence": 1.0},
)

ECHO = FramingVariant(
    name="echo",
    style=StyleVector(terseness=0.4, formality=0.5, warmth=0.6, detail=0.6, directness=0.7),
    score_weights={"warmth": 0.8, "confidence": 0.9},
)

REPAIR = FramingVariant(
    name="repair",
    style=StyleVector(terseness=0.4, formality=0.5, warmth=0.6, detail=0.6, directness=0.7,
                      repair_energy=0.8),
    score_weights={"repair_energy": 1.5, "confidence": 0.8},
)

HEDGED = FramingVariant(
    name="hedged",
    style=StyleVector(terseness=0.5, formality=0.6, warmth=0.4, detail=0.6, directness=0.4,
                      uncertainty=0.7),
    score_weights={"uncertainty": 1.3, "confidence": 0.7},
)

WARM_FOLLOWUP = FramingVariant(
    name="warm_followup",
    style=StyleVector(terseness=0.3, formality=0.4, warmth=0.9, detail=0.7, directness=0.6),
    score_weights={"warmth": 1.5, "detail": 1.0},
)

SHARP_REFUSAL = FramingVariant(
    name="sharp_refusal",
    style=StyleVector(terseness=0.9, formality=0.7, warmth=0.1, detail=0.2, directness=1.0),
    move_types_to_drop=frozenset({"evidence_explanation", "phatic_response", "acknowledge_heard"}),
    score_weights={"directness": 2.0, "safety": 1.5},
)

DEESCALATING_REFUSAL = FramingVariant(
    name="deescalating_refusal",
    style=StyleVector(terseness=0.5, formality=0.6, warmth=0.5, detail=0.5, directness=0.8),
    move_types_to_drop=frozenset({"evidence_explanation", "phatic_response"}),
    score_weights={"warmth": 0.8, "safety": 1.5, "directness": 1.0},
)

ALL_VARIANTS: dict[str, FramingVariant] = {
    v.name: v for v in (
        MINIMAL, DIRECT, ECHO, REPAIR, HEDGED, WARM_FOLLOWUP,
        SHARP_REFUSAL, DEESCALATING_REFUSAL,
    )
}


def variants_for_context(
    *,
    has_safety: bool,
    has_answer: bool,
    is_store_patch: bool,
    is_social: bool,
    is_repair: bool,
    confidence: float,
) -> list[FramingVariant]:
    """Select relevant framing variants for the current situation."""
    if has_safety:
        return [SHARP_REFUSAL, DEESCALATING_REFUSAL]

    variants: list[FramingVariant] = [DIRECT]

    if is_store_patch:
        variants.append(ECHO)
        variants.append(MINIMAL)
    elif is_repair:
        variants.append(REPAIR)
    elif is_social:
        variants.append(WARM_FOLLOWUP)
        variants.append(MINIMAL)
    elif has_answer and confidence < 0.6:
        variants.append(HEDGED)
    elif has_answer:
        variants.append(MINIMAL)

    return variants
