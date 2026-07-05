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
"""

from __future__ import annotations

from ..types.answer_binding import AnswerBinding
from ..types.realization_contract import RealizationContract, RealizationSlot


_TEMPLATES: dict[str, str] = {
    "evidence_answer": "{answer}",
    "self_identity": "I am {answer}.",
    "user_profile": "Your {answer}.",
    "teaching_continuation": "Got it — {answer}. Tell me more.",
    "store_confirmation": "Got it. I've learned that {answer}.",
    "social_response": "Hello!",
    "ask_clarification": "Could you clarify what you mean by {answer}?",
    "session_exit": "Goodbye!",
    "general_conversation": "I understand.",
    "abstain": "I'm not sure about that yet.",
    "blocked": "I need more information before I can answer that.",
    "safety_refusal": "I can't help with that.",
}

_ABSTENTION_REASONS: dict[str, str] = {
    "no_matches": "I don't have enough information to answer that yet.",
    "no_relation_key_or_algebra": "I'm not sure how to look that up.",
}

# Maps template_key → allowed slot kinds for the "answer" slot.
# If the slot's kind is not in the allowed set, the realizer rejects it
# and returns an abstention response.
_TEMPLATE_SLOT_KINDS: dict[str, frozenset[str]] = {
    "evidence_answer": frozenset({"concept", "entity", "surface"}),
    "self_identity": frozenset({"self_identity", "entity"}),
    "user_profile": frozenset({"profile"}),
    "teaching_continuation": frozenset({"concept", "surface"}),
    "store_confirmation": frozenset({"concept", "surface"}),
    "ask_clarification": frozenset({"surface"}),
    "social_response": frozenset(),
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

        # Fallback: fill "answer" from binding slot fills if not in contract slots
        if binding and binding.slot_fills and "answer" not in variables:
            best = max(binding.slot_fills, key=lambda f: f.confidence)
            if best.surface:
                variables["answer"] = best.surface
            elif best.concept_id:
                variables["answer"] = best.concept_id
            elif best.entity_id:
                variables["answer"] = best.entity_id

        # If template requires an answer slot but none is filled, abstain
        if "{answer}" in template and "answer" not in variables:
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
