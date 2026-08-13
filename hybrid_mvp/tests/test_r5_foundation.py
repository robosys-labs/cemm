from __future__ import annotations

import json
from pathlib import Path

import pytest
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
MAX_FOUNDATION_JSON_BYTES = 64 * 1024


__cemm_test_inventory__ = {
    "tests/test_r5_foundation.py::test_r5_foundation_loader_rejects_untrusted_json_bytes": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-foundation-loader-rejects-untrusted-json",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "af8cdb6cb754711e0c559671dd20a79db3ebbda3717523f8a23b4e9140f449a1",
    },
    "tests/test_r5_foundation.py::test_r5_foundation_contract_is_strict_and_exact": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-foundation-contract-strict-and-exact",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "32fd79013d6ca4c2ac3664f5c6bc93232daeaa842394c66dfdb2a90f2ef02b57",
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


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


def _load_strict_json(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        raw = handle.read(MAX_FOUNDATION_JSON_BYTES + 1)
    if len(raw) > MAX_FOUNDATION_JSON_BYTES:
        raise ValueError("foundation JSON exceeds byte bound")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("foundation JSON is not strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise ValueError("foundation JSON root must be an object")
    return value


def _foundation() -> dict[str, object]:
    return _load_strict_json(FOUNDATION_PATH)


def test_r5_foundation_loader_rejects_untrusted_json_bytes(tmp_path: Path) -> None:
    invalid_cases = (
        (b'{"schema":"first","schema":"second"}', "duplicate JSON key"),
        (b'{"value":NaN}', "non-finite JSON number"),
        (b'{"value":"\xff"}', "not strict UTF-8"),
        (
            b'{"padding":"' + b"x" * MAX_FOUNDATION_JSON_BYTES + b'"}',
            "exceeds byte bound",
        ),
    )
    for index, (payload, error_match) in enumerate(invalid_cases):
        path = tmp_path / f"invalid-{index}.json"
        path.write_bytes(payload)
        with pytest.raises(ValueError, match=error_match):
            _load_strict_json(path)


def test_r5_foundation_contract_is_strict_and_exact() -> None:
    schema = _load_strict_json(SCHEMA_PATH)
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
