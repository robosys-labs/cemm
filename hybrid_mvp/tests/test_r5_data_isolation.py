from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import cemm_authoritative_hybrid.r4_partition_access as access_module
import cemm_authoritative_hybrid.training as training_module
from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_partition_access import (
    AuthenticatedClassSnapshot,
    AuthenticatedR4TrainBatch,
    PartitionAccessError,
    load_r4_train_episodes,
)
from cemm_authoritative_hybrid.r4_partition_contracts import (
    R4ClassAuthorization,
    R4ClassCapability,
    canonical_json_bytes,
)
from cemm_authoritative_hybrid.training import (
    ReleaseProposalTrainer,
    ReleaseRealizerTrainer,
)

ROOT = Path(__file__).parents[1]


__cemm_test_inventory__ = {
    "tests/test_r5_data_isolation.py::test_training_loader_accepts_only_manifest_bound_train": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-accepts-manifest-bound-train",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '5242cd921cfcd4b4b4c0d418717d55af0db93649c250a2ccbf8fb8973cc3e01d',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_validation_and_test": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-nontrain-partitions",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '294678fc73da5fdf91a108e5ffc32ef500b6fbd96747839af7d9a7b5f0b93dc8',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_copied_train_at_other_path": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-copied-train",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": 'e604ff439922d5dddef8eb274f4034f143af58d8044b2765afed4814aefcceca',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_renamed_sealed_partition": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-renamed-sealed-partition",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '4c315c6c5019b142990ba85ef9d541a3207fbb1bb50dd04499d6ce02a6c56fe3',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_arbitrary_jsonl": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-arbitrary-jsonl",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '0e04d82672c3159db1f77f79e363ec1d43ec2e88d8d856b5c9e259229878775f',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_missing_and_malformed_manifest": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-requires-strict-manifest",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": 'b41aecc2d3103f9587d50a49de9cb592b115e902c796d7ccf8eee60f739787d9',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_rejects_manifest_path_and_symlink_escape": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-rejects-path-escape",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": 'cbb16f8fe9d2817d83309b19a451cbc67eb3ccde56e33bf545601b01b08265bd',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_requires_exact_canonical_manifest_paths": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-requires-canonical-manifest-paths",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '067fe10d1fced121b89977c75dc3c9328bf5c6caa3a353375e22f9969946b3f2',
    },
    "tests/test_r5_data_isolation.py::test_training_loader_parses_authenticated_snapshot_without_second_read": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-training-loader-parses-authenticated-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '33ebdec8359a40cceee6debd3ad551867fdd25dcf0378ade61e2da760a0ca941',
    },
    "tests/test_r5_data_isolation.py::test_release_trainers_authenticate_train_once": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-trainers-authenticate-train-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '7ea3bbf756ffcc06e3ee3db0ff53d22bf5eeac7ecea4f4ee3f126f0a0c87fd58',
    },
    "tests/test_r5_data_isolation.py::test_release_trainers_reject_nontrain_before_downstream_work": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-trainers-reject-nontrain-at-loader",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": '213fe668209da77409e3788bdf497df24475be3c51e141571d9aa394893e62ad',
    },
    "tests/test_r5_data_isolation.py::test_release_trainer_metadata_uses_authenticated_fit_snapshot": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-release-trainer-metadata-binds-fit-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "data-isolation",
        "source_ast_sha256": 'dfd89a8782348873a56caa880e28c27d9dc284e8594df600b9bcee3c6c1e63cd',
    },
}


def _selected_episode() -> AuthenticEpisode:
    for line in (ROOT / "artifacts/r4/episodes.jsonl").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        episode = AuthenticEpisode.from_dict(json.loads(line))
        cycle = episode.observed_cycle
        if (
            cycle.proposal is not None
            and cycle.verification is not None
            and cycle.verification.status == "selected"
            and cycle.response_meaning is not None
        ):
            return episode
    raise AssertionError("fixture requires one selected authentic R4 episode")


