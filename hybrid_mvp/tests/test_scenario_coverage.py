"""Tests for the 210-scenario coverage matrix.

The scenario matrix covers all semantic competency categories. Each case
specifies semantic assertions rather than exact prose. Each case has a unique
scenario_ref, review_status="reviewed", a competency_category, semantic
assertions, surface examples, and an expected_gap_kind (if any).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.episodes import ScenarioCase
from cemm_authoritative_hybrid.gaps import GapKind

ROOT = Path(__file__).parents[1]
SCENARIOS_PATH = ROOT / "data" / "scenarios" / "use_cases.jsonl"

# The full set of competency categories that must be covered.
COMPETENCY_CATEGORIES = [
    "designation_definition",
    "reordered_constructions",
    "polysemy",
    "modality",
    "negation_scope",
    "recursive_family_proof",
    "participant_reference",
    "reported_speech",
    "temporal_state",
    "reviewed_sensor_operation_evidence",
    "transition_simulation",
    "learning_security",
    "capability_policy_adapter_effect",
    "contradiction",
    "gap_kinds",
    "multilingual_aliases",
    "adversarial_programs",
    "restart",
    "realization_equivalence",
]


def _load_scenarios() -> list[ScenarioCase]:
    assert SCENARIOS_PATH.exists(), f"Missing {SCENARIOS_PATH}"
    cases: list[ScenarioCase] = []
    for line in SCENARIOS_PATH.read_text(encoding="utf-8").strip().splitlines():
        cases.append(ScenarioCase.from_dict(json.loads(line)))
    return cases


# ---------------------------------------------------------------------------
# File existence and validity
# ---------------------------------------------------------------------------


def test_scenarios_file_exists():
    assert SCENARIOS_PATH.exists(), f"Missing {SCENARIOS_PATH}"


def test_scenarios_file_is_valid_jsonl():
    lines = SCENARIOS_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 210
    for line in lines:
        data = json.loads(line)
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Count and uniqueness
# ---------------------------------------------------------------------------


def test_210_unique_reviewed_cases():
    cases = _load_scenarios()
    assert len(cases) == 210
    refs = [case.scenario_ref for case in cases]
    assert len(set(refs)) == 210, "Duplicate scenario_ref values"
    assert all(case.review_status == "reviewed" for case in cases)


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


def test_each_case_has_required_fields():
    cases = _load_scenarios()
    for case in cases:
        assert case.scenario_ref, "Missing scenario_ref"
        assert case.review_status == "reviewed"
        assert case.competency_category, f"{case.scenario_ref}: missing category"
        assert case.semantic_assertions, f"{case.scenario_ref}: no assertions"
        assert case.surface_examples is not None, (
            f"{case.scenario_ref}: no surface_examples"
        )


def test_each_case_specifies_semantic_assertions_not_prose():
    """Each case specifies semantic assertions rather than exact prose."""
    cases = _load_scenarios()
    for case in cases:
        # semantic_assertions is a list of structured assertion dicts, not
        # bare prose strings.
        for assertion in case.semantic_assertions:
            assert isinstance(assertion, dict), (
                f"{case.scenario_ref}: assertion is not structured: {assertion}"
            )
            assert "kind" in assertion, (
                f"{case.scenario_ref}: assertion missing 'kind': {assertion}"
            )


# ---------------------------------------------------------------------------
# Competency category coverage
# ---------------------------------------------------------------------------


def test_all_competency_categories_covered():
    cases = _load_scenarios()
    categories = Counter(case.competency_category for case in cases)
    for cat in COMPETENCY_CATEGORIES:
        assert cat in categories, f"Missing competency category: {cat}"
        assert categories[cat] > 0, f"Empty competency category: {cat}"


def test_every_gap_kind_represented():
    """Every gap kind has at least one scenario with that expected_gap_kind."""
    cases = _load_scenarios()
    gap_kinds_in_scenarios = {
        case.expected_gap_kind
        for case in cases
        if case.expected_gap_kind is not None
    }
    for kind in GapKind:
        assert kind.value in gap_kinds_in_scenarios, (
            f"No scenario for gap kind: {kind.value}"
        )


def test_gap_kind_scenarios_have_valid_kinds():
    cases = _load_scenarios()
    valid = {kind.value for kind in GapKind}
    for case in cases:
        if case.expected_gap_kind is not None:
            assert case.expected_gap_kind in valid, (
                f"{case.scenario_ref}: invalid gap kind {case.expected_gap_kind}"
            )


# ---------------------------------------------------------------------------
# Scenario ref format
# ---------------------------------------------------------------------------


def test_scenario_refs_are_well_formed():
    cases = _load_scenarios()
    for case in cases:
        assert case.scenario_ref.startswith("scenario:"), (
            f"Bad scenario_ref prefix: {case.scenario_ref}"
        )
