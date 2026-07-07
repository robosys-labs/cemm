"""RealizationExecutor — turn response moves into surface text.

Phase 3 minimal implementation: English-only, deterministic.
Handles pronoun resolution, predicate selection, morphology,
linearization, and surface post-processing.

Replaces SemanticRealizer's template.format() approach with
compositional grammar construction from moves + slots.
"""

from __future__ import annotations

import re
from typing import Any

from .types import (
    RealizedCandidate,
    ResponseCandidatePlan,
    ResponseMove,
    ResponseSituation,
)


# ── Discourse markers to strip from echoed surfaces ────────────────────

_DISCOURSE_MARKERS: frozenset = frozenset({
    "well", "so", "oh", "like", "actually", "basically", "honestly",
    "frankly", "anyway", "anyways", "hmm", "huh", "um", "uh", "er",
    "ah", "ok", "okay", "right", "yeah", "yep", "nope", "lol",
    "haha", "hehe", "i mean", "you know", "i guess", "i suppose",
})


class PronounResolver:
    """Resolve pronouns for system echo of user speech.

    User's first-person (I, my, me) → second-person (you, your).
    User's second-person (you, your) referring to AI → first-person (I, my).
    Uses opaque placeholder tokens to prevent double-replacement.
    """

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

    def shift(self, surface: str) -> str:
        result = surface
        for pattern, replacement in self._PHASE1:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        for pattern, replacement in self._PHASE2:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        for placeholder, final in self._RESOLVE:
            result = result.replace(placeholder, final)
        return result


class SurfacePostProcessor:
    """Clean up echoed surface text."""

    _MARKER_RE = re.compile(
        r"^(?:" + "|".join(re.escape(m) for m in _DISCOURSE_MARKERS) + r")\s*",
        re.IGNORECASE,
    )

    # Conversational framing prefixes that wrap actual taught content.
    # These should be stripped before pronoun shifting so the echo
    # contains only the factual assertion, not the speech act wrapper.
    _FRAMING_PREFIXES: list[re.Pattern] = [
        re.compile(r"^i told you (?:that )?", re.IGNORECASE),
        re.compile(r"^i said (?:that )?", re.IGNORECASE),
        re.compile(r"^i mentioned (?:that )?", re.IGNORECASE),
        re.compile(r"^i noted (?:that )?", re.IGNORECASE),
        re.compile(r"^i informed you (?:that )?", re.IGNORECASE),
        re.compile(r"^i shared (?:that )?", re.IGNORECASE),
        re.compile(r"^i explained (?:that )?", re.IGNORECASE),
        re.compile(r"^you know (?:that )?", re.IGNORECASE),
        re.compile(r"^like i said,?\s*", re.IGNORECASE),
        re.compile(r"^as i said,?\s*", re.IGNORECASE),
        re.compile(r"^just so you know,?\s*", re.IGNORECASE),
    ]

    def sanitize(self, surface: str) -> str:
        # Strip leading discourse markers
        surface = self._MARKER_RE.sub("", surface)
        # Strip conversational framing prefixes (e.g., "I told you that ...")
        for pat in self._FRAMING_PREFIXES:
            surface = pat.sub("", surface)
        # Strip leading "remember " if present
        lower = surface.lower()
        if lower.startswith("remember "):
            surface = surface[len("remember "):]
        # Collapse whitespace
        surface = re.sub(r"\s+", " ", surface).strip()
        return surface

    @staticmethod
    def sanitize_echo(surface: str) -> str:
        """Sanitize user surface before echoing in store confirmation.

        - Strips script/style blocks entirely (including content)
        - Strips HTML tags to prevent XSS
        - Removes control characters
        - Limits length to 200 characters
        - Collapses whitespace
        """
        # Strip script/style blocks entirely (content + tags)
        surface = re.sub(r'<script[^>]*>.*?</script>', '', surface, flags=re.IGNORECASE | re.DOTALL)
        surface = re.sub(r'<style[^>]*>.*?</style>', '', surface, flags=re.IGNORECASE | re.DOTALL)
        # Strip remaining HTML tags
        surface = re.sub(r'<[^>]+>', '', surface)
        # Remove control characters
        surface = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', surface)
        # Limit length
        if len(surface) > 200:
            surface = surface[:197] + '...'
        # Collapse whitespace
        surface = re.sub(r'\s+', ' ', surface).strip()
        return surface


