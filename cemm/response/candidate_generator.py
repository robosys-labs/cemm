"""Candidate plan generator.

Generates multiple ResponseCandidatePlan objects with different framing
variants. This is the variation layer that enables ranking and selection.

Language-agnostic: operates on moves and style, never on surface text.
"""

from __future__ import annotations

from typing import Any

from .framing import FramingVariant, variants_for_context
from .types import (
    PrimitiveResponseGoal,
    ResponseCandidatePlan,
    ResponseMove,
    ResponseSituation,
)


class CandidateGenerator:
    """Generate candidate plans with framing variants."""

    def generate(
        self,
        moves: list[ResponseMove],
        goals: list[PrimitiveResponseGoal],
        situation: ResponseSituation,
    ) -> list[ResponseCandidatePlan]:
        context = self._context(moves, goals, situation)
        variants = variants_for_context(**context)
        plans: list[ResponseCandidatePlan] = []
        for variant in variants:
            plan = self._build_plan(variant, moves, situation)
            plans.append(plan)
        return plans

    def _build_plan(
        self,
        variant: FramingVariant,
        moves: list[ResponseMove],
        situation: ResponseSituation,
    ) -> ResponseCandidatePlan:
        filtered = variant.apply(moves)
        return ResponseCandidatePlan(
            plan_id=f"candidate_{variant.name}",
            moves=filtered,
            style=variant.style,
            framing_variant=variant.name,
            evidence_refs=_dedupe([ref for m in filtered for ref in m.evidence_refs]),
            safety_tags=self._safety_tags(situation),
            required_components=set().union(*(m.required_components for m in filtered)) if filtered else set(),
            satisfied_components=set().union(*(m.satisfied_components for m in filtered)) if filtered else set(),
            score_parts=dict(variant.score_weights),
            total_score=0.0,
        )

    @staticmethod
    def _context(
        moves: list[ResponseMove],
        goals: list[PrimitiveResponseGoal],
        situation: ResponseSituation,
    ) -> dict[str, Any]:
        move_types = {m.move_type for m in moves}
        goal_types = {g.goal_type for g in goals}
        has_safety = any(m.safety_required for m in moves)
        binding = situation.answer_binding or (
            getattr(situation.evidence, "answer_binding", None) if situation.evidence else None
        )
        has_answer = bool(getattr(binding, "has_answer", False))
        confidence = float(getattr(binding, "confidence", 0.5) or 0.5)
        obligation_kind = ""
        if situation.obligation_frame is not None:
            obligation_kind = getattr(situation.obligation_frame, "obligation_kind", "") or ""
        is_store_patch = obligation_kind == "store_patch"
        is_social = obligation_kind == "social_reply" or "social_greet" in move_types or "social_farewell" in move_types
        is_repair = "repair_self" in goal_types or "repair_prior_response" in move_types
        return {
            "has_safety": has_safety,
            "has_answer": has_answer,
            "is_store_patch": is_store_patch,
            "is_social": is_social,
            "is_repair": is_repair,
            "confidence": confidence,
        }

    @staticmethod
    def _safety_tags(situation: ResponseSituation) -> list[str]:
        category = getattr(situation.safety_frame, "category", "") if situation.safety_frame is not None else ""
        return [category] if category else []


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
