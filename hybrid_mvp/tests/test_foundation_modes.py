"""Independent behavioral requirements over the existing post-VERIFY R3 owner.

The four canary modes deliberately use semantic graphs rather than a canned
utterance router. This is the structured-input half of the foundation proof.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _canaries():
    spec = importlib.util.spec_from_file_location(
        "_foundation_r3_canaries", ROOT / "scripts" / "run_r3_canaries.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_typed_observe_query_request_simulate_produce_distinct_effect_receipts(tmp_path):
    rows = _canaries().execute_canaries(ROOT, tmp_path / "r3", cases_path=None)
    by_mode = {row["semantic_mode"]: row for row in rows}
    assert set(by_mode) == {"OBSERVE", "QUERY", "REQUEST", "SIMULATE"}
    for row in rows:
        assert row["verified_meaning_ref"].startswith("verified_meaning:")
        assert row["expression_ref"]
        assert row["decision_ref"]
        assert row["effect_receipt_ref"]
        assert row["response_meaning_ref"].startswith("response_meaning:")
        assert row["effect_revision_delta"] > 0
    for mode in ("QUERY", "SIMULATE"):
        assert by_mode[mode]["world_revision_delta"] == 0
        assert by_mode[mode]["effect_kind"] == "NoEffectReceipt"
    assert by_mode["REQUEST"]["world_revision_delta"] == 0
    assert by_mode["REQUEST"]["decision_action"] != by_mode["QUERY"]["decision_action"]
