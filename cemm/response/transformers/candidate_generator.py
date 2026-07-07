"""Semantic response candidate generation.

Phase 4 generates candidate plans from response moves and abstract framing
variants. It never reads user text and never chooses language-specific wording.
Phase 5 may cap the number of generated plans through BudgetDecision.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

from ..types import ResponseCandidatePlan, ResponseMove, ResponseSituation, StyleVector
from .framing_variant import FramingVariant, VARIANTS, get_variant


class CandidateGenerator:
    def generate(self, moves: list[ResponseMove], situation: ResponseSituation) -> list[ResponseCandidatePlan]:
        limit = self._candidate_limit(situation)
        variant_keys = self._variant_keys_for(moves, situation)
        plans: list[ResponseCandidatePlan] = []
        for key in variant_keys:
            variant = get_variant(key)
            plan_moves = self._moves_for_variant(moves, variant)
            if not plan_moves:
                continue
            plan = self._build_plan(plan_moves, variant, situation)
            plans.append(plan)
            if len(plans) >= limit:
                break
        return plans or [ResponseCandidatePlan(plan_id="empty", moves=[], blocked_reason="no_candidate_moves")]

    @staticmethod
    def _candidate_limit(situation: ResponseSituation) -> int:
        stage = getattr(getattr(situation, "budget_decision", None), "stage_budget", None)
        return max(1, int(getattr(stage, "candidate_plan_limit", situation.budget_frame.max_candidate_plans) or 1))

    def _variant_keys_for(self, moves: list[ResponseMove], situation: ResponseSituation) -> list[str]:
        tags = self._tags(moves)
        required = self._required_components(moves)
        pressure = float(getattr(getattr(situation, "budget_decision", None), "pressure", 0.0) or 0.0)

        if "safety" in tags or any(m.safety_required for m in moves):
            # Never explore playful/warm/hedged alternatives for safety. These are
            # semantically strict refusal framings, not text templates.
            return ["sharp_refusal", "deescalating_refusal"]

        keys: list[str] = []
        if "repair" in tags or "acknowledge_prior_failure" in required:
            keys.append("repair")
        if pressure >= 0.75:
            keys.extend(["minimal", "direct"])
        else:
            keys.extend(["direct", "minimal"])

        if "answer" in tags and "evidence" in tags:
            keys.append("with_evidence")
        if situation.style.uncertainty >= 0.45 or "abstention" in tags:
            keys.append("hedged")
        if situation.style.warmth >= 0.65 and not ({"abstention", "safety"} & tags):
            keys.append("warm_followup")
        return _dedupe(keys)

    @staticmethod
    def _moves_for_variant(moves: list[ResponseMove], variant: FramingVariant) -> list[ResponseMove]:
        tags = CandidateGenerator._tags(moves)
        if variant.required_tags and not variant.required_tags.issubset(tags):
            return []
        selected = [m for m in moves if not (m.tags & variant.exclude_tags)]
        if variant.include_tags:
            include = [m for m in selected if m.tags & variant.include_tags]
            # Include required non-optional moves alongside the focused move.
            selected = [m for m in selected if m.required_components or m.safety_required] + include
        if variant.key == "minimal":
            required_moves = [m for m in selected if m.safety_required or m.required_components]
            selected = required_moves or selected[:1]
        if variant.key in {"sharp_refusal", "deescalating_refusal"}:
            selected = [m for m in selected if m.safety_required or "safety" in m.tags]
        return _dedupe_moves(selected)

    def _build_plan(self, moves: list[ResponseMove], variant: FramingVariant, situation: ResponseSituation) -> ResponseCandidatePlan:
        required = self._required_components(moves) | set(variant.required_components)
        satisfied = self._satisfied_components(moves)
        style = self._style_for_variant(situation.style, variant, situation)
        return ResponseCandidatePlan(
            plan_id=self._plan_id(moves, variant.key),
            moves=moves,
            style=style,
            framing_variant=variant.key,
            evidence_refs=_dedupe([ref for move in moves for ref in move.evidence_refs]),
            safety_tags=self._safety_tags(situation),
            required_components=required,
            satisfied_components=satisfied,
            estimated_cost_ms=self._estimated_cost(moves, variant),
        )

    @staticmethod
    def _style_for_variant(style: StyleVector, variant: FramingVariant, situation: ResponseSituation) -> StyleVector:
        values = {
            "terseness": style.terseness,
            "formality": style.formality,
            "warmth": style.warmth,
            "detail": style.detail,
            "directness": style.directness,
            "uncertainty": style.uncertainty,
            "repair_energy": style.repair_energy,
        }
        stage = getattr(getattr(situation, "budget_decision", None), "stage_budget", None)
        if stage is not None:
            values["detail"] = min(values["detail"], float(getattr(stage, "detail_level", values["detail"])))
        for key, target in variant.style_overrides.items():
            current = values.get(key, target)
            if key in {"detail", "directness"} and target < current:
                values[key] = target
            else:
                values[key] = max(current, target)
        return StyleVector(**values)

    @staticmethod
    def _estimated_cost(moves: list[ResponseMove], variant: FramingVariant) -> float:
        semantic_weight = sum(1.0 + len(m.required_components) * 0.15 + len(m.evidence_refs) * 0.05 for m in moves)
        return round(max(0.25, semantic_weight * variant.realization_cost_bias), 3)

    @staticmethod
    def _tags(moves: list[ResponseMove]) -> set[str]:
        return set().union(*(move.tags for move in moves)) if moves else set()

    @staticmethod
    def _required_components(moves: list[ResponseMove]) -> set[str]:
        return set().union(*(move.required_components for move in moves)) if moves else set()

    @staticmethod
    def _satisfied_components(moves: list[ResponseMove]) -> set[str]:
        return set().union(*(move.satisfied_components for move in moves)) if moves else set()

    @staticmethod
    def _safety_tags(situation: ResponseSituation) -> list[str]:
        safety = situation.safety_frame
        category = getattr(safety, "category", "") if safety is not None else ""
        return [category] if category else []

    @staticmethod
    def _plan_id(moves: list[ResponseMove], variant: str) -> str:
        material = variant + ":" + ",".join(move.move_type for move in moves)
        return "plan_" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:12]


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _dedupe_moves(moves: Iterable[ResponseMove]) -> list[ResponseMove]:
    out: list[ResponseMove] = []
    seen: set[str] = set()
    for move in moves:
        key = move.move_type + ":" + ",".join(sorted(move.tags))
        if key not in seen:
            out.append(move)
            seen.add(key)
    return out
