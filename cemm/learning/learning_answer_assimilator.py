"""LearningAnswerAssimilator — assimilates user answers under episode expectations.
Uses percept evidence (referents, tokens, meaning groups, unknown lexemes)
instead of raw text parsing. Episode constraints improve ranking but do not
replace evidence.
"""

from __future__ import annotations

from typing import Any

from ..types.semantic_gap import SemanticGap
from ..types.learning_episode import LearningEpisode, LearningObligation
from ..types.learning_hypothesis import LearningHypothesis


class LearningAnswerAssimilator:
    """Assimilates user answers to learning questions under episode expectations.
    
    The active episode supplies an expectation frame:
    - expected answer kind
    - open semantic fields
    - candidate hypotheses
    - referent and topic bindings
    - question provenance
    
    Normal perception still runs, but episode constraints improve ranking
    rather than replacing evidence.
    """
    
    def assimilate(
        self,
        episode: LearningEpisode,
        obligation: LearningObligation,
        user_text: str,
        percept: Any,
    ) -> list[tuple[str, Any]]:
        """Extract field values from percept evidence.
        
        Returns list of (field_name, value) tuples that can be used
        to update the hypothesis.
        """
        filled_fields: list[tuple[str, Any]] = []
        
        expected_kind = obligation.expected_answer_schema.get("answer_kind", "")
        
        referents = list(getattr(percept, "referents", []) or [])
        tokens = list(getattr(percept, "tokens", []) or [])
        unknown_lexemes = list(getattr(percept, "unknown_lexemes", []) or [])
        
        if expected_kind == "semantic_type":
            candidate = self._extract_semantic_type(referents, unknown_lexemes, tokens)
            if candidate:
                filled_fields.append(("semantic_type", candidate))
        
        elif expected_kind == "entity_reference":
            candidate = self._extract_entity_ref(referents, tokens)
            if candidate:
                filled_fields.append(("entity_ref", candidate))
        
        elif expected_kind == "state_change":
            candidate = self._extract_state_change(referents, tokens)
            if candidate:
                filled_fields.append(("effect_description", candidate))
        
        elif expected_kind == "dimension_name":
            candidate = self._extract_dimension(referents, tokens)
            if candidate:
                filled_fields.append(("dimension", candidate))
        
        elif expected_kind == "value_description":
            candidate = self._extract_value(referents, tokens)
            if candidate:
                filled_fields.append(("value", candidate))
        
        elif expected_kind == "direction":
            candidate = self._extract_direction(referents, tokens)
            if candidate:
                filled_fields.append(("direction", candidate))
        
        elif expected_kind in ("time_description", "spatial_relation"):
            desc = self._extract_description(referents, tokens)
            if desc:
                filled_fields.append(("description", desc))
        
        else:
            desc = self._extract_description(referents, tokens)
            if desc:
                filled_fields.append(("description", desc))
        
        return filled_fields
    
    @staticmethod
    def _extract_semantic_type(
        referents: list[Any],
        unknown_lexemes: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            etype = getattr(ref, "entity_type", "")
            if surface and etype in ("concept", "unknown", "type"):
                return surface
        for item in unknown_lexemes:
            if isinstance(item, dict):
                surface = item.get("surface", "")
            elif isinstance(item, str):
                surface = item
            else:
                surface = str(item)
            if surface and len(surface) > 1:
                return surface
        for token in tokens:
            if len(token) > 2:
                return token
        return ""
    
    @staticmethod
    def _extract_entity_ref(
        referents: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            if surface:
                return surface
        for token in tokens:
            if len(token) > 1:
                return token
        return ""
    
    @staticmethod
    def _extract_state_change(
        referents: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            if surface:
                return surface
        for token in tokens:
            if len(token) > 2:
                return token
        return ""
    
    @staticmethod
    def _extract_dimension(
        referents: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            if surface:
                return surface
        for token in tokens:
            if len(token) > 2:
                return token
        return ""
    
    @staticmethod
    def _extract_value(
        referents: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            if surface:
                return surface
        for token in tokens:
            if len(token) > 1:
                return token
        return ""
    
    @staticmethod
    def _extract_direction(
        referents: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            if surface:
                return surface
        if tokens:
            return tokens[0]
        return ""
    
    @staticmethod
    def _extract_description(
        referents: list[Any],
        tokens: list[str],
    ) -> str:
        for ref in referents:
            surface = getattr(ref, "surface", "")
            if surface:
                return surface
        if tokens:
            return " ".join(tokens)
        return ""
