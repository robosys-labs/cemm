from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SelfView:
    self_id: str = ""
    mode: str = "assistant"
    uncertainty: float = 0.0
    coherence: float = 1.0
    recent_error_rate: float = 0.0
    active_assumption_claim_ids: list[str] = field(default_factory=list)
    known_limit_claim_ids: list[str] = field(default_factory=list)
    coverage_gap_claim_ids: list[str] = field(default_factory=list)
    reliability_by_domain: dict[str, float] = field(default_factory=dict)
    recent_meta_memory_claim_ids: list[str] = field(default_factory=list)
    error_history: list[str] = field(default_factory=list)
    version: str = "cemm.self_view.v1"
