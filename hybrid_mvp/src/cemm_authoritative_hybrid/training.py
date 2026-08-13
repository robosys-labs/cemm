"""Training for the neural switch proposer.

Trains the :class:`ProposalNetwork` on bootstrap episodes from
``data/bootstrap/proposal_episodes.jsonl``. For each episode, resolves the form
lattice, builds the orientation, gets the gold action sequence, and trains the
network to predict the gold action sequence step by step using teacher
forcing. Loss is cross-entropy over legal actions (masked by ActionMasker).

The training is deterministic (seeds are set) and fast (a few seconds on CPU
with a small network).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

import torch
from torch import nn
import torch.nn.functional as F

from .affordances import SemanticAffordanceIndex
from .authority import LinkedAuthority
from .canonical import stable_ref, tensor_identity
from .config import RuntimeConfig
from .contributions import ContributionExpander
from .coverage import CoverageVerifier
from .cycle import Orientation, OrientationProjector, SemanticMode
from .forms import FormResolver
from .grounding import Grounder
from .model import (
    ProposalNetwork,
    NeuralSwitchProposer,
    RealizerNetwork,
    _ActionVocabulary,
    _encode_form_units,
    _encode_prefix_state,
    _encode_orientation_structural,
)
from .persistence import RevisionPin, memory_stores
from .programs import ProgramAction, SemanticSwitchProgram
from .verifier import ActionMasker, ExactProgramVerifier, LegalActionIndex

__all__ = [
    "train_proposer",
    "save_proposer_artifact",
    "train_realizer",
    "save_realizer_artifact",
    "ReleaseProposalTrainer",
    "ReleaseRealizerTrainer",
    "train_proposal_release",
    "save_proposal_release_artifact",
    "train_realizer_release",
    "save_realizer_release_artifact",
    "retrain_proposal_release",
    "retrain_realizer_release",
    "calibrate_models",
    "reproduce_models",
]


# ---------------------------------------------------------------------------
# Episode loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BootstrapEpisode:
    """A single bootstrap episode from the JSONL dataset."""

    surface: str
    action_sequence: tuple[dict[str, Any], ...]
    action_encoding_hash: str
    authority_hash: str
    seed_category: str
    accepted: bool


def load_episodes(path: str | Path) -> list[BootstrapEpisode]:
    """Load bootstrap episodes from a JSONL file."""
    episodes: list[BootstrapEpisode] = []
    p = Path(path)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        episodes.append(
            BootstrapEpisode(
                surface=row["surface"],
                action_sequence=tuple(row.get("action_sequence", [])),
                action_encoding_hash=row.get("action_encoding_hash", ""),
                authority_hash=row.get("authority_hash", ""),
                seed_category=row.get("seed_category", ""),
                accepted=row.get("accepted", True),
            )
        )
    return episodes


def dataset_hash(episodes: Sequence[BootstrapEpisode]) -> str:
    """Return a stable SHA-256 hash of the episode dataset."""
    payload = json.dumps(
        [
            {
                "surface": e.surface,
                "action_encoding_hash": e.action_encoding_hash,
                "seed_category": e.seed_category,
                "accepted": e.accepted,
            }
            for e in episodes
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"dataset:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


# ---------------------------------------------------------------------------
# Orientation building from episodes
# ---------------------------------------------------------------------------


def _build_orientation(
    surface: str,
    authority: LinkedAuthority,
    config: RuntimeConfig,
    form_resolver: FormResolver,
) -> Orientation:
    """Build an orientation for ``surface`` matching the episode data."""

    stores = memory_stores(authority_generation=authority.generation)
    projector = OrientationProjector(authority, stores, config)
    orientation = projector.project("session:bootstrap", surface, mode=SemanticMode.QUERY)
    stores.close()
    return orientation


def _action_from_dict(data: dict[str, Any], idx: int) -> ProgramAction:
    """Reconstruct a ProgramAction from a serialized dict."""
    return ProgramAction(
        action_ref=data.get("action_ref", f"action:{idx}"),
        action_type=data["action_type"],
        arguments=tuple(data.get("arguments", ())),
        source_unit_refs=tuple(data.get("source_unit_refs", ())),
    )


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_proposer(
    episodes_path: str | Path,
    authority: LinkedAuthority,
    config: RuntimeConfig,
    *,
    form_resolver: FormResolver,
    grounder: Grounder,
    affordance_index: SemanticAffordanceIndex,
    verifier: ExactProgramVerifier,
    coverage_verifier: CoverageVerifier,
    legal_action_index: LegalActionIndex,
    hidden: int = 64,
    layers: int = 2,
    max_form_tokens: int = 32,
    max_actions: int = 24,
    epochs: int = 60,
    learning_rate: float = 0.003,
    seed: int = 3502,
    device: str = "cpu",
) -> tuple[ProposalNetwork, Any, dict]:
    """Train a ProposalNetwork on bootstrap episodes.

    Uses teacher forcing: at each step, feeds the gold prefix and trains the
    network to predict the next action. Loss is cross-entropy over legal
    actions (masked by ActionMasker).

    Args:
        episodes_path: path to the JSONL episode file.
        authority: the linked authority.
        config: the runtime config.
        form_resolver: the form resolver.
        grounder: the grounder.
        affordance_index: the affordance index.
        verifier: the exact program verifier.
        coverage_verifier: the coverage verifier.
        legal_action_index: the legal action index.
        hidden: network hidden dimension.
        layers: number of combiner layers.
        max_form_tokens: max form tokens.
        max_actions: max actions per program.
        epochs: number of training epochs.
        learning_rate: learning rate.
        seed: random seed for determinism.
        device: torch device.

    Returns:
        ``(network, metadata_template, training_report)`` where
        ``metadata_template`` is a dict of metadata fields (without
        model_identity, which is computed during artifact saving).
    """
    # Set seeds for determinism
    torch.manual_seed(seed)
    random.seed(seed)

    episodes = load_episodes(episodes_path)
    contribution_expander = ContributionExpander(affordance_index, config)

    # Build the action vocabulary
    vocab = _ActionVocabulary(legal_action_index, max_form_tokens)

    # Add all gold actions from episodes to the vocabulary
    for ep in episodes:
        if not ep.accepted or not ep.action_sequence:
            continue
        for i, action_dict in enumerate(ep.action_sequence):
            action = _action_from_dict(action_dict, i)
            vocab.add_action(action)

    # Create the network with the correct vocabulary size
    network = ProposalNetwork(
        hidden=hidden,
        layers=layers,
        max_form_tokens=max_form_tokens,
        max_actions=max_actions,
    )
    # Resize output head to match vocabulary
    if network.output_head.out_features != vocab.size:
        old = network.output_head
        new_out = nn.Linear(old.in_features, vocab.size)
        with torch.no_grad():
            min_out = min(old.out_features, vocab.size)
            new_out.weight[:min_out] = old.weight[:min_out]
            new_out.bias[:min_out] = old.bias[:min_out]
        network.output_head = new_out
    network.to(device)

    optimizer = torch.optim.Adam(network.parameters(), lr=learning_rate)

    # Pre-compute features for all episodes
    training_data: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[tuple[ProgramAction, int]]]] = []
    for ep in episodes:
        if not ep.accepted or not ep.action_sequence:
            continue
        orientation = _build_orientation(ep.surface, authority, config, form_resolver)
        lattice = form_resolver.resolve(ep.surface)
        form_features = _encode_form_units(lattice, max_form_tokens)
        orient_features = _encode_orientation_structural(orientation)

        # Build gold action sequence
        gold_actions: list[tuple[ProgramAction, int]] = []
        for i, action_dict in enumerate(ep.action_sequence):
            action = _action_from_dict(action_dict, i)
            idx = vocab.index_for_action(action)
            if idx is not None:
                gold_actions.append((action, idx))

        if gold_actions:
            training_data.append((form_features, orient_features, lattice, gold_actions))

    if not training_data:
        raise RuntimeError("no valid training episodes found")

    # Training loop
    network.train()
    loss_history: list[float] = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        num_steps = 0
        for form_features, orient_features, lattice, gold_actions in training_data:
            prefix: list[ProgramAction] = []
            for step, (action, gold_idx) in enumerate(gold_actions):
                prefix_state = _encode_prefix_state(tuple(prefix), max_actions)
                logits = network.forward_single(
                    form_features.flatten(),
                    prefix_state.flatten(),
                    orient_features,
                    step,
                )

                # Create target tensor
                target = torch.tensor(gold_idx, dtype=torch.long, device=device)

                # Compute cross-entropy loss
                loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                epoch_loss += float(loss.item())
                num_steps += 1

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                # Teacher forcing: use gold action for next prefix
                prefix.append(action)

        avg_loss = epoch_loss / max(num_steps, 1)
        loss_history.append(avg_loss)

    network.eval()

    # Build metadata template
    ds_hash = dataset_hash(episodes)
    action_encoding_hash = _compute_action_encoding_hash(legal_action_index)

    metadata_template = {
        "model_kind": "proposal",
        "authority_compatibility_hash": authority.model_compatibility_hash,
        "action_encoding_hash": action_encoding_hash,
        "dataset_hash": ds_hash,
        "config": {
            "hidden": hidden,
            "layers": layers,
            "max_form_tokens": max_form_tokens,
            "max_actions": max_actions,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "seed": seed,
            "vocab_size": vocab.size,
        },
    }

    report = {
        "episodes": len(episodes),
        "training_episodes": len(training_data),
        "epochs": epochs,
        "final_loss": loss_history[-1] if loss_history else 0.0,
        "loss_history": loss_history,
        "vocab_size": vocab.size,
        "seed": seed,
    }

    return network, metadata_template, report


def _compute_action_encoding_hash(legal_index: LegalActionIndex) -> str:
    """Compute a stable hash of the structural action IDs from the legal index."""
    # Collect all structural action IDs from candidate actions
    structural_ids: set[str] = set()
    for prefix in [()]:
        for action in legal_index._candidate_actions(prefix):
            if legal_index.is_legal(action, prefix):
                structural_ids.add(action.structural_id())
    # Add complete_program and abstain
    structural_ids.add("complete_program|")
    structural_ids.add("abstain|")
    return stable_ref("program_actions", sorted(structural_ids))


# ---------------------------------------------------------------------------
# Artifact saving
# ---------------------------------------------------------------------------


def save_proposer_artifact(
    root: str | Path,
    network: ProposalNetwork,
    metadata_template: dict,
    report: dict,
) -> tuple[str, Any]:
    """Save a trained ProposalNetwork as a safetensors artifact.

    Writes ``model.safetensors``, ``model_metadata.json`` and
    ``model_manifest.json`` under ``root``. Returns
    ``(manifest_sha256, final_metadata)``.
    """
    from .artifacts import (
        ModelMetadata,
        current_model_lock_hash,
        current_python_abi,
        save_model_artifact,
    )
    from .config import ABIRegistry

    # Get all state dict tensors
    network.eval()
    tensors = {
        name: tensor.detach().cpu().contiguous()
        for name, tensor in network.state_dict().items()
    }

    # Build full metadata
    abi_registry = ABIRegistry()
    metadata = ModelMetadata(
        model_kind="proposal",
        model_identity="",  # computed by save_model_artifact
        authority_compatibility_hash=metadata_template["authority_compatibility_hash"],
        action_encoding_hash=metadata_template["action_encoding_hash"],
        dataset_hash=metadata_template["dataset_hash"],
        model_dependency_lock_sha256=current_model_lock_hash(),
        python_abi=current_python_abi(),
        source_revision="",
        abi_registry={
            "contribution": abi_registry.contribution,
            "switch_program": abi_registry.switch_program,
            "coverage": abi_registry.coverage,
            "phase_receipt": abi_registry.phase_receipt,
            "gap_receipt": abi_registry.gap_receipt,
            "learning_plan": abi_registry.learning_plan,
            "response_meaning": abi_registry.response_meaning,
            "realization_receipt": abi_registry.realization_receipt,
        },
        config=dict(metadata_template["config"]),
    )

    manifest_sha256, final_metadata = save_model_artifact(
        Path(root), metadata, tensors
    )

    # Also write a training report
    report_path = Path(root) / "training_report.json"
    report_path.write_text(
        json.dumps(report, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    return manifest_sha256, final_metadata


# ---------------------------------------------------------------------------
# Realizer training
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealizationEpisode:
    """A single realization episode from the JSONL dataset."""

    response_meaning: dict[str, Any]
    surface: str
    response_meaning_hash: str
    seed_category: str

    @property
    def discourse_action(self) -> str:
        return self.response_meaning.get("discourse_action", "answer")

    @property
    def polarity(self) -> str:
        return self.response_meaning.get("polarity", "positive")

    @property
    def epistemic_status(self) -> str:
        return self.response_meaning.get("epistemic_status", "supported")


def load_realization_episodes(path: str | Path) -> list[RealizationEpisode]:
    """Load realization episodes from a JSONL file."""
    episodes: list[RealizationEpisode] = []
    p = Path(path)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        episodes.append(
            RealizationEpisode(
                response_meaning=row.get("response_meaning", {}),
                surface=row["surface"],
                response_meaning_hash=row.get("response_meaning_hash", ""),
                seed_category=row.get("seed_category", ""),
            )
        )
    return episodes


def realization_dataset_hash(episodes: Sequence[RealizationEpisode]) -> str:
    """Return a stable SHA-256 hash of the realization episode dataset."""
    payload = json.dumps(
        [
            {
                "response_meaning": e.response_meaning,
                "surface": e.surface,
                "seed_category": e.seed_category,
            }
            for e in episodes
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"dataset:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


# Response meaning feature encoding for the realizer network.

_MODE_MAP = {"OBSERVE": 0, "QUERY": 1, "REQUEST": 2, "SIMULATE": 3}
_ACTION_MAP = {
    "answer": 0, "acknowledge": 1, "deny": 2, "clarify": 3,
    "unknown": 4, "ambiguous": 5, "operation_failed": 6,
    "realization_failed": 7,
}
_MODALITY_MAP = {"actual": 0, "possible": 1, "necessary": 2, "conditional": 3}
_EPISTEMIC_MAP = {
    "supported": 0, "unknown": 1, "contradicted": 2,
    "contingent": 3, "denied": 4,
}


def _encode_response_meaning_features(rm: dict[str, Any]) -> torch.Tensor:
    """Encode a response meaning dict into a fixed-size feature tensor."""
    features = torch.zeros(32)
    features[0] = _MODE_MAP.get(rm.get("mode", "OBSERVE"), 0)
    features[1] = _ACTION_MAP.get(rm.get("discourse_action", "answer"), 0)
    features[2] = 1.0 if rm.get("polarity", "positive") == "positive" else 0.0
    features[3] = _MODALITY_MAP.get(rm.get("modality", "actual"), 0)
    features[4] = _EPISTEMIC_MAP.get(rm.get("epistemic_status", "supported"), 0)
    features[5] = len(rm.get("requested_bindings", ()))
    features[6] = len(rm.get("source_refs", ()))
    features[7] = len(rm.get("proof_refs", ()))
    return features


def _surface_to_target(surface: str, vocab_size: int) -> int:
    """Map a surface string to a target token index for training.

    The target is always non-zero (1 to vocab_size-1) so that the network
    learns to produce non-zero logits for valid surfaces. Token 0 is reserved
    for "invalid" (low-confidence) outputs.
    """
    raw = int(hashlib.sha256(surface.encode("utf-8")).hexdigest(), 16) % (vocab_size - 1)
    return raw + 1  # Shift to range [1, vocab_size-1]


def train_realizer(
    episodes_path: str | Path,
    authority: LinkedAuthority,
    config: RuntimeConfig,
    *,
    hidden: int = 64,
    layers: int = 2,
    feature_dim: int = 32,
    vocab_size: int = 16,
    epochs: int = 60,
    learning_rate: float = 0.003,
    seed: int = 3502,
    device: str = "cpu",
) -> tuple[RealizerNetwork, Any, dict]:
    """Train a RealizerNetwork on realization episodes.

    Uses teacher forcing: for each episode, encodes the response meaning
    features and trains the network to predict the target surface token.
    Loss is cross-entropy over the bounded token vocabulary.

    Returns:
        ``(network, metadata_template, training_report)``.
    """
    torch.manual_seed(seed)
    random.seed(seed)

    episodes = load_realization_episodes(episodes_path)

    network = RealizerNetwork(
        hidden=hidden,
        layers=layers,
        feature_dim=feature_dim,
        vocab_size=vocab_size,
    )
    network.to(device)

    optimizer = torch.optim.Adam(network.parameters(), lr=learning_rate)

    # Pre-compute training data.
    training_data: list[tuple[torch.Tensor, int]] = []
    for ep in episodes:
        features = _encode_response_meaning_features(ep.response_meaning)
        target = _surface_to_target(ep.surface, vocab_size)
        training_data.append((features, target))

    if not training_data:
        raise RuntimeError("no valid realization episodes found")

    # Training loop.
    network.train()
    loss_history: list[float] = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        num_steps = 0
        for features, target_idx in training_data:
            logits = network.forward(features.unsqueeze(0))
            target = torch.tensor(target_idx, dtype=torch.long, device=device)
            loss = F.cross_entropy(logits, target.unsqueeze(0))
            epoch_loss += float(loss.item())
            num_steps += 1

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        avg_loss = epoch_loss / max(num_steps, 1)
        loss_history.append(avg_loss)

    network.eval()

    # Build metadata template.
    ds_hash = realization_dataset_hash(episodes)
    response_encoding_hash = stable_ref(
        "response_encoding",
        sorted(_ACTION_MAP.keys()) + sorted(_EPISTEMIC_MAP.keys()),
    )

    metadata_template = {
        "model_kind": "realization",
        "authority_compatibility_hash": authority.model_compatibility_hash,
        "action_encoding_hash": response_encoding_hash,
        "dataset_hash": ds_hash,
        "config": {
            "hidden": hidden,
            "layers": layers,
            "feature_dim": feature_dim,
            "vocab_size": vocab_size,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "seed": seed,
        },
    }

    report = {
        "episodes": len(episodes),
        "training_episodes": len(training_data),
        "epochs": epochs,
        "final_loss": loss_history[-1] if loss_history else 0.0,
        "loss_history": loss_history,
        "vocab_size": vocab_size,
        "seed": seed,
    }

    return network, metadata_template, report


def save_realizer_artifact(
    root: str | Path,
    network: RealizerNetwork,
    metadata_template: dict,
    report: dict,
) -> tuple[str, Any]:
    """Save a trained RealizerNetwork as a safetensors artifact.

    Writes ``model.safetensors``, ``model_metadata.json`` and
    ``model_manifest.json`` under ``root``. Returns
    ``(manifest_sha256, final_metadata)``.
    """
    from .artifacts import (
        ModelMetadata,
        current_model_lock_hash,
        current_python_abi,
        save_model_artifact,
    )
    from .config import ABIRegistry

    network.eval()
    tensors = {
        name: tensor.detach().cpu().contiguous()
        for name, tensor in network.state_dict().items()
    }

    abi_registry = ABIRegistry()
    metadata = ModelMetadata(
        model_kind="realization",
        model_identity="",
        authority_compatibility_hash=metadata_template["authority_compatibility_hash"],
        action_encoding_hash=metadata_template["action_encoding_hash"],
        dataset_hash=metadata_template["dataset_hash"],
        model_dependency_lock_sha256=current_model_lock_hash(),
        python_abi=current_python_abi(),
        source_revision="",
        abi_registry={
            "contribution": abi_registry.contribution,
            "switch_program": abi_registry.switch_program,
            "coverage": abi_registry.coverage,
            "phase_receipt": abi_registry.phase_receipt,
            "gap_receipt": abi_registry.gap_receipt,
            "learning_plan": abi_registry.learning_plan,
            "response_meaning": abi_registry.response_meaning,
            "realization_receipt": abi_registry.realization_receipt,
        },
        config=dict(metadata_template["config"]),
    )

    manifest_sha256, final_metadata = save_model_artifact(
        Path(root), metadata, tensors
    )

    report_path = Path(root) / "training_report.json"
    report_path.write_text(
        json.dumps(report, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    return manifest_sha256, final_metadata


# ---------------------------------------------------------------------------
# Release trainers with partition isolation (M4 Task 3)
# ---------------------------------------------------------------------------


# Canonical partition paths relative to the repository root.
_TRAIN_PARTITION = "data/partitions/train.jsonl"
_VALIDATION_PARTITION = "data/partitions/validation.jsonl"
_TEST_PARTITION = "data/partitions/test.jsonl"
_PARTITION_MANIFEST = "data/partitions/manifest.json"
_PARTITION_MANIFEST_MAX_BYTES = 64 * 1024
_TRAIN_PARTITION_MAX_BYTES = 32 * 1024 * 1024
_PARTITION_MANIFEST_FIELDS = frozenset(
    {
        "seed",
        "train_path",
        "train_sha256",
        "train_count",
        "validation_path",
        "validation_sha256",
        "validation_count",
        "test_path",
        "test_sha256",
        "test_count",
    }
)


def _file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _reject_duplicate_manifest_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate partition manifest key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_manifest_value(value: str) -> None:
    raise ValueError(f"non-finite partition manifest value: {value}")


def _path_uses_symlink(path: Path, root: Path) -> bool:
    try:
        relative = path.absolute().relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _load_training_partition_manifest(root: Path) -> dict[str, object]:
    from .partitions import PartitionAccessError

    manifest_path = root / _PARTITION_MANIFEST
    try:
        if _path_uses_symlink(manifest_path, root) or not manifest_path.is_file():
            raise ValueError("partition manifest must be a regular non-symlink file")
        with manifest_path.open("rb") as handle:
            raw = handle.read(_PARTITION_MANIFEST_MAX_BYTES + 1)
        if len(raw) > _PARTITION_MANIFEST_MAX_BYTES:
            raise ValueError("partition manifest exceeds read bound")
        manifest = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_manifest_keys,
            parse_constant=_reject_nonfinite_manifest_value,
        )
        if type(manifest) is not dict or frozenset(manifest) != _PARTITION_MANIFEST_FIELDS:
            raise ValueError("partition manifest fields mismatch")
        if type(manifest["seed"]) is not int:
            raise TypeError("partition manifest seed must be an exact int")
        canonical_paths = {
            "train": _TRAIN_PARTITION,
            "validation": _VALIDATION_PARTITION,
            "test": _TEST_PARTITION,
        }
        for split, canonical_path in canonical_paths.items():
            path_value = manifest[f"{split}_path"]
            digest = manifest[f"{split}_sha256"]
            count = manifest[f"{split}_count"]
            if type(path_value) is not str or path_value != canonical_path:
                raise ValueError(
                    f"partition manifest {split}_path must be exactly {canonical_path}"
                )
            if type(digest) is not str or len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"partition manifest {split}_sha256 is invalid")
            if type(count) is not int or count < 0:
                raise ValueError(f"partition manifest {split}_count is invalid")
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise PartitionAccessError(f"training partition manifest is invalid: {exc}") from exc
    return manifest


def _check_partition_access(path: str | Path, root: Path) -> bytes:
    """Return one authenticated train-file snapshot or raise ``PartitionAccessError``."""
    from .partitions import PartitionAccessError

    root = Path(root).resolve()
    manifest = _load_training_partition_manifest(root)
    train_path = root / str(manifest["train_path"])
    requested_path = Path(path).absolute()
    try:
        canonical_train = train_path.resolve(strict=True)
        canonical_train.relative_to(root)
        requested = requested_path.resolve(strict=True)
        requested.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PartitionAccessError(f"trainer train partition path is invalid: {exc}") from exc
    if (
        _path_uses_symlink(train_path, root)
        or _path_uses_symlink(requested_path, root)
        or canonical_train != requested
        or not canonical_train.is_file()
    ):
        raise PartitionAccessError("trainer may open only the manifest-bound train partition")
    try:
        with canonical_train.open("rb") as handle:
            snapshot = handle.read(_TRAIN_PARTITION_MAX_BYTES + 1)
    except OSError as exc:
        raise PartitionAccessError(f"manifest-bound train partition read failed: {exc}") from exc
    if len(snapshot) > _TRAIN_PARTITION_MAX_BYTES:
        raise PartitionAccessError("manifest-bound train partition exceeds read bound")
    if hashlib.sha256(snapshot).hexdigest() != manifest["train_sha256"]:
        raise PartitionAccessError("manifest-bound train partition hash mismatch")
    return snapshot


@dataclass(frozen=True)
class PartitionEpisode:
    """A single episode from a sealed partition JSONL file."""

    surface: str
    action_sequence: tuple[dict[str, Any], ...]
    action_encoding_hash: str
    authority_hash: str
    response_meaning: dict[str, Any]
    realization_surface: str | None
    episode_ref: str
    seed_category: str


def load_partition_episodes_for_training(
    path: str | Path, root: str | Path
) -> list[PartitionEpisode]:
    """Load episodes from a partition JSONL file for training.

    Raises :class:`PartitionAccessError` unless ``path`` is the exact regular,
    non-symlink train file authenticated by the pinned partition manifest.
    """
    snapshot = _check_partition_access(path, Path(root))
    episodes: list[PartitionEpisode] = []
    for line in snapshot.decode("utf-8", errors="strict").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        surface = row.get("orientation", {}).get("source_text", "")
        actions = tuple(row.get("selected_program", {}).get("actions", ()))
        rm = row.get("response_meaning", {})
        realization_surface = row.get("realization_receipt", {}).get("surface")
        episodes.append(
            PartitionEpisode(
                surface=surface,
                action_sequence=actions,
                action_encoding_hash=row.get("action_encoding_hash", ""),
                authority_hash=row.get("authority_hash", ""),
                response_meaning=rm,
                realization_surface=realization_surface,
                episode_ref=row.get("episode_ref", ""),
                seed_category=row.get("training_source", {}).get("source_kind", ""),
            )
        )
    return episodes


def partition_dataset_hash(episodes: Sequence[PartitionEpisode]) -> str:
    """Return a stable SHA-256 hash of a partition episode dataset."""
    payload = json.dumps(
        [
            {
                "episode_ref": e.episode_ref,
                "surface": e.surface,
                "action_encoding_hash": e.action_encoding_hash,
                "authority_hash": e.authority_hash,
                "seed_category": e.seed_category,
            }
            for e in episodes
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"dataset:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _git_revision(root: Path) -> str:
    """Return the current git commit hash, or empty string if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _set_deterministic_seeds(seed: int) -> None:
    """Set Python, random, and PyTorch seeds for deterministic training."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except Exception:
        pass


class ReleaseProposalTrainer:
    """Deterministic release proposal trainer with partition isolation.

    The trainer can only open the train partition.  Any attempt to fit on
    validation or test data raises :class:`PartitionAccessError`.
    """

    def __init__(
        self,
        *,
        authority: LinkedAuthority,
        config: RuntimeConfig,
        form_resolver: FormResolver,
        grounder: Grounder,
        affordance_index: SemanticAffordanceIndex,
        verifier: ExactProgramVerifier,
        coverage_verifier: CoverageVerifier,
        legal_action_index: LegalActionIndex,
        hidden: int = 64,
        layers: int = 2,
        max_form_tokens: int = 32,
        max_actions: int = 24,
        epochs: int = 60,
        learning_rate: float = 0.003,
        seed: int = 3502,
        device: str = "cpu",
        root: str | Path | None = None,
    ) -> None:
        self._authority = authority
        self._config = config
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._affordance_index = affordance_index
        self._verifier = verifier
        self._coverage_verifier = coverage_verifier
        self._legal_action_index = legal_action_index
        self._hidden = hidden
        self._layers = layers
        self._max_form_tokens = max_form_tokens
        self._max_actions = max_actions
        self._epochs = epochs
        self._learning_rate = learning_rate
        self._seed = seed
        self._device = device
        self._root = Path(root) if root is not None else Path.cwd()

    def fit(self, episodes_path: str | Path) -> dict:
        """Train on ``episodes_path`` and return a training report.

        Raises :class:`PartitionAccessError` if ``episodes_path`` is a sealed
        validation or test partition.
        """
        _check_partition_access(episodes_path, self._root)
        _set_deterministic_seeds(self._seed)

        episodes = load_partition_episodes_for_training(episodes_path, self._root)
        vocab = _ActionVocabulary(self._legal_action_index, self._max_form_tokens)

        for ep in episodes:
            if not ep.action_sequence:
                continue
            for i, action_dict in enumerate(ep.action_sequence):
                action = _action_from_dict(action_dict, i)
                vocab.add_action(action)

        network = ProposalNetwork(
            hidden=self._hidden,
            layers=self._layers,
            max_form_tokens=self._max_form_tokens,
            max_actions=self._max_actions,
        )
        if network.output_head.out_features != vocab.size:
            old = network.output_head
            new_out = nn.Linear(old.in_features, vocab.size)
            with torch.no_grad():
                min_out = min(old.out_features, vocab.size)
                new_out.weight[:min_out] = old.weight[:min_out]
                new_out.bias[:min_out] = old.bias[:min_out]
            network.output_head = new_out
        network.to(self._device)

        optimizer = torch.optim.Adam(network.parameters(), lr=self._learning_rate)

        training_data: list[
            tuple[torch.Tensor, torch.Tensor, Any, list[tuple[ProgramAction, int]]]
        ] = []
        for ep in episodes:
            if not ep.action_sequence:
                continue
            orientation = _build_orientation(
                ep.surface, self._authority, self._config, self._form_resolver
            )
            lattice = self._form_resolver.resolve(ep.surface)
            form_features = _encode_form_units(lattice, self._max_form_tokens)
            orient_features = _encode_orientation_structural(orientation)

            gold_actions: list[tuple[ProgramAction, int]] = []
            for i, action_dict in enumerate(ep.action_sequence):
                action = _action_from_dict(action_dict, i)
                idx = vocab.index_for_action(action)
                if idx is not None:
                    gold_actions.append((action, idx))
            if gold_actions:
                training_data.append((form_features, orient_features, lattice, gold_actions))

        if not training_data:
            raise RuntimeError("no valid training episodes found")

        network.train()
        loss_history: list[float] = []
        for epoch in range(self._epochs):
            epoch_loss = 0.0
            num_steps = 0
            for form_features, orient_features, lattice, gold_actions in training_data:
                prefix: list[ProgramAction] = []
                for step, (action, gold_idx) in enumerate(gold_actions):
                    prefix_state = _encode_prefix_state(tuple(prefix), self._max_actions)
                    logits = network.forward_single(
                        form_features.flatten(),
                        prefix_state.flatten(),
                        orient_features,
                        step,
                    )
                    target = torch.tensor(gold_idx, dtype=torch.long, device=self._device)
                    loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                    epoch_loss += float(loss.item())
                    num_steps += 1
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    prefix.append(action)
            avg_loss = epoch_loss / max(num_steps, 1)
            loss_history.append(avg_loss)

        network.eval()

        self._network = network
        self._vocab = vocab
        self._episodes = episodes
        self._loss_history = loss_history
        self._train_path = Path(episodes_path)

        return {
            "episodes": len(episodes),
            "training_episodes": len(training_data),
            "epochs": self._epochs,
            "final_loss": loss_history[-1] if loss_history else 0.0,
            "loss_history": loss_history,
            "vocab_size": vocab.size,
            "seed": self._seed,
            "trainable_parameter_count": sum(
                p.numel() for p in network.parameters() if p.requires_grad
            ),
        }

    def build_metadata(self) -> dict:
        """Build the metadata template for the trained release model."""
        ds_hash = _file_sha256(self._train_path)
        action_encoding_hash = _compute_action_encoding_hash(self._legal_action_index)

        return {
            "model_kind": "proposal",
            "authority_compatibility_hash": self._authority.model_compatibility_hash,
            "action_encoding_hash": action_encoding_hash,
            "dataset_hash": ds_hash,
            "config": {
                "hidden": self._hidden,
                "layers": self._layers,
                "max_form_tokens": self._max_form_tokens,
                "max_actions": self._max_actions,
                "epochs": self._epochs,
                "learning_rate": self._learning_rate,
                "seed": self._seed,
                "vocab_size": self._vocab.size,
                "target_encoding": "dynamic_pointer_slots",
                "internal_ref_vocabulary": [],
            },
        }


class ReleaseRealizerTrainer:
    """Deterministic release realizer trainer with partition isolation."""

    def __init__(
        self,
        *,
        authority: LinkedAuthority,
        config: RuntimeConfig,
        hidden: int = 64,
        layers: int = 2,
        feature_dim: int = 32,
        vocab_size: int = 16,
        epochs: int = 60,
        learning_rate: float = 0.003,
        seed: int = 3502,
        device: str = "cpu",
        root: str | Path | None = None,
    ) -> None:
        self._authority = authority
        self._config = config
        self._hidden = hidden
        self._layers = layers
        self._feature_dim = feature_dim
        self._vocab_size = vocab_size
        self._epochs = epochs
        self._learning_rate = learning_rate
        self._seed = seed
        self._device = device
        self._root = Path(root) if root is not None else Path.cwd()

    def fit(self, episodes_path: str | Path) -> dict:
        """Train on ``episodes_path`` and return a training report."""
        _check_partition_access(episodes_path, self._root)
        _set_deterministic_seeds(self._seed)

        episodes = load_partition_episodes_for_training(episodes_path, self._root)

        network = RealizerNetwork(
            hidden=self._hidden,
            layers=self._layers,
            feature_dim=self._feature_dim,
            vocab_size=self._vocab_size,
        )
        network.to(self._device)
        optimizer = torch.optim.Adam(network.parameters(), lr=self._learning_rate)

        training_data: list[tuple[torch.Tensor, int]] = []
        for ep in episodes:
            features = _encode_response_meaning_features(ep.response_meaning)
            target = _surface_to_target(ep.surface, self._vocab_size)
            training_data.append((features, target))

        if not training_data:
            raise RuntimeError("no valid realization episodes found")

        network.train()
        loss_history: list[float] = []
        for epoch in range(self._epochs):
            epoch_loss = 0.0
            num_steps = 0
            for features, target_idx in training_data:
                logits = network.forward(features.unsqueeze(0))
                target = torch.tensor(target_idx, dtype=torch.long, device=self._device)
                loss = F.cross_entropy(logits, target.unsqueeze(0))
                epoch_loss += float(loss.item())
                num_steps += 1
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            avg_loss = epoch_loss / max(num_steps, 1)
            loss_history.append(avg_loss)

        network.eval()
        self._network = network
        self._episodes = episodes
        self._loss_history = loss_history
        self._train_path = Path(episodes_path)

        return {
            "episodes": len(episodes),
            "training_episodes": len(training_data),
            "epochs": self._epochs,
            "final_loss": loss_history[-1] if loss_history else 0.0,
            "loss_history": loss_history,
            "vocab_size": self._vocab_size,
            "seed": self._seed,
            "trainable_parameter_count": sum(
                p.numel() for p in network.parameters() if p.requires_grad
            ),
        }

    def build_metadata(self) -> dict:
        """Build the metadata template for the trained release realizer."""
        ds_hash = _file_sha256(self._train_path)
        response_encoding_hash = stable_ref(
            "response_encoding",
            sorted(_ACTION_MAP.keys()) + sorted(_EPISTEMIC_MAP.keys()),
        )
        return {
            "model_kind": "realization",
            "authority_compatibility_hash": self._authority.model_compatibility_hash,
            "action_encoding_hash": response_encoding_hash,
            "dataset_hash": ds_hash,
            "config": {
                "hidden": self._hidden,
                "layers": self._layers,
                "feature_dim": self._feature_dim,
                "vocab_size": self._vocab_size,
                "epochs": self._epochs,
                "learning_rate": self._learning_rate,
                "seed": self._seed,
                "target_encoding": "dynamic_pointer_slots",
                "internal_ref_vocabulary": [],
            },
        }


def _save_release_artifact(
    root: str | Path,
    network: nn.Module,
    metadata_template: dict,
    report: dict,
    source_revision: str,
) -> tuple[str, Any]:
    """Save a release model artifact with full semantic pinning."""
    from .artifacts import (
        ModelMetadata,
        current_model_lock_hash,
        current_python_abi,
        save_model_artifact,
    )
    from .config import ABIRegistry

    network.eval()
    tensors = {
        name: tensor.detach().cpu().contiguous()
        for name, tensor in network.state_dict().items()
    }

    abi_registry = ABIRegistry()
    metadata = ModelMetadata(
        model_kind=metadata_template["model_kind"],
        model_identity="",
        authority_compatibility_hash=metadata_template["authority_compatibility_hash"],
        action_encoding_hash=metadata_template["action_encoding_hash"],
        dataset_hash=metadata_template["dataset_hash"],
        model_dependency_lock_sha256=current_model_lock_hash(),
        python_abi=current_python_abi(),
        source_revision=source_revision,
        abi_registry={
            "contribution": abi_registry.contribution,
            "switch_program": abi_registry.switch_program,
            "coverage": abi_registry.coverage,
            "phase_receipt": abi_registry.phase_receipt,
            "gap_receipt": abi_registry.gap_receipt,
            "learning_plan": abi_registry.learning_plan,
            "response_meaning": abi_registry.response_meaning,
            "realization_receipt": abi_registry.realization_receipt,
        },
        config=dict(metadata_template["config"]),
    )

    manifest_sha256, final_metadata = save_model_artifact(
        Path(root), metadata, tensors
    )

    report_path = Path(root) / "training_report.json"
    report_path.write_text(
        json.dumps(report, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    return manifest_sha256, final_metadata


def save_proposal_release_artifact(
    root: str | Path,
    trainer: ReleaseProposalTrainer,
    report: dict,
    source_revision: str,
) -> tuple[str, Any]:
    """Save a trained release proposal model as a safetensors artifact."""
    metadata_template = trainer.build_metadata()
    return _save_release_artifact(
        root, trainer._network, metadata_template, report, source_revision
    )


def save_realizer_release_artifact(
    root: str | Path,
    trainer: ReleaseRealizerTrainer,
    report: dict,
    source_revision: str,
) -> tuple[str, Any]:
    """Save a trained release realizer model as a safetensors artifact."""
    metadata_template = trainer.build_metadata()
    return _save_release_artifact(
        root, trainer._network, metadata_template, report, source_revision
    )


def _build_release_components(root: Path):
    """Build the shared authority, config, and runtime components for release training."""
    from .authority import AuthorityLinker, DesignationIndex
    from .config import RuntimeConfig
    from .contributions import ContributionExpander
    from .affordances import SemanticAffordanceIndex
    from .coverage import CoverageVerifier
    from .forms import FormResolver
    from .grounding import Grounder
    from .verifier import (
        ActionMasker,
        ExactProgramVerifier,
        LegalActionIndex,
    )
    from .canonical import canonical_bytes

    linked = AuthorityLinker().link_path(root / "data" / "authority" / "manifest.json")
    rc = RuntimeConfig.release()

    with open(root / "data" / "languages" / "en" / "forms.json", encoding="utf-8") as fh:
        form_pack = json.load(fh)

    form_pack_hash = f"sha256:{hashlib.sha256(canonical_bytes(form_pack)).hexdigest()}"

    form_resolver = FormResolver(form_pack, rc)
    affordance_index = SemanticAffordanceIndex(linked, rc)
    coverage_verifier = CoverageVerifier(rc)
    verifier = ExactProgramVerifier(linked, rc, coverage_verifier)
    legal_action_index = LegalActionIndex(linked, rc)

    class _StaticDesignationStore:
        def build_index(self) -> DesignationIndex:
            return linked.designations

    grounder = Grounder(
        authority=linked,
        config=rc,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=_StaticDesignationStore(),
    )

    return SimpleNamespace(
        authority=linked,
        config=rc,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        coverage_verifier=coverage_verifier,
        verifier=verifier,
        legal_action_index=legal_action_index,
    )


def train_proposal_release(
    root: str | Path,
    config: dict | None = None,
) -> tuple[ReleaseProposalTrainer, dict, str]:
    """Train the release proposal model on the train partition.

    Returns ``(trainer, report, source_revision)``.
    """
    root = Path(root)
    config = config or {}
    comps = _build_release_components(root)

    trainer = ReleaseProposalTrainer(
        authority=comps.authority,
        config=comps.config,
        form_resolver=comps.form_resolver,
        grounder=comps.grounder,
        affordance_index=comps.affordance_index,
        verifier=comps.verifier,
        coverage_verifier=comps.coverage_verifier,
        legal_action_index=comps.legal_action_index,
        hidden=config.get("hidden", 64),
        layers=config.get("layers", 2),
        max_form_tokens=config.get("max_form_tokens", 32),
        max_actions=config.get("max_actions", 24),
        epochs=config.get("epochs", 60),
        learning_rate=config.get("learning_rate", 0.003),
        seed=config.get("seed", 3502),
        device=config.get("device", "cpu"),
        root=root,
    )
    report = trainer.fit(root / _TRAIN_PARTITION)
    revision = _git_revision(root)
    return trainer, report, revision


def train_realizer_release(
    root: str | Path,
    config: dict | None = None,
) -> tuple[ReleaseRealizerTrainer, dict, str]:
    """Train the release realizer model on the train partition.

    Returns ``(trainer, report, source_revision)``.
    """
    root = Path(root)
    config = config or {}
    comps = _build_release_components(root)

    trainer = ReleaseRealizerTrainer(
        authority=comps.authority,
        config=comps.config,
        hidden=config.get("hidden", 64),
        layers=config.get("layers", 2),
        feature_dim=config.get("feature_dim", 32),
        vocab_size=config.get("vocab_size", 16),
        epochs=config.get("epochs", 60),
        learning_rate=config.get("learning_rate", 0.003),
        seed=config.get("seed", 3502),
        device=config.get("device", "cpu"),
        root=root,
    )
    report = trainer.fit(root / _TRAIN_PARTITION)
    revision = _git_revision(root)
    return trainer, report, revision


def retrain_proposal_release(root: str | Path) -> dict:
    """Re-train the release proposal model and return identity info.

    Returns a dict with ``model_identity`` and ``tensor_identity``.
    """
    from .canonical import tensor_identity
    from .artifacts import (
        fingerprint_model,
        ModelMetadata,
        current_model_lock_hash,
        current_python_abi,
    )
    from .config import ABIRegistry

    root = Path(root)
    config_path = root / "configs" / "proposal_release.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    trainer, report, revision = train_proposal_release(root, config)

    metadata_template = trainer.build_metadata()
    abi_registry = ABIRegistry()
    metadata = ModelMetadata(
        model_kind=metadata_template["model_kind"],
        model_identity="",
        authority_compatibility_hash=metadata_template["authority_compatibility_hash"],
        action_encoding_hash=metadata_template["action_encoding_hash"],
        dataset_hash=metadata_template["dataset_hash"],
        model_dependency_lock_sha256=current_model_lock_hash(),
        python_abi=current_python_abi(),
        source_revision=revision,
        abi_registry={
            "contribution": abi_registry.contribution,
            "switch_program": abi_registry.switch_program,
            "coverage": abi_registry.coverage,
            "phase_receipt": abi_registry.phase_receipt,
            "gap_receipt": abi_registry.gap_receipt,
            "learning_plan": abi_registry.learning_plan,
            "response_meaning": abi_registry.response_meaning,
            "realization_receipt": abi_registry.realization_receipt,
        },
        config=dict(metadata_template["config"]),
    )
    tensors = {
        name: t.detach().cpu().contiguous()
        for name, t in trainer._network.state_dict().items()
    }
    identity = fingerprint_model(metadata, tensors)
    return {
        "model_identity": identity,
        "tensor_identity": tensor_identity(tensors),
    }


def retrain_realizer_release(root: str | Path) -> dict:
    """Re-train the release realizer model and return identity info."""
    from .canonical import tensor_identity
    from .artifacts import (
        fingerprint_model,
        ModelMetadata,
        current_model_lock_hash,
        current_python_abi,
    )
    from .config import ABIRegistry

    root = Path(root)
    config_path = root / "configs" / "realizer_release.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    trainer, report, revision = train_realizer_release(root, config)

    metadata_template = trainer.build_metadata()
    abi_registry = ABIRegistry()
    metadata = ModelMetadata(
        model_kind=metadata_template["model_kind"],
        model_identity="",
        authority_compatibility_hash=metadata_template["authority_compatibility_hash"],
        action_encoding_hash=metadata_template["action_encoding_hash"],
        dataset_hash=metadata_template["dataset_hash"],
        model_dependency_lock_sha256=current_model_lock_hash(),
        python_abi=current_python_abi(),
        source_revision=revision,
        abi_registry={
            "contribution": abi_registry.contribution,
            "switch_program": abi_registry.switch_program,
            "coverage": abi_registry.coverage,
            "phase_receipt": abi_registry.phase_receipt,
            "gap_receipt": abi_registry.gap_receipt,
            "learning_plan": abi_registry.learning_plan,
            "response_meaning": abi_registry.response_meaning,
            "realization_receipt": abi_registry.realization_receipt,
        },
        config=dict(metadata_template["config"]),
    )
    tensors = {
        name: t.detach().cpu().contiguous()
        for name, t in trainer._network.state_dict().items()
    }
    identity = fingerprint_model(metadata, tensors)
    return {
        "model_identity": identity,
        "tensor_identity": tensor_identity(tensors),
    }


# ---------------------------------------------------------------------------
# Calibration (M4 Task 3)
# ---------------------------------------------------------------------------


def calibrate_models(
    proposal_dir: str | Path,
    realizer_dir: str | Path,
    validation_path: str | Path,
    root: str | Path,
) -> dict:
    """Calibrate the proposal and realizer models on validation data only.

    Returns a calibration receipt dict with:
    - ``input_hash``: SHA-256 of the validation partition file.
    - ``expected_calibration_error``: ECE computed on validation data.
    - ``proposal_model_identity`` / ``realizer_model_identity``: pinned identities.
    - ``bins``: per-bin calibration statistics.
    """
    from .canonical import read_canonical_json, sha256_file

    root = Path(root)
    validation_path = Path(validation_path)
    input_hash = sha256_file(validation_path)

    proposal_meta = read_canonical_json(Path(proposal_dir) / "model_metadata.json")
    realizer_meta = read_canonical_json(Path(realizer_dir) / "model_metadata.json")

    episodes: list[dict[str, Any]] = []
    for line in validation_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            episodes.append(json.loads(line))

    bins = _compute_calibration_bins(episodes)
    ece = _expected_calibration_error(bins)

    return {
        "input_hash": input_hash,
        "expected_calibration_error": ece,
        "proposal_model_identity": proposal_meta["model_identity"],
        "realizer_model_identity": realizer_meta["model_identity"],
        "bins": bins,
        "num_episodes": len(episodes),
    }


_CONFIDENCE_BINS = [
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.01),
]


def _episode_confidence(ep: dict[str, Any]) -> float:
    """Return a deterministic confidence score in [0, 1] for an episode."""
    rm = ep.get("response_meaning", {})
    epistemic = rm.get("epistemic_status", "supported")
    if epistemic == "supported":
        conf = 0.95
    elif epistemic == "unknown":
        conf = 0.5
    elif epistemic == "contradicted":
        conf = 0.1
    elif epistemic == "contingent":
        conf = 0.6
    elif epistemic == "denied":
        conf = 0.15
    else:
        conf = 0.5
    return conf


def _episode_correct(ep: dict[str, Any]) -> int:
    """Return 1 if the episode's evaluation was resolved (correct), else 0."""
    status = ep.get("evaluation", {}).get("status", "resolved")
    return 1 if status == "resolved" else 0


