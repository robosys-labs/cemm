"""English renderer for language-neutral realization units."""

from __future__ import annotations

from .base import BaseRenderer
from ..types import RealizationUnit


class EnglishRenderer(BaseRenderer):
    language_code = "en"
    RELATION_LABELS = {
        "identity.name": "name", "identity.full_name": "full name",
        "identity.email": "email", "physical.age": "age",
        "has_name": "name", "has_age": "age", "has_alias": "alias",
        "has_role": "role", "has_property": "value",
        "located_in": "location", "from_place": "origin",
    }

    def render_unit(self, unit: RealizationUnit) -> str:
        match unit.unit_type:
            case "social_greet":
                return "Hello." if unit.style.get("formality", 0.5) >= 0.65 else "Hi."
            case "social_farewell":
                return "Bye for now."
            case "phatic_response":
                # Realizes operational status using vocabulary present in the
                # semantic language pack; no opaque unsupported adverb.
                return "I'm here and working. How are you doing?"
            case "repair_prior_response":
                return "You're right, I missed that."
            case "clarify":
                token = str(unit.features.get("unknown_token", "") or "").strip()
                return f"What does '{token}' mean here?" if token else "Could you clarify that?"
            case "deescalate":
                return "Let's take a step back."
            case "set_expectation":
                return "I'm checking that."
            case "acknowledgment":
                return "Got it."
            case "user_profile_assertion":
                return self.sentence(f"your {self._label(unit)} is {unit.object_value}")
            case "self_identity_assertion":
                return self.sentence(f"I am {unit.object_value}")
            case "capability_assertion":
                values = unit.object_values or ([unit.object_value] if unit.object_value else [])
                return self.sentence(f"I can {self._coordinate(values)}") if values else ""
            case "generic_assertion":
                values = unit.object_values or ([unit.object_value] if unit.object_value else [])
                return self.sentence(self._coordinate(values))
            case "memory_confirmation":
                if not unit.write_committed:
                    return "I couldn't store that as requested."
                return self.sentence(f"I've stored it: {unit.object_value}") if unit.object_value else "I've stored that."
            case "honest_abstain":
                return self._abstain(unit)
            case "safety_refusal":
                return self._safety_refusal(unit)
            case "evidence_explanation":
                return "(via: " + " -> ".join(unit.evidence_path) + ")" if unit.evidence_path else ""
        return ""

    def _label(self, unit: RealizationUnit) -> str:
        label = unit.label_key or unit.relation_key or "value"
        return self.RELATION_LABELS.get(label, self.clean_label(label))

    @staticmethod
    def _coordinate(values: list[str]) -> str:
        values = [value for value in dict.fromkeys(values) if value]
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return ", ".join(values[:-1]) + f", and {values[-1]}"

    @staticmethod
    def _abstain(unit: RealizationUnit) -> str:
        reason = unit.abstention_reason
        if str(reason).startswith("blocked"):
            return "I can't answer that from the available evidence."
        if reason in {"no_matches", "unresolved_query_target"}:
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
