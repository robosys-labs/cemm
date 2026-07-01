from __future__ import annotations
from dataclasses import dataclass, field

from .latent_space import TypedLatents


@dataclass
class Trace:
    context_id: str
    input_signal_ids: list[str] = field(default_factory=list)
    selected_entity_ids: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    action_id: str = ""
    operator_model_id: str = ""
    causal_inference_used: bool = False
    frame_rules_applied: bool = False
    synthesis_strategy_model_id: str | None = None
    synthesis_verified: bool = False
    synthesis_verification_type: str | None = None
    verifier_model_id: str | None = None
    permission: str = "allowed"
    confidence: float = 0.0
    cost_ms: float = 0.0
    fallback_used: bool = False
    semantic_event_graph_id: str | None = None
    semantic_answer_graph_id: str | None = None
    grounded_graph_id: str | None = None
    memory_packet_id: str | None = None
    inference_packet_id: str | None = None
    realization_strategy: str | None = None
    realization_verified: bool = False
    realization_details: dict = field(default_factory=dict)
    verification_details: dict = field(default_factory=dict)
    typed_latents: TypedLatents | None = None
