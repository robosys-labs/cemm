"""R4.1 SR1 reviewed scenario source-universe hard-cut tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.episodes import ScenarioCase
from cemm_authoritative_hybrid.gaps import GapKind
from cemm_authoritative_hybrid.r4_contracts import ReviewedScenario


ROOT = Path(__file__).parents[1]
SCENARIOS_PATH = ROOT / "data" / "scenarios" / "use_cases.jsonl"


def _rows() -> tuple[dict[str, object], ...]:
    return tuple(
        json.loads(line)
        for line in SCENARIOS_PATH.read_text(encoding="utf-8").splitlines()
    )


def _cases() -> tuple[ScenarioCase, ...]:
    return tuple(ScenarioCase.from_dict(row) for row in _rows())


def test_sr1_every_gap_kind_is_owned_by_a_structured_gap_assertion() -> None:
    gap_kinds = {
        assertion["gap_kind"]
        for case in _cases()
        for assertion in case.semantic_assertions
        if assertion.get("kind") == "gap"
    }
    assert gap_kinds == {kind.value for kind in GapKind}


def test_sr1_structured_gap_assertions_use_only_closed_gap_kinds() -> None:
    valid_kinds = {kind.value for kind in GapKind}
    for case in _cases():
        for assertion in case.semantic_assertions:
            if assertion.get("kind") == "gap":
                assert assertion["gap_kind"] in valid_kinds, (
                    f"{case.scenario_ref}: invalid gap kind {assertion['gap_kind']}"
                )


def test_sr1_semantic_episode_source_gap_kinds_are_valid() -> None:
    valid_kinds = {kind.value for kind in GapKind}
    for case in _cases():
        for assertion in case.semantic_assertions:
            if assertion.get("kind") == "gap":
                assert assertion["gap_kind"] in valid_kinds, (
                    f"{case.scenario_ref} has invalid gap kind: "
                    f"{assertion['gap_kind']}"
                )


def test_sr1_expected_gap_kind_is_rejected_as_duplicate_truth() -> None:
    rows = _rows()
    assert all("expected_gap_kind" not in row for row in rows)
    tampered = dict(rows[0])
    tampered["expected_gap_kind"] = None
    with pytest.raises(ValueError, match="unknown field"):
        ReviewedScenario.from_dict(tampered)


def test_sr1_gap_truth_cannot_be_mixed_or_duplicated() -> None:
    base = {
        "scenario_ref": "scenario:invalid-gap",
        "review_status": "reviewed",
        "competency_category": "gap_kinds",
        "surface_examples": ["surface"],
        "metadata": {},
    }
    gap = {"kind": "gap", "gap_kind": "proposal", "description": "blocked"}
    for assertions in (
        [gap, dict(gap)],
        [gap, {"kind": "designates", "surface": "x", "target": "entity:x"}],
        [gap, {"kind": "adversarial", "attack": "unknown_operator"}],
    ):
        with pytest.raises(ValueError, match="gap.*mixed|multiple.*gap"):
            ReviewedScenario.from_dict({**base, "semantic_assertions": assertions})


__cemm_test_inventory__ = {'tests/test_r4_source_universe.py::test_sr1_every_gap_kind_is_owned_by_a_structured_gap_assertion': {'activation_phase': 'R4',
                                                                                                      'assertion_ref': 'assertion:scenario-coverage-every-gap-kind-represented',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R4.1-SR1',
                                                                                                      'owner_ref': 'expected-contract',
                                                                                                      'source_ast_sha256': '80c9b4661dc6723b755c5cd48ec0f26b31f5367f591e2db5b81ced49d117eeb2',
                                                                                                      'supersedes_node_id': 'tests/test_scenario_coverage.py::test_every_gap_kind_represented'},
 'tests/test_r4_source_universe.py::test_sr1_structured_gap_assertions_use_only_closed_gap_kinds': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:scenario-coverage-gap-kind-scenarios-have-valid-kinds',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R4.1-SR1',
                                                                                                    'owner_ref': 'expected-contract',
                                                                                                    'source_ast_sha256': '784be262bb089c09a8230e5d62ebdb090a254b41737c836e8e3c76af728477a1',
                                                                                                    'supersedes_node_id': 'tests/test_scenario_coverage.py::test_gap_kind_scenarios_have_valid_kinds'},
 'tests/test_r4_source_universe.py::test_sr1_semantic_episode_source_gap_kinds_are_valid': {'activation_phase': 'R4',
                                                                                            'assertion_ref': 'assertion:semantic-episode-scenario-gap-kinds-are-valid',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R4.1-SR1',
                                                                                            'owner_ref': 'expected-contract',
                                                                                            'source_ast_sha256': '0b6cf825c5c295637822dd576c3abc527d9355722470d8216af99e0d06079fce',
                                                                                            'supersedes_node_id': 'tests/test_semantic_episode.py::test_scenario_gap_kinds_are_valid'},
 'tests/test_r4_source_universe.py::test_sr1_expected_gap_kind_is_rejected_as_duplicate_truth': {'activation_phase': 'R4',
                                                                                                 'assertion_ref': 'assertion:r4-sr1-expected-gap-kind-duplicate-truth-rejected',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R4.1-SR1',
                                                                                                 'owner_ref': 'expected-contract',
                                                                                                 'source_ast_sha256': 'b41fa53fca4e81cdeacf9a73e2426681efb0e68a6ce790c718543069121c481f'},
 'tests/test_r4_source_universe.py::test_sr1_gap_truth_cannot_be_mixed_or_duplicated': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:r4-sr1-gap-truth-mixed-or-duplicate-rejected',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R4.1-SR1',
                                                                                        'owner_ref': 'expected-contract',
                                                                                        'source_ast_sha256': 'c123a408f5c55bfbbc2f1172cb7202505a99570013e5e11f66028b7a81158c8b'}}
