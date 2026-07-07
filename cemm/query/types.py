"""Budget-aware semantic query policy types.

These types are intentionally independent from natural language.  They describe
how much graph/query expansion is allowed, not what the assistant should say.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QueryBudgetPolicy:
    max_results: int = 8
    max_frame_scan: int = 128
    max_inference_depth: int = 1
    explanation_depth: int = 1
    allow_inverse: bool = True
    allow_inheritance: bool = True
    allow_composition: bool = False
    stop_on_first_sufficient: bool = True
    min_confidence: float = 0.5
    require_evidence_refs: bool = False
    prefer_current_turn: bool = True
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryBudgetTrace:
    policy: QueryBudgetPolicy = field(default_factory=QueryBudgetPolicy)
    input_frame_count: int = 0
    selected_frame_count: int = 0
    input_fill_count: int = 0
    selected_fill_count: int = 0
    reasons: list[str] = field(default_factory=list)