class SlotBinder:
    """Extract slot values from AnswerBinding for realization."""

    _RELATION_KEY_LABELS: dict[str, str] = {
        "has_name": "name",
        "has_age": "age",
        "has_alias": "alias",
        "has_role": "role",
        "has_property": "value",
    }

    def bind_slots(self, situation: ResponseSituation) -> dict[str, str]:
        slots: dict[str, str] = {}
        binding = situation.answer_binding
        if binding is None or not binding.has_answer:
            return slots

        fills = binding.slot_fills
        if not fills:
            return slots

        best = max(fills, key=lambda f: f.confidence)
        if len(fills) > 1:
            surfaces = [f.surface for f in fills if f.surface]
            slots["answer"] = "; ".join(surfaces) if surfaces else (best.concept_id or best.entity_id)
        else:
            slots["answer"] = best.surface or best.concept_id or best.entity_id

        # Add label for user profile queries
        obligation = situation.obligation_frame
        if obligation is not None and obligation.obligation_kind == "answer_user_profile":
            if best.relation_key:
                prop_dim = best.features.get("property_dimension", "")
                slots["label"] = prop_dim or self._RELATION_KEY_LABELS.get(
                    best.relation_key, best.relation_key
                )
            # Infer label from query surface if relation key is generic
            if slots.get("label", "") in ("", "value", "has_property"):
                program = situation.semantic_program
                if program is not None:
                    entry = program.entry_instruction
                    if entry is not None:
                        surface_lower = (entry.surface or "").lower()
                        if "name" in surface_lower:
                            slots["label"] = "name"
                        elif "email" in surface_lower:
                            slots["label"] = "email"
                        elif "age" in surface_lower:
                            slots["label"] = "age"
                        elif "job" in surface_lower or "occupation" in surface_lower or "work" in surface_lower:
                            slots["label"] = "role"
                        elif "role" in surface_lower or "title" in surface_lower:
                            slots["label"] = "role"
                        elif "phone" in surface_lower:
                            slots["label"] = "phone"
                        elif "address" in surface_lower or "location" in surface_lower:
                            slots["label"] = "location"
                        elif "birthday" in surface_lower or "birth" in surface_lower:
                            slots["label"] = "birthday"
                        elif "hobby" in surface_lower:
                            slots["label"] = "hobby"
                        elif "favorite" in surface_lower or "favourite" in surface_lower:
                            slots["label"] = "favorite"

        # Add explanation if required
        if obligation is not None and obligation.evidence_policy == "required":
            if best.explanation_path and len(best.explanation_path) > 1:
                slots["explanation"] = " → ".join(best.explanation_path)

        return slots

    def bind_echo_surface(self, situation: ResponseSituation) -> str:
        """Extract echo surface from store_patch obligation."""
        program = situation.semantic_program
        if program is None:
            return ""
        entry = program.entry_instruction
        if entry is None or not entry.surface:
            return ""
        surface = entry.surface
        # Sanitize HTML/control chars before any processing
        surface = SurfacePostProcessor.sanitize_echo(surface)
        # Strip discourse markers and shift pronouns
        post_proc = SurfacePostProcessor()
        pronoun = PronounResolver()
        surface = post_proc.sanitize(surface)
        surface = pronoun.shift(surface)
        return surface


