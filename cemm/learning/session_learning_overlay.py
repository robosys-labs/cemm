"""SessionLearningOverlay — session-scoped provisional learning.
Consulted before durable registries during lookup.
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict


class SessionLearningOverlay:
    """Session-scoped provisional learning overlay.
    
    Stores newly taught bindings that are active for the session
    but not yet promoted to durable storage.
    Session overlay lookup precedes durable lexicon lookup.
    """
    
    def __init__(self) -> None:
        self._lexeme_bindings: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._entity_bindings: dict[str, dict[str, Any]] = {}
        self._operator_bindings: dict[str, dict[str, Any]] = {}
        self._state_bindings: dict[str, dict[str, Any]] = {}
        self._provisional_scope: str = "session"
    
    def add_lexeme_binding(self, form: str, binding: dict[str, Any]) -> None:
        norm = form.strip().lower()
        self._lexeme_bindings[norm].append(binding)
    
    def lookup_lexeme(self, form: str) -> list[dict[str, Any]]:
        norm = form.strip().lower()
        return list(self._lexeme_bindings.get(norm, []))
    
    def add_entity_binding(self, entity_id: str, binding: dict[str, Any]) -> None:
        self._entity_bindings[entity_id] = binding
    
    def lookup_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._entity_bindings.get(entity_id)
    
    def has_binding(self, form: str) -> bool:
        norm = form.strip().lower()
        return norm in self._lexeme_bindings
    
    def clear(self) -> None:
        self._lexeme_bindings.clear()
        self._entity_bindings.clear()
        self._operator_bindings.clear()
        self._state_bindings.clear()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "lexeme_count": sum(len(v) for v in self._lexeme_bindings.values()),
            "entity_count": len(self._entity_bindings),
            "scope": self._provisional_scope,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionLearningOverlay":
        return cls()
