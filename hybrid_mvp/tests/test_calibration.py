"""Tests for model calibration (M4 Task 3).

These tests verify that:
- Calibration uses validation data ONLY (input_hash == validation sha256).
- The expected calibration error is <= 0.08.
- The calibration receipt pins the proposal and realizer model identities.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.partitions import load_partition_manifest

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_PATH = ROOT / "artifacts" / "calibration.json"
PARTITIONS_DIR = ROOT / "data" / "partitions"


@pytest.fixture
def manifests() -> SimpleNamespace:
    """Collect partition manifests for calibration assertions."""
    pm = load_partition_manifest(PARTITIONS_DIR / "manifest.json")
    return SimpleNamespace(
        validation=SimpleNamespace(sha256=pm.validation_sha256),
        train=SimpleNamespace(sha256=pm.train_sha256),
        test=SimpleNamespace(sha256=pm.test_sha256),
    )


@pytest.fixture
def calibration_receipt() -> dict:
    """Load the calibration receipt."""
    assert CALIBRATION_PATH.exists(), f"Missing {CALIBRATION_PATH}"
    return json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))


def test_calibration_uses_validation_only(calibration_receipt, manifests):
    """The calibration input hash must equal the validation partition hash."""
    assert calibration_receipt["input_hash"] == manifests.validation.sha256
    # The calibration must NOT reference train or test hashes.
    text = json.dumps(calibration_receipt, sort_keys=True)
    assert manifests.train.sha256 not in text
    assert manifests.test.sha256 not in text


def test_calibration_error_within_threshold(calibration_receipt):
    """The expected calibration error must be <= 0.08."""
    ece = calibration_receipt["expected_calibration_error"]
    assert ece <= 0.08
    assert ece >= 0.0


def test_calibration_pins_model_identities(calibration_receipt):
    """The calibration receipt pins both model identities."""
    assert calibration_receipt["proposal_model_identity"]
    assert calibration_receipt["realizer_model_identity"]


def test_calibration_records_confidence_bins(calibration_receipt):
    """The calibration receipt records confidence bins for audit."""
    assert "bins" in calibration_receipt
    assert isinstance(calibration_receipt["bins"], list)
    assert len(calibration_receipt["bins"]) > 0
