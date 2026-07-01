from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from cemm.cemm_trainer import PROMPTS, render_prompt, validate_training_record


def _payload_for(task_type: str) -> dict:
    payload = {
        "context_kernel": {"id": "ctx1", "permission": {"scope": "local_training"}},
        "input_signal_id": "sig1",
        "input_text": "hello",
        "output_text": "hello",
        "semantic_event_graph": {
            "id": "seg1",
            "source_signal_ids": ["sig1"],
            "context_id": "ctx1",
            "entity_refs": [],
            "processes": [{"kind": "process", "frame_key": "greeting", "confidence": 0.8}],
            "states": [],
            "claim_refs": [],
            "claim_candidates": [],
            "model_refs": [],
            "action_refs": [],
            "temporal_edges": [],
            "causal_edges": [],
            "permission_scope": "local_training",
            "confidence": 0.8,
        },
        "semantic_answer_graph": {
            "id": "sag1",
            "intent": "answer",
            "source_signal_ids": ["sig1"],
            "context_id": "ctx1",
            "selected_claim_ids": [],
            "selected_model_ids": [],
            "confidence": 0.8,
            "permission_scope": "local_training",
        },
        "memory_packet": {
            "id": "mem1",
            "selected_signal_ids": ["sig1"],
            "selected_claim_ids": [],
            "selected_model_ids": [],
            "ranking_trace": [],
            "confidence": 0.5,
        },
        "inference_packet": {
            "id": "inf1",
            "implications": [],
            "contradictions": [],
            "predictions": [],
            "missing_slots": [],
            "state_deltas": {},
            "inference_graph_input_signal_ids": ["sig1"],
            "inference_graph_output_model_ids": [],
            "confidence": 0.5,
        },
        "selected_evidence": {"selected_claim_ids": [], "selected_model_ids": []},
        "self_state": {"self_id": "self_main", "mode": "assistant"},
    }
    if task_type == "next_event_prediction":
        payload["recent_event_graphs"] = [payload["semantic_event_graph"]]
    if task_type == "verifier_calibration":
        payload["selected_evidence"] = {"selected_claim_ids": [], "selected_model_ids": []}
    return payload


@pytest.mark.parametrize("task_type", sorted(PROMPTS))
def test_all_prompts_render_without_missing_format_keys(task_type: str) -> None:
    payload = _payload_for(task_type)
    try:
        validate_training_record(task_type, payload)
    except ValueError:
        pass
    agent, system, user = render_prompt(task_type, json.dumps(payload))
    assert agent
    assert system
    assert user
    # No unresolved single-key placeholders (e.g. literal "{payload}") should remain;
    # curly braces from embedded JSON content are expected and fine.
    assert not re.search(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", user)
