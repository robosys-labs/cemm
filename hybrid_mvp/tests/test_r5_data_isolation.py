from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import cemm_authoritative_hybrid.training as training_module
from cemm_authoritative_hybrid.partitions import PartitionAccessError
from cemm_authoritative_hybrid.training import (
    ReleaseProposalTrainer,
    ReleaseRealizerTrainer,
    load_partition_episodes_for_training,
)


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
    "tests/test_r5_data_isolation.py::test_training_loader_requires_exact_canonical_manifest_paths": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-requires-canonical-manifest-paths",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "b115d301453f6087e991a4bb2d5c23766df14b86687880bfd4cad9a003c78598",
    },
    "tests/test_r5_data_isolation.py::test_training_loader_parses_authenticated_snapshot_without_second_read": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-parses-authenticated-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "bc45b09feb5296d947f55843167e9d0e9d33f4e9837b337f18eb1e23c20f59d1",
    },
    "tests/test_r5_data_isolation.py::test_release_trainers_authenticate_train_once": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-trainers-authenticate-train-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "2a46da66af92f620132bcbd9cd727d0abb3c1bf791f606c2f6212ec8e0857d7e",
    },
    "tests/test_r5_data_isolation.py::test_release_trainers_reject_nontrain_before_downstream_work": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-trainers-reject-nontrain-at-loader",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "81e25ca60f9724c6942a149260f779480213a9626b7f662540828ace8455896c",
    },
    "tests/test_r5_data_isolation.py::test_release_trainer_metadata_uses_authenticated_fit_snapshot": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-trainer-metadata-binds-fit-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": "29cd347df56a902e991ec934d5dc148406be3a04af62e261e7e5cb52db48b31b",
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


def _trainer_stopping_after_episode_load(trainer_type, root: Path):
    trainer = object.__new__(trainer_type)
    trainer._root = root
    trainer._seed = 1701
    trainer._authority = SimpleNamespace(model_compatibility_hash="authority:test")
    trainer._epochs = 0
    trainer._learning_rate = 0.0
    trainer._device = "cpu"
    if trainer_type is ReleaseProposalTrainer:
        trainer._legal_action_index = object()
        trainer._max_form_tokens = 1
        trainer._max_actions = 1
        trainer._hidden = 1
        trainer._layers = 1
    else:
        trainer._hidden = 1
        trainer._layers = 1
        trainer._feature_dim = 1
        trainer._vocab_size = 1
    return trainer


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


