from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from ..types.semantic_focus import SemanticFocus


@dataclass
class SemanticWorkingSet:
    focus_items: list[SemanticFocus] = field(default_factory=list)
    selected_paths: list[str] = field(default_factory=list)
    rejected_paths: list[str] = field(default_factory=list)
    unresolved_ports: list[dict[str, Any]] = field(default_factory=list)
    evidence_requirements: list[dict[str, Any]] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
