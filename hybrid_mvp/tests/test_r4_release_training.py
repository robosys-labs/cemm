from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_partition_contracts import (
    R4ClassAuthorization,
    R4ClassCapability,
    canonical_json_bytes,
)

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "run_r4_release_training.py"


def _load_controller():
    spec = importlib.util.spec_from_file_location("_cemm_r4_release_training_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _one_episode() -> AuthenticEpisode:
    for line in (ROOT / "artifacts" / "r4" / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            return AuthenticEpisode.from_dict(json.loads(line))
    raise AssertionError("R4 episode fixture is empty")


def _write_train_tree(root: Path):
    episode = _one_episode()
    payload = canonical_json_bytes(episode.as_dict())
    payload_sha = hashlib.sha256(payload).hexdigest()
    capability = R4ClassCapability.create(
        purpose="training",
        split="train",
        payload_path="artifacts/r4/splits/train.jsonl",
        payload_sha256=payload_sha,
        payload_count=1,
        source_set_ref="r4_partition_source_v3:test",
        split_manifest_ref="r4_split_manifest_v1:test",
    )
    capability_raw = capability.to_json_bytes()
    authorization = R4ClassAuthorization.create(
        purpose="training",
        expected_capability_ref=capability.capability_ref,
        expected_capability_sha256=hashlib.sha256(capability_raw).hexdigest(),
        artifact_graph_ref="r4_artifact_graph_v4:test",
        generator_source_revision="a" * 40,
        authority_generation="authority:test",
    )
    authorization_raw = authorization.to_json_bytes()
    paths = {
        "artifacts/r4/authorizations/train.json": authorization_raw,
        "artifacts/r4/capabilities/train.json": capability_raw,
        "artifacts/r4/splits/train.jsonl": payload,
    }
    for relative, raw in paths.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return authorization, hashlib.sha256(authorization_raw).hexdigest(), paths


def test_release_parent_import_does_not_load_torch(monkeypatch):
    sys.modules.pop("_cemm_r4_release_training_test", None)
    before = "torch" in sys.modules
    module = _load_controller()
    assert module.ReleaseTrainingError
    assert ("torch" in sys.modules) is before


def test_release_parent_requires_effective_r4_green():
    module = _load_controller()
    records = ({"phase": "R4", "status": "red"},)
    with pytest.raises(module.ReleaseTrainingError, match="not effectively green"):
        module._latest_effective_r4_record(records, {"R4": "red"})


def test_release_parent_projects_only_admission_authenticated_train_trust(tmp_path):
    module = _load_controller()
    authorization, authorization_sha, _ = _write_train_tree(tmp_path)
    record = {
        "phase": "R4",
        "status": "green",
        "admission_run_ref": "run:" + "1" * 24,
        "admission_gate_result_ref": "gate_result:" + "2" * 24,
        "predecessor_ref": "governance_record:" + "3" * 24,
        "source_base": "a" * 40,
    }
    receipt = SimpleNamespace(
        phase="R4",
        tier="admission",
        fresh=True,
        run_ref=record["admission_run_ref"],
        gate_result_ref=record["admission_gate_result_ref"],
        pre_admission_status_head_ref=record["predecessor_ref"],
        source_ref=record["source_base"],
        evidence_files=(
            SimpleNamespace(
                path="artifacts/r4/authorizations/train.json",
                sha256=authorization_sha,
            ),
            SimpleNamespace(path="artifacts/r4/BUILD_RECEIPT.json", sha256="f" * 64),
        ),
    )
    projection = module._extract_train_projection(tmp_path, record, receipt)
    assert projection.authorization_ref == authorization.authorization_ref
    assert projection.authorization_sha256 == authorization_sha
    assert not hasattr(projection, "split_manifest_ref")
    assert not hasattr(projection, "build_receipt_ref")


def test_release_parent_private_root_contains_only_authenticated_train_evidence(tmp_path):
    module = _load_controller()
    authorization, authorization_sha, paths = _write_train_tree(tmp_path)
    trust = module.TrainTrustProjection(
        admission_run_ref="run:" + "1" * 24,
        admission_gate_result_ref="gate_result:" + "2" * 24,
        admission_source_ref="a" * 40,
        authorization_ref=authorization.authorization_ref,
        authorization_sha256=authorization_sha,
    )
    isolated, batch = module.create_private_train_root(tmp_path, trust)
    try:
        actual = {
            path.relative_to(isolated).as_posix()
            for path in isolated.rglob("*")
            if path.is_file()
        }
        assert actual == set(paths)
        assert batch.authorization_ref == authorization.authorization_ref
        assert batch.snapshot.payload_bytes == paths["artifacts/r4/splits/train.jsonl"]
        assert not (isolated / "governance").exists()
        assert not (isolated / "artifacts/r4/BUILD_RECEIPT.json").exists()
        assert not (isolated / "artifacts/r4/split_manifest.json").exists()
    finally:
        import shutil
        shutil.rmtree(isolated, ignore_errors=True)


def test_release_parent_child_command_discloses_no_governance_or_sibling_identity(tmp_path):
    module = _load_controller()
    trust = module.TrainTrustProjection(
        admission_run_ref="run:" + "1" * 24,
        admission_gate_result_ref="gate_result:" + "2" * 24,
        admission_source_ref="a" * 40,
        authorization_ref="r4_class_authorization_v1:test",
        authorization_sha256="3" * 64,
    )
    command = module.child_command(
        model_kind="proposal",
        isolated_root=tmp_path,
        trust=trust,
    )
    text = " ".join(command)
    assert "--release-isolated-root" in command
    assert trust.authorization_ref in command
    assert trust.authorization_sha256 in command
    forbidden_tokens = (
        "replay_status",
        "BUILD_RECEIPT",
        "split_manifest",
        "frozen_test",
        "selection",
        "calibration",
    )
    for forbidden in forbidden_tokens:
        assert forbidden not in text
    for script in (ROOT / "scripts/train_proposer.py", ROOT / "scripts/train_realizer.py"):
        source = script.read_text(encoding="utf-8")
        assert "governance/replay_status" not in source
        assert "BUILD_RECEIPT" not in source
        assert "split_manifest" not in source
        assert "frozen_test" not in source


__cemm_test_inventory__ = {
    "tests/test_r4_release_training.py::test_release_parent_import_does_not_load_torch": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-parent-import-is-torch-free",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Partition-Corrective-Task-7",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "4dfd125dbb71c7597a61b0500eef27a059a42dfa85a1dfb9aacf74dda33d77eb",
    },
    "tests/test_r4_release_training.py::test_release_parent_requires_effective_r4_green": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-parent-requires-effective-r4-green",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Partition-Corrective-Task-7",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "986d714b7031b67a9638063dec098df8863ce44886bea64a4d5b3baf04a836e3",
    },
    "tests/test_r4_release_training.py::test_release_parent_projects_only_admission_authenticated_train_trust": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-parent-projects-only-admitted-train-trust",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Partition-Corrective-Task-7",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "7569529fabb1ee644930420d08e93256a7cd5ed05f9b943a92f749e32d820673",
    },
    "tests/test_r4_release_training.py::test_release_parent_private_root_contains_only_authenticated_train_evidence": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-parent-private-root-is-train-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Partition-Corrective-Task-7",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "bedd83a41a2d7a442dbe20008fd8d0ffc567af068c8fc7611b5a0119f8f142e4",
    },
    "tests/test_r4_release_training.py::test_release_parent_child_command_discloses_no_governance_or_sibling_identity": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-parent-child-command-nondisclosure",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Partition-Corrective-Task-7",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "fa26882980b4b7701e5a81a69496ea5109fd448a6c0388e12eac1ddc562b9ba1",
    },
}
