"""Session-scoped provisional bindings with lossless serialization."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class SessionLearningOverlay:
    def __init__(self) -> None:
        self._lexeme_bindings: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._entity_bindings: dict[str, dict[str, Any]] = {}
        self._operator_bindings: dict[str, dict[str, Any]] = {}
        self._state_bindings: dict[str, dict[str, Any]] = {}
        self._provisional_scope = "session"

    def add_lexeme_binding(self, form: str, binding: dict[str, Any]) -> None:
        norm = self._normalize(form)
        if not norm:
            return
        candidate = dict(binding)
        if candidate not in self._lexeme_bindings[norm]:
            self._lexeme_bindings[norm].append(candidate)

    def lookup_lexeme(self, form: str) -> list[dict[str, Any]]:
        return [dict(item) for item in self._lexeme_bindings.get(self._normalize(form), [])]

    def add_entity_binding(self, entity_id: str, binding: dict[str, Any]) -> None:
        if entity_id:
            self._entity_bindings[entity_id] = dict(binding)

    def lookup_entity(self, entity_id: str) -> dict[str, Any] | None:
        value = self._entity_bindings.get(entity_id)
        return dict(value) if value is not None else None

    def add_operator_binding(self, operator_key: str, binding: dict[str, Any]) -> None:
        if operator_key:
            self._operator_bindings[operator_key] = dict(binding)

    def lookup_operator(self, operator_key: str) -> dict[str, Any] | None:
        value = self._operator_bindings.get(operator_key)
        return dict(value) if value is not None else None

    def add_state_binding(self, state_key: str, binding: dict[str, Any]) -> None:
        if state_key:
            self._state_bindings[state_key] = dict(binding)

    def lookup_state(self, state_key: str) -> dict[str, Any] | None:
        value = self._state_bindings.get(state_key)
        return dict(value) if value is not None else None

    def has_binding(self, form: str) -> bool:
        return self._normalize(form) in self._lexeme_bindings

    def clear(self) -> None:
        self._lexeme_bindings.clear()
        self._entity_bindings.clear()
        self._operator_bindings.clear()
        self._state_bindings.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self._provisional_scope,
            "lexeme_bindings": {key: [dict(item) for item in values] for key, values in self._lexeme_bindings.items()},
            "entity_bindings": {key: dict(value) for key, value in self._entity_bindings.items()},
            "operator_bindings": {key: dict(value) for key, value in self._operator_bindings.items()},
            "state_bindings": {key: dict(value) for key, value in self._state_bindings.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionLearningOverlay":
        overlay = cls()
        overlay._provisional_scope = str(data.get("scope", "session") or "session")
        for key, values in (data.get("lexeme_bindings", {}) or {}).items():
            for value in values or []:
                if isinstance(value, dict):
                    overlay.add_lexeme_binding(str(key), value)
        for key, value in (data.get("entity_bindings", {}) or {}).items():
            if isinstance(value, dict): overlay.add_entity_binding(str(key), value)
        for key, value in (data.get("operator_bindings", {}) or {}).items():
            if isinstance(value, dict): overlay.add_operator_binding(str(key), value)
        for key, value in (data.get("state_bindings", {}) or {}).items():
            if isinstance(value, dict): overlay.add_state_binding(str(key), value)
        return overlay

    @staticmethod
    def _normalize(form: str) -> str:
        return " ".join(str(form or "").strip().lower().split())
