"""Safe tensor-only model artifact contract.

This module owns :class:`ModelMetadata`, manifests, safetensors loading and
fingerprinting. No production module calls ``torch.load``; weights are loaded
exclusively via ``safetensors.torch.load_file`` after every hash, dependency
lock and Python ABI check passes.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Mapping, Literal
import json
import sys

import safetensors.torch
import torch

from .canonical import (
    canonical_bytes,
    read_canonical_json,
    sha256_file,
    stable_ref,
    tensor_identity,
    write_canonical_json,
)


__all__ = [
    "ArtifactError",
    "ModelMetadata",
    "ModelManifest",
    "current_model_lock_hash",
    "current_python_abi",
    "fingerprint_model",
    "load_model_artifact",
    "save_model_artifact",
]


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MODEL_LOCK = _PROJECT_ROOT / "requirements-model.lock"


class ArtifactError(RuntimeError):
    """Raised when a model artifact fails a hash, lock or identity check."""


@dataclass(frozen=True)
class ModelMetadata:
    model_kind: Literal["proposal", "realization", "joint"]
    model_identity: str
    authority_compatibility_hash: str
    action_encoding_hash: str
    dataset_hash: str
    model_dependency_lock_sha256: str
    python_abi: str
    source_revision: str
    abi_registry: Mapping[str, int]
    config: Mapping[str, object]


@dataclass(frozen=True)
class ModelManifest:
    metadata_sha256: str
    weights_sha256: str


def current_model_lock_hash() -> str:
    """Return the SHA-256 of the canonical model-dependency lock file."""
    return sha256_file(_MODEL_LOCK)


def current_python_abi() -> str:
    """Return the stable Python ABI tag for the running interpreter."""
    return f"cp{sys.version_info.major}{sys.version_info.minor}"


def fingerprint_model(metadata: ModelMetadata, tensors: Mapping[str, torch.Tensor]) -> str:
    """Return the stable model identity for ``metadata`` + ``tensors``.

    The identity binds the model kind, tensor bytes/shapes/dtypes, the reviewed
    authority/action/dataset hashes, the ABI registry and the ranker config. It
    deliberately excludes the dependency lock and Python ABI (those are runtime
    environment pins, not model identity) and excludes itself.
    """
    payload = {
        "model_kind": metadata.model_kind,
        "tensor_identity": tensor_identity(tensors),
        "authority_compatibility_hash": metadata.authority_compatibility_hash,
        "action_encoding_hash": metadata.action_encoding_hash,
        "dataset_hash": metadata.dataset_hash,
        "abi_registry": dict(metadata.abi_registry),
        "config": dict(metadata.config),
    }
    return stable_ref("model", payload)


def _metadata_to_dict(metadata: ModelMetadata) -> dict[str, Any]:
    return {f.name: getattr(metadata, f.name) for f in fields(metadata)}


def _metadata_from_dict(row: Mapping[str, Any]) -> ModelMetadata:
    return ModelMetadata(
        model_kind=row["model_kind"],
        model_identity=row["model_identity"],
        authority_compatibility_hash=row["authority_compatibility_hash"],
        action_encoding_hash=row["action_encoding_hash"],
        dataset_hash=row["dataset_hash"],
        model_dependency_lock_sha256=row["model_dependency_lock_sha256"],
        python_abi=row["python_abi"],
        source_revision=row["source_revision"],
        abi_registry=dict(row["abi_registry"]),
        config=dict(row["config"]),
    )


def _verify_file_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ArtifactError(f"{label} hash mismatch: expected {expected}, got {actual}")


def load_model_artifact(
    root: Path, expected_manifest_sha256: str, device: str = "cpu"
) -> tuple[ModelMetadata, dict[str, torch.Tensor]]:
    """Load and fully verify a safetensors model artifact.

    Verification order: manifest hash -> metadata hash -> weights hash ->
    dependency lock pin -> Python ABI pin -> tensor identity. Every check runs
    before tensor use where applicable; the weights hash is verified before the
    safetensors file is read.
    """
    root = Path(root)
    manifest_path = root / "model_manifest.json"
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise ArtifactError("manifest hash mismatch")

    manifest_row = read_canonical_json(manifest_path)
    manifest = ModelManifest(
        metadata_sha256=manifest_row["metadata_sha256"],
        weights_sha256=manifest_row["weights_sha256"],
    )

    _verify_file_hash(root / "model_metadata.json", manifest.metadata_sha256, "metadata")
    _verify_file_hash(root / "model.safetensors", manifest.weights_sha256, "weights")

    metadata = _metadata_from_dict(read_canonical_json(root / "model_metadata.json"))

    if metadata.model_dependency_lock_sha256 != current_model_lock_hash():
        raise ArtifactError("dependency lock mismatch")
    if metadata.python_abi != current_python_abi():
        raise ArtifactError("python ABI mismatch")

    tensors = safetensors.torch.load_file(str(root / "model.safetensors"), device=device)

    if fingerprint_model(metadata, tensors) != metadata.model_identity:
        raise ArtifactError("model identity mismatch")

    return metadata, tensors


def save_model_artifact(
    root: Path, metadata: ModelMetadata, tensors: Mapping[str, torch.Tensor]
) -> tuple[str, ModelMetadata]:
    """Write a canonical safetensors artifact under ``root``.

    Computes the real :func:`fingerprint_model` identity, writes
    ``model.safetensors``, ``model_metadata.json`` and ``model_manifest.json``,
    and returns ``(manifest_sha256, final_metadata)``.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    identity = fingerprint_model(metadata, tensors)
    final = replace(metadata, model_identity=identity)

    weights_path = root / "model.safetensors"
    # safetensors requires contiguous CPU tensors with stable dtypes.
    safe_tensors = {
        name: tensor.detach().cpu().contiguous() for name, tensor in tensors.items()
    }
    safetensors.torch.save_file(safe_tensors, str(weights_path))

    metadata_path = root / "model_metadata.json"
    write_canonical_json(metadata_path, _metadata_to_dict(final))

    manifest = ModelManifest(
        metadata_sha256=sha256_file(metadata_path),
        weights_sha256=sha256_file(weights_path),
    )
    manifest_path = root / "model_manifest.json"
    write_canonical_json(manifest_path, {
        "metadata_sha256": manifest.metadata_sha256,
        "weights_sha256": manifest.weights_sha256,
    })

    return sha256_file(manifest_path), final
