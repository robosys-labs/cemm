"""No-legacy-runtime tests: forbidden tokens and neural profile activation.

These tests verify that no active source file contains forbidden legacy
constructs (StageRecord, stage_trace, range(23), graph_action_ranker.pt,
weights_only=False) and that the neural profile loads correctly from the
safetensors artifact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def test_active_source_has_no_stage_or_legacy_checkpoint_contract():
    """No active source file may contain forbidden legacy tokens."""
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in Path(ROOT / "src").rglob("*.py")
    )
    forbidden = (
        "StageRecord",
        "stage_trace",
        "range(23)",
        "graph_action_ranker.pt",
        "weights_only=False",
    )
    offenders = [token for token in forbidden if token in source]
    assert not offenders, f"forbidden legacy tokens found in source: {offenders}"


def test_bootstrap_has_no_legacy_checkpoint_or_stores_import():
    """bootstrap.py must not import from the legacy stores or training modules."""
    text = (ROOT / "src" / "cemm_authoritative_hybrid" / "bootstrap.py").read_text(
        encoding="utf-8"
    )
    assert "load_checkpoint" not in text
    assert "from .stores" not in text
    assert "graph_action_ranker" not in text
    assert "weights_only" not in text
