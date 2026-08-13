from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.run_active_test_suite import (
    ActiveSuiteError,
    ActiveSuiteFailure,
    authenticate_r5_active_suite,
    build_selector,
    classify_inactive_nodes,
    run_authenticated_suite,
)
from scripts.test_inventory_core import (
    InventoryError,
    PHASES,
    content_ref,
    load_and_verify,
    source_ast_sha256,
    verify_document_authority_pin,
)


ROOT = Path(__file__).parents[1]
R5_PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-08-13-r5-hard-cut-foundation-plan.md"
)
KNOWN_RAW_INACTIVE_ERROR = (
    "tests/test_evaluation_metrics.py::test_evaluator_loads_test_episodes"
)
ZERO_COLLECTION_LINEAGE_CARRIER = (
    "tests/test_six_phase_runtime.py::"
    "test_runtime_receipts_bind_exact_orientation_content_ref"
)


def _snapshot_reader(overrides: dict[Path, bytes]):
    normalized = {path.resolve(): raw for path, raw in overrides.items()}

    def read(path: Path) -> bytes:
        target = path.resolve()
        return normalized.get(target, target.read_bytes())

    return read


def _independent_inventory():
    inventory = ROOT / "governance" / "test_inventory.json"
    digest = verify_document_authority_pin(ROOT, inventory)
    return load_and_verify(
        ROOT,
        inventory,
        phase="R5",
        enforce_reviewed_counts=True,
        expected_sha256=digest,
    )


