"""Generate gold example JSONL for each packet type."""

import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import json
import uuid
import time

from cemm.types.semantic_event_graph import SemanticEventGraph, SemanticEdge
from cemm.types.semantic_answer_graph import SemanticAnswerGraph, AnswerVerification
from cemm.types.packets import (
    GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket,
    ActionPlan, RankingTraceEntry, packet_to_dict,
)
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission


def _ts():
    return int(time.time())


_GOLD_EXAMPLES: list[dict] = []


def add(task_type: str, packet: dict, label: str = "") -> None:
    _GOLD_EXAMPLES.append({
        "id": uuid.uuid4().hex[:16],
        "task_type": task_type,
        "permission_scope": "training_gold",
        "payload": {
            "packet": packet,
            "label": label or task_type,
            "created_at": _ts(),
        },
        "created_at": _ts(),
    })


# ── SEG examples ──────────────────────────────────────────────


add("semantic_event_graph", packet_to_dict(SemanticEventGraph(
    id="gold_seg_001",
    source_signal_ids=["sig_001"],
    context_id="ctx_001",
    entity_refs=[
        {"name": "Jupiter", "kind": "planet"},
        {"name": "Io", "kind": "moon"},
    ],
    processes=[{"frame_key": "orbital_relation", "confidence": 0.9}],
    states=[{"entity": "Io", "dimension": "orbital_period", "value": "1.77 days"}],
    claim_refs=["clm_001"],
    claim_candidates=[],
    temporal_edges=[SemanticEdge(source_id="Io", target_id="Jupiter", relation="orbits")],
    causal_edges=[SemanticEdge(source_id="gravity", target_id="orbit", relation="causes", confidence=0.8)],
    permission_scope="public",
    confidence=0.85,
)), label="planetary_orbital_relation")

add("semantic_event_graph", packet_to_dict(SemanticEventGraph(
    id="gold_seg_002",
    source_signal_ids=["sig_002"],
    context_id="ctx_002",
    entity_refs=[
        {"name": "user", "kind": "person"},
        {"name": "codebase", "kind": "artifact"},
    ],
    processes=[{"frame_key": "question_about_code", "confidence": 0.95}],
    states=[],
    claim_refs=["clm_010"],
    temporal_edges=[],
    causal_edges=[],
    permission_scope="user_private",
    confidence=0.75,
)), label="user_question_about_code")

add("semantic_event_graph", packet_to_dict(SemanticEventGraph(
    id="gold_seg_003",
    source_signal_ids=["sig_003"],
    context_id="ctx_003",
    entity_refs=[
        {"name": "assistant", "kind": "system"},
    ],
    processes=[{"frame_key": "self_referential_query", "confidence": 0.7}],
    states=[{"entity": "assistant", "dimension": "capability", "value": "language_model"}],
    claim_refs=["clm_020", "clm_021"],
    temporal_edges=[],
    causal_edges=[],
    permission_scope="public",
    confidence=0.6,
)), label="self_referential_query")


# ── SAG examples ──────────────────────────────────────────────


add("semantic_answer_graph", packet_to_dict(SemanticAnswerGraph(
    id="gold_sag_001",
    intent="answer",
    source_signal_ids=["sig_001"],
    context_id="ctx_001",
    selected_claim_ids=["clm_001", "clm_002"],
    selected_model_ids=["mdl_001"],
    entity_refs=[{"name": "Jupiter", "kind": "planet"}],
    processes=[{"frame_key": "explain_relation", "confidence": 0.9}],
    states=[{"entity": "Io", "state": "orbiting"}],
    causal_edges=[{"source": "gravity", "target": "tidal_heating", "relation": "causes"}],
    temporal_edges=[{"source": "Io", "target": "Jupiter", "relation": "orbits", "confidence": 0.95}],
    confidence=0.88,
    permission_scope="public",
    verification=AnswerVerification(supported=True, verification_type="hard", confidence=0.9, unsupported_spans=[]),
)), label="answer_with_verification")

add("semantic_answer_graph", packet_to_dict(SemanticAnswerGraph(
    id="gold_sag_002",
    intent="ask",
    source_signal_ids=["sig_002"],
    context_id="ctx_002",
    selected_claim_ids=[],
    selected_model_ids=[],
    entity_refs=[],
    processes=[{"frame_key": "request_clarification", "confidence": 0.8}],
    states=[],
    confidence=0.7,
    permission_scope="public",
    verification=AnswerVerification(supported=False, verification_type="none", confidence=0.0,
                                     unsupported_spans=[], uncertainty_reason="ambiguous intent"),
)), label="ask_for_clarification")

add("semantic_answer_graph", packet_to_dict(SemanticAnswerGraph(
    id="gold_sag_003",
    intent="abstain",
    source_signal_ids=["sig_003"],
    context_id="ctx_003",
    selected_claim_ids=[],
    selected_model_ids=[],
    entity_refs=[],
    processes=[],
    states=[],
    confidence=0.3,
    uncertainty_reasons=["insufficient evidence", "out of domain"],
    permission_scope="public",
    verification=AnswerVerification(supported=False, verification_type="none"),
)), label="abstain_insufficient_evidence")


# ── GroundedGraph examples ───────────────────────────────────


