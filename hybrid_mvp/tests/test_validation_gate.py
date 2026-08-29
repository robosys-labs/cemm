"""Tests for the bounded corrective-replay validation control plane."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cemm_authoritative_hybrid import process_control as process_control_module  # noqa: E402
sys.modules["process_control"] = process_control_module
import validation_gate as validation_gate_module  # noqa: E402
import test_inventory_core as inventory_core_module  # noqa: E402
from cemm_authoritative_hybrid.process_control import (  # noqa: E402
    ProcessControlError,
    ProcessErrorReason,
    capture_bounded_process,
)
from validation_gate import (  # noqa: E402
    AdmissionValidationError,
    EvidenceFile,
    GateConfigError,
    GateGraph,
    GatePolicy,
    GateReceipt,
    StepResult,
    bounded_slowest,
    canonical_json_bytes,
    content_ref,
    current_environment_material,
    isolated_test_environment,
    load_strict_json,
    load_verified_admission_receipt,
    observe_process,
    parse_pytest_report,
    verify_current_source_config,
    write_receipt_exclusive,
)


def _limits() -> dict[str, int]:
    return {
        "max_output_bytes": 1_048_576,
        "max_pytest_processes_per_tier": 1,
        "max_report_bytes": 1_048_576,
        "max_slowest_rows": 10,
        "max_steps_per_tier": 8,
        "pytest_timeout_seconds": 300,
        "rss_poll_interval_ms": 25,
    }


def _graph_payload() -> dict[str, object]:
    return {
        "limits": _limits(),
        "phases": {
            "G0": {
                "admission": ["pytest_active"],
                "owners": {"validation-runner": ["g0_owner_tests"]},
                "phase": ["g0_phase_tests"],
            }
        },
        "schema": "cemm-hybrid-validation-gates-v1",
        "steps": {
            "g0_owner_tests": {
                "depends_on": ["source_compile"],
                "exact_nodes": [
                    "tests/test_validation_gate.py::test_dag_deduplicates_shared_dependencies"
                ],
                "inputs": ["tests/test_validation_gate.py"],
                "kind": "pytest",
            },
            "g0_phase_tests": {
                "depends_on": ["source_compile"],
                "exact_nodes": [
                    "tests/test_g0_integration.py::test_g0_admission_plan_is_coalesced_and_bounded"
                ],
                "inputs": ["tests/test_g0_integration.py"],
                "kind": "pytest",
            },
            "governance": {
                "depends_on": [],
                "inputs": [
                    "docs/DOCUMENT_AUTHORITY.json",
                    "governance/receipt_invalidations.jsonl",
                    "governance/replay_status.jsonl",
                    "governance/test_inventory.json",
                    "pyproject.toml",
                ],
                "invalidation_ledger": "governance/receipt_invalidations.jsonl",
                "kind": "governance",
                "metadata_symbol": "__cemm_test_inventory__",
                "status_ledger": "governance/replay_status.jsonl",
                "test_inventory": "governance/test_inventory.json",
            },
            "pytest_active": {
                "depends_on": ["source_compile"],
                "inputs": [
                    "governance/test_inventory.json",
                    "pyproject.toml",
                    "src/",
                    "tests/",
                ],
                "kind": "pytest_inventory",
                "metadata_symbol": "__cemm_test_inventory__",
                "test_inventory": "governance/test_inventory.json",
                "test_root": "tests",
            },
            "source_compile": {
                "depends_on": ["governance"],
                "inputs": ["scripts/", "src/"],
                "kind": "compile",
                "roots": ["scripts/", "src/"],
            },
        },
    }


def _materialize_fixture_inputs(root: Path) -> None:
    for relative in (
        "docs/DOCUMENT_AUTHORITY.json",
        "governance/receipt_invalidations.jsonl",
        "governance/replay_status.jsonl",
        "governance/test_inventory.json",
        "pyproject.toml",
        "scripts/fixture.py",
        "src/fixture.py",
        "tests/test_g0_integration.py",
        "tests/test_validation_gate.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("fixture", encoding="utf-8")


def _dummy_evidence(path: str) -> EvidenceFile:
    return EvidenceFile(path=path, sha256="a" * 64)

def _fixture_input_files(
    root: Path, definition: dict[str, object]
) -> tuple[EvidenceFile, ...]:
    paths: set[str] = set()
    for declared in definition["inputs"]:
        target = root / str(declared).rstrip("/")
        if target.is_file():
            paths.add(target.relative_to(root).as_posix())
        else:
            paths.update(
                path.relative_to(root).as_posix()
                for path in target.rglob("*")
                if path.is_file()
            )
    return tuple(EvidenceFile.from_path(root, path) for path in sorted(paths))

def _receipt(root: Path) -> GateReceipt:
    _materialize_fixture_inputs(root)
    evidence_root = root / "artifacts" / "validation"
    evidence_root.mkdir(parents=True, exist_ok=True)
    for name in ("BASELINE_REPLAY_FINDINGS.json", "TEST_INVENTORY_RECEIPT.json"):
        (evidence_root / name).write_bytes(
            (ROOT / "artifacts" / "validation" / name).read_bytes()
        )
    config = _graph_payload()
    environment = current_environment_material(root)
    config_ref = content_ref("gate_config", config)
    environment_ref = content_ref("environment", environment)
    source_ref = "a" * 40
    step_results: list[StepResult] = []
    dependency_refs: tuple[str, ...] = ()
    for step_id in ("governance", "source_compile", "pytest_active"):
        report = None
        observation = None
        selector = None
        slowest: tuple[tuple[str, int], ...] = ()
        inputs = _fixture_input_files(root, config["steps"][step_id])
        if step_id == "governance":
            report = {
                "active_node_count": 1,
                "active_node_set_ref": content_ref("active_test_nodes", ["node"]),
                "collectable_node_count": 1,
                "collectable_node_set_ref": content_ref("collectable_test_nodes", ["node"]),
                "invalidation_record_count": 0,
                "inventory_ref": content_ref("test_inventory", {"value": 1}),
                "literal_metadata_ref": content_ref("literal_test_metadata", {"value": 1}),
                "parsed_module_count": 1,
                "schema": "cemm-governance-step-report-v1",
                "status_head_ref": "governance_record:" + "b" * 24,
                "status_record_count": 9,
            }
            observation = report
        elif step_id == "source_compile":
            compiled = [
                {"path": item.path, "sha256": item.sha256}
                for item in inputs
                if item.path.endswith(".py")
            ]
            report = {
                "compiled_file_count": len(compiled),
                "compiled_set_ref": content_ref("compiled_sources", compiled),
                "schema": "cemm-compile-step-report-v1",
            }
            observation = report
        else:
            observation = _producer_pytest_report()
            nodes = tuple(observation["expected_collected_node_ids"])
            selector = _admission_selector(nodes, nodes)
            observation["mode"] = "admission"
            observation["selector_ref"] = selector["selector_ref"]
            observation["test_root"] = "tests"
            observation.pop("report_ref")
            observation["report_ref"] = content_ref("pytest_report", observation)
            report = _semantic_pytest_projection(observation)
            slowest = ((nodes[0], 10),)
        result = StepResult.create(
            config_ref=config_ref,
            definition=config["steps"][step_id],
            dependency_step_refs=dependency_refs,
            disposition="passed",
            environment_ref=environment_ref,
            error_code=None,
            exit_code=0,
            input_files=inputs,
            kind=config["steps"][step_id]["kind"],
            peak_rss_bytes=100 if report is not None else None,
            report=report,
            selector=selector,
            slowest=slowest,
            source_ref=source_ref,
            step_id=step_id,
            wall_ns=10,
            observation_report=observation,
        )
        step_results.append(result)
        dependency_refs = (result.step_ref,)
    return GateReceipt.create(
        config=config,
        environment=environment,
        evidence_files=(
            EvidenceFile.from_path(
                root, "artifacts/validation/BASELINE_REPLAY_FINDINGS.json"
            ),
            EvidenceFile.from_path(
                root, "artifacts/validation/TEST_INVENTORY_RECEIPT.json"
            ),
        ),
        fresh=True,
        phase="G0",
        pre_admission_status_head_ref="governance_record:" + "b" * 24,
        run_nonce="nonce-for-test",
        source_ref=source_ref,
        started_at_utc="2026-07-31T00:00:00Z",
        step_results=tuple(step_results),
        tier="admission",
    )



def _producer_pytest_report(
    *, classification: str = "passed", duration_ns: int = 10
) -> dict[str, object]:
    node_id = "tests/test_example.py::test_example"
    if classification == "error":
        reports = [
            {"outcome": "failed", "wasxfail": False, "when": "setup"}
        ]
    elif classification == "skip":
        reports = [
            {"outcome": "skipped", "wasxfail": False, "when": "setup"}
        ]
    elif classification == "xfail":
        reports = [
            {"outcome": "passed", "wasxfail": False, "when": "setup"},
            {"outcome": "skipped", "wasxfail": True, "when": "call"},
            {"outcome": "passed", "wasxfail": False, "when": "teardown"},
        ]
    elif classification == "xpass":
        reports = [
            {"outcome": "passed", "wasxfail": False, "when": "setup"},
            {"outcome": "passed", "wasxfail": True, "when": "call"},
            {"outcome": "passed", "wasxfail": False, "when": "teardown"},
        ]
    else:
        reports = [
            {"outcome": "passed", "wasxfail": False, "when": "setup"},
            {
                "outcome": "failed" if classification == "failure" else "passed",
                "wasxfail": False,
                "when": "call",
            },
            {"outcome": "passed", "wasxfail": False, "when": "teardown"},
        ]
    counts = {
        key: int(classification == key)
        for key in ("error", "failure", "passed", "skip", "xfail", "xpass")
    }
    errors: list[dict[str, str]] = []
    if classification in {"error", "failure"}:
        errors.append(
            {
                "code": "test_error" if classification == "error" else "test_failure",
                "message": f"{classification} phase failed",
                "node_id": node_id,
            }
        )
    payload: dict[str, object] = {
        "active_node_ids": [node_id],
        "collected_node_ids": [node_id],
        "collection_errors": [],
        "collection_mismatch": None,
        "counts": counts,
        "deselected_node_ids": [],
        "disposition": (
            "error"
            if classification == "error"
            else "failed"
            if classification in {"failure", "skip", "xfail", "xpass"}
            else "passed"
        ),
        "error_codes": [],
        "errors": errors,
        "errors_truncated": False,
        "exit_status": 1 if classification in {"failure", "error", "xpass"} else 0,
        "expected_collected_node_ids": [node_id],
        "facts": [
            {
                "classification": classification,
                "duration_ns": duration_ns,
                "node_id": node_id,
                "reports": reports,
            }
        ],
        "mode": "exact",
        "schema": "cemm-pytest-report-v1",
        "selected_node_ids": [node_id],
        "selector_ref": "",
        "slowest": [{"duration_ns": duration_ns, "node_id": node_id}],
        "test_root": None,
    }
    selector = _exact_selector((node_id,))
    payload["selector_ref"] = selector["selector_ref"]
    payload["report_ref"] = content_ref("pytest_report", payload)
    return payload

def _exact_selector(node_ids: tuple[str, ...]) -> dict[str, object]:
    selector: dict[str, object] = {
        "exact_node_ids": list(node_ids),
        "mode": "exact",
        "schema": "cemm-pytest-selector-v1",
    }
    selector["selector_ref"] = content_ref("pytest_selector", selector)
    return selector


def _admission_selector(
    active_node_ids: tuple[str, ...],
    collectable_node_ids: tuple[str, ...],
) -> dict[str, object]:
    selector: dict[str, object] = {
        "active_node_ids": list(active_node_ids),
        "collectable_node_ids": list(collectable_node_ids),
        "mode": "admission",
        "schema": "cemm-pytest-selector-v1",
        "test_root": "tests",
    }
    selector["selector_ref"] = content_ref("pytest_selector", selector)
    return selector

def _semantic_pytest_projection(payload: dict[str, object]) -> dict[str, object]:
    projected = json.loads(canonical_json_bytes(payload))
    projected.pop("report_ref")
    projected.pop("slowest")
    for fact in projected["facts"]:
        fact.pop("duration_ns")
    return projected


def _write_pytest_report(path: Path, payload: dict[str, object]) -> None:
    material = dict(payload)
    material.pop("report_ref", None)
    material["report_ref"] = content_ref("pytest_report", material)
    path.write_bytes(canonical_json_bytes(material))
def test_strict_json_rejects_duplicate_keys_and_nonfinite(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(GateConfigError, match="duplicate JSON key"):
        load_strict_json(duplicate)
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"a":NaN}', encoding="utf-8")
    with pytest.raises(GateConfigError, match="non-finite"):
        load_strict_json(nonfinite)


def test_dag_deduplicates_shared_dependencies() -> None:
    graph = GateGraph.from_dict(_graph_payload())
    assert graph.resolve_phase("G0", "admission") == (
        "governance",
        "source_compile",
        "pytest_active",
    )
    assert isinstance(graph.material["steps"]["pytest_active"]["inputs"], tuple)
    with pytest.raises(TypeError):
        graph.material["steps"]["pytest_active"]["kind"] = "compile"


def test_dag_rejects_cycles_and_unknown_dependencies() -> None:
    payload = _graph_payload()
    payload["steps"]["governance"]["depends_on"] = ["source_compile"]
    with pytest.raises(GateConfigError, match="cycle"):
        GateGraph.from_dict(payload)

    payload = _graph_payload()
    payload["steps"]["source_compile"]["depends_on"] = ["missing"]
    with pytest.raises(GateConfigError, match="unknown dependency"):
        GateGraph.from_dict(payload)


def test_config_rejects_raw_selectors_and_owner_phase_overlap() -> None:
    payload = _graph_payload()
    payload["steps"]["g0_owner_tests"]["exact_nodes"] = [
        "tests/test_validation_gate.py"
    ]
    with pytest.raises(GateConfigError, match="exact node selectors required"):
        GateGraph.from_dict(payload)

    payload = _graph_payload()
    node = payload["steps"]["g0_owner_tests"]["exact_nodes"][0]
    payload["steps"]["g0_phase_tests"]["exact_nodes"] = [node]
    with pytest.raises(GateConfigError, match="owner/phase node overlap"):
        GateGraph.from_dict(payload)


def test_every_test_tier_is_fresh_and_single_process() -> None:
    graph = GateGraph.from_dict(_graph_payload())
    for tier in ("owner", "phase", "admission"):
        assert GatePolicy.for_tier(tier).test_results_must_be_fresh
    assert graph.pytest_process_count(
        "G0", "owner", owner="validation-runner"
    ) == 1
    assert graph.pytest_process_count("G0", "phase") == 1
    assert graph.pytest_process_count("G0", "admission") == 1


def test_isolated_environment_owns_all_writable_paths(tmp_path: Path) -> None:
    inherited = {
        "PATH": "kept",
        "PYTHONHOME": "forbidden",
        "PYTHONPATH": "forbidden",
        "PYTEST_ADDOPTS": "forbidden",
    }
    env, pytest_args = isolated_test_environment(tmp_path, inherited=inherited)
    for key in ("TMP", "TEMP", "TMPDIR", "PYTHONPYCACHEPREFIX"):
        assert Path(env[key]).is_relative_to(tmp_path)
    assert env["PATH"] == "kept"
    assert not {"PYTHONHOME", "PYTHONPATH", "PYTEST_ADDOPTS"} & set(env)
    assert Path(env["CEMM_PYTEST_IMPORT_ROOT"]).is_dir()
    assert str(tmp_path) in " ".join(pytest_args)
    command = validation_gate_module._pytest_runner_command(
        ROOT,
        tmp_path / "selector.json",
        tmp_path / "report.json",
    )
    assert command[:3] == (sys.executable, "-P", "-s")
    assert command[3] == str(ROOT / "scripts" / "pytest_gate_runner.py")


def test_git_snapshot_rejects_success_with_warning_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        returncode = 0
        stdout = ("# branch.oid " + "a" * 40 + "\n").encode("ascii")
        stderr = b"warning: access denied"

    monkeypatch.setattr(
        validation_gate_module,
        "capture_bounded_process",
        lambda *args, **kwargs: Completed(),
    )
    with pytest.raises(GateConfigError, match="bounded source snapshot"):
        validation_gate_module._clean_git_snapshot(ROOT)

def test_slowest_rows_are_bounded_and_sorted() -> None:
    rows = bounded_slowest((("a", 1), ("b", 9), ("c", 4)), limit=2)
    assert rows == (("b", 9), ("c", 4))


class _FakeProcess:
    def __init__(self) -> None:
        self._polls = iter((None, None, 0))
        self.returncode = 0

    def poll(self) -> int | None:
        return next(self._polls)


def test_runner_records_injected_peak_rss() -> None:
    process = _FakeProcess()
    observation = observe_process(
        process,
        rss_reader=iter((100, 12_345, 900)).__next__,
        monotonic_ns=iter((0, 1, 2, 3)).__next__,
        sleep=lambda _seconds: None,
        timeout_seconds=10,
    )
    assert observation.exit_code == 0
    assert observation.peak_rss_bytes == 12_345


class _NeverEndingProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None

    def poll(self) -> None:
        return None


def test_timeout_requires_confirmed_process_tree_termination() -> None:
    terminated = _NeverEndingProcess()
    calls: list[object] = []

    def stop_tree(process: object) -> bool:
        calls.append(process)
        terminated.returncode = -9
        return True

    observation = observe_process(
        terminated,
        rss_reader=lambda: None,
        monotonic_ns=iter((0, 2_000_000_000, 3_000_000_000)).__next__,
        sleep=lambda _seconds: None,
        timeout_seconds=1,
        tree_terminator=stop_tree,
    )
    assert calls == [terminated]
    assert observation.timed_out is True
    assert observation.termination_failed is False

    unconfirmed = _NeverEndingProcess()
    failed = observe_process(
        unconfirmed,
        rss_reader=lambda: None,
        monotonic_ns=iter((0, 2_000_000_000, 3_000_000_000)).__next__,
        sleep=lambda _seconds: None,
        timeout_seconds=1,
        tree_terminator=lambda _process: False,
    )
    assert failed.timed_out is True
    assert failed.termination_failed is True


def test_observer_rechecks_output_after_parent_exit(tmp_path: Path) -> None:
    output = tmp_path / "stdout.bin"
    output.write_bytes(b"ok")

    class ExitsAfterWriting:
        returncode: int | None = None

        def poll(self) -> int:
            output.write_bytes(b"x" * 33)
            self.returncode = 0
            return 0

    observation = observe_process(
        ExitsAfterWriting(),
        rss_reader=lambda: None,
        monotonic_ns=iter((0, 1, 2)).__next__,
        sleep=lambda _seconds: None,
        timeout_seconds=1,
        output_paths=(output,),
        max_output_bytes=32,
        tree_terminator=lambda _process: True,
    )
    assert observation.output_exceeded is True
    assert observation.termination_failed is False


def test_observer_cleans_tree_when_instrumentation_raises() -> None:
    process = _NeverEndingProcess()
    cleaned: list[object] = []

    def broken_rss() -> int:
        raise OSError("sampler failed")

    with pytest.raises(GateConfigError, match="observation"):
        observe_process(
            process,
            rss_reader=broken_rss,
            timeout_seconds=1,
            tree_terminator=lambda value: (cleaned.append(value), True)[1],
        )
    assert cleaned == [process]

def test_validation_run_root_cleanup_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        validation_gate_module.shutil,
        "rmtree",
        lambda _path: None,
    )
    with pytest.raises(GateConfigError, match="cleanup was incomplete"):
        with validation_gate_module._temporary_run_root(tmp_path, "cleanup-test"):
            pass

def test_missing_and_malformed_structured_reports_fail_closed(tmp_path: Path) -> None:
    missing = parse_pytest_report(tmp_path / "missing.json")
    assert missing.disposition == "error"
    assert missing.error_code == "structured_report_missing"

    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text("{}", encoding="utf-8")
    malformed = parse_pytest_report(malformed_path)
    assert malformed.disposition == "error"
    assert malformed.error_code == "structured_report_malformed"



def test_pytest_report_requires_exact_reconstructible_producer_schema(
    tmp_path: Path,
) -> None:
    minimal: dict[str, object] = {
        "disposition": "passed",
        "schema": "cemm-pytest-report-v1",
    }
    minimal["report_ref"] = content_ref("pytest_report", minimal)
    minimal_path = tmp_path / "minimal.json"
    minimal_path.write_bytes(canonical_json_bytes(minimal))
    rejected = parse_pytest_report(minimal_path)
    assert rejected.disposition == "error"
    assert rejected.error_code == "structured_report_malformed"

    valid_path = tmp_path / "valid.json"
    valid = _producer_pytest_report()
    _write_pytest_report(valid_path, valid)
    parsed = parse_pytest_report(valid_path)
    assert parsed.disposition == "passed"
    assert parsed.error_code is None
    assert parsed.report_ref == valid["report_ref"]


def test_pytest_report_rejects_self_inconsistent_facts_counts_and_collection(
    tmp_path: Path,
) -> None:
    wrong_fact = _producer_pytest_report()
    wrong_fact["facts"][0]["reports"][1]["outcome"] = "failed"

    wrong_counts = _producer_pytest_report()
    wrong_counts["counts"]["passed"] = 0

    wrong_collection = _producer_pytest_report()
    wrong_collection["selected_node_ids"] = []

    forged_error_codes = _producer_pytest_report()
    forged_error_codes["error_codes"] = ["collection_mismatch"]

    forged_truncation = _producer_pytest_report()
    forged_truncation["errors_truncated"] = True

    duplicate_collection = _producer_pytest_report()
    duplicate_collection["collected_node_ids"] *= 2

    incomplete_lifecycle = _producer_pytest_report()
    incomplete_lifecycle["facts"][0]["reports"].pop()

    for index, payload in enumerate(
        (
            wrong_fact,
            wrong_counts,
            wrong_collection,
            forged_error_codes,
            forged_truncation,
            duplicate_collection,
            incomplete_lifecycle,
        )
    ):
        path = tmp_path / f"inconsistent-{index}.json"
        _write_pytest_report(path, payload)
        parsed = parse_pytest_report(path)
        assert parsed.disposition == "error"
        assert parsed.error_code == "structured_report_malformed"


def test_pytest_nonexecution_outcomes_are_nonpassing(tmp_path: Path) -> None:
    for classification in ("skip", "xfail", "xpass"):
        payload = _producer_pytest_report(classification=classification)
        path = tmp_path / f"{classification}.json"
        _write_pytest_report(path, payload)
        parsed = parse_pytest_report(path)
        assert parsed.disposition == "failed"
        assert parsed.error_code is None


def test_step_result_rejects_foreign_schema_or_unbound_selector() -> None:
    node_id = "tests/test_example.py::test_example"
    definition = {
        "depends_on": [],
        "exact_nodes": [node_id],
        "inputs": ["tests/test_example.py"],
        "kind": "pytest",
    }
    observation = _producer_pytest_report()
    common = {
        "config_ref": content_ref("gate_config", {"value": 1}),
        "definition": definition,
        "dependency_step_refs": (),
        "disposition": "passed",
        "environment_ref": content_ref("environment", {"value": 1}),
        "error_code": None,
        "exit_code": 0,
        "input_files": (_dummy_evidence("tests/test_example.py"),),
        "kind": "pytest",
        "peak_rss_bytes": None,
        "report": _semantic_pytest_projection(observation),
        "selector": _exact_selector((node_id,)),
        "slowest": (),
        "source_ref": "a" * 40,
        "step_id": "g0_owner_tests",
        "wall_ns": 10,
        "observation_report": observation,
    }

    foreign = dict(observation)
    foreign["schema"] = "foreign-pytest-report-v1"
    with pytest.raises(AdmissionValidationError, match="schema"):
        StepResult.create(
            **{
                **common,
                "report": _semantic_pytest_projection(foreign),
                "observation_report": foreign,
            }
        )

    with pytest.raises(AdmissionValidationError, match="selector"):
        StepResult.create(**{**common, "selector": None})

    wrong_selector = _exact_selector(("tests/test_other.py::test_other",))
    with pytest.raises(AdmissionValidationError, match="selector"):
        StepResult.create(**{**common, "selector": wrong_selector})

def test_step_result_binds_pytest_report_to_observation_projection() -> None:
    node_id = "tests/test_example.py::test_example"
    definition = {
        "depends_on": [],
        "exact_nodes": [node_id],
        "inputs": ["tests/test_example.py"],
        "kind": "pytest",
    }
    common = {
        "config_ref": content_ref("gate_config", {"value": 1}),
        "definition": definition,
        "dependency_step_refs": (),
        "disposition": "passed",
        "environment_ref": content_ref("environment", {"value": 1}),
        "error_code": None,
        "exit_code": 0,
        "input_files": (_dummy_evidence("tests/test_example.py"),),
        "kind": "pytest",
        "peak_rss_bytes": 10,
        "selector": _exact_selector((node_id,)),
        "slowest": (),
        "source_ref": "a" * 40,
        "step_id": "g0_owner_tests",
        "wall_ns": 10,
    }
    first_observation = _producer_pytest_report(duration_ns=10)
    second_observation = _producer_pytest_report(duration_ns=50)
    first = StepResult.create(
        **common,
        report=_semantic_pytest_projection(first_observation),
        observation_report=first_observation,
    )
    second = StepResult.create(
        **{**common, "peak_rss_bytes": 20, "wall_ns": 50},
        report=_semantic_pytest_projection(second_observation),
        observation_report=second_observation,
    )
    assert first.step_ref == second.step_ref
    assert first.report_ref == second.report_ref
    assert first.observation_report_ref != second.observation_report_ref


def test_step_result_rejects_unbound_or_downgraded_observations() -> None:
    node_id = "tests/test_example.py::test_example"
    definition = {
        "depends_on": [],
        "exact_nodes": [node_id],
        "inputs": ["tests/test_example.py"],
        "kind": "pytest",
    }
    common = {
        "config_ref": content_ref("gate_config", {"value": 1}),
        "definition": definition,
        "dependency_step_refs": (),
        "environment_ref": content_ref("environment", {"value": 1}),
        "input_files": (_dummy_evidence("tests/test_example.py"),),
        "kind": "pytest",
        "peak_rss_bytes": None,
        "selector": _exact_selector((node_id,)),
        "slowest": (),
        "source_ref": "a" * 40,
        "step_id": "g0_owner_tests",
        "wall_ns": 10,
    }
    passed_observation = _producer_pytest_report()
    with pytest.raises(AdmissionValidationError, match="projection"):
        StepResult.create(
            **common,
            disposition="passed",
            error_code=None,
            exit_code=0,
            report={"schema": "forged-semantic-report-v1"},
            observation_report=passed_observation,
        )

    failed_observation = _producer_pytest_report(classification="failure")
    with pytest.raises(AdmissionValidationError, match="observation|disposition"):
        StepResult.create(
            **common,
            disposition="passed",
            error_code=None,
            exit_code=0,
            report=_semantic_pytest_projection(failed_observation),
            observation_report=failed_observation,
        )

    compile_definition = {
        "depends_on": [],
        "inputs": ["scripts/"],
        "kind": "compile",
        "roots": ["scripts/"],
    }
    with pytest.raises(AdmissionValidationError, match="observation|semantic"):
        StepResult.create(
            **{
                **common,
                "definition": compile_definition,
                "input_files": (_dummy_evidence("scripts/fixture.py"),),
                "selector": None,
                "kind": "compile",
                "step_id": "source_compile",
            },
            disposition="passed",
            error_code=None,
            exit_code=0,
            report={"schema": "semantic-v1"},
            observation_report={"schema": "different-v1"},
        )

def test_pytest_report_binds_selector_and_requires_canonical_bytes(
    tmp_path: Path,
) -> None:
    payload = _producer_pytest_report()
    expected_selector: dict[str, object] = {
        "exact_node_ids": ["tests/test_expected.py::test_expected"],
        "mode": "exact",
        "schema": "cemm-pytest-selector-v1",
    }
    expected_selector["selector_ref"] = content_ref(
        "pytest_selector", expected_selector
    )
    payload["selector_ref"] = expected_selector["selector_ref"]
    canonical_path = tmp_path / "selector-mismatch.json"
    _write_pytest_report(canonical_path, payload)
    mismatch = parse_pytest_report(
        canonical_path,
        expected_selector=expected_selector,
    )
    assert mismatch.disposition == "error"
    assert mismatch.error_code == "structured_report_selector_mismatch"

    noncanonical_path = tmp_path / "noncanonical.json"
    noncanonical_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    noncanonical = parse_pytest_report(noncanonical_path)
    assert noncanonical.disposition == "error"
    assert noncanonical.error_code == "structured_report_malformed"


def test_isolated_environment_disables_external_pytest_plugins(tmp_path: Path) -> None:
    env, _pytest_args = isolated_test_environment(
        tmp_path,
        inherited={
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
            "PYTEST_PLUGINS": "foreign.plugin",
        },
    )
    assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert "PYTEST_PLUGINS" not in env

def test_pytest_report_reconstructs_duration_aggregation_error(
    tmp_path: Path,
) -> None:
    payload = _producer_pytest_report()
    node_id = payload["selected_node_ids"][0]
    payload["facts"][0]["classification"] = "error"
    payload["facts"][0]["duration_ns"] = 0
    payload["counts"]["error"] = 1
    payload["counts"]["passed"] = 0
    payload["disposition"] = "error"
    payload["error_codes"] = ["duration_aggregation_error"]
    payload["errors"] = [
        {
            "code": "duration_aggregation_error",
            "message": "duration was not representable",
            "node_id": node_id,
        }
    ]
    payload["slowest"] = [{"duration_ns": 0, "node_id": node_id}]
    path = tmp_path / "duration-error.json"
    _write_pytest_report(path, payload)

    parsed = parse_pytest_report(path)
    assert parsed.disposition == "error"
    assert parsed.error_code is None
    assert parsed.payload is not None


def test_step_result_requires_exact_child_exit_for_observed_pytest_error() -> None:
    observation = _producer_pytest_report(classification="error")
    node_id = observation["selected_node_ids"][0]
    common = {
        "config_ref": content_ref("gate_config", {"value": 1}),
        "definition": {
            "depends_on": [],
            "exact_nodes": [node_id],
            "inputs": ["tests/test_example.py"],
            "kind": "pytest",
        },
        "dependency_step_refs": (),
        "disposition": "error",
        "environment_ref": content_ref("environment", {"value": 1}),
        "error_code": "pytest_test_error",
        "input_files": (_dummy_evidence("tests/test_example.py"),),
        "kind": "pytest",
        "peak_rss_bytes": None,
        "report": _semantic_pytest_projection(observation),
        "selector": _exact_selector((node_id,)),
        "slowest": (),
        "source_ref": "a" * 40,
        "step_id": "g0_owner_tests",
        "wall_ns": 10,
        "observation_report": observation,
    }
    with pytest.raises(AdmissionValidationError, match="exit"):
        StepResult.create(**common, exit_code=3)

    accepted = StepResult.create(**common, exit_code=2)
    assert accepted.disposition == "error"
def test_receipt_identity_and_exclusive_write(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path)
    target = tmp_path / "receipt.json"
    write_receipt_exclusive(target, receipt)
    assert target.read_bytes() == canonical_json_bytes(receipt.to_dict())
    with pytest.raises(FileExistsError):
        write_receipt_exclusive(target, receipt)

    mutated = receipt.to_dict()
    mutated["started_at_utc"] = "2026-07-31T00:00:01Z"
    with pytest.raises(AdmissionValidationError, match="run_ref"):
        GateReceipt.from_dict(mutated)


def test_verified_loader_selects_exact_run_and_authenticates_evidence(
    tmp_path: Path,
) -> None:
    receipt = _receipt(tmp_path)
    run_dir = tmp_path / "artifacts" / "validation" / "runs"
    run_dir.mkdir(parents=True)
    target = run_dir / f"{receipt.run_ref.removeprefix('run:')}.json"
    write_receipt_exclusive(target, receipt)

    loaded, paths = load_verified_admission_receipt(
        tmp_path, phase="G0", expected_status="passed", run_ref=receipt.run_ref
    )
    assert loaded == receipt
    assert paths == tuple(
        sorted(
            (
                "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
                "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
                target.relative_to(tmp_path).as_posix(),
            )
        )
    )

    evidence = tmp_path / "artifacts" / "validation" / "BASELINE_REPLAY_FINDINGS.json"
    original_evidence = evidence.read_bytes()
    invalid = json.loads(original_evidence)
    invalid["structural_findings"].pop("bootstrap_programs_author_gold")
    invalid_identity = dict(invalid)
    invalid_identity.pop("findings_ref")
    invalid["findings_ref"] = content_ref(
        "baseline_replay_findings", invalid_identity
    )
    evidence.write_bytes(canonical_json_bytes(invalid))
    invalid_receipt = GateReceipt.create(
        config=receipt.config,
        environment=receipt.environment,
        evidence_files=tuple(
            EvidenceFile.from_path(tmp_path, item.path)
            for item in receipt.evidence_files
        ),
        fresh=True,
        phase="G0",
        pre_admission_status_head_ref=receipt.pre_admission_status_head_ref,
        run_nonce="semantically-invalid-evidence",
        source_ref=receipt.source_ref,
        started_at_utc=receipt.started_at_utc,
        step_results=receipt.step_results,
        tier="admission",
    )
    invalid_target = run_dir / (
        invalid_receipt.run_ref.removeprefix("run:") + ".json"
    )
    write_receipt_exclusive(invalid_target, invalid_receipt)
    with pytest.raises(AdmissionValidationError, match="intrinsic evidence"):
        load_verified_admission_receipt(
            tmp_path,
            phase="G0",
            expected_status="passed",
            run_ref=invalid_receipt.run_ref,
        )

    evidence.write_bytes(original_evidence)
    evidence.write_text('{"tampered":true}', encoding="utf-8")
    with pytest.raises(AdmissionValidationError, match="evidence hash mismatch"):
        load_verified_admission_receipt(
            tmp_path, phase="G0", expected_status="passed", run_ref=receipt.run_ref
        )


def test_verified_loader_rejects_ambiguous_or_misnamed_runs(tmp_path: Path) -> None:
    first = _receipt(tmp_path)
    run_dir = tmp_path / "artifacts" / "validation" / "runs"
    run_dir.mkdir(parents=True)
    first_path = run_dir / f"{first.run_ref.removeprefix('run:')}.json"
    write_receipt_exclusive(first_path, first)

    second_payload = first.to_dict()
    second_payload.pop("run_ref")
    second_payload["run_nonce"] = "another-nonce"
    second = GateReceipt.from_unidentified_dict(second_payload)
    second_path = run_dir / f"{second.run_ref.removeprefix('run:')}.json"
    write_receipt_exclusive(second_path, second)
    with pytest.raises(AdmissionValidationError, match="ambiguous"):
        load_verified_admission_receipt(
            tmp_path, phase="G0", expected_status="passed", run_ref=None
        )

    first_path.rename(run_dir / ("f" * 24 + ".json"))
    with pytest.raises(AdmissionValidationError, match="filename|missing"):
        load_verified_admission_receipt(
            tmp_path, phase="G0", expected_status="passed", run_ref=first.run_ref
        )


def test_g0_receipt_requires_exact_external_evidence_set(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path)
    common = {
        "config": receipt.config,
        "environment": receipt.environment,
        "fresh": True,
        "phase": "G0",
        "pre_admission_status_head_ref": receipt.pre_admission_status_head_ref,
        "run_nonce": "evidence-policy-test",
        "source_ref": receipt.source_ref,
        "started_at_utc": receipt.started_at_utc,
        "step_results": receipt.step_results,
        "tier": "admission",
    }
    with pytest.raises(AdmissionValidationError, match="exact phase policy"):
        GateReceipt.create(
            **common,
            evidence_files=receipt.evidence_files[:1],
        )

    extra_path = tmp_path / "artifacts" / "validation" / "EXTRA.json"
    extra_path.write_bytes(canonical_json_bytes({"schema": "extra-v1"}))
    extra = EvidenceFile.from_path(
        tmp_path, "artifacts/validation/EXTRA.json"
    )
    with pytest.raises(AdmissionValidationError, match="exact phase policy"):
        GateReceipt.create(
            **common,
            evidence_files=tuple(sorted((*receipt.evidence_files, extra))),
        )

    baseline = json.loads(
        (ROOT / "artifacts/validation/BASELINE_REPLAY_FINDINGS.json").read_text(
            encoding="utf-8"
        )
    )
    validation_gate_module._validate_g0_baseline_findings(
        baseline,
        baseline_source_ref="58345240e67bf003e6ac7d5c68752e2e5eee4a7d",
    )
    noncanonical = json.dumps(baseline, indent=2).encode("utf-8")
    with pytest.raises(GateConfigError, match="not canonical JSON"):
        validation_gate_module._load_canonical_g0_evidence(
            noncanonical, path=Path("BASELINE_REPLAY_FINDINGS.json")
        )
    tampered = json.loads(json.dumps(baseline))
    tampered["quarantine"]["program_abi_1_descendants_quarantined"] = False
    identity = dict(tampered)
    identity.pop("findings_ref")
    tampered["findings_ref"] = content_ref("baseline_replay_findings", identity)
    with pytest.raises(GateConfigError, match="quarantine is incomplete"):
        validation_gate_module._validate_g0_baseline_findings(
            tampered,
            baseline_source_ref="58345240e67bf003e6ac7d5c68752e2e5eee4a7d",
        )

    inventory_path = ROOT / "governance" / "test_inventory.json"
    inventory_sha256 = inventory_core_module.verify_document_authority_pin(
        ROOT, inventory_path
    )
    inventory = inventory_core_module.load_and_verify(
        ROOT,
        inventory_path,
        phase="G0",
        enforce_reviewed_counts=True,
        expected_sha256=inventory_sha256,
    )
    graph, _ = validation_gate_module._load_gate_graph_with_source(
        ROOT / "configs" / "validation_gates.json"
    )
    selector = validation_gate_module.validate_inventory_contract(
        graph, inventory, phase="G0"
    )
    authority_raw = (ROOT / "docs" / "DOCUMENT_AUTHORITY.json").read_bytes()
    expected_receipt = validation_gate_module._expected_g0_inventory_receipt(
        authority_sha256=hashlib.sha256(authority_raw).hexdigest(),
        inventory_sha256=inventory_sha256,
        inventory=inventory,
        selector=selector,
    )
    checked_in_receipt = validation_gate_module._load_canonical_g0_evidence(
        (ROOT / "artifacts/validation/TEST_INVENTORY_RECEIPT.json").read_bytes(),
        path=Path("artifacts/validation/TEST_INVENTORY_RECEIPT.json"),
    )
    assert checked_in_receipt == expected_receipt


def test_current_source_config_rejects_alternate_receipt_plan(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path)
    with pytest.raises(AdmissionValidationError, match="config_ref"):
        verify_current_source_config(ROOT, receipt)


def test_current_source_config_rejects_incomplete_input_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _receipt(tmp_path)
    config_path = tmp_path / "configs" / "validation_gates.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_bytes(canonical_json_bytes(_graph_payload()))
    for relative in (
        "docs/DOCUMENT_AUTHORITY.json",
        "governance/receipt_invalidations.jsonl",
        "governance/replay_status.jsonl",
        "governance/test_inventory.json",
        "pyproject.toml",
        "tests/test_g0_integration.py",
        "tests/test_validation_gate.py",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    for relative in ("scripts", "src"):
        (tmp_path / relative).mkdir(exist_ok=True)
    (tmp_path / "pyproject.toml").write_text("changed", encoding="utf-8")

    def blob_id(path: Path) -> str:
        raw = path.read_bytes()
        digest = validation_gate_module.hashlib.sha1(usedforsecurity=False)
        digest.update(f"blob {len(raw)}\0".encode("ascii"))
        digest.update(raw)
        return digest.hexdigest()

    monkeypatch.setattr(
        validation_gate_module,
        "_tracked_source_blobs",
        lambda _root, _source_ref: {
            path.relative_to(tmp_path).as_posix(): blob_id(path)
            for path in tmp_path.rglob("*")
            if path.is_file()
        },
    )
    inventory = SimpleNamespace(parsed_module_count=1)
    inventory_core = SimpleNamespace(
        verify_document_authority_pin=lambda _root, _path, **_kwargs: "a" * 64,
        load_and_verify=lambda *_args, **_kwargs: inventory,
    )
    monkeypatch.setattr(
        validation_gate_module,
        "_load_exact_module",
        lambda _path, purpose, **_kwargs: (
            inventory_core if purpose == "test_inventory" else object()
        ),
    )
    node = "tests/test_example.py::test_example"
    monkeypatch.setattr(
        validation_gate_module,
        "validate_inventory_contract",
        lambda _graph, _inventory, phase: validation_gate_module.InventorySelector(
            phase=phase,
            inventory_ref=content_ref("test_inventory", {"value": 1}),
            literal_metadata_ref=content_ref("literal_test_metadata", {"value": 1}),
            active_node_set_ref=content_ref("active_test_nodes", [node]),
            active_node_ids=(node,),
            collectable_node_set_ref=content_ref("collectable_test_nodes", [node]),
            collectable_node_ids=(node,),
        ),
    )

    with pytest.raises(AdmissionValidationError, match="input manifest"):
        verify_current_source_config(tmp_path, receipt)

def test_step_identity_excludes_observational_timing() -> None:
    definition = {
        "depends_on": [],
        "inputs": ["scripts/"],
        "kind": "compile",
        "roots": ["scripts/"],
    }
    common = {
        "config_ref": content_ref("gate_config", {"value": 1}),
        "definition": definition,
        "dependency_step_refs": (),
        "disposition": "passed",
        "environment_ref": content_ref("environment", {"value": 1}),
        "error_code": None,
        "exit_code": 0,
        "input_files": (_dummy_evidence("scripts/fixture.py"),),
        "kind": "compile",
        "peak_rss_bytes": 10,
        "report": {
            "compiled_file_count": 1,
            "compiled_set_ref": content_ref(
                "compiled_sources",
                [{"path": "scripts/fixture.py", "sha256": "a" * 64}],
            ),
            "schema": "cemm-compile-step-report-v1",
        },
        "selector": None,
        "slowest": (),
        "source_ref": "a" * 40,
        "step_id": "source_compile",
        "wall_ns": 10,
    }
    first = StepResult.create(**common, observation_report=common["report"])
    second = StepResult.create(
        **{**common, "peak_rss_bytes": 20, "wall_ns": 50},
        observation_report=common["report"],
    )
    assert first.step_ref == second.step_ref
    assert first.report_ref == second.report_ref
    assert first.observation_report_ref == second.observation_report_ref


def test_cli_rejects_legacy_profile() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validate_mvp.py", "--profile", "development"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "unrecognized arguments" in completed.stderr


def test_canonical_json_rejects_nonfinite_values() -> None:
    with pytest.raises(GateConfigError, match="canonical JSON"):
        canonical_json_bytes({"value": float("inf")})


def test_governance_step_uses_one_manifest_snapshot_for_all_governed_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _materialize_fixture_inputs(tmp_path)
    authority_path = tmp_path / "docs" / "DOCUMENT_AUTHORITY.json"
    authority_path.write_bytes(canonical_json_bytes({"scope": "hybrid_mvp/"}))
    subject_path = tmp_path / "artifacts" / "validation" / "historical.json"
    subject_path.parent.mkdir(parents=True, exist_ok=True)
    subject_path.write_bytes(b"authenticated historical bytes\n")
    status_record = {"record_ref": "governance_record:" + "a" * 24}
    invalidation_record = {
        "record_ref": "governance_record:" + "b" * 24,
        "subject": "artifacts/validation/historical.json",
    }
    observed: list[tuple[str, bytes]] = []

    def read_hash_chain(path: Path, *, source_reader) -> tuple[dict[str, object], ...]:
        raw = source_reader(path)
        observed.append((path.relative_to(tmp_path).as_posix(), raw))
        if path.name == "replay_status.jsonl":
            authenticated_authority = source_reader(authority_path)
            observed.append(("docs/DOCUMENT_AUTHORITY.json", authenticated_authority))
            authority_path.write_bytes(canonical_json_bytes({"scope": "mutated/"}))
            return (status_record,)
        return (invalidation_record,)

    def verify_file_invalidation(root: Path, record, *, source_reader) -> None:
        target = root / str(record["subject"])
        authenticated = source_reader(target)
        observed.append((str(record["subject"]), authenticated))
        target.write_bytes(b"mutated live bytes\n")
        assert source_reader(target) == authenticated

    governance = SimpleNamespace(
        effective_replay_status=lambda _records: {"G0": "pending"},
        read_hash_chain=read_hash_chain,
        verify_file_invalidation=verify_file_invalidation,
    )

    def verify_document_authority_pin(_root, inventory_path, *, source_reader):
        assert source_reader(authority_path) == canonical_json_bytes(
            {"scope": "hybrid_mvp/"}
        )
        source_reader(inventory_path)
        return "a" * 64

    def load_and_verify(
        _root,
        inventory_path,
        *,
        phase,
        enforce_reviewed_counts,
        expected_sha256,
        source_reader,
    ):
        assert phase == "G0"
        assert enforce_reviewed_counts is True
        assert expected_sha256 == "a" * 64
        source_reader(inventory_path)
        source_reader(tmp_path / "pyproject.toml")
        return SimpleNamespace(parsed_module_count=1)

    inventory_core = SimpleNamespace(
        load_and_verify=load_and_verify,
        verify_document_authority_pin=verify_document_authority_pin,
    )
    monkeypatch.setattr(
        validation_gate_module,
        "_load_exact_module",
        lambda _path, purpose, **_kwargs: (
            governance if purpose == "governance" else inventory_core
        ),
    )
    selector = validation_gate_module.InventorySelector(
        phase="G0",
        inventory_ref="test_inventory:" + "1" * 24,
        literal_metadata_ref="literal_test_metadata:" + "2" * 24,
        active_node_set_ref="active_test_nodes:" + "3" * 24,
        active_node_ids=("tests/test_validation_gate.py::test_node",),
        collectable_node_set_ref="collectable_test_nodes:" + "4" * 24,
        collectable_node_ids=("tests/test_validation_gate.py::test_node",),
    )
    monkeypatch.setattr(
        validation_gate_module,
        "validate_inventory_contract",
        lambda _graph, _inventory, *, phase: selector,
    )
    for relative in (
        "artifacts/evaluation/CEMM_EVALUATION.json",
        "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
        "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())

    def validate_evidence(**material) -> None:
        assert material["authority_raw"] == canonical_json_bytes(
            {"scope": "hybrid_mvp/"}
        )
        assert material["baseline_raw"] == (
            ROOT / "artifacts/validation/BASELINE_REPLAY_FINDINGS.json"
        ).read_bytes()
        assert material["evaluation_raw"] == (
            ROOT / "artifacts/evaluation/CEMM_EVALUATION.json"
        ).read_bytes()
        assert material["inventory_receipt_raw"] == (
            ROOT / "artifacts/validation/TEST_INVENTORY_RECEIPT.json"
        ).read_bytes()

    monkeypatch.setattr(
        validation_gate_module,
        "_validate_g0_evidence_material",
        validate_evidence,
    )
    context = validation_gate_module._RunContext(
        tmp_path,
        GateGraph.from_dict(_graph_payload()),
        phase="G0",
        tier="admission",
        owner=None,
        source_ref="a" * 40,
        run_root=tmp_path / "run",
    )

    handled = context.run_governance()

    assert handled.disposition == "passed"
    assert handled.report["invalidation_record_count"] == 1
    assert ("docs/DOCUMENT_AUTHORITY.json", canonical_json_bytes(
        {"scope": "hybrid_mvp/"}
    )) in observed
    assert authority_path.read_bytes() == canonical_json_bytes({"scope": "mutated/"})
    assert subject_path.read_bytes() == b"mutated live bytes\n"


def test_governance_step_validates_effective_status_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[dict[str, object], ...]] = []
    records = ({"record_ref": "governance_record:" + "a" * 24},)

    def effective(value):
        calls.append(value)
        raise ValueError("duplicate admission consumption")

    governance = SimpleNamespace(
        effective_replay_status=effective,
        read_hash_chain=lambda _path, **_kwargs: records,
        verify_file_invalidation=lambda _root, _record, **_kwargs: None,
    )
    monkeypatch.setattr(
        validation_gate_module,
        "_load_exact_module",
        lambda _path, purpose, **_kwargs: (
            governance if purpose == "governance" else object()
        ),
    )
    context = validation_gate_module._RunContext(
        tmp_path,
        GateGraph.from_dict(_graph_payload()),
        phase="G0",
        tier="admission",
        owner=None,
        source_ref="a" * 40,
        run_root=tmp_path / "run",
    )
    with pytest.raises(GateConfigError, match="duplicate admission consumption"):
        context.run_governance()
    assert calls == [records]


def test_validation_temp_parent_rejects_link_or_reparse_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        validation_gate_module,
        "_path_is_link_or_reparse",
        lambda path: path.name == ".test-tmp",
    )
    with pytest.raises(GateConfigError, match="unsafe validation temp parent"):
        with validation_gate_module._temporary_run_root(tmp_path, "unsafe-parent"):
            pass


def test_receipt_writer_enforces_loader_size_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _receipt(tmp_path)
    target = tmp_path / "oversized-receipt.json"
    monkeypatch.setattr(validation_gate_module, "_MAX_RECEIPT_BYTES", 8)
    with pytest.raises(AdmissionValidationError, match="size bound"):
        write_receipt_exclusive(target, receipt)
    assert not target.exists()


def test_input_manifest_rejects_file_absent_from_source_commit(tmp_path: Path) -> None:
    path = tmp_path / "tests" / "ignored" / "rogue.py"
    path.parent.mkdir(parents=True)
    path.write_text("raise RuntimeError('rogue')", encoding="utf-8")
    manifest = validation_gate_module._InputManifestCache(
        tmp_path,
        committed_blobs={},
    )
    with pytest.raises(GateConfigError, match="committed source"):
        manifest.digest(path)


def test_current_source_verifier_rejects_forged_admission_subset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _receipt(tmp_path)
    config_path = tmp_path / "configs" / "validation_gates.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_bytes(canonical_json_bytes(_graph_payload()))
    expected_nodes = (
        "tests/test_example.py::test_example",
        "tests/test_example.py::test_second",
    )
    expected = validation_gate_module.InventorySelector(
        phase="G0",
        inventory_ref=content_ref("test_inventory", {"value": 1}),
        literal_metadata_ref=content_ref("literal_test_metadata", {"value": 1}),
        active_node_set_ref=content_ref("active_test_nodes", list(expected_nodes)),
        active_node_ids=expected_nodes,
        collectable_node_set_ref=content_ref("collectable_test_nodes", list(expected_nodes)),
        collectable_node_ids=expected_nodes,
    )
    inventory_core = SimpleNamespace(
        verify_document_authority_pin=lambda *_args, **_kwargs: "a" * 64,
        load_and_verify=lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        validation_gate_module,
        "_load_exact_module",
        lambda _path, purpose, **_kwargs: (
            inventory_core if purpose == "test_inventory" else object()
        ),
    )
    monkeypatch.setattr(
        validation_gate_module,
        "validate_inventory_contract",
        lambda _graph, _inventory, phase: expected,
    )

    results_by_step = {result.step_id: result for result in receipt.step_results}

    class AuthenticatedFixtureManifest:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def adopt(self, _path: Path, raw: bytes) -> str:
            return validation_gate_module.hashlib.sha256(raw).hexdigest()

        def evidence_file(self, relative: str) -> EvidenceFile:
            for evidence in receipt.evidence_files:
                if evidence.path == relative:
                    return evidence
            return EvidenceFile.from_path(tmp_path, relative)

        def input_files(self, step) -> tuple[EvidenceFile, ...]:
            return results_by_step[step.step_id].input_files

        def read(self, _path: Path) -> tuple[bytes, str]:
            raw = b"fixture"
            return raw, validation_gate_module.hashlib.sha256(raw).hexdigest()

    monkeypatch.setattr(
        validation_gate_module,
        "_InputManifestCache",
        AuthenticatedFixtureManifest,
    )
    monkeypatch.setattr(
        validation_gate_module,
        "_tracked_source_blobs",
        lambda _root, _source_ref: {},
    )
    monkeypatch.setattr(
        validation_gate_module,
        "_authenticate_complete_source_snapshot",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(AdmissionValidationError, match="inventory selector"):
        verify_current_source_config(tmp_path, receipt)


def test_receipt_verification_caches_fixed_evidence_per_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _receipt(tmp_path)
    run_dir = tmp_path / "artifacts" / "validation" / "runs"
    run_dir.mkdir(parents=True)
    target = run_dir / f"{receipt.run_ref.removeprefix('run:')}.json"
    write_receipt_exclusive(target, receipt)
    original = validation_gate_module._sha256_file_bounded
    calls: list[Path] = []

    def counted(path: Path, *, maximum: int = 64 * 1024 * 1024) -> str:
        calls.append(path)
        return original(path, maximum=maximum)

    monkeypatch.setattr(validation_gate_module, "_sha256_file_bounded", counted)
    validation_gate_module.reset_admission_verification_cache()
    for _ in range(2):
        load_verified_admission_receipt(
            tmp_path,
            phase="G0",
            expected_status="passed",
            run_ref=receipt.run_ref,
        )
    assert len(calls) == 1
    validation_gate_module.reset_admission_verification_cache()
    load_verified_admission_receipt(
        tmp_path,
        phase="G0",
        expected_status="passed",
        run_ref=receipt.run_ref,
    )
    assert len(calls) == 2

def test_bounded_process_capture_preserves_fast_output() -> None:
    payload = b"x" * 65_536
    result = capture_bounded_process(
        [
            sys.executable,
            "-c",
            "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())",
        ],
        input_bytes=payload,
        max_stdout_bytes=len(payload),
        max_stderr_bytes=32,
        max_combined_output_bytes=len(payload),
        timeout_seconds=5,
    )
    assert result.stdout == payload
    assert result.stderr == b""
    assert result.termination_confirmed is True


def test_bounded_process_capture_rejects_overflow_and_timeout() -> None:
    with pytest.raises(ProcessControlError) as overflow:
        capture_bounded_process(
            [sys.executable, "-c", "print('x'*1000)"],
            max_stdout_bytes=16,
            max_stderr_bytes=16,
            timeout_seconds=5,
        )
    assert overflow.value.reason is ProcessErrorReason.OUTPUT_LIMIT
    assert len(overflow.value.stdout) == 16
    assert overflow.value.termination_confirmed is True

    with pytest.raises(ProcessControlError) as combined:
        capture_bounded_process(
            [
                sys.executable,
                "-c",
                (
                    "import sys;"
                    "sys.stdout.buffer.write(b'o'*12);sys.stdout.flush();"
                    "sys.stderr.buffer.write(b'e'*12);sys.stderr.flush()"
                ),
            ],
            max_stdout_bytes=16,
            max_stderr_bytes=16,
            max_combined_output_bytes=20,
            timeout_seconds=5,
        )
    assert combined.value.reason is ProcessErrorReason.OUTPUT_LIMIT
    assert len(combined.value.stdout) + len(combined.value.stderr) == 20

    with pytest.raises(ProcessControlError) as timed_out:
        capture_bounded_process(
            [sys.executable, "-c", "import time;time.sleep(10)"],
            max_stdout_bytes=16,
            max_stderr_bytes=16,
            timeout_seconds=0.05,
        )
    assert timed_out.value.reason is ProcessErrorReason.TIMEOUT
    assert timed_out.value.termination_confirmed is True


def test_bounded_process_capture_kills_descendants_after_parent_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if process_control_module.os.name == "nt":
        flags = process_control_module.process_tree_popen_kwargs()["creationflags"]
        assert isinstance(flags, int)
        assert flags & 0x00000004  # CREATE_SUSPENDED: assign Job before execution.
    events: list[str] = []
    original_terminate = process_control_module.terminate_process_tree
    original_join = process_control_module.threading.Thread.join

    def recorded_terminate(*args, **kwargs) -> bool:
        events.append("terminate")
        return original_terminate(*args, **kwargs)

    def recorded_join(thread, *args, **kwargs) -> None:
        events.append("join")
        original_join(thread, *args, **kwargs)

    child = "import time;time.sleep(10)"
    parent = (
        "import subprocess,sys;"
        f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
        "print('parent-finished')"
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            process_control_module,
            "terminate_process_tree",
            recorded_terminate,
        )
        scoped.setattr(
            process_control_module.threading.Thread,
            "join",
            recorded_join,
        )
        result = capture_bounded_process(
            [sys.executable, "-c", parent],
            max_stdout_bytes=128,
            max_stderr_bytes=128,
            timeout_seconds=2,
        )
    assert result.stdout.strip() == b"parent-finished"
    assert result.termination_confirmed is True
    assert events == ["terminate", "join", "join"]


def test_bounded_process_capture_cleans_up_when_thread_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_start(_thread) -> None:
        raise RuntimeError("thread start failed")

    monkeypatch.setattr(process_control_module.threading.Thread, "start", fail_start)
    with pytest.raises(ProcessControlError) as failure:
        capture_bounded_process(
            [sys.executable, "-c", "import time;time.sleep(10)"],
            max_stdout_bytes=16,
            max_stderr_bytes=16,
            timeout_seconds=2,
        )
    assert failure.value.reason is ProcessErrorReason.PIPE_READ_FAILED
    assert failure.value.termination_confirmed is True


def test_committed_tree_parser_rejects_ambiguous_or_unsafe_records(
    tmp_path: Path,
) -> None:
    oid = b"a" * 40
    valid = b"100644 blob " + oid + b"\tpath/file.py\0"
    assert validation_gate_module._parse_tracked_source_blobs(valid) == {
        "path/file.py": "a" * 40
    }
    malformed = (
        valid[:-1],
        b"\xef\xbb\xbf" + valid,
        b"120000 blob " + oid + b"\tpath/link.py\0",
        (
            b"100644 blob " + oid + b"\tPath/file.py\0"
            b"100644 blob " + oid + b"\tpath/file.py\0"
        ),
    )
    for raw in malformed:
        with pytest.raises(GateConfigError, match="source tree"):
            validation_gate_module._parse_tracked_source_blobs(raw)

    source = tmp_path / ".gitattributes"
    original = b"*.py text eol=lf\n"
    source.write_bytes(original)
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(original)}\0".encode("ascii"))
    digest.update(original)
    committed = {".gitattributes": digest.hexdigest()}
    manifest = validation_gate_module._InputManifestCache(
        tmp_path, committed_blobs=committed
    )
    validation_gate_module._authenticate_complete_source_snapshot(
        tmp_path, manifest, committed
    )

    # Git index flags can hide this mutation from status; full blob auth cannot.
    source.write_bytes(b"*.py -text\n")
    with pytest.raises(GateConfigError, match="exact committed source"):
        validation_gate_module._authenticate_complete_source_snapshot(
            tmp_path,
            validation_gate_module._InputManifestCache(
                tmp_path, committed_blobs=committed
            ),
            committed,
        )

    source.write_bytes(original)
    (tmp_path / "ignored-but-executable.py").write_text(
        "raise RuntimeError('must not be ignored')\n", encoding="utf-8"
    )
    with pytest.raises(GateConfigError, match="path set"):
        validation_gate_module._authenticate_complete_source_snapshot(
            tmp_path,
            validation_gate_module._InputManifestCache(
                tmp_path, committed_blobs=committed
            ),
            committed,
        )


def test_r4_gate_plans_are_exact_bounded_and_single_process() -> None:
    graph = validation_gate_module.load_gate_graph(
        ROOT / "configs" / "validation_gates.json"
    )
    inventory_path = ROOT / "governance" / "test_inventory.json"
    inventory = inventory_core_module.load_and_verify(
        ROOT,
        inventory_path,
        phase="R4",
        enforce_reviewed_counts=True,
        expected_sha256=inventory_core_module.verify_document_authority_pin(
            ROOT, inventory_path
        ),
    )
    expected_steps = {
        "artifact-integrity": "r4_artifact_integrity_owner_tests",
        "expected-contract": "r4_contract_review_owner_tests",
        "governance": "r4_governance_owner_tests",
        "mutation-partition": "r4_data_owner_tests",
        "structural-sufficiency": "r4_structural_sufficiency_owner_tests",
        "surface-expansion": "r4_surface_expansion_owner_tests",
    }
    expected_counts = {
        "artifact-integrity": 16,
        "expected-contract": 33,
        "governance": 2,
        "mutation-partition": 92,
        "structural-sufficiency": 2,
        "surface-expansion": 2,
    }

    assert set(graph.phases["R4"].owners) == set(expected_steps)
    assert set(inventory.owner_node_ids) == set(expected_steps)
    owner_nodes: set[str] = set()
    for owner, step_id in expected_steps.items():
        resolved = graph.resolve_phase("R4", "owner", owner)
        assert resolved == ("governance", "source_compile", step_id)
        assert "r4_artifact_integrity" not in resolved
        assert graph.pytest_process_count("R4", "owner", owner) == 1
        selected = graph.resolve_pytest_nodes("R4", "owner", owner)
        assert selected == inventory.owner_node_ids[owner]
        assert len(selected) == expected_counts[owner]
        owner_nodes.update(selected)

    phase_resolved = graph.resolve_phase("R4", "phase")
    assert phase_resolved == ("governance", "source_compile", "r4_phase_tests")
    assert graph.pytest_process_count("R4", "phase") == 1
    phase_nodes = graph.resolve_pytest_nodes("R4", "phase")
    assert phase_nodes == inventory.phase_node_ids
    assert len(phase_nodes) == 33
    assert owner_nodes.isdisjoint(phase_nodes)

    admission = graph.resolve_phase("R4", "admission")
    assert admission == (
        "governance",
        "source_compile",
        "authority_link",
        "pytest_active",
        "sqlite_activation",
        "r4_artifact_integrity",
    )
    assert graph.pytest_process_count("R4", "admission") == 1
    assert admission.count("r4_artifact_integrity") == 1

    selected_steps = set(admission) | set(phase_resolved)
    for owner in expected_steps:
        selected_steps.update(graph.resolve_phase("R4", "owner", owner))
    selected_steps.update(graph.resolve_phase("R5", "phase"))
    for owner in graph.phases["R5"].owners:
        selected_steps.update(graph.resolve_phase("R5", "owner", owner))
    forbidden_inputs = {
        "artifacts/r4/training_allowlist.json",
        "configs/partitions.json",
        "data/partitions/",
        "scripts/partition_episodes.py",
        "src/cemm_authoritative_hybrid/partitions.py",
    }
    for step_id in selected_steps:
        inputs = tuple(graph.steps[step_id].material.get("inputs", ()))
        assert not forbidden_inputs.intersection(inputs)
        assert not any(path.startswith("artifacts/r4/partitions/") for path in inputs)


def test_r5_gate_plans_are_exact_bounded_and_single_process() -> None:
    graph = validation_gate_module.load_gate_graph(
        ROOT / "configs" / "validation_gates.json"
    )
    inventory_path = ROOT / "governance" / "test_inventory.json"
    inventory = inventory_core_module.load_and_verify(
        ROOT,
        inventory_path,
        phase="R5",
        enforce_reviewed_counts=True,
        expected_sha256=inventory_core_module.verify_document_authority_pin(
            ROOT, inventory_path
        ),
    )
    expected_counts = {
        "artifact-contract": 15,
        "data-isolation": 17,
        "legacy-hard-cut": 55,
        "proposal-contract": 3,
        "realization-contract": 1,
    }

    assert set(graph.phases["R5"].owners) == set(expected_counts)
    for owner, expected_count in expected_counts.items():
        resolved = graph.resolve_phase("R5", "owner", owner)
        assert resolved == (
            "governance",
            "source_compile",
            f"r5_{owner.replace('-', '_')}_owner_tests",
        )
        assert graph.pytest_process_count("R5", "owner", owner) == 1
        assert len(graph.resolve_pytest_nodes("R5", "owner", owner)) == expected_count
        assert graph.resolve_pytest_nodes("R5", "owner", owner) == (
            inventory.owner_node_ids[owner]
        )
        assert len(resolved) <= graph.limits["max_steps_per_tier"]

    assert graph.resolve_phase("R5", "phase") == (
        "governance",
        "source_compile",
        "r5_phase_tests",
    )
    assert graph.pytest_process_count("R5", "phase") == 1
    phase_nodes = set(graph.resolve_pytest_nodes("R5", "phase"))
    assert graph.resolve_pytest_nodes("R5", "phase") == inventory.phase_node_ids
    assert {
        "tests/test_replay_governance.py::test_r5_active_docs_publish_truthful_foundation_boundary",
        "tests/test_replay_governance.py::test_r5_appendix_guard_rejects_wrong_section_and_owner_mutations",
        "tests/test_replay_governance.py::test_r5_governing_plan_uses_exact_frozen_inventory_partition",
    }.issubset(phase_nodes)


def test_r5_admission_rejects_before_execution_or_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("R5 admission crossed the unavailable boundary")

    monkeypatch.setattr(validation_gate_module, "_clean_git_snapshot", forbidden)
    monkeypatch.setattr(validation_gate_module, "_temporary_run_root", forbidden)
    monkeypatch.setattr(validation_gate_module, "write_receipt_exclusive", forbidden)

    with pytest.raises(AdmissionValidationError, match=r"^R5 admission is not available$"):
        validation_gate_module.run_validation(
            ROOT,
            phase="R5",
            tier="admission",
        )


__cemm_test_inventory__ = {
    "tests/test_validation_gate.py::test_bounded_process_capture_cleans_up_when_thread_start_fails": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-bounded-process-cleans-on-thread-start-failure",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "3e847cb625efbd57fa31da32811b565b502e24430897081467c3a4254aada3f5"
    },
    "tests/test_validation_gate.py::test_bounded_process_capture_kills_descendants_after_parent_exit": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-bounded-process-kills-descendants",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "0ca2d681ff90f489ed085be2eb46b1a2653b2a86a731dfd9d5cca114724fba83"
    },
    "tests/test_validation_gate.py::test_bounded_process_capture_preserves_fast_output": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-bounded-process-preserves-fast-output",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "f420162bd20673a27fec2db16f4e17c05fb7d5d96f46b9e91df1aae36950ea39"
    },
    "tests/test_validation_gate.py::test_bounded_process_capture_rejects_overflow_and_timeout": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-bounded-process-rejects-overflow-and-timeout",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "7ad44c363d8c695e641888011fdf2f4409a11bd41c5a0e4c6abf0e984f258306"
    },
    "tests/test_validation_gate.py::test_canonical_json_rejects_nonfinite_values": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-canonical-json-rejects-nonfinite-values",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "d1d4009ff3df48fe2840cbeebe4c83ee5488827308f2601300710d9242239488"
    },
    "tests/test_validation_gate.py::test_cli_rejects_legacy_profile": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-cli-rejects-legacy-profile",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "0cde05bb5831d2ecc200a7a780eeb3bfb1aae03b245e5567e4a8acb7a9bd8737"
    },
    "tests/test_validation_gate.py::test_committed_tree_parser_rejects_ambiguous_or_unsafe_records": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-committed-tree-parser-rejects-unsafe-records",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "653231674e6125e67a8c17150290e671b51ed28bc236085711a94725d1b45ab2"
    },
    "tests/test_validation_gate.py::test_config_rejects_raw_selectors_and_owner_phase_overlap": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-rejects-raw-selectors-and-role-overlap",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "03473dea8b6e595b7b07b383e4a25870efaf9f8f2203bf43c66b836aef30e93b"
    },
    "tests/test_validation_gate.py::test_current_source_config_rejects_alternate_receipt_plan": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-current-source-config-rejects-alternate-plan",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "3e2808aaad1c3bb69063d620154431ee1d57be8c1e20a6a81865b393912029cd"
    },
    "tests/test_validation_gate.py::test_current_source_config_rejects_incomplete_input_manifest": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-current-source-rejects-incomplete-input-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "a7c027e33b057b860f8d70d3d93a5184da9a4c88115c1f828b64b95e96764b8b"
    },
    "tests/test_validation_gate.py::test_current_source_verifier_rejects_forged_admission_subset": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-current-source-rejects-forged-admission-subset",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "81772210f2a945c53de6ce52604f41943487bcc54cc454e1c2cad74e238acc24"
    },
    "tests/test_validation_gate.py::test_dag_deduplicates_shared_dependencies": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-dag-deduplicates-shared-dependencies",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "ec25d9df891cddd19603b26b97d05f077760fdc58f3e49e2bba86efb75d4163d"
    },
    "tests/test_validation_gate.py::test_dag_rejects_cycles_and_unknown_dependencies": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-dag-rejects-cycles-and-unknown-dependencies",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "a7b18c88ab14a6f1c6140e8273365e6da3d8b45a283b3fc5838b368e3a8f867f"
    },
    "tests/test_validation_gate.py::test_every_test_tier_is_fresh_and_single_process": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-tiers-are-fresh-and-single-process",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "4058439897dc43537ffe464aaefbda1ec22073da48d82c0ba8c74ea4c75143f4"
    },
    "tests/test_validation_gate.py::test_g0_receipt_requires_exact_external_evidence_set": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-receipt-requires-exact-g0-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "122769a0b15a40aa12db5f98a7cd41dbfbd5f864078521e4dbb569a67b8e24e1"
    },
    "tests/test_validation_gate.py::test_git_snapshot_rejects_success_with_warning_stderr": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-git-snapshot-rejects-warning-stderr",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "6f83f9b4554429e68e6e806a857f7bb04a5fbe0a6a92b63d2f5595029a193dfd"
    },
    "tests/test_validation_gate.py::test_governance_step_uses_one_manifest_snapshot_for_all_governed_reads": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-governance-uses-one-manifest-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "d91a684944da801206b2196caea09f5c9839c7e20fdd72daae03a8304ed0d434"
    },
    "tests/test_validation_gate.py::test_governance_step_validates_effective_status_semantics": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-governance-validates-effective-status",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "47d4640f632e6dcc3d2dbc735d8c21ee475ab9431d29013c4f686e17906c9b6d"
    },
    "tests/test_validation_gate.py::test_input_manifest_rejects_file_absent_from_source_commit": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-input-manifest-rejects-uncommitted-file",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "ab8968f44052e845e54f61b869a7fac6a3981949a8c2e77b3322acec55b351fb"
    },
    "tests/test_validation_gate.py::test_isolated_environment_disables_external_pytest_plugins": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-isolates-external-pytest-plugins",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "e55a9deaae8cfbc423fa718211535f19eff68f44ca609bc8d4575760e2bbda58"
    },
    "tests/test_validation_gate.py::test_isolated_environment_owns_all_writable_paths": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-isolated-environment-owns-writable-paths",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "a5ed733798066038bdcac824ed7167eb9d619bfe27c3c65af01fb45f6a0491cd"
    },
    "tests/test_validation_gate.py::test_missing_and_malformed_structured_reports_fail_closed": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-structured-report-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "8dd7d81c12733a3c63924046ab1e8fdba82c979ddc76243941f0b18bc1f1b674"
    },
    "tests/test_validation_gate.py::test_observer_cleans_tree_when_instrumentation_raises": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-observer-cleans-on-instrumentation-error",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "96f0d05fed608ec03b19a06f9bca0d9aaeb5e5fe4f76b7be0024bebbec6d8424"
    },
    "tests/test_validation_gate.py::test_observer_rechecks_output_after_parent_exit": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-observer-rechecks-final-output",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "23e10fc68d61739667d9494b42cb9a7315dbfdb69ccc542e86c9146c50cf8119"
    },
    "tests/test_validation_gate.py::test_pytest_nonexecution_outcomes_are_nonpassing": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-nonexecution-outcomes-are-nonpassing",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "67d719528ce5af4c3cca193c80221101ee27264e2a029bada427e69cfe363e62"
    },
    "tests/test_validation_gate.py::test_pytest_report_binds_selector_and_requires_canonical_bytes": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-pytest-report-binds-selector-and-canonical-bytes",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "7596cf59e3deb9114548a56798c79cca7bc931d7a4332f9ad4e7c26b93bff53a"
    },
    "tests/test_validation_gate.py::test_pytest_report_reconstructs_duration_aggregation_error": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-pytest-report-reconstructs-duration-error",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "60b499bbbccb9a71724881b96f90eff4ef79c5b6330a5c34a2e350a40d0ef152"
    },
    "tests/test_validation_gate.py::test_pytest_report_rejects_self_inconsistent_facts_counts_and_collection": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-pytest-report-rejects-inconsistent-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "6f9aedae54e3dfdc57eae7569c57b9c54447a8f69cde6940834f85bcb0be0afd"
    },
    "tests/test_validation_gate.py::test_pytest_report_requires_exact_reconstructible_producer_schema": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-pytest-report-requires-producer-schema",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "22de03c60a818655738120f740991cd87b8e4f2f4a302a2f762b7665028d7f4b"
    },
    "tests/test_validation_gate.py::test_receipt_identity_and_exclusive_write": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-receipt-identity-and-exclusive-write",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "4aa0ee18db7c5c1877d451685c6669e8ad695cea100877032391bf98e1fb7b70"
    },
    "tests/test_validation_gate.py::test_receipt_verification_caches_fixed_evidence_per_pass": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-receipt-verification-caches-fixed-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "ff710a300dc086cd4660de909cc80d2897e67a5992958e3b709c73d27a534ab1"
    },
    "tests/test_validation_gate.py::test_receipt_writer_enforces_loader_size_bound": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-receipt-writer-enforces-size-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "89fb93d771a17554797ef7c908d3b914504497a38d7555c4a8ce3dc109c67670"
    },
    "tests/test_validation_gate.py::test_r4_gate_plans_are_exact_bounded_and_single_process": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-validation-plans-exact-bounded-single-process",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R4-Partition-Corrective-Task-8",
        "source_ast_sha256": "369622ecfcc3d9b3cb53a246ab860d3f52ee81c3148ff107727fc7e41050e73c"
    },
    "tests/test_validation_gate.py::test_r5_admission_rejects_before_execution_or_publication": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-admission-rejects-before-execution",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "2d21aab4aa96a44aee0e086641a841b86c5e3e749b35c7f8fd4894a670a1a388"
    },
    "tests/test_validation_gate.py::test_r5_gate_plans_are_exact_bounded_and_single_process": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-validation-plans-exact-bounded-single-process",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "source_ast_sha256": "d23398f35138182bbca7eb829d5f447f701d47dad94823bb1d72cd983cffb244"
    },
    "tests/test_validation_gate.py::test_runner_records_injected_peak_rss": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-runner-records-peak-rss",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "fb2c8c2f8fa1b914657b73b0819d0fe4f21b136eb3096055f599ccc2d66912fc"
    },
    "tests/test_validation_gate.py::test_slowest_rows_are_bounded_and_sorted": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-slowest-rows-bounded-and-sorted",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "aa000deac3228bdbd7c0e97d84d19549b9635ac52e653794ef83cd6081779d31"
    },
    "tests/test_validation_gate.py::test_step_identity_excludes_observational_timing": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-step-identity-excludes-observational-timing",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "b0eace3caf7a6bba45b405464d71ee797ad0e55241a70b527c2914e4447709d3"
    },
    "tests/test_validation_gate.py::test_step_result_binds_pytest_report_to_observation_projection": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-step-binds-pytest-observation-projection",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "704b0e19e8d8b7722698bd5933bb68db92e00d7e81444bc227b908164dbb6cfd"
    },
    "tests/test_validation_gate.py::test_step_result_rejects_foreign_schema_or_unbound_selector": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-step-rejects-foreign-schema-unbound-selector",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "eed8da4a05a1a954773fce885e1b498c8a74408dc52597e441666a87dc1cc93b"
    },
    "tests/test_validation_gate.py::test_step_result_rejects_unbound_or_downgraded_observations": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-step-rejects-observation-downgrade",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "8d16d82f639fdf98374f80196522db5490ebc11d797ec0a7ca22535763c8b1dc"
    },
    "tests/test_validation_gate.py::test_step_result_requires_exact_child_exit_for_observed_pytest_error": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-step-requires-exact-pytest-error-exit",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "ebe40be8eadb8c7fbb6d7584db8f517aba71440aebab2abbfc27dbbe9ec030ca"
    },
    "tests/test_validation_gate.py::test_strict_json_rejects_duplicate_keys_and_nonfinite": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-strict-json-rejects-duplicate-and-nonfinite",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "24b96a643a1de37ed7aff5f5af71e077176f576fe72a3dec9f7f3b0687cd2a49"
    },
    "tests/test_validation_gate.py::test_timeout_requires_confirmed_process_tree_termination": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-timeout-requires-process-tree-termination",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "070f2bdc7b7571dfb3c84a72346234f94a53a1c86ad9de397c636a72655d63a1"
    },
    "tests/test_validation_gate.py::test_validation_run_root_cleanup_fails_closed": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-run-root-cleanup-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "246c070ba67883e65bafff8c66754faefa637511655d0b262b1bd6a13b49d067"
    },
    "tests/test_validation_gate.py::test_validation_temp_parent_rejects_link_or_reparse_boundary": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-temp-parent-rejects-reparse",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "3abd108b394967848781fa90307c5f8937e8c140810aecd7160c5f2bb4531c17"
    },
    "tests/test_validation_gate.py::test_verified_loader_rejects_ambiguous_or_misnamed_runs": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-loader-rejects-ambiguous-and-misnamed-runs",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "ca507fc4b617a38380e49cc67285ce8de792ca3138a96d294983033435e56be7"
    },
    "tests/test_validation_gate.py::test_verified_loader_selects_exact_run_and_authenticates_evidence": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:gate-loader-authenticates-exact-run-and-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "895cdb1f0d6cb2f55e87be235bead9b390e1ac5b36b218d4ab89d7de8b14082a"
    }
}
