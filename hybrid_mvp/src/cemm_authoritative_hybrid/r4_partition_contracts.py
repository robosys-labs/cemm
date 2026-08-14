"""Strict immutable contracts for the R4 global partition hard cut.

This module owns only serialized ABI contracts and class-scoped trust checks.
Leakage extraction, connected-component construction, assignment, feasibility,
artifact generation, and admission remain separate owners.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Any, Callable, Mapping, TypeVar

from .canonical import stable_ref
from .r3_codec import exact_bool, exact_fields, exact_int, exact_refs, exact_text, wire_refs

PARTITION_EVIDENCE_ABI_VERSION = 3
R4_SPLIT_MANIFEST_ABI_VERSION = 1
R4_PARTITION_SUFFICIENCY_ABI_VERSION = 1
R4_CLASS_CAPABILITY_ABI_VERSION = 1
R4_CLASS_AUTHORIZATION_ABI_VERSION = 1

MAX_SOURCE_EPISODES = 4_096
MAX_HYPEREDGES = 32_768
MAX_LABELS = 32_768
MAX_MEMBERS_PER_RECORD = 4_096
MAX_HYPEREDGES_PER_EPISODE = 128
MAX_LABELS_PER_EPISODE = 128
MAX_TOTAL_HYPEREDGE_MEMBERSHIPS = 131_072
MAX_TOTAL_LABEL_MEMBERSHIPS = 131_072
MAX_COMPONENTS = 4_096
MAX_EPISODE_INPUT_BYTES = 64 * 1024 * 1024
MAX_PARTITION_ARTIFACT_BYTES = 128 * 1024 * 1024

SPLITS = ("train", "selection", "calibration", "frozen_test")
PURPOSES = ("training", "selection", "calibration", "evaluation")
PURPOSE_BY_SPLIT = dict(zip(SPLITS, PURPOSES, strict=True))
AXES = (
    "general",
    "lexical",
    "semantic_target",
    "topology",
    "dialogue",
    "mutation",
    "realization",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_REVISION_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*:[^\s:][^\s]*")
_WINDOWS_DEVICE_RE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", re.IGNORECASE)

_T = TypeVar("_T")

__all__ = [
    "AXES",
    "MAX_COMPONENTS",
    "MAX_EPISODE_INPUT_BYTES",
    "MAX_HYPEREDGES",
    "MAX_HYPEREDGES_PER_EPISODE",
    "MAX_LABELS",
    "MAX_LABELS_PER_EPISODE",
    "MAX_MEMBERS_PER_RECORD",
    "MAX_PARTITION_ARTIFACT_BYTES",
    "MAX_SOURCE_EPISODES",
    "MAX_TOTAL_HYPEREDGE_MEMBERSHIPS",
    "MAX_TOTAL_LABEL_MEMBERSHIPS",
    "PARTITION_EVIDENCE_ABI_VERSION",
    "PURPOSES",
    "PURPOSE_BY_SPLIT",
    "R4_CLASS_AUTHORIZATION_ABI_VERSION",
    "R4_CLASS_CAPABILITY_ABI_VERSION",
    "R4_PARTITION_SUFFICIENCY_ABI_VERSION",
    "R4_SPLIT_MANIFEST_ABI_VERSION",
    "SPLITS",
    "LeakageHyperedge",
    "StratificationLabel",
    "GlobalPartitionComponent",
    "PartitionEvidence",
    "LabelCount",
    "SplitClassRecord",
    "R4SplitManifest",
    "ClassCount",
    "DimensionSufficiency",
    "R4PartitionSufficiencyReceipt",
    "R4ClassCapability",
    "R4ClassAuthorization",
    "artifact_graph_ref_for",
    "authenticate_class_capability",
    "canonical_json_bytes",
    "payload_ref_for",
]


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise TypeError("JSON object keys must be exact strings")
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise ValueError(f"non-finite JSON value: {value}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the one admitted canonical JSON wire representation."""
    if type(value) is not dict:
        raise TypeError("canonical JSON payload must be an exact dict")
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _strict_decode(
    raw: object,
    decoder: Callable[[Mapping[str, Any]], _T],
    *,
    maximum: int = MAX_PARTITION_ARTIFACT_BYTES,
) -> _T:
    if type(raw) is not bytes:
        raise TypeError("serialized contract must be exact bytes")
    if not raw or len(raw) > maximum:
        raise ValueError("serialized contract violates byte bounds")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("serialized contract is not strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise TypeError("serialized contract must contain one exact object")
    if raw != canonical_json_bytes(value):
        raise ValueError("serialized contract bytes are not canonical")
    return decoder(value)


def _exact_ref(value: object, name: str) -> str:
    text = exact_text(value, name)
    if _REF_RE.fullmatch(text) is None:
        raise ValueError(f"{name} is not an admitted content/reference identity")
    return text


def _exact_sha256(value: object, name: str) -> str:
    text = exact_text(value, name, maximum=64)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be lowercase SHA-256 hex")
    return text


def _exact_revision(value: object, name: str) -> str:
    text = exact_text(value, name, maximum=64)
    if _REVISION_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be a full lowercase Git object id")
    return text


def _exact_split(value: object) -> str:
    split = exact_text(value, "split", maximum=32)
    if split not in SPLITS:
        raise ValueError("unsupported R4 split")
    return split


def _exact_purpose(value: object) -> str:
    purpose = exact_text(value, "purpose", maximum=32)
    if purpose not in PURPOSES:
        raise ValueError("unsupported class capability purpose")
    return purpose


def _exact_sorted_refs(
    value: object,
    name: str,
    *,
    nonempty: bool = False,
    maximum: int = MAX_MEMBERS_PER_RECORD,
) -> tuple[str, ...]:
    refs = exact_refs(value, name, nonempty=nonempty, maximum=maximum)
    admitted = tuple(_exact_ref(ref, f"{name} item") for ref in refs)
    if admitted != tuple(sorted(admitted)):
        raise ValueError(f"{name} must be strictly sorted")
    return admitted


def _wire_sorted_refs(
    value: object,
    name: str,
    *,
    nonempty: bool = False,
    maximum: int = MAX_MEMBERS_PER_RECORD,
) -> tuple[str, ...]:
    refs = wire_refs(value, name, nonempty=nonempty, maximum=maximum)
    admitted = tuple(_exact_ref(ref, f"{name} item") for ref in refs)
    if admitted != tuple(sorted(admitted)):
        raise ValueError(f"{name} must be strictly sorted")
    return admitted


def _exact_tuple(
    value: object,
    name: str,
    expected_type: type[_T],
    *,
    nonempty: bool = False,
    maximum: int,
    key: Callable[[_T], object],
) -> tuple[_T, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    if any(type(item) is not expected_type for item in value):
        raise TypeError(f"{name} must contain exact {expected_type.__name__} values")
    rows = tuple(value)
    identities = tuple(key(item) for item in rows)
    if len(identities) != len(set(identities)):
        raise ValueError(f"{name} contains duplicate identities")
    if identities != tuple(sorted(identities)):
        raise ValueError(f"{name} must be in canonical order")
    return rows


def _wire_tuple(
    value: object,
    name: str,
    decoder: Callable[[Mapping[str, Any]], _T],
    *,
    nonempty: bool = False,
    maximum: int,
) -> tuple[_T, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    return tuple(decoder(item) for item in value)


def _payload_path(split: str, value: object) -> str:
    path = exact_text(value, "payload_path", maximum=256)
    if "\x00" in path or "\\" in path or ":" in path:
        raise ValueError("payload_path contains a forbidden path form")
    posix = PurePosixPath(path)
    windows = PureWindowsPath(path)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or windows.root
        or not posix.parts
        or any(part in {"", ".", ".."} for part in posix.parts)
        or any(_WINDOWS_DEVICE_RE.fullmatch(part.rstrip(" .")) for part in posix.parts)
    ):
        raise ValueError("payload_path is not a safe repository-relative path")
    expected = f"artifacts/r4/splits/{split}.jsonl"
    if path != expected:
        raise ValueError(f"payload_path must be exactly {expected}")
    return path


def payload_ref_for(*, split: str, payload_sha256: str, payload_count: int) -> str:
    admitted_split = _exact_split(split)
    digest = _exact_sha256(payload_sha256, "payload_sha256")
    count = exact_int(payload_count, "payload_count", minimum=1, maximum=MAX_SOURCE_EPISODES)
    return stable_ref(
        "r4_split_payload_v1",
        {"split": admitted_split, "payload_sha256": digest, "payload_count": count},
    )


def _new(cls: type[_T], **values: object) -> _T:
    obj = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(obj, name, value)
    return obj


@dataclass(frozen=True, init=False)
class LeakageHyperedge:
    axis: str
    key_namespace: str
    key_ref: str
    member_refs: tuple[str, ...]
    hyperedge_ref: str

    _FIELDS = frozenset({"axis", "key_namespace", "key_ref", "member_refs", "hyperedge_ref"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use LeakageHyperedge.create")

    @classmethod
    def create(
        cls,
        *,
        axis: str,
        key_namespace: str,
        key_ref: str,
        member_refs: tuple[str, ...],
    ) -> "LeakageHyperedge":
        axis_name = exact_text(axis, "axis", maximum=32)
        if axis_name not in AXES:
            raise ValueError("unsupported leakage axis")
        namespace = exact_text(key_namespace, "key_namespace", maximum=128)
        key_identity = _exact_ref(key_ref, "key_ref")
        members = _exact_sorted_refs(member_refs, "member_refs", nonempty=True)
        if len(members) < 2:
            raise ValueError("leakage hyperedge requires at least two members")
        material = {
            "axis": axis_name,
            "key_namespace": namespace,
            "key_ref": key_identity,
            "member_refs": list(members),
        }
        return _new(
            cls,
            axis=axis_name,
            key_namespace=namespace,
            key_ref=key_identity,
            member_refs=members,
            hyperedge_ref=stable_ref("r4_leakage_hyperedge_v3", material),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis,
            "key_namespace": self.key_namespace,
            "key_ref": self.key_ref,
            "member_refs": list(self.member_refs),
            "hyperedge_ref": self.hyperedge_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LeakageHyperedge":
        row = exact_fields(value, cls._FIELDS, "LeakageHyperedge")
        rebuilt = cls.create(
            axis=row["axis"],
            key_namespace=row["key_namespace"],
            key_ref=row["key_ref"],
            member_refs=_wire_sorted_refs(row["member_refs"], "member_refs", nonempty=True),
        )
        if rebuilt.hyperedge_ref != row["hyperedge_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical LeakageHyperedge")
        return rebuilt


@dataclass(frozen=True, init=False)
class StratificationLabel:
    namespace: str
    label_ref: str
    member_refs: tuple[str, ...]

    _FIELDS = frozenset({"namespace", "label_ref", "member_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use StratificationLabel.create")

    @classmethod
    def create(
        cls,
        *,
        namespace: str,
        member_refs: tuple[str, ...],
    ) -> "StratificationLabel":
        admitted_namespace = exact_text(namespace, "namespace", maximum=128)
        members = _exact_sorted_refs(member_refs, "member_refs", nonempty=True)
        material = {"namespace": admitted_namespace, "member_refs": list(members)}
        return _new(
            cls,
            namespace=admitted_namespace,
            label_ref=stable_ref("r4_stratification_label_v3", material),
            member_refs=members,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "label_ref": self.label_ref,
            "member_refs": list(self.member_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StratificationLabel":
        row = exact_fields(value, cls._FIELDS, "StratificationLabel")
        rebuilt = cls.create(
            namespace=row["namespace"],
            member_refs=_wire_sorted_refs(row["member_refs"], "member_refs", nonempty=True),
        )
        if rebuilt.label_ref != row["label_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical StratificationLabel")
        return rebuilt


@dataclass(frozen=True, init=False)
class GlobalPartitionComponent:
    component_ref: str
    source_set_ref: str
    partition_abi_version: int
    member_refs: tuple[str, ...]
    hyperedge_refs: tuple[str, ...]
    split: str

    _FIELDS = frozenset(
        {"component_ref", "source_set_ref", "partition_abi_version", "member_refs", "hyperedge_refs", "split"}
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use GlobalPartitionComponent.create")

    @classmethod
    def create(
        cls,
        *,
        source_set_ref: str,
        member_refs: tuple[str, ...],
        hyperedge_refs: tuple[str, ...],
        split: str,
    ) -> "GlobalPartitionComponent":
        source_identity = _exact_ref(source_set_ref, "source_set_ref")
        members = _exact_sorted_refs(member_refs, "member_refs", nonempty=True)
        hyperedges = _exact_sorted_refs(
            hyperedge_refs,
            "hyperedge_refs",
            maximum=MAX_HYPEREDGES,
        )
        admitted_split = _exact_split(split)
        material = {
            "source_set_ref": source_identity,
            "partition_abi_version": PARTITION_EVIDENCE_ABI_VERSION,
            "member_refs": list(members),
            "hyperedge_refs": list(hyperedges),
        }
        return _new(
            cls,
            component_ref=stable_ref("r4_global_partition_component_v3", material),
            source_set_ref=source_identity,
            partition_abi_version=PARTITION_EVIDENCE_ABI_VERSION,
            member_refs=members,
            hyperedge_refs=hyperedges,
            split=admitted_split,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_ref": self.component_ref,
            "source_set_ref": self.source_set_ref,
            "partition_abi_version": self.partition_abi_version,
            "member_refs": list(self.member_refs),
            "hyperedge_refs": list(self.hyperedge_refs),
            "split": self.split,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GlobalPartitionComponent":
        row = exact_fields(value, cls._FIELDS, "GlobalPartitionComponent")
        if row["partition_abi_version"] != PARTITION_EVIDENCE_ABI_VERSION:
            raise ValueError("unsupported partition component ABI")
        rebuilt = cls.create(
            source_set_ref=row["source_set_ref"],
            member_refs=_wire_sorted_refs(row["member_refs"], "member_refs", nonempty=True),
            hyperedge_refs=_wire_sorted_refs(
                row["hyperedge_refs"], "hyperedge_refs", maximum=MAX_HYPEREDGES
            ),
            split=row["split"],
        )
        if rebuilt.component_ref != row["component_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical GlobalPartitionComponent")
        return rebuilt


@dataclass(frozen=True, init=False)
class PartitionEvidence:
    abi_version: int
    evidence_ref: str
    source_set_ref: str
    config_ref: str
    hyperedges: tuple[LeakageHyperedge, ...]
    labels: tuple[StratificationLabel, ...]
    components: tuple[GlobalPartitionComponent, ...]

    _FIELDS = frozenset(
        {"abi_version", "evidence_ref", "source_set_ref", "config_ref", "hyperedges", "labels", "components"}
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use PartitionEvidence.create")

    @classmethod
    def create(
        cls,
        *,
        source_set_ref: str,
        config_ref: str,
        hyperedges: tuple[LeakageHyperedge, ...],
        labels: tuple[StratificationLabel, ...],
        components: tuple[GlobalPartitionComponent, ...],
    ) -> "PartitionEvidence":
        source_identity = _exact_ref(source_set_ref, "source_set_ref")
        config_identity = _exact_ref(config_ref, "config_ref")
        edge_rows = _exact_tuple(
            hyperedges,
            "hyperedges",
            LeakageHyperedge,
            nonempty=True,
            maximum=MAX_HYPEREDGES,
            key=lambda row: row.hyperedge_ref,
        )
        label_rows = _exact_tuple(
            labels,
            "labels",
            StratificationLabel,
            nonempty=True,
            maximum=MAX_LABELS,
            key=lambda row: row.label_ref,
        )
        component_rows = _exact_tuple(
            components,
            "components",
            GlobalPartitionComponent,
            nonempty=True,
            maximum=MAX_COMPONENTS,
            key=lambda row: row.component_ref,
        )
        if any(
            row.source_set_ref != source_identity
            or row.partition_abi_version != PARTITION_EVIDENCE_ABI_VERSION
            for row in component_rows
        ):
            raise ValueError("partition components do not bind the evidence source/ABI")

        member_owner: dict[str, str] = {}
        component_members: dict[str, frozenset[str]] = {}
        for component in component_rows:
            members = frozenset(component.member_refs)
            component_members[component.component_ref] = members
            for member in members:
                if member in member_owner:
                    raise ValueError("partition components overlap")
                member_owner[member] = component.component_ref
        if not member_owner or len(member_owner) > MAX_SOURCE_EPISODES:
            raise ValueError("partition evidence source universe violates bounds")
        expected_source = stable_ref("r4_partition_source_v3", sorted(member_owner))
        if source_identity != expected_source:
            raise ValueError("partition evidence source_set_ref mismatch")

        assigned_edges: dict[str, list[str]] = {
            component.component_ref: [] for component in component_rows
        }
        edge_memberships = 0
        for edge in edge_rows:
            edge_memberships += len(edge.member_refs)
            owner = member_owner.get(edge.member_refs[0])
            if owner is None or any(member_owner.get(member) != owner for member in edge.member_refs):
                raise ValueError("leakage hyperedge crosses or escapes components")
            assigned_edges[owner].append(edge.hyperedge_ref)
        if edge_memberships > MAX_TOTAL_HYPEREDGE_MEMBERSHIPS:
            raise ValueError("partition evidence exceeds hyperedge membership bound")
        for component in component_rows:
            if component.hyperedge_refs != tuple(sorted(assigned_edges[component.component_ref])):
                raise ValueError("component hyperedge_refs are not exact")

        label_memberships = 0
        for label in label_rows:
            label_memberships += len(label.member_refs)
            if any(member not in member_owner for member in label.member_refs):
                raise ValueError("stratification label escapes source universe")
        if label_memberships > MAX_TOTAL_LABEL_MEMBERSHIPS:
            raise ValueError("partition evidence exceeds label membership bound")

        material = {
            "abi_version": PARTITION_EVIDENCE_ABI_VERSION,
            "source_set_ref": source_identity,
            "config_ref": config_identity,
            "hyperedges": [row.as_dict() for row in edge_rows],
            "labels": [row.as_dict() for row in label_rows],
            "components": [row.as_dict() for row in component_rows],
        }
        return _new(
            cls,
            abi_version=PARTITION_EVIDENCE_ABI_VERSION,
            evidence_ref=stable_ref("r4_partition_evidence_v3", material),
            source_set_ref=source_identity,
            config_ref=config_identity,
            hyperedges=edge_rows,
            labels=label_rows,
            components=component_rows,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "evidence_ref": self.evidence_ref,
            "source_set_ref": self.source_set_ref,
            "config_ref": self.config_ref,
            "hyperedges": [row.as_dict() for row in self.hyperedges],
            "labels": [row.as_dict() for row in self.labels],
            "components": [row.as_dict() for row in self.components],
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PartitionEvidence":
        row = exact_fields(value, cls._FIELDS, "PartitionEvidence")
        if row["abi_version"] != PARTITION_EVIDENCE_ABI_VERSION:
            raise ValueError("unsupported Partition Evidence ABI")
        rebuilt = cls.create(
            source_set_ref=row["source_set_ref"],
            config_ref=row["config_ref"],
            hyperedges=_wire_tuple(
                row["hyperedges"],
                "hyperedges",
                LeakageHyperedge.from_dict,
                nonempty=True,
                maximum=MAX_HYPEREDGES,
            ),
            labels=_wire_tuple(
                row["labels"],
                "labels",
                StratificationLabel.from_dict,
                nonempty=True,
                maximum=MAX_LABELS,
            ),
            components=_wire_tuple(
                row["components"],
                "components",
                GlobalPartitionComponent.from_dict,
                nonempty=True,
                maximum=MAX_COMPONENTS,
            ),
        )
        if rebuilt.evidence_ref != row["evidence_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical PartitionEvidence")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "PartitionEvidence":
        return _strict_decode(raw, cls.from_dict)


@dataclass(frozen=True, init=False)
class LabelCount:
    label_ref: str
    count: int

    _FIELDS = frozenset({"label_ref", "count"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use LabelCount.create")

    @classmethod
    def create(cls, *, label_ref: str, count: int) -> "LabelCount":
        return _new(
            cls,
            label_ref=_exact_ref(label_ref, "label_ref"),
            count=exact_int(count, "count", minimum=1, maximum=MAX_SOURCE_EPISODES),
        )

    def as_dict(self) -> dict[str, Any]:
        return {"label_ref": self.label_ref, "count": self.count}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LabelCount":
        row = exact_fields(value, cls._FIELDS, "LabelCount")
        rebuilt = cls.create(label_ref=row["label_ref"], count=row["count"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical LabelCount")
        return rebuilt


@dataclass(frozen=True, init=False)
class SplitClassRecord:
    split: str
    purpose: str
    payload_path: str
    payload_ref: str
    payload_sha256: str
    payload_count: int
    member_refs: tuple[str, ...]
    component_refs: tuple[str, ...]
    label_counts: tuple[LabelCount, ...]

    _FIELDS = frozenset(
        {
            "split",
            "purpose",
            "payload_path",
            "payload_ref",
            "payload_sha256",
            "payload_count",
            "member_refs",
            "component_refs",
            "label_counts",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use SplitClassRecord.create")

    @classmethod
    def create(
        cls,
        *,
        split: str,
        purpose: str,
        payload_path: str,
        payload_sha256: str,
        payload_count: int,
        member_refs: tuple[str, ...],
        component_refs: tuple[str, ...],
        label_counts: tuple[LabelCount, ...],
    ) -> "SplitClassRecord":
        admitted_split = _exact_split(split)
        admitted_purpose = _exact_purpose(purpose)
        if PURPOSE_BY_SPLIT[admitted_split] != admitted_purpose:
            raise ValueError("purpose/split pairing is not admitted")
        members = _exact_sorted_refs(member_refs, "member_refs", nonempty=True)
        components = _exact_sorted_refs(
            component_refs, "component_refs", nonempty=True, maximum=MAX_COMPONENTS
        )
        labels = _exact_tuple(
            label_counts,
            "label_counts",
            LabelCount,
            maximum=MAX_LABELS,
            key=lambda row: row.label_ref,
        )
        count = exact_int(
            payload_count, "payload_count", minimum=1, maximum=MAX_SOURCE_EPISODES
        )
        if count != len(members):
            raise ValueError("payload_count does not match exact member_refs")
        digest = _exact_sha256(payload_sha256, "payload_sha256")
        return _new(
            cls,
            split=admitted_split,
            purpose=admitted_purpose,
            payload_path=_payload_path(admitted_split, payload_path),
            payload_ref=payload_ref_for(
                split=admitted_split, payload_sha256=digest, payload_count=count
            ),
            payload_sha256=digest,
            payload_count=count,
            member_refs=members,
            component_refs=components,
            label_counts=labels,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "split": self.split,
            "purpose": self.purpose,
            "payload_path": self.payload_path,
            "payload_ref": self.payload_ref,
            "payload_sha256": self.payload_sha256,
            "payload_count": self.payload_count,
            "member_refs": list(self.member_refs),
            "component_refs": list(self.component_refs),
            "label_counts": [row.as_dict() for row in self.label_counts],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SplitClassRecord":
        row = exact_fields(value, cls._FIELDS, "SplitClassRecord")
        rebuilt = cls.create(
            split=row["split"],
            purpose=row["purpose"],
            payload_path=row["payload_path"],
            payload_sha256=row["payload_sha256"],
            payload_count=row["payload_count"],
            member_refs=_wire_sorted_refs(row["member_refs"], "member_refs", nonempty=True),
            component_refs=_wire_sorted_refs(
                row["component_refs"], "component_refs", nonempty=True, maximum=MAX_COMPONENTS
            ),
            label_counts=_wire_tuple(
                row["label_counts"], "label_counts", LabelCount.from_dict, maximum=MAX_LABELS
            ),
        )
        if rebuilt.payload_ref != row["payload_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical SplitClassRecord")
        return rebuilt


@dataclass(frozen=True, init=False)
class R4SplitManifest:
    abi_version: int
    manifest_ref: str
    source_set_ref: str
    generator_source_revision: str
    authority_generation: str
    config_ref: str
    partition_evidence_ref: str
    partition_sufficiency_ref: str
    classes: tuple[SplitClassRecord, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "manifest_ref",
            "source_set_ref",
            "generator_source_revision",
            "authority_generation",
            "config_ref",
            "partition_evidence_ref",
            "partition_sufficiency_ref",
            "classes",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use R4SplitManifest.create")

    @classmethod
    def create(
        cls,
        *,
        source_set_ref: str,
        generator_source_revision: str,
        authority_generation: str,
        config_ref: str,
        partition_evidence_ref: str,
        partition_sufficiency_ref: str,
        classes: tuple[SplitClassRecord, ...],
    ) -> "R4SplitManifest":
        class_rows = _exact_tuple(
            classes,
            "classes",
            SplitClassRecord,
            nonempty=True,
            maximum=len(SPLITS),
            key=lambda row: SPLITS.index(row.split),
        )
        if tuple(row.split for row in class_rows) != SPLITS:
            raise ValueError("split manifest requires exactly four canonical classes")
        members: list[str] = []
        components: list[str] = []
        for row in class_rows:
            members.extend(row.member_refs)
            components.extend(row.component_refs)
        if len(members) != len(set(members)) or len(components) != len(set(components)):
            raise ValueError("split manifest classes overlap")
        if not members or len(members) > MAX_SOURCE_EPISODES:
            raise ValueError("split manifest source universe violates bounds")
        source_identity = _exact_ref(source_set_ref, "source_set_ref")
        if source_identity != stable_ref("r4_partition_source_v3", sorted(members)):
            raise ValueError("split manifest source_set_ref mismatch")
        material = {
            "abi_version": R4_SPLIT_MANIFEST_ABI_VERSION,
            "source_set_ref": source_identity,
            "generator_source_revision": _exact_revision(
                generator_source_revision, "generator_source_revision"
            ),
            "authority_generation": _exact_ref(
                authority_generation, "authority_generation"
            ),
            "config_ref": _exact_ref(config_ref, "config_ref"),
            "partition_evidence_ref": _exact_ref(
                partition_evidence_ref, "partition_evidence_ref"
            ),
            "partition_sufficiency_ref": _exact_ref(
                partition_sufficiency_ref, "partition_sufficiency_ref"
            ),
            "classes": [row.as_dict() for row in class_rows],
        }
        return _new(
            cls,
            abi_version=R4_SPLIT_MANIFEST_ABI_VERSION,
            manifest_ref=stable_ref("r4_split_manifest_v1", material),
            source_set_ref=source_identity,
            generator_source_revision=material["generator_source_revision"],
            authority_generation=material["authority_generation"],
            config_ref=material["config_ref"],
            partition_evidence_ref=material["partition_evidence_ref"],
            partition_sufficiency_ref=material["partition_sufficiency_ref"],
            classes=class_rows,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "manifest_ref": self.manifest_ref,
            "source_set_ref": self.source_set_ref,
            "generator_source_revision": self.generator_source_revision,
            "authority_generation": self.authority_generation,
            "config_ref": self.config_ref,
            "partition_evidence_ref": self.partition_evidence_ref,
            "partition_sufficiency_ref": self.partition_sufficiency_ref,
            "classes": [row.as_dict() for row in self.classes],
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4SplitManifest":
        row = exact_fields(value, cls._FIELDS, "R4SplitManifest")
        if row["abi_version"] != R4_SPLIT_MANIFEST_ABI_VERSION:
            raise ValueError("unsupported R4 Split Manifest ABI")
        rebuilt = cls.create(
            source_set_ref=row["source_set_ref"],
            generator_source_revision=row["generator_source_revision"],
            authority_generation=row["authority_generation"],
            config_ref=row["config_ref"],
            partition_evidence_ref=row["partition_evidence_ref"],
            partition_sufficiency_ref=row["partition_sufficiency_ref"],
            classes=_wire_tuple(
                row["classes"],
                "classes",
                SplitClassRecord.from_dict,
                nonempty=True,
                maximum=len(SPLITS),
            ),
        )
        if rebuilt.manifest_ref != row["manifest_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4SplitManifest")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4SplitManifest":
        return _strict_decode(raw, cls.from_dict)


@dataclass(frozen=True, init=False)
class ClassCount:
    split: str
    source_count: int
    component_count: int

    _FIELDS = frozenset({"split", "source_count", "component_count"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use ClassCount.create")

    @classmethod
    def create(cls, *, split: str, source_count: int, component_count: int) -> "ClassCount":
        return _new(
            cls,
            split=_exact_split(split),
            source_count=exact_int(
                source_count, "source_count", minimum=1, maximum=MAX_SOURCE_EPISODES
            ),
            component_count=exact_int(
                component_count, "component_count", minimum=1, maximum=MAX_COMPONENTS
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "split": self.split,
            "source_count": self.source_count,
            "component_count": self.component_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ClassCount":
        row = exact_fields(value, cls._FIELDS, "ClassCount")
        rebuilt = cls.create(
            split=row["split"],
            source_count=row["source_count"],
            component_count=row["component_count"],
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ClassCount")
        return rebuilt


@dataclass(frozen=True, init=False)
class DimensionSufficiency:
    dimension_ref: str
    split: str
    source_support: int
    feasible_component_support: int
    observed_support: int
    minimum: int
    maximum: int
    passed: bool
    infeasibility_reason: str

    _FIELDS = frozenset(
        {
            "dimension_ref",
            "split",
            "source_support",
            "feasible_component_support",
            "observed_support",
            "minimum",
            "maximum",
            "passed",
            "infeasibility_reason",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use DimensionSufficiency.create")

    @classmethod
    def create(
        cls,
        *,
        dimension_ref: str,
        split: str,
        source_support: int,
        feasible_component_support: int,
        observed_support: int,
        minimum: int,
        maximum: int,
        passed: bool,
        infeasibility_reason: str,
    ) -> "DimensionSufficiency":
        source = exact_int(
            source_support, "source_support", minimum=1, maximum=MAX_SOURCE_EPISODES
        )
        feasible = exact_int(
            feasible_component_support,
            "feasible_component_support",
            minimum=1,
            maximum=MAX_COMPONENTS,
        )
        observed = exact_int(
            observed_support, "observed_support", minimum=0, maximum=MAX_SOURCE_EPISODES
        )
        lower = exact_int(minimum, "minimum", minimum=1, maximum=MAX_SOURCE_EPISODES)
        upper = exact_int(maximum, "maximum", minimum=1, maximum=MAX_SOURCE_EPISODES)
        if lower > upper or upper > source or observed > source:
            raise ValueError("dimension sufficiency counts are inconsistent")
        admitted_passed = exact_bool(passed, "passed")
        expected_passed = lower <= observed <= upper
        if admitted_passed != expected_passed:
            raise ValueError("dimension sufficiency passed flag is not reconstructible")
        reason = exact_text(
            infeasibility_reason,
            "infeasibility_reason",
            allow_empty=True,
            maximum=512,
        )
        if admitted_passed and reason:
            raise ValueError("passed dimension cannot carry an infeasibility reason")
        if not admitted_passed and not reason:
            raise ValueError("failed dimension requires an infeasibility reason")
        return _new(
            cls,
            dimension_ref=_exact_ref(dimension_ref, "dimension_ref"),
            split=_exact_split(split),
            source_support=source,
            feasible_component_support=feasible,
            observed_support=observed,
            minimum=lower,
            maximum=upper,
            passed=admitted_passed,
            infeasibility_reason=reason,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension_ref": self.dimension_ref,
            "split": self.split,
            "source_support": self.source_support,
            "feasible_component_support": self.feasible_component_support,
            "observed_support": self.observed_support,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "passed": self.passed,
            "infeasibility_reason": self.infeasibility_reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DimensionSufficiency":
        row = exact_fields(value, cls._FIELDS, "DimensionSufficiency")
        rebuilt = cls.create(**row)
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DimensionSufficiency")
        return rebuilt


@dataclass(frozen=True, init=False)
class R4PartitionSufficiencyReceipt:
    abi_version: int
    receipt_ref: str
    passed: bool
    class_counts: tuple[ClassCount, ...]
    dimension_rows: tuple[DimensionSufficiency, ...]

    _FIELDS = frozenset({"abi_version", "receipt_ref", "passed", "class_counts", "dimension_rows"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use R4PartitionSufficiencyReceipt.create")

    @classmethod
    def create(
        cls,
        *,
        passed: bool,
        class_counts: tuple[ClassCount, ...],
        dimension_rows: tuple[DimensionSufficiency, ...],
    ) -> "R4PartitionSufficiencyReceipt":
        counts = _exact_tuple(
            class_counts,
            "class_counts",
            ClassCount,
            nonempty=True,
            maximum=len(SPLITS),
            key=lambda row: SPLITS.index(row.split),
        )
        if tuple(row.split for row in counts) != SPLITS:
            raise ValueError("sufficiency receipt requires exactly four nonempty classes")
        rows = _exact_tuple(
            dimension_rows,
            "dimension_rows",
            DimensionSufficiency,
            nonempty=True,
            maximum=MAX_LABELS * len(SPLITS),
            key=lambda row: (row.dimension_ref, SPLITS.index(row.split)),
        )
        if (
            sum(row.source_count for row in counts) > MAX_SOURCE_EPISODES
            or sum(row.component_count for row in counts) > MAX_COMPONENTS
        ):
            raise ValueError("aggregate class counts exceed admitted bounds")
        splits_by_dimension: dict[str, list[str]] = {}
        for row in rows:
            splits_by_dimension.setdefault(row.dimension_ref, []).append(row.split)
        if any(tuple(splits) != SPLITS for splits in splits_by_dimension.values()):
            raise ValueError(
                "every sufficiency dimension must cover every canonical split"
            )
        admitted_passed = exact_bool(passed, "passed")
        if admitted_passed != all(row.passed for row in rows):
            raise ValueError("sufficiency receipt passed flag is not reconstructible")
        material = {
            "abi_version": R4_PARTITION_SUFFICIENCY_ABI_VERSION,
            "passed": admitted_passed,
            "class_counts": [row.as_dict() for row in counts],
            "dimension_rows": [row.as_dict() for row in rows],
        }
        return _new(
            cls,
            abi_version=R4_PARTITION_SUFFICIENCY_ABI_VERSION,
            receipt_ref=stable_ref("r4_partition_sufficiency_v1", material),
            passed=admitted_passed,
            class_counts=counts,
            dimension_rows=rows,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "receipt_ref": self.receipt_ref,
            "passed": self.passed,
            "class_counts": [row.as_dict() for row in self.class_counts],
            "dimension_rows": [row.as_dict() for row in self.dimension_rows],
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4PartitionSufficiencyReceipt":
        row = exact_fields(value, cls._FIELDS, "R4PartitionSufficiencyReceipt")
        if row["abi_version"] != R4_PARTITION_SUFFICIENCY_ABI_VERSION:
            raise ValueError("unsupported R4 Partition Sufficiency ABI")
        rebuilt = cls.create(
            passed=row["passed"],
            class_counts=_wire_tuple(
                row["class_counts"],
                "class_counts",
                ClassCount.from_dict,
                nonempty=True,
                maximum=len(SPLITS),
            ),
            dimension_rows=_wire_tuple(
                row["dimension_rows"],
                "dimension_rows",
                DimensionSufficiency.from_dict,
                nonempty=True,
                maximum=MAX_LABELS * len(SPLITS),
            ),
        )
        if rebuilt.receipt_ref != row["receipt_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4PartitionSufficiencyReceipt")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4PartitionSufficiencyReceipt":
        return _strict_decode(raw, cls.from_dict)


@dataclass(frozen=True, init=False)
class R4ClassCapability:
    abi_version: int
    capability_ref: str
    purpose: str
    split: str
    payload_path: str
    payload_ref: str
    payload_sha256: str
    payload_count: int
    source_set_ref: str
    split_manifest_ref: str

    _FIELDS = frozenset(
        {
            "abi_version",
            "capability_ref",
            "purpose",
            "split",
            "payload_path",
            "payload_ref",
            "payload_sha256",
            "payload_count",
            "source_set_ref",
            "split_manifest_ref",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use R4ClassCapability.create")

    @classmethod
    def create(
        cls,
        *,
        purpose: str,
        split: str,
        payload_path: str,
        payload_sha256: str,
        payload_count: int,
        source_set_ref: str,
        split_manifest_ref: str,
    ) -> "R4ClassCapability":
        admitted_split = _exact_split(split)
        admitted_purpose = _exact_purpose(purpose)
        if PURPOSE_BY_SPLIT[admitted_split] != admitted_purpose:
            raise ValueError("purpose/split pairing is not admitted")
        digest = _exact_sha256(payload_sha256, "payload_sha256")
        count = exact_int(
            payload_count, "payload_count", minimum=1, maximum=MAX_SOURCE_EPISODES
        )
        material = {
            "abi_version": R4_CLASS_CAPABILITY_ABI_VERSION,
            "purpose": admitted_purpose,
            "split": admitted_split,
            "payload_path": _payload_path(admitted_split, payload_path),
            "payload_ref": payload_ref_for(
                split=admitted_split, payload_sha256=digest, payload_count=count
            ),
            "payload_sha256": digest,
            "payload_count": count,
            "source_set_ref": _exact_ref(source_set_ref, "source_set_ref"),
            "split_manifest_ref": _exact_ref(
                split_manifest_ref, "split_manifest_ref"
            ),
        }
        return _new(
            cls,
            capability_ref=stable_ref("r4_class_capability_v1", material),
            **material,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "capability_ref": self.capability_ref,
            "purpose": self.purpose,
            "split": self.split,
            "payload_path": self.payload_path,
            "payload_ref": self.payload_ref,
            "payload_sha256": self.payload_sha256,
            "payload_count": self.payload_count,
            "source_set_ref": self.source_set_ref,
            "split_manifest_ref": self.split_manifest_ref,
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4ClassCapability":
        row = exact_fields(value, cls._FIELDS, "R4ClassCapability")
        if row["abi_version"] != R4_CLASS_CAPABILITY_ABI_VERSION:
            raise ValueError("unsupported R4 Class Capability ABI")
        rebuilt = cls.create(
            purpose=row["purpose"],
            split=row["split"],
            payload_path=row["payload_path"],
            payload_sha256=row["payload_sha256"],
            payload_count=row["payload_count"],
            source_set_ref=row["source_set_ref"],
            split_manifest_ref=row["split_manifest_ref"],
        )
        if (
            rebuilt.capability_ref != row["capability_ref"]
            or rebuilt.payload_ref != row["payload_ref"]
            or rebuilt.as_dict() != dict(row)
        ):
            raise ValueError("non-canonical R4ClassCapability")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4ClassCapability":
        return _strict_decode(raw, cls.from_dict)


@dataclass(frozen=True, init=False)
class R4ClassAuthorization:
    abi_version: int
    authorization_ref: str
    purpose: str
    expected_capability_ref: str
    expected_capability_sha256: str
    artifact_graph_ref: str
    generator_source_revision: str
    authority_generation: str

    _FIELDS = frozenset(
        {
            "abi_version",
            "authorization_ref",
            "purpose",
            "expected_capability_ref",
            "expected_capability_sha256",
            "artifact_graph_ref",
            "generator_source_revision",
            "authority_generation",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use R4ClassAuthorization.create")

    @classmethod
    def create(
        cls,
        *,
        purpose: str,
        expected_capability_ref: str,
        expected_capability_sha256: str,
        artifact_graph_ref: str,
        generator_source_revision: str,
        authority_generation: str,
    ) -> "R4ClassAuthorization":
        material = {
            "abi_version": R4_CLASS_AUTHORIZATION_ABI_VERSION,
            "purpose": _exact_purpose(purpose),
            "expected_capability_ref": _exact_ref(
                expected_capability_ref, "expected_capability_ref"
            ),
            "expected_capability_sha256": _exact_sha256(
                expected_capability_sha256, "expected_capability_sha256"
            ),
            "artifact_graph_ref": _exact_ref(artifact_graph_ref, "artifact_graph_ref"),
            "generator_source_revision": _exact_revision(
                generator_source_revision, "generator_source_revision"
            ),
            "authority_generation": _exact_ref(
                authority_generation, "authority_generation"
            ),
        }
        return _new(
            cls,
            authorization_ref=stable_ref("r4_class_authorization_v1", material),
            **material,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "authorization_ref": self.authorization_ref,
            "purpose": self.purpose,
            "expected_capability_ref": self.expected_capability_ref,
            "expected_capability_sha256": self.expected_capability_sha256,
            "artifact_graph_ref": self.artifact_graph_ref,
            "generator_source_revision": self.generator_source_revision,
            "authority_generation": self.authority_generation,
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4ClassAuthorization":
        row = exact_fields(value, cls._FIELDS, "R4ClassAuthorization")
        if row["abi_version"] != R4_CLASS_AUTHORIZATION_ABI_VERSION:
            raise ValueError("unsupported R4 Class Authorization ABI")
        rebuilt = cls.create(
            purpose=row["purpose"],
            expected_capability_ref=row["expected_capability_ref"],
            expected_capability_sha256=row["expected_capability_sha256"],
            artifact_graph_ref=row["artifact_graph_ref"],
            generator_source_revision=row["generator_source_revision"],
            authority_generation=row["authority_generation"],
        )
        if rebuilt.authorization_ref != row["authorization_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4ClassAuthorization")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4ClassAuthorization":
        return _strict_decode(raw, cls.from_dict)


def artifact_graph_ref_for(
    *,
    source_set_ref: str,
    config_ref: str,
    partition_evidence_ref: str,
    partition_sufficiency_ref: str,
    split_manifest_ref: str,
    capability_ref: str,
) -> str:
    """Return the exact acyclic R4 artifact-graph identity for one class."""
    material = {
        "source_set_ref": _exact_ref(source_set_ref, "source_set_ref"),
        "config_ref": _exact_ref(config_ref, "config_ref"),
        "partition_evidence_ref": _exact_ref(
            partition_evidence_ref, "partition_evidence_ref"
        ),
        "partition_sufficiency_ref": _exact_ref(
            partition_sufficiency_ref, "partition_sufficiency_ref"
        ),
        "split_manifest_ref": _exact_ref(
            split_manifest_ref, "split_manifest_ref"
        ),
        "capability_ref": _exact_ref(capability_ref, "capability_ref"),
    }
    return stable_ref("r4_artifact_graph_v4", material)


def authenticate_class_capability(
    capability: R4ClassCapability,
    authorization: R4ClassAuthorization,
    *,
    expected_authorization_ref: str,
    expected_authorization_sha256: str,
) -> R4ClassCapability:
    """Authenticate one class capability from an independently trusted root.

    The caller must project the expected authorization ref/SHA from an admitted
    repository run. Capability and authorization files cannot replace that
    external trust root by replacing each other together.
    """
    if type(capability) is not R4ClassCapability:
        raise TypeError("capability must be exact R4ClassCapability")
    if type(authorization) is not R4ClassAuthorization:
        raise TypeError("authorization must be exact R4ClassAuthorization")
    trusted_ref = _exact_ref(expected_authorization_ref, "expected_authorization_ref")
    trusted_sha = _exact_sha256(
        expected_authorization_sha256, "expected_authorization_sha256"
    )
    observed_authorization_sha = hashlib.sha256(authorization.to_json_bytes()).hexdigest()
    if authorization.authorization_ref != trusted_ref:
        raise ValueError("authorization ref does not match admitted trust projection")
    if observed_authorization_sha != trusted_sha:
        raise ValueError("authorization SHA does not match admitted trust projection")
    if authorization.purpose != capability.purpose:
        raise ValueError("authorization purpose does not match capability")
    if authorization.expected_capability_ref != capability.capability_ref:
        raise ValueError("authorization does not name this capability")
    observed_capability_sha = hashlib.sha256(capability.to_json_bytes()).hexdigest()
    if authorization.expected_capability_sha256 != observed_capability_sha:
        raise ValueError("authorization capability SHA mismatch")
    return capability
