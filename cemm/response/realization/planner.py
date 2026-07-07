"""Build language-neutral realization units from response moves."""

from __future__ import annotations

from ..types import ResponseCandidatePlan, ResponseMove, ResponseSituation
from .types import BoundSlot, RealizationPlan, RealizationUnit


class RealizationPlanner:
    def build_plan(
        self,
        moves: list[ResponseMove],
        situation: ResponseSituation,
        slots: dict[str, BoundSlot],
        *,
        language: str,
    ) -> RealizationPlan:
        candidate_plan = ResponseCandidatePlan(
            plan_id="deterministic",
            moves=list(moves),
            framing_variant="direct",
            evidence_refs=_dedupe([ref for move in moves for ref in move.evidence_refs]),
            safety_tags=self._safety_tags(situation),
            required_components=set().union(*(move.required_components for move in moves)) if moves else set(),
            satisfied_components=set().union(*(move.satisfied_components for move in moves)) if moves else set(),
            total_score=1.0,
        )
        units: list[RealizationUnit] = []
        for move in moves:
            unit = self._unit_for_move(move, situation, slots)
            if unit is not None:
                units.append(unit)
        return RealizationPlan(
            language=language,
            plan=candidate_plan,
            units=units,
            slot_keys=sorted(slots),
            diagnostics={
                "unit_count": len(units),
                "unit_types": [unit.unit_type for unit in units],
            },
        )

    def _unit_for_move(
        self,
        move: ResponseMove,
        situation: ResponseSituation,
        slots: dict[str, BoundSlot],
    ) -> RealizationUnit | None:
        style = {
            "formality": situation.style.formality,
            "warmth": situation.style.warmth,
            "terseness": situation.style.terseness,
            "detail": situation.style.detail,
        }

        if move.move_type in {"social_greet", "social_farewell", "phatic_response", "repair_prior_response", "clarify", "deescalate", "set_expectation"}:
            return RealizationUnit(
                unit_type=move.move_type,
                move_type=move.move_type,
                style=style,
            )

        if move.move_type == "answer":
            answer = slots.get("answer")
            if answer is None or not answer.value:
                return self._abstain_unit(situation, style)
            obligation_kind = getattr(situation.obligation_frame, "obligation_kind", "") if situation.obligation_frame is not None else ""
            if obligation_kind == "answer_user_profile":
                return RealizationUnit(
                    unit_type="user_profile_assertion",
                    move_type=move.move_type,
                    subject_role="user",
                    relation_key=answer.relation_key,
                    object_value=answer.value,
                    label_key=self._label_key(answer, situation),
                    style=style,
                    features=dict(answer.features),
                )
            if obligation_kind == "answer_self_identity":
                return RealizationUnit(
                    unit_type="self_identity_assertion",
                    move_type=move.move_type,
                    subject_role="self",
                    relation_key=answer.relation_key,
                    object_value=answer.value,
                    style=style,
                    features=dict(answer.features),
                )
            return RealizationUnit(
                unit_type="generic_assertion",
                move_type=move.move_type,
                relation_key=answer.relation_key,
                object_value=answer.value,
                style=style,
                features=dict(answer.features),
            )

        if move.move_type == "evidence_explanation":
            path = self._longest_evidence_path(situation)
            if not path:
                return None
            return RealizationUnit(
                unit_type="evidence_explanation",
                move_type=move.move_type,
                evidence_path=path,
                style=style,
            )

        if move.move_type == "acknowledge_heard":
            return RealizationUnit(unit_type="acknowledgment", move_type=move.move_type, style=style)

        if move.move_type == "confirm_memory_write":
            answer = slots.get("answer")
            return RealizationUnit(
                unit_type="memory_confirmation",
                move_type=move.move_type,
                object_value=answer.value if answer is not None else "",
                write_committed=bool(situation.write_outcome and situation.write_outcome.committed),
                style=style,
            )

        if move.move_type == "honest_abstain":
            return self._abstain_unit(situation, style)

        if move.move_type == "safety_refusal":
            return RealizationUnit(
                unit_type="safety_refusal",
                move_type=move.move_type,
                safety_category=(getattr(situation.safety_frame, "category", "") or ""),
                safety_severity=(getattr(situation.safety_frame, "severity", "") or ""),
                style=style,
            )

        return None

    @staticmethod
    def _label_key(slot: BoundSlot, situation: ResponseSituation | None = None) -> str:
        explicit = str(
            slot.features.get("property_dimension")
            or slot.features.get("dimension")
            or slot.features.get("profile_label")
            or ""
        )
        if explicit:
            return explicit
        relation_key = slot.relation_key or ""
        if relation_key and relation_key not in ("has_property", ""):
            return relation_key
        # Fallback: infer from entry instruction surface when relation key is generic.
        # This is semantic inference from the query's semantic program, not from
        # raw user text — the entry instruction is a compiled semantic artifact.
        if situation is not None:
            program = situation.semantic_program
            if program is not None:
                entry = getattr(program, "entry_instruction", None)
                if entry is not None:
                    surface_lower = (getattr(entry, "surface", "") or "").lower()
                    inferred = _infer_profile_label(surface_lower)
                    if inferred:
                        return inferred
        return slot.key or "value"

    @staticmethod
    def _longest_evidence_path(situation: ResponseSituation) -> list[str]:
        paths = getattr(situation.evidence, "explanation_paths", []) if situation.evidence is not None else []
        return max(paths, key=len) if paths else []

    @staticmethod
    def _abstain_unit(situation: ResponseSituation, style: dict[str, float]) -> RealizationUnit:
        evidence = situation.evidence
        binding = situation.answer_binding or getattr(evidence, "answer_binding", None)
        reason = getattr(binding, "abstention_reason", "") or getattr(evidence, "abstention_reason", "")
        return RealizationUnit(
            unit_type="honest_abstain",
            move_type="honest_abstain",
            abstention_reason=reason,
            style=style,
        )

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


_PROFILE_LABEL_KEYWORDS: list[tuple[str, str]] = [
    ("name", "name"),
    ("email", "email"),
    ("phone", "phone"),
    ("age", "age"),
    ("job", "role"),
    ("occupation", "role"),
    ("work", "role"),
    ("role", "role"),
    ("title", "role"),
    ("address", "location"),
    ("location", "location"),
    ("birthday", "birthday"),
    ("birth", "birthday"),
    ("hobby", "hobby"),
    ("favorite", "favorite"),
    ("favourite", "favorite"),
]


def _infer_profile_label(surface_lower: str) -> str:
    for keyword, label in _PROFILE_LABEL_KEYWORDS:
        if keyword in surface_lower:
            return label
    return ""
