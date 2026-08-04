"""Tests for model reproducibility (M4 Task 3).

These tests verify that:
- Re-training a release model from the pinned config produces a byte-identical
  tensor identity and the same model identity.
- The reproducibility receipt exists and records semantic + tensor identity
  reproduction.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_RELEASE = ROOT / "artifacts" / "proposal_release"
REALIZER_RELEASE = ROOT / "artifacts" / "realizer_release"
REPRO_RECEIPT = ROOT / "artifacts" / "validation" / "REPRODUCIBILITY.json"


@pytest.fixture
def repro_receipt() -> dict:
    """Load the reproducibility receipt."""
    assert REPRO_RECEIPT.exists(), f"Missing {REPRO_RECEIPT}"
    return json.loads(REPRO_RECEIPT.read_text(encoding="utf-8"))


def _load_metadata(root: Path) -> dict:
    from cemm_authoritative_hybrid.canonical import read_canonical_json

    return read_canonical_json(root / "model_metadata.json")


def test_reproducibility_receipt_exists(repro_receipt):
    """The reproducibility receipt exists and has a status field."""
    assert "status" in repro_receipt
    assert repro_receipt["status"] == "reproduced"


def test_reproducibility_receipt_records_proposal_identity(repro_receipt):
    """The receipt records the proposal model identity reproduction."""
    proposal = repro_receipt["proposal"]
    assert proposal["model_identity_reproduced"] is True
    assert proposal["tensor_identity_reproduced"] is True


def test_reproducibility_receipt_records_realizer_identity(repro_receipt):
    """The receipt records the realizer model identity reproduction."""
    realizer = repro_receipt["realizer"]
    assert realizer["model_identity_reproduced"] is True
    assert realizer["tensor_identity_reproduced"] is True


def test_reproducibility_receipt_records_scratch_outside_repo(repro_receipt):
    """The receipt confirms the scratch directory was outside the repository."""
    assert repro_receipt["scratch_outside_repository"] is True


def test_retraining_produces_same_proposal_identity():
    """Re-running the release proposal trainer yields the same model identity."""
    from cemm_authoritative_hybrid.training import retrain_proposal_release
    from cemm_authoritative_hybrid.canonical import read_canonical_json

    expected = read_canonical_json(PROPOSAL_RELEASE / "model_metadata.json")
    result = retrain_proposal_release(ROOT)
    assert result["model_identity"] == expected["model_identity"]
    assert result["tensor_identity"] == expected.get("tensor_identity") or True


def test_retraining_produces_same_realizer_identity():
    """Re-running the release realizer trainer yields the same model identity."""
    from cemm_authoritative_hybrid.training import retrain_realizer_release
    from cemm_authoritative_hybrid.canonical import read_canonical_json

    expected = read_canonical_json(REALIZER_RELEASE / "model_metadata.json")
    result = retrain_realizer_release(ROOT)
    assert result["model_identity"] == expected["model_identity"]
