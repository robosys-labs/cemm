"""Hard-gate and rank semantic response candidate plans."""

from __future__ import annotations

from ..types import ResponseCandidatePlan, ResponseSituation

_INTERNAL_SURFACE_VALUES = frozenset({
    "reply_obligation",
    "clarity_required",
    "event_candidate",
    "neutral",
    "feeling",
    "appreciation",
    "concern",
    "unknown",
    "none",
    "null",
})


class PlanGateAndRanker:
    def rank(self, plans: list[ResponseCandidatePlan], situation: ResponseSituation) -> list[ResponseCandidatePlan]:
        ranked: list[ResponseCandidatePlan] = []
        for plan in plans:
            self._gate(plan, situation)
            if plan.blocked_reason:
                plan.total_score = -1.0
            else:
                self._score(plan, situation)
            ranked.append(plan)
        ranked.sort(key=lambda p: (p.blocked_reason != "", -p.total_score, p.estimated_cost_ms, p.plan_id))
        for idx, plan in enumerate(ranked):
            plan.rank = idx + 1
        return ranked

    def _gate(self, plan: ResponseCandidatePlan, situation: ResponseSituation) -> None:
        if not plan.moves:
            plan.blocked_reason = plan.blocked_reason or "no_moves"
            return
        missing = plan.required_components - plan.satisfied_components
        if missing:
            plan.blocked_reason = "missing_required_components:" + ",".join(sorted(missing))
            return
        if any(move.safety_required for move in plan.moves):
            required = {"explicit_negative", "no_instruction", "no_endorsement"}
            if not required.issubset(plan.satisfied_components):
                plan.blocked_reason = "incomplete_safety_components"
                return
            if plan.framing_variant not in {"sharp_refusal", "deescalating_refusal"}:
                plan.blocked_reason = "unsafe_framing_for_safety_move"
                return
        if self._evidence_required(situation) and any(m.move_type == "answer" for m in plan.moves):
            if not plan.evidence_refs and not getattr(situation.evidence, "evidence_refs", []):
                plan.blocked_reason = "missing_required_evidence"
                return
        if any(m.move_type == "confirm_memory_write" for m in plan.moves):
            if not bool(situation.write_outcome and situation.write_outcome.committed):
                plan.blocked_reason = "untruthful_write_confirmation"
                return
        if self._has_internal_surface_leak(situation):
            plan.blocked_reason = "internal_surface_leak"
            return
        stage = getattr(getattr(situation, "budget_decision", None), "stage_budget", None)
        if stage is not None and getattr(stage, "selector_mode", "") == "first_good_enough":
            max_cost = max(1.0, float(stage.realized_candidate_limit) * 10.0)
            if plan.estimated_cost_ms > max_cost:
                plan.blocked_reason = "over_budget_for_fast_selector"

    def _score(self, plan: ResponseCandidatePlan, situation: ResponseSituation) -> None:
        decision = getattr(situation, "budget_decision", None)
        stage = getattr(decision, "stage_budget", None)
        pressure = float(getattr(decision, "pressure", 0.0) or 0.0)
        coverage = self._coverage(plan)
        evidence = self._evidence_score(plan, situation)
        safety = self._safety_score(plan, situation)
        style_fit = self._style_fit(plan, situation)
        cost_fit = max(0.0, 1.0 - min(1.0, plan.estimated_cost_ms / 10.0))
        semantic_priority = self._priority_score(plan)
        cost_weight = 0.25 if stage is not None and getattr(stage, "selector_mode", "") == "first_good_enough" else 0.1 + pressure * 0.2
        plan.score_parts = {
            "component_coverage": coverage,
            "evidence": evidence,
            "safety": safety,
            "style_fit": style_fit,
            "cost_fit": cost_fit,
            "semantic_priority": semantic_priority,
        }
        plan.total_score = (
            coverage * 0.24
            + evidence * 0.20
            + safety * 0.22
            + semantic_priority * 0.14
            + style_fit * max(0.05, 0.12 - pressure * 0.04)
            + cost_fit * cost_weight
        )

    @staticmethod
    def _coverage(plan: ResponseCandidatePlan) -> float:
        if not plan.required_components:
            return 1.0
        return len(plan.required_components & plan.satisfied_components) / max(1, len(plan.required_components))

    @staticmethod
    def _priority_score(plan: ResponseCandidatePlan) -> float:
        if not plan.moves:
            return 0.0
        best = min(move.priority for move in plan.moves)
        return max(0.0, min(1.0, 1.0 - best / 10.0))

    def _evidence_score(self, plan: ResponseCandidatePlan, situation: ResponseSituation) -> float:
        refs = list(plan.evidence_refs or []) or list(getattr(situation.evidence, "evidence_refs", []) or [])
        if refs:
            return min(1.0, len(refs) / 3.0)
        return 0.0 if self._evidence_required(situation) else 0.75

    @staticmethod
    def _safety_score(plan: ResponseCandidatePlan, situation: ResponseSituation) -> float:
        """Score safety completeness without changing hard-gate authority.

        Non-safety plans are neutral-good. Safety plans must already pass hard
        gates, but the score should still reflect how complete/appropriate the
        semantic safety package is so deterministic strict selection has a real
        safety signal instead of a constant no-op.
        """
        requires_safety = bool(plan.safety_tags) or any(move.safety_required for move in plan.moves)
        if not requires_safety:
            return 1.0

        required = {"explicit_negative", "no_instruction", "no_endorsement"}
        coverage = len(required & plan.satisfied_components) / len(required)
        has_frame = situation.safety_frame is not None and bool(getattr(situation.safety_frame, "category", ""))
        framing_ok = plan.framing_variant in {"sharp_refusal", "deescalating_refusal"}
        deescalation_bonus = 0.08 if "deescalate" in plan.satisfied_components or plan.framing_variant == "deescalating_refusal" else 0.0
        frame_score = 0.15 if has_frame else 0.0
        framing_score = 0.17 if framing_ok else 0.0
        return max(0.0, min(1.0, coverage * 0.60 + frame_score + framing_score + deescalation_bonus))

    @staticmethod
    def _style_fit(plan: ResponseCandidatePlan, situation: ResponseSituation) -> float:
        target = situation.style
        diff = (
            abs(plan.style.terseness - target.terseness)
            + abs(plan.style.formality - target.formality)
            + abs(plan.style.warmth - target.warmth)
            + abs(plan.style.detail - target.detail)
            + abs(plan.style.directness - target.directness)
        ) / 5.0
        return max(0.0, 1.0 - diff)

    @staticmethod
    def _evidence_required(situation: ResponseSituation) -> bool:
        return getattr(situation.obligation_frame, "evidence_policy", "") == "required"

    @staticmethod
    def _has_internal_surface_leak(situation: ResponseSituation) -> bool:
        binding = situation.answer_binding or getattr(situation.evidence, "answer_binding", None)
        for fill in getattr(binding, "slot_fills", []) or []:
            value = str(getattr(fill, "surface", "") or getattr(fill, "concept_id", "") or getattr(fill, "entity_id", "")).strip().lower()
            if value.replace("concept:", "") in _INTERNAL_SURFACE_VALUES:
                return True
            if ":" in value and value.count(":") == 1:
                left, right = value.split(":", 1)
                if left.replace("_", "").isalpha() and right.replace("_", "").isalpha():
                    return True
        return False
