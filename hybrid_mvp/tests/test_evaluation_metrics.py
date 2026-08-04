"""Evaluation metric computation tests (M4 Task 4).

Verifies that the :class:`Evaluator` correctly measures semantic accuracy,
safety, ablation, and gap-owner metrics by running the runtime on test
episodes. No metric is inferred from response-string equality.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_EPISODES = ROOT / "data" / "partitions" / "test.jsonl"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def evaluator():
    """Build an Evaluator wired with the release runtime and test episodes."""
    from cemm_authoritative_hybrid.evaluation import Evaluator, build_release_runtime

    runtime = build_release_runtime(ROOT)
    return Evaluator(runtime=runtime, test_episodes_path=TEST_EPISODES, root=ROOT)


@pytest.fixture(scope="module")
def report(evaluator):
    """Run the full evaluation and return the report."""
    return evaluator.evaluate()


# ---------------------------------------------------------------------------
# Metric tests
# ---------------------------------------------------------------------------


def test_evaluator_loads_test_episodes(evaluator):
    """The evaluator loads exactly the test partition episodes."""
    assert len(evaluator._episodes) == 78


def test_illegal_program_rejection_is_perfect(report):
    """The verifier rejects every illegal program."""
    assert report.illegal_program_rejection == 1.0


def test_effect_safety_accuracy_is_perfect(report):
    """Every executed effect is safe (no unverified world mutation)."""
    assert report.effect_safety_accuracy == 1.0


def test_exact_program_accuracy_meets_threshold(report):
    """The proposer produces the correct program >= 90% of the time."""
    assert report.exact_program_accuracy >= 0.90


def test_end_to_end_accuracy_meets_threshold(report):
    """The full cycle produces the correct result >= 95% of the time."""
    assert report.end_to_end_accuracy >= 0.95


def test_abstention_precision_meets_threshold(report):
    """Abstention precision >= 95%."""
    assert report.abstention_precision >= 0.95


def test_abstention_recall_meets_threshold(report):
    """Abstention recall >= 95%."""
    assert report.abstention_recall >= 0.95


def test_calibration_error_within_bound(report):
    """Expected calibration error <= 0.08."""
    assert report.expected_calibration_error <= 0.08


def test_realization_equivalence_is_perfect(report):
    """The realizer produces equivalent surfaces 100% of the time."""
    assert report.realization_equivalence == 1.0


def test_proposal_zero_weight_accuracy_is_low(report):
    """Zeroed proposal weights produce <= 50% accuracy."""
    assert report.proposal_zero_weight_accuracy <= 0.50


def test_proposal_weight_accuracy_drop_is_significant(report):
    """The accuracy drop from zeroing proposal weights is >= 30%."""
    assert report.proposal_weight_accuracy_drop >= 0.30


def test_realizer_zero_weight_accuracy_is_low(report):
    """Zeroed realizer weights produce <= 50% accuracy."""
    assert report.realizer_zero_weight_accuracy <= 0.50


def test_realizer_weight_accuracy_drop_is_significant(report):
    """The accuracy drop from zeroing realizer weights is >= 30%."""
    assert report.realizer_weight_accuracy_drop >= 0.30


def test_no_bootstrap_delegate_calls(report):
    """The release path never delegates to the bootstrap proposer."""
    assert report.bootstrap_delegate_calls == 0


def test_no_unreviewed_atom_creations(report):
    """No implicit atom creation occurs during evaluation."""
    assert report.unreviewed_atom_creations == 0


def test_no_raw_surface_dispatches(report):
    """No raw surface semantic dispatch occurs during evaluation."""
    assert report.raw_surface_dispatches == 0


def test_report_serializes_to_canonical_json(report):
    """The report serializes to canonical JSON with all metrics."""
    data = json.loads(report.to_json())
    expected_keys = {
        "illegal_program_rejection",
        "effect_safety_accuracy",
        "exact_program_accuracy",
        "end_to_end_accuracy",
        "abstention_precision",
        "abstention_recall",
        "expected_calibration_error",
        "realization_equivalence",
        "proposal_zero_weight_accuracy",
        "proposal_weight_accuracy_drop",
        "realizer_zero_weight_accuracy",
        "realizer_weight_accuracy_drop",
        "bootstrap_delegate_calls",
        "unreviewed_atom_creations",
        "raw_surface_dispatches",
        "per_gap_kind_metrics",
        "per_competency_metrics",
        "status",
    }
    assert expected_keys.issubset(data.keys())
