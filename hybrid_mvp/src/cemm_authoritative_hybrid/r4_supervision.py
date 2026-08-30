"""Immutable reviewed-source contracts for R4.1 supervision.

These values own reviewed inputs only.  They neither compile a blueprint nor
consult runtime observations, bootstrap proposals, or verifier selections.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping, NamedTuple

from ._r4_source_codec import (
    MAX_R4_SOURCE_BYTES,
    MAX_R4_SOURCE_RECORDS,
    MAX_R4_TEXT_CHARS,
    canonical_json_bytes,
    construct,
    exact_abi,
    exact_bool,
    exact_case_ref,
    exact_content_ref,
    exact_content_ref_tuple,
    exact_fields,
    exact_int,
    exact_ref,
    exact_ref_tuple,
    exact_review_refs,
    exact_reviewer_refs,
    exact_revision,
    exact_sha256,
    exact_text,
    exact_value_tuple,
    strict_decode,
    wire_content_ref_tuple,
    wire_ref_tuple,
    wire_value_tuple,
)
from .canonical import stable_ref
from .contributions import ContributionKind
from .epistemic import exact_epistemic_status_ref
from .programs import ACTION_ABI_HASH, ACTION_ABI_SCHEMAS, PROGRAM_ABI_VERSION, SWITCH_ACTION_TYPES
from .r4_contracts import SourceDisposition

R4_REVIEW_MANIFEST_ABI_VERSION = 1
PROPOSAL_SUPERVISION_ABI_VERSION = 1
REALIZATION_SUPERVISION_ABI_VERSION = 1
MUTATION_CONTRACT_ABI_VERSION = 1

MAX_BLUEPRINT_ACTIONS = 208
MAX_DERIVATIONS_PER_CASE = 16
MAX_SELECTORS_PER_ACTION = max(
    len(variant) - 1 + 24 if variant[-1:] == ("operand_node_refs[2:24]",) else len(variant)
    for variants in ACTION_ABI_SCHEMAS.values()
    for variant in variants
)
MAX_SELECTOR_BINDINGS = 1_024
MAX_SOURCE_ASSIGNMENTS = 64
MAX_SOURCE_SPANS = 64
MAX_REALIZATION_VARIANTS_PER_CASE = 4
MAX_REALIZATION_SLOTS = 64
MAX_REALIZATION_BINDINGS = 64
MAX_REALIZATION_ALIGNMENTS = 64

R4_REVIEW_MANIFEST_PATH = "data/review/r4_1/REVIEW_MANIFEST.json"
R4_SCENARIO_SOURCE_PATH = "data/scenarios/use_cases.jsonl"
R4_REVIEW_SOURCE_FILE_COUNT = 5  # manifest plus the four child owners below
R4_REVIEW_BUNDLE_READ_COUNT = 6  # file opens/snapshots, not low-level read syscalls
MAX_R4_REVIEW_BUNDLE_BYTES = R4_REVIEW_BUNDLE_READ_COUNT * MAX_R4_SOURCE_BYTES
MAX_R4_SOURCE_READ_SYSCALLS = 8_192
_AUTHENTICATED_BUNDLE_SEAL = object()


def source_disposition_is_supervision_eligible(
    disposition: SourceDisposition,
) -> bool:
    """Return whether reviewed source truth may enter later supervision."""

    if type(disposition) is not SourceDisposition:
        raise TypeError("disposition must be exact SourceDisposition")
    return disposition is not SourceDisposition.RESTART_DIAGNOSTIC_CANDIDATE

_SOURCE_PATHS = (
    "data/review/r4_1/mutation_contracts.jsonl",
    "data/review/r4_1/proposal_supervision.jsonl",
    "data/review/r4_1/purpose_contract.json",
    "data/review/r4_1/realization_supervision.jsonl",
)
_ALL_AUTHENTICATED_SOURCE_PATHS = (
    R4_REVIEW_MANIFEST_PATH,
    *_SOURCE_PATHS,
    R4_SCENARIO_SOURCE_PATH,
)
_ABI_VERSIONS = {
    "mutation_contract": 1,
    "proposal_supervision": 1,
    "purpose_contract": 1,
    "r4_review_manifest": 1,
    "realization_supervision": 1,
}
_STRUCTURAL_SELECTOR_PREFIXES: Mapping[str, tuple[str, ...]] = {
    "context_slot": ("proposal_context:",),
    "mode_slot": ("mode_slot:",),
    "local_node": ("application:", "expression_link:", "scope:", "binder:", "local_node:"),
    "role_ref": ("role:",),
    "variant_tag": ("action_variant:",),
}
_GROUNDED_SELECTOR_PREFIXES: Mapping[str, tuple[str, ...]] = {
    "context_slot": ("proposal_context:",),
    "mode_slot": ("mode_slot:",),
    "designation_slot": ("designation_slot:",),
    "frame_slot": ("application_frame_slot:",),
    "contribution_slot": ("contribution_slot:",),
    "reference_slot": ("reference_slot:",),
    "scope_slot": ("scope_slot:",),
    "expression_link_slot": ("expression_link_slot:",),
    "variable_slot": ("variable_slot:",),
    "transition_slot": ("transition_slot:",),
}
_SOURCE_SELECTOR_PREFIXES: Mapping[str, tuple[str, ...]] = {
    "source_unit": ("unit:",),
    "contribution": ("contribution_slot:",),
}
_SAFE_SELECTOR_REF_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9_.-]*:[A-Za-z0-9][A-Za-z0-9_.-]*\Z"
)
_CONTRIBUTION_KINDS = frozenset(ContributionKind.__args__)
_ASSIGNMENT_KINDS = frozenset(
    {"role", "predicate", "reference", "scope", "qualifier", "discourse", "connector", "residual"}
)
_SOURCE_ASSIGNMENT_COMPATIBILITY = frozenset(
    {
        ("predicate", "predicate", "instantiate_operator"),
        ("anchor", "role", "bind_role"),
        ("literal", "role", "bind_role"),
        ("qualifier", "qualifier", "bind_role"),
        ("reference", "reference", "bind_reference"),
        ("scope", "scope", "attach_scope"),
        ("connector", "connector", "bind_nested_application"),
        ("discourse", "discourse", "select_mode"),
        ("discourse", "discourse", "bind_nested_application"),
        ("discourse", "discourse", "propose_transition"),
        ("open_variable", "role", "project_variable"),
        ("binder", "role", "project_variable"),
    }
)
_ACTION_FIELD_SHAPES: Mapping[str, tuple[str, tuple[str, ...]]] = {
    "proposal_context_ref": ("context_slot", ("proposal_context:",)),
    "mode_slot_ref": ("mode_slot", ("mode_slot:",)),
    "designation_slot_ref": ("designation_slot", ("designation_slot:",)),
    "application_local_ref": ("local_node", ("application:",)),
    "application_frame_slot_ref": ("frame_slot", ("application_frame_slot:",)),
    "role_ref": ("role_ref", ("role:",)),
    "contribution_slot_ref": ("contribution_slot", ("contribution_slot:",)),
    "reference_slot_ref": ("reference_slot", ("reference_slot:",)),
    "literal:role": ("variant_tag", ("action_variant:role",)),
    "literal:link": ("variant_tag", ("action_variant:link",)),
    "parent_application_ref": ("local_node", ("application:",)),
    "child_node_ref": ("local_node", ("application:", "expression_link:", "scope:", "binder:")),
    "link_local_ref": ("local_node", ("expression_link:",)),
    "expression_link_slot_ref": ("expression_link_slot", ("expression_link_slot:",)),
    "operand_node_refs[2:24]": ("local_node", ("application:", "expression_link:", "scope:", "binder:")),
    "scope_local_ref": ("local_node", ("scope:",)),
    "scope_slot_ref": ("scope_slot", ("scope_slot:",)),
    "operand_node_ref": ("local_node", ("application:", "expression_link:", "scope:", "binder:")),
    "binder_local_ref": ("local_node", ("binder:",)),
    "variable_slot_ref": ("variable_slot", ("variable_slot:",)),
    "body_node_ref": ("local_node", ("application:", "expression_link:", "scope:", "binder:")),
    "transition_slot_ref": ("transition_slot", ("transition_slot:",)),
    "source_application_ref": ("local_node", ("application:",)),
}
_OWNER_PHASES = frozenset({"orient", "propose", "verify", "evaluate", "effect", "realize"})
_SAFE_DISPOSITIONS = frozenset({"frontier", "clarify", "reject"})
_MUTATION_DISPOSITIONS = frozenset({"accept", "reject", "frontier"})
_LANGUAGE_RE = re.compile(r"[a-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z")
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class _FileIdentity(NamedTuple):
    device: int
    file_index: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    link_count: int
    file_attributes: int


class _DecodedR4Source(NamedTuple):
    records: tuple[object, ...]
    record_count: int


def _identity_from_stat(metadata: os.stat_result) -> _FileIdentity:
    return _FileIdentity(
        device=metadata.st_dev,
        file_index=metadata.st_ino,
        mode=metadata.st_mode,
        size=metadata.st_size,
        mtime_ns=metadata.st_mtime_ns,
        ctime_ns=metadata.st_ctime_ns,
        link_count=metadata.st_nlink,
        file_attributes=getattr(metadata, "st_file_attributes", 0),
    )


def _path_identity(path: Path) -> _FileIdentity:
    try:
        return _identity_from_stat(os.lstat(path))
    except OSError as exc:
        raise ValueError(f"reviewed source is unavailable or missing: {path}") from exc


def _descriptor_identity(descriptor: int) -> _FileIdentity:
    try:
        return _identity_from_stat(os.fstat(descriptor))
    except OSError as exc:
        raise ValueError("cannot inspect opened reviewed source") from exc


def _is_link_or_reparse(identity: _FileIdentity) -> bool:
    return stat.S_ISLNK(identity.mode) or bool(
        identity.file_attributes & _WINDOWS_REPARSE_POINT
    )


def _same_open_file(left: _FileIdentity, right: _FileIdentity) -> bool:
    # Windows may expose a different ctime through fstat immediately after an
    # open.  Device/file index, type, size, mtime, link count and reparse state
    # are the portable identity/change evidence used here.
    return (
        left.device,
        left.file_index,
        stat.S_IFMT(left.mode),
        left.size,
        left.mtime_ns,
        left.link_count,
        left.file_attributes & _WINDOWS_REPARSE_POINT,
    ) == (
        right.device,
        right.file_index,
        stat.S_IFMT(right.mode),
        right.size,
        right.mtime_ns,
        right.link_count,
        right.file_attributes & _WINDOWS_REPARSE_POINT,
    )


def _canonical_project_root(project_root: str | Path) -> Path:
    raw = os.fspath(project_root)
    if type(raw) is not str or not raw or "\x00" in raw:
        raise ValueError("reviewed source root must be one nonempty filesystem path")
    candidate = Path(raw).absolute()
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("reviewed source root is unavailable") from exc
    identity = _path_identity(candidate)
    if (
        candidate != resolved
        or not stat.S_ISDIR(identity.mode)
        or _is_link_or_reparse(identity)
    ):
        raise ValueError("reviewed source root must be one canonical directory")
    return resolved


def _assert_regular_source_path(
    project_root: Path, relative_path: str
) -> tuple[Path, _FileIdentity, tuple[tuple[Path, _FileIdentity], ...]]:
    if relative_path not in _ALL_AUTHENTICATED_SOURCE_PATHS:
        raise ValueError("reviewed source path is outside the exact approved namespaces")
    path = project_root.joinpath(*relative_path.split("/"))
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("reviewed source path escapes the project root") from exc
    current = project_root
    ancestors: list[tuple[Path, _FileIdentity]] = [
        (project_root, _path_identity(project_root))
    ]
    for component in relative_path.split("/")[:-1]:
        current = current / component
        identity = _path_identity(current)
        if not stat.S_ISDIR(identity.mode) or _is_link_or_reparse(identity):
            raise ValueError("reviewed source path traverses a link or reparse point")
        ancestors.append((current, identity))
    identity = _path_identity(path)
    if not stat.S_ISREG(identity.mode) or _is_link_or_reparse(identity):
        raise ValueError("reviewed source must be a regular non-link file")
    if identity.link_count != 1:
        raise ValueError("reviewed source hardlink/link count is not one")
    return path, identity, tuple(ancestors)


def _read_descriptor_bytes(descriptor: int, path: Path, *, maximum: int) -> bytes:
    del path  # retained as a deterministic hostile-I/O seam
    expected_size = _descriptor_identity(descriptor).size
    read_limit = min(maximum + 1, expected_size + 1)
    chunks: list[bytes] = []
    total = 0
    for _ in range(MAX_R4_SOURCE_READ_SYSCALLS):
        try:
            chunk = os.read(descriptor, read_limit - total)
        except InterruptedError:
            continue
        except OSError as exc:
            if exc.errno == errno.EINTR:
                continue
            raise ValueError("cannot read reviewed source") from exc
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total >= read_limit:
            return b"".join(chunks)
    raise ValueError("reviewed source exceeds the bounded read syscall count")


def _read_regular_file_once(
    project_root: Path, relative_path: str, *, maximum: int
) -> bytes:
    path, before_path, ancestors = _assert_regular_source_path(project_root, relative_path)
    if before_path.size <= 0 or before_path.size > maximum:
        raise ValueError("reviewed source violates byte bounds")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = _descriptor_identity(descriptor)
        if not _same_open_file(opened, before_path):
            raise ValueError("reviewed source was replaced before open")
        raw = _read_descriptor_bytes(descriptor, path, maximum=maximum)
        after_descriptor = _descriptor_identity(descriptor)
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError("cannot open reviewed source without following links") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    after_path = _path_identity(path)
    for ancestor, before_ancestor in ancestors:
        after_ancestor = _path_identity(ancestor)
        if (
            not stat.S_ISDIR(after_ancestor.mode)
            or _is_link_or_reparse(after_ancestor)
            or not _same_open_file(after_ancestor, before_ancestor)
        ):
            raise ValueError(
                "reviewed source ancestor was replaced or changed while being read"
            )
    if not _same_open_file(after_descriptor, opened) or not _same_open_file(after_path, opened):
        raise ValueError("reviewed source was replaced or changed while being read")
    if len(raw) < opened.size:
        raise ValueError("reviewed source short read or changed while being read")
    if len(raw) > opened.size:
        raise ValueError("reviewed source grew or changed while being read")
    return raw


def _decode_authenticated_source(path: str, raw: bytes) -> _DecodedR4Source:
    if path.endswith(".json"):
        if path == "data/review/r4_1/purpose_contract.json":
            from .r4_purpose import PurposeContract

            record = PurposeContract.from_json_bytes(raw)
        else:
            record = strict_decode(
                raw, lambda value: value, owner=f"reviewed source {path}"
            )
        return _DecodedR4Source((record,), 1)
    if not raw.endswith(b"\n"):
        raise ValueError(f"reviewed source {path} must be LF terminated")
    if b"\r" in raw:
        raise ValueError(f"reviewed source {path} must use canonical LF-only JSONL")
    line_count = raw.count(b"\n")
    if line_count < 1 or line_count > MAX_R4_SOURCE_RECORDS:
        raise ValueError(f"reviewed source {path} violates record count bounds")
    lines = raw[:-1].split(b"\n")
    if len(lines) != line_count or any(not line for line in lines):
        raise ValueError(f"reviewed source {path} violates record count bounds")
    records: list[object] = []
    row_refs: set[str] = set()
    realization_variants_by_case: dict[str, int] = {}
    for index, line in enumerate(lines, 1):
        record = line + b"\n"
        if path == "data/review/r4_1/mutation_contracts.jsonl":
            decoded = MutationContract.from_json_bytes(record)
            row_ref = decoded.mutation_contract_ref
        elif path == "data/review/r4_1/proposal_supervision.jsonl":
            decoded = ProposalTarget.from_json_bytes(record)
            row_ref = decoded.proposal_target_ref
        elif path == "data/review/r4_1/realization_supervision.jsonl":
            decoded = RealizationRow.from_json_bytes(record)
            row_ref = decoded.realization_ref
            count = realization_variants_by_case.get(decoded.source_case_ref, 0) + 1
            if count > MAX_REALIZATION_VARIANTS_PER_CASE:
                raise ValueError("realization supervision exceeds four variants for one case")
            realization_variants_by_case[decoded.source_case_ref] = count
        elif path == R4_SCENARIO_SOURCE_PATH:
            from .r4_contracts import ReviewedScenario

            decoded = strict_decode(
                record,
                ReviewedScenario.from_dict,
                owner=f"reviewed source {path} record {index}",
            )
            row_ref = decoded.scenario_ref
            if decoded.review_status != "reviewed":
                raise ValueError("scenario source contains an unreviewed scenario")
        else:
            raise ValueError("reviewed JSONL source path has no exact decoder owner")
        if row_ref in row_refs:
            raise ValueError(f"reviewed source {path} contains a duplicate row identity")
        row_refs.add(row_ref)
        records.append(decoded)
    return _DecodedR4Source(tuple(records), len(records))


def _source_bundle_ref(
    sources: tuple["AuthenticatedR4SourceBytes", ...],
    scenario_source: "AuthenticatedR4SourceBytes",
) -> str:
    return stable_ref(
        "r4_review_bundle_v1",
        {
            "scenario_source": scenario_source.identity_dict(),
            "sources": [source.identity_dict() for source in sources],
        },
    )


def _factory_only(owner: str) -> TypeError:
    return TypeError(f"use {owner}.create")


def _wire_optional_ref(value: object, name: str) -> str | None:
    if value is None:
        return None
    return exact_ref(value, name)


def _exact_selector_ref(
    value: object,
    name: str,
    *,
    prefixes: tuple[str, ...],
) -> str:
    ref = exact_ref(value, name)
    if not ref.startswith(prefixes) or _SAFE_SELECTOR_REF_RE.fullmatch(ref) is None:
        raise ValueError(
            f"{name} must be one exact typed selector ref without regex, raw phrase, or nested internal-ref spelling"
        )
    return ref


def _canonical_nested(value: object, expected_type: type[Any], name: str) -> Any:
    if type(value) is not expected_type:
        raise TypeError(f"{name} must be exact {expected_type.__name__}")
    try:
        rebuilt = expected_type.from_dict(value.as_dict())
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not canonical") from exc
    if rebuilt != value:
        raise ValueError(f"{name} is not canonical")
    return rebuilt


def _matches_action_variant(
    bindings: tuple["SelectorBinding", ...],
    selector_handles: tuple[int, ...],
    variant: tuple[str, ...],
) -> bool:
    repeated = variant[-1:] == ("operand_node_refs[2:24]",)
    if repeated:
        if not len(variant) + 1 <= len(selector_handles) <= len(variant) + 23:
            return False
        fields = variant[:-1] + (variant[-1],) * (len(selector_handles) - len(variant) + 1)
    else:
        if len(selector_handles) != len(variant):
            return False
        fields = variant
    selectors = tuple(bindings[handle] for handle in selector_handles)
    return all(
        selector.selector_kind == _ACTION_FIELD_SHAPES[field][0]
        and (
            selector.value_ref == _ACTION_FIELD_SHAPES[field][1][0]
            if field.startswith("literal:")
            else selector.value_ref.startswith(_ACTION_FIELD_SHAPES[field][1])
        )
        for selector, field in zip(selectors, fields, strict=True)
    )


@dataclass(frozen=True, init=False)
class ReviewSourceFile:
    abi_version: int
    source_ref: str
    path: str
    sha256: str
    record_count: int
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "source_ref", "path", "sha256", "record_count", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ReviewSourceFile")

    @classmethod
    def create(cls, *, source_ref: str, path: str, sha256: str, record_count: int, review_refs: tuple[str, ...]) -> "ReviewSourceFile":
        if type(source_ref) is str and source_ref.startswith(("runtime_observation:", "bootstrap_output:")):
            raise ValueError("reviewed source cannot be a runtime or bootstrap output")
        ref = exact_content_ref(source_ref, "source_ref", prefix="reviewed_source:")
        exact_path = exact_text(path, "source path", maximum=256)
        if exact_path not in _SOURCE_PATHS:
            raise ValueError("source path is not an R4.1 reviewed source owner")
        return construct(
            cls,
            abi_version=R4_REVIEW_MANIFEST_ABI_VERSION,
            source_ref=ref,
            path=exact_path,
            sha256=exact_sha256(sha256, "source sha256"),
            record_count=exact_int(record_count, "record_count", minimum=1, maximum=MAX_R4_SOURCE_RECORDS),
            review_refs=exact_review_refs(review_refs),
        )

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "source_ref": self.source_ref, "path": self.path, "sha256": self.sha256, "record_count": self.record_count, "review_refs": list(self.review_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewSourceFile":
        row = exact_fields(value, cls._FIELDS, "ReviewSourceFile")
        exact_abi(row["abi_version"], R4_REVIEW_MANIFEST_ABI_VERSION, "R4 Review Manifest")
        rebuilt = cls.create(source_ref=row["source_ref"], path=row["path"], sha256=row["sha256"], record_count=row["record_count"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ReviewSourceFile")
        return rebuilt


@dataclass(frozen=True, init=False)
class R4ReviewManifest:
    abi_version: int
    manifest_ref: str
    review_policy_ref: str
    reviewer_refs: tuple[str, ...]
    reviewed_base_revision: str
    authority_generation: str
    source_bundle_ref: str
    scenario_source_sha256: str
    sources: tuple[ReviewSourceFile, ...]
    abi_versions: Mapping[str, int]
    approval_state: str
    supersedes_refs: tuple[str, ...]
    runtime_observations_are_source_authority: bool
    bootstrap_outputs_are_source_authority: bool

    _FIELDS = frozenset({"abi_version", "manifest_ref", "review_policy_ref", "reviewer_refs", "reviewed_base_revision", "authority_generation", "source_bundle_ref", "scenario_source_sha256", "sources", "abi_versions", "approval_state", "supersedes_refs", "runtime_observations_are_source_authority", "bootstrap_outputs_are_source_authority"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("R4ReviewManifest")

    @classmethod
    def create(cls, *, review_policy_ref: str, reviewer_refs: tuple[str, ...], reviewed_base_revision: str, authority_generation: str, source_bundle_ref: str, scenario_source_sha256: str, sources: tuple[ReviewSourceFile, ...], approval_state: str, supersedes_refs: tuple[str, ...], runtime_observations_are_source_authority: bool, bootstrap_outputs_are_source_authority: bool) -> "R4ReviewManifest":
        source_rows = exact_value_tuple(sources, "sources", ReviewSourceFile, nonempty=True, maximum=len(_SOURCE_PATHS), identity=lambda row: row.path)
        source_rows = tuple(_canonical_nested(row, ReviewSourceFile, "source") for row in source_rows)
        if tuple(row.path for row in source_rows) != _SOURCE_PATHS:
            raise ValueError("manifest must bind every exact R4.1 reviewed source")
        if len({row.source_ref for row in source_rows}) != len(source_rows):
            raise ValueError("manifest contains duplicate source refs")
        reviewers = exact_reviewer_refs(reviewer_refs)
        supersedes = exact_ref_tuple(supersedes_refs, "supersedes_refs", nonempty=False)
        runtime_authority = exact_bool(runtime_observations_are_source_authority, "runtime_observations_are_source_authority")
        bootstrap_authority = exact_bool(bootstrap_outputs_are_source_authority, "bootstrap_outputs_are_source_authority")
        if runtime_authority or bootstrap_authority:
            raise ValueError("runtime observations and bootstrap outputs cannot be source authority")
        if approval_state != "approved":
            raise ValueError("review manifest approval_state must be approved")
        material = {
            "abi_version": R4_REVIEW_MANIFEST_ABI_VERSION,
            "review_policy_ref": exact_ref(review_policy_ref, "review_policy_ref", prefix="review_policy:"),
            "reviewer_refs": list(reviewers),
            "reviewed_base_revision": exact_revision(reviewed_base_revision, "reviewed_base_revision"),
            "authority_generation": exact_text(authority_generation, "authority_generation"),
            "source_bundle_ref": exact_content_ref(source_bundle_ref, "source_bundle_ref", prefix="r4_review_bundle_v1:"),
            "scenario_source_sha256": exact_sha256(scenario_source_sha256, "scenario_source_sha256"),
            "sources": [row.as_dict() for row in source_rows],
            "abi_versions": dict(_ABI_VERSIONS),
            "approval_state": approval_state,
            "supersedes_refs": list(supersedes),
            "runtime_observations_are_source_authority": runtime_authority,
            "bootstrap_outputs_are_source_authority": bootstrap_authority,
        }
        return construct(cls, manifest_ref=stable_ref("r4_review_manifest_v1", material), sources=source_rows, abi_versions=MappingProxyType(dict(_ABI_VERSIONS)), **{key: value if key not in {"reviewer_refs", "supersedes_refs"} else tuple(value) for key, value in material.items() if key not in {"sources", "abi_versions"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "manifest_ref": self.manifest_ref, "review_policy_ref": self.review_policy_ref, "reviewer_refs": list(self.reviewer_refs), "reviewed_base_revision": self.reviewed_base_revision, "authority_generation": self.authority_generation, "source_bundle_ref": self.source_bundle_ref, "scenario_source_sha256": self.scenario_source_sha256, "sources": [row.as_dict() for row in self.sources], "abi_versions": dict(self.abi_versions), "approval_state": self.approval_state, "supersedes_refs": list(self.supersedes_refs), "runtime_observations_are_source_authority": self.runtime_observations_are_source_authority, "bootstrap_outputs_are_source_authority": self.bootstrap_outputs_are_source_authority}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4ReviewManifest":
        if type(value) is dict and frozenset(value).intersection(
            {
                "containing_commit_revision",
                "manifest_commit_revision",
                "source_commit_revision",
                "generator_source_revision",
            }
        ):
            raise ValueError(
                "self-referential containing-commit identity is forbidden in the review manifest"
            )
        row = exact_fields(value, cls._FIELDS, "R4ReviewManifest")
        exact_abi(row["abi_version"], R4_REVIEW_MANIFEST_ABI_VERSION, "R4 Review Manifest")
        if type(row["abi_versions"]) is not dict or set(row["abi_versions"]) != set(_ABI_VERSIONS):
            raise ValueError("manifest ABI versions are not the exact ABI 1 allocation")
        for name, expected in _ABI_VERSIONS.items():
            exact_abi(row["abi_versions"][name], expected, f"manifest {name}")
        rebuilt = cls.create(review_policy_ref=row["review_policy_ref"], reviewer_refs=wire_ref_tuple(row["reviewer_refs"], "reviewer_refs", nonempty=True), reviewed_base_revision=row["reviewed_base_revision"], authority_generation=row["authority_generation"], source_bundle_ref=row["source_bundle_ref"], scenario_source_sha256=row["scenario_source_sha256"], sources=wire_value_tuple(row["sources"], "sources", ReviewSourceFile.from_dict, nonempty=True, maximum=len(_SOURCE_PATHS)), approval_state=row["approval_state"], supersedes_refs=wire_ref_tuple(row["supersedes_refs"], "supersedes_refs", nonempty=False), runtime_observations_are_source_authority=row["runtime_observations_are_source_authority"], bootstrap_outputs_are_source_authority=row["bootstrap_outputs_are_source_authority"])
        if rebuilt.manifest_ref != row["manifest_ref"]:
            raise ValueError("manifest ref does not match canonical content")
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4ReviewManifest")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4ReviewManifest":
        return strict_decode(raw, cls.from_dict, owner="R4 review manifest")


@dataclass(frozen=True, init=False)
class AuthenticatedR4SourceBytes:
    path: str
    raw_bytes: bytes
    sha256: str
    record_count: int
    records: tuple[object, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("AuthenticatedR4SourceBytes")

    @classmethod
    def create(cls, *, path: str, raw_bytes: bytes) -> "AuthenticatedR4SourceBytes":
        if path not in (*_SOURCE_PATHS, R4_SCENARIO_SOURCE_PATH):
            raise ValueError("authenticated source path is outside the exact bundle membership")
        if type(raw_bytes) is not bytes:
            raise TypeError("authenticated source bytes must be exact immutable bytes")
        decoded = _decode_authenticated_source(path, raw_bytes)
        return construct(
            cls,
            path=path,
            raw_bytes=raw_bytes,
            sha256=hashlib.sha256(raw_bytes).hexdigest(),
            record_count=decoded.record_count,
            records=decoded.records,
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "record_count": self.record_count,
        }


@dataclass(frozen=True, init=False)
class AuthenticatedR4ReviewBundle:
    manifest: R4ReviewManifest
    manifest_bytes: bytes
    manifest_sha256: str
    sources: tuple[AuthenticatedR4SourceBytes, ...]
    scenario_source: AuthenticatedR4SourceBytes
    reviewed_base_revision: str
    authority_generation: str
    source_bundle_ref: str
    read_count: int
    aggregate_bytes: int
    scenarios: tuple[object, ...]
    proposal_targets: tuple[object, ...]
    realization_rows: tuple[object, ...]
    mutation_contracts: tuple[object, ...]
    purpose_contract: object
    _seal: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "AuthenticatedR4ReviewBundle is created only by "
            "load_authenticated_r4_review_bundle"
        )

    @property
    def source_bytes(self) -> Mapping[str, bytes]:
        return MappingProxyType(
            {
                self.scenario_source.path: self.scenario_source.raw_bytes,
                **{source.path: source.raw_bytes for source in self.sources},
            }
        )


def load_authenticated_r4_review_bundle(
    project_root: str | Path,
) -> AuthenticatedR4ReviewBundle:
    """Read and authenticate the exact six-file R4.1 reviewed-source bundle.

    The manifest and each named source are opened once; bounded repeated read
    syscalls may consume that same descriptor.  No directory listing, runtime
    observation, bootstrap output, or generated artifact is consulted.
    The descriptor/path/ancestor identity checks detect stable replacement
    observed across the read within the portable metadata exposed by the host
    OS.  A transient ancestor swap restored before the post-read probe, a remote
    filesystem snapshot, and a cryptographic filesystem transaction are outside
    this cross-platform guarantee.
    """

    root = _canonical_project_root(project_root)
    read_paths: set[str] = set()
    aggregate_bytes = 0

    def read(relative_path: str) -> bytes:
        nonlocal aggregate_bytes
        if relative_path in read_paths:
            raise ValueError(f"duplicate reviewed source read is forbidden: {relative_path}")
        read_paths.add(relative_path)
        raw = _read_regular_file_once(root, relative_path, maximum=MAX_R4_SOURCE_BYTES)
        aggregate_bytes += len(raw)
        if aggregate_bytes > MAX_R4_REVIEW_BUNDLE_BYTES:
            raise ValueError("review bundle violates aggregate byte bounds")
        return raw

    manifest_bytes = read(R4_REVIEW_MANIFEST_PATH)
    manifest = R4ReviewManifest.from_json_bytes(manifest_bytes)
    sources: list[AuthenticatedR4SourceBytes] = []
    for source_record in manifest.sources:
        raw = read(source_record.path)
        source = AuthenticatedR4SourceBytes.create(
            path=source_record.path, raw_bytes=raw
        )
        if source.record_count != source_record.record_count:
            raise ValueError(f"reviewed source record count mismatch: {source.path}")
        if source.sha256 != source_record.sha256:
            raise ValueError(f"reviewed source SHA-256 mismatch: {source.path}")
        sources.append(source)
    scenario_raw = read(R4_SCENARIO_SOURCE_PATH)
    scenario = AuthenticatedR4SourceBytes.create(
        path=R4_SCENARIO_SOURCE_PATH, raw_bytes=scenario_raw
    )
    if scenario.sha256 != manifest.scenario_source_sha256:
        raise ValueError("reviewed scenario source SHA-256 mismatch")
    if read_paths != set(_ALL_AUTHENTICATED_SOURCE_PATHS):
        raise ValueError("review bundle read membership is not exact")
    exact_sources = tuple(sources)
    computed_ref = _source_bundle_ref(exact_sources, scenario)
    if computed_ref != manifest.source_bundle_ref:
        raise ValueError("review manifest source-bundle content ref does not reconstruct")
    sources_by_path = {source.path: source for source in exact_sources}
    purpose_records = sources_by_path[
        "data/review/r4_1/purpose_contract.json"
    ].records
    if len(purpose_records) != 1:
        raise ValueError("purpose contract source must contain exactly one record")
    return construct(
        AuthenticatedR4ReviewBundle,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        sources=exact_sources,
        scenario_source=scenario,
        reviewed_base_revision=manifest.reviewed_base_revision,
        authority_generation=manifest.authority_generation,
        source_bundle_ref=computed_ref,
        read_count=len(read_paths),
        aggregate_bytes=aggregate_bytes,
        scenarios=scenario.records,
        proposal_targets=sources_by_path[
            "data/review/r4_1/proposal_supervision.jsonl"
        ].records,
        realization_rows=sources_by_path[
            "data/review/r4_1/realization_supervision.jsonl"
        ].records,
        mutation_contracts=sources_by_path[
            "data/review/r4_1/mutation_contracts.jsonl"
        ].records,
        purpose_contract=purpose_records[0],
        _seal=_AUTHENTICATED_BUNDLE_SEAL,
    )


@dataclass(frozen=True)
class CrossSourceValidationResult:
    """Non-authoritative, non-serialized diagnostics for one bound snapshot."""

    source_bundle_ref: str
    authority_generation: str
    source_set_ref: str
    source_case_count: int
    supervised_case_count: int
    diagnostic_case_count: int
    proposal_count: int
    realization_count: int
    membership_count: int
    operation_count: int


def validate_authenticated_r4_source_semantics(
    bundle: AuthenticatedR4ReviewBundle,
    *,
    authority: object,
) -> CrossSourceValidationResult:
    """Validate the already-decoded R4.1 source snapshot with linear joins.

    This is part of the existing authenticated-bundle owner.  It does not
    compile gold, call a solver/model/runtime, or create an admission gate.
    """

    from .authority import LinkedAuthority
    from .r4_expansion import expand_reviewed_source_universe
    from .r4_purpose import PurposeContract, PurposeMembership

    if type(bundle) is not AuthenticatedR4ReviewBundle:
        raise TypeError("bundle must be an exact authenticated R4 review bundle")
    if getattr(bundle, "_seal", None) is not _AUTHENTICATED_BUNDLE_SEAL:
        raise ValueError("review bundle was not minted by the authenticated loader")

    if (
        type(bundle.manifest_bytes) is not bytes
        or bundle.manifest.to_json_bytes() != bundle.manifest_bytes
        or hashlib.sha256(bundle.manifest_bytes).hexdigest()
        != bundle.manifest_sha256
    ):
        raise ValueError("retained manifest does not match authenticated bytes")

    def verify_retained_source(source: AuthenticatedR4SourceBytes) -> int:
        if type(source) is not AuthenticatedR4SourceBytes:
            raise TypeError("authenticated bundle source is not exact")
        if (
            type(source.raw_bytes) is not bytes
            or hashlib.sha256(source.raw_bytes).hexdigest() != source.sha256
            or len(source.records) != source.record_count
        ):
            raise ValueError("retained typed records do not match authenticated bytes")
        digest = hashlib.sha256()
        for record in source.records:
            if source.path == R4_SCENARIO_SOURCE_PATH:
                from .r4_contracts import ReviewedScenario

                if type(record) is not ReviewedScenario:
                    raise TypeError("retained scenario record is not exact")
                encoded = canonical_json_bytes(record.as_dict())
            elif source.path == "data/review/r4_1/mutation_contracts.jsonl":
                if type(record) is not MutationContract:
                    raise TypeError("retained mutation record is not exact")
                encoded = record.to_json_bytes()
            elif source.path == "data/review/r4_1/proposal_supervision.jsonl":
                if type(record) is not ProposalTarget:
                    raise TypeError("retained proposal record is not exact")
                encoded = record.to_json_bytes()
            elif source.path == "data/review/r4_1/realization_supervision.jsonl":
                if type(record) is not RealizationRow:
                    raise TypeError("retained realization record is not exact")
                encoded = record.to_json_bytes()
            elif source.path == "data/review/r4_1/purpose_contract.json":
                if type(record) is not PurposeContract:
                    raise TypeError("retained purpose record is not exact")
                encoded = record.to_json_bytes()
            else:
                raise ValueError("authenticated bundle contains an unknown source path")
            digest.update(encoded)
        if digest.hexdigest() != source.sha256:
            raise ValueError("retained typed records do not match authenticated bytes")
        return len(source.records)

    sources_by_path = {source.path: source for source in bundle.sources}
    if (
        len(sources_by_path) != len(_SOURCE_PATHS)
        or tuple(sources_by_path) != _SOURCE_PATHS
        or bundle.scenarios is not bundle.scenario_source.records
        or bundle.proposal_targets
        is not sources_by_path["data/review/r4_1/proposal_supervision.jsonl"].records
        or bundle.realization_rows
        is not sources_by_path["data/review/r4_1/realization_supervision.jsonl"].records
        or bundle.mutation_contracts
        is not sources_by_path["data/review/r4_1/mutation_contracts.jsonl"].records
        or len(sources_by_path["data/review/r4_1/purpose_contract.json"].records)
        != 1
        or bundle.purpose_contract
        is not sources_by_path["data/review/r4_1/purpose_contract.json"].records[0]
    ):
        raise ValueError("authenticated bundle typed projections do not match source ownership")
    rebound_records = verify_retained_source(bundle.scenario_source)
    for source in bundle.sources:
        rebound_records += verify_retained_source(source)
    if (
        _source_bundle_ref(bundle.sources, bundle.scenario_source)
        != bundle.source_bundle_ref
        or bundle.source_bundle_ref != bundle.manifest.source_bundle_ref
        or bundle.authority_generation != bundle.manifest.authority_generation
        or bundle.reviewed_base_revision
        != bundle.manifest.reviewed_base_revision
        or bundle.scenario_source.sha256
        != bundle.manifest.scenario_source_sha256
        or tuple(
            (source.path, source.sha256, source.record_count)
            for source in bundle.sources
        )
        != tuple(
            (source.path, source.sha256, source.record_count)
            for source in bundle.manifest.sources
        )
    ):
        raise ValueError("retained source bundle identity does not reconstruct")
    if type(authority) is not LinkedAuthority:
        raise TypeError("authority must be exact LinkedAuthority")
    if authority.generation != bundle.authority_generation:
        raise ValueError("authority generation differs from the authenticated review bundle")
    if any(type(row) is not ProposalTarget for row in bundle.proposal_targets):
        raise TypeError("authenticated proposal projection is not exact")
    if any(type(row) is not RealizationRow for row in bundle.realization_rows):
        raise TypeError("authenticated realization projection is not exact")
    if any(type(row) is not MutationContract for row in bundle.mutation_contracts):
        raise TypeError("authenticated mutation projection is not exact")
    if type(bundle.purpose_contract) is not PurposeContract:
        raise TypeError("authenticated purpose projection is not exact")

    universe = expand_reviewed_source_universe(
        bundle.scenarios,
        authority=authority,
    )
    operations = sum(universe.operation_counts.values()) + rebound_records

    cases_by_ref: dict[str, object] = {}
    for case in universe.cases:
        operations += 1
        if case.case_ref in cases_by_ref:
            raise ValueError("source universe contains a duplicate case identity")
        cases_by_ref[case.case_ref] = case
    source_set_ref = universe.source_set_ref
    purpose_contract = bundle.purpose_contract
    if purpose_contract.source_set_ref != source_set_ref:
        raise ValueError("purpose contract source-set ref does not reconstruct")

    proposals_by_case: dict[str, ProposalTarget] = {}
    selector_owner: dict[tuple[str, str, str], str] = {}
    selector_geometry: dict[tuple[str, str, str], tuple[object, ...]] = {}

    def bind_selector_owner(
        key: tuple[str, str, str], surface_ref: str, geometry: tuple[object, ...]
    ) -> None:
        nonlocal operations
        operations += 1
        previous_owner = selector_owner.get(key)
        if previous_owner is not None and previous_owner != surface_ref:
            raise ValueError("reviewed source selector crosses its case surface")
        previous_geometry = selector_geometry.get(key)
        if geometry and previous_geometry is not None and previous_geometry != geometry:
            raise ValueError("reviewed source selector has inconsistent grounded geometry")
        selector_owner[key] = surface_ref
        if geometry:
            selector_geometry[key] = geometry

    for proposal in bundle.proposal_targets:
        operations += 1
        case = cases_by_ref.get(proposal.source_case_ref)
        if case is None:
            raise ValueError("proposal supervision contains an extra source case")
        if proposal.source_case_ref in proposals_by_case:
            raise ValueError("proposal supervision contains duplicate rows for one case")
        proposals_by_case[proposal.source_case_ref] = proposal
        for derivation in proposal.derivations:
            operations += 1
            for assignment in derivation.source_assignment_blueprint.assignments:
                operations += 1
                bind_selector_owner(
                    (
                        proposal.source_case_ref,
                        "source_unit",
                        assignment.source_unit_ref,
                    ),
                    case.surface_ref,
                    (),
                )
                bind_selector_owner(
                    (
                        proposal.source_case_ref,
                        "contribution",
                        assignment.contribution_slot_ref,
                    ),
                    case.surface_ref,
                    (),
                )
            for binding in derivation.selector_bindings:
                operations += 1
                if type(binding) is not GroundedSelectorBinding:
                    continue
                if (
                    binding.source_case_ref != proposal.source_case_ref
                    or binding.surface_ref != case.surface_ref
                ):
                    raise ValueError("grounded selector has cross-case or cross-surface ownership")
                spans = tuple(
                    (span.surface_ref, span.start, span.end) for span in binding.spans
                )
                for span in binding.spans:
                    operations += 1
                    if (
                        span.surface_ref != case.surface_ref
                        or span.start < 0
                        or span.end <= span.start
                        or span.end > len(case.surface)
                    ):
                        raise ValueError("grounded selector span is outside its exact source surface")
                selector_key = (
                    proposal.source_case_ref,
                    binding.source_selector_kind,
                    binding.source_selector_ref,
                )
                if selector_key not in selector_owner:
                    raise ValueError(
                        "grounded selector is not declared by its source assignment blueprint"
                    )
                bind_selector_owner(
                    selector_key,
                    case.surface_ref,
                    (
                        binding.graph_component_ref,
                        binding.semantic_kind_ref,
                        spans,
                    ),
                )

    realizations_by_case: dict[str, list[RealizationRow]] = {}
    for realization in bundle.realization_rows:
        operations += 1
        if realization.source_case_ref not in cases_by_ref:
            raise ValueError("realization supervision contains an extra source case")
        rows = realizations_by_case.setdefault(realization.source_case_ref, [])
        rows.append(realization)
        if len(rows) > MAX_REALIZATION_VARIANTS_PER_CASE:
            raise ValueError("realization supervision exceeds four variants for one case")

    memberships_by_case: dict[str, PurposeMembership] = {}
    for membership in purpose_contract.memberships:
        operations += 1
        if membership.source_case_ref not in cases_by_ref:
            raise ValueError("purpose contract contains an extra source case")
        if membership.source_case_ref in memberships_by_case:
            raise ValueError("purpose contract contains duplicate membership for one case")
        memberships_by_case[membership.source_case_ref] = membership

    for mutation in bundle.mutation_contracts:
        operations += 1
        if mutation.source_case_ref not in cases_by_ref:
            raise ValueError("mutation contract contains an orphan source case")

    expected_classification = {
        SourceDisposition.SEMANTIC: "semantic_supervision",
        SourceDisposition.EXPLICIT_GAP: "typed_abstention",
        SourceDisposition.VERIFICATION_REJECTION: "verification_rejection",
        SourceDisposition.RESTART_DIAGNOSTIC_CANDIDATE: "diagnostic_only",
    }
    supervised_count = 0
    diagnostic_count = 0
    for case_ref, case in cases_by_ref.items():
        operations += 1
        disposition = case.source_disposition
        eligible = source_disposition_is_supervision_eligible(disposition)
        proposal = proposals_by_case.get(case_ref)
        realization_rows = realizations_by_case.get(case_ref, [])
        membership = memberships_by_case.get(case_ref)
        if membership is None:
            raise ValueError("purpose membership is missing for a source case")
        if membership.classification != expected_classification[disposition]:
            raise ValueError("purpose membership classification disagrees with source disposition")
        if not eligible:
            diagnostic_count += 1
            if proposal is not None or realization_rows:
                raise ValueError("diagnostic source case cannot carry proposal or realization supervision")
            continue

        supervised_count += 1
        if proposal is None:
            raise ValueError("proposal supervision is missing for a supervised source case")
        if len(realization_rows) != 1:
            raise ValueError("exactly one initial realization is required for each supervised source case")
        realization = realization_rows[0]
        expected_response = case.contract.expected_response
        if (
            realization.language != case.language
            or realization.discourse_action_ref
            != f"response_action:{expected_response.discourse_action}"
            or realization.polarity_ref != expected_response.polarity_ref
            or realization.modality_ref != expected_response.modality_ref
            or realization.epistemic_status_ref
            != expected_response.epistemic_status_ref
        ):
            if realization.language != case.language:
                raise ValueError("realization language disagrees with reviewed source truth")
            raise ValueError("realization response contract disagrees with reviewed source truth")

        if disposition is SourceDisposition.SEMANTIC:
            expected_refs = tuple(
                sorted(
                    expression.expression_ref
                    for expression in case.contract.expected_expressions
                )
            )
            relation = case.contract.expression_relation.value
            if relation == "single":
                expected_relation = "single"
            elif relation in {"any", "conflict"}:
                expected_relation = "conflict"
            else:
                raise ValueError("semantic source relation is not representable by proposal ABI 1")
            if (
                proposal.target_kind != "derive"
                or proposal.expected_expression_refs != expected_refs
                or proposal.expected_expression_relation != expected_relation
            ):
                raise ValueError("proposal expression target disagrees with reviewed source truth")
            subject = realization.response_subject
            if (
                type(subject) is not ExpressionSetResponseSubject
                or subject.expression_refs != proposal.expected_expression_refs
                or subject.expected_expression_relation
                != proposal.expected_expression_relation
            ):
                raise ValueError("realization subject disagrees with the proposal expression set")
        elif disposition is SourceDisposition.EXPLICIT_GAP:
            if proposal.target_kind != "abstain" or proposal.abstention is None:
                raise ValueError("explicit gap requires one typed abstention proposal")
            expected_gap = case.contract.expected_gap
            if (
                expected_gap is None
                or proposal.abstention.gap_kind_ref
                != f"gap_kind:{expected_gap.kind}"
            ):
                raise ValueError("proposal gap kind disagrees with reviewed source truth")
            subject = realization.response_subject
            if (
                type(subject) is not TypedGapResponseSubject
                or subject.typed_gap != proposal.abstention
            ):
                raise ValueError("gap realization subject disagrees with proposal truth")
            if realization.authorized_surface.strip().casefold() == case.surface.strip().casefold():
                raise ValueError("safe gap realization cannot echo the input surface")
        else:
            if (
                proposal.target_kind != "verification_rejection"
                or proposal.verification_rejection is None
            ):
                raise ValueError("verification source requires one rejection proposal")
            expected_gap = case.contract.expected_gap
            if expected_gap is None or expected_gap.error_code is None:
                raise ValueError("verification source truth has no exact error code")
            error_namespace, separator, error_name = expected_gap.error_code.partition(":")
            if separator != ":" or error_namespace != "verification" or not error_name:
                raise ValueError("verification source truth error code is not canonical")
            if (
                proposal.verification_rejection.verification_error_code
                != f"verification_error:{error_name}"
            ):
                raise ValueError(
                    "proposal verification error disagrees with reviewed source truth"
                )
            subject = realization.response_subject
            if (
                type(subject) is not VerifierRejectionResponseSubject
                or subject.verifier_rejection != proposal.verification_rejection
            ):
                raise ValueError("rejection realization subject disagrees with proposal truth")
            if realization.authorized_surface.strip().casefold() == case.surface.strip().casefold():
                raise ValueError("safe rejection realization cannot echo the input surface")

    if set(proposals_by_case) != {
        case_ref
        for case_ref, case in cases_by_ref.items()
        if source_disposition_is_supervision_eligible(case.source_disposition)
    }:
        raise ValueError("proposal supervision case membership is not exact")
    if set(realizations_by_case) != set(proposals_by_case):
        raise ValueError("realization supervision case membership is not exact")
    if set(memberships_by_case) != set(cases_by_ref):
        raise ValueError("purpose membership case coverage is not exact")

    return CrossSourceValidationResult(
        source_bundle_ref=bundle.source_bundle_ref,
        authority_generation=bundle.authority_generation,
        source_set_ref=source_set_ref,
        source_case_count=len(cases_by_ref),
        supervised_case_count=supervised_count,
        diagnostic_case_count=diagnostic_count,
        proposal_count=len(proposals_by_case),
        realization_count=len(bundle.realization_rows),
        membership_count=len(memberships_by_case),
        operation_count=operations,
    )


@dataclass(frozen=True, init=False)
class SourceSpan:
    abi_version: int
    span_ref: str
    surface_ref: str
    start: int
    end: int

    _FIELDS = frozenset({"abi_version", "span_ref", "surface_ref", "start", "end"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("SourceSpan")

    @classmethod
    def create(cls, *, surface_ref: str, start: int, end: int) -> "SourceSpan":
        surface = exact_content_ref(surface_ref, "surface_ref", prefix="reviewed_surface:")
        first = exact_int(start, "source span start", maximum=MAX_R4_TEXT_CHARS)
        last = exact_int(end, "source span end", maximum=MAX_R4_TEXT_CHARS)
        if last <= first:
            raise ValueError("source span must have positive width")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "surface_ref": surface,
            "start": first,
            "end": last,
        }
        return construct(cls, span_ref=stable_ref("source_span_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "span_ref": self.span_ref,
            "surface_ref": self.surface_ref,
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceSpan":
        row = exact_fields(value, cls._FIELDS, "SourceSpan")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        rebuilt = cls.create(surface_ref=row["surface_ref"], start=row["start"], end=row["end"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical SourceSpan")
        return rebuilt


@dataclass(frozen=True, init=False)
class GroundedSelectorBinding:
    abi_version: int
    binding_ref: str
    binding_kind: str
    selector_handle: int
    selector_kind: str
    source_case_ref: str
    surface_ref: str
    graph_component_ref: str
    semantic_kind_ref: str
    spans: tuple[SourceSpan, ...]
    source_selector_kind: str
    source_selector_ref: str

    _FIELDS = frozenset(
        {
            "abi_version", "binding_ref", "binding_kind", "selector_handle",
            "selector_kind", "source_case_ref", "surface_ref", "graph_component_ref",
            "semantic_kind_ref", "spans", "source_selector_kind", "source_selector_ref",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("GroundedSelectorBinding")

    @classmethod
    def create(
        cls,
        *,
        selector_handle: int,
        selector_kind: str,
        source_case_ref: str,
        surface_ref: str,
        graph_component_ref: str,
        semantic_kind_ref: str,
        spans: tuple[SourceSpan, ...],
        source_selector_kind: str,
        source_selector_ref: str,
    ) -> "GroundedSelectorBinding":
        handle = exact_int(selector_handle, "selector_handle", maximum=MAX_SELECTOR_BINDINGS - 1)
        kind = exact_text(selector_kind, "selector_kind", maximum=64)
        if kind not in _GROUNDED_SELECTOR_PREFIXES:
            raise ValueError("grounded selector kind is not closed or requires structural ownership")
        component = _exact_selector_ref(
            graph_component_ref,
            "graph_component_ref",
            prefixes=_GROUNDED_SELECTOR_PREFIXES[kind],
        )
        semantic_kind = _exact_selector_ref(
            semantic_kind_ref,
            "semantic kind ref",
            prefixes=("semantic_kind:",),
        )
        surface = exact_content_ref(surface_ref, "surface_ref", prefix="reviewed_surface:")
        if type(spans) is not tuple or not spans or len(spans) > MAX_SOURCE_SPANS:
            raise ValueError("grounded selector requires bounded nonempty source spans")
        if any(type(item) is not SourceSpan for item in spans):
            raise TypeError("grounded selector spans must contain exact SourceSpan values")
        canonical_spans = tuple(_canonical_nested(item, SourceSpan, "source span") for item in spans)
        if any(item.surface_ref != surface for item in canonical_spans):
            raise ValueError("grounded selector span surface does not match its exact surface")
        if any(
            left.start > right.start or left.end > right.start
            for left, right in zip(canonical_spans, canonical_spans[1:])
        ):
            raise ValueError("grounded selector spans must be ordered and non-overlapping")
        selector_source_kind = exact_text(source_selector_kind, "source selector kind", maximum=32)
        if selector_source_kind not in _SOURCE_SELECTOR_PREFIXES:
            raise ValueError("source selector kind must be exact unit or contribution")
        selector_source_ref = _exact_selector_ref(
            source_selector_ref,
            "source selector ref",
            prefixes=_SOURCE_SELECTOR_PREFIXES[selector_source_kind],
        )
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "binding_kind": "grounded",
            "selector_handle": handle,
            "selector_kind": kind,
            "source_case_ref": exact_case_ref(source_case_ref),
            "surface_ref": surface,
            "graph_component_ref": component,
            "semantic_kind_ref": semantic_kind,
            "spans": [item.as_dict() for item in canonical_spans],
            "source_selector_kind": selector_source_kind,
            "source_selector_ref": selector_source_ref,
        }
        return construct(
            cls,
            binding_ref=stable_ref("grounded_selector_binding_v1", material),
            spans=canonical_spans,
            **{key: item for key, item in material.items() if key != "spans"},
        )

    @property
    def value_ref(self) -> str:
        return self.graph_component_ref

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "binding_ref": self.binding_ref,
            "binding_kind": self.binding_kind,
            "selector_handle": self.selector_handle,
            "selector_kind": self.selector_kind,
            "source_case_ref": self.source_case_ref,
            "surface_ref": self.surface_ref,
            "graph_component_ref": self.graph_component_ref,
            "semantic_kind_ref": self.semantic_kind_ref,
            "spans": [item.as_dict() for item in self.spans],
            "source_selector_kind": self.source_selector_kind,
            "source_selector_ref": self.source_selector_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GroundedSelectorBinding":
        row = exact_fields(value, cls._FIELDS, "GroundedSelectorBinding")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        if row["binding_kind"] != "grounded":
            raise ValueError("grounded selector binding has the wrong union tag")
        rebuilt = cls.create(
            selector_handle=row["selector_handle"],
            selector_kind=row["selector_kind"],
            source_case_ref=row["source_case_ref"],
            surface_ref=row["surface_ref"],
            graph_component_ref=row["graph_component_ref"],
            semantic_kind_ref=row["semantic_kind_ref"],
            spans=wire_value_tuple(row["spans"], "spans", SourceSpan.from_dict, nonempty=True, maximum=MAX_SOURCE_SPANS),
            source_selector_kind=row["source_selector_kind"],
            source_selector_ref=row["source_selector_ref"],
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical GroundedSelectorBinding")
        return rebuilt


@dataclass(frozen=True, init=False)
class StructuralSelectorBinding:
    abi_version: int
    binding_ref: str
    binding_kind: str
    selector_handle: int
    selector_kind: str
    value_ref: str

    _FIELDS = frozenset({"abi_version", "binding_ref", "binding_kind", "selector_handle", "selector_kind", "value_ref"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("StructuralSelectorBinding")

    @classmethod
    def create(cls, *, selector_handle: int, selector_kind: str, value_ref: str) -> "StructuralSelectorBinding":
        handle = exact_int(selector_handle, "selector_handle", maximum=MAX_SELECTOR_BINDINGS - 1)
        kind = exact_text(selector_kind, "selector_kind", maximum=64)
        if kind not in _STRUCTURAL_SELECTOR_PREFIXES:
            raise ValueError("structural selector kind is closed; raw phrase, regex, and internal-ref spelling are forbidden")
        ref = _exact_selector_ref(
            value_ref,
            "structural selector value_ref",
            prefixes=_STRUCTURAL_SELECTOR_PREFIXES[kind],
        )
        if kind == "variant_tag" and ref not in {"action_variant:role", "action_variant:link"}:
            raise ValueError("structural selector closed literal is forbidden")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "binding_kind": "structural",
            "selector_handle": handle,
            "selector_kind": kind,
            "value_ref": ref,
        }
        return construct(cls, binding_ref=stable_ref("structural_selector_binding_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "binding_ref": self.binding_ref,
            "binding_kind": self.binding_kind,
            "selector_handle": self.selector_handle,
            "selector_kind": self.selector_kind,
            "value_ref": self.value_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StructuralSelectorBinding":
        row = exact_fields(value, cls._FIELDS, "StructuralSelectorBinding")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        if row["binding_kind"] != "structural":
            raise ValueError("structural selector binding has the wrong union tag")
        rebuilt = cls.create(selector_handle=row["selector_handle"], selector_kind=row["selector_kind"], value_ref=row["value_ref"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical StructuralSelectorBinding")
        return rebuilt


SelectorBinding = GroundedSelectorBinding | StructuralSelectorBinding


def selector_binding_from_dict(value: Mapping[str, Any]) -> SelectorBinding:
    if type(value) is not dict:
        raise TypeError("selector binding must be an exact object")
    tag = value.get("binding_kind")
    if tag == "grounded":
        return GroundedSelectorBinding.from_dict(value)
    if tag == "structural":
        return StructuralSelectorBinding.from_dict(value)
    raise ValueError("selector binding has an unsupported closed union tag")


def _canonical_selector_binding(value: object) -> SelectorBinding:
    if type(value) not in {GroundedSelectorBinding, StructuralSelectorBinding}:
        raise TypeError("selector bindings must contain exact closed-union values")
    try:
        rebuilt = selector_binding_from_dict(value.as_dict())
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("selector binding is not canonical") from exc
    if rebuilt != value:
        raise ValueError("selector binding is not canonical")
    return rebuilt


@dataclass(frozen=True, init=False)
class SourceAssignmentEntry:
    abi_version: int
    assignment_ref: str
    source_unit_ref: str
    contribution_slot_ref: str
    contribution_kind: str
    assignment_kind: str
    target_action_index: int | None
    target_role_ref: str | None
    residual_kind: str | None
    critical: bool

    _FIELDS = frozenset(
        {
            "abi_version", "assignment_ref", "source_unit_ref", "contribution_slot_ref", "contribution_kind",
            "assignment_kind", "target_action_index", "target_role_ref", "residual_kind", "critical",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("SourceAssignmentEntry")

    @classmethod
    def create(
        cls,
        *,
        source_unit_ref: str,
        contribution_slot_ref: str,
        contribution_kind: str,
        assignment_kind: str,
        target_action_index: int | None,
        target_role_ref: str | None,
        residual_kind: str | None,
        critical: bool,
    ) -> "SourceAssignmentEntry":
        contribution = exact_text(contribution_kind, "contribution_kind", maximum=32)
        if contribution not in _CONTRIBUTION_KINDS:
            raise ValueError("source assignment has an unsupported contribution kind")
        assignment = exact_text(assignment_kind, "assignment_kind", maximum=32)
        if assignment not in _ASSIGNMENT_KINDS:
            raise ValueError("source assignment has an unsupported assignment kind")
        action_index = None if target_action_index is None else exact_int(target_action_index, "target_action_index", maximum=MAX_BLUEPRINT_ACTIONS - 1)
        role = None if target_role_ref is None else _exact_selector_ref(
            target_role_ref, "target_role_ref", prefixes=("role:",)
        )
        residual = None if residual_kind is None else exact_text(residual_kind, "residual_kind", maximum=32)
        is_critical = exact_bool(critical, "critical")
        if assignment == "residual":
            if (
                action_index is not None
                or role is not None
                or residual not in _CONTRIBUTION_KINDS
                or residual != contribution
            ):
                raise ValueError("residual assignment requires only one typed residual kind")
        else:
            if action_index is None or residual is not None:
                raise ValueError("consumed assignment requires a target action and no residual kind")
            requires_role = assignment in {"reference", "qualifier"} or (
                assignment == "role" and contribution not in {"binder", "open_variable"}
            )
            if requires_role != (role is not None):
                raise ValueError("consumed assignment target-role ownership is incompatible with its contribution")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "source_unit_ref": _exact_selector_ref(
                source_unit_ref, "source_unit_ref", prefixes=("unit:",)
            ),
            "contribution_slot_ref": _exact_selector_ref(
                contribution_slot_ref,
                "contribution_slot_ref",
                prefixes=("contribution_slot:",),
            ),
            "contribution_kind": contribution,
            "assignment_kind": assignment,
            "target_action_index": action_index,
            "target_role_ref": role,
            "residual_kind": residual,
            "critical": is_critical,
        }
        return construct(cls, assignment_ref=stable_ref("source_assignment_blueprint_entry_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "assignment_ref": self.assignment_ref,
            "source_unit_ref": self.source_unit_ref,
            "contribution_slot_ref": self.contribution_slot_ref,
            "contribution_kind": self.contribution_kind,
            "assignment_kind": self.assignment_kind,
            "target_action_index": self.target_action_index,
            "target_role_ref": self.target_role_ref,
            "residual_kind": self.residual_kind,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceAssignmentEntry":
        row = exact_fields(value, cls._FIELDS, "SourceAssignmentEntry")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        rebuilt = cls.create(
            source_unit_ref=row["source_unit_ref"], contribution_slot_ref=row["contribution_slot_ref"],
            contribution_kind=row["contribution_kind"],
            assignment_kind=row["assignment_kind"], target_action_index=row["target_action_index"],
            target_role_ref=row["target_role_ref"], residual_kind=row["residual_kind"], critical=row["critical"],
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical SourceAssignmentEntry")
        return rebuilt


@dataclass(frozen=True, init=False)
class SourceAssignmentBlueprint:
    abi_version: int
    source_assignment_blueprint_ref: str
    observed_source_unit_refs: tuple[str, ...]
    assignments: tuple[SourceAssignmentEntry, ...]

    _FIELDS = frozenset({"abi_version", "source_assignment_blueprint_ref", "observed_source_unit_refs", "assignments"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("SourceAssignmentBlueprint")

    @classmethod
    def create(
        cls,
        *,
        observed_source_unit_refs: tuple[str, ...],
        assignments: tuple[SourceAssignmentEntry, ...],
    ) -> "SourceAssignmentBlueprint":
        observed = exact_ref_tuple(
            observed_source_unit_refs,
            "observed_source_unit_refs",
            nonempty=True,
            maximum=MAX_SOURCE_ASSIGNMENTS,
            prefix="unit:",
            canonical_order=False,
        )
        if type(assignments) is not tuple or not assignments or len(assignments) > MAX_SOURCE_ASSIGNMENTS:
            raise ValueError("source assignments must be bounded and nonempty")
        if any(type(item) is not SourceAssignmentEntry for item in assignments):
            raise TypeError("source assignments must contain exact SourceAssignmentEntry values")
        canonical = tuple(_canonical_nested(item, SourceAssignmentEntry, "source assignment") for item in assignments)
        if tuple(item.source_unit_ref for item in canonical) != observed:
            raise ValueError("source assignments must cover the declared observed source units exactly once in order")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "observed_source_unit_refs": list(observed),
            "assignments": [item.as_dict() for item in canonical],
        }
        return construct(
            cls,
            source_assignment_blueprint_ref=stable_ref("source_assignment_blueprint_v1", material),
            observed_source_unit_refs=observed,
            assignments=canonical,
            abi_version=PROPOSAL_SUPERVISION_ABI_VERSION,
        )

    @property
    def has_critical_residual(self) -> bool:
        return any(item.assignment_kind == "residual" and item.critical for item in self.assignments)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "source_assignment_blueprint_ref": self.source_assignment_blueprint_ref,
            "observed_source_unit_refs": list(self.observed_source_unit_refs),
            "assignments": [item.as_dict() for item in self.assignments],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceAssignmentBlueprint":
        row = exact_fields(value, cls._FIELDS, "SourceAssignmentBlueprint")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        rebuilt = cls.create(
            observed_source_unit_refs=wire_ref_tuple(row["observed_source_unit_refs"], "observed_source_unit_refs", nonempty=True, maximum=MAX_SOURCE_ASSIGNMENTS, prefix="unit:", canonical_order=False),
            assignments=wire_value_tuple(row["assignments"], "assignments", SourceAssignmentEntry.from_dict, nonempty=True, maximum=MAX_SOURCE_ASSIGNMENTS),
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical SourceAssignmentBlueprint")
        return rebuilt


@dataclass(frozen=True, init=False)
class BlueprintAction:
    abi_version: int
    action_ref: str
    action_index: int
    action_type: str
    selector_handles: tuple[int, ...]

    _FIELDS = frozenset({"abi_version", "action_ref", "action_index", "action_type", "selector_handles"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("BlueprintAction")

    @classmethod
    def create(cls, *, action_index: int, action_type: str, selector_handles: tuple[int, ...]) -> "BlueprintAction":
        index = exact_int(action_index, "action_index", maximum=MAX_BLUEPRINT_ACTIONS - 1)
        action = exact_text(action_type, "action_type", maximum=64)
        if action not in SWITCH_ACTION_TYPES:
            raise ValueError("unsupported Program ABI 2 action type")
        if type(selector_handles) is not tuple or len(selector_handles) > MAX_SELECTORS_PER_ACTION:
            raise TypeError("selector_handles must be a bounded exact integer tuple")
        handles = tuple(exact_int(item, "selector handle", maximum=MAX_SELECTOR_BINDINGS - 1) for item in selector_handles)
        if len(handles) != len(set(handles)):
            raise ValueError("action contains duplicate selector handles")
        repeated_lengths = tuple(
            range(len(variant) + 1, len(variant) + 24)
            if variant[-1:] == ("operand_node_refs[2:24]",)
            else (len(variant),)
            for variant in ACTION_ABI_SCHEMAS[action]
        )
        if len(handles) not in {length for lengths in repeated_lengths for length in lengths}:
            raise ValueError("selector handle count does not match the Program ABI 2 action shape")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "action_index": index,
            "action_type": action,
            "selector_handles": list(handles),
        }
        return construct(cls, action_ref=stable_ref("derivation_action_v1", material), selector_handles=handles, **{key: item for key, item in material.items() if key != "selector_handles"})

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "action_ref": self.action_ref,
            "action_index": self.action_index,
            "action_type": self.action_type,
            "selector_handles": list(self.selector_handles),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BlueprintAction":
        row = exact_fields(value, cls._FIELDS, "BlueprintAction")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        if type(row["selector_handles"]) is not list:
            raise TypeError("selector_handles wire value must be an exact list")
        rebuilt = cls.create(action_index=row["action_index"], action_type=row["action_type"], selector_handles=tuple(row["selector_handles"]))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical BlueprintAction")
        return rebuilt


@dataclass(frozen=True, init=False)
class DerivationBlueprint:
    abi_version: int
    blueprint_ref: str
    program_abi_version: int
    action_abi_ref: str
    selector_bindings: tuple[SelectorBinding, ...]
    actions: tuple[BlueprintAction, ...]
    root_local_refs: tuple[str, ...]
    expected_expression_ref: str
    source_assignment_blueprint: SourceAssignmentBlueprint

    _FIELDS = frozenset(
        {
            "abi_version", "blueprint_ref", "program_abi_version", "action_abi_ref",
            "selector_bindings", "actions", "root_local_refs", "expected_expression_ref",
            "source_assignment_blueprint",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("DerivationBlueprint")

    @classmethod
    def create(
        cls,
        *,
        selector_bindings: tuple[SelectorBinding, ...],
        actions: tuple[BlueprintAction, ...],
        root_local_refs: tuple[str, ...],
        expected_expression_ref: str,
        source_assignment_blueprint: SourceAssignmentBlueprint,
    ) -> "DerivationBlueprint":
        if type(selector_bindings) is not tuple or not selector_bindings or len(selector_bindings) > MAX_SELECTOR_BINDINGS:
            raise ValueError("selector binding table must be bounded and nonempty")
        canonical_bindings = tuple(_canonical_selector_binding(item) for item in selector_bindings)
        if tuple(item.selector_handle for item in canonical_bindings) != tuple(range(len(canonical_bindings))):
            raise ValueError("selector binding handles must be dense, unique and in exact order")
        if type(actions) is not tuple or not actions or len(actions) > MAX_BLUEPRINT_ACTIONS:
            raise ValueError("derivation blueprint violates its action bound")
        if any(type(item) is not BlueprintAction for item in actions):
            raise TypeError("actions must contain exact BlueprintAction values")
        canonical_actions = tuple(
            _canonical_nested(item, BlueprintAction, "action") for item in actions
        )
        if tuple(item.action_index for item in canonical_actions) != tuple(range(len(canonical_actions))):
            raise ValueError("blueprint action indices must be contiguous")
        types = tuple(item.action_type for item in canonical_actions)
        if len(actions) < 3 or types[:2] != ("select_context", "select_mode") or types[-1] != "complete_program":
            raise ValueError("derive blueprint must select context/mode and end complete_program")
        if "abstain" in types or types.count("select_context") != 1 or types.count("select_mode") != 1 or types.count("complete_program") != 1:
            raise ValueError("derive blueprint has an invalid Program ABI 2 terminal structure")
        used_handles = {
            handle for action in canonical_actions for handle in action.selector_handles
        }
        if any(handle >= len(canonical_bindings) for handle in used_handles):
            raise ValueError("blueprint action contains an unbound selector handle")
        if used_handles != set(range(len(canonical_bindings))):
            raise ValueError("every selector binding handle must be referenced by an action exactly as reviewed")
        for action in canonical_actions:
            if not any(
                _matches_action_variant(canonical_bindings, action.selector_handles, variant)
                for variant in ACTION_ABI_SCHEMAS[action.action_type]
            ):
                raise ValueError("selector bindings do not match the Program ABI 2 action shape")
        roots = exact_ref_tuple(root_local_refs, "root_local_refs", nonempty=True, maximum=8)
        declared: set[str] = set()
        for action in canonical_actions:
            selectors = tuple(canonical_bindings[handle] for handle in action.selector_handles)
            declarations: tuple[str, ...] = ()
            uses: tuple[str, ...] = ()
            if action.action_type == "instantiate_operator":
                declarations = (selectors[0].value_ref,)
            elif action.action_type in {"bind_role", "bind_reference"}:
                uses = (selectors[0].value_ref,)
            elif action.action_type == "bind_nested_application":
                if selectors[0].value_ref == "action_variant:role":
                    uses = (selectors[1].value_ref, selectors[3].value_ref)
                else:
                    declarations = (selectors[1].value_ref,)
                    uses = tuple(item.value_ref for item in selectors[3:])
            elif action.action_type in {"attach_scope", "project_variable"}:
                declarations = (selectors[0].value_ref,)
                uses = (selectors[2].value_ref,)
            elif action.action_type == "propose_transition":
                uses = (selectors[1].value_ref,)
            if any(ref not in declared for ref in uses):
                raise ValueError("blueprint uses a local node before declaration")
            if any(ref in declared for ref in declarations):
                raise ValueError("blueprint contains a duplicate local declaration")
            declared.update(declarations)
        if any(root not in declared for root in roots):
            raise ValueError("blueprint root is not a declared source-local node")
        assignment_blueprint = _canonical_nested(
            source_assignment_blueprint, SourceAssignmentBlueprint, "source_assignment_blueprint"
        )
        for assignment in assignment_blueprint.assignments:
            if assignment.target_action_index is None:
                continue
            if assignment.target_action_index >= len(canonical_actions):
                raise ValueError("source assignment target action is not in the blueprint")
            target_action = canonical_actions[assignment.target_action_index]
            compatibility = (
                assignment.contribution_kind,
                assignment.assignment_kind,
                target_action.action_type,
            )
            if compatibility not in _SOURCE_ASSIGNMENT_COMPATIBILITY:
                raise ValueError(
                    "source assignment contribution, assignment kind and target action are incompatible"
                )
            target_bindings = tuple(
                canonical_bindings[handle] for handle in target_action.selector_handles
            )
            if target_action.action_type == "bind_nested_application" and (
                not target_bindings or target_bindings[0].value_ref != "action_variant:link"
            ):
                raise ValueError("connector/discourse assignment requires the link action variant")
            contribution_bindings = tuple(
                row
                for row in target_bindings
                if type(row) is GroundedSelectorBinding
                and row.source_selector_kind == "contribution"
                and row.source_selector_ref == assignment.contribution_slot_ref
            )
            if len(contribution_bindings) != 1:
                raise ValueError(
                    "source assignment contribution slot must resolve once through its target action"
                )
            if assignment.target_role_ref is not None:
                if not any(
                    row.selector_kind == "role_ref" and row.value_ref == assignment.target_role_ref
                    for row in target_bindings
                ):
                    raise ValueError("source assignment target role is not bound by its target action")
        expression_ref = exact_content_ref(expected_expression_ref, "expected_expression_ref", prefix="expression:")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "program_abi_version": PROGRAM_ABI_VERSION,
            "action_abi_ref": ACTION_ABI_HASH,
            "selector_bindings": [item.as_dict() for item in canonical_bindings],
            "actions": [item.as_dict() for item in canonical_actions],
            "root_local_refs": list(roots),
            "expected_expression_ref": expression_ref,
            "source_assignment_blueprint": assignment_blueprint.as_dict(),
        }
        return construct(
            cls,
            blueprint_ref=stable_ref("derivation_blueprint_v1", material),
            selector_bindings=canonical_bindings,
            actions=canonical_actions,
            root_local_refs=roots,
            expected_expression_ref=expression_ref,
            source_assignment_blueprint=assignment_blueprint,
            abi_version=PROPOSAL_SUPERVISION_ABI_VERSION,
            program_abi_version=PROGRAM_ABI_VERSION,
            action_abi_ref=ACTION_ABI_HASH,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "blueprint_ref": self.blueprint_ref,
            "program_abi_version": self.program_abi_version,
            "action_abi_ref": self.action_abi_ref,
            "selector_bindings": [item.as_dict() for item in self.selector_bindings],
            "actions": [item.as_dict() for item in self.actions],
            "root_local_refs": list(self.root_local_refs),
            "expected_expression_ref": self.expected_expression_ref,
            "source_assignment_blueprint": self.source_assignment_blueprint.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DerivationBlueprint":
        row = exact_fields(value, cls._FIELDS, "DerivationBlueprint")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        exact_abi(row["program_abi_version"], PROGRAM_ABI_VERSION, "Program")
        if row["action_abi_ref"] != ACTION_ABI_HASH:
            raise ValueError("unsupported Program action ABI")
        if type(row["selector_bindings"]) is not list or not row["selector_bindings"] or len(row["selector_bindings"]) > MAX_SELECTOR_BINDINGS:
            raise ValueError("selector binding wire table violates its bound")
        if any(type(item) is not dict for item in row["selector_bindings"]):
            raise TypeError("selector binding wire rows must be exact objects")
        if type(row["source_assignment_blueprint"]) is not dict:
            raise TypeError("source_assignment_blueprint must be an exact object")
        rebuilt = cls.create(
            selector_bindings=tuple(selector_binding_from_dict(item) for item in row["selector_bindings"]),
            actions=wire_value_tuple(row["actions"], "actions", BlueprintAction.from_dict, nonempty=True, maximum=MAX_BLUEPRINT_ACTIONS),
            root_local_refs=wire_ref_tuple(row["root_local_refs"], "root_local_refs", nonempty=True, maximum=8),
            expected_expression_ref=row["expected_expression_ref"],
            source_assignment_blueprint=SourceAssignmentBlueprint.from_dict(row["source_assignment_blueprint"]),
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DerivationBlueprint")
        return rebuilt


@dataclass(frozen=True, init=False)
class TypedAbstention:
    abi_version: int
    abstention_ref: str
    gap_kind_ref: str
    critical: bool
    earliest_owner: str
    safe_disposition: str

    _FIELDS = frozenset({"abi_version", "abstention_ref", "gap_kind_ref", "critical", "earliest_owner", "safe_disposition"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("TypedAbstention")

    @classmethod
    def create(cls, *, gap_kind_ref: str, critical: bool, earliest_owner: str, safe_disposition: str) -> "TypedAbstention":
        owner = exact_text(earliest_owner, "earliest_owner", maximum=16)
        disposition = exact_text(safe_disposition, "safe_disposition", maximum=16)
        if owner not in _OWNER_PHASES:
            raise ValueError("unsupported earliest owner")
        if disposition not in _SAFE_DISPOSITIONS:
            raise ValueError("unsupported safe disposition")
        material = {"abi_version": PROPOSAL_SUPERVISION_ABI_VERSION, "gap_kind_ref": exact_ref(gap_kind_ref, "gap_kind_ref", prefix="gap_kind:"), "critical": exact_bool(critical, "critical"), "earliest_owner": owner, "safe_disposition": disposition}
        return construct(cls, abstention_ref=stable_ref("typed_abstention_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "abstention_ref": self.abstention_ref, "gap_kind_ref": self.gap_kind_ref, "critical": self.critical, "earliest_owner": self.earliest_owner, "safe_disposition": self.safe_disposition}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TypedAbstention":
        row = exact_fields(value, cls._FIELDS, "TypedAbstention")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        rebuilt = cls.create(gap_kind_ref=row["gap_kind_ref"], critical=row["critical"], earliest_owner=row["earliest_owner"], safe_disposition=row["safe_disposition"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical TypedAbstention")
        return rebuilt


@dataclass(frozen=True, init=False)
class VerificationRejection:
    abi_version: int
    verification_rejection_ref: str
    input_kind: str
    adversarial_blueprint_ref: str | None
    mutation_payload_ref: str | None
    expected_owner: str
    verification_error_code: str
    rejection_disposition: str
    critical: bool

    _FIELDS = frozenset(
        {
            "abi_version", "verification_rejection_ref", "input_kind",
            "adversarial_blueprint_ref", "mutation_payload_ref", "expected_owner",
            "verification_error_code", "rejection_disposition", "critical",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("VerificationRejection")

    @classmethod
    def create(
        cls,
        *,
        input_kind: str,
        adversarial_blueprint_ref: str | None,
        mutation_payload_ref: str | None,
        expected_owner: str,
        verification_error_code: str,
        rejection_disposition: str,
        critical: bool,
    ) -> "VerificationRejection":
        kind = exact_text(input_kind, "verification rejection input_kind", maximum=32)
        if kind not in {"adversarial_blueprint", "mutation_payload"}:
            raise ValueError("verification rejection requires an exact adversarial blueprint or mutation payload input")
        adversarial = None if adversarial_blueprint_ref is None else exact_content_ref(
            adversarial_blueprint_ref, "adversarial_blueprint_ref", prefix="adversarial_blueprint:"
        )
        mutation = None if mutation_payload_ref is None else exact_content_ref(
            mutation_payload_ref, "mutation_payload_ref", prefix="mutation_payload:"
        )
        if (kind == "adversarial_blueprint") != (adversarial is not None) or (
            kind == "mutation_payload"
        ) != (mutation is not None):
            raise ValueError("verification rejection input tag and payload do not match exactly")
        if (adversarial is None) == (mutation is None):
            raise ValueError("verification rejection requires exactly one reviewed input")
        owner = exact_text(expected_owner, "verification rejection expected owner", maximum=16)
        if owner != "verify":
            raise ValueError("verification rejection expected owner must be verify")
        error_code = exact_ref(
            verification_error_code, "verification_error_code", prefix="verification_error:"
        )
        disposition = exact_text(rejection_disposition, "rejection_disposition", maximum=16)
        if disposition != "reject":
            raise ValueError("verification rejection disposition must be reject")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "input_kind": kind,
            "adversarial_blueprint_ref": adversarial,
            "mutation_payload_ref": mutation,
            "expected_owner": owner,
            "verification_error_code": error_code,
            "rejection_disposition": disposition,
            "critical": exact_bool(critical, "critical"),
        }
        return construct(
            cls,
            verification_rejection_ref=stable_ref("verification_rejection_v1", material),
            **material,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "verification_rejection_ref": self.verification_rejection_ref,
            "input_kind": self.input_kind,
            "adversarial_blueprint_ref": self.adversarial_blueprint_ref,
            "mutation_payload_ref": self.mutation_payload_ref,
            "expected_owner": self.expected_owner,
            "verification_error_code": self.verification_error_code,
            "rejection_disposition": self.rejection_disposition,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationRejection":
        row = exact_fields(value, cls._FIELDS, "VerificationRejection")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        rebuilt = cls.create(
            input_kind=row["input_kind"],
            adversarial_blueprint_ref=row["adversarial_blueprint_ref"],
            mutation_payload_ref=row["mutation_payload_ref"],
            expected_owner=row["expected_owner"],
            verification_error_code=row["verification_error_code"],
            rejection_disposition=row["rejection_disposition"],
            critical=row["critical"],
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical VerificationRejection")
        return rebuilt


@dataclass(frozen=True, init=False)
class ProposalTarget:
    abi_version: int
    proposal_target_ref: str
    source_case_ref: str
    target_kind: str
    expected_expression_refs: tuple[str, ...]
    match_policy: str
    expected_expression_relation: str
    derivations: tuple[DerivationBlueprint, ...]
    abstention: TypedAbstention | None
    verification_rejection: VerificationRejection | None
    review_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version", "proposal_target_ref", "source_case_ref", "target_kind",
            "expected_expression_refs", "match_policy", "expected_expression_relation",
            "derivations", "abstention", "verification_rejection", "review_refs",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ProposalTarget")

    @classmethod
    def create(
        cls,
        *,
        source_case_ref: str,
        target_kind: str,
        expected_expression_refs: tuple[str, ...],
        match_policy: str,
        expected_expression_relation: str,
        derivations: tuple[DerivationBlueprint, ...],
        abstention: TypedAbstention | None,
        verification_rejection: VerificationRejection | None,
        review_refs: tuple[str, ...],
    ) -> "ProposalTarget":
        case_ref = exact_case_ref(source_case_ref)
        kind = exact_text(target_kind, "target_kind", maximum=32)
        if kind not in {"derive", "abstain", "verification_rejection"}:
            raise ValueError("unsupported proposal target kind")
        policy = exact_text(match_policy, "match_policy", maximum=5)
        if policy != "exact":
            raise ValueError("proposal supervision match_policy must be exact")
        relation = exact_text(expected_expression_relation, "expected_expression_relation", maximum=16)
        if relation not in {"none", "single", "conflict"}:
            raise ValueError("unsupported expected expression relation")
        expressions = exact_content_ref_tuple(
            expected_expression_refs,
            "expected_expression_refs",
            nonempty=kind == "derive",
            maximum=MAX_DERIVATIONS_PER_CASE,
            prefix="expression:",
        )
        if type(derivations) is not tuple or len(derivations) > MAX_DERIVATIONS_PER_CASE:
            raise ValueError("proposal target violates its derivation bound")
        if any(type(item) is not DerivationBlueprint for item in derivations):
            raise TypeError("derivations must contain exact DerivationBlueprint values")
        canonical_derivations = tuple(
            _canonical_nested(item, DerivationBlueprint, "derivation") for item in derivations
        )
        canonical_abstention = (
            None
            if abstention is None
            else _canonical_nested(abstention, TypedAbstention, "abstention")
        )
        canonical_rejection = (
            None
            if verification_rejection is None
            else _canonical_nested(
                verification_rejection, VerificationRejection, "verification_rejection"
            )
        )
        if len({item.blueprint_ref for item in canonical_derivations}) != len(canonical_derivations):
            raise ValueError("proposal target contains duplicate derivations")
        if tuple(item.blueprint_ref for item in canonical_derivations) != tuple(sorted(item.blueprint_ref for item in canonical_derivations)):
            raise ValueError("derivations must be in canonical order")
        grounded_bindings = tuple(
            binding
            for derivation in canonical_derivations
            for binding in derivation.selector_bindings
            if type(binding) is GroundedSelectorBinding
        )
        if any(binding.source_case_ref != case_ref for binding in grounded_bindings):
            raise ValueError("grounded selector binding belongs to a different source case")
        if len({binding.surface_ref for binding in grounded_bindings}) > 1:
            raise ValueError("grounded selector bindings cross exact source surfaces")
        if kind == "derive":
            required_relation = "single" if len(expressions) == 1 else "conflict"
            if relation != required_relation:
                raise ValueError("derive expression cardinality and expected relation disagree")
            if not canonical_derivations or canonical_abstention is not None or canonical_rejection is not None:
                raise ValueError("derive target requires derivations and no abstention or rejection")
            mapped = {item.expected_expression_ref for item in canonical_derivations}
            if mapped != set(expressions):
                raise ValueError("derive alternatives must each be explicitly mapped by a derivation")
            if any(item.source_assignment_blueprint.has_critical_residual for item in canonical_derivations):
                raise ValueError("critical residual makes a derive target non-executable")
        elif kind == "abstain":
            if relation != "none" or expressions or canonical_derivations or type(canonical_abstention) is not TypedAbstention or canonical_rejection is not None:
                raise ValueError("abstain target requires relation none and only one typed abstention")
        elif (
            relation != "none"
            or expressions
            or canonical_derivations
            or canonical_abstention is not None
            or type(canonical_rejection) is not VerificationRejection
        ):
            raise ValueError("verification rejection target requires relation none and only exact rejection truth")
        material = {
            "abi_version": PROPOSAL_SUPERVISION_ABI_VERSION,
            "source_case_ref": case_ref,
            "target_kind": kind,
            "expected_expression_refs": list(expressions),
            "match_policy": "exact",
            "expected_expression_relation": relation,
            "derivations": [item.as_dict() for item in canonical_derivations],
            "abstention": None if canonical_abstention is None else canonical_abstention.as_dict(),
            "verification_rejection": None if canonical_rejection is None else canonical_rejection.as_dict(),
            "review_refs": list(exact_review_refs(review_refs)),
        }
        return construct(
            cls,
            proposal_target_ref=stable_ref("proposal_supervision_v1", material),
            expected_expression_refs=expressions,
            derivations=canonical_derivations,
            abstention=canonical_abstention,
            verification_rejection=canonical_rejection,
            review_refs=tuple(material["review_refs"]),
            **{
                key: val
                for key, val in material.items()
                if key not in {"expected_expression_refs", "derivations", "abstention", "verification_rejection", "review_refs"}
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "proposal_target_ref": self.proposal_target_ref,
            "source_case_ref": self.source_case_ref,
            "target_kind": self.target_kind,
            "expected_expression_refs": list(self.expected_expression_refs),
            "match_policy": self.match_policy,
            "expected_expression_relation": self.expected_expression_relation,
            "derivations": [item.as_dict() for item in self.derivations],
            "abstention": None if self.abstention is None else self.abstention.as_dict(),
            "verification_rejection": None if self.verification_rejection is None else self.verification_rejection.as_dict(),
            "review_refs": list(self.review_refs),
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProposalTarget":
        row = exact_fields(value, cls._FIELDS, "ProposalTarget")
        exact_abi(row["abi_version"], PROPOSAL_SUPERVISION_ABI_VERSION, "Proposal Supervision")
        if row["abstention"] is not None and type(row["abstention"]) is not dict:
            raise TypeError("abstention must be an exact object or null")
        if row["verification_rejection"] is not None and type(row["verification_rejection"]) is not dict:
            raise TypeError("verification_rejection must be an exact object or null")
        rebuilt = cls.create(
            source_case_ref=row["source_case_ref"],
            target_kind=row["target_kind"],
            expected_expression_refs=wire_content_ref_tuple(row["expected_expression_refs"], "expected_expression_refs", nonempty=row["target_kind"] == "derive", maximum=MAX_DERIVATIONS_PER_CASE, prefix="expression:"),
            match_policy=row["match_policy"],
            expected_expression_relation=row["expected_expression_relation"],
            derivations=wire_value_tuple(row["derivations"], "derivations", DerivationBlueprint.from_dict, nonempty=row["target_kind"] == "derive", maximum=MAX_DERIVATIONS_PER_CASE),
            abstention=None if row["abstention"] is None else TypedAbstention.from_dict(row["abstention"]),
            verification_rejection=None if row["verification_rejection"] is None else VerificationRejection.from_dict(row["verification_rejection"]),
            review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True),
        )
        if rebuilt.proposal_target_ref != row["proposal_target_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ProposalTarget")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "ProposalTarget":
        return strict_decode(raw, cls.from_dict, owner="proposal supervision")


@dataclass(frozen=True, init=False)
class ExpressionSetResponseSubject:
    abi_version: int
    response_subject_ref: str
    subject_kind: str
    expected_expression_relation: str
    expression_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "response_subject_ref",
            "subject_kind",
            "expected_expression_relation",
            "expression_refs",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ExpressionSetResponseSubject")

    @classmethod
    def create(
        cls,
        *,
        expected_expression_relation: str,
        expression_refs: tuple[str, ...],
    ) -> "ExpressionSetResponseSubject":
        relation = exact_text(
            expected_expression_relation,
            "expected_expression_relation",
            maximum=16,
        )
        expressions = exact_content_ref_tuple(
            expression_refs,
            "expression_refs",
            nonempty=True,
            maximum=MAX_DERIVATIONS_PER_CASE,
            prefix="expression:",
        )
        expected = "single" if len(expressions) == 1 else "conflict"
        if relation != expected:
            raise ValueError(
                "expression-set relation must be single for one expression and conflict for alternatives"
            )
        material = {
            "abi_version": REALIZATION_SUPERVISION_ABI_VERSION,
            "subject_kind": "expression_set",
            "expected_expression_relation": relation,
            "expression_refs": list(expressions),
        }
        return construct(
            cls,
            response_subject_ref=stable_ref("response_subject_v1", material),
            expression_refs=expressions,
            **{key: value for key, value in material.items() if key != "expression_refs"},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "response_subject_ref": self.response_subject_ref,
            "subject_kind": self.subject_kind,
            "expected_expression_relation": self.expected_expression_relation,
            "expression_refs": list(self.expression_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpressionSetResponseSubject":
        row = exact_fields(value, cls._FIELDS, "ExpressionSetResponseSubject")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["subject_kind"] != "expression_set":
            raise ValueError("response subject kind is not expression_set")
        rebuilt = cls.create(
            expected_expression_relation=row["expected_expression_relation"],
            expression_refs=wire_content_ref_tuple(
                row["expression_refs"],
                "expression_refs",
                nonempty=True,
                maximum=MAX_DERIVATIONS_PER_CASE,
                prefix="expression:",
            ),
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical expression-set response subject")
        return rebuilt


@dataclass(frozen=True, init=False)
class TypedGapResponseSubject:
    abi_version: int
    response_subject_ref: str
    subject_kind: str
    expected_expression_relation: str
    typed_gap: TypedAbstention

    _FIELDS = frozenset(
        {
            "abi_version",
            "response_subject_ref",
            "subject_kind",
            "expected_expression_relation",
            "typed_gap",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("TypedGapResponseSubject")

    @classmethod
    def create(cls, *, typed_gap: TypedAbstention) -> "TypedGapResponseSubject":
        gap = _canonical_nested(typed_gap, TypedAbstention, "typed gap")
        material = {
            "abi_version": REALIZATION_SUPERVISION_ABI_VERSION,
            "subject_kind": "typed_gap",
            "expected_expression_relation": "none",
            "typed_gap": gap.as_dict(),
        }
        return construct(
            cls,
            response_subject_ref=stable_ref("response_subject_v1", material),
            typed_gap=gap,
            **{key: value for key, value in material.items() if key != "typed_gap"},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "response_subject_ref": self.response_subject_ref,
            "subject_kind": self.subject_kind,
            "expected_expression_relation": self.expected_expression_relation,
            "typed_gap": self.typed_gap.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TypedGapResponseSubject":
        row = exact_fields(value, cls._FIELDS, "TypedGapResponseSubject")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["subject_kind"] != "typed_gap" or row["expected_expression_relation"] != "none":
            raise ValueError("typed-gap response subject must use relation none")
        if type(row["typed_gap"]) is not dict:
            raise TypeError("typed_gap must be an exact object")
        rebuilt = cls.create(typed_gap=TypedAbstention.from_dict(row["typed_gap"]))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical typed-gap response subject")
        return rebuilt


@dataclass(frozen=True, init=False)
class VerifierRejectionResponseSubject:
    abi_version: int
    response_subject_ref: str
    subject_kind: str
    expected_expression_relation: str
    verifier_rejection: VerificationRejection

    _FIELDS = frozenset(
        {
            "abi_version",
            "response_subject_ref",
            "subject_kind",
            "expected_expression_relation",
            "verifier_rejection",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("VerifierRejectionResponseSubject")

    @classmethod
    def create(
        cls, *, verifier_rejection: VerificationRejection
    ) -> "VerifierRejectionResponseSubject":
        rejection = _canonical_nested(
            verifier_rejection, VerificationRejection, "verifier rejection"
        )
        material = {
            "abi_version": REALIZATION_SUPERVISION_ABI_VERSION,
            "subject_kind": "verifier_rejection",
            "expected_expression_relation": "none",
            "verifier_rejection": rejection.as_dict(),
        }
        return construct(
            cls,
            response_subject_ref=stable_ref("response_subject_v1", material),
            verifier_rejection=rejection,
            **{
                key: value
                for key, value in material.items()
                if key != "verifier_rejection"
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "response_subject_ref": self.response_subject_ref,
            "subject_kind": self.subject_kind,
            "expected_expression_relation": self.expected_expression_relation,
            "verifier_rejection": self.verifier_rejection.as_dict(),
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "VerifierRejectionResponseSubject":
        row = exact_fields(value, cls._FIELDS, "VerifierRejectionResponseSubject")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if (
            row["subject_kind"] != "verifier_rejection"
            or row["expected_expression_relation"] != "none"
        ):
            raise ValueError("verifier-rejection response subject must use relation none")
        if type(row["verifier_rejection"]) is not dict:
            raise TypeError("verifier_rejection must be an exact object")
        rebuilt = cls.create(
            verifier_rejection=VerificationRejection.from_dict(
                row["verifier_rejection"]
            )
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical verifier-rejection response subject")
        return rebuilt


ResponseSubject = (
    ExpressionSetResponseSubject
    | TypedGapResponseSubject
    | VerifierRejectionResponseSubject
)


def response_subject_from_dict(value: Mapping[str, Any]) -> ResponseSubject:
    if type(value) is not dict:
        raise TypeError("response subject must be an exact object")
    kind = value.get("subject_kind")
    decoder = {
        "expression_set": ExpressionSetResponseSubject.from_dict,
        "typed_gap": TypedGapResponseSubject.from_dict,
        "verifier_rejection": VerifierRejectionResponseSubject.from_dict,
    }.get(kind)
    if decoder is None:
        raise ValueError("response subject kind is outside the closed union")
    return decoder(value)


def _canonical_response_subject(value: object) -> ResponseSubject:
    if type(value) not in {
        ExpressionSetResponseSubject,
        TypedGapResponseSubject,
        VerifierRejectionResponseSubject,
    }:
        raise TypeError("response_subject must be one exact closed-union value")
    rebuilt = response_subject_from_dict(value.as_dict())
    if rebuilt != value:
        raise ValueError("response subject is not canonical")
    return rebuilt


@dataclass(frozen=True, init=False)
class RealizationBinding:
    abi_version: int
    binding_ref: str
    binding_key_ref: str
    semantic_ref: str

    _FIELDS = frozenset({"abi_version", "binding_ref", "binding_key_ref", "semantic_ref"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("RealizationBinding")

    @classmethod
    def create(cls, *, binding_key_ref: str, semantic_ref: str) -> "RealizationBinding":
        material = {
            "abi_version": REALIZATION_SUPERVISION_ABI_VERSION,
            "binding_key_ref": exact_ref(binding_key_ref, "binding_key_ref", prefix="binding_key:"),
            "semantic_ref": exact_ref(semantic_ref, "semantic_ref"),
        }
        return construct(cls, binding_ref=stable_ref("realization_binding_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "binding_ref": self.binding_ref,
            "binding_key_ref": self.binding_key_ref,
            "semantic_ref": self.semantic_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RealizationBinding":
        row = exact_fields(value, cls._FIELDS, "RealizationBinding")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        rebuilt = cls.create(
            binding_key_ref=row["binding_key_ref"], semantic_ref=row["semantic_ref"]
        )
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical RealizationBinding")
        return rebuilt


@dataclass(frozen=True, init=False)
class RealizationSlot:
    abi_version: int
    slot_ref: str
    semantic_ref: str
    required: bool
    qualifier_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "slot_ref", "semantic_ref", "required", "qualifier_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("RealizationSlot")

    @classmethod
    def create(cls, *, slot_ref: str, semantic_ref: str, required: bool, qualifier_refs: tuple[str, ...]) -> "RealizationSlot":
        exact_required = exact_bool(required, "required")
        return construct(cls, abi_version=REALIZATION_SUPERVISION_ABI_VERSION, slot_ref=exact_ref(slot_ref, "slot_ref", prefix="response_slot:"), semantic_ref=exact_ref(semantic_ref, "semantic_ref"), required=exact_required, qualifier_refs=exact_ref_tuple(qualifier_refs, "qualifier_refs", nonempty=False, maximum=128, prefix="qualifier:"))

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "slot_ref": self.slot_ref, "semantic_ref": self.semantic_ref, "required": self.required, "qualifier_refs": list(self.qualifier_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RealizationSlot":
        row = exact_fields(value, cls._FIELDS, "RealizationSlot")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        rebuilt = cls.create(slot_ref=row["slot_ref"], semantic_ref=row["semantic_ref"], required=row["required"], qualifier_refs=wire_ref_tuple(row["qualifier_refs"], "qualifier_refs", nonempty=False, maximum=128, prefix="qualifier:"))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical RealizationSlot")
        return rebuilt


def _surface_span(start: object, end: object) -> tuple[int, int]:
    if type(start) is not int or type(end) is not int:
        raise TypeError("realization alignment spans must use exact integers")
    exact_start = exact_int(start, "surface_start", maximum=MAX_R4_TEXT_CHARS)
    exact_end = exact_int(end, "surface_end", maximum=MAX_R4_TEXT_CHARS)
    if exact_start >= exact_end:
        raise ValueError("realization alignment must own one positive output span")
    return exact_start, exact_end


def _alignment_material(
    *, alignment_kind: str, slot_ref: str, surface_start: object, surface_end: object
) -> dict[str, Any]:
    start, end = _surface_span(surface_start, surface_end)
    return {
        "abi_version": REALIZATION_SUPERVISION_ABI_VERSION,
        "alignment_kind": alignment_kind,
        "slot_ref": exact_ref(slot_ref, "slot_ref", prefix="response_slot:"),
        "surface_start": start,
        "surface_end": end,
    }


@dataclass(frozen=True, init=False)
class DesignationAlignment:
    abi_version: int
    alignment_ref: str
    alignment_kind: str
    slot_ref: str
    designation_fact_ref: str
    surface_start: int
    surface_end: int

    _FIELDS = frozenset(
        {
            "abi_version", "alignment_ref", "alignment_kind", "slot_ref",
            "designation_fact_ref", "surface_start", "surface_end",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("DesignationAlignment")

    @classmethod
    def create(cls, *, slot_ref: str, designation_fact_ref: str, surface_start: int, surface_end: int) -> "DesignationAlignment":
        material = {
            **_alignment_material(alignment_kind="designation", slot_ref=slot_ref, surface_start=surface_start, surface_end=surface_end),
            "designation_fact_ref": exact_content_ref(designation_fact_ref, "designation_fact_ref", prefix="designation:"),
        }
        return construct(cls, alignment_ref=stable_ref("realization_alignment_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._FIELDS}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DesignationAlignment":
        row = exact_fields(value, cls._FIELDS, "DesignationAlignment")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["alignment_kind"] != "designation":
            raise ValueError("designation alignment has the wrong tag")
        rebuilt = cls.create(slot_ref=row["slot_ref"], designation_fact_ref=row["designation_fact_ref"], surface_start=row["surface_start"], surface_end=row["surface_end"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical designation alignment")
        return rebuilt


@dataclass(frozen=True, init=False)
class ReferenceAlignment:
    abi_version: int
    alignment_ref: str
    alignment_kind: str
    slot_ref: str
    participant_ref: str
    reference_authority_ref: str
    surface_start: int
    surface_end: int

    _FIELDS = frozenset(
        {
            "abi_version", "alignment_ref", "alignment_kind", "slot_ref",
            "participant_ref", "reference_authority_ref", "surface_start", "surface_end",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ReferenceAlignment")

    @classmethod
    def create(cls, *, slot_ref: str, participant_ref: str, reference_authority_ref: str, surface_start: int, surface_end: int) -> "ReferenceAlignment":
        material = {
            **_alignment_material(alignment_kind="reference", slot_ref=slot_ref, surface_start=surface_start, surface_end=surface_end),
            "participant_ref": exact_ref(participant_ref, "participant_ref", prefix="participant:"),
            "reference_authority_ref": exact_content_ref(reference_authority_ref, "reference_authority_ref", prefix="source_review:"),
        }
        return construct(cls, alignment_ref=stable_ref("realization_alignment_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._FIELDS}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceAlignment":
        row = exact_fields(value, cls._FIELDS, "ReferenceAlignment")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["alignment_kind"] != "reference":
            raise ValueError("reference alignment has the wrong tag")
        rebuilt = cls.create(slot_ref=row["slot_ref"], participant_ref=row["participant_ref"], reference_authority_ref=row["reference_authority_ref"], surface_start=row["surface_start"], surface_end=row["surface_end"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical reference alignment")
        return rebuilt


@dataclass(frozen=True, init=False)
class LiteralAlignment:
    abi_version: int
    alignment_ref: str
    alignment_kind: str
    slot_ref: str
    literal_source_ref: str
    surface_start: int
    surface_end: int

    _FIELDS = frozenset(
        {
            "abi_version", "alignment_ref", "alignment_kind", "slot_ref",
            "literal_source_ref", "surface_start", "surface_end",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("LiteralAlignment")

    @classmethod
    def create(cls, *, slot_ref: str, literal_source_ref: str, surface_start: int, surface_end: int) -> "LiteralAlignment":
        source_ref = exact_text(literal_source_ref, "literal_source_ref")
        source_prefix = next(
            (
                prefix
                for prefix in (
                    "reviewed_literal:",
                    "decision_literal:",
                    "effect_literal:",
                    "obligation_literal:",
                )
                if source_ref.startswith(prefix)
            ),
            None,
        )
        if source_prefix is None:
            raise ValueError("literal alignment requires independent reviewed or boundary-authenticated literal authority")
        source_ref = exact_content_ref(
            source_ref,
            "literal_source_ref",
            prefix=source_prefix,
        )
        material = {
            **_alignment_material(alignment_kind="literal", slot_ref=slot_ref, surface_start=surface_start, surface_end=surface_end),
            "literal_source_ref": source_ref,
        }
        return construct(cls, alignment_ref=stable_ref("realization_alignment_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._FIELDS}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LiteralAlignment":
        row = exact_fields(value, cls._FIELDS, "LiteralAlignment")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["alignment_kind"] != "literal":
            raise ValueError("literal alignment has the wrong tag")
        rebuilt = cls.create(slot_ref=row["slot_ref"], literal_source_ref=row["literal_source_ref"], surface_start=row["surface_start"], surface_end=row["surface_end"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical literal alignment")
        return rebuilt


@dataclass(frozen=True, init=False)
class MorphologyAlignment:
    abi_version: int
    alignment_ref: str
    alignment_kind: str
    slot_ref: str
    morphology_authority_ref: str
    surface_start: int
    surface_end: int

    _FIELDS = frozenset(
        {
            "abi_version", "alignment_ref", "alignment_kind", "slot_ref",
            "morphology_authority_ref", "surface_start", "surface_end",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("MorphologyAlignment")

    @classmethod
    def create(cls, *, slot_ref: str, morphology_authority_ref: str, surface_start: int, surface_end: int) -> "MorphologyAlignment":
        material = {
            **_alignment_material(alignment_kind="morphology", slot_ref=slot_ref, surface_start=surface_start, surface_end=surface_end),
            "morphology_authority_ref": exact_content_ref(morphology_authority_ref, "morphology_authority_ref", prefix="source_review:"),
        }
        return construct(cls, alignment_ref=stable_ref("realization_alignment_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._FIELDS}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MorphologyAlignment":
        row = exact_fields(value, cls._FIELDS, "MorphologyAlignment")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["alignment_kind"] != "morphology":
            raise ValueError("morphology alignment has the wrong tag")
        rebuilt = cls.create(slot_ref=row["slot_ref"], morphology_authority_ref=row["morphology_authority_ref"], surface_start=row["surface_start"], surface_end=row["surface_end"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical morphology alignment")
        return rebuilt


@dataclass(frozen=True, init=False)
class OmissionAlignment:
    abi_version: int
    alignment_ref: str
    alignment_kind: str
    slot_ref: str
    omission_authority_ref: str
    surface_start: None
    surface_end: None

    _FIELDS = frozenset(
        {"abi_version", "alignment_ref", "alignment_kind", "slot_ref", "omission_authority_ref", "surface_start", "surface_end"}
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("OmissionAlignment")

    @classmethod
    def create(cls, *, slot_ref: str, omission_authority_ref: str) -> "OmissionAlignment":
        material = {
            "abi_version": REALIZATION_SUPERVISION_ABI_VERSION,
            "alignment_kind": "omission",
            "slot_ref": exact_ref(slot_ref, "slot_ref", prefix="response_slot:"),
            "omission_authority_ref": exact_content_ref(omission_authority_ref, "omission_authority_ref", prefix="source_review:"),
            "surface_start": None,
            "surface_end": None,
        }
        return construct(cls, alignment_ref=stable_ref("realization_alignment_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._FIELDS}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OmissionAlignment":
        row = exact_fields(value, cls._FIELDS, "OmissionAlignment")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if row["alignment_kind"] != "omission":
            raise ValueError("omission alignment has the wrong tag")
        if row["surface_start"] is not None or row["surface_end"] is not None:
            raise ValueError("omission alignment must use canonical null output geometry")
        rebuilt = cls.create(slot_ref=row["slot_ref"], omission_authority_ref=row["omission_authority_ref"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical omission alignment")
        return rebuilt


RealizationAlignment = (
    DesignationAlignment
    | ReferenceAlignment
    | LiteralAlignment
    | MorphologyAlignment
    | OmissionAlignment
)


def realization_alignment_from_dict(value: Mapping[str, Any]) -> RealizationAlignment:
    if type(value) is not dict:
        raise TypeError("realization alignment must be an exact object")
    decoder = {
        "designation": DesignationAlignment.from_dict,
        "reference": ReferenceAlignment.from_dict,
        "literal": LiteralAlignment.from_dict,
        "morphology": MorphologyAlignment.from_dict,
        "omission": OmissionAlignment.from_dict,
    }.get(value.get("alignment_kind"))
    if decoder is None:
        raise ValueError("realization alignment kind is outside the closed union")
    return decoder(value)


def _canonical_alignment(value: object) -> RealizationAlignment:
    if type(value) not in {
        DesignationAlignment,
        ReferenceAlignment,
        LiteralAlignment,
        MorphologyAlignment,
        OmissionAlignment,
    }:
        raise TypeError("alignment must be one exact closed-union value")
    rebuilt = realization_alignment_from_dict(value.as_dict())
    if rebuilt != value:
        raise ValueError("realization alignment is not canonical")
    return rebuilt


@dataclass(frozen=True, init=False)
class RealizationRow:
    abi_version: int
    realization_ref: str
    source_case_ref: str
    response_signature_ref: str
    response_subject: ResponseSubject
    bindings: tuple[RealizationBinding, ...]
    discourse_action_ref: str
    polarity_ref: str
    modality_ref: str
    epistemic_status_ref: str
    output_speaker_ref: str
    output_addressee_ref: str
    authorized_surface: str
    language: str
    semantic_slots: tuple[RealizationSlot, ...]
    alignments: tuple[RealizationAlignment, ...]
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "realization_ref", "source_case_ref", "response_signature_ref", "response_subject", "bindings", "discourse_action_ref", "polarity_ref", "modality_ref", "epistemic_status_ref", "output_speaker_ref", "output_addressee_ref", "authorized_surface", "language", "semantic_slots", "alignments", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("RealizationRow")

    @classmethod
    def create(cls, *, source_case_ref: str, response_subject: ResponseSubject, bindings: tuple[RealizationBinding, ...], discourse_action_ref: str, polarity_ref: str, modality_ref: str, epistemic_status_ref: str, output_speaker_ref: str, output_addressee_ref: str, authorized_surface: str, language: str, semantic_slots: tuple[RealizationSlot, ...], alignments: tuple[RealizationAlignment, ...], review_refs: tuple[str, ...]) -> "RealizationRow":
        surface = exact_text(authorized_surface, "authorized_surface", maximum=MAX_R4_TEXT_CHARS)
        if not surface.strip() or surface.strip().casefold() in {
            "[no authorized surface]",
            "[no surface]",
        }:
            raise ValueError("authorized_surface must be a nonblank reviewed surface, never a UI placeholder")
        language_value = exact_text(language, "language", maximum=64)
        if _LANGUAGE_RE.fullmatch(language_value) is None:
            raise ValueError("language is not canonical")
        reviews = exact_review_refs(review_refs)
        exact_bindings = exact_value_tuple(bindings, "bindings", RealizationBinding, nonempty=False, maximum=MAX_REALIZATION_BINDINGS, identity=lambda item: item.binding_key_ref)
        exact_bindings = tuple(_canonical_nested(item, RealizationBinding, "binding") for item in exact_bindings)
        slots = exact_value_tuple(semantic_slots, "semantic_slots", RealizationSlot, nonempty=True, maximum=MAX_REALIZATION_SLOTS, identity=lambda item: item.slot_ref)
        slots = tuple(_canonical_nested(item, RealizationSlot, "semantic slot") for item in slots)
        subject = _canonical_response_subject(response_subject)
        if type(alignments) is not tuple or len(alignments) > MAX_REALIZATION_ALIGNMENTS:
            raise TypeError("alignments must be one bounded exact tuple")
        exact_alignments = tuple(_canonical_alignment(item) for item in alignments)
        alignment_refs = tuple(item.alignment_ref for item in exact_alignments)
        if len(alignment_refs) != len(set(alignment_refs)):
            raise ValueError("alignments contain duplicate identities")
        alignment_order = tuple(
            (item.slot_ref, item.alignment_kind, item.alignment_ref)
            for item in exact_alignments
        )
        if any(left >= right for left, right in zip(alignment_order, alignment_order[1:])):
            raise ValueError("alignments must be in canonical slot/tag/ref order")
        slots_by_ref = {item.slot_ref: item for item in slots}
        review_ref_set = set(reviews)
        coverage: dict[str, int] = {slot_ref: 0 for slot_ref in slots_by_ref}
        for alignment in exact_alignments:
            slot = slots_by_ref.get(alignment.slot_ref)
            if slot is None:
                raise ValueError("realization alignment targets an unknown semantic slot")
            coverage[alignment.slot_ref] += 1
            if type(alignment) is not OmissionAlignment and alignment.surface_end > len(surface):
                raise ValueError("realization alignment output span exceeds the authorized surface")
            if (
                type(alignment) is LiteralAlignment
                and alignment.literal_source_ref.startswith("reviewed_literal:")
                and alignment.literal_source_ref
                != stable_ref(
                    "reviewed_literal",
                    {
                        "literal": surface[
                            alignment.surface_start : alignment.surface_end
                        ],
                        "language": language_value,
                        "review_refs": list(reviews),
                    },
                )
            ):
                raise ValueError(
                    "reviewed literal alignment must resolve to the exact reviewed output projection"
                )
            if (
                type(alignment) is ReferenceAlignment
                and alignment.participant_ref != slot.semantic_ref
            ):
                raise ValueError("reference alignment participant must equal its slot semantic ref")
            authority_ref = getattr(alignment, f"{alignment.alignment_kind}_authority_ref", None)
            if authority_ref is not None and authority_ref not in review_ref_set:
                raise ValueError("row-local alignment authority must resolve through review_refs")
        for slot in slots:
            count = coverage[slot.slot_ref]
            if slot.required and count != 1:
                raise ValueError("every required semantic slot must be covered exactly once")
            if not slot.required and count > 1:
                raise ValueError("an optional semantic slot cannot have duplicate coverage")
        action_ref = exact_ref(
            discourse_action_ref,
            "discourse_action_ref",
            prefix="response_action:",
        )
        exact_polarity_ref = exact_ref(
            polarity_ref, "polarity_ref", prefix="polarity:"
        )
        exact_modality_ref = exact_ref(
            modality_ref, "modality_ref", prefix="modality:"
        )
        exact_epistemic_ref = exact_epistemic_status_ref(epistemic_status_ref)
        speaker_ref = exact_ref(
            output_speaker_ref,
            "output_speaker_ref",
            prefix="participant:",
        )
        addressee_ref = exact_ref(
            output_addressee_ref,
            "output_addressee_ref",
            prefix="participant:",
        )
        if type(subject) in {
            TypedGapResponseSubject,
            VerifierRejectionResponseSubject,
        }:
            if exact_bindings:
                raise ValueError("safe gap and rejection responses cannot retain semantic bindings")
            if type(subject) is TypedGapResponseSubject:
                required_action_ref = "response_action:report_gap"
                required_slot_ref = "response_slot:gap"
                required_semantic_ref = subject.typed_gap.abstention_ref
            else:
                required_action_ref = "response_action:reject_candidate"
                required_slot_ref = "response_slot:verifier_rejection"
                required_semantic_ref = (
                    subject.verifier_rejection.verification_rejection_ref
                )
            if (
                action_ref != required_action_ref
                or exact_polarity_ref != "polarity:positive"
                or exact_modality_ref != "modality:actual"
                or exact_epistemic_ref != "epistemic_status:unknown"
            ):
                raise ValueError("safe response subject has a noncanonical response contract")
            if (
                len(slots) != 1
                or slots[0].slot_ref != required_slot_ref
                or slots[0].semantic_ref != required_semantic_ref
                or not slots[0].required
                or slots[0].qualifier_refs
            ):
                raise ValueError("safe response subject requires its one exact semantic slot")
            if (
                len(exact_alignments) != 1
                or type(exact_alignments[0]) is not LiteralAlignment
                or exact_alignments[0].slot_ref != required_slot_ref
                or exact_alignments[0].surface_start != 0
                or exact_alignments[0].surface_end != len(surface)
            ):
                raise ValueError("safe response subject requires one full-surface reviewed literal alignment")
        signature = {
            "response_subject": subject.as_dict(),
            "bindings": [item.as_dict() for item in exact_bindings],
            "discourse_action_ref": action_ref,
            "polarity_ref": exact_polarity_ref,
            "modality_ref": exact_modality_ref,
            "epistemic_status_ref": exact_epistemic_ref,
            "output_speaker_ref": speaker_ref,
            "output_addressee_ref": addressee_ref,
            "semantic_slots": [item.as_dict() for item in slots],
        }
        material = {"abi_version": REALIZATION_SUPERVISION_ABI_VERSION, "source_case_ref": exact_case_ref(source_case_ref), "response_signature_ref": stable_ref("response_signature", signature), **signature, "authorized_surface": surface, "language": language_value, "alignments": [item.as_dict() for item in exact_alignments], "review_refs": list(reviews)}
        return construct(cls, realization_ref=stable_ref("realization_supervision_v1", material), response_subject=subject, bindings=exact_bindings, semantic_slots=slots, alignments=exact_alignments, review_refs=tuple(material["review_refs"]), **{key: val for key, val in material.items() if key not in {"response_subject", "bindings", "semantic_slots", "alignments", "review_refs"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "realization_ref": self.realization_ref, "source_case_ref": self.source_case_ref, "response_signature_ref": self.response_signature_ref, "response_subject": self.response_subject.as_dict(), "bindings": [item.as_dict() for item in self.bindings], "discourse_action_ref": self.discourse_action_ref, "polarity_ref": self.polarity_ref, "modality_ref": self.modality_ref, "epistemic_status_ref": self.epistemic_status_ref, "output_speaker_ref": self.output_speaker_ref, "output_addressee_ref": self.output_addressee_ref, "authorized_surface": self.authorized_surface, "language": self.language, "semantic_slots": [item.as_dict() for item in self.semantic_slots], "alignments": [item.as_dict() for item in self.alignments], "review_refs": list(self.review_refs)}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RealizationRow":
        row = exact_fields(value, cls._FIELDS, "RealizationRow")
        exact_abi(row["abi_version"], REALIZATION_SUPERVISION_ABI_VERSION, "Realization Supervision")
        if type(row["response_subject"]) is not dict:
            raise TypeError("response_subject must be an exact object")
        if type(row["alignments"]) is not list or len(row["alignments"]) > MAX_REALIZATION_ALIGNMENTS:
            raise TypeError("alignments wire value must be one bounded exact array")
        rebuilt = cls.create(source_case_ref=row["source_case_ref"], response_subject=response_subject_from_dict(row["response_subject"]), bindings=wire_value_tuple(row["bindings"], "bindings", RealizationBinding.from_dict, nonempty=False, maximum=MAX_REALIZATION_BINDINGS), discourse_action_ref=row["discourse_action_ref"], polarity_ref=row["polarity_ref"], modality_ref=row["modality_ref"], epistemic_status_ref=row["epistemic_status_ref"], output_speaker_ref=row["output_speaker_ref"], output_addressee_ref=row["output_addressee_ref"], authorized_surface=row["authorized_surface"], language=row["language"], semantic_slots=wire_value_tuple(row["semantic_slots"], "semantic_slots", RealizationSlot.from_dict, nonempty=True, maximum=MAX_REALIZATION_SLOTS), alignments=tuple(realization_alignment_from_dict(item) for item in row["alignments"]), review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.response_signature_ref != row["response_signature_ref"] or rebuilt.realization_ref != row["realization_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical RealizationRow")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "RealizationRow":
        return strict_decode(raw, cls.from_dict, owner="realization supervision")


@dataclass(frozen=True, init=False)
class MutationContract:
    abi_version: int
    mutation_contract_ref: str
    mutation_family_ref: str
    source_case_ref: str
    changed_dimension_ref: str
    expected_earliest_owner: str
    disposition: str
    effect_kind: str
    expected_effect_ref: str | None
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "mutation_contract_ref", "mutation_family_ref", "source_case_ref", "changed_dimension_ref", "expected_earliest_owner", "disposition", "effect_kind", "expected_effect_ref", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("MutationContract")

    @classmethod
    def create(cls, *, mutation_family_ref: str, source_case_ref: str, changed_dimension_ref: str, expected_earliest_owner: str, disposition: str, effect_kind: str, expected_effect_ref: str | None, review_refs: tuple[str, ...]) -> "MutationContract":
        owner = exact_text(expected_earliest_owner, "expected_earliest_owner", maximum=16)
        if owner not in _OWNER_PHASES:
            raise ValueError("unsupported expected earliest owner")
        exact_disposition = exact_text(disposition, "disposition", maximum=16)
        if exact_disposition not in _MUTATION_DISPOSITIONS:
            raise ValueError("unsupported mutation disposition")
        kind = exact_text(effect_kind, "effect_kind", maximum=16)
        if kind not in {"effect", "no_effect"}:
            raise ValueError("unsupported effect kind")
        effect_ref = _wire_optional_ref(expected_effect_ref, "expected_effect_ref")
        if (kind == "effect") != (effect_ref is not None):
            raise ValueError("effect ref must be present exactly for an effect contract")
        material = {"abi_version": MUTATION_CONTRACT_ABI_VERSION, "mutation_family_ref": exact_ref(mutation_family_ref, "mutation_family_ref", prefix="mutation_family:"), "source_case_ref": exact_case_ref(source_case_ref), "changed_dimension_ref": exact_ref(changed_dimension_ref, "changed_dimension_ref"), "expected_earliest_owner": owner, "disposition": exact_disposition, "effect_kind": kind, "expected_effect_ref": effect_ref, "review_refs": list(exact_review_refs(review_refs))}
        return construct(cls, mutation_contract_ref=stable_ref("mutation_contract_v1", material), review_refs=tuple(material["review_refs"]), **{key: val for key, val in material.items() if key != "review_refs"})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "mutation_contract_ref": self.mutation_contract_ref, "mutation_family_ref": self.mutation_family_ref, "source_case_ref": self.source_case_ref, "changed_dimension_ref": self.changed_dimension_ref, "expected_earliest_owner": self.expected_earliest_owner, "disposition": self.disposition, "effect_kind": self.effect_kind, "expected_effect_ref": self.expected_effect_ref, "review_refs": list(self.review_refs)}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MutationContract":
        row = exact_fields(value, cls._FIELDS, "MutationContract")
        exact_abi(row["abi_version"], MUTATION_CONTRACT_ABI_VERSION, "Mutation Contract")
        rebuilt = cls.create(mutation_family_ref=row["mutation_family_ref"], source_case_ref=row["source_case_ref"], changed_dimension_ref=row["changed_dimension_ref"], expected_earliest_owner=row["expected_earliest_owner"], disposition=row["disposition"], effect_kind=row["effect_kind"], expected_effect_ref=row["expected_effect_ref"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.mutation_contract_ref != row["mutation_contract_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical MutationContract")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "MutationContract":
        return strict_decode(raw, cls.from_dict, owner="mutation contract")


__all__ = [
    "AuthenticatedR4ReviewBundle",
    "AuthenticatedR4SourceBytes",
    "MAX_R4_REVIEW_BUNDLE_BYTES",
    "MAX_R4_SOURCE_READ_SYSCALLS",
    "MUTATION_CONTRACT_ABI_VERSION",
    "PROPOSAL_SUPERVISION_ABI_VERSION",
    "R4_REVIEW_MANIFEST_ABI_VERSION",
    "R4_REVIEW_BUNDLE_READ_COUNT",
    "R4_REVIEW_MANIFEST_PATH",
    "R4_REVIEW_SOURCE_FILE_COUNT",
    "R4_SCENARIO_SOURCE_PATH",
    "REALIZATION_SUPERVISION_ABI_VERSION",
    "MAX_BLUEPRINT_ACTIONS",
    "MAX_DERIVATIONS_PER_CASE",
    "MAX_REALIZATION_ALIGNMENTS",
    "MAX_REALIZATION_BINDINGS",
    "MAX_REALIZATION_SLOTS",
    "MAX_REALIZATION_VARIANTS_PER_CASE",
    "MAX_SELECTOR_BINDINGS",
    "MAX_SOURCE_ASSIGNMENTS",
    "MAX_SOURCE_SPANS",
    "BlueprintAction",
    "CrossSourceValidationResult",
    "DerivationBlueprint",
    "DesignationAlignment",
    "ExpressionSetResponseSubject",
    "GroundedSelectorBinding",
    "LiteralAlignment",
    "MorphologyAlignment",
    "MutationContract",
    "OmissionAlignment",
    "ProposalTarget",
    "R4ReviewManifest",
    "RealizationBinding",
    "RealizationAlignment",
    "RealizationRow",
    "RealizationSlot",
    "ReferenceAlignment",
    "ReviewSourceFile",
    "SelectorBinding",
    "SourceAssignmentBlueprint",
    "SourceAssignmentEntry",
    "SourceSpan",
    "StructuralSelectorBinding",
    "TypedAbstention",
    "TypedGapResponseSubject",
    "ResponseSubject",
    "VerificationRejection",
    "VerifierRejectionResponseSubject",
    "SourceDisposition",
    "selector_binding_from_dict",
    "realization_alignment_from_dict",
    "response_subject_from_dict",
    "source_disposition_is_supervision_eligible",
    "load_authenticated_r4_review_bundle",
    "validate_authenticated_r4_source_semantics",
]
