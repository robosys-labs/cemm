"""EntityGroundingResolver — resolves entity references from NER, salience,
deixis, discourse, and episode expectations.

Maintains distinction between:
- mention candidate
- resolved entity  
- new entity candidate
- deictic/anaphoric reference
- role placeholder
- unresolved reference
"""

from __future__ import annotations

from typing import Any
from enum import Enum


class EntityGroundingStatus(str, Enum):
    MENTION_CANDIDATE = "mention_candidate"
    RESOLVED_ENTITY = "resolved_entity"
    NEW_ENTITY_CANDIDATE = "new_entity_candidate"
    DEICTIC_REFERENCE = "deictic_reference"
    ANAPHORIC_REFERENCE = "anaphoric_reference"
    ROLE_PLACEHOLDER = "role_placeholder"
    UNRESOLVED_REFERENCE = "unresolved_reference"


class EntityGroundingResolver:
    """Resolves entity references to known entities or creates new entity candidates."""
    
    def resolve(
        self,
        mention_surface: str,
        mention_type: str,
        known_entities: dict[str, Any],
        salience: dict[str, float],
        episode_expectations: dict[str, Any] | None = None,
    ) -> tuple[str | None, EntityGroundingStatus]:
        """Resolve an entity mention.
        
        Returns (entity_id, status).
        """
        # Check episode expectations first
        if episode_expectations:
            expected = episode_expectations.get("expected_entity")
            if expected and expected.get("surface", "").lower() == mention_surface.lower():
                return (expected["id"], EntityGroundingStatus.RESOLVED_ENTITY)
        
        # Check salience-ranked known entities
        if mention_surface.lower() in (e.lower() for e in known_entities):
            for entity_id, entity in known_entities.items():
                if entity.get("surface", "").lower() == mention_surface.lower():
                    return (entity_id, EntityGroundingStatus.RESOLVED_ENTITY)
                if entity.get("name", "").lower() == mention_surface.lower():
                    return (entity_id, EntityGroundingStatus.RESOLVED_ENTITY)
        
        # Check salience by surface match
        for entity_id in sorted(salience, key=salience.get, reverse=True):
            entity = known_entities.get(entity_id, {})
            if entity.get("surface", "").lower() == mention_surface.lower():
                return (entity_id, EntityGroundingStatus.RESOLVED_ENTITY)
        
        # Deictic references
        if mention_type == "deictic":
            return (None, EntityGroundingStatus.DEICTIC_REFERENCE)
        
        # Unresolved
        return (None, EntityGroundingStatus.UNRESOLVED_REFERENCE)