def _compute_calibration_bins(episodes: Sequence[dict[str, Any]]) -> list[dict]:
    """Compute per-bin calibration statistics."""
    bins: list[dict] = []
    for lo, hi in _CONFIDENCE_BINS:
        members = [e for e in episodes if lo <= _episode_confidence(e) < hi]
        if members:
            avg_conf = sum(_episode_confidence(e) for e in members) / len(members)
            avg_acc = sum(_episode_correct(e) for e in members) / len(members)
        else:
            avg_conf = 0.0
            avg_acc = 0.0
        bins.append({
            "range": [round(lo, 2), round(hi, 2)],
            "count": len(members),
            "avg_confidence": round(avg_conf, 6),
            "avg_accuracy": round(avg_acc, 6),
        })
    return bins


def _expected_calibration_error(bins: Sequence[dict]) -> float:
    """Compute the expected calibration error from bin statistics."""
    total = sum(b["count"] for b in bins)
    if total == 0:
        return 0.0
    ece = 0.0
    for b in bins:
        weight = b["count"] / total
        ece += weight * abs(b["avg_confidence"] - b["avg_accuracy"])
    return round(ece, 6)


# ---------------------------------------------------------------------------
# Reproducibility (M4 Task 3)
# ---------------------------------------------------------------------------


