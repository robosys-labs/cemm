"""Current R4→R5 authenticated train-capability boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_partition_access import (
    PartitionAccessError,
    load_r4_train_episodes,
)
from cemm_authoritative_hybrid.r4_partition_contracts import (
    R4ClassAuthorization,
    R4ClassCapability,
    canonical_json_bytes,
)


ROOT = Path(__file__).parents[1]


def _one_episode() -> AuthenticEpisode:
    for line in (ROOT / "artifacts" / "r4" / "episodes.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
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
    for relative, raw in (
        ("artifacts/r4/authorizations/train.json", authorization_raw),
        ("artifacts/r4/capabilities/train.json", capability_raw),
        ("artifacts/r4/splits/train.jsonl", payload),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return authorization, capability, hashlib.sha256(authorization_raw).hexdigest()


def test_current_training_loader_can_open_train(tmp_path: Path) -> None:
    authorization, capability, authorization_sha = _write_train_tree(tmp_path)
    batch = load_r4_train_episodes(
        "artifacts/r4/authorizations/train.json",
        "artifacts/r4/capabilities/train.json",
        tmp_path,
        expected_authorization_ref=authorization.authorization_ref,
        expected_authorization_sha256=authorization_sha,
    )
    assert len(batch.episodes) == 1
    assert batch.snapshot.capability_ref == capability.capability_ref
    assert batch.snapshot.payload_ref == capability.payload_ref


def test_current_training_loader_rejects_validation(tmp_path: Path) -> None:
    authorization, _, authorization_sha = _write_train_tree(tmp_path)
    with pytest.raises(PartitionAccessError):
        load_r4_train_episodes(
            "artifacts/r4/authorizations/train.json",
            "artifacts/r4/capabilities/selection.json",
            tmp_path,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256=authorization_sha,
        )


def test_current_training_loader_rejects_test(tmp_path: Path) -> None:
    authorization, _, authorization_sha = _write_train_tree(tmp_path)
    with pytest.raises(PartitionAccessError):
        load_r4_train_episodes(
            "artifacts/r4/authorizations/train.json",
            "data/partitions/test.jsonl",
            tmp_path,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256=authorization_sha,
        )


def test_train_capability_discloses_no_sibling_identity(tmp_path: Path) -> None:
    authorization, capability, _ = _write_train_tree(tmp_path)
    capability_text = json.dumps(capability.as_dict(), sort_keys=True)
    authorization_text = json.dumps(authorization.as_dict(), sort_keys=True)
    assert capability.purpose == "training"
    assert capability.split == "train"
    assert capability.payload_path == "artifacts/r4/splits/train.jsonl"
    for sibling in ("selection", "calibration", "frozen_test"):
        assert sibling not in capability_text
        assert sibling not in authorization_text


__cemm_test_inventory__ = {'tests/test_r4_training_partition_boundary.py::test_current_training_loader_can_open_train': {'activation_phase': 'R4',
                                                                                               'assertion_ref': 'assertion:training-isolation-trainer-can-open-train',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                               'owner_ref': 'artifact-integrity',
                                                                                               'source_ast_sha256': 'e0e56c0a5cd4aec2e55f80bf278cad77656d445d64d9e71628281f7cea5f24c3',
                                                                                               'supersedes_node_id': 'tests/test_training_isolation.py::test_trainer_can_open_train'},
 'tests/test_r4_training_partition_boundary.py::test_current_training_loader_rejects_validation': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:training-isolation-trainer-cannot-open-validation',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                                   'owner_ref': 'artifact-integrity',
                                                                                                   'source_ast_sha256': 'a46e90ee3d337a473646cb24226eb1ac7c08308c2f2ade5d1fe52632a226f894',
                                                                                                   'supersedes_node_id': 'tests/test_training_isolation.py::test_trainer_cannot_open_validation'},
 'tests/test_r4_training_partition_boundary.py::test_current_training_loader_rejects_test': {'activation_phase': 'R4',
                                                                                             'assertion_ref': 'assertion:training-isolation-trainer-cannot-open-validation-or-test',
                                                                                             'diagnostic_role': 'owner',
                                                                                             'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                             'owner_ref': 'artifact-integrity',
                                                                                             'source_ast_sha256': '4aa3613d1520fef3c09bee0f6a38fb18c1b6a7598438ac40d3c473c1f4d24818',
                                                                                             'supersedes_node_id': 'tests/test_training_isolation.py::test_trainer_cannot_open_validation_or_test'},
 'tests/test_r4_training_partition_boundary.py::test_train_capability_discloses_no_sibling_identity': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:partition-leakage-sealed-test-hash-is-not-available-to-training',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                                       'owner_ref': 'artifact-integrity',
                                                                                                       'source_ast_sha256': '107208937e8f03be68185f26d1db531f3e0f95ccf1322224a0e56dadb26ec4ef',
                                                                                                       'supersedes_node_id': 'tests/test_partition_leakage.py::test_sealed_test_hash-is-not-available-to-training'}}
