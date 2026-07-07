"""Minimal English realization executor.

This is the only response v3.1 phase-3 module that is intentionally
language-specific. It receives language-agnostic response moves and semantic
slots, then performs English pronoun, predicate, morphology, and linearization
work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .types import RealizedCandidate, ResponseCandidatePlan, ResponseMove, ResponseSituation


_DISCOURSE_MARKERS = frozenset({
    "well", "so", "oh", "actually", "basically", "honestly", "anyway",
    "anyways", "hmm", "huh", "um", "uh", "er", "ah", "ok", "okay",
    "right", "yeah", "yep", "nope", "lol", "haha", "hehe",
})


@dataclass
class BoundSlot:
    key: str
    value: str
    relation_key: str = ""
    slot_kind: str = "surface"
    confidence: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


class PronounResolver:
    """English pronoun shifting for echoing user-originated assertions."""

    _PHASE1 = [
        (r"\bI'm\b", "\x001ST_IM\x00"),
        (r"\bIm\b", "\x001ST_IM\x00"),
        (r"\bmyself\b", "\x001ST_MYSELF\x00"),
        (r"\bmine\b", "\x001ST_MINE\x00"),
        (r"\bme\b", "\x001ST_ME\x00"),
        (r"\bmy\b", "\x001ST_MY\x00"),
        (r"\bI\b", "\x001ST_I\x00"),
        (r"\bours\b", "\x001ST_OURS\x00"),
        (r"\bour\b", "\x001ST_OUR\x00"),
    ]
    _PHASE2 = [
        (r"\byou're\b", "\x002ND_YOURE\x00"),
        (r"\byoure\b", "\x002ND_YOURE\x00"),
        (r"\byourself\b", "\x002ND_YOURSELF\x00"),
        (r"\byourselves\b", "\x002ND_OURSELVES\x00"),
        (r"\byours\b", "\x002ND_YOURS\x00"),
        (r"\byour\b", "\x002ND_YOUR\x00"),
        (r"\byou\b", "\x002ND_YOU\x00"),
    ]
    _RESOLVE = [
        ("\x001ST_I\x00", "you"),
        ("\x001ST_IM\x00", "you're"),
        ("\x001ST_MY\x00", "your"),
        ("\x001ST_ME\x00", "you"),
        ("\x001ST_MINE\x00", "yours"),
        ("\x001ST_MYSELF\x00", "yourself"),
        ("\x001ST_OURS\x00", "yours"),
        ("\x001ST_OUR\x00", "your"),
        ("\x002ND_YOURE\x00", "I'm"),
        ("\x002ND_YOURSELF\x00", "myself"),
        ("\x002ND_OURSELVES\x00", "ourselves"),
        ("\x002ND_YOURS\x00", "mine"),
        ("\x002ND_YOUR\x00", "my"),
        ("\x002ND_YOU\x00", "I"),
    ]

    def shift_user_assertion_to_assistant_echo(self, surface: str) -> str:
        result = surface
        for pattern, replacement in self._PHASE1:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        for pattern, replacement in self._PHASE2:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        for placeholder, final in self._RESOLVE:
            result = result.replace(placeholder, final)
        return result


class PredicateSelector:
    """Choose compact English predicate forms from semantic relation keys."""

    _PROFILE_LABELS = {
        "has_name": "name",
        "has_age": "age",
        "has_alias": "alias",
        "has_role": "role",
        "has_property": "value",
        "has_email": "email",
        "has_phone": "phone",
        "located_in": "location",
        "from_place": "origin",
    }

    _SURFACE_LABEL_HINTS: list[tuple[str, str]] = [
        ("email", "email"),
        ("phone", "phone"),
        ("address", "location"),
        ("location", "location"),
        ("birthday", "birthday"),
        ("birth", "birthday"),
        ("hobby", "hobby"),
        ("favorite", "favorite"),
        ("favourite", "favorite"),
        ("name", "name"),
        ("age", "age"),
        ("job", "role"),
        ("occupation", "role"),
        ("work", "role"),
        ("role", "role"),
        ("title", "role"),
    ]

    def label_for(self, slot: BoundSlot) -> str:
        dimension = (
            slot.features.get("property_dimension")
            or slot.features.get("dimension")
            or slot.features.get("profile_label")
            or ""
        )
        if dimension:
            return self._clean_label(str(dimension))
        return self._PROFILE_LABELS.get(slot.relation_key, self._clean_label(slot.relation_key or slot.key or "value"))

    def label_from_surface(self, query_surface: str, fallback: str = "value") -> str:
        lower = query_surface.lower()
        for hint, label in self._SURFACE_LABEL_HINTS:
            if hint in lower:
                return label
        return fallback

    @staticmethod
    def _clean_label(value: str) -> str:
        value = value.replace("has_", "").replace("_", " ").strip()
        return value or "value"


class Morphologizer:
    @staticmethod
    def sentence(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
        return text


class Linearizer:
    @staticmethod
    def user_profile(label: str, value: str) -> str:
        return f"your {label} is {value}"

    @staticmethod
    def self_identity(value: str) -> str:
        return f"I am {value}"

    @staticmethod
    def evidence_explanation(path: str) -> str:
        return f"(via: {path})"


class SurfacePostProcessor:
    _SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
    _STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
    _TAG_RE = re.compile(r"<[^>]+>")
    _CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    _FRAMING_PREFIXES = [
        re.compile(r"^i told you (?:that )?", re.IGNORECASE),
        re.compile(r"^i said (?:that )?", re.IGNORECASE),
        re.compile(r"^i mentioned (?:that )?", re.IGNORECASE),
        re.compile(r"^i informed you (?:that )?", re.IGNORECASE),
        re.compile(r"^remember\s+", re.IGNORECASE),
    ]

    def clean_echo(self, surface: str, *, limit: int = 200) -> str:
        surface = self._SCRIPT_RE.sub("", surface)
        surface = self._STYLE_RE.sub("", surface)
        surface = self._TAG_RE.sub("", surface)
        surface = self._CONTROL_RE.sub("", surface)
        surface = re.sub(r"\s+", " ", surface).strip()
        tokens = surface.split()
        while tokens and tokens[0].lower() in _DISCOURSE_MARKERS:
            tokens.pop(0)
        while tokens and tokens[-1].lower() in _DISCOURSE_MARKERS:
            tokens.pop()
        surface = " ".join(tokens)
        for pattern in self._FRAMING_PREFIXES:
            surface = pattern.sub("", surface).strip()
        if len(surface) > limit:
            surface = surface[: max(0, limit - 3)].rstrip() + "..."
        return surface


class SlotBinder:
    def bind(self, situation: ResponseSituation) -> dict[str, BoundSlot]:
        slots: dict[str, BoundSlot] = {}
        for key, slot in getattr(situation.evidence, "selected_slots", {}).items() if situation.evidence is not None else []:
            value = getattr(slot, "value", "")
            if value:
                slots[key] = BoundSlot(
                    key=key,
                    value=str(value),
                    slot_kind=getattr(slot, "slot_kind", "surface") or "surface",
                    confidence=float(getattr(slot, "confidence", 0.5) or 0.5),
                    source_refs=[getattr(slot, "source_relation_id", "") or getattr(slot, "source_atom_id", "")],
                )
        binding = situation.answer_binding or getattr(situation.evidence, "answer_binding", None)
        fills = list(getattr(binding, "slot_fills", []) or [])
        if fills and "answer" not in slots:
            best = max(fills, key=lambda fill: getattr(fill, "confidence", 0.0) or 0.0)
            value = self._surface_value(best)
            slots["answer"] = BoundSlot(
                key="answer",
                value=value,
                relation_key=getattr(best, "relation_key", "") or "",
                confidence=float(getattr(best, "confidence", 0.5) or 0.5),
                source_refs=[*getattr(best, "source_frame_ids", []), *getattr(best, "evidence_refs", [])],
                features=dict(getattr(best, "features", {}) or {}),
            )
        return slots

    def echo_surface(self, situation: ResponseSituation) -> str:
        slots = self.bind(situation)
        if "answer" in slots and slots["answer"].value:
            return slots["answer"].value
        entry = getattr(situation.semantic_program, "entry_instruction", None)
        return getattr(entry, "surface", "") or ""

    @staticmethod
    def _surface_value(fill: Any) -> str:
        return (
            getattr(fill, "surface", "")
            or getattr(fill, "concept_id", "")
            or getattr(fill, "entity_id", "")
            or ""
        )


class RealizationExecutor:
    def __init__(self) -> None:
        self._slots = SlotBinder()
        self._pronouns = PronounResolver()
        self._predicates = PredicateSelector()
        self._morph = Morphologizer()
        self._linearizer = Linearizer()
        self._post = SurfacePostProcessor()

    def realize(self, moves: list[ResponseMove], situation: ResponseSituation) -> str:
        candidate = self.realize_candidate(moves, situation)
        return candidate.text

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
        parts: list[str] = []
        for move in moves:
            text = self._realize_move(move, situation, slots)
            if text:
                parts.append(text)
        return RealizedCandidate(
            plan=plan,
            text=" ".join(parts).strip(),
            language=situation.language or "en",
            grammar_trace={"move_count": len(moves), "slot_keys": sorted(slots)},
        )

    def _realize_move(self, move: ResponseMove, situation: ResponseSituation, slots: dict[str, BoundSlot]) -> str:
        if move.move_type == "social_greet":
            return "Hello." if situation.style.formality >= 0.65 else "Hi."
        if move.move_type == "social_farewell":
            return "Bye for now."
        if move.move_type == "phatic_response":
            return "I'm here and running normally. How are you doing?"
        if move.move_type == "answer":
            return self._answer(situation, slots)
        if move.move_type == "evidence_explanation":
            return self._evidence_explanation(situation)
        if move.move_type == "acknowledge_heard":
            return self._acknowledge_heard(situation)
        if move.move_type == "confirm_memory_write":
            return self._confirm_write(situation)
        if move.move_type == "honest_abstain":
            return self._abstain(situation)
        if move.move_type == "safety_refusal":
            return self._safety_refusal(situation)
        if move.move_type == "repair_prior_response":
            return "You're right, I missed that."
        if move.move_type == "clarify":
            return "Could you clarify what you mean?"
        if move.move_type == "deescalate":
            return "Let's take a step back."
        if move.move_type == "set_expectation":
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
            label = self._predicates.label_for(answer)
            if label in ("value", "has_property", ""):
                query_surface = getattr(
                    getattr(situation.semantic_program, "entry_instruction", None),
                    "surface", "",
                ) or ""
                label = self._predicates.label_from_surface(query_surface, fallback=label)
            return self._morph.sentence(self._linearizer.user_profile(label, answer.value))
        if obligation_kind in {"answer_self_capability", "answer_self_knowledge", "answer_self_model"}:
            return self._morph.sentence(answer.value)
        return self._morph.sentence(answer.value)

    def _acknowledge_heard(self, situation: ResponseSituation) -> str:
        echo = self._echo(situation)
        if echo and situation.style.detail > 0.65:
            return self._morph.sentence(f"got it, {echo}")
        return "Got it."

    def _confirm_write(self, situation: ResponseSituation) -> str:
        write = situation.write_outcome
        if write is None or not write.committed:
            return "Got it."
        echo = self._echo(situation)
        if echo:
            return self._morph.sentence(f"I've stored it: {echo}")
        return "I've stored that."

    def _abstain(self, situation: ResponseSituation) -> str:
        binding = situation.answer_binding or getattr(situation.evidence, "answer_binding", None)
        reason = getattr(binding, "abstention_reason", "") or getattr(situation.evidence, "abstention_reason", "")
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

    def _echo(self, situation: ResponseSituation) -> str:
        surface = self._slots.echo_surface(situation)
        surface = self._post.clean_echo(surface)
        surface = self._pronouns.shift_user_assertion_to_assistant_echo(surface)
        return surface

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
