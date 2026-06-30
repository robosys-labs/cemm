from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticEdge:
    source_id: str
    target_id: str
    relation: str
    confidence: float = 0.5
    confidence_type: str = "inferred"


@dataclass
class SemanticEventGraph:
    id: str
    source_signal_ids: list[str]
    context_id: str
    entity_refs: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    states: list[dict[str, Any]] = field(default_factory=list)
    claim_refs: list[str] = field(default_factory=list)
    claim_candidates: list[dict[str, Any]] = field(default_factory=list)
    model_refs: list[str] = field(default_factory=list)
    action_refs: list[str] = field(default_factory=list)
    temporal_edges: list[SemanticEdge] = field(default_factory=list)
    causal_edges: list[dict[str, Any]] = field(default_factory=list)
    permission_scope: str = "public"
    confidence: float = 0.5
    version: str = "cemm.semantic_event_graph.v1"