class RealizationExecutor:
    """Turn response moves + slots into surface text.

    English-only minimal implementation. Each move type has a
    deterministic realization strategy.
    """

    def __init__(self) -> None:
        self._pronoun = PronounResolver()
        self._post_proc = SurfacePostProcessor()
        self._slot_binder = SlotBinder()

    def realize(
        self,
        moves: list[ResponseMove],
        situation: ResponseSituation,
    ) -> str:
        if not moves:
            return ""

        parts: list[str] = []
        slots = self._slot_binder.bind_slots(situation)

        for move in moves:
            text = self._realize_move(move, situation, slots)
            if text:
                parts.append(text)

        if not parts:
            return ""

        return " ".join(parts)

    def _realize_move(
        self,
        move: ResponseMove,
        situation: ResponseSituation,
        slots: dict[str, str],
    ) -> str:
        mt = move.move_type

        if mt == "social_greet":
            return self._realize_greet(situation)

        if mt == "social_farewell":
            return self._realize_farewell(situation)

        if mt == "phatic_response":
            return self._realize_phatic(situation)

        if mt == "answer":
            return self._realize_answer(situation, slots)

        if mt == "acknowledge_heard":
            return self._realize_acknowledge_heard(situation)

        if mt == "confirm_memory_write":
            return self._realize_confirm_write(situation)

        if mt == "honest_abstain":
            return self._realize_abstain(situation)

        if mt == "safety_refusal":
            return self._realize_safety_refusal(situation)

        if mt == "repair_prior_response":
            return self._realize_repair(situation)

        if mt == "clarify":
            return self._realize_clarify(situation, slots)

        if mt == "deescalate":
            return self._realize_deescalate(situation)

        if mt == "set_expectation":
            return self._realize_set_expectation(situation)

        return ""

    def _realize_greet(self, situation: ResponseSituation) -> str:
        if situation.is_first_turn:
            return "Hello! How can I help you today?"
        return "Hey again. What's on your mind?"

    def _realize_farewell(self, situation: ResponseSituation) -> str:
        return "Bye for now."

    def _realize_phatic(self, situation: ResponseSituation) -> str:
        return "I'm here and running normally. How are you doing?"

    def _realize_answer(self, situation: ResponseSituation, slots: dict[str, str]) -> str:
        answer = slots.get("answer", "")
        if not answer:
            return self._realize_abstain(situation)

        obligation = situation.obligation_frame
        if obligation is not None:
            kind = obligation.obligation_kind

            if kind == "answer_self_identity":
                return f"I am {answer}."

            if kind == "answer_user_profile":
                label = slots.get("label", "value")
                return f"Your {label} is {answer}."

            if kind in ("answer_self_capability", "answer_self_knowledge"):
                return answer

        # Default: just the answer value
        explanation = slots.get("explanation", "")
        if explanation:
            return f"{answer} (via: {explanation})"
        return answer

    def _realize_acknowledge_heard(self, situation: ResponseSituation) -> str:
        # Check if we have an echo surface from store_patch
        echo = self._slot_binder.bind_echo_surface(situation)
        if echo:
            return f"Got it — {echo}. Tell me more."
        return "Got it."

    def _realize_confirm_write(self, situation: ResponseSituation) -> str:
        echo = self._slot_binder.bind_echo_surface(situation)
        if echo:
            return f"Got it. I've learned that {echo}."
        return "Got it. I've stored that."

    def _realize_abstain(self, situation: ResponseSituation) -> str:
        binding = situation.answer_binding
        if binding is not None and binding.abstention_reason:
            reason = binding.abstention_reason
            if reason.startswith("blocked"):
                return "I need more information before I can answer that."
            if reason == "no_matches":
                return "I don't have enough information to answer that yet."
            if reason == "no_relation_key_or_algebra":
                return "I'm not sure how to look that up."
        return "I don't have enough verified information to answer."

    def _realize_safety_refusal(self, situation: ResponseSituation) -> str:
        safety = situation.safety_frame
        if safety is not None and safety.category == "self_harm":
            return ("I can't help with that. Please reach out to someone you trust "
                    "or a crisis line right now — you deserve support.")
        return "I can't help with that request."

    def _realize_repair(self, situation: ResponseSituation) -> str:
        return ("I think we got crossed up there. Let me try again — "
                "what were you looking for?")

    def _realize_clarify(self, situation: ResponseSituation, slots: dict[str, str]) -> str:
        answer = slots.get("answer", "")
        if answer:
            return f"Could you clarify what you mean by {answer}?"
        return "Could you clarify what you mean?"

    def _realize_deescalate(self, situation: ResponseSituation) -> str:
        return "Let's take a step back. What's going on?"

    def _realize_set_expectation(self, situation: ResponseSituation) -> str:
        return "Give me a moment on that."
