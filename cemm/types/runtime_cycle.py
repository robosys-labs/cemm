from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeCycleResult:
    signal: Any
    context_kernel: Any
    percept: Any | None = None
    uol_graph: Any | None = None
    working_set: Any | None = None
    retrieval: Any | None = None
    resolution: Any | None = None
    act_plan: Any | None = None
    patch_candidates: list[Any] = field(default_factory=list)
    validation: list[Any] = field(default_factory=list)
    consolidation: list[Any] = field(default_factory=list)
    realized_output: str = ""
    diagnostics: Any | None = None
    cost_ms: float = 0.0