def _minimal_inventory_project(
    tmp_path: Path,
    source: str,
    *,
    name: str,
    source_ref: str = "tests/test_owned.py::test_owned",
) -> tuple[Path, Path]:
    root = tmp_path / name
    module_path = root / "tests" / "test_owned.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(source, encoding="utf-8", newline="\n")
    (root / "pyproject.toml").write_text(
        """[tool.pytest.ini_options]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test*"]
python_classes = ["Test*"]
""",
        encoding="utf-8",
        newline="\n",
    )
    function_name = source_ref.rsplit("::", 1)[1]
    functions = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    assert len(functions) == 1
    record = {
        "activation_phase": "G0",
        "assertion_ref": "assertion:minimal-owned-test",
        "case_node_ids": [source_ref],
        "classification": "retained",
        "source_ast_sha256": source_ast_sha256(functions[0]),
        "source_test_ref": source_ref,
        "successor_node_ids": [],
    }
    records = [record]
    cases = [source_ref]
    inventory: dict[str, object] = {
        "baseline_source_ref": "0" * 40,
        "case_count": 1,
        "case_set_ref": content_ref("case_set", cases),
        "classification_counts": {
            "historical": 0,
            "retained": 1,
            "rewritten": 0,
        },
        "file_count": 1,
        "files": [
            {
                "baseline_blob_ref": (
                    "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
                ),
                "path": "tests/test_owned.py",
            }
        ],
        "schema": "cemm-hybrid-test-inventory-v1",
        "source_set_ref": content_ref("source_set", records),
        "source_test_count": 1,
        "source_tests": records,
    }
    inventory["inventory_ref"] = content_ref("test_inventory", inventory)
    inventory_path = root / "governance" / "test_inventory.json"
    inventory_path.parent.mkdir()
    inventory_path.write_text(
        json.dumps(
            inventory,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
        newline="",
    )
    return root, inventory_path


def test_r5_active_suite_contract_equals_authenticated_inventory() -> None:
    expected = _independent_inventory()
    contract = authenticate_r5_active_suite(ROOT)
    selector = build_selector(contract)

    assert contract.phase == "R5"
    assert contract.inventory_ref == expected.inventory_ref
    assert contract.literal_metadata_ref == expected.literal_metadata_ref
    assert contract.active_node_set_ref == expected.active_node_set_ref
    assert contract.collectable_node_set_ref == expected.collectable_node_set_ref
    assert contract.active_node_ids == expected.active_node_ids
    assert contract.collectable_node_ids == expected.collectable_node_ids
    assert selector["active_node_ids"] == list(expected.active_node_ids)
    assert selector["collectable_node_ids"] == list(expected.collectable_node_ids)


def test_r5_collectable_inactive_partition_is_exhaustive_and_derived() -> None:
    result = _independent_inventory()
    classification = classify_inactive_nodes(result, phase="R5")
    inactive = set(result.collectable_node_ids) - set(result.active_node_ids)

    classified = {
        node_id
        for node_ids in classification.values()
        for node_id in node_ids
    }
    assert classified == inactive
    assert sum(map(len, classification.values())) == len(inactive)
    assert set(classification) == {
        "disposition_deferred",
        "disposition_retired",
        "future_phase",
        "lifecycle_historical",
        "lifecycle_rewritten",
        "superseded",
    }

    source_by_node = {
        node_id: record
        for record in result.source_tests.values()
        for node_id in record.case_node_ids
    }
    later_by_node = result.later_nodes
    superseded = {
        record.supersedes_node_id
        for record in later_by_node.values()
        if record.supersedes_node_id is not None
    }
    for node_id in classification["superseded"]:
        assert node_id in superseded
    for node_id in classification["lifecycle_historical"]:
        assert source_by_node[node_id].classification == "historical"
    for node_id in classification["lifecycle_rewritten"]:
        assert source_by_node[node_id].classification == "rewritten"
    for node_id in classification["future_phase"]:
        record = later_by_node.get(node_id) or source_by_node[node_id]
        assert PHASES.index(record.activation_phase) > PHASES.index("R5")


def test_r5_nonexecutable_lineage_carrier_is_not_physically_collectable() -> None:
    result = _independent_inventory()

    assert ZERO_COLLECTION_LINEAGE_CARRIER in result.later_nodes
    assert ZERO_COLLECTION_LINEAGE_CARRIER not in result.collectable_node_ids
    assert ZERO_COLLECTION_LINEAGE_CARRIER not in result.active_node_ids


def test_module_test_false_cannot_hide_unsuperseded_active_leaf(
    tmp_path: Path,
) -> None:
    root, inventory = _minimal_inventory_project(
        tmp_path,
        "__test__ = False\n\ndef test_owned() -> None:\n    assert True\n",
        name="hidden-active",
    )

    with pytest.raises(InventoryError, match="no current executable source"):
        load_and_verify(root, inventory, phase="G0")


def test_module_test_true_remains_physically_collectable(tmp_path: Path) -> None:
    root, inventory = _minimal_inventory_project(
        tmp_path,
        "__test__ = True\n\ndef test_owned() -> None:\n    assert True\n",
        name="explicit-true",
    )

    result = load_and_verify(root, inventory, phase="G0")
    assert result.active_node_ids == ("tests/test_owned.py::test_owned",)
    assert result.collectable_node_ids == ("tests/test_owned.py::test_owned",)


def test_module_test_control_rejects_dynamic_and_rebound_assignments(
    tmp_path: Path,
) -> None:
    sources = (
        "__test__ = bool(0)\n\ndef test_owned() -> None:\n    assert True\n",
        "__test__ = False\n__test__ = False\n\ndef test_owned() -> None:\n    assert True\n",
    )
    for index, source in enumerate(sources):
        root, inventory = _minimal_inventory_project(
            tmp_path,
            source,
            name=f"ambiguous-{index}",
        )
        with pytest.raises(InventoryError, match="__test__"):
            load_and_verify(root, inventory, phase="G0")


def test_class_level_test_control_is_rejected_not_generalized(
    tmp_path: Path,
) -> None:
    root, inventory = _minimal_inventory_project(
        tmp_path,
        """class TestOwned:
    __test__ = False

    def test_owned(self) -> None:
        assert True
""",
        name="class-control",
        source_ref="tests/test_owned.py::TestOwned::test_owned",
    )
    with pytest.raises(InventoryError, match="class.*__test__|__test__.*class"):
        load_and_verify(root, inventory, phase="G0")


def test_r5_inactive_classification_rejects_unclassified_collectable_node() -> None:
    malformed = SimpleNamespace(
        active_node_ids=(),
        collectable_node_ids=("tests/test_unknown.py::test_unknown",),
        deferred_r5_assertion_refs=(),
        retired_r5_assertion_refs=(),
        later_nodes={},
        source_tests={},
    )
    with pytest.raises(ActiveSuiteError, match="unclassified collectable inactive"):
        classify_inactive_nodes(malformed, phase="R5")


@pytest.mark.parametrize(
    "target",
    ["inventory", "source", "disposition"],
    ids=["inventory", "source", "disposition"],
)
def test_r5_active_suite_authentication_rejects_tampered_governed_source(
    target: str,
) -> None:
    if target == "inventory":
        path = ROOT / "governance" / "test_inventory.json"
        raw = path.read_bytes().replace(
            b'"file_count": 60',
            b'"file_count": 61',
            1,
        )
    elif target == "source":
        path = ROOT / "tests" / "test_r5_foundation.py"
        raw = path.read_bytes().replace(
            b'assert schema["additionalProperties"] is False',
            b'assert schema["additionalProperties"] == False',
            1,
        )
    else:
        path = ROOT / "governance" / "r5_test_dispositions.json"
        raw = path.read_bytes().replace(
            b'"disposition": "deferred"',
            b'"disposition": "retired"',
            1,
        )

    with pytest.raises(InventoryError):
        authenticate_r5_active_suite(
            ROOT,
            source_reader=_snapshot_reader({path: raw}),
        )


def test_r5_selector_rejects_tampered_identity_and_node_sets() -> None:
    contract = authenticate_r5_active_suite(ROOT)
    selector = build_selector(contract)

    forged_ref = dict(selector)
    forged_ref["selector_ref"] = "pytest_selector:" + "0" * 24
    with pytest.raises(ActiveSuiteError, match="selector identity"):
        build_selector(contract, candidate=forged_ref)

    omitted = dict(selector)
    omitted["active_node_ids"] = omitted["active_node_ids"][:-1]
    omitted.pop("selector_ref")
    with pytest.raises(ActiveSuiteError, match="active node set"):
        build_selector(contract, candidate=omitted)


def test_r5_runner_selects_no_known_raw_inactive_error_and_spawns_once(
    tmp_path: Path,
) -> None:
    contract = authenticate_r5_active_suite(ROOT)
    calls: list[dict[str, object]] = []
    run_roots: list[Path] = []

    def fake_runner(*, root, run_root, manifest_path, report_path, limits):
        del root, report_path, limits
        run_roots.append(run_root)
        selector = json.loads(manifest_path.read_text(encoding="utf-8"))
        calls.append(selector)
        assert KNOWN_RAW_INACTIVE_ERROR in selector["collectable_node_ids"]
        assert KNOWN_RAW_INACTIVE_ERROR not in selector["active_node_ids"]
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def fake_parser(_path, *, expected_selector, max_bytes):
        del max_bytes
        return SimpleNamespace(
            disposition="passed",
            error_code=None,
            payload={
                "active_node_ids": expected_selector["active_node_ids"],
                "collected_node_ids": expected_selector["collectable_node_ids"],
                "counts": {
                    "error": 0,
                    "failure": 0,
                    "passed": len(expected_selector["active_node_ids"]),
                    "skip": 0,
                    "xfail": 0,
                    "xpass": 0,
                },
                "deselected_node_ids": sorted(
                    set(expected_selector["collectable_node_ids"])
                    - set(expected_selector["active_node_ids"])
                ),
                "selected_node_ids": expected_selector["active_node_ids"],
                "selector_ref": expected_selector["selector_ref"],
            },
        )

    summary = run_authenticated_suite(
        ROOT,
        contract,
        process_runner=fake_runner,
        report_parser=fake_parser,
        temporary_parent=tmp_path,
    )

    assert len(calls) == 1
    assert summary["inactive_node_count"] == (
        len(contract.collectable_node_ids) - len(contract.active_node_ids)
    )
    assert all(not path.exists() for path in run_roots)


def test_r5_runner_rejects_tampered_report_and_removes_temporary_root(
    tmp_path: Path,
) -> None:
    contract = authenticate_r5_active_suite(ROOT)
    run_roots: list[Path] = []

    def fake_runner(*, root, run_root, manifest_path, report_path, limits):
        del root, manifest_path, report_path, limits
        run_roots.append(run_root)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def tampered_parser(_path, *, expected_selector, max_bytes):
        del max_bytes
        return SimpleNamespace(
            disposition="passed",
            error_code=None,
            payload={
                "active_node_ids": expected_selector["active_node_ids"],
                "collected_node_ids": expected_selector["collectable_node_ids"],
                "counts": {
                    "error": 0,
                    "failure": 0,
                    "passed": len(expected_selector["active_node_ids"]),
                    "skip": 0,
                    "xfail": 0,
                    "xpass": 0,
                },
                "deselected_node_ids": [],
                "selected_node_ids": expected_selector["active_node_ids"],
                "selector_ref": "pytest_selector:" + "0" * 24,
            },
        )

    with pytest.raises(ActiveSuiteError, match="report selector"):
        run_authenticated_suite(
            ROOT,
            contract,
            process_runner=fake_runner,
            report_parser=tampered_parser,
            temporary_parent=tmp_path,
        )
    assert all(not path.exists() for path in run_roots)


def test_r5_runner_failure_names_bounded_failed_nodes_and_cleans(
    tmp_path: Path,
) -> None:
    contract = authenticate_r5_active_suite(ROOT)
    failed_node = contract.active_node_ids[0]
    run_roots: list[Path] = []

    def fake_runner(*, root, run_root, manifest_path, report_path, limits):
        del root, manifest_path, report_path, limits
        run_roots.append(run_root)
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"")

    def failed_parser(_path, *, expected_selector, max_bytes):
        del max_bytes
        return SimpleNamespace(
            disposition="failed",
            error_code=None,
            payload={
                "active_node_ids": expected_selector["active_node_ids"],
                "collected_node_ids": expected_selector["collectable_node_ids"],
                "counts": {
                    "error": 0,
                    "failure": 1,
                    "passed": len(expected_selector["active_node_ids"]) - 1,
                    "skip": 0,
                    "xfail": 0,
                    "xpass": 0,
                },
                "deselected_node_ids": sorted(
                    set(expected_selector["collectable_node_ids"])
                    - set(expected_selector["active_node_ids"])
                ),
                "facts": [
                    {"classification": "failure", "node_id": failed_node}
                ],
                "selected_node_ids": expected_selector["active_node_ids"],
                "selector_ref": expected_selector["selector_ref"],
            },
        )

    with pytest.raises(ActiveSuiteFailure, match=failed_node):
        run_authenticated_suite(
            ROOT,
            contract,
            process_runner=fake_runner,
            report_parser=failed_parser,
            temporary_parent=tmp_path,
        )
    assert all(not path.exists() for path in run_roots)


