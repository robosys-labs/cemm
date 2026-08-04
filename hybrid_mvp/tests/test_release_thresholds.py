"""Release threshold tests for the CEMM evaluation report (M4 Task 4).

These tests verify that the full evaluation report meets every release
threshold specified in the MVP acceptance contract. No metric is inferred
from response-string equality — every assertion checks semantic structure,
proof, coverage, safety, or ablation behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_JSON = ROOT / "artifacts" / "evaluation" / "CEMM_EVALUATION.json"


@pytest.fixture(scope="module")
def report():
    """Load the evaluation report from the canonical JSON artifact."""
    from cemm_authoritative_hybrid.evaluation import EvaluationReport

    if not EVALUATION_JSON.exists():
        pytest.fail(
            f"CEMM_EVALUATION.json not found at {EVALUATION_JSON}. "
            "Run: python scripts/evaluate_cemm.py"
        )
    return EvaluationReport.from_json(EVALUATION_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Release threshold assertions
# ---------------------------------------------------------------------------


def test_release_thresholds(report):
    """Every release threshold from the MVP acceptance contract must be met."""
    assert report.illegal_program_rejection == 1.0
    assert report.effect_safety_accuracy == 1.0
    assert report.exact_program_accuracy >= 0.90
    assert report.end_to_end_accuracy >= 0.95
    assert report.abstention_precision >= 0.95
    assert report.abstention_recall >= 0.95
    assert report.expected_calibration_error <= 0.08
    assert report.realization_equivalence == 1.0
    assert report.proposal_zero_weight_accuracy <= 0.50
    assert report.proposal_weight_accuracy_drop >= 0.30
    assert report.realizer_zero_weight_accuracy <= 0.50
    assert report.realizer_weight_accuracy_drop >= 0.30
    assert report.bootstrap_delegate_calls == 0
    assert report.unreviewed_atom_creations == 0
    assert report.raw_surface_dispatches == 0


def test_report_has_per_gap_kind_metrics(report):
    """The report carries per-gap-kind metrics."""
    assert report.per_gap_kind_metrics is not None
    assert len(report.per_gap_kind_metrics) > 0


def test_report_has_per_competency_metrics(report):
    """The report carries per-competency metrics."""
    assert report.per_competency_metrics is not None
    assert len(report.per_competency_metrics) > 0


def test_report_status_is_passed(report):
    """A failed gate makes the report status 'failed'; no aggregate hides it."""
    assert report.status == "passed"
