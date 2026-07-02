from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from .semantic_answer_graph import SemanticAnswerGraph


def _gen_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass
class GroundedGraph:
    id: str = field(default_factory=_gen_id)
    semantic_event_graph_id: str = ""
    entity_ids: list[str] = field(default_factory=list)
    resolved_time_refs: list[str] = field(default_factory=list)
    resolved_location_ids: list[str] = field(default_factory=list)
    active_frame_ids: list[str] = field(default_factory=list)
    permission: str = "public"
    missing_slots: list[str] = field(default_factory=list)
    confidence: float = 0.5
    version: str = "cemm.grounded_graph.v1"


@dataclass
class RankingTraceEntry:
    candidate_id: str
    score: float
    reason: str


@dataclass
class MemoryPacket:
    id: str = field(default_factory=_gen_id)
    selected_signal_ids: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    ranking_trace: list[RankingTraceEntry] = field(default_factory=list)
    confidence: float = 0.5
    version: str = "cemm.memory_packet.v1"


@dataclass
class InferencePacket:
    id: str = field(default_factory=_gen_id)
    implications: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    predictions: list[dict[str, Any]] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    state_deltas: dict[str, Any] = field(default_factory=dict)
    inference_graph_input_signal_ids: list[str] = field(default_factory=list)
    inference_graph_output_model_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    version: str = "cemm.inference_packet.v1"


@dataclass
class ActionPlan:
    id: str = field(default_factory=_gen_id)
    action_kind: str = "abstain"
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    tool_id: str | None = None
    execution_allowed: bool = False
    confidence: float = 0.5
    risk: float = 0.0
    version: str = "cemm.action_plan.v1"


@dataclass
class DecisionPacket:
    action_kind: str
    id: str = field(default_factory=_gen_id)
    semantic_answer_graph_id: str | None = None
    semantic_answer_graph: SemanticAnswerGraph | None = None
    action_plan: ActionPlan | None = None
    confidence: float = 0.5
    reason: str = ""
    version: str = "cemm.decision_packet.v1"


# ── serialization ─────────────────────────────────────────────


def packet_to_dict(packet: Any) -> dict:
    return asdict(packet)
