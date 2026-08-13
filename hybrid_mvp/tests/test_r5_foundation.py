from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from cemm_authoritative_hybrid.governance import (
    effective_replay_status,
    read_hash_chain,
)


ROOT = Path(__file__).parents[1]
FOUNDATION_PATH = ROOT / "configs" / "r5_foundation.json"
SCHEMA_PATH = ROOT / "schemas" / "r5_foundation.schema.json"
EXPECTED_OWNERS = [
    "artifact-contract",
    "data-isolation",
    "legacy-hard-cut",
    "proposal-contract",
    "realization-contract",
]
EXPECTED_ACCESS_CLASSES = ["calibration", "frozen_test", "selection", "train"]


__cemm_test_inventory__ = {
    "tests/test_r5_foundation.py::test_r5_foundation_contract_is_strict_and_exact": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-foundation-contract-strict-and-exact",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "c60242b6e90fbc482bb9d98f20821b199cab9b10cf11dfaf4db673d8416d6fca",
    },
    "tests/test_r5_foundation.py::test_r5_foundation_declares_future_data_authorization_vocabulary": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-foundation-declares-future-data-access-classes",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "380e08feeb2a5702419cbc877220d7f930ebcb807c01a12194a918eddfa6d3ff",
    },
    "tests/test_r5_foundation.py::test_r5_foundation_status_matches_canonical_governance": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-foundation-remains-red-and-not-admitted",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "fbdcf6108de430c00ca4e5b5810435377901d66e1046776935d8029d41e75771",
    },
}


def _foundation() -> dict[str, object]:
    return json.loads(FOUNDATION_PATH.read_text(encoding="utf-8"))


def test_r5_foundation_contract_is_strict_and_exact() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    Draft202012Validator(schema).validate(_foundation())

    assert _foundation() == {
        "schema": "cemm-r5-foundation-contract-v1",
        "phase": "R5",
        "increment": "hard-cut-foundation",
        "effective_replay_status": "red",
        "admission_available": False,
        "owners": EXPECTED_OWNERS,
        "data_access_classes": EXPECTED_ACCESS_CLASSES,
        "neural_activation_task_ref": "R5-Neural-Activation",
    }


def test_r5_foundation_declares_future_data_authorization_vocabulary() -> None:
    foundation = _foundation()
    assert foundation["data_access_classes"] == EXPECTED_ACCESS_CLASSES
    assert foundation["neural_activation_task_ref"] == "R5-Neural-Activation"
    assert foundation["admission_available"] is False


def test_r5_foundation_status_matches_canonical_governance() -> None:
    records = read_hash_chain(ROOT / "governance" / "replay_status.jsonl")
    effective = effective_replay_status(records)
    r5_green_records = [
        record
        for record in records
        if record["phase"] == "R5" and record["status"] == "green"
    ]

    assert effective["R5"] == _foundation()["effective_replay_status"] == "red"
    assert r5_green_records == []
    assert _foundation()["admission_available"] is False
