from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest
import scripts.run_active_test_suite as active_suite

from scripts.run_active_test_suite import (
    ActiveSuiteError,
    ActiveSuiteFailure,
    authenticate_r5_active_suite,
    build_selector,
    classify_inactive_nodes,
    run_authenticated_suite,
    validation_gate,
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


def _unit_source_identity(root: Path) -> tuple[str, bool, str]:
    del root
    return "1" * 40, False, "source_tree:" + "2" * 24


def _contract():
    return authenticate_r5_active_suite(
        ROOT,
        source_identity_provider=_unit_source_identity,
    )


@contextmanager
def _same_root_snapshot(root: Path, source_ref: str, temporary_parent: Path | None):
    del source_ref, temporary_parent
    yield root


def _noop_snapshot_authenticator(root: Path, source_ref: str) -> None:
    del root, source_ref


def _parsed_report(disposition: str, payload: dict[str, object]):
    return SimpleNamespace(
        disposition=disposition,
        error_code=None,
        payload=payload,
        report_ref="pytest_report:" + "3" * 24,
    )


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
    contract = _contract()
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
            source_identity_provider=_unit_source_identity,
        )


def test_r5_selector_rejects_tampered_identity_and_node_sets() -> None:
    contract = _contract()
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
    contract = _contract()
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
        return _parsed_report(
            "passed",
            {
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
        snapshot_provider=_same_root_snapshot,
        source_identity_provider=_unit_source_identity,
        snapshot_authenticator=_noop_snapshot_authenticator,
    )

    assert len(calls) == 1
    assert summary["inactive_node_count"] == (
        len(contract.collectable_node_ids) - len(contract.active_node_ids)
    )
    assert all(not path.exists() for path in run_roots)


def test_r5_runner_rejects_tampered_report_and_removes_temporary_root(
    tmp_path: Path,
) -> None:
    contract = _contract()
    run_roots: list[Path] = []

    def fake_runner(*, root, run_root, manifest_path, report_path, limits):
        del root, manifest_path, report_path, limits
        run_roots.append(run_root)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def tampered_parser(_path, *, expected_selector, max_bytes):
        del max_bytes
        return _parsed_report(
            "passed",
            {
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
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=_noop_snapshot_authenticator,
        )
    assert all(not path.exists() for path in run_roots)


def test_r5_runner_failure_names_bounded_failed_nodes_and_cleans(
    tmp_path: Path,
) -> None:
    contract = _contract()
    failed_node = contract.active_node_ids[0]
    run_roots: list[Path] = []

    def fake_runner(*, root, run_root, manifest_path, report_path, limits):
        del root, manifest_path, report_path, limits
        run_roots.append(run_root)
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"")

    def failed_parser(_path, *, expected_selector, max_bytes):
        del max_bytes
        return _parsed_report(
            "failed",
            {
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
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=_noop_snapshot_authenticator,
        )
    assert all(not path.exists() for path in run_roots)


def test_r5_runner_rejects_contract_root_substitution(tmp_path: Path) -> None:
    contract = _contract()
    with pytest.raises(ActiveSuiteError, match="root"):
        run_authenticated_suite(
            tmp_path,
            contract,
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=_noop_snapshot_authenticator,
        )


@pytest.mark.parametrize(
    "reason",
    [
        validation_gate.ProcessErrorReason.TIMEOUT,
        validation_gate.ProcessErrorReason.OUTPUT_LIMIT,
    ],
    ids=["timeout", "output-limit"],
)
def test_r5_runner_translates_process_control_failure_and_cleans(
    tmp_path: Path,
    reason: validation_gate.ProcessErrorReason,
) -> None:
    contract = _contract()
    run_roots: list[Path] = []

    def failed_runner(*, root, run_root, manifest_path, report_path, limits):
        del root, manifest_path, report_path, limits
        run_roots.append(run_root)
        raise validation_gate.ProcessControlError(
            reason,
            f"bounded {reason.value}",
            termination_confirmed=True,
        )

    with pytest.raises(ActiveSuiteError, match=reason.value):
        run_authenticated_suite(
            ROOT,
            contract,
            process_runner=failed_runner,
            temporary_parent=tmp_path,
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=_noop_snapshot_authenticator,
        )
    assert all(not path.exists() for path in run_roots)


def test_r5_runner_authenticates_mutated_snapshot_after_confirmed_timeout(
    tmp_path: Path,
) -> None:
    contract = _contract()
    authentication_count = 0

    def mutation_detector(root: Path, source_ref: str) -> None:
        nonlocal authentication_count
        del root, source_ref
        authentication_count += 1
        if authentication_count == 3:
            raise ActiveSuiteError("post-exit source mutation")

    def timed_out_runner(**kwargs):
        del kwargs
        raise validation_gate.ProcessControlError(
            validation_gate.ProcessErrorReason.TIMEOUT,
            "bounded timeout",
            termination_confirmed=True,
        )

    with pytest.raises(ActiveSuiteError, match="post-exit source mutation"):
        run_authenticated_suite(
            ROOT,
            contract,
            process_runner=timed_out_runner,
            temporary_parent=tmp_path,
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=mutation_detector,
        )
    assert authentication_count == 3


def test_r5_runner_authenticates_mutated_snapshot_before_report_parsing(
    tmp_path: Path,
) -> None:
    contract = _contract()
    authentication_count = 0
    parser_called = False

    def mutation_detector(root: Path, source_ref: str) -> None:
        nonlocal authentication_count
        del root, source_ref
        authentication_count += 1
        if authentication_count == 3:
            raise ActiveSuiteError("post-exit source mutation")

    def completed_runner(**kwargs):
        del kwargs
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def malformed_parser(*args, **kwargs):
        nonlocal parser_called
        del args, kwargs
        parser_called = True
        raise ActiveSuiteError("malformed report")

    with pytest.raises(ActiveSuiteError, match="post-exit source mutation"):
        run_authenticated_suite(
            ROOT,
            contract,
            process_runner=completed_runner,
            report_parser=malformed_parser,
            temporary_parent=tmp_path,
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=mutation_detector,
        )
    assert authentication_count == 3
    assert parser_called is False


def test_r5_runner_rejects_live_source_drift_after_authentication(
    tmp_path: Path,
) -> None:
    contract = _contract()

    def drifted_source(root: Path) -> tuple[str, bool, str]:
        del root
        return "4" * 40, False, contract.source_tree_ref

    with pytest.raises(ActiveSuiteError, match="live source"):
        run_authenticated_suite(
            ROOT,
            contract,
            temporary_parent=tmp_path,
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=drifted_source,
            snapshot_authenticator=_noop_snapshot_authenticator,
        )


def test_r5_runner_rejects_snapshot_swap_before_pytest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract()
    called = False

    def swapped_authentication(*args, **kwargs):
        del args, kwargs
        return replace(contract, literal_metadata_ref="literal_test_metadata:" + "5" * 24)

    def forbidden_runner(**kwargs):
        nonlocal called
        del kwargs
        called = True

    monkeypatch.setattr(
        "scripts.run_active_test_suite.authenticate_r5_active_suite",
        swapped_authentication,
    )
    with pytest.raises(ActiveSuiteError, match="snapshot differs"):
        run_authenticated_suite(
            ROOT,
            contract,
            process_runner=forbidden_runner,
            temporary_parent=tmp_path,
            snapshot_provider=_same_root_snapshot,
            source_identity_provider=_unit_source_identity,
            snapshot_authenticator=_noop_snapshot_authenticator,
        )
    assert called is False


def test_r5_snapshot_cleanup_attempts_prune_after_remove_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "CEMM Test"],
        check=True,
    )
    (repository / "hybrid_mvp").mkdir()
    (repository / "hybrid_mvp" / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "fixture"], check=True)
    source_ref = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    temporary_parent = tmp_path / "control"
    temporary_parent.mkdir()
    actual = active_suite._git_worktree_command
    calls: list[str] = []

    def fail_remove(root: Path, arguments):
        operation = arguments[1]
        calls.append(operation)
        if operation == "remove":
            raise ActiveSuiteError("injected remove error")
        return actual(root, arguments)

    monkeypatch.setattr(active_suite, "_git_worktree_command", fail_remove)
    with pytest.raises(ActiveSuiteError, match="remove"):
        with active_suite._detached_git_snapshot(
            repository / "hybrid_mvp", source_ref, temporary_parent
        ):
            pass
    assert calls == ["add", "remove", "prune"]
    worktrees = subprocess.check_output(
        ["git", "-C", str(repository), "worktree", "list", "--porcelain"],
        text=True,
    )
    # Git stores object files read-only on Windows; restore fixture write bits so
    # the governing validation run-root can perform its strict cleanup.
    active_suite._restore_snapshot_write_bits(repository)
    assert "source-worktree" not in worktrees


