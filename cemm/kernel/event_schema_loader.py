"""Event schema loader — loads event semantics entries from uol_semantics.json.

Per §8.10 of cemm_foundational_fixes.md, UOL semantics JSON now carries
event_schemas alongside the flat alias-to-act table. This module provides
a typed loader for those entries so kernel components can consume them
without duplicating parsing logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


@dataclass
class LoadedActionSchema:
    schema_key: str = ""
    action_key: str = ""
    actor_role: str = ""
    target_role: str = ""
    object_role: str = ""
    place_role: str = ""
    source_role: str = ""
    destination_role: str = ""
    recipient_role: str = ""
    aliases: list[str] = field(default_factory=list)
    expected_outcomes: list[dict[str, Any]] = field(default_factory=list)
    safety_category: str = ""


@dataclass
class LoadedStateSchema:
    schema_key: str = ""
    dimension: str = ""
    polarity: str = ""
    aliases: list[str] = field(default_factory=list)
    triggers_need: str | None = None


@dataclass
class LoadedNeedSchema:
    schema_key: str = ""
    dimension: str = ""
    aliases: list[str] = field(default_factory=list)
    satisfies_state: str = ""


@dataclass
class LoadedAffordanceSchema:
    schema_key: str = ""
    entity_type: str = ""
    affords: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


@dataclass
class LoadedSocialSchema:
    schema_key: str = ""
    aliases: list[str] = field(default_factory=list)
    reply_obligation: bool = False
    expected_response: str | None = None


@dataclass
class LoadedSafetySchema:
    schema_key: str = ""
    aliases: list[str] = field(default_factory=list)
    severity: str = "high"
    allowed_response_mode: str = "deescalate"


@dataclass
class LoadedIdiomSchema:
    schema_key: str = ""
    literal_meaning: str = ""
    figurative_meaning: str = ""
    language: str = "en"
    aliases: list[str] = field(default_factory=list)
    act_type: str = "unknown"


@dataclass
class EventSchemaStore:
    """Container for all loaded event schema entries."""
    action_schemas: dict[str, LoadedActionSchema] = field(default_factory=dict)
    state_schemas: dict[str, LoadedStateSchema] = field(default_factory=dict)
    need_schemas: dict[str, LoadedNeedSchema] = field(default_factory=dict)
    place_affordances: dict[str, LoadedAffordanceSchema] = field(default_factory=dict)
    object_affordances: dict[str, LoadedAffordanceSchema] = field(default_factory=dict)
    social_schemas: dict[str, LoadedSocialSchema] = field(default_factory=dict)
    safety_schemas: dict[str, LoadedSafetySchema] = field(default_factory=dict)
    idiom_schemas: dict[str, LoadedIdiomSchema] = field(default_factory=dict)

    def lookup_alias(self, text: str) -> tuple[str, str] | None:
        """Look up a surface text against all schema aliases.

        Returns (entry_kind, schema_key) if found, else None.
        """
        text_lower = text.lower().strip()
        for key, schema in self.action_schemas.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("action_schema", key)
        for key, schema in self.state_schemas.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("state_schema", key)
        for key, schema in self.need_schemas.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("need_schema", key)
        for key, schema in self.place_affordances.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("place_affordance", key)
        for key, schema in self.object_affordances.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("object_affordance", key)
        for key, schema in self.social_schemas.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("social_schema", key)
        for key, schema in self.safety_schemas.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("safety_schema", key)
        for key, schema in self.idiom_schemas.items():
            if text_lower in [a.lower() for a in schema.aliases]:
                return ("idiom_schema", key)
        return None


def load_event_schemas(path: Path | None = None) -> EventSchemaStore:
    """Load event schemas from uol_semantics.json."""
    p = path or _UOL_SEMANTICS_PATH
    if not p.exists():
        return EventSchemaStore()
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data.get("event_schemas", [])
    store = EventSchemaStore()
    for entry in entries:
        kind = entry.get("entry_kind", "")
        key = entry.get("schema_key", "")
        if not key:
            continue
        if kind == "action_schema":
            store.action_schemas[key] = LoadedActionSchema(
                schema_key=key,
                action_key=entry.get("action_key", ""),
                actor_role=entry.get("actor_role", ""),
                target_role=entry.get("target_role", ""),
                object_role=entry.get("object_role", ""),
                place_role=entry.get("place_role", ""),
                source_role=entry.get("source_role", ""),
                destination_role=entry.get("destination_role", ""),
                recipient_role=entry.get("recipient_role", ""),
                aliases=entry.get("aliases", []),
                expected_outcomes=entry.get("expected_outcomes", []),
                safety_category=entry.get("safety_category", ""),
            )
        elif kind == "state_schema":
            store.state_schemas[key] = LoadedStateSchema(
                schema_key=key,
                dimension=entry.get("dimension", ""),
                polarity=entry.get("polarity", ""),
                aliases=entry.get("aliases", []),
                triggers_need=entry.get("triggers_need"),
            )
        elif kind == "need_schema":
            store.need_schemas[key] = LoadedNeedSchema(
                schema_key=key,
                dimension=entry.get("dimension", ""),
                aliases=entry.get("aliases", []),
                satisfies_state=entry.get("satisfies_state", ""),
            )
        elif kind == "place_affordance":
            store.place_affordances[key] = LoadedAffordanceSchema(
                schema_key=key,
                entity_type="place",
                affords=entry.get("affords", []),
                aliases=entry.get("aliases", []),
            )
        elif kind == "object_affordance":
            store.object_affordances[key] = LoadedAffordanceSchema(
                schema_key=key,
                entity_type="object",
                affords=entry.get("affords", []),
                aliases=entry.get("aliases", []),
            )
        elif kind == "social_schema":
            store.social_schemas[key] = LoadedSocialSchema(
                schema_key=key,
                aliases=entry.get("aliases", []),
                reply_obligation=entry.get("reply_obligation", False),
                expected_response=entry.get("expected_response"),
            )
        elif kind == "safety_schema":
            store.safety_schemas[key] = LoadedSafetySchema(
                schema_key=key,
                aliases=entry.get("aliases", []),
                severity=entry.get("severity", "high"),
                allowed_response_mode=entry.get("allowed_response_mode", "deescalate"),
            )
        elif kind == "idiom_schema":
            store.idiom_schemas[key] = LoadedIdiomSchema(
                schema_key=key,
                literal_meaning=entry.get("literal_meaning", ""),
                figurative_meaning=entry.get("figurative_meaning", ""),
                language=entry.get("language", "en"),
                aliases=entry.get("aliases", []),
                act_type=entry.get("act_type", "unknown"),
            )
    return store
