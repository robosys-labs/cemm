"""PrimitiveGoalComposer — map ObligationFrame to primitive response goals.

Deterministic mapping: obligation_kind + context → list of PrimitiveResponseGoal.
No candidate variation, no randomness. Just the right semantic force.
"""

from __future__ import annotations

from typing import Any

from .types import (
    PrimitiveResponseGoal,
    PRIMITIVE_GOALS,
    ResponseSituation,
)


# ── Greeting/farewell surface cues ─────────────────────────────────────

_GREETING_CUES = (
    "hello", "hi", "hey", "greetings", "howdy", "sup",
    "morning", "afternoon", "evening",
)

_FAREWELL_CUES = (
    "bye", "goodbye", "later", "cya", "see you",
    "see ya", "farewell", "good night", "goodnight",
)

_CHECKIN_CUES = (
    "how are you", "how do you do", "how's it going",
    "hows it going", "how are things", "how you doing",
    "how's your day", "hows your day", "what's up", "whats up",
    "how are you today",
)

_FRUSTRATION_CUES = (
    "dumb", "stupid", "useless", "broken",
    "suck", "worthless", "worse", "terrible", "awful",
)


def _entry_surface(situation: ResponseSituation) -> str:
    """Extract the entry instruction surface text."""
    program = situation.semantic_program
    if program is None:
        return ""
    entry = program.entry_instruction
    if entry is None:
        return ""
    return (entry.surface or "").lower()


def _is_greeting_surface(surface: str) -> bool:
    return any(cue in surface for cue in _GREETING_CUES)


def _is_farewell_surface(surface: str) -> bool:
    return any(cue in surface for cue in _FAREWELL_CUES)


def _is_checkin_surface(surface: str) -> bool:
    return any(cue in surface for cue in _CHECKIN_CUES)


def _is_frustration_surface(surface: str) -> bool:
    return any(cue in surface for cue in _FRUSTRATION_CUES)


class PrimitiveGoalComposer:
    """Compose primitive goals from the response situation.

    This is the semantic force layer: it decides WHAT communicative
    force to apply, not how to phrase it.
    """

    def compose(
        self,
        situation: ResponseSituation,
    ) -> list[PrimitiveResponseGoal]:
        obligation = situation.obligation_frame
        if obligation is None:
            return [PrimitiveResponseGoal(goal_type="assert", confidence=0.3)]

        kind = obligation.obligation_kind
        surface = _entry_surface(situation)
        binding = situation.answer_binding
        has_answer = binding is not None and binding.has_answer
        safety = situation.safety_frame

        # Safety takes absolute priority
        if safety is not None and safety.category != "none":
            return self._compose_safety(safety, kind, surface)

        # Map obligation kind to goals
        if kind == "exit":
            return [PrimitiveResponseGoal(goal_type="farewell", confidence=0.95)]

        if kind == "social_reply":
            return self._compose_social(surface, situation)

        if kind == "store_patch":
            return self._compose_store_patch(situation)

        if kind == "acknowledge_emotional_context":
            return self._compose_emotional(situation)

        if kind == "ask_clarification":
            return [PrimitiveResponseGoal(goal_type="query", confidence=0.8)]

        if kind == "repair":
            return [PrimitiveResponseGoal(goal_type="repair_self", confidence=0.85)]

        if kind in ("answer_concept", "answer_relation", "answer_self_model",
                    "answer_user_profile", "answer_self_identity",
                    "answer_self_capability", "answer_self_knowledge"):
            if has_answer:
                return [PrimitiveResponseGoal(goal_type="assert", confidence=0.85)]
            return [
                PrimitiveResponseGoal(goal_type="negate", confidence=0.6),
                PrimitiveResponseGoal(goal_type="hedge", confidence=0.5),
            ]

        if kind == "continue_teaching":
            return [PrimitiveResponseGoal(goal_type="acknowledge", confidence=0.8)]

        if kind == "abstain_policy":
            return [
                PrimitiveResponseGoal(goal_type="negate", confidence=0.5),
                PrimitiveResponseGoal(goal_type="hedge", confidence=0.6),
            ]

        return [PrimitiveResponseGoal(goal_type="assert", confidence=0.3)]

    def _compose_safety(
        self,
        safety: Any,
        kind: str,
        surface: str,
    ) -> list[PrimitiveResponseGoal]:
        goals = [PrimitiveResponseGoal(goal_type="refuse", confidence=0.95)]
        goals.append(PrimitiveResponseGoal(goal_type="deescalate", confidence=0.85))
        return goals

    def _compose_social(
        self,
        surface: str,
        situation: ResponseSituation,
    ) -> list[PrimitiveResponseGoal]:
        goals: list[PrimitiveResponseGoal] = []

        if _is_greeting_surface(surface):
            goals.append(PrimitiveResponseGoal(goal_type="greet", confidence=0.9))
        elif _is_farewell_surface(surface):
            goals.append(PrimitiveResponseGoal(goal_type="farewell", confidence=0.9))
        elif _is_checkin_surface(surface):
            goals.append(PrimitiveResponseGoal(goal_type="reciprocate", confidence=0.8))
            goals.append(PrimitiveResponseGoal(goal_type="assert", confidence=0.6,
                                               slots={"self_state": "here and running normally"}))
        elif _is_frustration_surface(surface):
            goals.append(PrimitiveResponseGoal(goal_type="repair_self", confidence=0.7))
        else:
            # First-turn non-greeting: treat as greeting context
            if situation.is_first_turn:
                goals.append(PrimitiveResponseGoal(goal_type="greet", confidence=0.5))
                goals.append(PrimitiveResponseGoal(goal_type="acknowledge", confidence=0.6))
            else:
                goals.append(PrimitiveResponseGoal(goal_type="acknowledge", confidence=0.6))

        return goals

    def _compose_store_patch(
        self,
        situation: ResponseSituation,
    ) -> list[PrimitiveResponseGoal]:
        goals: list[PrimitiveResponseGoal] = []
        write = situation.write_outcome

        if write is not None and write.commit_status == "committed":
            goals.append(PrimitiveResponseGoal(goal_type="acknowledge", confidence=0.85))
            goals.append(PrimitiveResponseGoal(goal_type="confirm_write", confidence=0.9))
        else:
            # Patch proposed but not committed — just acknowledge hearing
            goals.append(PrimitiveResponseGoal(goal_type="acknowledge", confidence=0.75))

        return goals

    def _compose_emotional(
        self,
        situation: ResponseSituation,
    ) -> list[PrimitiveResponseGoal]:
        goals: list[PrimitiveResponseGoal] = []
        goals.append(PrimitiveResponseGoal(goal_type="acknowledge", confidence=0.8))

        # Check affordance predictions for evaluation shift
        obligation = situation.obligation_frame
        if obligation is not None:
            preds = obligation.context.get("affordance_predictions", [])
            for pred in preds:
                effect = getattr(pred, "effect_type", "")
                if effect == "evaluation_shift":
                    patch_tmpl = getattr(pred, "predicted_patch_template", {})
                    shift = patch_tmpl.get("affect_shift", "")
                    if "positive" in shift:
                        goals.append(PrimitiveResponseGoal(
                            goal_type="assert", confidence=0.6,
                            slots={"evaluation": "appreciation"},
                        ))
                    elif "negative" in shift:
                        goals.append(PrimitiveResponseGoal(
                            goal_type="assert", confidence=0.6,
                            slots={"evaluation": "concern"},
                        ))
                    break

        return goals
