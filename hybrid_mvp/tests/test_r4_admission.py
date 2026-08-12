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
from cemm_authoritative_hybrid.r4_pipeline import R4BuildReceipt


ROOT = Path(__file__).parents[1]


def _copied_r4_project(tmp_path: Path) -> tuple[Path, R4BuildReceipt]:
    project = tmp_path / "project"
    artifact_target = project / "artifacts" / "r4"
    artifact_target.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "artifacts" / "r4", artifact_target)
    scenario_target = project / "data" / "scenarios" / "use_cases.jsonl"
    scenario_target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "data" / "scenarios" / "use_cases.jsonl", scenario_target)

    receipt_path = artifact_target / "BUILD_RECEIPT.json"
    legacy = json.loads(receipt_path.read_text(encoding="utf-8"))
    values = {
        key: value
        for key, value in legacy.items()
        if key not in {"abi_version", "receipt_ref", "review_state"}
    }
    values["partition_manifest_sha256s"] = tuple(
        values["partition_manifest_sha256s"]
    )
    values["admission_state"] = "candidate"
    receipt = R4BuildReceipt.create(**values)
    receipt_path.write_text(
        json.dumps(
            receipt.as_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return project, receipt


def test_r4_admission_reconstructs_repository_owned_artifacts(
    tmp_path: Path,
) -> None:
    project, receipt = _copied_r4_project(tmp_path)
    report = verify_r4_admission(
        project,
        expected_source_revision=receipt.source_revision,
        expected_authority_generation=receipt.authority_generation,
    )
    assert set(report) == {
        "schema",
        "artifact_count",
        "artifact_set_ref",
        "build_receipt_ref",
        "source_revision",
        "authority_generation",
        "integrity_ref",
    }
    assert report["schema"] == "cemm-r4-artifact-integrity-step-report-v1"
    assert report["artifact_count"] > 400


@pytest.mark.parametrize(
    ("relative", "before", "after"),
    (
        ("episodes.jsonl", b'"decision_match":true', b'"decision_match":false'),
        ("partitions/general.json", b'"axis":"general"', b'"axis":"lexical"'),
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
            expected_source_revision=receipt.source_revision,
            expected_authority_generation=receipt.authority_generation,
        )


__cemm_test_inventory__ = {'tests/test_r4_admission.py::test_r4_admission_reconstructs_repository_owned_artifacts': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-admission-reconstructs-repository-artifacts',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                           'owner_ref': 'artifact-integrity',
                                                                                           'source_ast_sha256': '71299d54d4323fba9e053aac7f9ba606551e7393c84babe480a9b39492c7394e'},
 'tests/test_r4_admission.py::test_r4_admission_rejects_tampered_artifact[episode]': {'activation_phase': 'R4',
                                                                                      'assertion_ref': 'assertion:r4-admission-rejects-tampered-episode',
                                                                                      'diagnostic_role': 'owner',
                                                                                      'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                      'owner_ref': 'artifact-integrity',
                                                                                      'source_ast_sha256': '39185b6e67b50020d58624d38f3259d0fa0594c0915b3637613a6bb3b1271272'},
 'tests/test_r4_admission.py::test_r4_admission_rejects_tampered_artifact[partition]': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:r4-admission-rejects-tampered-partition',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                        'owner_ref': 'artifact-integrity',
                                                                                        'source_ast_sha256': '39185b6e67b50020d58624d38f3259d0fa0594c0915b3637613a6bb3b1271272'},
 'tests/test_r4_admission.py::test_r4_admission_rejects_tampered_artifact[receipt]': {'activation_phase': 'R4',
                                                                                      'assertion_ref': 'assertion:r4-admission-rejects-tampered-receipt',
                                                                                      'diagnostic_role': 'owner',
                                                                                      'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                      'owner_ref': 'artifact-integrity',
                                                                                      'source_ast_sha256': '39185b6e67b50020d58624d38f3259d0fa0594c0915b3637613a6bb3b1271272'}}
