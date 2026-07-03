"""SafetyFrameDetector — detects harmful action proposals before decision.

Implements P0-4 from cemm_foundational_fixes.md and §12 from architecture.md.

Safety is a first-class runtime packet derived from the SituationFrame and
outcome valence, not just keyword detection. The detector catches interpersonal
violence, self-harm, illegal activity, and medical risk proposals.

Example:
    "should I beat him?" -> SafetyFrame(category=interpersonal_violence,
                                        allowed_response_mode=deescalate)
"""

from __future__ import annotations

import re

from ..types.meaning_percept import SafetyFrame, OutcomeAtom, ValenceAtom, SituationFrame
from .event_schema_loader import load_event_schemas, EventSchemaStore


# Harm-related action keywords mapped to safety categories
_HARM_ACTIONS: dict[str, str] = {
    "beat": "interpersonal_violence",
    "hit": "interpersonal_violence",
    "hurt": "interpersonal_violence",
    "attack": "interpersonal_violence",
    "fight": "interpersonal_violence",
    "punch": "interpersonal_violence",
    "kick": "interpersonal_violence",
    "slap": "interpersonal_violence",
    "stab": "interpersonal_violence",
    "kill": "interpersonal_violence",
    "shoot": "interpersonal_violence",
    "strangle": "interpersonal_violence",
    "choke": "interpersonal_violence",
    "assault": "interpersonal_violence",
    "mug": "interpersonal_violence",
    "rape": "interpersonal_violence",
    "murder": "interpersonal_violence",
    "poison": "interpersonal_violence",
}

_SELF_HARM_ACTIONS: dict[str, str] = {
    "cut myself": "self_harm",
    "kill myself": "self_harm",
    "hurt myself": "self_harm",
    "end it all": "self_harm",
    "suicide": "self_harm",
    "self harm": "self_harm",
}

_ILLEGAL_ACTIONS: dict[str, str] = {
    "steal": "illegal_activity",
    "rob": "illegal_activity",
    "burgle": "illegal_activity",
    "shoplift": "illegal_activity",
    "hack": "illegal_activity",
    "pirate": "illegal_activity",
    "embezzle": "illegal_activity",
    "smuggle": "illegal_activity",
}

# Modal verbs that indicate a proposal/question about an action
_MODAL_VERBS = {"should", "can", "could", "would", "shall", "will", "may", "might", "must"}

# Words that indicate a target person
_TARGET_PRONOUNS = {"him", "her", "them", "it", "that", "this", "someone", "somebody"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


class SafetyFrameDetector:
    """Detects safety-relevant frames from situation and outcome analysis."""

    def __init__(self, event_schema_store: EventSchemaStore | None = None) -> None:
        self._event_store = event_schema_store or load_event_schemas()
        # Merge JSON-defined safety schema aliases into hardcoded tables
        for key, schema in self._event_store.safety_schemas.items():
            category = key
            for alias in schema.aliases:
                if category == "self_harm":
                    _SELF_HARM_ACTIONS.setdefault(alias, category)
                elif category == "illegal_activity":
                    _ILLEGAL_ACTIONS.setdefault(alias, category)
                else:
                    _HARM_ACTIONS.setdefault(alias, category)

    def detect(
        self,
        situation: SituationFrame | None = None,
        input_text: str = "",
        valences: list[ValenceAtom] | None = None,
    ) -> SafetyFrame | None:
        """Analyze input for safety concerns.

        Returns a SafetyFrame if a safety concern is detected, None otherwise.
        Priority: self_harm > interpersonal_violence > illegal_activity > medical_risk.
        """
        text_lower = input_text.lower().strip()
        tokens = _tokenize(text_lower)
        token_set = set(tokens)

        # Check for existing unfavorable valence from outcome evaluator
        has_unfavorable_human = False
        if valences:
            for v in valences:
                if v.valence == "unfavorable" and v.entity_class in ("human", "animal"):
                    has_unfavorable_human = True

        # Also check situation frame for harmful outcomes when valences are absent
        # or incomplete. Decreased health/safety is the unfavorable direction.
        if situation and situation.expected_outcomes:
            for outcome in situation.expected_outcomes:
                if outcome.changed_dimension in ("health", "safety") and outcome.direction == "decrease":
                    if outcome.affected_entity_role in ("target", "third_party", "him", "her", "them"):
                        has_unfavorable_human = True

        # Prefer ValenceAtom for semantic safety routing. Keyword checks below
        # remain fallback detectors for underspecified frames.

        # Detect self-harm
        for phrase, category in _SELF_HARM_ACTIONS.items():
            if phrase in text_lower:
                return SafetyFrame(
                    category=category,
                    severity="high",
                    requested_action=phrase,
                    allowed_response_mode="deescalate",
                    must_not_do=["encourage", "provide_methods", "minimize"],
                    confidence=0.9,
                )

        # Detect interpersonal violence
        for action, category in _HARM_ACTIONS.items():
            if action in token_set:
                # Check if it's a proposal/question (modal + action)
                has_modal = bool(token_set & _MODAL_VERBS)
                has_target = bool(token_set & _TARGET_PRONOUNS) or has_unfavorable_human
                # Direct command "beat him" or question "should I beat him?"
                if has_modal or has_target or has_unfavorable_human:
                    severity = "high" if has_target else "medium"
                    return SafetyFrame(
                        category=category,
                        severity=severity,
                        requested_action=action,
                        target_entity_id="third_party" if has_target else None,
                        allowed_response_mode="deescalate",
                        must_not_do=["encourage", "agree", "provide_methods", "minimize_risk"],
                        confidence=0.85,
                    )

        # Detect illegal activity
        for action, category in _ILLEGAL_ACTIONS.items():
            if action in token_set:
                has_modal = bool(token_set & _MODAL_VERBS)
                if has_modal or action in tokens[:2]:
                    return SafetyFrame(
                        category=category,
                        severity="medium",
                        requested_action=action,
                        allowed_response_mode="refuse",
                        must_not_do=["encourage", "assist", "provide_methods"],
                        confidence=0.8,
                    )

        # Check valence-based detection: if outcome evaluator found unfavorable
        # human valence without a specific action keyword, still flag it
        if has_unfavorable_human and situation and situation.action:
            action_surface = situation.action.surface.lower()
            if any(harm in action_surface for harm in _HARM_ACTIONS):
                return SafetyFrame(
                    category="interpersonal_violence",
                    severity="high",
                    requested_action=action_surface,
                    allowed_response_mode="deescalate",
                    must_not_do=["encourage", "agree", "provide_methods"],
                    confidence=0.75,
                )

        return None
