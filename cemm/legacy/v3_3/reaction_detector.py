"""ReactionDetector — lightweight pre-classification reaction detection.

Detects that the current input is a reaction to the previous assistant output
before normal classification. This is split from ErrorAttributionEngine because
the full engine needs ConversationActPacket, DecisionPacket, and
SemanticAnswerGraph — none of which exist before classification. The
ReactionDetector only needs MeaningPerceptPacket and DiscourseStateStack.

Detection signals (structural, not alias-based):
- short user turn (< 5 tokens) + previous assistant output exists
- StateAtom(confused/lost/frustrated) in percept
- punctuation ??? or ?! in signal
- previous response was low confidence or generic response mode
- affect marker in percept (frustration, repair)

Prediction error framework:
  If previous response was evidence_answer → expected: follow-up, ack, topic shift
  If previous response was social_response → expected: continuation, new topic, reciprocal
  If previous response was general_conversation → expected: continuation, new topic, clarification
  "what???" matches NONE of these → error signal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...types.meaning_percept import MeaningPerceptPacket
from ...types.context_kernel import DiscourseStateStack


@dataclass
class ReactionSignal:
    """Lightweight signal that the current input reacts to a previous turn."""
    is_reaction: bool = False
    target_turn_id: str = ""
    reaction_kind: str = ""  # confusion, frustration, correction, meta_critique
    likely_error_type: str = ""  # response_too_generic, intent_misclassified, ...
    confidence: float = 0.5
    evidence: dict[str, Any] = field(default_factory=dict)


# Expected follow-up types per previous response mode
_EXPECTED_FOLLOW_UPS: dict[str, set[str]] = {
    "evidence_answer": {"follow_up_question", "acknowledgment", "topic_shift", "elaboration"},
    "social_response": {"continuation", "new_topic", "reciprocal", "acknowledgment"},
    "general_conversation": {"continuation", "new_topic", "clarification", "acknowledgment"},
    "capability_summary": {"follow_up_question", "acknowledgment", "topic_shift"},
    "teaching_prompt": {"teaching_input", "acknowledgment", "topic_shift"},
    "unknown_entity_response": {"teaching_input", "acknowledgment", "topic_shift"},
    "repair_response": {"acknowledgment", "topic_shift", "continuation"},
    "creative_response": {"acknowledgment", "topic_shift", "continuation"},
}

# State keys that signal confusion/frustration
_CONFUSION_STATES = {"confused", "lost", "frustrated", "angry", "annoyed"}

# Affect markers that signal repair need
_REPAIR_AFFECTS = {"frustration", "confusion", "repair", "annoyance"}


class ReactionDetector:
    """Detects reactions to previous assistant output before classification."""

    def detect(
        self,
        percept: MeaningPerceptPacket | None,
        discourse_stack: DiscourseStateStack | None,
    ) -> ReactionSignal:
        signal = ReactionSignal()

        if not percept or not discourse_stack or not discourse_stack.entries:
            return signal

        last_entry = discourse_stack.last_entry
        if not last_entry or not last_entry.assistant_text:
            return signal

        # If this is the first turn, no reaction possible
        if last_entry.status == "completed" and not last_entry.assistant_text:
            return signal

        evidence: dict[str, Any] = {}
        reaction_score = 0.0

        # Signal 1: Short user turn (< 5 tokens) after assistant output
        token_count = len(percept.tokens) if percept.tokens else len(percept.raw_text.split())
        if token_count < 5:
            evidence["short_turn"] = True
            evidence["token_count"] = token_count
            reaction_score += 0.25

        # Signal 2: Confusion/frustration state atoms in percept
        confusion_states = [
            s for s in percept.states
            if s.state_key in _CONFUSION_STATES
        ]
        if confusion_states:
            evidence["confusion_states"] = [s.state_key for s in confusion_states]
            reaction_score += 0.3

        # Signal 3: Heavy question/exclamation punctuation
        raw = percept.raw_text or ""
        q_density = raw.count("?") + raw.count("!")
        if q_density >= 2:
            evidence["punctuation_density"] = q_density
            reaction_score += 0.2

        # Signal 4: Previous response was low confidence or generic
        prev_mode = last_entry.assistant_response_mode
        # Treat empty mode as general_conversation — it means the response
        # wasn't tagged with a specific mode, which is generic by default.
        if not prev_mode:
            prev_mode = "general_conversation"
        if prev_mode in ("general_conversation", "unknown_entity_response"):
            evidence["prev_generic_response"] = True
            evidence["prev_response_mode"] = prev_mode
            reaction_score += 0.15

        # Signal 5: Affect markers indicating repair
        repair_affects = [
            a for a in percept.affect_markers
            if any(marker in _REPAIR_AFFECTS for marker in [a.get("type", ""), a.get("key", ""), a.get("label", "")])
        ]
        if repair_affects:
            evidence["repair_affects"] = [a.get("type", a.get("key", a.get("label", ""))) for a in repair_affects]
            reaction_score += 0.2

        # Signal 6: Prediction error — input doesn't match expected follow-up
        expected = _EXPECTED_FOLLOW_UPS.get(prev_mode, set())
        if expected and prev_mode:
            # If the turn is very short and has confusion markers, it's unlikely
            # to be a normal follow-up — this is a prediction error
            if token_count < 5 and (confusion_states or q_density >= 2):
                evidence["prediction_error"] = True
                evidence["expected_follow_ups"] = list(expected)
                reaction_score += 0.2

        # Determine reaction kind and likely error type
        if reaction_score >= 0.5:
            signal.is_reaction = True
            signal.target_turn_id = last_entry.turn_id
            signal.confidence = min(1.0, reaction_score)

            # Classify reaction kind
            if confusion_states and any(s.state_key == "frustrated" for s in confusion_states):
                signal.reaction_kind = "frustration"
                signal.likely_error_type = "intent_misclassified"
            elif confusion_states:
                signal.reaction_kind = "confusion"
                signal.likely_error_type = "response_too_generic"
            elif q_density >= 3:
                signal.reaction_kind = "confusion"
                signal.likely_error_type = "response_too_generic"
            elif repair_affects:
                signal.reaction_kind = "correction"
                signal.likely_error_type = "intent_misclassified"
            else:
                signal.reaction_kind = "meta_critique"
                signal.likely_error_type = "response_too_generic"

            signal.evidence = evidence

        return signal