def test_r5_authenticated_snapshot_preserves_writable_fixture_copy_semantics() -> None:
    source_ref = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    common_dir = Path(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(ROOT),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ],
            text=True,
        ).strip()
    ).resolve()
    external_parent = common_dir.parent.parent

    with tempfile.TemporaryDirectory(
        prefix="cemm-r5-fixture-", dir=external_parent
    ) as temporary:
        control = Path(temporary) / "control"
        control.mkdir()
        copied = Path(temporary) / "copied-receipt.json"
        with active_suite._detached_git_snapshot(
            ROOT, source_ref, control
        ) as snapshot:
            shutil.copy2(
                snapshot / "artifacts" / "r4" / "BUILD_RECEIPT.json", copied
            )
            original = copied.read_bytes()
            copied.write_bytes(original + b"\n")
            assert copied.read_bytes() == original + b"\n"


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
        "source_ast_sha256": 'c7eeaaadad16916680ecd77795d1efc22ba3e8b43a02bcaeed98310e0624e2e4',
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
        "source_ast_sha256": '59eeab6a013d8c6bd5bfa7e4edd93afb7bff3474f1f58214db559c14cc0a3998',
    },
    "tests/test_r5_active_regression.py::test_r5_active_suite_authentication_rejects_tampered_governed_source[source]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-tampered-source",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '59eeab6a013d8c6bd5bfa7e4edd93afb7bff3474f1f58214db559c14cc0a3998',
    },
    "tests/test_r5_active_regression.py::test_r5_active_suite_authentication_rejects_tampered_governed_source[disposition]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-tampered-disposition",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '59eeab6a013d8c6bd5bfa7e4edd93afb7bff3474f1f58214db559c14cc0a3998',
    },
    "tests/test_r5_active_regression.py::test_r5_selector_rejects_tampered_identity_and_node_sets": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-selector-is-exact",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '1f12316257903af72c3ed3b0da2c6afb8752b5abe7c96757045f2f1c77bd73b3',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_selects_no_known_raw_inactive_error_and_spawns_once": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-runs-one-process-without-inactive-errors",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'f1656b368f616a239631ab21cecc180e53c8e65b06180fb1e16ad894b321b310',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_rejects_tampered_report_and_removes_temporary_root": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-report-is-authenticated-and-ephemeral",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'd163dda3eba9d27803080d1c1fb405ff078ca547efb6f6cf977fcdab1635c28b',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_failure_names_bounded_failed_nodes_and_cleans": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-failure-summary-is-bounded",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'c93b98f6abb02bfe339198374da8632a095ded2a00edaf6f3e125fc131f81c35',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_rejects_contract_root_substitution": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-contract-binds-root",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '8ac439d16efc03ed00e37fe0950e29c2b381515b5983ac53de63e96d4d674a8e',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_translates_process_control_failure_and_cleans[timeout]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-timeout-is-controlled",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'a5e8a34210ceae71fbc7b2650683dfee80186b11e306c1874fcfb49aa172b5e4',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_translates_process_control_failure_and_cleans[output-limit]": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-output-limit-is-controlled",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'a5e8a34210ceae71fbc7b2650683dfee80186b11e306c1874fcfb49aa172b5e4',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_authenticates_mutated_snapshot_after_confirmed_timeout": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-authenticates-source-after-timeout",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '812f03d52a8512168b46563d5db8b6a234bbff8fb02f05692fa17b12295ba0ff',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_authenticates_mutated_snapshot_before_report_parsing": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-authenticates-source-before-report-parse",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '90a367719cdd0d9d0b1b8f47c81fc258b59aa64b087329ae5e85c2e0b57bb49b',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_rejects_live_source_drift_after_authentication": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-live-source-drift",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '6a6b2f90b89b39c8b901f6e90d11f80ce65402771b4e7485dd1c6df9f4e86f85',
    },
    "tests/test_r5_active_regression.py::test_r5_runner_rejects_snapshot_swap_before_pytest": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-rejects-snapshot-swap",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": 'd6a6dfb17b6762a148a57f4639c587209b1a771502f4aa7900a6f1a057ed4685',
    },
    "tests/test_r5_active_regression.py::test_r5_snapshot_cleanup_attempts_prune_after_remove_exception": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-cleanup-prunes-after-remove-error",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '0c145e7de1ccc6e8ce13f358871a92bba8a9be19b26457baa68012b93749536e',
    },
    "tests/test_r5_active_regression.py::test_r5_authenticated_snapshot_preserves_writable_fixture_copy_semantics": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-active-suite-preserves-writable-fixture-copies",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '7d74fa8a9146bd67496cbff6acc230a5798d62340c20c54a12d3ad112bf7a3e6',
    },
    "tests/test_r5_active_regression.py::test_r5_task10_uses_governed_active_suite_as_release_gate": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-task10-governs-active-suite-topology",
        "diagnostic_role": "phase",
        "introduced_by_task": "R5-Task-10-Topology-Correction",
        "source_ast_sha256": '15b32da1cd903224a82748362d81f1ceb6771496c239732787903079f98106bb',
    },
}
