from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from cemm_authoritative_hybrid.artifacts import (
    ArtifactError,
    ModelMetadata,
    current_model_lock_hash,
    current_python_abi,
    load_model_artifact,
    save_model_artifact,
)
from cemm_authoritative_hybrid.canonical import (
    read_canonical_json,
    sha256_file,
    stable_ref,
    tensor_identity,
    write_canonical_json,
)


__cemm_test_inventory__ = {
    "tests/test_r5_artifact_contract.py::test_current_model_lock_hash_is_stable": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-current-model-lock-hash-is-stable",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_current_model_lock_hash_is_stable",
        "source_ast_sha256": "deba3674a729b196735b9e6e615de0085af5dab008d384c06ccad4f229e5d3b0",
    },
    "tests/test_r5_artifact_contract.py::test_current_python_abi_matches_runtime": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-current-python-abi-matches-runtime",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_current_python_abi_matches_runtime",
        "source_ast_sha256": "24e770035b92f6b602b909db7fbbf863cb31a7253028e294ddbafb9b7293f938",
    },
    "tests/test_r5_artifact_contract.py::test_identity_mismatch_fails_before_tensor_use": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-identity-mismatch-fails-before-tensor-use",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_identity_mismatch_fails_before_tensor_use",
        "source_ast_sha256": "876ed517d2f4d50c6cf87231b2633916fda0b55a38c525d8bad09c567299aa31",
    },
    "tests/test_r5_artifact_contract.py::test_manifest_tamper_fails_before_tensor_use": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-manifest-tamper-fails-before-tensor-use",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_manifest_tamper_fails_before_tensor_use",
        "source_ast_sha256": "b4eea61c4a7976201e2632942317f54daa839064dc28246b6ca12fab2183e96a",
    },
    "tests/test_r5_artifact_contract.py::test_metadata_tamper_fails_before_tensor_use": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-metadata-tamper-fails-before-tensor-use",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_metadata_tamper_fails_before_tensor_use",
        "source_ast_sha256": "288bdecbcf08afcb4992a10c8e0042c7220fbd3e2c3507ae4509a90f1992055a",
    },
    "tests/test_r5_artifact_contract.py::test_model_dependency_lock_mismatch_fails_before_tensor_use": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-model-dependency-lock-mismatch-fails-before-tensor-use",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_model_dependency_lock_mismatch_fails_before_tensor_use",
        "source_ast_sha256": "9d1d83e90386db06385e958b29bf8a72b0cca30f4c074a478978861672b866f2",
    },
    "tests/test_r5_artifact_contract.py::test_no_production_module_calls_unsafe_torch_load": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-no-production-module-calls-unsafe-torch-load",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_no_production_module_calls_unsafe_torch_load",
        "source_ast_sha256": "67022d12d54c2e00736f4460ddbb1821ecbbe2ffd8b04ab9de975a178739b767",
    },
    "tests/test_r5_artifact_contract.py::test_python_abi_mismatch_fails_before_tensor_use": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-python-abi-mismatch-fails-before-tensor-use",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_python_abi_mismatch_fails_before_tensor_use",
        "source_ast_sha256": "af88ce2a9c97a9bb6c1864b98d7ea13700f480c3511c63905c7f68c838b4233d",
    },
    "tests/test_r5_artifact_contract.py::test_safe_safetensors_load_file_is_allowed_in_source_scan": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-safe-safetensors-load-file-is-allowed-in-source-scan",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_safe_safetensors_load_file_is_allowed_in_source_scan",
        "source_ast_sha256": "fc47bf1861eb2d80cb8a4b5ef9b70a00b204b38b63b54373c9f26b81d856d80e",
    },
    "tests/test_r5_artifact_contract.py::test_tail_tamper_fails_before_tensor_use": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-tail-tamper-fails-before-tensor-use",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_tail_tamper_fails_before_tensor_use",
        "source_ast_sha256": "80ec88d115c857c4707646d32484a0b44c32d3c059b46af777f511b743aa155d",
    },
    "tests/test_r5_artifact_contract.py::test_valid_artifact_loads": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:artifact-security-valid-artifact-loads",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_artifact_security.py::test_valid_artifact_loads",
        "source_ast_sha256": "d23ceb8b558725823123a15773f52e419d62c6bbcdb173d5a7b9265192a8939d",
    },
    "tests/test_r5_artifact_contract.py::test_tensor_identity_changes_on_byte_tamper": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:canonical-tensor-identity-changes-on-byte-tamper",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_canonical.py::test_tensor_identity_changes_on_byte_tamper",
        "source_ast_sha256": "3201e3f96e582ca6d79d8d31d9b73ebbfbb886c02dfd5f05b0803a745cc1125a",
    },
    "tests/test_r5_artifact_contract.py::test_tensor_identity_changes_on_dtype": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:canonical-tensor-identity-changes-on-dtype",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_canonical.py::test_tensor_identity_changes_on_dtype",
        "source_ast_sha256": "3fbcf3a1c523c184c050541357e1c0d0ed35cfc20bc419c0a0858f71c928cb25",
    },
    "tests/test_r5_artifact_contract.py::test_tensor_identity_changes_on_shape": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:canonical-tensor-identity-changes-on-shape",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_canonical.py::test_tensor_identity_changes_on_shape",
        "source_ast_sha256": "04b08afb03777e7f848d796b851e112575367e3a89993c18ebb3d51c2543257e",
    },
    "tests/test_r5_artifact_contract.py::test_tensor_identity_is_byte_and_shape_deterministic": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:canonical-tensor-identity-is-byte-and-shape-deterministic",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "artifact-contract",
        "supersedes_node_id": "tests/test_canonical.py::test_tensor_identity_is_byte_and_shape_deterministic",
        "source_ast_sha256": "b2a4b682d2fa84163e041ad2998a98ae5d65026a2220fb56ec91cda86b721ff1",
    },
}