add("grounded_graph", packet_to_dict(GroundedGraph(
    semantic_event_graph_id="gold_seg_001",
    entity_ids=["ent_jupiter", "ent_io"],
    resolved_time_refs=["2024-01-15T10:00:00Z"],
    resolved_location_ids=["loc_solar_system"],
    active_frame_ids=["frame_orbital_mechanics"],
    permission="public",
    missing_slots=[],
    confidence=0.85,
)), label="fully_grounded")

add("grounded_graph", packet_to_dict(GroundedGraph(
    semantic_event_graph_id="gold_seg_002",
    entity_ids=["ent_user_001"],
    resolved_time_refs=[],
    resolved_location_ids=[],
    active_frame_ids=["frame_general_query"],
    permission="user_private",
    missing_slots=["entity_id"],
    confidence=0.5,
)), label="partial_grounding_missing_slots")

add("grounded_graph", packet_to_dict(GroundedGraph(
    semantic_event_graph_id="gold_seg_003",
    entity_ids=[],
    resolved_time_refs=[],
    resolved_location_ids=[],
    active_frame_ids=[],
    permission="system_private",
    missing_slots=["entity_id", "time_ref", "frame_id"],
    confidence=0.2,
)), label="no_grounding")


# ── MemoryPacket examples ────────────────────────────────────


add("memory_packet", packet_to_dict(MemoryPacket(
    selected_signal_ids=["sig_001", "sig_002"],
    selected_claim_ids=["clm_001", "clm_002", "clm_003"],
    selected_model_ids=["mdl_001"],
    ranking_trace=[
        RankingTraceEntry(candidate_id="clm_001", score=0.92, reason="relevance+recency"),
        RankingTraceEntry(candidate_id="clm_002", score=0.78, reason="relevance"),
        RankingTraceEntry(candidate_id="clm_003", score=0.55, reason="partial_relevance"),
    ],
    confidence=0.82,
)), label="three_ranked_claims")

add("memory_packet", packet_to_dict(MemoryPacket(
    selected_signal_ids=[],
    selected_claim_ids=[],
    selected_model_ids=[],
    ranking_trace=[],
    confidence=0.0,
)), label="empty_memory_packet")


# ── InferencePacket examples ─────────────────────────────────


add("inference_packet", packet_to_dict(InferencePacket(
    implications=[
        {"model_id": "mdl_causal_001", "predicate": "causes_tidal_heating", "confidence": 0.85},
        {"model_id": "mdl_causal_001", "predicate": "sustains_orbit", "confidence": 0.75},
    ],
    contradictions=[
        {"claim_id": "clm_003", "contradicted_by": "clm_004", "confidence": 0.6},
    ],
    predictions=[
        {"model_id": "mdl_causal_001", "predicate": "will_continue_orbiting", "confidence": 0.9},
    ],
    missing_slots=["cause_mechanism"],
    state_deltas={"orbital_energy": "stable"},
    confidence=0.78,
)), label="causal_inference_with_predictions")

add("inference_packet", packet_to_dict(InferencePacket(
    implications=[],
    contradictions=[],
    predictions=[],
    missing_slots=[],
    state_deltas={},
    confidence=0.5,
)), label="empty_inference")


# ── DecisionPacket examples ──────────────────────────────────


add("decision_packet", packet_to_dict(DecisionPacket(
    action_kind="answer",
    action_plan=ActionPlan(
        action_kind="answer",
        selected_claim_ids=["clm_001", "clm_002"],
        selected_model_ids=["mdl_001"],
        required_slots=[],
        missing_slots=[],
        execution_allowed=True,
        confidence=0.85,
        risk=0.0,
    ),
    confidence=0.85,
    reason="sufficient evidence with high confidence",
)), label="answer_decision")

add("decision_packet", packet_to_dict(DecisionPacket(
    action_kind="ask",
    action_plan=ActionPlan(
        action_kind="ask",
        required_slots=["entity_id"],
        missing_slots=["entity_id"],
        execution_allowed=True,
        confidence=0.9,
        risk=0.0,
    ),
    confidence=0.9,
    reason="missing required slot: entity_id",
)), label="ask_for_missing_slot")

add("decision_packet", packet_to_dict(DecisionPacket(
    action_kind="abstain",
    action_plan=ActionPlan(
        action_kind="abstain",
        execution_allowed=False,
        confidence=0.4,
        risk=0.5,
    ),
    confidence=0.4,
    reason="insufficient evidence (confidence=0.30)",
)), label="abstain_decision")

add("decision_packet", packet_to_dict(DecisionPacket(
    action_kind="remember",
    action_plan=ActionPlan(
        action_kind="remember",
        selected_claim_ids=["clm_new_001"],
        execution_allowed=True,
        confidence=0.7,
        risk=0.1,
    ),
    confidence=0.7,
    reason="user explicitly requested save",
)), label="remember_decision")

add("decision_packet", packet_to_dict(DecisionPacket(
    action_kind="update",
    action_plan=ActionPlan(
        action_kind="update",
        selected_claim_ids=["clm_001"],
        execution_allowed=True,
        confidence=0.8,
        risk=0.05,
    ),
    confidence=0.8,
    reason="new evidence supersedes old claim",
)), label="update_decision")


# ── write ─────────────────────────────────────────────────────

def main() -> None:
    path = "generated/gold_examples.jsonl"
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in _GOLD_EXAMPLES:
            f.write(json.dumps(ex, default=str) + "\n")
    print(f"Wrote {len(_GOLD_EXAMPLES)} gold examples to {path}")


if __name__ == "__main__":
    main()
