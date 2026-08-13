from __future__ import annotations

import copy
import importlib.util
import inspect
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


def test_r5_disposition_validator_has_no_caller_expectation_override() -> None:
    generator = _load_script(GENERATOR_PATH, "_r5_disposition_generator_signature")

    assert tuple(inspect.signature(generator.validate_receipt).parameters) == (
        "root",
        "candidate",
    )


def test_r5_disposition_validator_rejects_rehashed_self_authenticated_tamper() -> None:
    generator = _load_script(GENERATOR_PATH, "_r5_disposition_generator_self_auth")
    tampered = copy.deepcopy(generator.build_receipt(ROOT))
    row = next(item for item in tampered["rows"] if item["disposition"] == "successor")
    row["successor_node_ids"] = ["tests/test_r5_missing.py::test_missing"]
    without_ref = {key: value for key, value in tampered.items() if key != "receipt_ref"}
    tampered["receipt_ref"] = generator.content_ref(
        "r5_test_disposition_receipt",
        without_ref,
    )
    kwargs = {}
    if "_expected" in inspect.signature(generator.validate_receipt).parameters:
        kwargs["_expected"] = tampered

    with pytest.raises(generator.R5DispositionReceiptError, match="authenticated|match"):
        generator.validate_receipt(ROOT, tampered, **kwargs)


def test_r5_disposition_output_rejects_symlinked_parent(tmp_path: Path) -> None:
    generator = _load_script(GENERATOR_PATH, "_r5_disposition_generator_symlink")
    root = tmp_path / "root"
    root.mkdir()
    external = tmp_path / "external"
    (external / "validation").mkdir(parents=True)
    (root / "artifacts").symlink_to(external, target_is_directory=True)

    with pytest.raises(generator.R5DispositionReceiptError, match="symlink|contained"):
        generator._exact_artifact_path(root, generator.RECEIPT_RELATIVE_PATH)


def test_r5_disposition_atomic_replace_failure_preserves_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = _load_script(GENERATOR_PATH, "_r5_disposition_generator_atomic")
    target = tmp_path / "receipt.json"
    target.write_bytes(b"original")

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(generator.os, "replace", fail_replace)
    with pytest.raises(generator.R5DispositionReceiptError, match="atomic replace"):
        generator._atomic_write(target, b"replacement")

    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]


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


def test_r5_metadata_refresher_uses_exact_qualified_class_methods(
    tmp_path: Path,
) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_qualified")
    tests = tmp_path / "tests"
    tests.mkdir()
    path = tests / "test_r5_classes.py"
    zero = "0" * 64
    path.write_text(
        "class TestAlpha:\n"
        "    def test_same(self) -> None:\n"
        "        assert True\n\n"
        "class TestBeta:\n"
        "    def test_same(self) -> None:\n"
        "        assert False\n\n"
        "__cemm_test_inventory__ = {\n"
        "    'tests/test_r5_classes.py::TestAlpha::test_same': {\n"
        f"        'source_ast_sha256': '{zero}',\n"
        "    },\n"
        "    'tests/test_r5_classes.py::TestBeta::test_same': {\n"
        f"        'source_ast_sha256': '{zero}',\n"
        "    },\n"
        "}\n",
        encoding="utf-8",
        newline="\n",
    )

    assert refresher.refresh_r5_test_metadata(tmp_path) == (2, 1)
    hashes = refresher.metadata_hashes(path)
    assert hashes.keys() == {
        "tests/test_r5_classes.py::TestAlpha::test_same",
        "tests/test_r5_classes.py::TestBeta::test_same",
    }
    assert len(set(hashes.values())) == 2
    assert refresher.refresh_r5_test_metadata(tmp_path) == (0, 1)


