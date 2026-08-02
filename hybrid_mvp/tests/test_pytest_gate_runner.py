from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = PROJECT_ROOT / "scripts" / "pytest_gate_runner.py"


def _runner():
    assert RUNNER_PATH.is_file(), "pytest gate runner has not been implemented"
    module_name = "_cemm_pytest_gate_runner_for_tests"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _content_ref(kind: str, value: object) -> str:
    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return f"{kind}:{digest[:24]}"


def _write_manifest(path: Path, payload: dict[str, object]) -> dict[str, object]:
    complete = dict(payload)
    complete["selector_ref"] = _content_ref("pytest_selector", payload)
    path.write_bytes(_canonical_bytes(complete))
    return complete


def _exact_payload(*node_ids: str) -> dict[str, object]:
    return {
        "schema": "cemm-pytest-selector-v1",
        "mode": "exact",
        "exact_node_ids": sorted(node_ids),
    }


def _admission_payload(
    *, collectable: tuple[str, ...], active: tuple[str, ...]
) -> dict[str, object]:
    return {
        "schema": "cemm-pytest-selector-v1",
        "mode": "admission",
        "test_root": "tests",
        "collectable_node_ids": sorted(collectable),
        "active_node_ids": sorted(active),
    }


@dataclass
class FakeItem:
    nodeid: str


class FakeHook:
    def __init__(self) -> None:
        self.deselected: list[str] = []

    def pytest_deselected(self, *, items: list[FakeItem]) -> None:
        self.deselected.extend(item.nodeid for item in items)


class FakeConfig:
    def __init__(self) -> None:
        self.hook = FakeHook()


class FakeSession:
    def __init__(self) -> None:
        self.shouldfail: str | bool = False


@dataclass
class FakeRunReport:
    nodeid: str
    when: str
    outcome: str
    duration: float = 0.001
    wasxfail: str | None = None


@dataclass
class FakeCollectReport:
    nodeid: str
    outcome: str
    longrepr: str = "collection failed"


def _collect(plugin: Any, node_ids: tuple[str, ...]) -> tuple[list[FakeItem], FakeSession, FakeConfig]:
    items = [FakeItem(node_id) for node_id in node_ids]
    session = FakeSession()
    config = FakeConfig()
    plugin.pytest_collection_modifyitems(session, config, items)
    plugin.pytest_collection_finish(session)
    return items, session, config


def _log_complete_pass(plugin: Any, node_id: str, duration: float = 0.001) -> None:
    plugin.pytest_runtest_logreport(FakeRunReport(node_id, "setup", "passed", 0.0))
    plugin.pytest_runtest_logreport(
        FakeRunReport(node_id, "call", "passed", duration)
    )
    plugin.pytest_runtest_logreport(FakeRunReport(node_id, "teardown", "passed", 0.0))


def test_exact_manifest_is_strict_and_content_addressed(tmp_path: Path) -> None:
    runner = _runner()
    node_ids = (
        "tests/test_alpha.py::test_one",
        "tests/test_alpha.py::test_two[case-a]",
    )
    path = tmp_path / "selector.json"
    expected = _write_manifest(path, _exact_payload(*node_ids))

    manifest = runner.load_selector_manifest(path)

    assert manifest.selector_ref == expected["selector_ref"]
    assert manifest.mode == "exact"
    assert manifest.expected_collected_node_ids == node_ids
    assert manifest.active_node_ids == node_ids
    assert manifest.pytest_targets == node_ids

    tampered = dict(expected)
    tampered["exact_node_ids"] = ["tests/test_alpha.py::test_changed"]
    path.write_bytes(_canonical_bytes(tampered))
    with pytest.raises(runner.ManifestError, match="identity"):
        runner.load_selector_manifest(path)


def test_admission_manifest_requires_active_subset_and_pinned_root(
    tmp_path: Path,
) -> None:
    runner = _runner()
    collectable = (
        "tests/test_alpha.py::test_one",
        "tests/test_beta.py::test_two",
        "tests/test_beta.py::test_three",
    )
    active = ("tests/test_beta.py::test_two",)
    path = tmp_path / "selector.json"
    _write_manifest(
        path,
        _admission_payload(collectable=collectable, active=active),
    )

    manifest = runner.load_selector_manifest(path)

    assert manifest.mode == "admission"
    assert manifest.test_root == "tests"
    assert manifest.expected_collected_node_ids == tuple(sorted(collectable))
    assert manifest.active_node_ids == active
    assert manifest.pytest_targets == ("tests",)

    invalid = _admission_payload(
        collectable=collectable,
        active=("tests/test_missing.py::test_missing",),
    )
    _write_manifest(path, invalid)
    with pytest.raises(runner.ManifestError, match="subset"):
        runner.load_selector_manifest(path)

    wrong_root = _admission_payload(collectable=collectable, active=active)
    wrong_root["test_root"] = "tests/../outside"
    _write_manifest(path, wrong_root)
    with pytest.raises(runner.ManifestError, match="test_root"):
        runner.load_selector_manifest(path)


