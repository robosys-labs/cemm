"""SemanticRealizer — turn RealizationContract + AnswerBinding into response text.

This is the semantic equivalent of RealizationPipeline, but data-driven
from the RealizationContract instead of hardcoded if/else chains on
intent strings. The realizer uses template patterns derived from the
contract's template_key, fills variables from typed RealizationSlots,
validates slot kind compatibility, and appends explanation paths when
required.

Slot kind validation prevents the "Your name is good" bug: a mood value
(slot_kind="surface") cannot fill a name slot (template expects
"self_identity" or "profile").

Templates are loaded from cemm/data/response_templates.json to keep
linguistic data out of code.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..types.answer_binding import AnswerBinding
from ..types.realization_contract import RealizationContract, RealizationSlot


def _load_templates() -> dict[str, str]:
    """Load language-indexed templates from response_templates.json."""
    path = Path(__file__).parent.parent / "data" / "response_templates.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("en", {})


_TEMPLATES: dict[str, str] = _load_templates()

_ABSTENTION_REASONS: dict[str, str] = {
    "no_matches": "I don't have enough information to answer that yet.",
    "no_relation_key_or_algebra": "I'm not sure how to look that up.",
    "safety_policy": "I cannot help with that request.",
}

_TEMPLATE_FALLBACK: dict[str, str] = {
    "teaching_continuation": "teaching_acknowledgment",
    "store_confirmation": "store_acknowledgment",
}

# Maps template_key → allowed slot kinds for the "answer" slot.
# If the slot's kind is not in the allowed set, the realizer rejects it
# and returns an abstention response.
_TEMPLATE_SLOT_KINDS: dict[str, frozenset[str]] = {
    "evidence_answer": frozenset({"concept", "entity", "surface"}),
    "self_identity": frozenset({"self_identity", "entity"}),
    "user_profile": frozenset({"profile"}),
    "teaching_continuation": frozenset({"concept", "surface", "profile"}),
    "teaching_acknowledgment": frozenset(),
    "store_confirmation": frozenset({"concept", "surface"}),
    "store_acknowledgment": frozenset(),
    "ask_clarification": frozenset({"surface"}),
    "social_response": frozenset(),
    "emotional_response": frozenset({"surface"}),
    "emotional_acknowledgment": frozenset({"surface"}),
    "session_exit": frozenset(),
    "general_conversation": frozenset(),
    "abstain": frozenset(),
    "blocked": frozenset(),
    "safety_refusal": frozenset(),
}


class SemanticRealizer:
    def realize(
        self,
        contract: RealizationContract,
        binding: AnswerBinding | None = None,
    ) -> str:
        if contract.abstention_reason:
            return _ABSTENTION_REASONS.get(
                contract.abstention_reason,
                _TEMPLATES.get(contract.template_key, "I'm not sure about that yet."),
            )

        template = _TEMPLATES.get(contract.template_key, _TEMPLATES["general_conversation"])

        # Build variables from typed slots with kind validation
        variables: dict[str, str] = {}
        allowed_kinds = _TEMPLATE_SLOT_KINDS.get(contract.template_key, frozenset())

        for key, slot in contract.slots.items():
            if allowed_kinds and key == "answer" and slot.slot_kind not in allowed_kinds:
                continue
            variables[key] = slot.value

        # If template requires an answer slot but none is filled,
        # use fallback template or abstain
        if "{answer}" in template and "answer" not in variables:
            fallback_key = _TEMPLATE_FALLBACK.get(contract.template_key)
            if fallback_key:
                return _TEMPLATES.get(fallback_key, _TEMPLATES["abstain"])
            return _TEMPLATES["abstain"]

        try:
            text = template.format(**variables)
        except KeyError:
            text = template

        if contract.explanation_required and binding and binding.explanation_paths:
            longest = max(binding.explanation_paths, key=len)
            if len(longest) > 1:
                text += " (via: " + " → ".join(longest) + ")"

        return text