def test_r5_metadata_refresher_rejects_duplicate_literal_metadata_keys(
    tmp_path: Path,
) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_duplicates")
    tests = tmp_path / "tests"
    tests.mkdir()
    path = tests / "test_r5_duplicate.py"
    row = "{'source_ast_sha256': '" + "0" * 64 + "'}"
    path.write_text(
        "def test_duplicate() -> None:\n    assert True\n\n"
        "__cemm_test_inventory__ = {\n"
        f"    'tests/test_r5_duplicate.py::test_duplicate': {row},\n"
        f"    'tests/test_r5_duplicate.py::test_duplicate': {row},\n"
        "}\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="duplicate literal metadata key"):
        refresher.metadata_hashes(path)


def test_r5_metadata_refresher_reads_sources_with_a_hard_byte_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_bound")
    path = tmp_path / "test_r5_oversize.py"
    path.write_bytes(b"x" * (refresher.MAX_SOURCE_BYTES + 1))

    def forbid_unbounded_read(_path: Path) -> bytes:
        raise AssertionError("unbounded Path.read_bytes was used")

    monkeypatch.setattr(Path, "read_bytes", forbid_unbounded_read)
    with pytest.raises(ValueError, match="source byte bound"):
        refresher.metadata_hashes(path)


def test_r5_metadata_refresher_late_validation_failure_writes_nothing(
    tmp_path: Path,
) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_late_invalid")
    tests = tmp_path / "tests"
    tests.mkdir()
    first = tests / "test_r5_a_valid.py"
    zero = "0" * 64
    first.write_text(
        "def test_valid() -> None:\n    assert True\n\n"
        "__cemm_test_inventory__ = {\n"
        "    'tests/test_r5_a_valid.py::test_valid': {\n"
        f"        'source_ast_sha256': '{zero}',\n"
        "    },\n}\n",
        encoding="utf-8",
        newline="\n",
    )
    original = first.read_bytes()
    (tests / "test_r5_z_invalid.py").write_text(
        "def test_invalid(:\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(SyntaxError):
        refresher.refresh_r5_test_metadata(tmp_path)

    assert first.read_bytes() == original


def test_r5_metadata_refresher_replace_failure_rolls_back_prior_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_rollback")
    tests = tmp_path / "tests"
    tests.mkdir()
    zero = "0" * 64
    paths = []
    originals = {}
    for letter in ("a", "b"):
        path = tests / f"test_r5_{letter}.py"
        path.write_text(
            f"def test_{letter}() -> None:\n    assert True\n\n"
            "__cemm_test_inventory__ = {\n"
            f"    'tests/test_r5_{letter}.py::test_{letter}': {{\n"
            f"        'source_ast_sha256': '{zero}',\n"
            "    },\n}\n",
            encoding="utf-8",
            newline="\n",
        )
        paths.append(path)
        originals[path] = path.read_bytes()
    real_replace = refresher.os.replace
    calls = 0

    def fail_second_replace(source: object, target: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second replace failure")
        real_replace(source, target)

    monkeypatch.setattr(refresher.os, "replace", fail_second_replace)
    with pytest.raises(ValueError, match="atomic replace"):
        refresher.refresh_r5_test_metadata(tmp_path)

    assert {path: path.read_bytes() for path in paths} == originals
    assert sorted(path.name for path in tests.iterdir()) == [path.name for path in paths]


def test_r5_metadata_refresher_rejects_reparse_boundary_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresher = _load_script(REFRESHER_PATH, "_r5_metadata_refresher_reparse")
    root = tmp_path / "root"
    tests = root / "tests"
    tests.mkdir(parents=True)
    sentinel = tests / "test_r5_sentinel.py"
    sentinel.write_bytes(b"external-must-not-change")
    monkeypatch.setattr(
        refresher,
        "_is_reparse_point",
        lambda path: path == tests,
    )

    with pytest.raises(ValueError, match="reparse|junction"):
        refresher.refresh_r5_test_metadata(root)

    assert sentinel.read_bytes() == b"external-must-not-change"


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
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_validator_has_no_caller_expectation_override": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-validator-has-no-self-auth-override",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'a8bba02b1b68da3c25f2a9ab173a12c6642ce652e9ad466a9d043c1e7cc732d5',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_validator_rejects_rehashed_self_authenticated_tamper": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-rehashed-self-auth-tamper-fails",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '82de2c195204cb7a4a76f32f0f68b2bbd2f25fdf4fb9a8b66cc51efac7875e28',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_uses_exact_qualified_class_methods": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-uses-qualified-methods",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'b569efe618735d3d239542e7734b768462db16b37b2b928caa927da953045180',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_rejects_duplicate_literal_metadata_keys": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-rejects-duplicate-keys",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": 'a4c844cd057484ffc7fedc1dd9ef16edf702d5126d82e9b1e4367231fdcbf368',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_disposition_atomic_replace_failure_preserves_receipt": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-disposition-atomic-failure-preserves-receipt",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '8d12fbeb9c316c575e19b291ef487e176d314a7f25ba7e6f04d14a1049ab3e2c',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_reads_sources_with_a_hard_byte_bound": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-bounds-source-reads",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '7e0b694398364cf2d9dcb6dbe8f2327c80dbc419aa14da50c2241ecfa7deac0c',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_late_validation_failure_writes_nothing": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-validates-before-writing",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '4d986d07d4a7bb5237e1e0a259b1c6fc267060780ec6c8ebc82de55773a0b0af',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_replace_failure_rolls_back_prior_files": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-replace-failure-rolls-back",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '91df474ee087d512f6287213d2275a72d29ed8683873b1dd407a041857ab5ccb',
    },
    "tests/test_r5_legacy_hard_cut.py::test_r5_metadata_refresher_rejects_reparse_boundary_before_writes": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-test-metadata-refresher-rejects-reparse-boundary",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "legacy-hard-cut",
        "source_ast_sha256": '86813bb9387392d292386088d7ed7d93b0223d4cdcd84447a8e468bdcd920d5f',
    },
}