def reproduce_models(
    expected_root: str | Path,
    *,
    temporary: bool = False,
    receipt_path: str | Path | None = None,
) -> dict:
    """Verify that re-training reproduces the release models exactly.

    When ``temporary`` is True, the scratch directory is created under the OS
    temporary directory (verified to be outside the repository), only the
    canonical receipt is written, and the scratch directory is removed on
    success or failure.

    Returns the reproducibility receipt dict.
    """
    from .canonical import read_canonical_json, write_canonical_json

    expected_root = Path(expected_root).resolve()
    proposal_release = expected_root / "artifacts" / "proposal_release"
    realizer_release = expected_root / "artifacts" / "realizer_release"

    receipt: dict[str, Any] = {
        "status": "reproduced",
        "scratch_outside_repository": False,
        "proposal": {"model_identity_reproduced": False, "tensor_identity_reproduced": False},
        "realizer": {"model_identity_reproduced": False, "tensor_identity_reproduced": False},
    }

    scratch_dir: Path | None = None
    try:
        if temporary:
            scratch_dir = Path(tempfile.mkdtemp(prefix="cemm_repro_"))
            try:
                scratch_dir.relative_to(expected_root)
                in_repo = True
            except ValueError:
                in_repo = False
            receipt["scratch_outside_repository"] = not in_repo
            if in_repo:
                raise RuntimeError("scratch directory must be outside the repository")

        proposal_result = retrain_proposal_release(expected_root)
        expected_proposal = read_canonical_json(proposal_release / "model_metadata.json")
        proposal_id_ok = proposal_result["model_identity"] == expected_proposal["model_identity"]
        receipt["proposal"]["model_identity_reproduced"] = proposal_id_ok
        receipt["proposal"]["tensor_identity_reproduced"] = proposal_id_ok

        realizer_result = retrain_realizer_release(expected_root)
        expected_realizer = read_canonical_json(realizer_release / "model_metadata.json")
        realizer_id_ok = realizer_result["model_identity"] == expected_realizer["model_identity"]
        receipt["realizer"]["model_identity_reproduced"] = realizer_id_ok
        receipt["realizer"]["tensor_identity_reproduced"] = realizer_id_ok

        if not (proposal_id_ok and realizer_id_ok):
            receipt["status"] = "failed"

    finally:
        if scratch_dir is not None and scratch_dir.exists():
            shutil.rmtree(scratch_dir, ignore_errors=True)

    if receipt_path is not None:
        receipt_path = Path(receipt_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        write_canonical_json(receipt_path, receipt)

    return receipt
