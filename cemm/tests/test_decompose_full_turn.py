from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.cemm_trainer import _decompose_full_turn, PROMPTS


def test_decompose_includes_temporal_relation_derivation() -> None:
    """When SEG has temporal_edges, decomposition should include
    temporal_relation_derivation task type."""
    turn = {
        "payload": {
            "context_kernel": {"id": "ck1"},
            "input_text": "first I ate then I slept",
            "output_text": "user ate then slept",
            "semantic_event_graph": {
                "id": "seg1",
                "entities": [],
                "events": [{"id": "e1"}, {"id": "e2"}],
                "temporal_edges": [
                    {"source": "e1", "target": "e2", "relation": "before"},
                ],
                "processes": [],
            },
            "semantic_answer_graph": {"id": "sag1", "intent": "answer"},
            "selected_evidence": {},
        }
    }
    sub_examples = _decompose_full_turn(turn)
    seen = {t for t, _ in sub_examples}
    assert "temporal_relation_derivation" in seen, (
        f"Expected temporal_relation_derivation in decomposition, got: {sorted(seen)}"
    )


def test_decompose_includes_frame_classification() -> None:
    """When SEG has processes with frame_keys, decomposition should include
    frame_classification task type."""
    turn = {
        "payload": {
            "context_kernel": {"id": "ck1"},
            "input_text": "schedule a meeting",
            "output_text": "meeting scheduled",
            "semantic_event_graph": {
                "id": "seg1",
                "entities": [],
                "events": [],
                "temporal_edges": [],
                "processes": [
                    {"frame_key": "schedule", "participants": ["user"]},
                ],
            },
            "semantic_answer_graph": {"id": "sag1", "intent": "answer"},
            "selected_evidence": {},
        }
    }
    sub_examples = _decompose_full_turn(turn)
    seen = {t for t, _ in sub_examples}
    assert "frame_classification" in seen, (
        f"Expected frame_classification in decomposition, got: {sorted(seen)}"
    )
