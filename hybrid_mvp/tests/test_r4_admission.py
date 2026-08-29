"""Repository-owned R4 artifact admission tests."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from cemm_authoritative_hybrid.r4_admission import (
    R4AdmissionError,
    verify_r4_admission,
)


ROOT = Path(__file__).parents[1]


def _copied_r4_project(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    project = tmp_path / "project"
    artifact_target = project / "artifacts" / "r4"
    artifact_target.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "artifacts" / "r4", artifact_target)
    scenario_target = project / "data" / "scenarios" / "use_cases.jsonl"
    scenario_target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "data" / "scenarios" / "use_cases.jsonl", scenario_target)
    config_target = project / "configs" / "r4_partitions.json"
    config_target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "configs" / "r4_partitions.json", config_target)
    receipt = json.loads((artifact_target / "BUILD_RECEIPT.json").read_text(encoding="utf-8"))
    assert receipt["abi_version"] == 4
    return project, receipt


def test_r4_admission_reconstructs_repository_owned_artifacts(
    tmp_path: Path,
) -> None:
    project, receipt = _copied_r4_project(tmp_path)
    report = verify_r4_admission(
        project,
        expected_source_revision=str(receipt["source_revision"]),
        expected_authority_generation=str(receipt["authority_generation"]),
    )
    assert set(report) == {
        "schema",
        "artifact_count",
        "artifact_set_ref",
        "build_receipt_ref",
        "build_receipt_abi_version",
        "source_revision",
        "authority_generation",
        "integrity_ref",
    }
    assert report["schema"] == "cemm-r4-artifact-integrity-step-report-v1"
    assert report["build_receipt_abi_version"] == 4
    assert report["artifact_count"] > 400

    candidate = project / "candidate"
    shutil.copytree(project / "artifacts" / "r4", candidate)
    candidate_report = verify_r4_admission(
        project,
        expected_source_revision=str(receipt["source_revision"]),
        expected_authority_generation=str(receipt["authority_generation"]),
        candidate_root=candidate,
    )
    assert candidate_report == report


@pytest.mark.parametrize(
    ("relative", "before", "after"),
    (
        ("episodes.jsonl", b'"decision_match":true', b'"decision_match":false'),
        (
            "partition_evidence.json",
            b'"evidence_ref":"r4_partition_evidence_v3:',
            b'"evidence_ref":"tampered_partition_evidence:',
        ),
        (
            "BUILD_RECEIPT.json",
            b'"authority_generation":"',
            b'"authority_generation":"tampered-',
        ),
    ),
    ids=("episode", "partition", "receipt"),
)
def test_r4_admission_rejects_tampered_artifact(
    tmp_path: Path,
    relative: str,
    before: bytes,
    after: bytes,
) -> None:
    project, receipt = _copied_r4_project(tmp_path)
    target = project / "artifacts" / "r4" / relative
    raw = target.read_bytes()
    assert before in raw
    target.write_bytes(raw.replace(before, after, 1))

    with pytest.raises(R4AdmissionError):
        verify_r4_admission(
            project,
            expected_source_revision=str(receipt["source_revision"]),
            expected_authority_generation=str(receipt["authority_generation"]),
        )


__cemm_test_inventory__ = {'tests/test_r4_admission.py::test_r4_admission_reconstructs_repository_owned_artifacts': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-admission-reconstructs-repository-artifacts',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                           'owner_ref': 'artifact-integrity',
                                                                                           'source_ast_sha256': '33d525534ed7599dc0b8194a3340eff94fb28d616c33c81d7e0627cdafb163ea'},
 'tests/test_r4_admission.py::test_r4_admission_rejects_tampered_artifact[episode]': {'activation_phase': 'R4',
                                                                                      'assertion_ref': 'assertion:r4-admission-rejects-tampered-episode',
                                                                                      'diagnostic_role': 'owner',
                                                                                      'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                      'owner_ref': 'artifact-integrity',
                                                                                      'source_ast_sha256': '242f1bd9d432f6621e982b3b1167877cb77b9c6e01aa636dcbd91dc33586caa4'},
 'tests/test_r4_admission.py::test_r4_admission_rejects_tampered_artifact[partition]': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:r4-admission-rejects-tampered-partition',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                        'owner_ref': 'artifact-integrity',
                                                                                        'source_ast_sha256': '242f1bd9d432f6621e982b3b1167877cb77b9c6e01aa636dcbd91dc33586caa4'},
 'tests/test_r4_admission.py::test_r4_admission_rejects_tampered_artifact[receipt]': {'activation_phase': 'R4',
                                                                                      'assertion_ref': 'assertion:r4-admission-rejects-tampered-receipt',
                                                                                      'diagnostic_role': 'owner',
                                                                                      'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                      'owner_ref': 'artifact-integrity',
                                                                                      'source_ast_sha256': '242f1bd9d432f6621e982b3b1167877cb77b9c6e01aa636dcbd91dc33586caa4'}}
