from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.cemm_trainer import render_prompt


def test_render_prompt_with_braces_in_payload() -> None:
    """render_prompt must not crash when payload JSON contains curly braces
    inside string values. str.format() should handle this correctly since
    {payload} is a keyword argument substitution."""
    payload_json = '{"context_kernel": {"id": "test", "greeting": "hello {world}"}}'
    agent, system, user = render_prompt("uol_mapping", payload_json)
    assert agent == "uol_mapper"
    assert system
    assert "hello {world}" in user or "{world}" in user
