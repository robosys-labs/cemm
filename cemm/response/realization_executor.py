"""Language-specific realization for response moves.

This module is English-specific, but it must not interpret English input.
Interpretation belongs to MeaningPerceptor/MeaningGraphBuilder and the query
engine. The executor only renders already-bound semantic slots and response
moves into English surface text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .types import RealizedCandidate, ResponseCandidatePlan, ResponseMove, ResponseSituation


@dataclass
class BoundSlot:
    key: str
    value: str
    relation_key: str = ""
    slot_kind: str = "surface"
    confidence: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


class SlotBinder:
    """Bind response slots from SemanticQueryEngine outputs.

    This class does not inspect the user's raw text. If no semantic slot was
    bound upstream, the renderer must not invent one by re-parsing surface.
    """

    def bind(self, situation: ResponseSituation) -> dict[str, BoundSlot]:
        slots: dict[str, BoundSlot] = {}
        evidence = situation.evidence
        for key, slot in getattr(evidence, "selected_slots", {}).items() if evidence is not None else []:
            value = getattr(slot, "value", "")
            if value:
                slots[key] = BoundSlot(
                    key=key,
                    value=self._clean_semantic_value(str(value)),
                    relation_key=getattr(slot, "relation_key", "") or "",
                    slot_kind=getattr(slot, "slot_kind", "surface") or "surface",
                    confidence=float(getattr(slot, "confidence", 0.5) or 0.5),
                    source_refs=self._slot_refs(slot),
                )

        binding = situation.answer_binding or getattr(evidence, "answer_binding", None)
        fills = list(getattr(binding, "slot_fills", []) or [])
        if fills and "answer" not in slots:
            best = max(fills, key=lambda fill: getattr(fill, "confidence", 0.0) or 0.0)
            value = self._fill_value(best)
            if value:
                slots["answer"] = BoundSlot(
                    key="answer",
                    value=self._clean_semantic_value(value),
                    relation_key=getattr(best, "relation_key", "") or "",
                    confidence=float(getattr(best, "confidence", 0.5) or 0.5),
                    source_refs=[*getattr(best, "source_frame_ids", []), *getattr(best, "evidence_refs", [])],
                    features=dict(getattr(best, "features", {}) or {}),
                )
        return slots

    @staticmethod
    def _fill_value(fill: Any) -> str:
        return str(
            getattr(fill, "surface", "")
            or getattr(fill, "concept_id", "")
            or getattr(fill, "entity_id", "")
            or ""
        )

    @staticmethod
    def _slot_refs(slot: Any) -> list[str]:
        refs = [
            getattr(slot, "source_binding_id", ""),
            getattr(slot, "source_atom_id", ""),
            getattr(slot, "source_relation_id", ""),
            getattr(slot, "source_record_id", ""),
        ]
        return [ref for ref in refs if ref]

    @staticmethod
    def _clean_semantic_value(value: str) -> str:
        # Mechanical output hygiene only. This is not interpretation.
        allowed = []
        for char in value:
            code = ord(char)
            if code in (9, 10, 13) or code >= 32:
                allowed.append(char)
        return " ".join("".join(allowed).split()).strip()


class EnglishPredicateSelector:
    """Map semantic relation keys to English labels."""

    RELATION_LABELS = {
        "has_name": "name",
        "has_age": "age",
        "has_alias": "alias",
        "has_role": "role",
        "has_property": "value",
        "located_in": "location",
        "from_place": "origin",
    }

    def user_profile_label(self, slot: BoundSlot) -> str:
        dimension = (
            slot.features.get("property_dimension")
            or slot.features.get("dimension")
            or slot.features.get("profile_label")
            or ""
        )
        if dimension:
            return self._english_label(str(dimension))
        return self.RELATION_LABELS.get(slot.relation_key, self._english_label(slot.relation_key or "value"))

    @staticmethod
    def _english_label(value: str) -> str:
        if value.startswith("has_"):
            value = value[4:]
        if ":" in value:
            value = value.split(":", 1)[1]
        return " ".join(part for part in value.split("_") if part) or "value"


class EnglishMorphologizer:
    @staticmethod
    def sentence(text: str) -> str:
        text = " ".join((text or "").split()).strip()
        if not text:
            return ""
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
        return text


class EnglishLinearizer:
    @staticmethod
    def user_profile(label: str, value: str) -> str:
        return f"your {label} is {value}"

    @staticmethod
    def self_identity(value: str) -> str:
        return f"I am {value}"

    @staticmethod
    def evidence_explanation(path: str) -> str:
        return f"(via: {path})"


class RealizationExecutor:
    """Render response moves into English from semantic slots only."""

    def __init__(self) -> None:
        self._slots = SlotBinder()
        self._predicates = EnglishPredicateSelector()
        self._morph = EnglishMorphologizer()
        self._linearizer = EnglishLinearizer()

    def realize(self, moves: list[ResponseMove], situation: ResponseSituation) -> str:
        return self.realize_candidate(moves, situation).text

    def realize_candidate(self, moves: list[ResponseMove], situation: ResponseSituation) -> RealizedCandidate:
        plan = ResponseCandidatePlan(
            plan_id="deterministic",
            moves=list(moves),
            framing_variant="direct",
            evidence_refs=_dedupe([ref for move in moves for ref in move.evidence_refs]),
            safety_tags=self._safety_tags(situation),
            required_components=set().union(*(move.required_components for move in moves)) if moves else set(),
            satisfied_components=set().union(*(move.satisfied_components for move in moves)) if moves else set(),
            total_score=1.0,
        )
        slots = self._slots.bind(situation)
        parts = [self._realize_move(move, situation, slots) for move in moves]
        text = " ".join(part for part in parts if part).strip()
        return RealizedCandidate(
            plan=plan,
            text=text,
            language=situation.language or "en",
            grammar_trace={
                "language": "en",
                "move_count": len(moves),
                "slot_keys": sorted(slots),
                "surface_source": "semantic_slots_only",
            },
        )

    def _realize_move(
        self,
        move: ResponseMove,
        situation: ResponseSituation,
        slots: dict[str, BoundSlot],
    ) -> str:
        match move.move_type:
            case "social_greet":
                return "Hello." if situation.style.formality >= 0.65 else "Hi."
            case "social_farewell":
                return "Bye for now."
            case "phatic_response":
                return "I'm here and running normally. How are you doing?"
            case "answer":
                return self._answer(situation, slots)
            case "evidence_explanation":
                return self._evidence_explanation(situation)
            case "acknowledge_heard":
                return "Got it."
            case "confirm_memory_write":
                return self._confirm_write(situation, slots)
            case "honest_abstain":
                return self._abstain(situation)
            case "safety_refusal":
                return self._safety_refusal(situation)
            case "repair_prior_response":
                return "You're right, I missed that."
            case "clarify":
                return "Could you clarify that?"
            case "deescalate":
                return "Let's take a step back."
            case "set_expectation":
                return "Give me a moment on that."
        return ""

    def _answer(self, situation: ResponseSituation, slots: dict[str, BoundSlot]) -> str:
        answer = slots.get("answer")
        if answer is None or not answer.value:
            return self._abstain(situation)
        obligation_kind = getattr(situation.obligation_frame, "obligation_kind", "") if situation.obligation_frame is not None else ""
        if obligation_kind == "answer_self_identity":
            return self._morph.sentence(self._linearizer.self_identity(answer.value))
        if obligation_kind == "answer_user_profile":
            label = self._predicates.user_profile_label(answer)
            return self._morph.sentence(self._linearizer.user_profile(label, answer.value))
        return self._morph.sentence(answer.value)

    def _confirm_write(self, situation: ResponseSituation, slots: dict[str, BoundSlot]) -> str:
        write = situation.write_outcome
        if write is None or not write.committed:
            return "Got it."
        answer = slots.get("answer")
        if answer is not None and answer.value:
            return self._morph.sentence(f"I've stored it: {answer.value}")
        return "I've stored that."

    def _abstain(self, situation: ResponseSituation) -> str:
        evidence = situation.evidence
        binding = situation.answer_binding or getattr(evidence, "answer_binding", None)
        reason = getattr(binding, "abstention_reason", "") or getattr(evidence, "abstention_reason", "")
        if str(reason).startswith("blocked"):
            return "I can't answer that from the available evidence."
        if reason == "no_matches":
            return "I don't have enough information to answer that yet."
        if reason == "no_relation_key_or_algebra":
            return "I'm not sure how to look that up yet."
        return "I don't have enough verified information to answer that."

    def _safety_refusal(self, situation: ResponseSituation) -> str:
        category = (getattr(situation.safety_frame, "category", "") or "").lower()
        severity = (getattr(situation.safety_frame, "severity", "") or "").lower()
        if category == "self_harm":
            return "No. I can't help with self-harm. Please reach out to someone you trust or emergency support right now."
        if category in {"interpersonal_violence", "violence", "harm"}:
            if severity in {"high", "critical", "imminent"}:
                return "No. Step away from the situation and get immediate help if anyone is in danger."
            return "No. I don't want anyone getting hurt."
        return "No. I can't help with that request."

    def _evidence_explanation(self, situation: ResponseSituation) -> str:
        paths = getattr(situation.evidence, "explanation_paths", []) if situation.evidence is not None else []
        longest = max(paths, key=len) if paths else []
        if len(longest) > 1:
            return self._linearizer.evidence_explanation(" -> ".join(longest))
        return ""

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