@pytest.mark.parametrize(
    "defect",
    ["duplicate-key", "unknown-field", "unsorted", "unsafe-node", "non-finite"],
    ids=["duplicate-key", "unknown-field", "unsorted", "unsafe-node", "non-finite"],
)
def test_manifest_rejects_noncanonical_shapes(tmp_path: Path, defect: str) -> None:
    runner = _runner()
    path = tmp_path / "selector.json"
    payload = _exact_payload(
        "tests/test_alpha.py::test_a",
        "tests/test_alpha.py::test_b",
    )
    complete = _write_manifest(path, payload)

    if defect == "duplicate-key":
        path.write_text(
            '{"schema":"cemm-pytest-selector-v1",'
            '"schema":"cemm-pytest-selector-v1"}',
            encoding="utf-8",
        )
    elif defect == "unknown-field":
        complete["extra"] = True
        path.write_bytes(_canonical_bytes(complete))
    elif defect == "unsorted":
        payload["exact_node_ids"] = list(reversed(payload["exact_node_ids"]))
        _write_manifest(path, payload)
    elif defect == "unsafe-node":
        payload["exact_node_ids"] = ["../tests/test_alpha.py::test_a"]
        _write_manifest(path, payload)
    else:
        path.write_text(
            '{"schema":"cemm-pytest-selector-v1",'
            '"mode":"exact","exact_node_ids":[NaN],'
            '"selector_ref":"pytest_selector:000000000000000000000000"}',
            encoding="utf-8",
        )

    with pytest.raises(runner.ManifestError):
        runner.load_selector_manifest(path)


def test_manifest_reader_rejects_empty_file(tmp_path: Path) -> None:
    runner = _runner()
    path = tmp_path / "selector.json"
    path.write_bytes(b"")

    with pytest.raises(runner.ManifestError, match="empty"):
        runner.load_selector_manifest(path)


def test_manifest_reader_caps_read_before_rejecting_oversize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    path = tmp_path / "selector.json"
    read_sizes: list[int] = []

    class OversizedStream:
        def __enter__(self) -> "OversizedStream":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            read_sizes.append(size)
            return b"x" * (runner.MAX_MANIFEST_BYTES + 1)

    def fake_open(
        _path: Path,
        mode: str = "r",
        *_args: object,
        **_kwargs: object,
    ) -> OversizedStream:
        assert mode == "rb"
        return OversizedStream()

    monkeypatch.setattr(Path, "open", fake_open)

    with pytest.raises(runner.ManifestError, match="exceeds its byte bound"):
        runner.load_selector_manifest(path)

    assert read_sizes == [runner.MAX_MANIFEST_BYTES + 1]


def test_exact_plugin_rejects_collection_mismatch_before_calls() -> None:
    runner = _runner()
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        ("tests/test_alpha.py::test_expected",),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)

    items, session, config = _collect(
        plugin,
        ("tests/test_alpha.py::test_unexpected",),
    )
    payload = plugin.finalize(exitstatus=1)

    assert items == []
    assert session.shouldfail
    assert config.hook.deselected == ["tests/test_alpha.py::test_unexpected"]
    assert payload["disposition"] == "error"
    assert "collection_mismatch" in payload["error_codes"]
    assert payload["facts"] == []
    assert payload["collection_mismatch"] == {
        "duplicate_node_ids": [],
        "extra_node_ids": ["tests/test_alpha.py::test_unexpected"],
        "missing_node_ids": ["tests/test_alpha.py::test_expected"],
    }