@pytest.fixture
def model_artifact(tmp_path: Path) -> SimpleNamespace:
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
    manifest_sha256, final = save_model_artifact(tmp_path, metadata, tensors)
    return SimpleNamespace(
        root=tmp_path,
        weights=tmp_path / "model.safetensors",
        manifest_sha256=manifest_sha256,
        metadata=final,
    )


def test_current_model_lock_hash_is_stable():
    assert len(current_model_lock_hash()) == 64
    assert current_model_lock_hash() == current_model_lock_hash()


def test_current_python_abi_matches_runtime():
    import sys

    assert current_python_abi() == f"cp{sys.version_info.major}{sys.version_info.minor}"


def test_identity_mismatch_fails_before_tensor_use(model_artifact):
    bad = asdict(model_artifact.metadata)
    bad["model_identity"] = "model:tampered0000000000000000"
    write_canonical_json(model_artifact.root / "model_metadata.json", bad)

    manifest_path = model_artifact.root / "model_manifest.json"
    manifest = read_canonical_json(manifest_path)
    manifest["metadata_sha256"] = sha256_file(
        model_artifact.root / "model_metadata.json"
    )
    write_canonical_json(manifest_path, manifest)

    with pytest.raises(ArtifactError, match="model identity"):
        load_model_artifact(model_artifact.root, sha256_file(manifest_path))


def test_manifest_tamper_fails_before_tensor_use(model_artifact):
    path = model_artifact.root / "model_manifest.json"
    payload = bytearray(path.read_bytes())
    payload[0] ^= 1
    path.write_bytes(payload)

    with pytest.raises(ArtifactError, match="manifest hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_metadata_tamper_fails_before_tensor_use(model_artifact):
    path = model_artifact.root / "model_metadata.json"
    payload = bytearray(path.read_bytes())
    payload[0] ^= 1
    path.write_bytes(payload)

    with pytest.raises(ArtifactError, match="metadata hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_model_dependency_lock_mismatch_fails_before_tensor_use(
    model_artifact, monkeypatch
):
    monkeypatch.setattr(
        "cemm_authoritative_hybrid.artifacts.current_model_lock_hash", lambda: "0" * 64
    )

    with pytest.raises(ArtifactError, match="dependency lock"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_no_production_module_calls_unsafe_torch_load():
    root = Path(__file__).parents[1] / "src" / "cemm_authoritative_hybrid"
    forbidden = ("torch.load(", "weights_only=False", "graph_action_ranker.pt")
    offenders = []
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.name}: {token}")

    assert not offenders, f"unsafe legacy loader remains: {offenders}"


def test_python_abi_mismatch_fails_before_tensor_use(model_artifact, monkeypatch):
    monkeypatch.setattr(
        "cemm_authoritative_hybrid.artifacts.current_python_abi", lambda: "cp99"
    )

    with pytest.raises(ArtifactError, match="python ABI"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_safe_safetensors_load_file_is_allowed_in_source_scan():
    root = Path(__file__).parents[1] / "src" / "cemm_authoritative_hybrid"
    allowed = ("safetensors.torch.load_file", "load_file")
    found = False
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in allowed):
            found = True
            break

    assert found, "safe safetensors load_file should be present in production modules"


def test_tail_tamper_fails_before_tensor_use(model_artifact):
    payload = bytearray(model_artifact.weights.read_bytes())
    payload[-1] ^= 1
    model_artifact.weights.write_bytes(payload)

    with pytest.raises(ArtifactError, match="weights hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)


def test_valid_artifact_loads(model_artifact):
    metadata, tensors = load_model_artifact(
        model_artifact.root, model_artifact.manifest_sha256
    )

    assert metadata.model_kind == "proposal"
    assert set(tensors) == {"weight"}
    assert tensors["weight"].shape == (2, 2)


def test_tensor_identity_changes_on_byte_tamper():
    tensor = torch.zeros(2, 2)
    original = tensor_identity({"w": tensor})
    tampered = tensor.clone()
    tampered[0, 0] = 1.0

    assert tensor_identity({"w": tampered}) != original


def test_tensor_identity_changes_on_dtype():
    assert tensor_identity({"w": torch.zeros(2, 2)}) != tensor_identity(
        {"w": torch.zeros(2, 2, dtype=torch.float64)}
    )


def test_tensor_identity_changes_on_shape():
    assert tensor_identity({"w": torch.zeros(2, 2)}) != tensor_identity(
        {"w": torch.zeros(2, 3)}
    )


def test_tensor_identity_is_byte_and_shape_deterministic():
    first = {"w": torch.zeros(2, 2), "b": torch.ones(2)}
    reordered = {"b": torch.ones(2), "w": torch.zeros(2, 2)}

    assert tensor_identity(first) == tensor_identity(reordered)
