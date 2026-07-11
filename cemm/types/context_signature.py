from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


@dataclass(frozen=True, slots=True)
class ContextSignature:
    """Immutable signature of the context in which a learning observation occurred.
    
    Used to determine sense splitting, context restriction, and promotion eligibility.
    Context signatures may include language, domain, neighboring roles, entity kinds,
    construction ID, discourse function, modality, polarity, time, and place.
    """
    language_tag: str = "und"
    domain: str = ""
    dialect: str = ""
    register: str = ""
    
    # Semantic context
    neighboring_roles: tuple[str, ...] = ()
    entity_kinds: tuple[str, ...] = ()
    construction_ids: tuple[str, ...] = ()
    discourse_function: str = ""
    state_family: str = ""
    relation_family: str = ""
    operator_family: str = ""
    
    # Modality context
    modality: str = ""
    polarity: str = ""
    evidentiality: str = ""
    
    # Discourse context
    turn_index: int = 0
    prior_intents: tuple[str, ...] = ()
    topic: str = ""
    
    def matches(self, other: "ContextSignature", exact: bool = False) -> bool:
        """Check if this context matches another.
        
        In exact mode, all fields must match.
        In relaxed mode, only non-empty fields are checked.
        """
        if exact:
            return self == other
        
        # Relaxed matching: non-empty fields must match
        for field_name in ("language_tag", "domain", "dialect", "register",
                          "discourse_function", "state_family", "relation_family",
                          "operator_family", "modality", "polarity", "topic"):
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if self_val and other_val and self_val != other_val:
                return False
        
        # Check tuple fields
        for field_name in ("neighboring_roles", "entity_kinds", "construction_ids"):
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if self_val and other_val:
                if set(self_val) & set(other_val):
                    continue
                return False
        
        return True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "language_tag": self.language_tag,
            "domain": self.domain,
            "dialect": self.dialect,
            "register": self.register,
            "discourse_function": self.discourse_function,
            "modality": self.modality,
            "polarity": self.polarity,
            "topic": self.topic,
        }
