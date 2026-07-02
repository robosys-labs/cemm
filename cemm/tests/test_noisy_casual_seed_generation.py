from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.cemm_seed_generator import generate_dry_run_category, validate_and_flatten


def test_noisy_casual_seed_examples_include_graph_packets() -> None:
    category = {
        "name": "noisy_casual_chat",
        "task_types": ["uol_mapping", "pragmatic_interpretation", "context_inference", "semantic_graph_extraction"],
    }
    payload = generate_dry_run_category(category, 5)
    _, examples = validate_and_flatten(payload)
    assert examples
    for payload in examples:
        assert payload["context_kernel"]
        assert payload["semantic_event_graph"]
        assert "output_text" not in payload or payload.get("semantic_answer_graph")