def test_training_loader_requires_exact_canonical_manifest_paths(tmp_path):
    train, _, _ = _write_partition_root(tmp_path)
    manifest = tmp_path / "data" / "partitions" / "manifest.json"
    original = json.loads(manifest.read_text(encoding="utf-8"))
    alternate = train.with_name("alternate.jsonl")
    shutil.copyfile(train, alternate)
    mutations = (
        ("train_path", "data/partitions/alternate.jsonl"),
        ("validation_path", "data/partitions/train.jsonl"),
        ("test_path", "data/partitions/validation.jsonl"),
    )
    for field, value in mutations:
        row = dict(original)
        row[field] = value
        manifest.write_text(
            json.dumps(row, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        requested = alternate if field == "train_path" else train
        with pytest.raises(PartitionAccessError):
            load_partition_episodes_for_training(requested, tmp_path)


def test_training_loader_parses_authenticated_snapshot_without_second_read(
    tmp_path, monkeypatch
):
    train, _, _ = _write_partition_root(tmp_path)
    original_read_text = Path.read_text

    def mutate_train_before_second_read(path, *args, **kwargs):
        if path.resolve() == train.resolve():
            path.write_text('{"episode_ref":"episode:mutated"}\n', encoding="utf-8")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mutate_train_before_second_read)
    episodes = load_partition_episodes_for_training(train, tmp_path)
    assert [episode.episode_ref for episode in episodes] == ["episode:train"]


def test_release_trainers_authenticate_train_once(tmp_path, monkeypatch):
    train, _, _ = _write_partition_root(tmp_path)
    original_check = training_module._check_partition_access

    class LoadedEpisodes(RuntimeError):
        pass

    for trainer_type, downstream_name in (
        (ReleaseProposalTrainer, "_ActionVocabulary"),
        (ReleaseRealizerTrainer, "RealizerNetwork"),
    ):
        calls = 0
        seed_calls = 0

        def counted_check(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original_check(*args, **kwargs)

        def counted_seed(_seed):
            nonlocal seed_calls
            seed_calls += 1

        def stop_after_load(*_args, **_kwargs):
            raise LoadedEpisodes

        with monkeypatch.context() as context:
            context.setattr(training_module, "_check_partition_access", counted_check)
            context.setattr(training_module, "_set_deterministic_seeds", counted_seed)
            context.setattr(training_module, downstream_name, stop_after_load)
            trainer = _trainer_stopping_after_episode_load(trainer_type, tmp_path)
            with pytest.raises(LoadedEpisodes):
                trainer.fit(train)
        assert calls == 1
        assert seed_calls == 1


def test_release_trainers_reject_nontrain_before_downstream_work(tmp_path, monkeypatch):
    _, validation, test = _write_partition_root(tmp_path)
    arbitrary = tmp_path / "arbitrary.jsonl"
    arbitrary.write_text('{"episode_ref":"episode:arbitrary"}\n', encoding="utf-8")
    seed_calls = 0

    def counted_seed(_seed):
        nonlocal seed_calls
        seed_calls += 1

    def downstream_must_not_run(*_args, **_kwargs):
        raise AssertionError("trainer reached downstream work for a non-train partition")

    for trainer_type, downstream_name in (
        (ReleaseProposalTrainer, "_ActionVocabulary"),
        (ReleaseRealizerTrainer, "RealizerNetwork"),
    ):
        with monkeypatch.context() as context:
            context.setattr(training_module, "_set_deterministic_seeds", counted_seed)
            context.setattr(training_module, downstream_name, downstream_must_not_run)
            trainer = _trainer_stopping_after_episode_load(trainer_type, tmp_path)
            for path in (validation, test, arbitrary):
                with pytest.raises(PartitionAccessError):
                    trainer.fit(path)
    assert seed_calls == 0


def test_release_trainer_metadata_uses_authenticated_fit_snapshot(tmp_path, monkeypatch):
    train, _, _ = _write_partition_root(tmp_path)
    expected_dataset_hash = _sha256(train)
    original_train_bytes = train.read_bytes()
    original_load = training_module._load_partition_episodes_with_hash

    class FakeVocabulary:
        size = 1

        def __init__(self, *_args, **_kwargs):
            pass

        def add_action(self, _action):
            pass

        def index_for_action(self, _action):
            return 0

    class FakeNetwork:
        output_head = SimpleNamespace(out_features=1)

        def __init__(self, *_args, **_kwargs):
            pass

        def to(self, _device):
            return self

        def parameters(self):
            return ()

        def train(self):
            pass

        def eval(self):
            pass

    class FakeOptimizer:
        def __init__(self, *_args, **_kwargs):
            pass

    def load_with_proposal_action(*args, **kwargs):
        episodes, digest = original_load(*args, **kwargs)
        return [replace(episodes[0], action_sequence=({"action_type": "test"},))], digest

    for trainer_type in (ReleaseProposalTrainer, ReleaseRealizerTrainer):
        with monkeypatch.context() as context:
            context.setattr(training_module, "_set_deterministic_seeds", lambda _seed: None)
            context.setattr(training_module.torch.optim, "Adam", FakeOptimizer)
            context.setattr(training_module, "_ActionVocabulary", FakeVocabulary)
            context.setattr(training_module, "ProposalNetwork", FakeNetwork)
            context.setattr(training_module, "RealizerNetwork", FakeNetwork)
            context.setattr(training_module, "_action_from_dict", lambda *_args: object())
            context.setattr(training_module, "_build_orientation", lambda *_args: object())
            context.setattr(training_module, "_encode_form_units", lambda *_args: object())
            context.setattr(
                training_module, "_encode_orientation_structural", lambda *_args: object()
            )
            context.setattr(
                training_module, "_encode_response_meaning_features", lambda *_args: object()
            )
            context.setattr(training_module, "_surface_to_target", lambda *_args: 0)
            context.setattr(
                training_module, "_compute_action_encoding_hash", lambda _index: "action:test"
            )
            if trainer_type is ReleaseProposalTrainer:
                context.setattr(
                    training_module,
                    "_load_partition_episodes_with_hash",
                    load_with_proposal_action,
                )
            trainer = _trainer_stopping_after_episode_load(trainer_type, tmp_path)
            trainer._form_resolver = SimpleNamespace(resolve=lambda _surface: object())
            if trainer_type is ReleaseProposalTrainer:
                trainer._config = object()
            with pytest.raises(AttributeError):
                trainer.build_metadata()
            trainer.fit(train)
            train.write_text('{"episode_ref":"episode:mutated"}\n', encoding="utf-8")
            context.setattr(
                training_module,
                "_file_sha256",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError("build_metadata reopened the train partition")
                ),
            )
            assert trainer.build_metadata()["dataset_hash"] == expected_dataset_hash
        train.write_bytes(original_train_bytes)