def _write_r4_train_root(root: Path):
    episode = _selected_episode()
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
        "authorization": root / "artifacts/r4/authorizations/train.json",
        "capability": root / "artifacts/r4/capabilities/train.json",
        "payload": root / "artifacts/r4/splits/train.jsonl",
    }
    for key, raw in (
        ("authorization", authorization_raw),
        ("capability", capability_raw),
        ("payload", payload),
    ):
        paths[key].parent.mkdir(parents=True, exist_ok=True)
        paths[key].write_bytes(raw)
    return authorization, capability, hashlib.sha256(authorization_raw).hexdigest(), paths, payload


def _load(root: Path, authorization: R4ClassAuthorization, authorization_sha: str):
    return load_r4_train_episodes(
        "artifacts/r4/authorizations/train.json",
        "artifacts/r4/capabilities/train.json",
        root,
        expected_authorization_ref=authorization.authorization_ref,
        expected_authorization_sha256=authorization_sha,
    )


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
    authorization, capability, authorization_sha, _, _ = _write_r4_train_root(tmp_path)
    batch = _load(tmp_path, authorization, authorization_sha)
    assert len(batch.episodes) == 1
    assert batch.snapshot.capability_ref == capability.capability_ref
    assert batch.snapshot.payload_ref == capability.payload_ref


def test_training_loader_rejects_validation_and_test(tmp_path):
    authorization, _, authorization_sha, _, _ = _write_r4_train_root(tmp_path)
    for capability_path in (
        "artifacts/r4/capabilities/selection.json",
        "artifacts/r4/capabilities/frozen_test.json",
    ):
        with pytest.raises(PartitionAccessError):
            load_r4_train_episodes(
                "artifacts/r4/authorizations/train.json",
                capability_path,
                tmp_path,
                expected_authorization_ref=authorization.authorization_ref,
                expected_authorization_sha256=authorization_sha,
            )


def test_training_loader_rejects_copied_train_at_other_path(tmp_path):
    authorization, _, authorization_sha, paths, _ = _write_r4_train_root(tmp_path)
    copied = tmp_path / "copied-train-capability.json"
    shutil.copyfile(paths["capability"], copied)
    with pytest.raises(PartitionAccessError):
        load_r4_train_episodes(
            "artifacts/r4/authorizations/train.json",
            copied,
            tmp_path,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256=authorization_sha,
        )


def test_training_loader_rejects_renamed_sealed_partition(tmp_path):
    authorization, _, authorization_sha, paths, _ = _write_r4_train_root(tmp_path)
    renamed = paths["capability"].with_name("renamed-train.json")
    paths["capability"].rename(renamed)
    with pytest.raises(PartitionAccessError):
        _load(tmp_path, authorization, authorization_sha)


def test_training_loader_rejects_arbitrary_jsonl(tmp_path):
    authorization, _, authorization_sha, _, _ = _write_r4_train_root(tmp_path)
    arbitrary = tmp_path / "arbitrary.jsonl"
    arbitrary.write_text('{"episode_ref":"episode:arbitrary"}\n', encoding="utf-8")
    with pytest.raises(PartitionAccessError):
        load_r4_train_episodes(
            "artifacts/r4/authorizations/train.json",
            arbitrary,
            tmp_path,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256=authorization_sha,
        )


def test_training_loader_rejects_missing_and_malformed_manifest(tmp_path):
    authorization, _, authorization_sha, paths, _ = _write_r4_train_root(tmp_path)
    original = paths["authorization"].read_bytes()
    paths["authorization"].unlink()
    with pytest.raises(PartitionAccessError):
        _load(tmp_path, authorization, authorization_sha)
    paths["authorization"].write_bytes(b"{}\n")
    with pytest.raises(PartitionAccessError):
        _load(tmp_path, authorization, authorization_sha)
    paths["authorization"].write_bytes(b"{" * (64 * 1024 + 1))
    with pytest.raises(PartitionAccessError):
        _load(tmp_path, authorization, authorization_sha)
    paths["authorization"].write_bytes(original)


