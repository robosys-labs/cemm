"""Strict train-only access to authenticated R4 class evidence.

This module is intentionally independent of training/model code.  It consumes
only the externally trusted train authorization projection, its exact train
capability, and one immutable train payload snapshot.  No global manifest,
Build Receipt, sibling capability, or legacy ``data/partitions`` authority is
accepted here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
from typing import Any

from .r4_episodes import AuthenticEpisode
from .r4_partition_contracts import (
    R4ClassAuthorization,
    R4ClassCapability,
    authenticate_class_capability,
    canonical_json_bytes,
)

__all__ = [
    "PartitionAccessError",
    "AuthenticatedClassSnapshot",
    "AuthenticatedR4TrainBatch",
    "load_r4_train_episodes",
]

_AUTHORIZATION_RELATIVE = PurePosixPath("artifacts/r4/authorizations/train.json")
_CAPABILITY_RELATIVE = PurePosixPath("artifacts/r4/capabilities/train.json")
_PAYLOAD_RELATIVE = PurePosixPath("artifacts/r4/splits/train.jsonl")
_AUTHORIZATION_MAX_BYTES = 64 * 1024
_CAPABILITY_MAX_BYTES = 64 * 1024
_PAYLOAD_MAX_BYTES = 32 * 1024 * 1024
_MAX_EPISODES = 4096
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class PartitionAccessError(ValueError):
    """Raised when train-class evidence cannot be authenticated exactly."""


@dataclass(frozen=True)
class AuthenticatedClassSnapshot:
    capability_ref: str
    payload_ref: str
    payload_sha256: str
    payload_bytes: bytes
    episode_count: int


@dataclass(frozen=True)
class AuthenticatedR4TrainBatch:
    episodes: tuple[AuthenticEpisode, ...]
    snapshot: AuthenticatedClassSnapshot
    authorization_ref: str
    authorization_sha256: str
    artifact_graph_ref: str
    generator_source_revision: str
    authority_generation: str


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PartitionAccessError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise PartitionAccessError(f"non-finite JSON constant: {value}")


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise PartitionAccessError(f"cannot inspect path component: {path}") from exc
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _WINDOWS_REPARSE_POINT)


def _assert_regular_path(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise PartitionAccessError("R4 train evidence path escapes the isolated root") from exc
    current = root
    if _is_link_or_reparse(current):
        raise PartitionAccessError("R4 train evidence root may not be a link/reparse point")
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise PartitionAccessError("R4 train evidence may not traverse a link/reparse point")
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise PartitionAccessError(f"R4 train evidence is unavailable: {path}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise PartitionAccessError("R4 train evidence must be a regular file")


def _safe_root(root: str | Path) -> Path:
    candidate = Path(root)
    try:
        absolute = candidate.absolute()
        resolved = absolute.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PartitionAccessError("R4 train evidence root is unavailable") from exc
    if absolute != resolved or not resolved.is_dir() or _is_link_or_reparse(resolved):
        raise PartitionAccessError("R4 train evidence root must be one canonical directory")
    return resolved


def _requested_path(
    value: str | Path,
    *,
    root: Path,
    expected_relative: PurePosixPath,
    label: str,
) -> Path:
    raw = os.fspath(value)
    if type(raw) is not str or not raw or "\x00" in raw:
        raise PartitionAccessError(f"{label} path must be nonempty text")
    normalized = raw.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(raw)
    expected_text = expected_relative.as_posix()
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        candidate = Path(raw).absolute()
    else:
        if normalized != expected_text:
            raise PartitionAccessError(f"{label} path must be exactly {expected_text}")
        candidate = root.joinpath(*expected_relative.parts)
    expected = root.joinpath(*expected_relative.parts)
    if candidate != expected:
        raise PartitionAccessError(f"{label} path must be exactly {expected_text}")
    _assert_regular_path(root, expected)
    return expected


def _read_once(path: Path, *, maximum: int, label: str) -> bytes:
    try:
        expected_size = path.stat(follow_symlinks=False).st_size
        if expected_size <= 0 or expected_size > maximum:
            raise PartitionAccessError(f"{label} violates byte bounds")
        with path.open("rb") as handle:
            raw = handle.read(maximum + 1)
    except PartitionAccessError:
        raise
    except OSError as exc:
        raise PartitionAccessError(f"cannot read {label}") from exc
    if len(raw) != expected_size or len(raw) > maximum:
        raise PartitionAccessError(f"{label} changed while being read")
    return raw


def _exact_sha256(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise PartitionAccessError(f"{label} must be lowercase SHA-256 hex")
    return value


def _strict_episode_payload(raw: bytes) -> tuple[AuthenticEpisode, ...]:
    if not raw.endswith(b"\n"):
        raise PartitionAccessError("R4 train payload must be LF terminated")
    lines = raw.splitlines()
    if not lines or len(lines) > _MAX_EPISODES:
        raise PartitionAccessError("R4 train payload violates episode bounds")
    episodes: list[AuthenticEpisode] = []
    canonical_lines: list[bytes] = []
    for index, line in enumerate(lines, 1):
        if not line:
            raise PartitionAccessError(f"R4 train payload contains blank line {index}")
        try:
            value = json.loads(
                line.decode("utf-8", errors="strict"),
                object_pairs_hook=_strict_pairs,
                parse_constant=_reject_nonfinite,
            )
        except PartitionAccessError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            raise PartitionAccessError(f"R4 train payload row {index} is invalid JSON") from exc
        if type(value) is not dict:
            raise PartitionAccessError(f"R4 train payload row {index} must be one object")
        canonical = canonical_json_bytes(value)[:-1]
        if line != canonical:
            raise PartitionAccessError(f"R4 train payload row {index} is not canonical JSON")
        canonical_lines.append(canonical)
        try:
            episodes.append(AuthenticEpisode.from_dict(value))
        except (TypeError, ValueError) as exc:
            raise PartitionAccessError(
                f"R4 train payload row {index} is not an authentic R4 episode"
            ) from exc
    if raw != b"\n".join(canonical_lines) + b"\n":
        raise PartitionAccessError("R4 train payload bytes are not canonical JSONL")
    refs = tuple(episode.episode_ref for episode in episodes)
    if refs != tuple(sorted(refs)) or len(refs) != len(set(refs)):
        raise PartitionAccessError("R4 train episodes must be uniquely sorted by episode_ref")
    return tuple(episodes)


def load_r4_train_episodes(
    authorization_path: str | Path,
    capability_path: str | Path,
    root: str | Path,
    *,
    expected_authorization_ref: str,
    expected_authorization_sha256: str,
) -> AuthenticatedR4TrainBatch:
    """Authenticate and return one immutable R4 train-class snapshot.

    External trust is checked from the authorization bytes before capability or
    payload access.  The function never opens a sibling split and never accepts
    legacy ``data/partitions`` paths.
    """
    canonical_root = _safe_root(root)
    authorization_file = _requested_path(
        authorization_path,
        root=canonical_root,
        expected_relative=_AUTHORIZATION_RELATIVE,
        label="train authorization",
    )
    trusted_sha = _exact_sha256(
        expected_authorization_sha256, "expected authorization SHA"
    )
    if type(expected_authorization_ref) is not str or not expected_authorization_ref:
        raise PartitionAccessError("expected authorization ref must be nonempty text")

    authorization_raw = _read_once(
        authorization_file,
        maximum=_AUTHORIZATION_MAX_BYTES,
        label="train authorization",
    )
    authorization_sha = hashlib.sha256(authorization_raw).hexdigest()
    if authorization_sha != trusted_sha:
        raise PartitionAccessError("train authorization SHA differs from admitted trust pin")
    try:
        authorization = R4ClassAuthorization.from_json_bytes(authorization_raw)
    except (TypeError, ValueError) as exc:
        raise PartitionAccessError("train authorization failed strict ABI decoding") from exc
    if authorization.authorization_ref != expected_authorization_ref:
        raise PartitionAccessError("train authorization ref differs from admitted trust pin")
    if authorization.purpose != "training":
        raise PartitionAccessError("train authorization purpose must be training")

    capability_file = _requested_path(
        capability_path,
        root=canonical_root,
        expected_relative=_CAPABILITY_RELATIVE,
        label="train capability",
    )
    capability_raw = _read_once(
        capability_file,
        maximum=_CAPABILITY_MAX_BYTES,
        label="train capability",
    )
    try:
        capability = R4ClassCapability.from_json_bytes(capability_raw)
        authenticate_class_capability(
            capability,
            authorization,
            expected_authorization_ref=expected_authorization_ref,
            expected_authorization_sha256=trusted_sha,
        )
    except (TypeError, ValueError) as exc:
        raise PartitionAccessError("train capability failed authorization") from exc
    if capability.purpose != "training" or capability.split != "train":
        raise PartitionAccessError("only the R4 training/train capability is accepted")
    if capability.payload_path != _PAYLOAD_RELATIVE.as_posix():
        raise PartitionAccessError("train capability names a non-train payload")

    payload_file = _requested_path(
        capability.payload_path,
        root=canonical_root,
        expected_relative=_PAYLOAD_RELATIVE,
        label="train payload",
    )
    payload_raw = _read_once(
        payload_file,
        maximum=_PAYLOAD_MAX_BYTES,
        label="train payload",
    )
    payload_sha = hashlib.sha256(payload_raw).hexdigest()
    if payload_sha != capability.payload_sha256:
        raise PartitionAccessError("train payload SHA differs from authenticated capability")
    episodes = _strict_episode_payload(payload_raw)
    if len(episodes) != capability.payload_count:
        raise PartitionAccessError("train payload count differs from authenticated capability")

    snapshot = AuthenticatedClassSnapshot(
        capability_ref=capability.capability_ref,
        payload_ref=capability.payload_ref,
        payload_sha256=payload_sha,
        payload_bytes=payload_raw,
        episode_count=len(episodes),
    )
    return AuthenticatedR4TrainBatch(
        episodes=episodes,
        snapshot=snapshot,
        authorization_ref=authorization.authorization_ref,
        authorization_sha256=authorization_sha,
        artifact_graph_ref=authorization.artifact_graph_ref,
        generator_source_revision=authorization.generator_source_revision,
        authority_generation=authorization.authority_generation,
    )