def test_admission_plugin_compares_full_collection_then_deselects_inactive() -> None:
    runner = _runner()
    all_nodes = (
        "tests/test_alpha.py::test_a",
        "tests/test_alpha.py::test_b",
        "tests/test_beta.py::test_c",
    )
    active = ("tests/test_alpha.py::test_b",)
    manifest = runner.SelectorManifest.for_admission(
        "pytest_selector:000000000000000000000000",
        test_root="tests",
        collectable_node_ids=all_nodes,
        active_node_ids=active,
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)

    items, session, config = _collect(plugin, all_nodes)
    _log_complete_pass(plugin, active[0], duration=0.25)
    payload = plugin.finalize(exitstatus=0)

    assert not session.shouldfail
    assert [item.nodeid for item in items] == list(active)
    assert config.hook.deselected == [all_nodes[0], all_nodes[2]]
    assert payload["collected_node_ids"] == list(all_nodes)
    assert payload["selected_node_ids"] == list(active)
    assert payload["deselected_node_ids"] == [all_nodes[0], all_nodes[2]]
    assert payload["counts"] == {
        "error": 0,
        "failure": 0,
        "passed": 1,
        "skip": 0,
        "xfail": 0,
        "xpass": 0,
    }
    assert payload["disposition"] == "passed"


def test_selected_skip_fails_governed_report() -> None:
    runner = _runner()
    node = "tests/test_outcomes.py::test_skip"
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (node,),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)
    _collect(plugin, (node,))
    plugin.pytest_runtest_logreport(
        FakeRunReport(node, "setup", "skipped", duration=0.1)
    )

    payload = plugin.finalize(exitstatus=0)

    assert payload["counts"]["skip"] == 1
    assert payload["disposition"] == "failed"


def test_selected_xfail_fails_governed_report() -> None:
    runner = _runner()
    node = "tests/test_outcomes.py::test_xfail"
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (node,),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)
    _collect(plugin, (node,))
    plugin.pytest_runtest_logreport(
        FakeRunReport(
            node,
            "call",
            "skipped",
            duration=0.1,
            wasxfail="known defect",
        )
    )

    payload = plugin.finalize(exitstatus=0)

    assert payload["counts"]["xfail"] == 1
    assert payload["disposition"] == "failed"


def test_report_classification_is_structural_and_bounded() -> None:
    runner = _runner()
    nodes = tuple(
        sorted(
            f"tests/test_outcomes.py::test_{name}"
            for name in ("pass", "failure", "error", "skip", "xfail", "xpass")
        )
    )
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        nodes,
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(
        manifest,
        slowest_limit=2,
    )
    _collect(plugin, nodes)
    _log_complete_pass(plugin, nodes[0], duration=0.1)
    plugin.pytest_runtest_logreport(FakeRunReport(nodes[1], "call", "failed", 0.2))
    plugin.pytest_runtest_logreport(FakeRunReport(nodes[2], "setup", "failed", 0.3))
    plugin.pytest_runtest_logreport(FakeRunReport(nodes[3], "setup", "skipped", 0.4))
    plugin.pytest_runtest_logreport(
        FakeRunReport(nodes[4], "call", "skipped", 0.5, wasxfail="known")
    )
    plugin.pytest_runtest_logreport(
        FakeRunReport(nodes[5], "call", "passed", 0.6, wasxfail="unexpected")
    )

    payload = plugin.finalize(exitstatus=1)

    assert payload["counts"] == {
        "error": 1,
        "failure": 1,
        "passed": 1,
        "skip": 1,
        "xfail": 1,
        "xpass": 1,
    }
    assert payload["disposition"] == "error"
    assert payload["slowest"] == [
        {"duration_ns": 600_000_000, "node_id": nodes[5]},
        {"duration_ns": 500_000_000, "node_id": nodes[4]},
    ]
    assert len(payload["facts"]) == 6

    incomplete_node = "tests/test_outcomes.py::test_incomplete_lifecycle"
    incomplete_manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (incomplete_node,),
    )
    incomplete = runner.StructuredReportPlugin.for_unit_test(incomplete_manifest)
    _collect(incomplete, (incomplete_node,))
    incomplete.pytest_runtest_logreport(
        FakeRunReport(incomplete_node, "setup", "passed", 0.0)
    )
    incomplete.pytest_runtest_logreport(
        FakeRunReport(incomplete_node, "call", "passed", 0.1)
    )
    incomplete_payload = incomplete.finalize(exitstatus=0)

    assert incomplete_payload["counts"]["error"] == 1
    assert incomplete_payload["counts"]["passed"] == 0
    assert incomplete_payload["disposition"] == "error"
    assert "missing_report" in incomplete_payload["error_codes"]


