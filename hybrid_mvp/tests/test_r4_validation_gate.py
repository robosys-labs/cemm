"""R4 repository-owned validation-control tests."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cemm_authoritative_hybrid import process_control as process_control_module  # noqa: E402

sys.modules["process_control"] = process_control_module
import validation_gate as gate  # noqa: E402


def _valid_report() -> dict[str, object]:
    material: dict[str, object] = {
        "schema": "cemm-r4-artifact-integrity-step-report-v1",
        "artifact_count": 401,
        "artifact_set_ref": gate.content_ref("artifact_set", ["x"]),
        "build_receipt_ref": gate.content_ref("build_receipt", {"x": 1}),
        "build_receipt_abi_version": 4,
        "source_revision": "1" * 40,
        "authority_generation": "authority:test",
    }
    material["integrity_ref"] = gate.content_ref("r4_artifact_integrity", material)
    return material


def test_r4_integrity_report_has_exact_internal_shape() -> None:
    historical = dict(gate._R4_HISTORICAL_ABI3_INTEGRITY_REPORT)
    gate._validate_admission_step_report(
        "r4_artifact_integrity",
        historical,
        source_ref=gate._R4_HISTORICAL_ABI3_SOURCE_REF,
    )
    with pytest.raises(gate.AdmissionValidationError, match="exact source tuple"):
        gate._validate_admission_step_report(
            "r4_artifact_integrity",
            historical,
            source_ref="2" * 40,
        )

    report = _valid_report()
    gate._validate_admission_step_report(
        "r4_artifact_integrity", report, source_ref="2" * 40
    )
    report["build_receipt_abi_version"] = 3
    identity = dict(report)
    identity.pop("integrity_ref")
    report["integrity_ref"] = gate.content_ref("r4_artifact_integrity", identity)
    with pytest.raises(gate.AdmissionValidationError, match="must be 4"):
        gate._validate_admission_step_report(
            "r4_artifact_integrity", report, source_ref="2" * 40
        )
    with pytest.raises(gate.AdmissionValidationError, match="exact ABI 3"):
        gate._validate_admission_step_report(
            "r4_artifact_integrity",
            _valid_report(),
            source_ref=gate._R4_HISTORICAL_ABI3_SOURCE_REF,
        )


def test_r4_integrity_report_rejects_retired_review_fields() -> None:
    report = _valid_report()
    report["reviewer_ref"] = "reviewer:test"
    with pytest.raises(gate.AdmissionValidationError):
        gate._validate_admission_step_report(
            "r4_artifact_integrity", report, source_ref="2" * 40
        )


def test_r4_generator_source_is_parent_of_artifact_only_commit(monkeypatch) -> None:
    artifact_commit = "2" * 40
    generator_commit = "1" * 40

    def probe(_root: Path, arguments: tuple[str, ...], **_kwargs) -> bytes:
        if arguments == ("rev-list", "--parents", "-n", "1", artifact_commit):
            return f"{artifact_commit} {generator_commit}\n".encode()
        if arguments == (
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            artifact_commit,
        ):
            return (
                b"hybrid_mvp/artifacts/r4/BUILD_RECEIPT.json\n"
                b"hybrid_mvp/artifacts/r4/episodes.jsonl\n"
            )
        if arguments == ("rev-parse", "--show-prefix"):
            return b"hybrid_mvp/\n"
        raise AssertionError(arguments)

    monkeypatch.setattr(gate, "_bounded_git_probe", probe)
    assert gate._r4_generator_source_revision(ROOT, artifact_commit) == generator_commit


def test_r4_generator_source_rejects_merge_commit(monkeypatch) -> None:
    artifact_commit = "3" * 40

    monkeypatch.setattr(
        gate,
        "_bounded_git_probe",
        lambda *_args, **_kwargs: f"{artifact_commit} {'1' * 40} {'2' * 40}\n".encode(),
    )
    with pytest.raises(gate.GateConfigError, match="exactly one parent"):
        gate._r4_generator_source_revision(ROOT, artifact_commit)


def test_r4_generator_source_rejects_nonartifact_change(monkeypatch) -> None:
    artifact_commit = "2" * 40
    generator_commit = "1" * 40

    def probe(_root: Path, arguments: tuple[str, ...], **_kwargs) -> bytes:
        if arguments[0] == "rev-list":
            return f"{artifact_commit} {generator_commit}\n".encode()
        if arguments == ("rev-parse", "--show-prefix"):
            return b"hybrid_mvp/\n"
        return b"artifacts/r4/BUILD_RECEIPT.json\nsrc/cemm_authoritative_hybrid/r4_pipeline.py\n"

    monkeypatch.setattr(gate, "_bounded_git_probe", probe)
    with pytest.raises(gate.GateConfigError, match="only artifacts/r4"):
        gate._r4_generator_source_revision(ROOT, artifact_commit)


def test_historical_receipt_keeps_unselected_retired_step_opaque() -> None:
    payload = json.loads(
        (ROOT / "configs" / "validation_gates.json").read_text(encoding="utf-8")
    )
    payload["steps"]["r4_artifact_integrity"]["kind"] = "retired_control"
    graph = gate.GateGraph.from_dict(payload, historical_phase="R3")
    assert graph.phases["R3"].admission
    with pytest.raises(gate.GateConfigError, match="unknown kind"):
        gate.GateGraph.from_dict(payload)


def test_r4_admission_evidence_policy_is_sorted_and_unique(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt_path = (
        ROOT
        / "artifacts"
        / "validation"
        / "runs"
        / "300579c997da31e29d1c1a06.json"
    )
    historical_receipt = gate._load_receipt_file(receipt_path)
    historical_paths = tuple(
        item.path for item in historical_receipt.evidence_files
    )
    assert historical_paths == gate._R4_HISTORICAL_ABI3_EVIDENCE_PATHS
    assert historical_paths == tuple(sorted(set(historical_paths)))
    assert gate._required_admission_evidence_paths(
        "R4",
        source_ref=historical_receipt.source_ref,
        step_results=historical_receipt.step_results,
        evidence_paths=historical_paths,
    ) == historical_paths
    with pytest.raises(gate.AdmissionValidationError, match="source/report tuple"):
        gate._required_admission_evidence_paths(
            "R4",
            source_ref="2" * 40,
            step_results=historical_receipt.step_results,
            evidence_paths=historical_paths,
        )

    current_root = tmp_path / "current"
    build_receipt = current_root / "artifacts" / "r4" / "BUILD_RECEIPT.json"
    build_receipt.parent.mkdir(parents=True)
    build_receipt.write_bytes(gate.canonical_json_bytes({"abi_version": 4}) + b"\n")
    current_paths = gate._required_admission_evidence_paths(
        "R4", root=current_root
    )
    assert current_paths == gate._R4_CURRENT_ABI4_EVIDENCE_PATHS
    assert current_paths == tuple(sorted(set(current_paths)))
    assert "artifacts/r4/partition_evidence.json" in current_paths
    assert "artifacts/r4/training_allowlist.json" not in current_paths
    build_receipt.write_bytes(gate.canonical_json_bytes({"abi_version": 3}) + b"\n")
    with pytest.raises(gate.AdmissionValidationError, match="version 4"):
        gate._required_admission_evidence_paths("R4", root=current_root)

    historical_blobs = gate._tracked_source_blobs(
        ROOT, gate._R4_HISTORICAL_ABI3_SOURCE_REF
    )
    assert set(historical_paths).issubset(historical_blobs)
    committed_bytes = {
        path: gate._read_committed_blob(
            ROOT,
            object_id=historical_blobs[path],
            relative=path,
        )
        for path in historical_paths
    }
    monkeypatch.setattr(
        gate,
        "_tracked_source_blobs",
        lambda _root, source_ref: historical_blobs
        if source_ref == gate._R4_HISTORICAL_ABI3_SOURCE_REF
        else {},
    )
    monkeypatch.setattr(
        gate,
        "_read_committed_blob",
        lambda _root, *, object_id, relative: committed_bytes[relative],
    )
    run_directory = tmp_path / "artifacts" / "validation" / "runs"
    run_directory.mkdir(parents=True)
    historical_run_path = run_directory / receipt_path.name
    historical_run_path.write_bytes(receipt_path.read_bytes())
    reconstructed, reconstructed_paths = gate.load_verified_admission_receipt(
        tmp_path,
        phase="R4",
        expected_status="passed",
        run_ref=historical_receipt.run_ref,
    )
    assert reconstructed.run_ref == historical_receipt.run_ref
    assert reconstructed.source_ref == historical_receipt.source_ref
    assert reconstructed_paths == tuple(
        sorted((*historical_paths, historical_run_path.relative_to(tmp_path).as_posix()))
    )


def test_r4_active_inventory_timeout_covers_measured_suite_bound() -> None:
    payload = json.loads(
        (ROOT / "configs" / "validation_gates.json").read_text(encoding="utf-8")
    )
    assert payload["limits"]["pytest_timeout_seconds"] == 900


__cemm_test_inventory__ = {'tests/test_r4_validation_gate.py::test_r4_integrity_report_has_exact_internal_shape': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:r4-integrity-report-exact-internal-shape',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                         'owner_ref': 'artifact-integrity',
                                                                                         'source_ast_sha256': 'a79be629304bb1da7335cfc1bbf0889d2c8b2639f2b2b0cef3cf29798518c196'},
 'tests/test_r4_validation_gate.py::test_r4_integrity_report_rejects_retired_review_fields': {'activation_phase': 'R4',
                                                                                              'assertion_ref': 'assertion:r4-integrity-report-rejects-review-fields',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                              'owner_ref': 'artifact-integrity',
                                                                                              'source_ast_sha256': '60d7d58a06b634f634a713a6cdcd13d3b802ec577fb7d65f60f0c5298569200a'},
 'tests/test_r4_validation_gate.py::test_r4_generator_source_is_parent_of_artifact_only_commit': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-generator-source-is-artifact-parent',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                                  'owner_ref': 'artifact-integrity',
                                                                                                  'source_ast_sha256': '7a4b9080f5061b604ffb598e88bb3d3360ae4a24e9d32c106c0503cbae15b9f2'},
 'tests/test_r4_validation_gate.py::test_r4_generator_source_rejects_merge_commit': {'activation_phase': 'R4',
                                                                                     'assertion_ref': 'assertion:r4-generator-source-rejects-merge',
                                                                                     'diagnostic_role': 'owner',
                                                                                     'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                     'owner_ref': 'artifact-integrity',
                                                                                     'source_ast_sha256': 'e6a83d271f044d38be245eab614833b7e1f8b5a48d33680e64490662e07c1294'},
 'tests/test_r4_validation_gate.py::test_r4_generator_source_rejects_nonartifact_change': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-generator-source-rejects-nonartifact-change',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                           'owner_ref': 'artifact-integrity',
                                                                                           'source_ast_sha256': '8da1fa159bf48d2df86dc483850deda8330df3eca870b060240702be5f060664'},
 'tests/test_r4_validation_gate.py::test_historical_receipt_keeps_unselected_retired_step_opaque': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:historical-receipt-unselected-step-is-opaque',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                                    'owner_ref': 'artifact-integrity',
                                                                                                    'source_ast_sha256': '5c2e20bf958cae1b04c08c21d55d40524a4632d6ce6903d4d3632b99616a2812'},
 'tests/test_r4_validation_gate.py::test_r4_admission_evidence_policy_is_sorted_and_unique': {'activation_phase': 'R4',
                                                                                              'assertion_ref': 'assertion:r4-admission-evidence-policy-canonical-order',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                              'owner_ref': 'artifact-integrity',
                                                                                              'source_ast_sha256': '24c2dcfdbebfcfce2046cf9236c591355f4d86d352abb7d3089a0f3cf00c83fc'},
 'tests/test_r4_validation_gate.py::test_r4_active_inventory_timeout_covers_measured_suite_bound': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:r4-active-inventory-timeout-measured-bound',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                                    'owner_ref': 'artifact-integrity',
                                                                                                    'source_ast_sha256': 'a7ed45a72f38edde14a45d59e4a049fb22c191330f41473310f67993b9f9ceb0'}}
