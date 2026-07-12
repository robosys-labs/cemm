"""Language-neutral realization IR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types import ResponseCandidatePlan


@dataclass
class BoundSlot:
    key: str
    value: str = ""
    values: list[str] = field(default_factory=list)
    relation_key: str = ""
    slot_kind: str = "surface"
    confidence: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = [str(item) for item in self.values if str(item)]
        if self.value and self.value not in values:
            values.insert(0, self.value)
        self.values = list(dict.fromkeys(values))
        if not self.value and self.values:
            self.value = self.values[0]


@dataclass
class RealizationUnit:
    unit_type: str
    move_type: str
    subject_role: str = ""
    relation_key: str = ""
    object_value: str = ""
    object_values: list[str] = field(default_factory=list)
    label_key: str = ""
    safety_category: str = ""
    safety_severity: str = ""
    abstention_reason: str = ""
    evidence_path: list[str] = field(default_factory=list)
    write_committed: bool = False
    style: dict[str, float] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class RealizationPlan:
    language: str
    plan: ResponseCandidatePlan
    units: list[RealizationUnit] = field(default_factory=list)
    slot_keys: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