def test_training_loader_rejects_manifest_path_and_symlink_escape(tmp_path, monkeypatch):
    authorization, _, authorization_sha, paths, _ = _write_r4_train_root(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_bytes(paths["capability"].read_bytes())
    try:
        with pytest.raises(PartitionAccessError):
            load_r4_train_episodes(
                "artifacts/r4/authorizations/train.json",
                outside,
                tmp_path,
                expected_authorization_ref=authorization.authorization_ref,
                expected_authorization_sha256=authorization_sha,
            )
        original = access_module._is_link_or_reparse

        def mark_capability_as_link(path: Path) -> bool:
            return path == paths["capability"] or original(path)

        monkeypatch.setattr(access_module, "_is_link_or_reparse", mark_capability_as_link)
        with pytest.raises(PartitionAccessError, match="link/reparse"):
            _load(tmp_path, authorization, authorization_sha)
    finally:
        outside.unlink(missing_ok=True)


def test_training_loader_requires_exact_canonical_manifest_paths(tmp_path):
    authorization, _, authorization_sha, _, _ = _write_r4_train_root(tmp_path)
    for capability_path in (
        "./artifacts/r4/capabilities/train.json",
        "artifacts/r4/capabilities/../capabilities/train.json",
        "artifacts/r4/capabilities/train-copy.json",
    ):
        with pytest.raises(PartitionAccessError):
            load_r4_train_episodes(
                "artifacts/r4/authorizations/train.json",
                capability_path,
                tmp_path,
                expected_authorization_ref=authorization.authorization_ref,
                expected_authorization_sha256=authorization_sha,
            )


def test_training_loader_parses_authenticated_snapshot_without_second_read(tmp_path, monkeypatch):
    authorization, _, authorization_sha, paths, payload = _write_r4_train_root(tmp_path)
    original_read_once = access_module._read_once
    payload_reads = 0

    def mutate_after_snapshot(path: Path, *, maximum: int, label: str) -> bytes:
        nonlocal payload_reads
        raw = original_read_once(path, maximum=maximum, label=label)
        if label == "train payload":
            payload_reads += 1
            path.write_bytes(b"tampered-after-snapshot\n")
        return raw

    monkeypatch.setattr(access_module, "_read_once", mutate_after_snapshot)
    batch = _load(tmp_path, authorization, authorization_sha)
    assert payload_reads == 1
    assert batch.snapshot.payload_bytes == payload
    assert paths["payload"].read_bytes() != batch.snapshot.payload_bytes


def _authenticated_batch() -> AuthenticatedR4TrainBatch:
    for line in (ROOT / "artifacts/r4/episodes.jsonl").read_text(encoding="utf-8").splitlines():
        episode = AuthenticEpisode.from_dict(json.loads(line))
        cycle = episode.observed_cycle
        if (
            cycle.proposal is not None
            and cycle.verification is not None
            and cycle.verification.status == "selected"
            and cycle.response_meaning is not None
        ):
            raw = canonical_json_bytes(episode.as_dict())
            digest = hashlib.sha256(raw).hexdigest()
            return AuthenticatedR4TrainBatch(
                episodes=(episode,),
                snapshot=AuthenticatedClassSnapshot(
                    capability_ref="r4_class_capability_v1:test",
                    payload_ref="r4_split_payload_v1:test",
                    payload_sha256=digest,
                    payload_bytes=raw,
                    episode_count=1,
                ),
                authorization_ref="r4_class_authorization_v1:test",
                authorization_sha256="1" * 64,
                artifact_graph_ref="r4_artifact_graph_v4:test",
                generator_source_revision="a" * 40,
                authority_generation="authority:test",
            )
    raise AssertionError("fixture requires one selected authentic R4 episode")


def test_release_trainers_authenticate_train_once(tmp_path, monkeypatch):
    batch = _authenticated_batch()
    original_validate = training_module._validated_train_batch

    class LoadedEpisodes(RuntimeError):
        pass

    for trainer_type, downstream_name in (
        (ReleaseProposalTrainer, "_ActionVocabulary"),
        (ReleaseRealizerTrainer, "RealizerNetwork"),
    ):
        validation_calls = 0
        seed_calls = 0

        def counted_validate(value):
            nonlocal validation_calls
            validation_calls += 1
            return original_validate(value)

        def counted_seed(_seed):
            nonlocal seed_calls
            seed_calls += 1

        def stop_after_authenticated_batch(*_args, **_kwargs):
            raise LoadedEpisodes

        with monkeypatch.context() as context:
            context.setattr(training_module, "_validated_train_batch", counted_validate)
            context.setattr(training_module, "_set_deterministic_seeds", counted_seed)
            context.setattr(training_module, downstream_name, stop_after_authenticated_batch)
            trainer = _trainer_stopping_after_episode_load(trainer_type, tmp_path)
            with pytest.raises(LoadedEpisodes):
                trainer.fit(batch)
        assert validation_calls == 1
        assert seed_calls == 1


def test_release_trainers_reject_nontrain_before_downstream_work(tmp_path, monkeypatch):
    batch = _authenticated_batch()
    seed_calls = 0

    def counted_seed(_seed):
        nonlocal seed_calls
        seed_calls += 1

    def downstream_must_not_run(*_args, **_kwargs):
        raise AssertionError("trainer reached downstream work for unauthenticated input")

    for trainer_type, downstream_name in (
        (ReleaseProposalTrainer, "_ActionVocabulary"),
        (ReleaseRealizerTrainer, "RealizerNetwork"),
    ):
        with monkeypatch.context() as context:
            context.setattr(training_module, "_set_deterministic_seeds", counted_seed)
            context.setattr(training_module, downstream_name, downstream_must_not_run)
            trainer = _trainer_stopping_after_episode_load(trainer_type, tmp_path)
            for value in (
                ROOT / "data/partitions/train.jsonl",
                batch.snapshot,
                object(),
            ):
                with pytest.raises(TypeError):
                    trainer.fit(value)
    assert seed_calls == 0


def test_release_trainer_metadata_uses_authenticated_fit_snapshot(tmp_path, monkeypatch):
    batch = _authenticated_batch()
    expected_dataset_hash = batch.snapshot.payload_sha256

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

    expected_provenance = {
        "authorization_ref": batch.authorization_ref,
        "authorization_sha256": batch.authorization_sha256,
        "capability_ref": batch.snapshot.capability_ref,
        "payload_ref": batch.snapshot.payload_ref,
        "payload_sha256": batch.snapshot.payload_sha256,
        "episode_count": batch.snapshot.episode_count,
        "artifact_graph_ref": batch.artifact_graph_ref,
        "generator_source_revision": batch.generator_source_revision,
        "authority_generation": batch.authority_generation,
    }

    for trainer_type in (ReleaseProposalTrainer, ReleaseRealizerTrainer):
        with monkeypatch.context() as context:
            context.setattr(training_module, "_set_deterministic_seeds", lambda _seed: None)
            context.setattr(training_module.torch.optim, "Adam", FakeOptimizer)
            context.setattr(training_module, "_ActionVocabulary", FakeVocabulary)
            context.setattr(training_module, "ProposalNetwork", FakeNetwork)
            context.setattr(training_module, "RealizerNetwork", FakeNetwork)
            context.setattr(training_module, "_build_orientation", lambda *_args: object())
            context.setattr(training_module, "_encode_form_units", lambda *_args: object())
            context.setattr(training_module, "_encode_orientation_structural", lambda *_args: object())
            context.setattr(training_module, "_encode_response_meaning_features", lambda *_args: object())
            context.setattr(training_module, "_surface_to_target", lambda *_args: 0)
            context.setattr(training_module, "_compute_action_encoding_hash", lambda _index: "action:test")
            trainer = _trainer_stopping_after_episode_load(trainer_type, tmp_path)
            trainer._epochs = 0
            trainer._form_resolver = SimpleNamespace(resolve=lambda _surface: object())
            if trainer_type is ReleaseProposalTrainer:
                trainer._config = object()
            with pytest.raises(AttributeError):
                trainer.build_metadata()
            trainer.fit(batch)
            metadata = trainer.build_metadata()
            assert metadata["dataset_hash"] == expected_dataset_hash
            assert metadata["config"]["train_data"] == expected_provenance
