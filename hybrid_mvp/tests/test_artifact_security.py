from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.artifacts import (
    ArtifactError,
    ModelMetadata,
    current_model_lock_hash,
    current_python_abi,
    load_model_artifact,
    save_model_artifact,
)


@pytest.fixture
def model_artifact(tmp_path):
    tensors = {"weight": torch.zeros(2, 2)}
    metadata = ModelMetadata(
        model_kind="proposal",
        model_identity="",
        authority_compatibility_hash=stable_ref("authority", "test"),
        action_encoding_hash=stable_ref("action-encoding", "test"),
        dataset_hash=stable_ref("dataset", "test"),
        model_dependency_lock_sha256=current_model_lock_hash(),
        python_abi=current_python_abi(),
        source_revision="test-revision",
        abi_registry={"semantic_contribution": 1},
        config={"hidden": 4},
    )
    manifest_sha, final = save_model_artifact(tmp_path, metadata, tensors)
    return SimpleNamespace(
        root=tmp_path,
        weights=tmp_path / "model.safetensors",
        manifest_sha256=manifest_sha,
        metadata=final,
    )


def test_valid_artifact_loads(model_artifact):
    metadata, tensors = load_model_artifact(
        model_artifact.root, model_artifact.manifest_sha256
    )
    assert metadata.model_kind == "proposal"
    assert set(tensors) == {"weight"}
    assert tensors["weight"].shape == (2, 2)


def test_manifest_tamper_fails_before_tensor_use(model_artifact):
    payload = bytearray(model_artifact.root.joinpath("model_manifest.json").read_bytes())
    payload[0] ^= 1
    model_artifact.root.joinpath("model_manifest.json").write_bytes(payload)
    with pytest.raises(ArtifactError, match="manifest hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_tail_tamper_fails_before_tensor_use(model_artifact):
    payload = bytearray(model_artifact.weights.read_bytes())
    payload[-1] ^= 1
    model_artifact.weights.write_bytes(payload)
    with pytest.raises(ArtifactError, match="weights hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_metadata_tamper_fails_before_tensor_use(model_artifact):
    path = model_artifact.root / "model_metadata.json"
    payload = bytearray(path.read_bytes())
    payload[0] ^= 1
    path.write_bytes(payload)
    with pytest.raises(ArtifactError, match="metadata hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_model_dependency_lock_mismatch_fails_before_tensor_use(model_artifact, monkeypatch):
    monkeypatch.setattr(
        "cemm_authoritative_hybrid.artifacts.current_model_lock_hash", lambda: "0" * 64
    )
    with pytest.raises(ArtifactError, match="dependency lock"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_python_abi_mismatch_fails_before_tensor_use(model_artifact, monkeypatch):
    monkeypatch.setattr(
        "cemm_authoritative_hybrid.artifacts.current_python_abi", lambda: "cp99"
    )
    with pytest.raises(ArtifactError, match="python ABI"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_identity_mismatch_fails_before_tensor_use(model_artifact):
    # Rewrite metadata with a wrong identity but a correct hash chain so the
    # load reaches the identity check rather than the metadata-hash check.
    from cemm_authoritative_hybrid.canonical import write_canonical_json
    from cemm_authoritative_hybrid.artifacts import _metadata_to_dict, sha256_file
    import json

    bad = dict(_metadata_to_dict(model_artifact.metadata))
    bad["model_identity"] = "model:tampered0000000000000000"
    write_canonical_json(model_artifact.root / "model_metadata.json", bad)
    manifest_path = model_artifact.root / "model_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["metadata_sha256"] = sha256_file(model_artifact.root / "model_metadata.json")
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    new_manifest_sha = sha256_file(manifest_path)
    with pytest.raises(ArtifactError, match="model identity"):
        load_model_artifact(model_artifact.root, new_manifest_sha)


def test_current_model_lock_hash_is_stable():
    assert len(current_model_lock_hash()) == 64
    assert current_model_lock_hash() == current_model_lock_hash()


def test_current_python_abi_matches_runtime():
    import sys

    assert current_python_abi() == f"cp{sys.version_info.major}{sys.version_info.minor}"


def test_no_production_module_calls_unsafe_torch_load():
    root = Path(__file__).parents[1] / "src" / "cemm_authoritative_hybrid"
    # bootstrap.py is the legacy startup shim deferred to Task 6; it is the only
    # module still permitted to reference the retired .pt path while it awaits
    # its own rewrite. Every other production module must be free of unsafe
    # loaders.
    deferred = {"bootstrap.py"}
    forbidden = ("torch.load(", "weights_only=False", "graph_action_ranker.pt")
    offenders = []
    for path in sorted(root.glob("*.py")):
        if path.name in deferred:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.name}: {token}")
    assert not offenders, f"unsafe legacy loader remains: {offenders}"


def test_safe_safetensors_load_file_is_allowed_in_source_scan():
    root = Path(__file__).parents[1] / "src" / "cemm_authoritative_hybrid"
    allowed = ("safetensors.torch.load_file", "load_file")
    found = False
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in allowed):
            found = True
            break
    # The artifacts module must use the safe loader; this guards against the
    # source scan accidentally rejecting the canonical safe API.
    assert found, "safe safetensors load_file should be present in production modules"
