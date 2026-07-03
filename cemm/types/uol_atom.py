from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CANONICAL_ATOM_KINDS = frozenset({
    "entity",
    "process",
    "state",
    "relation",
    "quality",
    "quantity",
    "time",
    "place",
    "intent",
    "need",
    "modality",
    "evidence",
    "source",
    "permission",
    "action",
    "self",
})

CANONICAL_EDGE_TYPES = frozenset({
    "has_role",
    "modifies",
    "refers_to",
    "asks_about",
    "teaches",
    "evaluates",
    "causes",
    "enables",
    "prevents",
    "before",
    "after",
    "same_as",
    "is_a",
    "part_of",
    "used_for",
    "has_property",
})


@dataclass
class UOLAtom:
    id: str
    kind: str
    key: str
    surface: str = ""
    group_id: str = ""
    span_id: str = ""
    value: str | int | float | bool | None = None
    features: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    source: str = "surface"
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def training_label(self) -> str:
        return f"{self.kind}:{self.key}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "key": self.key,
            "surface": self.surface,
            "group_id": self.group_id,
            "span_id": self.span_id,
            "value": self.value,
            "features": dict(self.features),
            "confidence": self.confidence,
            "source": self.source,
            "evidence": [dict(item) for item in self.evidence],
            "label": self.training_label(),
        }


@dataclass
class UOLEdge:
    id: str
    edge_type: str
    source_id: str
    target_id: str
    group_id: str = ""
    predicate_id: str = ""
    confidence: float = 0.5
    source: str = "uol_graph_builder"
    features: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def training_label(self) -> str:
        return self.edge_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "edge_type": self.edge_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "group_id": self.group_id,
            "predicate_id": self.predicate_id,
            "confidence": self.confidence,
            "source": self.source,
            "features": dict(self.features),
            "evidence": [dict(item) for item in self.evidence],
            "label": self.training_label(),
        }
