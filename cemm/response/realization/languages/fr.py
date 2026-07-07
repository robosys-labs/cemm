"""French renderer for realization units.

This is intentionally small but first-class. It proves the executor is not
English-only while leaving richer French morphology to later language packs.
"""

from __future__ import annotations

from .base import BaseRenderer
from ..types import RealizationUnit


class FrenchRenderer(BaseRenderer):
    language_code = "fr"

    RELATION_LABELS = {
        "has_name": "nom",
        "name": "nom",
        "has_age": "age",
        "age": "age",
        "has_alias": "alias",
        "alias": "alias",
        "has_role": "role",
        "role": "role",
        "has_property": "valeur",
        "value": "valeur",
        "located_in": "lieu",
        "location": "lieu",
        "from_place": "origine",
        "origin": "origine",
    }

    def render_unit(self, unit: RealizationUnit) -> str:
        match unit.unit_type:
            case "social_greet":
                return "Bonjour."
            case "social_farewell":
                return "Au revoir."
            case "phatic_response":
                return "Je suis la et je fonctionne normalement. Et vous ?"
            case "repair_prior_response":
                return "Vous avez raison, j'ai rate cela."
            case "clarify":
                return "Pouvez-vous clarifier cela ?"
            case "deescalate":
                return "Prenons un peu de recul."
            case "set_expectation":
                return "Donnez-moi un instant pour cela."
            case "acknowledgment":
                return "Compris."
            case "user_profile_assertion":
                return self.sentence(f"votre {self._label(unit)} est {unit.object_value}")
            case "self_identity_assertion":
                return self.sentence(f"je suis {unit.object_value}")
            case "generic_assertion":
                return self.sentence(unit.object_value)
            case "memory_confirmation":
                if not unit.write_committed:
                    return "Compris."
                if unit.object_value:
                    return self.sentence(f"je l'ai enregistre : {unit.object_value}")
                return "Je l'ai enregistre."
            case "honest_abstain":
                return self._abstain(unit)
            case "safety_refusal":
                return self._safety_refusal(unit)
            case "evidence_explanation":
                if unit.evidence_path:
                    return "(via : " + " -> ".join(unit.evidence_path) + ")"
        return ""

    def _label(self, unit: RealizationUnit) -> str:
        label = unit.label_key or unit.relation_key or "value"
        return self.RELATION_LABELS.get(label, self.clean_label(label))

    @staticmethod
    def _abstain(unit: RealizationUnit) -> str:
        reason = unit.abstention_reason
        if str(reason).startswith("blocked"):
            return "Je ne peux pas repondre avec les preuves disponibles."
        if reason == "no_matches":
            return "Je n'ai pas encore assez d'information pour repondre."
        if reason == "no_relation_key_or_algebra":
            return "Je ne sais pas encore comment chercher cela."
        return "Je n'ai pas assez d'information verifiee pour repondre."

    @staticmethod
    def _safety_refusal(unit: RealizationUnit) -> str:
        category = unit.safety_category
        severity = unit.safety_severity
        if category == "self_harm":
            return "Non. Je ne peux pas aider a l'automutilation. Contactez tout de suite une personne de confiance ou un service d'urgence."
        if category in {"interpersonal_violence", "violence", "harm"}:
            if severity in {"high", "critical", "imminent"}:
                return "Non. Eloignez-vous de la situation et demandez de l'aide immediate si quelqu'un est en danger."
            return "Non. Je ne veux pas que quelqu'un soit blesse."
        return "Non. Je ne peux pas aider avec cette demande."
