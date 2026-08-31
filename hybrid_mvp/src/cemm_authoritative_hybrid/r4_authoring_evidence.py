"""Pinned, non-authoritative evidence for offline R4 worksheet authoring.

This module deliberately has no network client.  It can validate a local
content-addressed snapshot and turn explicitly permitted observations into
inert suggestions; it cannot mint semantic authority or selectable gold.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Iterable, Mapping

from .canonical import canonical_json, stable_ref
from .r3_codec import exact_text

MAX_EVIDENCE_SOURCES = 64
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024
MAX_SUGGESTIONS_PER_SOURCE = 512
EVIDENCE_MANIFEST_VERSION = 1
EVIDENCE_SOURCE_FAMILIES = frozenset({"oewn", "wikidata_lexeme", "cldr"})
EVIDENCE_LICENSE_POLICIES = frozenset(
    {"suggestion_permitted", "advisory_only"}
)
_SUGGESTION_LICENSES = {
    "oewn": frozenset({"PDDL-1.0"}),
    "wikidata_lexeme": frozenset({"CC0-1.0"}),
    "cldr": frozenset({"Unicode-3.0"}),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

__all__ = [
    "EvidenceSource",
    "EvidenceSuggestion",
    "EvidenceSnapshot",
    "normalize_evidence",
    "write_evidence_snapshot",
]


def _exact_relative_path(value: object) -> str:
    path = exact_text(value, "relative_path", maximum=512)
    if "\\" in path:
        raise ValueError("relative_path must use POSIX separators")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError("relative_path must be a safe relative path")
    return path


def _exact_sha256(value: object, name: str = "sha256") -> str:
    digest = exact_text(value, name, maximum=64)
    if _SHA256.fullmatch(digest) is None:
        raise ValueError(f"{name} must be lowercase SHA-256")
    return digest


def _normalizer_source_sha256() -> str:
    return hashlib.sha256(inspect.getsource(normalize_evidence).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceSource:
    source_ref: str
    source_family: str
    revision: str
    sha256: str
    byte_length: int
    license_id: str
    license_policy: str
    relative_path: str

    @classmethod
    def create(
        cls,
        *,
        source_family: str,
        revision: str,
        sha256: str,
        byte_length: int,
        license_id: str,
        license_policy: str,
        relative_path: str,
    ) -> "EvidenceSource":
        family = exact_text(source_family, "source_family")
        if family not in EVIDENCE_SOURCE_FAMILIES:
            raise ValueError(f"unsupported evidence source family: {family}")
        policy = exact_text(license_policy, "license_policy")
        if policy not in EVIDENCE_LICENSE_POLICIES:
            raise ValueError(f"unsupported evidence license policy: {policy}")
        license_value = exact_text(license_id, "license_id")
        if (
            policy == "suggestion_permitted"
            and license_value not in _SUGGESTION_LICENSES[family]
        ):
            raise ValueError("license is not reviewed for suggestion emission")
        if type(byte_length) is not int or not 0 <= byte_length <= MAX_EVIDENCE_BYTES:
            raise ValueError("byte_length exceeds the evidence snapshot bound")
        payload = {
            "source_family": family,
            "revision": exact_text(revision, "revision"),
            "sha256": _exact_sha256(sha256),
            "byte_length": byte_length,
            "license_id": license_value,
            "license_policy": policy,
            "relative_path": _exact_relative_path(relative_path),
        }
        return cls(
            source_ref=stable_ref("evidence_source_v1", payload),
            **payload,
        )

    @classmethod
    def from_dict(cls, value: object) -> "EvidenceSource":
        if type(value) is not dict or set(value) != {
            "source_ref",
            "source_family",
            "revision",
            "sha256",
            "byte_length",
            "license_id",
            "license_policy",
            "relative_path",
        }:
            raise ValueError("evidence source has unknown or missing fields")
        rebuilt = cls.create(
            source_family=value["source_family"],
            revision=value["revision"],
            sha256=value["sha256"],
            byte_length=value["byte_length"],
            license_id=value["license_id"],
            license_policy=value["license_policy"],
            relative_path=value["relative_path"],
        )
        if rebuilt.source_ref != value["source_ref"]:
            raise ValueError("evidence source identity mismatch")
        return rebuilt

    def as_dict(self) -> dict[str, object]:
        return {
            "source_ref": self.source_ref,
            "source_family": self.source_family,
            "revision": self.revision,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "license_id": self.license_id,
            "license_policy": self.license_policy,
            "relative_path": self.relative_path,
        }


@dataclass(frozen=True)
class EvidenceSuggestion:
    suggestion_ref: str
    source_ref: str
    evidence_kind: str
    observed_form: str
    observed_sense_key: str | None
    conflict_refs: tuple[str, ...]
    selectable: bool = False


def normalize_evidence(
    source: EvidenceSource,
    observations: Iterable[Mapping[str, object]] = (),
) -> tuple[EvidenceSuggestion, ...]:
    """Normalize already-local observations into bounded inert suggestions."""

    if type(source) is not EvidenceSource:
        raise TypeError("evidence source must be exact EvidenceSource")
    if source.license_policy != "suggestion_permitted":
        return ()
    if source.license_id not in _SUGGESTION_LICENSES[source.source_family]:
        return ()
    rows: list[EvidenceSuggestion] = []
    for index, raw in enumerate(observations):
        if index >= MAX_SUGGESTIONS_PER_SOURCE:
            raise ValueError("evidence suggestion bound exceeded")
        if type(raw) is not dict or not set(raw).issubset(
            {"evidence_kind", "observed_form", "observed_sense_key", "conflict_refs"}
        ) or not {"evidence_kind", "observed_form"}.issubset(raw):
            raise ValueError("evidence observation has unknown or missing fields")
        kind = exact_text(raw["evidence_kind"], "evidence_kind")
        form = exact_text(raw["observed_form"], "observed_form", maximum=4096)
        sense_raw = raw.get("observed_sense_key")
        sense = (
            None
            if sense_raw is None
            else exact_text(sense_raw, "observed_sense_key", maximum=512)
        )
        conflicts_raw = raw.get("conflict_refs", [])
        if type(conflicts_raw) is not list or len(conflicts_raw) > 64:
            raise TypeError("conflict_refs must be a bounded exact array")
        conflicts = tuple(exact_text(ref, "conflict_ref") for ref in conflicts_raw)
        if len(conflicts) != len(set(conflicts)):
            raise ValueError("conflict_refs must be unique")
        payload = {
            "source_ref": source.source_ref,
            "evidence_kind": kind,
            "observed_form": form,
            "observed_sense_key": sense,
            "conflict_refs": conflicts,
            "selectable": False,
        }
        rows.append(
            EvidenceSuggestion(
                suggestion_ref=stable_ref("evidence_suggestion_v1", payload),
                **payload,
            )
        )
        if len({row.suggestion_ref for row in rows}) != len(rows):
            raise ValueError("evidence suggestions must be unique")
    return tuple(rows)


@dataclass(frozen=True)
class EvidenceSnapshot:
    snapshot_ref: str
    sources: tuple[EvidenceSource, ...]
    total_bytes: int

    @classmethod
    def create(cls, *, sources: tuple[EvidenceSource, ...]) -> "EvidenceSnapshot":
        if type(sources) is not tuple or len(sources) > MAX_EVIDENCE_SOURCES:
            raise ValueError("evidence snapshot may contain at most 64 sources")
        if any(type(source) is not EvidenceSource for source in sources):
            raise TypeError("snapshot sources must be exact EvidenceSource values")
        ordered = tuple(sorted(sources, key=lambda source: source.source_ref))
        if len({source.source_ref for source in ordered}) != len(ordered):
            raise ValueError("evidence source refs must be unique")
        if len({source.relative_path for source in ordered}) != len(ordered):
            raise ValueError("evidence source paths must be unique")
        total = sum(source.byte_length for source in ordered)
        if total > MAX_EVIDENCE_BYTES:
            raise ValueError("aggregate evidence byte bound exceeded")
        identity = {
            "normalizer_source_sha256": _normalizer_source_sha256(),
            "sources": [source.as_dict() for source in ordered],
            "total_bytes": total,
        }
        return cls(
            snapshot_ref=stable_ref("evidence_snapshot_v1", identity),
            sources=ordered,
            total_bytes=total,
        )

    def as_manifest(self) -> dict[str, object]:
        return {
            "manifest_version": EVIDENCE_MANIFEST_VERSION,
            "snapshot_ref": self.snapshot_ref,
            "normalizer_source_sha256": _normalizer_source_sha256(),
            "total_bytes": self.total_bytes,
            "sources": [source.as_dict() for source in self.sources],
        }

    @classmethod
    def from_directory(cls, directory: str | Path) -> "EvidenceSnapshot":
        root = Path(directory)
        if not root.is_dir() or _is_link_or_reparse(root):
            raise ValueError("evidence snapshot directory is absent or linked")
        manifest_path = root / "evidence_manifest.json"
        if not manifest_path.is_file() or _is_link_or_reparse(manifest_path):
            raise ValueError("evidence manifest is absent or linked")
        raw_manifest = manifest_path.read_bytes()
        def reject_duplicate_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate manifest key: {key}")
                result[key] = value
            return result

        try:
            manifest = json.loads(
                raw_manifest,
                object_pairs_hook=reject_duplicate_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite manifest value: {value}")
                ),
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("evidence manifest is invalid JSON") from exc
        if type(manifest) is not dict or set(manifest) != {
            "manifest_version",
            "snapshot_ref",
            "normalizer_source_sha256",
            "total_bytes",
            "sources",
        }:
            raise ValueError("evidence manifest has unknown or missing fields")
        if manifest["manifest_version"] != EVIDENCE_MANIFEST_VERSION:
            raise ValueError("unsupported evidence manifest version")
        if raw_manifest != canonical_json(manifest).encode("utf-8") + b"\n":
            raise ValueError("evidence manifest is not canonical JSON")
        if manifest["normalizer_source_sha256"] != _normalizer_source_sha256():
            raise ValueError("evidence normalizer source hash mismatch")
        rows = manifest["sources"]
        if type(rows) is not list:
            raise TypeError("evidence manifest sources must be an exact array")
        sources = tuple(EvidenceSource.from_dict(row) for row in rows)
        snapshot = cls.create(sources=sources)
        if snapshot.snapshot_ref != manifest["snapshot_ref"]:
            raise ValueError("evidence snapshot identity mismatch")
        if snapshot.total_bytes != manifest["total_bytes"]:
            raise ValueError("evidence snapshot total byte mismatch")
        root_resolved = root.resolve(strict=True)
        expected_files = {"evidence_manifest.json"}
        for source in snapshot.sources:
            path = root.joinpath(*PurePosixPath(source.relative_path).parts)
            expected_files.add(source.relative_path)
            if not path.is_file() or _path_has_link_or_reparse(root, path):
                raise ValueError("evidence source is absent or linked")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root_resolved):
                raise ValueError("evidence relative_path escapes snapshot")
            payload = path.read_bytes()
            if len(payload) != source.byte_length:
                raise ValueError("evidence source byte length mismatch")
            if hashlib.sha256(payload).hexdigest() != source.sha256:
                raise ValueError("evidence source sha256 mismatch")
        actual_files = {
            path.relative_to(root).as_posix()
            for path in _bounded_snapshot_files(root)
        }
        if actual_files != expected_files:
            raise ValueError("evidence snapshot contains unexpected files")
        return snapshot


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse = getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse)


def _path_has_link_or_reparse(root: Path, path: Path) -> bool:
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if _is_link_or_reparse(current):
            return True
    return False


def _bounded_snapshot_files(root: Path) -> tuple[Path, ...]:
    pending = [root]
    files: list[Path] = []
    entry_count = 0
    maximum_entries = MAX_EVIDENCE_SOURCES * 2 + 2
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                entry_count += 1
                if entry_count > maximum_entries:
                    raise ValueError("evidence snapshot file-count bound exceeded")
                path = Path(entry.path)
                if _is_link_or_reparse(path):
                    raise ValueError("evidence snapshot contains a linked entry")
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    raise ValueError("evidence snapshot contains a special file")
    return tuple(files)


def write_evidence_snapshot(
    directory: str | Path,
    source_payloads: tuple[tuple[EvidenceSource, bytes], ...],
) -> EvidenceSnapshot:
    """Transactionally publish one local snapshot, or accept an identical one."""

    if type(source_payloads) is not tuple:
        raise TypeError("source_payloads must be an exact tuple")
    sources = tuple(row[0] for row in source_payloads)
    snapshot = EvidenceSnapshot.create(sources=sources)
    for source, payload in source_payloads:
        if type(payload) is not bytes:
            raise TypeError("evidence payload must be exact bytes")
        if len(payload) != source.byte_length or hashlib.sha256(payload).hexdigest() != source.sha256:
            raise ValueError("evidence payload differs from source identity")
    target = Path(directory)
    if target.exists():
        existing = EvidenceSnapshot.from_directory(target)
        if existing != snapshot:
            raise FileExistsError("existing evidence snapshot is not identical")
        return existing
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=parent))
    try:
        for source, payload in source_payloads:
            destination = staging.joinpath(*PurePosixPath(source.relative_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        manifest_bytes = (
            canonical_json(snapshot.as_manifest()).encode("utf-8") + b"\n"
        )
        (staging / "evidence_manifest.json").write_bytes(manifest_bytes)
        os.replace(staging, target)
    except BaseException:
        if staging.exists():
            import shutil

            shutil.rmtree(staging)
        raise
    return EvidenceSnapshot.from_directory(target)
