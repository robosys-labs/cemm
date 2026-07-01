from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.cemm_seed_generator import ALLOWED_TASK_TYPES


def test_seed_spec_categories_use_allowed_task_types() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    spec_path = os.path.join(repo_root, "cemm", "cemm_seed_spec.json")
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    categories = spec["categories"]
    assert categories
    for category in categories:
        assert category["name"]
        assert category["task_types"]
        for task_type in category["task_types"]:
            assert task_type in ALLOWED_TASK_TYPES, f"{category['name']} uses invalid task_type {task_type}"
    names = {c["name"] for c in categories}
    assert "noisy_casual_conversation" in names
    assert "self_state_and_reflection" in names
