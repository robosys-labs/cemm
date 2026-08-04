"""Bounded append-only governance for the Hybrid MVP corrective replay.

The normal loader verifies the authority-pinned initial prefix and every suffix
record against immutable Git commit bytes.  This module is external governance;
the cognitive runtime never imports it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Callable, Mapping, NoReturn, Sequence

from .canonical import stable_ref
from .process_control import ProcessControlError, capture_bounded_process


STATUS_SCHEMA = "cemm-replay-status-record-v1"
INVALIDATION_SCHEMA = "cemm-receipt-invalidation-record-v1"
ANCHOR_SCHEMA = "cemm-governance-ledger-anchors-v1"
PHASES = ("G0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")
REPLAY_STATUSES = frozenset({"pending", "red", "green", "externally_blocked"})
MAX_LEDGER_BYTES = 128 * 1024
MAX_LEDGER_LINE_BYTES = 8 * 1024
MAX_GIT_INPUT_BYTES = 16 * 1024 * 1024
MAX_LEDGER_RECORDS = 128
MAX_COMMIT_GRAPH_BYTES = 16 * 1024 * 1024
MAX_COMMIT_GRAPH_RECORDS = 65_536
MAX_GIT_METADATA_BYTES = 256 * 1024
MAX_GIT_STDERR_BYTES = 64 * 1024
GIT_TIMEOUT_SECONDS = 60
MAX_GOVERNED_JSON_BYTES = 1024 * 1024
INITIAL_STATUS = {
    "G0": "pending",
    "R1": "red",
    "R2": "red",
    "R3": "red",
    "R4": "red",
    "R5": "red",
    "R6": "red",
    "R7": "red",
    "R8": "red",
}
STATUS_FIELDS = frozenset({
    "schema",
    "sequence",
    "predecessor_ref",
    "source_base",
    "phase",
    "status",
    "admission_gate_result_ref",
    "admission_run_ref",
    "rationale",
    "record_ref",
})
INVALIDATION_FIELDS = frozenset({
    "schema",
    "sequence",
    "predecessor_ref",
    "source_base",
    "subject",
    "subject_sha256",
    "disposition",
    "rationale",
    "record_ref",
})
_COMMIT_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_CONTENT_REF_RE = re.compile(
    r"[a-z][a-z0-9_-]*(?::[a-z0-9_-]+)*:[0-9a-f]{24}\Z"
)
_GATE_RESULT_REF_RE = re.compile(r"gate_result:[0-9a-f]{24}\Z")
_RUN_REF_RE = re.compile(r"run:[0-9a-f]{24}\Z")


class GovernanceError(ValueError):
    """Raised when governed replay evidence fails closed."""


@dataclass(frozen=True)
class LedgerAnchor:
    """Authority-pinned exact initial bytes for one ledger."""

    ledger_path: str
    record_schema: str
    initial_count: int
    genesis_ref: str
    initial_head_ref: str
    initial_bytes_size: int
    initial_bytes_sha256: str
    source_base: str

    def __post_init__(self) -> None:
        path = PurePosixPath(self.ledger_path)
        if (
            type(self.ledger_path) is not str
            or path.is_absolute()
            or ".." in path.parts
            or not self.ledger_path.startswith("governance/")
        ):
            raise GovernanceError("ledger anchor has an unsafe ledger_path")
        if type(self.record_schema) is not str or self.record_schema not in {STATUS_SCHEMA, INVALIDATION_SCHEMA}:
            raise GovernanceError("ledger anchor has unknown record_schema")
        if type(self.initial_count) is not int or self.initial_count <= 0:
            raise GovernanceError("ledger anchor initial_count must be a positive integer")
        if type(self.initial_bytes_size) is not int or self.initial_bytes_size <= 0:
            raise GovernanceError("ledger anchor initial_bytes_size must be positive")
        for field in ("genesis_ref", "initial_head_ref"):
            value = getattr(self, field)
            if type(value) is not str or _CONTENT_REF_RE.fullmatch(value) is None:
                raise GovernanceError(f"ledger anchor has invalid {field}")
        if (
            type(self.initial_bytes_sha256) is not str
            or _SHA256_RE.fullmatch(self.initial_bytes_sha256) is None
        ):
            raise GovernanceError("ledger anchor has invalid initial_bytes_sha256")
        if type(self.source_base) is not str or _COMMIT_RE.fullmatch(self.source_base) is None:
            raise GovernanceError("ledger anchor has invalid source_base")


@dataclass(frozen=True)
class _PrefixWitness:
    revision: str
    expected_size: int


@dataclass(frozen=True)
class _CheckedBlob:
    revision: str
    object_id: str
    expected_size: int


@dataclass
class _CommitGraph:
    boundary_ref: str
    head_ref: str
    parents: dict[str, tuple[str, ...]]
    ancestry_cache: dict[tuple[str, str], bool] = field(default_factory=dict)


def _require_exact_fields(
    record: Mapping[str, object], expected: frozenset[str], *, sequence: int
) -> None:
    actual = set(record)
    if actual != expected:
        raise GovernanceError(
            f"record {sequence} has non-exact fields; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def _require_text(value: object, field: str, *, sequence: int) -> str:
    if type(value) is not str or not value.strip():
        raise GovernanceError(f"record {sequence} field {field} must be non-empty text")
    return value


def _require_content_ref(value: object, field: str, *, sequence: int) -> str:
    if type(value) is not str or _CONTENT_REF_RE.fullmatch(value) is None:
        raise GovernanceError(f"record {sequence} has invalid {field}")
    return value


def _validate_common(record: Mapping[str, object], *, sequence: int) -> None:
    if type(record.get("sequence")) is not int or record["sequence"] != sequence:
        raise GovernanceError(f"record {sequence} has invalid sequence")
    source_base = record.get("source_base")
    if type(source_base) is not str or _COMMIT_RE.fullmatch(source_base) is None:
        raise GovernanceError(f"record {sequence} has invalid source_base")
    predecessor = record.get("predecessor_ref")
    if predecessor is not None:
        _require_content_ref(predecessor, "predecessor_ref", sequence=sequence)
    _require_text(record.get("rationale"), "rationale", sequence=sequence)
    _require_content_ref(record.get("record_ref"), "record_ref", sequence=sequence)


def _validate_status_record(record: Mapping[str, object], *, sequence: int) -> None:
    _require_exact_fields(record, STATUS_FIELDS, sequence=sequence)
    _validate_common(record, sequence=sequence)
    if type(record["schema"]) is not str or record["schema"] != STATUS_SCHEMA:
        raise GovernanceError(f"record {sequence} has invalid status schema")
    phase = record["phase"]
    if type(phase) is not str or phase not in PHASES:
        raise GovernanceError(f"record {sequence} has invalid phase")
    status = record["status"]
    if type(status) is not str or status not in REPLAY_STATUSES:
        raise GovernanceError(f"record {sequence} has invalid status")
    gate_ref = record["admission_gate_result_ref"]
    run_ref = record["admission_run_ref"]
    if status in {"green", "externally_blocked"}:
        if type(gate_ref) is not str or _GATE_RESULT_REF_RE.fullmatch(gate_ref) is None:
            raise GovernanceError(
                f"record {sequence} has invalid admission_gate_result_ref"
            )
        if type(run_ref) is not str or _RUN_REF_RE.fullmatch(run_ref) is None:
            raise GovernanceError(f"record {sequence} has invalid admission_run_ref")
    elif gate_ref is not None or run_ref is not None:
        raise GovernanceError(
            f"record {sequence} non-admission status cannot consume receipt refs"
        )


def _validate_subject(subject: object, *, sequence: int) -> str:
    value = _require_text(subject, "subject", sequence=sequence)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise GovernanceError(f"record {sequence} subject is not a safe relative path")
    if not path.parts or path.parts[0] != "artifacts":
        raise GovernanceError(f"record {sequence} subject must be under artifacts/")
    return value


def _validate_invalidation_record(
    record: Mapping[str, object], *, sequence: int
) -> None:
    _require_exact_fields(record, INVALIDATION_FIELDS, sequence=sequence)
    _validate_common(record, sequence=sequence)
    if type(record["schema"]) is not str or record["schema"] != INVALIDATION_SCHEMA:
        raise GovernanceError(f"record {sequence} has invalid invalidation schema")
    _validate_subject(record["subject"], sequence=sequence)
    digest = record["subject_sha256"]
    if type(digest) is not str or _SHA256_RE.fullmatch(digest) is None:
        raise GovernanceError(f"record {sequence} has invalid subject_sha256")
    if (
        type(record["disposition"]) is not str
        or record["disposition"] != "invalidated_for_corrective_replay"
    ):
        raise GovernanceError(f"record {sequence} has invalid disposition")


def expected_record_ref(record: Mapping[str, object]) -> str:
    material = dict(record)
    material.pop("record_ref", None)
    return stable_ref("governance_record", material)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GovernanceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> NoReturn:
    raise GovernanceError(f"non-finite JSON constant is forbidden: {value}")


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise GovernanceError("governed value is not canonical JSON") from exc


def canonical_jsonl_row(record: Mapping[str, object]) -> bytes:
    return _canonical_json_bytes(dict(record)) + b"\n"


def parse_and_validate_records(raw: bytes) -> tuple[dict[str, object], ...]:
    if not raw:
        raise GovernanceError("ledger is empty")
    if len(raw) > MAX_LEDGER_BYTES:
        raise GovernanceError("ledger exceeds its external governance byte bound")
    if not raw.endswith(b"\n"):
        raise GovernanceError("ledger must end with one newline")
    lines = raw.split(b"\n")
    lines.pop()
    if len(lines) > MAX_LEDGER_RECORDS:
        raise GovernanceError("ledger contains too many records")
    if not lines or any(not line for line in lines):
        raise GovernanceError("ledger contains a blank JSONL row")
    if any(len(line) > MAX_LEDGER_LINE_BYTES for line in lines):
        raise GovernanceError("ledger JSONL row exceeds its byte bound")

    records: list[dict[str, object]] = []
    predecessor: str | None = None
    for sequence, line in enumerate(lines):
        try:
            decoded = line.decode("utf-8")
            record = json.loads(
                decoded,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except GovernanceError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            raise GovernanceError(f"record {sequence} is not canonical JSON") from exc
        if type(record) is not dict:
            raise GovernanceError(f"record {sequence} must be a JSON object")
        if _canonical_json_bytes(record) != line:
            raise GovernanceError(f"record {sequence} is not canonical JSON")
        schema = record.get("schema")
        if schema == STATUS_SCHEMA:
            _validate_status_record(record, sequence=sequence)
        elif schema == INVALIDATION_SCHEMA:
            _validate_invalidation_record(record, sequence=sequence)
        else:
            raise GovernanceError(f"record {sequence} has unknown schema")
        if record["predecessor_ref"] != predecessor:
            raise GovernanceError(f"record {sequence} predecessor does not match prior head")
        if record["record_ref"] != expected_record_ref(record):
            raise GovernanceError(f"record {sequence} content ref mismatch")
        predecessor = str(record["record_ref"])
        records.append(record)
    return tuple(records)


def _read_governed_bytes(
    path: Path,
    *,
    maximum: int,
    source_reader: Callable[[Path], bytes] | None,
    context: str,
) -> bytes:
    try:
        if source_reader is None:
            with path.open("rb") as stream:
                raw = stream.read(maximum + 1)
        else:
            raw = source_reader(path)
    except GovernanceError:
        raise
    except (OSError, ValueError, KeyError) as exc:
        raise GovernanceError(f"cannot read {context}: {path}") from exc
    if type(raw) is not bytes:
        raise GovernanceError(f"{context} reader did not return exact bytes: {path}")
    if not raw or len(raw) > maximum:
        raise GovernanceError(f"{context} exceeds its byte bound: {path}")
    return raw


def _decode_governed_json(raw: bytes, *, path: Path) -> dict[str, object]:
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except GovernanceError:
        raise
    except (
        UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError,
    ) as exc:
        raise GovernanceError(f"cannot read governed JSON: {path}") from exc
    if type(value) is not dict:
        raise GovernanceError(f"governed JSON must be an object: {path}")
    return value


def _load_json(
    path: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, object]:
    raw = _read_governed_bytes(
        path,
        maximum=MAX_GOVERNED_JSON_BYTES,
        source_reader=source_reader,
        context="governed JSON",
    )
    return _decode_governed_json(raw, path=path)


def _verify_anchor_pin(
    root: Path,
    anchors_path: Path,
    anchors_raw: bytes,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> None:
    authority = _load_json(
        root / "docs" / "DOCUMENT_AUTHORITY.json",
        source_reader=source_reader,
    )
    pin = authority.get("governance_ledger_anchors")
    if type(pin) is not dict or set(pin) != {"path", "sha256"}:
        raise GovernanceError("document authority lacks an exact ledger-anchor pin")
    if type(pin["path"]) is not str or pin["path"] != "governance/ledger_anchors.json":
        raise GovernanceError("document authority has an unsafe ledger-anchor path")
    digest = pin["sha256"]
    if type(digest) is not str or _SHA256_RE.fullmatch(digest) is None:
        raise GovernanceError("document authority has an invalid ledger-anchor digest")
    pinned = (root / pin["path"]).resolve()
    try:
        pinned.relative_to(root.resolve())
    except ValueError as exc:
        raise GovernanceError("ledger-anchor pin escapes the hybrid root") from exc
    if pinned != anchors_path.resolve():
        raise GovernanceError("ledger-anchor pin resolves to the wrong file")
    if hashlib.sha256(anchors_raw).hexdigest() != digest:
        raise GovernanceError("ledger anchors do not match document authority")


def load_ledger_anchor(
    path: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> LedgerAnchor:
    ledger_path = path.resolve()
    root = ledger_path.parent.parent
    anchors_path = ledger_path.parent / "ledger_anchors.json"
    anchors_raw = _read_governed_bytes(
        anchors_path,
        maximum=MAX_GOVERNED_JSON_BYTES,
        source_reader=source_reader,
        context="governed JSON",
    )
    _verify_anchor_pin(
        root,
        anchors_path,
        anchors_raw,
        source_reader=source_reader,
    )
    payload = _decode_governed_json(anchors_raw, path=anchors_path)
    if set(payload) != {"schema", "source_base", "ledgers"}:
        raise GovernanceError("ledger anchor document has non-exact fields")
    if payload["schema"] != ANCHOR_SCHEMA:
        raise GovernanceError("ledger anchor document has an invalid schema")
    ledgers = payload["ledgers"]
    if type(ledgers) is not dict:
        raise GovernanceError("ledger anchors must be a mapping")
    key = f"governance/{ledger_path.name}"
    entry = ledgers.get(key)
    expected = {
        "record_schema",
        "initial_count",
        "genesis_ref",
        "initial_head_ref",
        "initial_bytes_size",
        "initial_bytes_sha256",
    }
    if type(entry) is not dict or set(entry) != expected:
        raise GovernanceError(f"ledger anchor is missing or malformed: {key}")
    return LedgerAnchor(
        ledger_path=key,
        record_schema=entry["record_schema"],
        initial_count=entry["initial_count"],
        genesis_ref=entry["genesis_ref"],
        initial_head_ref=entry["initial_head_ref"],
        initial_bytes_size=entry["initial_bytes_size"],
        initial_bytes_sha256=entry["initial_bytes_sha256"],
        source_base=payload["source_base"],
    )


def _verify_anchored_bytes(
    raw: bytes, anchor: LedgerAnchor
) -> tuple[dict[str, object], ...]:
    records = parse_and_validate_records(raw)
    if len(records) < anchor.initial_count:
        raise GovernanceError("ledger truncated below governed anchor")
    if records[0]["record_ref"] != anchor.genesis_ref:
        raise GovernanceError("governance genesis mismatch")
    if records[anchor.initial_count - 1]["record_ref"] != anchor.initial_head_ref:
        raise GovernanceError("governed initial prefix changed")
    if any(record["schema"] != anchor.record_schema for record in records):
        raise GovernanceError("ledger mixes record schemas")
    if any(
        record["source_base"] != anchor.source_base
        for record in records[: anchor.initial_count]
    ):
        raise GovernanceError("initial ledger source_base differs from its anchor")
    lines = raw.splitlines(keepends=True)
    initial_size = sum(len(line) for line in lines[: anchor.initial_count])
    if initial_size != anchor.initial_bytes_size:
        raise GovernanceError("governed initial prefix byte size changed")
    digest = hashlib.sha256(raw[:initial_size]).hexdigest()
    if digest != anchor.initial_bytes_sha256:
        raise GovernanceError("governed initial prefix bytes changed")
    return records


def _find_git_root(path: Path) -> Path:
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            return parent
    raise GovernanceError("Git history is required for governed ledger verification")


def _prefix_witnesses(
    raw: bytes,
    records: Sequence[Mapping[str, object]],
    anchor: LedgerAnchor,
) -> tuple[_PrefixWitness, ...]:
    lines = raw.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    witnesses: list[_PrefixWitness] = []
    seen: set[str] = set()
    for index, record in enumerate(
        records[anchor.initial_count :], start=anchor.initial_count
    ):
        revision = str(record["source_base"])
        if revision in seen:
            raise GovernanceError("ledger suffix repeats a source_base")
        seen.add(revision)
        witnesses.append(_PrefixWitness(revision, offsets[index]))
    return tuple(witnesses)


def _sanitized_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["LANG"] = "C"
    environment["LC_ALL"] = "C"
    return environment


def _run_bounded_git_stdout(
    command: Sequence[str],
    *,
    max_bytes: int,
    input_bytes: bytes | None = None,
    timeout_seconds: int = GIT_TIMEOUT_SECONDS,
) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        raise TypeError("Git output byte bound must be positive")
    if type(timeout_seconds) is not int or timeout_seconds <= 0:
        raise TypeError("Git timeout must be positive")
    if input_bytes is not None and type(input_bytes) is not bytes:
        raise TypeError("Git input must be exact bytes")
    if input_bytes is not None and len(input_bytes) > MAX_GIT_INPUT_BYTES:
        raise GovernanceError("Git witness input exceeds its byte bound")
    try:
        result = capture_bounded_process(
            command,
            max_stdout_bytes=max_bytes,
            max_stderr_bytes=MAX_GIT_STDERR_BYTES,
            max_combined_output_bytes=max_bytes + MAX_GIT_STDERR_BYTES,
            timeout_seconds=timeout_seconds,
            input_bytes=input_bytes,
            env=_sanitized_git_environment(),
        )
    except (ProcessControlError, OSError, ValueError) as exc:
        raise GovernanceError("bounded Git witness command failed closed") from exc
    if result.returncode != 0 or result.stderr:
        raise GovernanceError("bounded Git witness command failed")
    return result.stdout

def _git_batch_check_witnesses(
    root: Path,
    path: Path,
    anchor_ref: str,
    prefixes: Sequence[_PrefixWitness],
) -> tuple[str, tuple[_CheckedBlob, ...]]:
    revisions = (anchor_ref, *(witness.revision for witness in prefixes))
    if len(set(revisions)) != len(revisions):
        raise GovernanceError("ledger source_base sequence is not strictly monotonic")
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    expressions = tuple(
        f"{witness.revision}:{relative}" for witness in prefixes
    )
    queries = ("HEAD", *revisions, *expressions)
    command = (
        "git",
        "--no-replace-objects",
        "-C",
        str(root),
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
    )
    output = _run_bounded_git_stdout(
        command,
        max_bytes=MAX_GIT_METADATA_BYTES,
        input_bytes="".join(f"{query}\n" for query in queries).encode("ascii"),
    )
    rows = output.splitlines()
    if len(rows) != len(queries):
        raise GovernanceError("Git returned incomplete witness metadata")

    parsed: list[tuple[str, str, int]] = []
    for query, row in zip(queries, rows, strict=True):
        parts = row.split()
        if len(parts) != 3:
            raise GovernanceError(f"Git witness object is missing: {query}")
        try:
            object_id = parts[0].decode("ascii")
            object_type = parts[1].decode("ascii")
            size = int(parts[2])
        except (UnicodeDecodeError, ValueError) as exc:
            raise GovernanceError("Git returned malformed witness metadata") from exc
        if _COMMIT_RE.fullmatch(object_id) is None or size < 0:
            raise GovernanceError("Git returned malformed witness object identity")
        parsed.append((object_id, object_type, size))

    head_ref, head_type, _head_size = parsed[0]
    if head_type != "commit":
        raise GovernanceError("Git HEAD is not a commit")
    for requested, (object_id, object_type, _size) in zip(
        revisions, parsed[1 : 1 + len(revisions)], strict=True
    ):
        if object_id != requested or object_type != "commit":
            raise GovernanceError(f"ledger source_base is not an exact commit: {requested}")

    checked: list[_CheckedBlob] = []
    blob_rows = parsed[1 + len(revisions) :]
    for witness, (object_id, object_type, size) in zip(
        prefixes, blob_rows, strict=True
    ):
        if object_type != "blob":
            raise GovernanceError("Git source_base path is not a blob")
        if size != witness.expected_size:
            raise GovernanceError(
                "Git blob does not have the exact committed prefix size"
            )
        checked.append(
            _CheckedBlob(witness.revision, object_id, witness.expected_size)
        )
    return head_ref, tuple(checked)


def _parse_commit_graph(
    raw: bytes,
    head_ref: str,
    boundary_ref: str | None = None,
) -> _CommitGraph:
    if len(raw) > MAX_COMMIT_GRAPH_BYTES:
        raise GovernanceError("Git commit graph exceeds its byte bound")
    if b"\r" in raw:
        raise GovernanceError("Git commit graph is not canonical LF text")
    rows = raw.splitlines()
    if len(rows) > MAX_COMMIT_GRAPH_RECORDS:
        raise GovernanceError("Git commit graph exceeds its record bound")
    parents: dict[str, tuple[str, ...]] = {}
    for row in rows:
        try:
            tokens = tuple(token.decode("ascii") for token in row.split())
        except UnicodeDecodeError as exc:
            raise GovernanceError("Git commit graph is not ASCII") from exc
        if not tokens or any(_COMMIT_RE.fullmatch(token) is None for token in tokens):
            raise GovernanceError("Git commit graph contains a malformed commit")
        node, node_parents = tokens[0], tokens[1:]
        if node in parents:
            raise GovernanceError("Git commit graph contains a duplicate commit")
        parents[node] = node_parents
    boundary = boundary_ref if boundary_ref is not None else ""
    if head_ref != boundary and head_ref not in parents:
        raise GovernanceError("Git commit graph does not contain HEAD")
    return _CommitGraph(boundary, head_ref, parents)


_MAX_COMMIT_GRAPH_CACHE_ENTRIES = 8
_COMMIT_GRAPH_CACHE: dict[tuple[str, str, str | None], _CommitGraph] = {}


def _reset_commit_graph_cache() -> None:
    _COMMIT_GRAPH_CACHE.clear()


def _git_load_commit_graph(
    root: Path,
    head_ref: str,
    boundary_ref: str | None = None,
) -> _CommitGraph:
    try:
        root_identity = str(root.resolve(strict=True))
    except OSError as exc:
        raise GovernanceError("Git root is unavailable") from exc
    cache_key = (root_identity, head_ref, boundary_ref)
    cached = _COMMIT_GRAPH_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if boundary_ref == head_ref:
        graph = _CommitGraph(str(boundary_ref), head_ref, {})
    else:
        revision = head_ref if boundary_ref is None else f"{boundary_ref}..{head_ref}"
        command = (
            "git",
            "--no-replace-objects",
            "-C",
            str(root),
            "rev-list",
            "--parents",
            "--topo-order",
            "--ancestry-path",
            f"--max-count={MAX_COMMIT_GRAPH_RECORDS + 1}",
            revision,
        )
        raw = _run_bounded_git_stdout(command, max_bytes=MAX_COMMIT_GRAPH_BYTES)
        graph = _parse_commit_graph(raw, head_ref, boundary_ref)
    if len(_COMMIT_GRAPH_CACHE) >= _MAX_COMMIT_GRAPH_CACHE_ENTRIES:
        _COMMIT_GRAPH_CACHE.pop(next(iter(_COMMIT_GRAPH_CACHE)))
    _COMMIT_GRAPH_CACHE[cache_key] = graph
    return graph


def _graph_is_ancestor(
    graph: _CommitGraph, ancestor: str, descendant: str
) -> bool:
    key = (ancestor, descendant)
    cached = graph.ancestry_cache.get(key)
    if cached is not None:
        return cached
    if ancestor == descendant:
        graph.ancestry_cache[key] = True
        return True
    if descendant != graph.boundary_ref and descendant not in graph.parents:
        graph.ancestry_cache[key] = False
        return False
    pending = [descendant]
    seen = {descendant}
    found = False
    while pending and not found:
        node = pending.pop()
        for parent in graph.parents.get(node, ()):
            if parent == ancestor:
                found = True
                break
            if parent in graph.parents and parent not in seen:
                seen.add(parent)
                pending.append(parent)
    graph.ancestry_cache[key] = found
    return found


def _verify_graph_history(
    anchor_ref: str,
    prefixes: Sequence[_PrefixWitness],
    graph: _CommitGraph,
) -> None:
    previous = anchor_ref
    for witness in prefixes:
        if witness.revision == previous or not _graph_is_ancestor(
            graph, previous, witness.revision
        ):
            raise GovernanceError("ledger source_base sequence is not strictly monotonic")
        previous = witness.revision
    if not _graph_is_ancestor(graph, previous, graph.head_ref):
        raise GovernanceError("ledger source_base is not an ancestor of HEAD")


def _git_batch_load_checked_blobs(
    root: Path,
    checked: Sequence[_CheckedBlob],
) -> dict[str, bytes]:
    if not checked:
        return {}
    aggregate = sum(item.expected_size for item in checked)
    if aggregate > MAX_LEDGER_RECORDS * MAX_LEDGER_BYTES:
        raise GovernanceError("committed prefix aggregate exceeds its byte bound")
    header_allowance = len(checked) * 160 + 1
    command = (
        "git",
        "--no-replace-objects",
        "-C",
        str(root),
        "cat-file",
        "--batch",
    )
    output = _run_bounded_git_stdout(
        command,
        max_bytes=aggregate + header_allowance,
        input_bytes="".join(
            f"{item.object_id}\n" for item in checked
        ).encode("ascii"),
    )
    cursor = 0
    result: dict[str, bytes] = {}
    for item in checked:
        newline = output.find(b"\n", cursor)
        if newline < 0:
            raise GovernanceError("Git returned a truncated blob header")
        header = output[cursor:newline].split()
        cursor = newline + 1
        expected_header = (
            item.object_id.encode("ascii"),
            b"blob",
            str(item.expected_size).encode("ascii"),
        )
        if tuple(header) != expected_header:
            raise GovernanceError("Git blob header changed after metadata check")
        end = cursor + item.expected_size
        if end >= len(output) or output[end : end + 1] != b"\n":
            raise GovernanceError("Git returned truncated committed ledger bytes")
        result[item.revision] = output[cursor:end]
        cursor = end + 1
    if cursor != len(output):
        raise GovernanceError("Git returned unexpected trailing blob data")
    return result


def _load_git_witnesses(
    root: Path,
    path: Path,
    anchor_ref: str,
    prefixes: Sequence[_PrefixWitness],
) -> tuple[str, dict[str, bytes]]:
    head_ref, checked = _git_batch_check_witnesses(
        root, path, anchor_ref, prefixes
    )
    graph = _git_load_commit_graph(root, head_ref, anchor_ref)
    _verify_graph_history(anchor_ref, prefixes, graph)
    return head_ref, _git_batch_load_checked_blobs(root, checked)










def _verify_git_witnesses(
    raw: bytes,
    records: Sequence[Mapping[str, object]],
    anchor: LedgerAnchor,
    *,
    committed_blobs: Mapping[str, bytes],
    commit_kinds: Mapping[str, str],
    head_ref: str,
    is_ancestor: Callable[[str, str], bool],
) -> None:
    suffix = records[anchor.initial_count :]
    revisions = (anchor.source_base, *(str(record["source_base"]) for record in suffix), head_ref)
    for revision in revisions:
        if commit_kinds.get(revision) != "commit":
            raise GovernanceError(f"ledger source_base is not a commit: {revision}")
    if not is_ancestor(anchor.source_base, head_ref):
        raise GovernanceError("ledger anchor source_base is not an ancestor of HEAD")

    lines = raw.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    previous = anchor.source_base
    for index, record in enumerate(suffix, start=anchor.initial_count):
        source_base = str(record["source_base"])
        if source_base == previous or not is_ancestor(previous, source_base):
            raise GovernanceError("ledger source_base sequence is not strictly monotonic")
        if not is_ancestor(source_base, head_ref):
            raise GovernanceError("ledger source_base is not an ancestor of HEAD")
        committed = committed_blobs.get(source_base)
        expected_size = offsets[index]
        if committed is None or len(committed) != expected_size or not raw.startswith(committed):
            raise GovernanceError(
                f"record {index} source_base does not bind its exact committed prefix"
            )
        previous = source_base


def _read_hash_chain_for_test(
    path: Path,
    anchor: LedgerAnchor,
    *,
    committed_blobs: Mapping[str, bytes],
    commit_kinds: Mapping[str, str],
    head_ref: str | None,
    is_ancestor: Callable[[str, str], bool] | None,
) -> tuple[dict[str, object], ...]:
    """Private pure seam for corruption and Git-witness unit tests."""

    raw = path.read_bytes()
    records = _verify_anchored_bytes(raw, anchor)
    if len(records) > anchor.initial_count:
        if head_ref is None or is_ancestor is None:
            raise GovernanceError("suffix verification requires authenticated Git witnesses")
        _verify_git_witnesses(
            raw,
            records,
            anchor,
            committed_blobs=committed_blobs,
            commit_kinds=commit_kinds,
            head_ref=head_ref,
            is_ancestor=is_ancestor,
        )
    return records


def read_hash_chain(
    path: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> tuple[dict[str, object], ...]:
    """Verify one governed ledger; suffix verification always requires Git."""

    raw = _read_governed_bytes(
        path,
        maximum=MAX_LEDGER_BYTES,
        source_reader=source_reader,
        context="ledger",
    )
    anchor = load_ledger_anchor(path, source_reader=source_reader)
    records = _verify_anchored_bytes(raw, anchor)
    root = _find_git_root(path.resolve().parent)
    prefixes = _prefix_witnesses(raw, records, anchor)
    _head_ref, blobs = _load_git_witnesses(
        root, path, anchor.source_base, prefixes
    )
    raw_view = memoryview(raw)
    for witness in prefixes:
        committed = blobs.get(witness.revision)
        if (
            committed is None
            or len(committed) != witness.expected_size
            or raw_view[: witness.expected_size] != committed
        ):
            raise GovernanceError(
                "source_base does not bind its exact committed prefix"
            )
    return records


def effective_replay_status(
    records: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    if len(records) < len(PHASES):
        raise GovernanceError("replay status lacks its governed initial phase set")
    predecessor: str | None = None
    for sequence, record in enumerate(records):
        _validate_status_record(record, sequence=sequence)
        if record["predecessor_ref"] != predecessor:
            raise GovernanceError(f"record {sequence} predecessor does not match prior head")
        if record["record_ref"] != expected_record_ref(record):
            raise GovernanceError(f"record {sequence} content ref mismatch")
        predecessor = str(record["record_ref"])
    for index, phase in enumerate(PHASES):
        record = records[index]
        if (
            record["phase"] != phase
            or record["status"] != INITIAL_STATUS[phase]
            or record["admission_gate_result_ref"] is not None
            or record["admission_run_ref"] is not None
        ):
            raise GovernanceError("replay status initial phase set is not truthful")

    status = dict(INITIAL_STATUS)
    consumed_gates: set[str] = set()
    consumed_runs: set[str] = set()
    for record in records[len(PHASES) :]:
        phase = str(record["phase"])
        next_status = str(record["status"])
        phase_index = PHASES.index(phase)
        for descendant in PHASES[phase_index + 1 :]:
            status[descendant] = "red"
        if next_status == "pending":
            raise GovernanceError("pending is reserved for the initial G0 record")
        if next_status in {"green", "externally_blocked"}:
            gate_ref = str(record["admission_gate_result_ref"])
            run_ref = str(record["admission_run_ref"])
            if gate_ref in consumed_gates:
                raise GovernanceError(f"admission gate result already consumed: {gate_ref}")
            if run_ref in consumed_runs:
                raise GovernanceError(f"admission run already consumed: {run_ref}")
            unmet = [
                dependency
                for dependency in PHASES[:phase_index]
                if status[dependency] != "green"
            ]
            if unmet:
                raise GovernanceError(
                    f"phase {phase} has a non-green dependency: {', '.join(unmet)}"
                )
            consumed_gates.add(gate_ref)
            consumed_runs.add(run_ref)
        status[phase] = next_status
    return status


def verify_file_invalidation(
    root: Path,
    record: Mapping[str, object],
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> None:
    sequence = record.get("sequence")
    if type(sequence) is not int:
        raise GovernanceError("invalidation sequence must be an integer")
    _validate_invalidation_record(record, sequence=sequence)
    if record["record_ref"] != expected_record_ref(record):
        raise GovernanceError("invalidation content ref mismatch")
    root_resolved = root.resolve()
    subject = (root_resolved / str(record["subject"])).resolve()
    try:
        subject.relative_to(root_resolved)
    except ValueError as exc:
        raise GovernanceError("invalidation subject escapes the hybrid root") from exc
    try:
        if source_reader is None:
            if not subject.is_file():
                raise GovernanceError("invalidation subject is not a file")
            raw = subject.read_bytes()
        else:
            raw = source_reader(subject)
    except GovernanceError:
        raise
    except (OSError, ValueError, KeyError) as exc:
        raise GovernanceError("cannot read invalidation subject bytes") from exc
    if type(raw) is not bytes:
        raise GovernanceError("invalidation subject reader did not return exact bytes")
    if hashlib.sha256(raw).hexdigest() != record["subject_sha256"]:
        raise GovernanceError("invalidation subject bytes changed")


def make_status_record(
    records: Sequence[Mapping[str, object]],
    *,
    source_base: str,
    phase: str,
    status: str,
    admission_gate_result_ref: str | None,
    admission_run_ref: str | None,
    rationale: str,
) -> dict[str, object]:
    if not records:
        raise GovernanceError("cannot append to an empty replay status ledger")
    record: dict[str, object] = {
        "schema": STATUS_SCHEMA,
        "sequence": len(records),
        "predecessor_ref": records[-1]["record_ref"],
        "source_base": source_base,
        "phase": phase,
        "status": status,
        "admission_gate_result_ref": admission_gate_result_ref,
        "admission_run_ref": admission_run_ref,
        "rationale": rationale,
    }
    record["record_ref"] = expected_record_ref(record)
    effective_replay_status((*records, record))
    return record
