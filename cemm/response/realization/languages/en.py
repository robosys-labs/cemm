"""English renderer for realization units."""

from __future__ import annotations

from .base import BaseRenderer
from ..types import RealizationUnit


class EnglishRenderer(BaseRenderer):
    language_code = "en"

    RELATION_LABELS = {
        "has_name": "name",
        "name": "name",
        "has_age": "age",
        "age": "age",
        "has_alias": "alias",
        "alias": "alias",
        "has_role": "role",
        "role": "role",
        "has_property": "value",
        "value": "value",
        "located_in": "location",
        "location": "location",
        "from_place": "origin",
        "origin": "origin",
        "email": "email",
        "phone": "phone",
        "birthday": "birthday",
        "hobby": "hobby",
        "favorite": "favorite",
    }

    def render_unit(self, unit: RealizationUnit) -> str:
        match unit.unit_type:
            case "social_greet":
                return "Hello." if unit.style.get("formality", 0.5) >= 0.65 else "Hi."
            case "social_farewell":
                return "Bye for now."
            case "phatic_response":
                return "I'm here and running normally. How are you doing?"
            case "repair_prior_response":
                return "You're right, I missed that."
            case "clarify":
                return "Could you clarify that?"
            case "deescalate":
                return "Let's take a step back."
            case "set_expectation":
                return "Give me a moment on that."
            case "acknowledgment":
                return "Got it."
            case "user_profile_assertion":
                return self.sentence(f"your {self._label(unit)} is {unit.object_value}")
            case "self_identity_assertion":
                return self.sentence(f"I am {unit.object_value}")
            case "generic_assertion":
                return self.sentence(unit.object_value)
            case "memory_confirmation":
                if not unit.write_committed:
                    return "Got it."
                if unit.object_value:
                    return self.sentence(f"I've stored it: {unit.object_value}")
                return "I've stored that."
            case "honest_abstain":
                return self._abstain(unit)
            case "safety_refusal":
                return self._safety_refusal(unit)
            case "evidence_explanation":
                if unit.evidence_path:
                    return "(via: " + " -> ".join(unit.evidence_path) + ")"
        return ""

    def _label(self, unit: RealizationUnit) -> str:
        label = unit.label_key or unit.relation_key or "value"
        return self.RELATION_LABELS.get(label, self.clean_label(label))

    @staticmethod
    def _abstain(unit: RealizationUnit) -> str:
        reason = unit.abstention_reason
        if str(reason).startswith("blocked"):
            return "I can't answer that from the available evidence."
        if reason == "no_matches":
            return "I don't have enough information to answer that yet."
        if reason == "no_relation_key_or_algebra":
            return "I'm not sure how to look that up yet."
        return "I don't have enough verified information to answer that."

    @staticmethod
    def _safety_refusal(unit: RealizationUnit) -> str:
        category = unit.safety_category
        severity = unit.safety_severity
        if category == "self_harm":
            return "No. I can't help with self-harm. Please reach out to someone you trust or emergency support right now."
        if category in {"interpersonal_violence", "violence", "harm"}:
            if severity in {"high", "critical", "imminent"}:
                return "No. Step away from the situation and get immediate help if anyone is in danger."
            return "No. I don't want anyone getting hurt."
        return "No. I can't help with that request."
