"""Current-owner successors for the retired trainer-fixture isolation tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.partitions import PartitionAccessError
from cemm_authoritative_hybrid.training import load_partition_episodes_for_training


ROOT = Path(__file__).parents[1]
PARTITIONS = ROOT / "data" / "partitions"


def test_current_training_loader_can_open_train() -> None:
    episodes = load_partition_episodes_for_training(PARTITIONS / "train.jsonl", ROOT)
    assert len(episodes) == 234


def test_current_training_loader_rejects_validation() -> None:
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(PARTITIONS / "validation.jsonl", ROOT)


def test_current_training_loader_rejects_test() -> None:
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(PARTITIONS / "test.jsonl", ROOT)


__cemm_test_inventory__ = {'tests/test_r4_training_partition_boundary.py::test_current_training_loader_can_open_train': {'activation_phase': 'R4',
                                                                                               'assertion_ref': 'assertion:training-isolation-trainer-can-open-train',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                               'owner_ref': 'artifact-integrity',
                                                                                               'source_ast_sha256': 'e08e63006ed3fa7325cae0b8a311a853de44d98af70b295c79c487f89667ecef',
                                                                                               'supersedes_node_id': 'tests/test_training_isolation.py::test_trainer_can_open_train'},
 'tests/test_r4_training_partition_boundary.py::test_current_training_loader_rejects_validation': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:training-isolation-trainer-cannot-open-validation',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                                   'owner_ref': 'artifact-integrity',
                                                                                                   'source_ast_sha256': '3693ec5b24b2be2f97e97dbe79d7896185e4065aef1793b27a0a207da239164f',
                                                                                                   'supersedes_node_id': 'tests/test_training_isolation.py::test_trainer_cannot_open_validation'},
 'tests/test_r4_training_partition_boundary.py::test_current_training_loader_rejects_test': {'activation_phase': 'R4',
                                                                                             'assertion_ref': 'assertion:training-isolation-trainer-cannot-open-validation-or-test',
                                                                                             'diagnostic_role': 'owner',
                                                                                             'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                             'owner_ref': 'artifact-integrity',
                                                                                             'source_ast_sha256': '83830cff2e2b8361a2f6caf14317c88adfd1e96a16ff52a8fb3808e5b466d47f',
                                                                                             'supersedes_node_id': 'tests/test_training_isolation.py::test_trainer_cannot_open_validation_or_test'}}
