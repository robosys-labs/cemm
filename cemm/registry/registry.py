from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class RegistryEntry:
    model_id: str
    canonical_key: str
    kind: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    required_slots: list[str] = field(default_factory=list)
    version: str = "cemm.registry_entry.v1"
    metadata: dict = field(default_factory=dict)


class Registry:
    def __init__(self) -> None:
        self._predicates: dict[str, RegistryEntry] = {}
        self._entity_types: dict[str, RegistryEntry] = {}
        self._operators: dict[str, RegistryEntry] = {}
        self._synthesis_strategies: dict[str, RegistryEntry] = {}
        self._frame_rules: dict[str, RegistryEntry] = {}
        self._inductors: dict[str, RegistryEntry] = {}
        self._context_rules: dict[str, RegistryEntry] = {}
        self._verifiers: dict[str, RegistryEntry] = {}
        self._uol_semantics: dict[str, RegistryEntry] = {}
        self._procedures: dict[str, RegistryEntry] = {}
        self._tools: dict[str, RegistryEntry] = {}
        self._alias_map: dict[str, str] = {}

    def register(self, entry: RegistryEntry) -> None:
        kind_map = {
            "predicate": self._predicates,
            "entity_type": self._entity_types,
            "operator": self._operators,
            "synthesis_strategy": self._synthesis_strategies,
            "context_rule": self._context_rules,
            "frame_rule": self._frame_rules,
            "verifier": self._verifiers,
            "inductor": self._inductors,
            "uol_semantic": self._uol_semantics,
            "procedure": self._procedures,
            "tool": self._tools,
        }
        store = kind_map.get(entry.kind)
        if store is None:
            raise ValueError(f"Unknown registry kind: {entry.kind}")
        store[entry.canonical_key] = entry
        for alias in entry.aliases:
            self._alias_map[alias] = entry.canonical_key

    def resolve_predicate(self, alias_or_key: str) -> str | None:
        if alias_or_key in self._predicates:
            return alias_or_key
        canonical = self._alias_map.get(alias_or_key)
        if canonical and canonical in self._predicates:
            return canonical
        return None

    def resolve_entity_type(self, alias_or_key: str) -> str | None:
        if alias_or_key in self._entity_types:
            return alias_or_key
        canonical = self._alias_map.get(alias_or_key)
        if canonical and canonical in self._entity_types:
            return canonical
        return None

    def resolve_operator(self, alias_or_key: str) -> RegistryEntry | None:
        if alias_or_key in self._operators:
            return self._operators[alias_or_key]
        canonical = self._alias_map.get(alias_or_key)
        if canonical and canonical in self._operators:
            return self._operators[canonical]
        return None

    def get_predicate(self, key: str) -> RegistryEntry | None:
        return self._predicates.get(key)

    def get_entity_type(self, key: str) -> RegistryEntry | None:
        return self._entity_types.get(key)

    def get_operator(self, key: str) -> RegistryEntry | None:
        return self._operators.get(key)

    def get_synthesis_strategy(self, key: str) -> RegistryEntry | None:
        return self._synthesis_strategies.get(key)

    def get_frame_rule(self, key: str) -> RegistryEntry | None:
        return self._frame_rules.get(key)

    def get_inductor(self, key: str) -> RegistryEntry | None:
        return self._inductors.get(key)

    def get_context_rule(self, key: str) -> RegistryEntry | None:
        return self._context_rules.get(key)

    def get_verifier(self, key: str) -> RegistryEntry | None:
        return self._verifiers.get(key)

    def all_by_kind(self, kind: str) -> list[RegistryEntry]:
        kind_map = {
            "predicate": self._predicates,
            "entity_type": self._entity_types,
            "operator": self._operators,
            "synthesis_strategy": self._synthesis_strategies,
            "context_rule": self._context_rules,
            "frame_rule": self._frame_rules,
            "verifier": self._verifiers,
            "inductor": self._inductors,
            "uol_semantic": self._uol_semantics,
            "procedure": self._procedures,
            "tool": self._tools,
        }
        store = kind_map.get(kind)
        if store is None:
            return []
        return list(store.values())

    def get_procedure(self, key: str) -> RegistryEntry | None:
        return self._procedures.get(key)

    def get_tool(self, key: str) -> RegistryEntry | None:
        return self._tools.get(key)

    def get_uol_semantic(self, key: str) -> RegistryEntry | None:
        return self._uol_semantics.get(key)

    def resolve_uol(self, atom_key: str) -> RegistryEntry | None:
        for entry in self._uol_semantics.values():
            if entry.canonical_key == atom_key:
                return entry
        return None

    def all_predicate_keys(self) -> list[str]:
        return list(self._predicates.keys())

    def all_operator_entries(self) -> list[RegistryEntry]:
        return list(self._operators.values())

    def canonicalize_predicate(self, raw: str) -> str:
        resolved = self.resolve_predicate(raw.lower().strip())
        if resolved:
            return resolved
        return raw

    def canonicalize_entity_type(self, raw: str) -> str:
        resolved = self.resolve_entity_type(raw.lower().strip())
        if resolved:
            return resolved
        return raw

    def to_json(self, path: str | Path) -> None:
        data = {
            "version": "cemm.registry.v1",
            "predicates": {k: self._entry_to_dict(v) for k, v in self._predicates.items()},
            "entity_types": {k: self._entry_to_dict(v) for k, v in self._entity_types.items()},
            "operators": {k: self._entry_to_dict(v) for k, v in self._operators.items()},
            "synthesis_strategies": {k: self._entry_to_dict(v) for k, v in self._synthesis_strategies.items()},
            "context_rules": {k: self._entry_to_dict(v) for k, v in self._context_rules.items()},
            "frame_rules": {k: self._entry_to_dict(v) for k, v in self._frame_rules.items()},
            "verifiers": {k: self._entry_to_dict(v) for k, v in self._verifiers.items()},
            "inductors": {k: self._entry_to_dict(v) for k, v in self._inductors.items()},
            "procedures": {k: self._entry_to_dict(v) for k, v in self._procedures.items()},
            "tools": {k: self._entry_to_dict(v) for k, v in self._tools.items()},
            "_alias_map": self._alias_map,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_json(cls, path: str | Path) -> Registry:
        reg = cls()
        with open(path) as f:
            data = json.load(f)
        for kind_name in ("predicates", "entity_types", "operators", "synthesis_strategies", "context_rules", "frame_rules", "verifiers", "inductors", "procedures", "tools"):
            kind_key = kind_name.rstrip("s")
            for key, entry_dict in data.get(kind_name, {}).items():
                entry = cls._dict_to_entry(entry_dict, kind=kind_key)
                reg.register(entry)
        reg._alias_map = data.get("_alias_map", {})
        return reg

    @staticmethod
    def _entry_to_dict(e: RegistryEntry) -> dict:
        return {
            "model_id": e.model_id,
            "canonical_key": e.canonical_key,
            "kind": e.kind,
            "aliases": e.aliases,
            "description": e.description,
            "required_slots": e.required_slots,
            "version": e.version,
            "metadata": e.metadata,
        }

    @staticmethod
    def _dict_to_entry(d: dict, kind: str) -> RegistryEntry:
        return RegistryEntry(
            model_id=d["model_id"],
            canonical_key=d["canonical_key"],
            kind=kind,
            aliases=d.get("aliases", []),
            description=d.get("description", ""),
            required_slots=d.get("required_slots", []),
            version=d.get("version", "cemm.registry_entry.v1"),
            metadata=d.get("metadata", {}),
        )