def test_r5_task10_uses_governed_active_suite_as_release_gate() -> None:
    text = R5_PLAN.read_text(encoding="utf-8")
    task10 = text.split(
        "### Task 10: Run exact R5 foundation and full regression gates",
        1,
    )[1].split("## Appendix A:", 1)[0]

    assert "python scripts/run_active_test_suite.py" in task10
    assert "python -m pytest -q -p no:cacheprovider" not in task10
    assert "optional raw collection diagnostic" in task10.lower()


__cemm_test_inventory__ = {
    "tests/test_r5_active_regression.py::test_r5_active_suite_contract_equals_authenticated_inventory": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-equals-authenticated-inventory",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '216e6caf1bf8ecb6351b714a8e6657e4b5a7065c9b2efe663de919e05a3ef6c3',
    },
    "tests/test_r5_active_regression.py::test_r5_collectable_inactive_partition_is_exhaustive_and_derived": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-inactive-suite-partition-is-exhaustive",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'd4e9d78964750d90e38913ceb355835c9328804cf4c50a1034370f9d9ad29621',
    },
    "tests/test_r5_active_regression.py::test_r5_inactive_classification_rejects_unclassified_collectable_node": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-inactive-suite-rejects-unclassified-node",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'b63f8a608dbf331547f3dbcf600cb9975e7c9209898a4a15d80dca2f51848646',
    },
    "tests/test_r5_active_regression.py::test_r5_nonexecutable_lineage_carrier_is_not_physically_collectable": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-zero-collection-carrier-is-nonexecutable",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'bf9833dc2f2696fd87b0d5244fdfc8bd69dfb927105b30cdd563909f4c180c47',
    },
    "tests/test_r5_active_regression.py::test_module_test_false_cannot_hide_unsuperseded_active_leaf": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-module-noncollection-cannot-hide-active-leaf",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '95088957e90602604eb322c5b5e9c74b3406ea28aca7e8413f076893f3ccc951',
    },
    "tests/test_r5_active_regression.py::test_module_test_true_remains_physically_collectable": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-module-test-true-remains-collectable",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '1b8d55bc913009b91a5bd869b8c5eb7a55c005fa32d0b63966e77dda92dae05e',
    },
    "tests/test_r5_active_regression.py::test_module_test_control_rejects_dynamic_and_rebound_assignments": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-module-test-control-is-literal-and-unique",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'b98df0a99730351a2b2b0e66b3347d138f77bab8c4f9418ebd106854abaa43d6',
    },
    "tests/test_r5_active_regression.py::test_class_level_test_control_is_rejected_not_generalized": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-class-test-control-is-not-generalized",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '7d5254aa6c5a69c4ebdd899cee8f6da3f35d46cd7b529b5986fef53b964947c7',
    },
    "tests/test_r5_active_regression.py::test_r5_active_suite_authentication_rejects_tampered_governed_source[inventory]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-tampered-inventory",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '71efc336ba13de51c6863979607f832604690ab05d2d7df2abe659e6bf240b58',
    },
    "tests/test_r5_active_regression.py::test_r5_active_suite_authentication_rejects_tampered_governed_source[source]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-tampered-source",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '71efc336ba13de51c6863979607f832604690ab05d2d7df2abe659e6bf240b58',
    },
    "tests/test_r5_active_regression.py::test_r5_active_suite_authentication_rejects_tampered_governed_source[disposition]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-tampered-disposition",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '71efc336ba13de51c6863979607f832604690ab05d2d7df2abe659e6bf240b58',
    },
    "tests/test_r5_active_regression.py::test_r5_selector_rejects_tampered_identity_and_node_sets": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-selector-is-exact",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'c2c15c085bacef52e947346c795dc628884d14e90ed55babda5c924372d9e54a',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_selects_no_known_raw_inactive_error_and_spawns_once": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-runs-one-process-without-inactive-errors",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'dfde370a86a018a1126dc1df631ec28b012c6286b07509e19299d8d25c3d59e4',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_rejects_tampered_report_and_removes_temporary_root": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-report-is-authenticated-and-ephemeral",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'a7f6d6d5e3fb33be6d6a9eb8fbdd0202f1dac83a4ac292f92f3bae6f3761f860',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_failure_names_bounded_failed_nodes_and_cleans": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-failure-summary-is-bounded",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'c056855d4a30e885d14566f58b60fb978e8bc83b648016f3aaea3de0ef2bb477',
    },
    "tests/test_r5_active_regression.py::test_r5_task10_uses_governed_active_suite_as_release_gate": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-task10-governs-active-suite-topology",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '15b32da1cd903224a82748362d81f1ceb6771496c239732787903079f98106bb',
    },
}
