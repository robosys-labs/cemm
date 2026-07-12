"""French renderer for language-neutral realization units."""

from __future__ import annotations

from .base import BaseRenderer
from ..types import RealizationUnit


class FrenchRenderer(BaseRenderer):
    language_code = "fr"
    RELATION_LABELS = {
        "identity.name": "nom", "identity.full_name": "nom complet",
        "identity.email": "adresse e-mail", "physical.age": "âge",
        "has_name": "nom", "name": "nom", "has_age": "âge", "age": "âge",
        "has_alias": "alias", "alias": "alias", "has_role": "rôle",
        "role": "rôle", "has_property": "valeur", "value": "valeur",
        "located_in": "lieu", "location": "lieu", "from_place": "origine", "origin": "origine",
    }

    def render_unit(self, unit: RealizationUnit) -> str:
        match unit.unit_type:
            case "social_greet": return "Bonjour."
            case "social_farewell": return "Au revoir."
            case "phatic_response": return "Je suis là et je fonctionne. Et vous ?"
            case "repair_prior_response": return "Vous avez raison, j'ai manqué cela."
            case "clarify":
                token = str(unit.features.get("unknown_token", "") or "").strip()
                return f"Que signifie « {token} » ici ?" if token else "Pouvez-vous clarifier cela ?"
            case "deescalate": return "Prenons un peu de recul."
            case "set_expectation": return "Je vérifie cela."
            case "acknowledgment": return "Compris."
            case "user_profile_assertion": return self.sentence(f"votre {self._label(unit)} est {unit.object_value}")
            case "self_identity_assertion": return self.sentence(f"je suis {unit.object_value}")
            case "capability_assertion":
                values = unit.object_values or ([unit.object_value] if unit.object_value else [])
                return self.sentence(f"je peux {self._coordinate(values)}") if values else ""
            case "generic_assertion":
                values = unit.object_values or ([unit.object_value] if unit.object_value else [])
                return self.sentence(self._coordinate(values))
            case "memory_confirmation":
                if not unit.write_committed: return "Je n'ai pas pu l'enregistrer comme demandé."
                return self.sentence(f"je l'ai enregistré : {unit.object_value}") if unit.object_value else "Je l'ai enregistré."
            case "honest_abstain": return self._abstain(unit)
            case "safety_refusal": return self._safety_refusal(unit)
            case "evidence_explanation": return "(via : " + " -> ".join(unit.evidence_path) + ")" if unit.evidence_path else ""
        return ""

    def _label(self, unit: RealizationUnit) -> str:
        label = unit.label_key or unit.relation_key or "value"
        return self.RELATION_LABELS.get(label, self.clean_label(label))

    @staticmethod
    def _coordinate(values: list[str]) -> str:
        values = [value for value in dict.fromkeys(values) if value]
        if not values: return ""
        if len(values) == 1: return values[0]
        if len(values) == 2: return f"{values[0]} et {values[1]}"
        return ", ".join(values[:-1]) + f" et {values[-1]}"

    @staticmethod
    def _abstain(unit: RealizationUnit) -> str:
        reason = unit.abstention_reason
        if str(reason).startswith("blocked"): return "Je ne peux pas répondre avec les preuves disponibles."
        if reason in {"no_matches", "unresolved_query_target"}: return "Je n'ai pas encore assez d'informations pour répondre."
        if reason == "no_relation_key_or_algebra": return "Je ne sais pas encore comment chercher cela."
        return "Je n'ai pas assez d'informations vérifiées pour répondre."

    @staticmethod
    def _safety_refusal(unit: RealizationUnit) -> str:
        if unit.safety_category == "self_harm":
            return "Non. Je ne peux pas aider à l'automutilation. Contactez immédiatement une personne de confiance ou un service d'urgence."
        if unit.safety_category in {"interpersonal_violence", "violence", "harm"}:
            if unit.safety_severity in {"high", "critical", "imminent"}:
                return "Non. Éloignez-vous de la situation et demandez une aide immédiate si quelqu'un est en danger."
            return "Non. Je ne veux pas que quelqu'un soit blessé."
        return "Non. Je ne peux pas aider avec cette demande."
