from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from cemm_authoritative_hybrid.partitions import PartitionAccessError
from cemm_authoritative_hybrid.training import load_partition_episodes_for_training


__cemm_test_inventory__ = {
    "tests/test_r5_data_isolation.py::test_training_loader_accepts_only_manifest_bound_train": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-accepts-manifest-bound-train",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "a6d606995d37a4c12ff95bb628f7700354c3ed2bd047edef497e5dd2e9eb117f",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_validation_and_test": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-nontrain-partitions",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "9605adfee640cc97d6d91107e8fd4f7581dabf126be84daaa9f095a62ea66466",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_copied_train_at_other_path": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-copied-train",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "9617627f5e098fed3489bc2e749e482d050a0371b4a0db13870723c631c9b602",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_renamed_sealed_partition": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-renamed-sealed-partition",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "e38c3bd48b9b4db78b1224cde561419549064d512f9de202f5b05fa26bfc4501",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_arbitrary_jsonl": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-arbitrary-jsonl",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "3498a6544db81edf70a8e825de5c133e256bfccc8ad95e8bae0cfe9666379d5b",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_missing_and_malformed_manifest": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-requires-strict-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "a4105bb4dca8eefb71280939b05f91a301d30521589377f118ab4a90f4686366",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_manifest_path_and_symlink_escape": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-path-escape",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "b819ff42b0bb4707a953c3e622485b1b8436bf726cd50e866915fd1df177cf42",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_partition_root(root: Path) -> tuple[Path, Path, Path]:
    partitions = root / "data" / "partitions"
    partitions.mkdir(parents=True)
    train = partitions / "train.jsonl"
    validation = partitions / "validation.jsonl"
    test = partitions / "test.jsonl"
    train.write_text('{"episode_ref":"episode:train"}\n', encoding="utf-8")
    validation.write_text('{"episode_ref":"episode:validation"}\n', encoding="utf-8")
    test.write_text('{"episode_ref":"episode:test"}\n', encoding="utf-8")
    manifest = {
        "seed": 1701,
        "test_count": 1,
        "test_path": "data/partitions/test.jsonl",
        "test_sha256": _sha256(test),
        "train_count": 1,
        "train_path": "data/partitions/train.jsonl",
        "train_sha256": _sha256(train),
        "validation_count": 1,
        "validation_path": "data/partitions/validation.jsonl",
        "validation_sha256": _sha256(validation),
    }
    (partitions / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    return train, validation, test


def test_training_loader_accepts_only_manifest_bound_train(tmp_path):
    train, _, _ = _write_partition_root(tmp_path)
    episodes = load_partition_episodes_for_training(train, tmp_path)
    assert [episode.episode_ref for episode in episodes] == ["episode:train"]


def test_training_loader_rejects_validation_and_test(tmp_path):
    _, validation, test = _write_partition_root(tmp_path)
    for path in (validation, test):
        with pytest.raises(PartitionAccessError):
            load_partition_episodes_for_training(path, tmp_path)


def test_training_loader_rejects_copied_train_at_other_path(tmp_path):
    train, _, _ = _write_partition_root(tmp_path)
    copied = tmp_path / "copied-train.jsonl"
    shutil.copyfile(train, copied)
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(copied, tmp_path)


def test_training_loader_rejects_renamed_sealed_partition(tmp_path):
    _, validation, _ = _write_partition_root(tmp_path)
    renamed = tmp_path / "renamed-validation.jsonl"
    shutil.copyfile(validation, renamed)
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(renamed, tmp_path)


def test_training_loader_rejects_arbitrary_jsonl(tmp_path):
    _write_partition_root(tmp_path)
    arbitrary = tmp_path / "arbitrary.jsonl"
    arbitrary.write_text('{"episode_ref":"episode:arbitrary"}\n', encoding="utf-8")
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(arbitrary, tmp_path)


def test_training_loader_rejects_missing_and_malformed_manifest(tmp_path):
    train, _, _ = _write_partition_root(tmp_path)
    manifest = tmp_path / "data" / "partitions" / "manifest.json"
    manifest.unlink()
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(train, tmp_path)
    manifest.write_text('{"train_path":"data/partitions/train.jsonl"}', encoding="utf-8")
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(train, tmp_path)
    manifest.write_bytes(b"{" * (64 * 1024 + 1))
    with pytest.raises(PartitionAccessError):
        load_partition_episodes_for_training(train, tmp_path)


def test_training_loader_rejects_manifest_path_and_symlink_escape(tmp_path):
    train, _, _ = _write_partition_root(tmp_path)
    manifest = tmp_path / "data" / "partitions" / "manifest.json"
    row = json.loads(manifest.read_text(encoding="utf-8"))
    outside = tmp_path.parent / f"{tmp_path.name}-outside.jsonl"
    outside.write_bytes(train.read_bytes())
    try:
        row["train_path"] = f"../{outside.name}"
        row["train_sha256"] = _sha256(outside)
        manifest.write_text(
            json.dumps(row, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        with pytest.raises(PartitionAccessError):
            load_partition_episodes_for_training(outside, tmp_path)

        link = tmp_path / "data" / "partitions" / "train-link.jsonl"
        os.symlink(outside, link)
        row["train_path"] = "data/partitions/train-link.jsonl"
        manifest.write_text(
            json.dumps(row, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        with pytest.raises(PartitionAccessError):
            load_partition_episodes_for_training(link, tmp_path)
    finally:
        outside.unlink(missing_ok=True)
