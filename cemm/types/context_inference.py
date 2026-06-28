from dataclasses import dataclass, field

@dataclass
class ContextInference:
    id: str
    source_signal_id: str
    inferred_claim_ids: list[str] = field(default_factory=list)
    applied_context_rule_model_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    decay_half_life_ms: float = 300000.0
    frame_id: str = ""
