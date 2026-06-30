from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnswerVerification:
    supported: bool = False
    verification_type: str = "none"
    confidence: float = 0.0
    unsupported_spans: list[str] = field(default_factory=list)
    uncertainty_reason: str = ""


@dataclass
class SemanticAnswerGraph:
    id: str
    intent: str
    source_signal_ids: list[str]
    context_id: str
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    entity_refs: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    states: list[dict[str, Any]] = field(default_factory=list)
    causal_edges: list[dict[str, Any]] = field(default_factory=list)
    temporal_edges: list[dict[str, Any]] = field(default_factory=list)
    action_candidates: list[dict[str, Any]] = field(default_factory=list)
    answer_latent: list[float] = field(default_factory=list)
    engagement_rule: str = "default"
    conversation_dynamics_keys: list[str] = field(default_factory=list)
    action_scope: str = "direct"
    confidence: float = 0.5
    uncertainty_reasons: list[str] = field(default_factory=list)
    permission_scope: str = "public"
    verification: AnswerVerification = field(default_factory=AnswerVerification)
    version: str = "cemm.semantic_answer_graph.v1"
