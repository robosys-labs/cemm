"""TL1 deterministic typed feature extractor.

Extracts typed features from any CEMM packet.
Output is a flat list of (namespace, key, value) triples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Feature:
    namespace: str
    key: str
    value: float = 1.0


def _cnf(val: Any) -> float:
    """Extract confidence from a value or return 1.0"""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        return float(val.get("confidence", 1.0))
    return 1.0


def _bucket(v: float, n: int = 4) -> str:
    """Bucket a float into n equal-width buckets 0..1."""
    v = max(0.0, min(1.0, v))
    idx = min(int(v * n), n - 1)
    return f"{idx / n:.2f}-{(idx + 1) / n:.2f}"


def extract_semantic_event_graph(packet: dict) -> list[Feature]:
    feats: list[Feature] = []
    for ent in packet.get("entity_refs", []):
        feats.append(Feature("entity_type", str(ent.get("kind", "unknown")), _cnf(ent)))
        name = ent.get("name", "")
        if name:
            feats.append(Feature("entity_name", str(name).casefold()))
    for proc in packet.get("processes", []):
        fk = proc.get("frame_key", "")
        if fk:
            feats.append(Feature("process_frame_key", str(fk), _cnf(proc)))
        for role in proc.get("participants", []):
            feats.append(Feature("participant_role", str(role.get("role", "unknown"))))
    for st in packet.get("states", []):
        sk = st.get("state_key", "")
        if sk:
            feats.append(Feature("state_key", str(sk)))
        holder = st.get("holder", "")
        if holder:
            feats.append(Feature("state_holder", str(holder)))
        dim = st.get("dimension", "")
        if dim:
            feats.append(Feature("state_dimension", str(dim)))
    for edge in packet.get("temporal_edges", []):
        feats.append(Feature("temporal_relation", str(edge.get("relation", "unknown")), _cnf(edge)))
    for edge in packet.get("causal_edges", []):
        feats.append(Feature("causal_relation", str(edge.get("relation", "unknown")), _cnf(edge)))
    feats.append(Feature("confidence_bucket", _bucket(packet.get("confidence", 0.5))))
    return feats


def extract_semantic_answer_graph(packet: dict) -> list[Feature]:
    feats: list[Feature] = []
    feats.append(Feature("sag_intent", str(packet.get("intent", "unknown"))))
    for ent in packet.get("entity_refs", []):
        feats.append(Feature("entity_type", str(ent.get("kind", "unknown")), _cnf(ent)))
    for proc in packet.get("processes", []):
        fk = proc.get("frame_key", "")
        if fk:
            feats.append(Feature("process_frame_key", str(fk), _cnf(proc)))
    for edge in packet.get("temporal_edges", []):
        feats.append(Feature("temporal_relation", str(edge.get("relation")), _cnf(edge)))
    for edge in packet.get("causal_edges", []):
        feats.append(Feature("causal_relation", str(edge.get("relation")), _cnf(edge)))
    ver = packet.get("verification", {})
    if isinstance(ver, dict):
        feats.append(Feature("verification_type", str(ver.get("verification_type", "none"))))
        feats.append(Feature("verification_supported", str(ver.get("supported", False))))
    feats.append(Feature("confidence_bucket", _bucket(packet.get("confidence", 0.5))))
    return feats


def extract_grounded_graph(packet: dict) -> list[Feature]:
    feats: list[Feature] = []
    for fid in packet.get("active_frame_ids", []):
        feats.append(Feature("active_frame_id", str(fid)))
    for ent_id in packet.get("entity_ids", []):
        feats.append(Feature("grounded_entity", str(ent_id)))
    for loc_id in packet.get("resolved_location_ids", []):
        feats.append(Feature("resolved_location", str(loc_id)))
    for slot in packet.get("missing_slots", []):
        feats.append(Feature("missing_slot", str(slot)))
    feats.append(Feature("confidence_bucket", _bucket(packet.get("confidence", 0.0))))
    return feats


def extract_memory_packet(packet: dict) -> list[Feature]:
    feats: list[Feature] = []
    for entry in packet.get("ranking_trace", []):
        cid = entry.get("candidate_id", "")
        if cid:
            feats.append(Feature("memory_candidate_id", str(cid)))
        reason = entry.get("reason", "")
        if reason:
            feats.append(Feature("ranking_reason", str(reason)))
        score = entry.get("score", 0.0)
        feats.append(Feature("ranking_score_bucket", _bucket(score)))
    for sig_id in packet.get("selected_signal_ids", []):
        feats.append(Feature("selected_signal", str(sig_id)))
    for clm_id in packet.get("selected_claim_ids", []):
        feats.append(Feature("selected_claim", str(clm_id)))
    feats.append(Feature("confidence_bucket", _bucket(packet.get("confidence", 0.0))))
    return feats


def extract_inference_packet(packet: dict) -> list[Feature]:
    feats: list[Feature] = []
    for impl in packet.get("implications", []):
        feats.append(Feature("implication_predicate", str(impl.get("predicate", "unknown")), _cnf(impl)))
    for pred in packet.get("predictions", []):
        feats.append(Feature("prediction_predicate", str(pred.get("predicate", "unknown")), _cnf(pred)))
    for contra in packet.get("contradictions", []):
        feats.append(Feature("contradiction", str(contra.get("claim_id", "unknown")), _cnf(contra)))
    for slot in packet.get("missing_slots", []):
        feats.append(Feature("missing_slot", str(slot)))
    for key in packet.get("state_deltas", {}):
        feats.append(Feature("state_delta", str(key)))
    feats.append(Feature("confidence_bucket", _bucket(packet.get("confidence", 0.0))))
    return feats


def extract_decision_packet(packet: dict) -> list[Feature]:
    feats: list[Feature] = []
    feats.append(Feature("action_kind", str(packet.get("action_kind", "unknown"))))
    ap = packet.get("action_plan", {})
    if isinstance(ap, dict):
        for clm_id in ap.get("selected_claim_ids", []):
            feats.append(Feature("action_selected_claim", str(clm_id)))
        for slot in ap.get("missing_slots", []):
            feats.append(Feature("action_missing_slot", str(slot)))
        for slot in ap.get("required_slots", []):
            feats.append(Feature("action_required_slot", str(slot)))
        feats.append(Feature("execution_allowed", str(ap.get("execution_allowed", False))))
        feats.append(Feature("action_risk_bucket", _bucket(ap.get("risk", 0.0))))
    feats.append(Feature("confidence_bucket", _bucket(packet.get("confidence", 0.0))))
    return feats


_EXTRACTORS: dict[str, callable] = {
    "semantic_event_graph": extract_semantic_event_graph,
    "semantic_answer_graph": extract_semantic_answer_graph,
    "grounded_graph": extract_grounded_graph,
    "memory_packet": extract_memory_packet,
    "inference_packet": extract_inference_packet,
    "decision_packet": extract_decision_packet,
}


def extract_features(packet: dict, task_type: str) -> list[Feature]:
    fn = _EXTRACTORS.get(task_type)
    if fn is None:
        return [Feature("unknown_task_type", task_type)]
    return fn(packet)
