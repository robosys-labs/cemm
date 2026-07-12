"""Assimilate a current user percept under a prior learning obligation."""

from __future__ import annotations

from typing import Any

from ..kernel.proposition_semantics import is_internal_identifier
from ..types.learning_episode import LearningEpisode, LearningObligation


class LearningAnswerAssimilator:
    def assimilate(
        self,
        episode: LearningEpisode,
        obligation: LearningObligation,
        user_text: str,
        percept: Any,
    ) -> list[tuple[str, Any]]:
        """Return grounded field values; never use IDs as semantic content."""
        expected = str(obligation.expected_answer_schema.get("answer_kind", "") or "")
        relations = list(getattr(percept, "relations", []) or [])
        referents = list(getattr(percept, "referents", []) or [])
        states = list(getattr(percept, "states", []) or [])
        tokens = [str(token) for token in (getattr(percept, "tokens", []) or []) if str(token)]
        unknowns = list(getattr(percept, "unknown_lexemes", []) or [])

        value: Any = None
        field = "description"
        if expected == "semantic_type":
            field = "semantic_type"
            value = self._relation_object(relations) or self._semantic_type(referents, unknowns, tokens)
        elif expected == "entity_reference":
            field = "entity_ref"
            value = self._entity_reference(referents, relations, tokens)
        elif expected == "state_change":
            field = "effect_description"
            value = self._state_change(states, relations, referents, tokens)
        elif expected == "dimension_name":
            field = "dimension"
            value = self._dimension(states, relations, tokens)
        elif expected == "value_description":
            field = "value"
            value = self._relation_object(relations) or self._referent_surface(referents) or self._description(tokens)
        elif expected == "direction":
            field = "direction"
            value = self._direction(states, tokens)
        elif expected in {"time_description", "spatial_relation", "free_form", ""}:
            value = self._relation_object(relations) or self._referent_surface(referents) or self._description(tokens)

        if isinstance(value, str):
            value = value.strip()
            if not value or is_internal_identifier(value):
                return []
        return [(field, value)] if value not in (None, "", [], {}) else []

    @staticmethod
    def _relation_object(relations: list[Any]) -> str:
        for relation in relations:
            features = getattr(relation, "features", {}) or {}
            if str(features.get("proposition_mode", getattr(relation, "proposition_mode", "asserted")) or "asserted") == "queried":
                continue
            surface = str(features.get("object_surface", "") or "").strip()
            if surface and not is_internal_identifier(surface):
                return surface
        return ""

    @staticmethod
    def _semantic_type(referents: list[Any], unknowns: list[Any], tokens: list[str]) -> str:
        for ref in referents:
            surface = str(getattr(ref, "surface", "") or "").strip()
            entity_type = str(getattr(ref, "entity_type", "") or "")
            if surface and entity_type in {"concept", "type", "unknown"} and not is_internal_identifier(surface):
                return surface
        for item in unknowns:
            surface = str(item.get("surface", "") if isinstance(item, dict) else item).strip()
            if surface and not is_internal_identifier(surface):
                return surface
        return LearningAnswerAssimilator._description(tokens)

    @staticmethod
    def _entity_reference(referents: list[Any], relations: list[Any], tokens: list[str]) -> str:
        relation_object = LearningAnswerAssimilator._relation_object(relations)
        if relation_object:
            return relation_object
        return LearningAnswerAssimilator._referent_surface(referents) or LearningAnswerAssimilator._description(tokens)

    @staticmethod
    def _referent_surface(referents: list[Any]) -> str:
        for ref in referents:
            surface = str(getattr(ref, "surface", "") or "").strip()
            if surface and surface.lower() not in {"user", "self", "topic"} and not is_internal_identifier(surface):
                return surface
        return ""

    @staticmethod
    def _state_change(states: list[Any], relations: list[Any], referents: list[Any], tokens: list[str]) -> str:
        for state in states:
            surface = str(getattr(state, "surface", "") or getattr(state, "state_key", "") or "").strip()
            if surface and not is_internal_identifier(surface):
                return surface
        return LearningAnswerAssimilator._relation_object(relations) or LearningAnswerAssimilator._referent_surface(referents) or LearningAnswerAssimilator._description(tokens)

    @staticmethod
    def _dimension(states: list[Any], relations: list[Any], tokens: list[str]) -> str:
        for state in states:
            dimension = str(getattr(state, "dimension", "") or "").strip()
            if dimension and dimension != "unknown":
                return dimension
        for relation in relations:
            features = getattr(relation, "features", {}) or {}
            dimension = str(features.get("property_dimension", "") or features.get("dimension", "") or "").strip()
            if dimension:
                return dimension
        return LearningAnswerAssimilator._description(tokens)

    @staticmethod
    def _direction(states: list[Any], tokens: list[str]) -> str:
        for state in states:
            polarity = str(getattr(state, "polarity", "") or "").strip()
            if polarity and polarity != "unknown":
                return polarity
        return LearningAnswerAssimilator._description(tokens)

    @staticmethod
    def _description(tokens: list[str]) -> str:
        return " ".join(token for token in tokens if token).strip()
