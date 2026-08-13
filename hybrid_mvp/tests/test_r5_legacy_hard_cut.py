from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_r5_test_dispositions.py"
REFRESHER_PATH = ROOT / "scripts" / "refresh_r5_test_metadata.py"
RECEIPT_PATH = ROOT / "artifacts" / "validation" / "R5_TEST_DISPOSITIONS.json"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_r5_disposition_receipt_is_deterministic_and_checked_in() -> None:
    generator = _load_script(GENERATOR_PATH, "_r5_disposition_generator_test")

    first = generator.canonical_receipt_bytes(ROOT)
    second = generator.canonical_receipt_bytes(ROOT)

    assert first == second == RECEIPT_PATH.read_bytes()
    payload = json.loads(first)
    assert len(payload["rows"]) == 43
    assert payload["counts"] == {"deferred": 25, "retired": 1, "successor": 17}
    assert payload["inventory_ref"] == "test_inventory:c715e262526c0ea26a6fef90"
    assert payload["disposition_source_sha256"].startswith("sha256:")
    assert payload["literal_metadata_ref"].startswith("literal_test_metadata:")
    assert payload["receipt_ref"].startswith("r5_test_disposition_receipt:")


@pytest.mark.parametrize(
    ("disposition", "field"),
    (("successor", "successor_node_ids"), ("successor", "assertion_ref"), ("deferred", "future_owner_ref")),
    ids=("successor-node", "assertion-ref", "deferred-owner"),
)
def test_r5_disposition_receipt_rejects_tampered_rows(
    disposition: str,
    field: str,
) -> None:
    generator = _load_script(
        GENERATOR_PATH,
        f"_r5_disposition_generator_tamper_{field}",
    )
    payload = generator.build_receipt(ROOT)
    tampered = copy.deepcopy(payload)
    row = next(item for item in tampered["rows"] if item["disposition"] == disposition)
    row[field] = ["tests/test_r5_missing.py::test_missing"] if field == "successor_node_ids" else "forged-owner"

    with pytest.raises(generator.R5DispositionReceiptError, match="authenticated|match"):
        generator.validate_receipt(ROOT, tampered)


def test_r5_disposition_output_rejects_symlinked_parent(tmp_path: Path) -> None:
    generator = _load_script(GENERATOR_PATH, "_r5_disposition_generator_symlink")
    root = tmp_path / "root"
    root.mkdir()
    external = tmp_path / "external"
    (external / "validation").mkdir(parents=True)
    (root / "artifacts").symlink_to(external, target_is_directory=True)

    with pytest.raises(generator.R5DispositionReceiptError, match="symlink|contained"):
        generator._exact_artifact_path(root, generator.RECEIPT_RELATIVE_PATH)


def test_r5_metadata_refresher_changes_only_r5_ast_hash_literals(tmp_path: Path) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_test")
    tests = tmp_path / "tests"
    tests.mkdir()
    r5 = tests / "test_r5_sample.py"
    r5.write_text(
        "def test_sample() -> None:\n    assert True\n\n"
        "__cemm_test_inventory__ = {\n"
        "    'tests/test_r5_sample.py::test_sample': {\n"
        "        'assertion_ref': 'assertion:sample',\n"
        "        'activation_phase': 'R5',\n"
        "        'diagnostic_role': 'phase',\n"
        "        'introduced_by_task': 'R5-Hard-Cut-Foundation',\n"
        "        'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',\n"
        "    },\n}\n",
        encoding="utf-8",
        newline="\n",
    )
    unrelated = tests / "test_r4_sample.py"
    unrelated.write_text("UNCHANGED\n", encoding="utf-8", newline="\n")
    before = r5.read_text(encoding="utf-8")

    assert refresher.refresh_r5_test_metadata(tmp_path) == (1, 1)
    after = r5.read_text(encoding="utf-8")
    assert unrelated.read_text(encoding="utf-8") == "UNCHANGED\n"
    assert before.replace("'0000000000000000000000000000000000000000000000000000000000000000'", "HASH") == after.replace(
        repr(refresher.metadata_hashes(r5)["tests/test_r5_sample.py::test_sample"]),
        "HASH",
    )
    assert refresher.refresh_r5_test_metadata(tmp_path) == (0, 1)


__cemm_test_inventory__ = {
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_receipt_is_deterministic_and_checked_in": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-receipt-is-deterministic",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'e9885b745008c15f95e1c2ac0a6dd10a60f90154f31eba3b24d625a7c84eef88',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_receipt_rejects_tampered_rows[successor-node]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-successor-tamper-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'be76c0cd0dabfac10a5f749ef08d55a76be28458bd1ef3a63c5fada38b8bc93f',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_receipt_rejects_tampered_rows[assertion-ref]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-assertion-tamper-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'be76c0cd0dabfac10a5f749ef08d55a76be28458bd1ef3a63c5fada38b8bc93f',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_receipt_rejects_tampered_rows[deferred-owner]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-deferred-owner-tamper-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'be76c0cd0dabfac10a5f749ef08d55a76be28458bd1ef3a63c5fada38b8bc93f',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_changes_only_r5_ast_hash_literals": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-only-updates-ast-hashes",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '49ad617e4c8cab21d432990c321a26aa28b283ddf0bdda90ebfc9c7ab658cea7',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_output_rejects_symlinked_parent": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-output-is-contained",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'f0ce29e7299f795c12a74ec183a83e7cce1831cc5c91660a97fa3be754f8a829',
    },
}
