"""Normalized durable relation identity and cardinality semantics.

Contradiction detection, deduplication, supersession, indexing, and retrieval
must use the same slot identity. Object values deliberately do not participate
in the slot identity; they distinguish occupants of that slot.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
import json
from typing import Any, Mapping

VALID_CARDINALITIES = frozenset({"single", "optional_one", "many", "set", "unknown"})


def normalize_dimension(value: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return ".".join(part for part in text.split(".") if part)


def normalize_scope(value: str) -> str:
    return str(value or "").strip().lower()


def normalize_qualifiers(value: Mapping[str, Any] | None) -> str:
    def canonical(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(k): canonical(v) for k, v in sorted(item.items(), key=lambda pair: str(pair[0]))}
        if isinstance(item, (list, tuple, set, frozenset)):
            return [canonical(v) for v in item]
        if isinstance(item, str):
            return item.strip()
        if dataclasses.is_dataclass(item):
            return canonical(dataclasses.asdict(item))
        if hasattr(item, "__dict__"):
            return canonical(item.__dict__)
        return item

    return json.dumps(canonical(value or {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def subject_key_from_fields(fields: Mapping[str, Any]) -> str:
    return str(
        fields.get("subject_entity_id", "")
        or fields.get("subject_concept_id", "")
        or fields.get("subject_surface", "")
        or ""
    ).strip()


def object_key_from_fields(fields: Mapping[str, Any]) -> str:
    return str(
        fields.get("object_entity_id", "")
        or fields.get("object_concept_id", "")
        or fields.get("object_surface", "")
        or ""
    ).strip()


def dimension_from_fields(fields: Mapping[str, Any]) -> str:
    features = fields.get("features", {}) or {}
    if not isinstance(features, Mapping):
        features = {}
    return normalize_dimension(
        str(
            fields.get("dimension", "")
            or features.get("dimension", "")
            or features.get("property_dimension", "")
            or ""
        )
    )


def scope_from_fields(fields: Mapping[str, Any]) -> str:
    features = fields.get("features", {}) or {}
    if not isinstance(features, Mapping):
        features = {}
    return normalize_scope(str(fields.get("relation_scope", "") or features.get("relation_scope", "") or ""))


def cardinality_from_fields(
    fields: Mapping[str, Any],
    *,
    schema_store: Any | None = None,
    default: str = "unknown",
) -> str:
    features = fields.get("features", {}) or {}
    if not isinstance(features, Mapping):
        features = {}
    value = str(fields.get("cardinality", "") or features.get("cardinality", "") or "").strip().lower()
    if value in VALID_CARDINALITIES:
        return value
    relation_key = str(fields.get("relation_key", "") or "")
    if schema_store is not None and relation_key:
        schema = schema_store.get(relation_key)
        schema_value = str(getattr(schema, "cardinality", "") or "").strip().lower() if schema is not None else ""
        if schema_value in VALID_CARDINALITIES:
            return schema_value
    return default if default in VALID_CARDINALITIES else "unknown"


@dataclass(frozen=True, slots=True)
class RelationIdentity:
    relation_key: str
    subject_key: str
    dimension: str = ""
    relation_scope: str = ""
    qualifiers_fingerprint: str = "{}"

    @classmethod
    def from_fields(cls, fields: Mapping[str, Any]) -> "RelationIdentity":
        return cls(
            relation_key=str(fields.get("relation_key", "") or "").strip(),
            subject_key=subject_key_from_fields(fields),
            dimension=dimension_from_fields(fields),
            relation_scope=scope_from_fields(fields),
            qualifiers_fingerprint=normalize_qualifiers(fields.get("qualifiers", {}) or {}),
        )

    def as_key(self) -> str:
        return "\x1f".join((
            self.relation_key,
            self.subject_key,
            self.dimension,
            self.relation_scope,
            self.qualifiers_fingerprint,
        ))
