from __future__ import annotations
from dataclasses import dataclass, field
from .self_state import SelfState


@dataclass
class SelfView:
    self_id: str = ""
    mode: str = "assistant"
    uncertainty: float = 0.0
    coherence: float = 1.0
    recent_error_rate: float = 0.0
    active_assumptions: list[str] = field(default_factory=list)
    known_limits: list[str] = field(default_factory=list)
    reliability_by_domain: dict[str, float] = field(default_factory=dict)
    recent_meta_memory_claim_ids: list[str] = field(default_factory=list)
    version: str = "erca.self_view.v1"

    @classmethod
    def from_self_state(cls, state: SelfState | None, recent_claim_ids: list[str] | None = None) -> SelfView:
        if state is None:
            return cls()
        return cls(
            self_id=state.id,
            mode=state.mode.value if hasattr(state.mode, 'value') else str(state.mode),
            uncertainty=state.uncertainty,
            coherence=state.coherence,
            recent_error_rate=state.recent_error_rate,
            active_assumptions=state.metacognition.active_assumptions,
            known_limits=state.metacognition.known_limits,
            reliability_by_domain=state.metacognition.reliability_by_domain,
            recent_meta_memory_claim_ids=recent_claim_ids or state.meta_memory.recently_written_claim_ids[-10:],
        )