def test_collection_error_is_structured_without_nested_pytest() -> None:
    runner = _runner()
    node = "tests/test_broken.py::test_never_runs"
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (node,),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)

    plugin.pytest_collectreport(
        FakeCollectReport(nodeid="tests/test_broken.py", outcome="failed")
    )
    payload = plugin.finalize(exitstatus=2)

    assert payload["counts"]["error"] == 1
    assert payload["disposition"] == "error"
    assert payload["collection_errors"] == [
        {
            "message": "collection failed",
            "node_id": "tests/test_broken.py",
        }
    ]
    assert "collection_error" in payload["error_codes"]


def test_report_write_is_exclusive_and_content_addressed(tmp_path: Path) -> None:
    runner = _runner()
    node = "tests/test_alpha.py::test_one"
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (node,),
    )
    report_path = tmp_path / "report.json"
    plugin = runner.StructuredReportPlugin(manifest, report_path=report_path)
    _collect(plugin, (node,))
    _log_complete_pass(plugin, node)

    payload = plugin.write_report(exitstatus=0)
    raw = report_path.read_bytes()
    stored = json.loads(raw)
    identity_payload = dict(stored)
    report_ref = identity_payload.pop("report_ref")

    assert raw == _canonical_bytes(stored)
    assert stored == payload
    assert report_ref == _content_ref("pytest_report", identity_payload)
    with pytest.raises(FileExistsError):
        plugin.write_report(exitstatus=0)


