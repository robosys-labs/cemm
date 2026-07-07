"""Language-neutral realization IR.

Response moves are converted into these units before any language renderer
sees them. This keeps grammar/rendering multilingual from day one without
letting language-specific rules leak back into response planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types import ResponseCandidatePlan


@dataclass
class BoundSlot:
    key: str
    value: str
    relation_key: str = ""
    slot_kind: str = "surface"
    confidence: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class RealizationUnit:
    """Smallest language-neutral unit rendered by a language module."""

    unit_type: str
    move_type: str
    subject_role: str = ""
    relation_key: str = ""
    object_value: str = ""
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
