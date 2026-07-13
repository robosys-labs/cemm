"""VerbSchemaFacade — verb schema lookup backed by SemanticSchemaStore.

Import boundary: standard library + schema submodules only.

Architectural guardrails (AGENTS.md §7):
- The retired verb schema and PredicateSchema may not remain competing
  authorities. Actions and processes are event-oriented predicate
  schemas; executable operations use OperationSchema and reference
  semantic predicates for preconditions and effects.
- This facade provides backward-compatible lookup APIs for legacy
  consumers while delegating authority to SemanticSchemaStore.

The facade loads verb schema data from JSON, registers PredicateSchema
records in SemanticSchemaStore, and provides the same lookup methods
that legacy consumers expect (get, lookup_alias, slots_for, etc.).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .store import SemanticSchemaStore
from .envelope import SchemaEnvelope
from .predicate import PredicateSchema, MutationTemplate
from ..model.identity import Scope, ScopeLevel, Provenance, Permission


@dataclass(frozen=True, slots=True)
class VerbSchemaRecord:
    """Immutable verb schema metadata — adapter for legacy consumers."""
    action_key: str
    operator_family: str
    aliases: dict[str, list[str]]
    slots: dict[str, dict[str, Any]]
    preconditions: list[dict[str, Any]]
    state_deltas: list[dict[str, Any]]
    relation_deltas: list[dict[str, Any]]
    needs_satisfied: list[str]
    risk: str
    permission_policy: str
    safety_category: str
    emotional_valence: str


def _boot_provenance() -> Provenance:
    return Provenance(source_id="boot", source_kind="boot")


def _build_predicate_schema(record: VerbSchemaRecord) -> PredicateSchema:
    """Build a PredicateSchema from a verb schema record."""
    effects: list[MutationTemplate] = []
    for delta in record.state_deltas:
        effects.append(MutationTemplate(
            target_kind=delta.get("target", "actor"),
            operation="update",
            pattern_ref=f"state_delta:{delta.get('dimension', '')}",
        ))
    for delta in record.relation_deltas:
        effects.append(MutationTemplate(
            target_kind=delta.get("target", ""),
            operation="create",
            pattern_ref=f"relation_delta:{delta.get('relation_key', '')}",
        ))

    return PredicateSchema(
        semantic_key=f"verb:{record.action_key}",
        predication_kind="event",
        agentive=True,
        role_refs=tuple(f"role:{r}" for r in record.slots.keys()),
        predicted_effects=tuple(effects),
    )


def load_verb_schemas(
    schemas_dir: Path,
    store: SemanticSchemaStore | None = None,
) -> tuple[VerbSchemaRecord, ...]:
    """Load verb schemas from JSON and register them in SemanticSchemaStore.

    Returns a tuple of VerbSchemaRecord objects for legacy consumers.
    If a store is provided, each verb is registered as a PredicateSchema
    record in the store, making SemanticSchemaStore the sole authority.
    """
    action_data = json.loads(
        (schemas_dir / "action_operator_schemas.json").read_text(encoding="utf-8")
    )

    records: list[VerbSchemaRecord] = []
    for s in action_data:
        record = VerbSchemaRecord(
            action_key=s["action_key"],
            operator_family=s.get("operator_family", ""),
            aliases=s.get("aliases", {}),
            slots=s.get("slots", {}),
            preconditions=s.get("preconditions", []),
            state_deltas=s.get("state_deltas", []),
            relation_deltas=s.get("relation_deltas", []),
            needs_satisfied=s.get("needs_satisfied", []),
            risk=s.get("risk", "low"),
            permission_policy=s.get("permission_policy", "normal"),
            safety_category=s.get("safety_category", ""),
            emotional_valence=s.get("emotional_valence", "neutral"),
        )
        records.append(record)

        if store is not None:
            predicate_schema = _build_predicate_schema(record)
            envelope = SchemaEnvelope(
                record_id=f"boot:verb:{record.action_key}:v1",
                semantic_key=f"verb:{record.action_key}",
                schema_kind="predicate",
                status="candidate",
                scope=Scope(level=ScopeLevel.GLOBAL),
                version=1,
                payload=predicate_schema,
                provenance=_boot_provenance(),
                permission=Permission.public(),
            )
            store.register(envelope)

            for lang, aliases in record.aliases.items():
                for alias in aliases:
                    store.index_lexical_form(alias, lang, f"verb:{record.action_key}")

    return tuple(records)


class VerbSchemaFacade:
    """Backward-compatible verb schema lookup backed by SemanticSchemaStore.

    Provides the same API as the retired verb registry:
    - get(action_key) -> VerbSchemaRecord | None
    - lookup_alias(surface, language) -> str | None
    - all_action_keys() -> list[str]
    - slots_for(action_key) -> dict
    - state_deltas_for(action_key) -> list[dict]
    - relation_deltas_for(action_key) -> list[dict]
    - needs_satisfied_for(action_key) -> list[str]
    - safety_category_for(action_key) -> str
    - permission_policy_for(action_key) -> str
    - risk_for(action_key) -> str
    - emotional_valence_for(action_key) -> str

    Authority flows through SemanticSchemaStore — the facade is a
    read-only adapter for legacy consumers.
    """

    def __init__(
        self,
        records: tuple[VerbSchemaRecord, ...],
        store: SemanticSchemaStore | None = None,
    ) -> None:
        self._by_key: dict[str, VerbSchemaRecord] = {r.action_key: r for r in records}
        self._alias_to_key: dict[str, str] = {}
        self._lang_alias_to_key: dict[str, dict[str, str]] = {}
        self._store = store

        for r in records:
            for lang, aliases in r.aliases.items():
                if lang not in self._lang_alias_to_key:
                    self._lang_alias_to_key[lang] = {}
                for alias in aliases:
                    normalized = alias.strip().lower()
                    self._alias_to_key[normalized] = r.action_key
                    self._lang_alias_to_key[lang][normalized] = r.action_key

    @classmethod
    def from_directory(
        cls,
        schemas_dir: Path | None = None,
        store: SemanticSchemaStore | None = None,
    ) -> VerbSchemaFacade:
        """Load verb schemas from JSON directory and optionally register in store."""
        d = schemas_dir or Path(__file__).parent.parent.parent / "data" / "semantic_schemas"
        records = load_verb_schemas(d, store)
        return cls(records, store)

    def get(self, action_key: str) -> VerbSchemaRecord | None:
        return self._by_key.get(action_key)

    def lookup_alias(self, surface: str, language: str = "en") -> str | None:
        normalized = surface.strip().lower()
        lang_map = self._lang_alias_to_key.get(language, {})
        return lang_map.get(normalized)

    def all_action_keys(self) -> list[str]:
        return list(self._by_key.keys())

    def slots_for(self, action_key: str) -> dict[str, dict[str, Any]]:
        schema = self._by_key.get(action_key)
        return schema.slots if schema else {}

    def state_deltas_for(self, action_key: str) -> list[dict[str, Any]]:
        schema = self._by_key.get(action_key)
        return schema.state_deltas if schema else []

    def relation_deltas_for(self, action_key: str) -> list[dict[str, Any]]:
        schema = self._by_key.get(action_key)
        return schema.relation_deltas if schema else []

    def needs_satisfied_for(self, action_key: str) -> list[str]:
        schema = self._by_key.get(action_key)
        return schema.needs_satisfied if schema else []

    def safety_category_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.safety_category if schema else ""

    def permission_policy_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.permission_policy if schema else "normal"

    def risk_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.risk if schema else "low"

    def emotional_valence_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.emotional_valence if schema else "neutral"