def test_main_calls_pytest_once_with_manifest_targets_and_isolated_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    node = "tests/test_alpha.py::test_one"
    manifest_path = tmp_path / "selector.json"
    report_path = tmp_path / "report.json"
    _write_manifest(manifest_path, _exact_payload(node))
    calls: list[tuple[list[str], list[object]]] = []

    def fake_pytest_main(args: list[str], *, plugins: list[object]) -> int:
        calls.append((list(args), list(plugins)))
        plugin = plugins[0]
        items, session, _config = _collect(plugin, (node,))
        assert [item.nodeid for item in items] == [node]
        _log_complete_pass(plugin, node)
        plugin.pytest_sessionfinish(session, 0)
        return 0

    monkeypatch.setattr(runner.pytest, "main", fake_pytest_main)
    project_root_text = str(PROJECT_ROOT)
    monkeypatch.setattr(
        runner.sys,
        "path",
        [entry for entry in runner.sys.path if entry != project_root_text],
    )
    expected_sys_path = list(runner.sys.path)

    exit_code = runner.main(
        [
            "--selector-manifest",
            str(manifest_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1
    args, plugins = calls[0]
    assert node in args
    assert args[args.index("-c") + 1] == str(PROJECT_ROOT / "pyproject.toml")
    assert args[args.index("--confcutdir") + 1] == str(PROJECT_ROOT / "tests")
    assert "--basetemp" not in " ".join(args)
    assert "no:tmpdir" in args
    assert "no:cacheprovider" in args
    assert not any(argument.startswith("cache_dir=") for argument in args)
    assert len(plugins) == 1
    assert runner.sys.path == expected_sys_path
    assert json.loads(report_path.read_text(encoding="utf-8"))["disposition"] == "passed"


def test_main_records_pytest_exception_as_infrastructure_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    node = "tests/test_alpha.py::test_one"
    manifest_path = tmp_path / "selector.json"
    report_path = tmp_path / "report.json"
    _write_manifest(manifest_path, _exact_payload(node))

    def explode(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("boom")

    monkeypatch.setattr(runner.pytest, "main", explode)

    exit_code = runner.main(
        [
            "--selector-manifest",
            str(manifest_path),
            "--report",
            str(report_path),
        ]
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 2
    assert payload["disposition"] == "error"
    assert "pytest_exception" in payload["error_codes"]
    assert "boom" in payload["errors"][0]["message"]


def test_finalize_rejects_coercible_non_integer_exitstatus() -> None:
    runner = _runner()
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        ("tests/test_alpha.py::test_one",),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)

    for exitstatus in (True, 1.0, "1", None):
        with pytest.raises(runner.ReportError, match="integer"):
            plugin.finalize(exitstatus=exitstatus)


def test_collection_not_finished_has_bounded_diagnostic_row() -> None:
    runner = _runner()
    node = "tests/test_alpha.py::test_one"
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (node,),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)
    items = [FakeItem(node)]
    plugin.pytest_collection_modifyitems(FakeSession(), FakeConfig(), items)

    payload = plugin.finalize(exitstatus=2)

    rows = [
        row
        for row in payload["errors"]
        if row["code"] == "collection_not_finished"
    ]
    assert len(rows) == 1
    assert rows[0]["message"]
    assert len(rows[0]["message"]) <= runner.MAX_ERROR_CHARS
    assert "collection_not_finished" in payload["error_codes"]
    assert payload["disposition"] == "error"


def test_bounded_text_contains_hostile_stringification_and_long_text() -> None:
    runner = _runner()

    class HostileText:
        def __str__(self) -> str:
            raise RuntimeError("stringification failed")

    hostile = runner._bounded_text(HostileText())
    bounded = runner._bounded_text("x" * (runner.MAX_ERROR_CHARS + 10_000))

    assert hostile.startswith("<unprintable HostileText")
    assert len(hostile) <= runner.MAX_ERROR_CHARS
    assert len(bounded) == runner.MAX_ERROR_CHARS
    assert bounded.startswith("x" * (runner.MAX_ERROR_CHARS - 1))


def test_extreme_finite_duration_is_structured_infrastructure_error() -> None:
    runner = _runner()
    node = "tests/test_alpha.py::test_one"
    manifest = runner.SelectorManifest.for_exact(
        "pytest_selector:000000000000000000000000",
        (node,),
    )
    plugin = runner.StructuredReportPlugin.for_unit_test(manifest)
    _collect(plugin, (node,))
    plugin.pytest_runtest_logreport(
        FakeRunReport(node, "call", "passed", duration=sys.float_info.max)
    )

    payload = plugin.finalize(exitstatus=0)

    assert payload["disposition"] == "error"
    assert "duration_aggregation_error" in payload["error_codes"]
    assert any(
        row["code"] == "duration_aggregation_error"
        and row["node_id"] == node
        for row in payload["errors"]
    )
    assert payload["facts"] == [
        {
            "classification": "error",
            "duration_ns": 0,
            "node_id": node,
            "reports": [
                {"outcome": "passed", "wasxfail": False, "when": "call"}
            ],
        }
    ]


def test_main_contains_arithmetic_failure_during_report_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    node = "tests/test_alpha.py::test_one"
    manifest_path = tmp_path / "selector.json"
    report_path = tmp_path / "report.json"
    _write_manifest(manifest_path, _exact_payload(node))

    def explode_pytest(*_args: object, **_kwargs: object) -> int:
        raise OverflowError("pytest arithmetic failed")

    def explode_report(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise OverflowError("report arithmetic failed")

    monkeypatch.setattr(runner.pytest, "main", explode_pytest)
    monkeypatch.setattr(runner.StructuredReportPlugin, "write_report", explode_report)

    assert runner.main(
        [
            "--selector-manifest",
            str(manifest_path),
            "--report",
            str(report_path),
        ]
    ) == 2


def test_runner_import_boundary_is_stdlib_plus_pytest() -> None:
    _runner()
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots <= {
        "__future__",
        "argparse",
        "collections",
        "dataclasses",
        "hashlib",
        "json",
        "math",
        "os",
        "pathlib",
        "re",
        "sys",
        "typing",
        "pytest",
    }
    assert not {
        "cemm_authoritative_hybrid",
        "model",
        "torch",
        "training",
    } & imported_roots


__cemm_test_inventory__ = {
    "tests/test_pytest_gate_runner.py::test_admission_manifest_requires_active_subset_and_pinned_root": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-admission-manifest-bounds",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'b19bbc71c8132d146085d387a35c603a820fd7ef5c9f72ff6e9f13c7673a2ab3',
    },
    "tests/test_pytest_gate_runner.py::test_admission_plugin_compares_full_collection_then_deselects_inactive": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-admission-collection-equality",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '3ed441686c4d4488a89f1fd591ebb056934c8c2852a6fef46750f14af4e40aa8',
    },
    "tests/test_pytest_gate_runner.py::test_bounded_text_contains_hostile_stringification_and_long_text": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-bounded-hostile-text",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6e910b716cec0cfef4ebba0e38bf5c7cc4e1c4c4bf46c29680eee734a155f6f8',
    },
    "tests/test_pytest_gate_runner.py::test_collection_error_is_structured_without_nested_pytest": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-collection-error-structured",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '34d086e0277e11d431710452d9fd3451238c99afff4189ad50a9d338fb7b71b7',
    },
    "tests/test_pytest_gate_runner.py::test_collection_not_finished_has_bounded_diagnostic_row": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-collection-not-finished-diagnostic",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'aad3e199185d65ff360cef7e410655ba5dfd22631cfc960c859b147f34c7fac3',
    },
    "tests/test_pytest_gate_runner.py::test_exact_manifest_is_strict_and_content_addressed": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-exact-manifest-identity",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '8f10448097e031c6b562294910177739d82b7cae5e28757af230ce7d729aae34',
    },
    "tests/test_pytest_gate_runner.py::test_exact_plugin_rejects_collection_mismatch_before_calls": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-exact-collection-equality",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '5aa4fca7c1021ef4ddd1cbf20260c15cc6970431c15e658ca53b5891cc6e770f',
    },
    "tests/test_pytest_gate_runner.py::test_extreme_finite_duration_is_structured_infrastructure_error": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-duration-overflow-infrastructure-error",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'bc60d6ba420611fc9c10239fe0c2821e1ea56028e04bb4f816ab00a3a6984b7c',
    },
    "tests/test_pytest_gate_runner.py::test_finalize_rejects_coercible_non_integer_exitstatus": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-exact-integer-exitstatus",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'b3be211b6d1e85fed57233a9029de1201c69357a85cd86013e82adc7616107e3',
    },
    "tests/test_pytest_gate_runner.py::test_main_calls_pytest_once_with_manifest_targets_and_isolated_paths": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-one-process-isolated-paths",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'd44a928955f7f68807641ad0df491c703735212519c02ea37f1d1002dd4077ae',
    },
    "tests/test_pytest_gate_runner.py::test_main_contains_arithmetic_failure_during_report_retry": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-report-retry-arithmetic-containment",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'eef8ca68af116e5c3affa41307e76cbe90b26a0aae5c42fbaa4bfa81f5a2cce1',
    },
    "tests/test_pytest_gate_runner.py::test_main_records_pytest_exception_as_infrastructure_error": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-exception-infrastructure-error",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '642937226c998bf4cc3c032a59ad07748bbcc35f423b1cb21f8bdd7cfc6a7eca',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_reader_caps_read_before_rejecting_oversize": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-runner-manifest-read-is-bounded",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '3ae4826188f4a9b686cada5e01fa2379cddf1ba9ae1e41b1978f88e3e5ef48f5',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_reader_rejects_empty_file": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-runner-manifest-empty-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'f5d3bc5a5f4c517c441ad0d58a275b1c65464ce7936bd2ab1a630df19ea1134c',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_rejects_noncanonical_shapes[duplicate-key]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-rejects-noncanonical-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6fd273e353cbf9339088cfcb17ded04110b4ad4bfae5d587ba20f4e70b95d51d',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_rejects_noncanonical_shapes[non-finite]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-rejects-noncanonical-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6fd273e353cbf9339088cfcb17ded04110b4ad4bfae5d587ba20f4e70b95d51d',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_rejects_noncanonical_shapes[unknown-field]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-rejects-noncanonical-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6fd273e353cbf9339088cfcb17ded04110b4ad4bfae5d587ba20f4e70b95d51d',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_rejects_noncanonical_shapes[unsafe-node]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-rejects-noncanonical-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6fd273e353cbf9339088cfcb17ded04110b4ad4bfae5d587ba20f4e70b95d51d',
    },
    "tests/test_pytest_gate_runner.py::test_manifest_rejects_noncanonical_shapes[unsorted]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-rejects-noncanonical-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6fd273e353cbf9339088cfcb17ded04110b4ad4bfae5d587ba20f4e70b95d51d',
    },
    "tests/test_pytest_gate_runner.py::test_report_classification_is_structural_and_bounded": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-report-classification-structural",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '59d66092a40bc5298fcda8bc30ba6ea4f8f0b3af07ff340450ef39e5be5af4de',
    },
    "tests/test_pytest_gate_runner.py::test_report_write_is_exclusive_and_content_addressed": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-report-exclusive-content-addressed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '05ff248d1d495b2bee094504a9382dbb63f10222a9f469c69c1a60aef878f561',
    },
    "tests/test_pytest_gate_runner.py::test_runner_import_boundary_is_stdlib_plus_pytest": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:pytest-runner-import-boundary",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": '6e5780b3c2da8f71e3641afe00de7cf44a85fcf524d0342a5d1f06dbb7300ba8',
    },
    "tests/test_pytest_gate_runner.py::test_selected_skip_fails_governed_report": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-runner-selected-skip-fails",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'c6441defb7bec70df2a97b099cac0538ac5e00fa63683318a4f4d342e28b574a',
    },
    "tests/test_pytest_gate_runner.py::test_selected_xfail_fails_governed_report": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-runner-selected-xfail-fails",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": 'fb4292ea1670bf826866a6eee3310a179b1f435f3a7dff439ff52fa5c1b5539b',
    },
}
