"""Enforce deletion and zero historical execution routes."""
from pathlib import Path

from cemm_authoritative_hybrid.foundation_audit import (
    reachable_modules, verify_retirement,
)

REPO = Path(__file__).resolve().parents[2]


def test_no_archived_root_runtime_or_lineage_snapshots():
    verify_retirement(REPO)


def test_single_foundation_entrypoint_never_reaches_unadmitted_models():
    modules = reachable_modules()
    assert {"foundation", "bootstrap", "runtime", "proposal", "verifier",
            "expressions", "r3_kernel", "r3_effects", "r3_response"} <= modules
    assert "model" not in modules
    assert "realization" not in modules
    assert "training" not in modules
    assert "learning" not in modules
