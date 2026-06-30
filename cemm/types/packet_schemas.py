from __future__ import annotations

PACKET_SCHEMAS: dict[str, dict] = {
    "semantic_event_graph": {
        "type": "object",
        "required": ["id", "source_signal_ids", "context_id"],
        "properties": {
            "id": {"type": "string", "description": "Unique graph identifier"},
            "source_signal_ids": {"type": "array", "items": {"type": "string"}},
            "context_id": {"type": "string"},
            "entity_refs": {"type": "array", "items": {"type": "object"}},
            "processes": {"type": "array", "items": {"type": "object"}},
            "states": {"type": "array", "items": {"type": "object"}},
            "claim_refs": {"type": "array", "items": {"type": "string"}},
            "claim_candidates": {"type": "array", "items": {"type": "object"}},
            "model_refs": {"type": "array", "items": {"type": "string"}},
            "action_refs": {"type": "array", "items": {"type": "string"}},
            "temporal_edges": {"type": "array", "items": {"type": "object"}},
            "causal_edges": {"type": "array", "items": {"type": "object"}},
            "permission_scope": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "version": {"type": "string", "pattern": "^cemm\\.semantic_event_graph\\.v1$"},
        },
    },
    "semantic_answer_graph": {
        "type": "object",
        "required": ["id", "intent", "source_signal_ids", "context_id"],
        "properties": {
            "id": {"type": "string"},
            "intent": {
                "type": "string",
                "enum": ["answer", "ask", "abstain", "remember", "update_claim", "simulate", "act", "reflect"],
            },
            "source_signal_ids": {"type": "array", "items": {"type": "string"}},
            "context_id": {"type": "string"},
            "selected_claim_ids": {"type": "array", "items": {"type": "string"}},
            "selected_model_ids": {"type": "array", "items": {"type": "string"}},
            "entity_refs": {"type": "array", "items": {"type": "object"}},
            "processes": {"type": "array", "items": {"type": "object"}},
            "states": {"type": "array", "items": {"type": "object"}},
            "causal_edges": {"type": "array", "items": {"type": "object"}},
            "temporal_edges": {"type": "array", "items": {"type": "object"}},
            "action_candidates": {"type": "array", "items": {"type": "object"}},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "uncertainty_reasons": {"type": "array", "items": {"type": "string"}},
            "permission_scope": {"type": "string"},
            "verification": {
                "type": "object",
                "properties": {
                    "supported": {"type": "boolean"},
                    "verification_type": {"type": "string", "enum": ["hard", "soft", "none"]},
                    "confidence": {"type": "number"},
                    "unsupported_spans": {"type": "array", "items": {"type": "string"}},
                },
            },
            "version": {"type": "string", "pattern": "^cemm\\.semantic_answer_graph\\.v1$"},
        },
    },
    "grounded_graph": {
        "type": "object",
        "required": ["semantic_event_graph_id"],
        "properties": {
            "semantic_event_graph_id": {"type": "string"},
            "entity_ids": {"type": "array", "items": {"type": "string"}},
            "resolved_time_refs": {"type": "array", "items": {"type": "string"}},
            "resolved_location_ids": {"type": "array", "items": {"type": "string"}},
            "active_frame_ids": {"type": "array", "items": {"type": "string"}},
            "permission": {"type": "string"},
            "missing_slots": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "version": {"type": "string", "pattern": "^cemm\\.grounded_graph\\.v1$"},
        },
    },
    "memory_packet": {
        "type": "object",
        "properties": {
            "selected_signal_ids": {"type": "array", "items": {"type": "string"}},
            "selected_claim_ids": {"type": "array", "items": {"type": "string"}},
            "selected_model_ids": {"type": "array", "items": {"type": "string"}},
            "ranking_trace": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["candidate_id", "score"],
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "score": {"type": "number"},
                        "reason": {"type": "string"},
                    },
                },
            },
            "confidence": {"type": "number"},
            "version": {"type": "string", "pattern": "^cemm\\.memory_packet\\.v1$"},
        },
    },
    "inference_packet": {
        "type": "object",
        "properties": {
            "implications": {"type": "array", "items": {"type": "object"}},
            "contradictions": {"type": "array", "items": {"type": "object"}},
            "predictions": {"type": "array", "items": {"type": "object"}},
            "missing_slots": {"type": "array", "items": {"type": "string"}},
            "state_deltas": {"type": "object"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "version": {"type": "string", "pattern": "^cemm\\.inference_packet\\.v1$"},
        },
    },
    "decision_packet": {
        "type": "object",
        "required": ["action_kind"],
        "properties": {
            "action_kind": {
                "type": "string",
                "enum": ["answer", "ask", "remember", "update", "act", "abstain"],
            },
            "semantic_answer_graph_id": {"type": "string", "default": None},
            "action_plan": {
                "type": "object",
                "properties": {
                    "action_kind": {"type": "string"},
                    "required_slots": {"type": "array", "items": {"type": "string"}},
                    "missing_slots": {"type": "array", "items": {"type": "string"}},
                    "selected_claim_ids": {"type": "array", "items": {"type": "string"}},
                    "selected_model_ids": {"type": "array", "items": {"type": "string"}},
                    "tool_id": {"type": "string"},
                    "execution_allowed": {"type": "boolean"},
                    "confidence": {"type": "number"},
                    "risk": {"type": "number"},
                },
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
            "version": {"type": "string", "pattern": "^cemm\\.decision_packet\\.v1$"},
        },
    },
}


def get_schema(packet_type: str) -> dict | None:
    return PACKET_SCHEMAS.get(packet_type)
