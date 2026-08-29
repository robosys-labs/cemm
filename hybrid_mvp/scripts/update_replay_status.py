#!/usr/bin/env python
"""Verify or append corrective-replay status through reviewed admission evidence.

Task 4 owns ``AdmissionValidationError`` and this stable seam::

    load_verified_admission_receipt(
        root, *, phase, expected_status, run_ref
    ) -> tuple[GateReceipt, tuple[str, ...]]

    verify_current_source_config(root, receipt) -> None

The public seam may support ambiguity-safe discovery with ``run_ref=None``.
This CLI always supplies an exact run ref for candidate review and append.
The returned paths are the exact current run/admission/baseline/inventory files
that Task 4 validated in the current checkout.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from types import ModuleType
from typing import Callable, Iterator, NoReturn

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
SRC = ROOT / "src"
_MAX_BOOTSTRAP_SOURCE_BYTES = 4 * 1024 * 1024


def _is_link_or_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        junction = getattr(path, "is_junction", None)
        if callable(junction) and junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError as exc:
        raise RuntimeError(f"cannot inspect reviewed source: {path.name}") from exc
    return bool(attributes & 0x400)


def _resolve_reviewed_source_path(path: Path) -> Path:
    root = ROOT.resolve(strict=True)
    candidate = path if path.is_absolute() else ROOT / path
    try:
        relative = candidate.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError("reviewed source escapes the Hybrid MVP root") from exc
    current = root
    if _is_link_or_reparse(ROOT):
        raise RuntimeError("Hybrid MVP root is a redirected path")
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise RuntimeError(f"reviewed source path is redirected: {path.name}")
        resolved = current.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("reviewed source escapes the Hybrid MVP root") from exc
        if resolved != current:
            raise RuntimeError(f"reviewed source path is redirected: {path.name}")
    return current

def _load_reviewed_source(
    path: Path,
    name: str,
    *,
    package: str = "",
) -> ModuleType:
    resolved = _resolve_reviewed_source_path(path)
    if not resolved.is_file():
        raise RuntimeError(f"reviewed source is unavailable: {path.name}")
    with resolved.open("rb") as stream:
        raw = stream.read(_MAX_BOOTSTRAP_SOURCE_BYTES + 1)
    if not raw or len(raw) > _MAX_BOOTSTRAP_SOURCE_BYTES:
        raise RuntimeError(f"reviewed source is invalid: {path.name}")
    code = compile(raw, str(resolved), "exec", dont_inherit=True, optimize=0)
    module = ModuleType(name)
    module.__file__ = str(resolved)
    module.__package__ = package
    module.__cached__ = None
    module.__loader__ = None
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except BaseException:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    return module


_process_control_source = (
    SRC / "cemm_authoritative_hybrid" / "process_control.py"
)
_process_control = _load_reviewed_source(
    _process_control_source, "process_control"
)
ProcessControlError = _process_control.ProcessControlError
capture_bounded_process = _process_control.capture_bounded_process

_governance_package_name = "_cemm_reviewed_governance_owner"
_governance_package = ModuleType(_governance_package_name)
_governance_package.__package__ = _governance_package_name
_governance_package.__path__ = ()
_governance_package.__loader__ = None
sys.modules[_governance_package_name] = _governance_package
_load_reviewed_source(
    _process_control_source,
    f"{_governance_package_name}.process_control",
    package=_governance_package_name,
)
_load_reviewed_source(
    SRC / "cemm_authoritative_hybrid" / "canonical.py",
    f"{_governance_package_name}.canonical",
    package=_governance_package_name,
)
_governance_source = SRC / "cemm_authoritative_hybrid" / "governance.py"
_existing_governance = sys.modules.get("cemm_authoritative_hybrid.governance")
_existing_governance_error = getattr(
    _existing_governance, "GovernanceError", None
)
_governance = _load_reviewed_source(
    _governance_source,
    f"{_governance_package_name}.governance",
    package=_governance_package_name,
)
if (
    isinstance(_existing_governance, ModuleType)
    and Path(getattr(_existing_governance, "__file__", "")).resolve()
    == _governance_source.resolve()
    and type(_existing_governance_error) is type
    and _existing_governance_error.__name__ == "GovernanceError"
    and _existing_governance_error.__module__
    == "cemm_authoritative_hybrid.governance"
    and issubclass(_existing_governance_error, ValueError)
):
    # Preserve exception identity for an already authenticated in-process owner;
    # all behavior still comes from the source-executed module above.
    _governance.GovernanceError = _existing_governance_error
GovernanceError = _governance.GovernanceError
canonical_jsonl_row = _governance.canonical_jsonl_row
effective_replay_status = _governance.effective_replay_status
make_status_record = _governance.make_status_record
read_hash_chain = _governance.read_hash_chain
verify_file_invalidation = _governance.verify_file_invalidation

STATUS_LEDGER = ROOT / "governance" / "replay_status.jsonl"
INVALIDATION_LEDGER = ROOT / "governance" / "receipt_invalidations.jsonl"
APPEND_LOCK = ROOT.parent / ".cemm-hybrid-replay-status.lock"
_CONTENT_REF_RE = re.compile(
    r"[a-z][a-z0-9_-]*(?::[a-z0-9_-]+)*:[0-9a-f]{24}\Z"
)
_GATE_RESULT_REF_RE = re.compile(r"gate_result:[0-9a-f]{24}\Z")
_RUN_REF_RE = re.compile(r"run:[0-9a-f]{24}\Z")
_ADMISSION_PATH_RE = re.compile(
    r"artifacts/validation/runs/[0-9a-f]{24}\.json\Z"
)
_R4_HISTORICAL_ABI3_EVIDENCE_PATHS = frozenset(
    {
        "artifacts/r4/BUILD_RECEIPT.json",
        "artifacts/r4/episodes.jsonl",
        "artifacts/r4/expanded_cases.jsonl",
        "artifacts/r4/expected_contracts.jsonl",
        "artifacts/r4/expected_derivations.jsonl",
        "artifacts/r4/mutation_observations.jsonl",
        "artifacts/r4/mutations.jsonl",
        "artifacts/r4/partitions/dialogue.json",
        "artifacts/r4/partitions/general.json",
        "artifacts/r4/partitions/lexical.json",
        "artifacts/r4/partitions/mutation.json",
        "artifacts/r4/partitions/realization.json",
        "artifacts/r4/partitions/semantic_target.json",
        "artifacts/r4/partitions/topology.json",
        "artifacts/r4/structural_sufficiency.json",
        "artifacts/r4/training_allowlist.json",
    }
)
_R4_CURRENT_ABI4_EVIDENCE_PATHS = frozenset(
    {
        "artifacts/r4/BUILD_RECEIPT.json",
        "artifacts/r4/authorizations/train.json",
        "artifacts/r4/capabilities/train.json",
        "artifacts/r4/episodes.jsonl",
        "artifacts/r4/expanded_cases.jsonl",
        "artifacts/r4/expected_contracts.jsonl",
        "artifacts/r4/expected_derivations.jsonl",
        "artifacts/r4/mutation_observations.jsonl",
        "artifacts/r4/mutations.jsonl",
        "artifacts/r4/partition_evidence.json",
        "artifacts/r4/partition_sufficiency.json",
        "artifacts/r4/split_manifest.json",
        "artifacts/r4/splits/calibration.jsonl",
        "artifacts/r4/splits/frozen_test.jsonl",
        "artifacts/r4/splits/selection.jsonl",
        "artifacts/r4/splits/train.jsonl",
        "artifacts/r4/structural_sufficiency.json",
    }
)
_PHASE_ADMISSION_EVIDENCE_PATHS = {
    "G0": frozenset(
        {
            "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
            "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
        }
    ),
    "R1": frozenset(),
    "R2": frozenset(),
    "R3": frozenset(
        {"artifacts/validation/R3_ACTIVATION_CANARIES.json"}
    ),
    "R4": _R4_HISTORICAL_ABI3_EVIDENCE_PATHS
    | _R4_CURRENT_ABI4_EVIDENCE_PATHS,
    "R5": frozenset(),
    "R6": frozenset(),
    "R7": frozenset(),
    "R8": frozenset(),
}

_FIXED_EVIDENCE_PATHS = frozenset().union(
    *_PHASE_ADMISSION_EVIDENCE_PATHS.values()
)
_GIT_PROBE_TIMEOUT_SECONDS = 60
_MAX_GIT_PROBE_OUTPUT_BYTES = 4 * 1024 * 1024


def _noop_cache_reset() -> None:
    return None


@dataclass(frozen=True)
class AdmissionOwner:
    validation_error_type: type[Exception]
    loader: Callable[..., tuple[object, tuple[str, ...]]]
    current_source_config_verifier: Callable[[Path, object], None]
    cache_reset: Callable[[], None] = _noop_cache_reset

    def __post_init__(self) -> None:
        if (
            type(self.validation_error_type) is not type
            or not issubclass(self.validation_error_type, Exception)
            or not callable(self.loader)
            or not callable(self.current_source_config_verifier)
            or not callable(self.cache_reset)
        ):
            raise TypeError("Task 4 exported an invalid admission owner")


def _fail(message: str) -> NoReturn:
    raise GovernanceError(message)


def _is_syntactically_safe_evidence_path(value: object) -> bool:
    if type(value) is not str:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in value
        and (
            value in _FIXED_EVIDENCE_PATHS
            or _ADMISSION_PATH_RE.fullmatch(value) is not None
        )
    )


def _static_evidence_candidates(
    phase: str, run_ref: str | None
) -> frozenset[str]:
    if phase not in _PHASE_ADMISSION_EVIDENCE_PATHS:
        raise GovernanceError("admission phase is invalid")
    phase_evidence = _PHASE_ADMISSION_EVIDENCE_PATHS[phase]
    if run_ref is None:
        return phase_evidence
    if _RUN_REF_RE.fullmatch(run_ref) is None:
        raise GovernanceError("admission run_ref must be an exact run: content ref")
    digest = run_ref.removeprefix("run:")
    return frozenset(
        {
            *phase_evidence,
            f"artifacts/validation/runs/{digest}.json",
        }
    )

def _preflight_owner_import(
    phase: str,
    run_ref: str | None,
    *,
    authenticated_ledger: bool = False,
) -> None:
    dirty = _dirty_hybrid_paths()
    if authenticated_ledger:
        allowed = {
            value
            for value in dirty
            if _is_syntactically_safe_evidence_path(value)
        }
        allowed.add("governance/replay_status.jsonl")
    else:
        allowed = set(_static_evidence_candidates(phase, run_ref))
    _reject_dirty_governed_inputs(dirty, allowed)


def _load_admission_owner(
    *,
    phase: str,
    run_ref: str | None,
    authenticated_ledger: bool = False,
    preflight_dirty_paths: frozenset[str] | None = None,
    preflight_allowed_paths: frozenset[str] | None = None,
) -> AdmissionOwner:
    if preflight_dirty_paths is None:
        if preflight_allowed_paths is not None:
            raise TypeError("preflight allowed paths require captured dirty paths")
        _preflight_owner_import(
            phase, run_ref, authenticated_ledger=authenticated_ledger
        )
    else:
        if authenticated_ledger or preflight_allowed_paths is None:
            raise TypeError("captured preflight requires exact allowed paths")
        _reject_dirty_governed_inputs(
            preflight_dirty_paths, preflight_allowed_paths
        )
    gate_path = (ROOT / "scripts" / "validation_gate.py").resolve()
    if not gate_path.is_file() or gate_path.is_symlink():
        raise GovernanceError("validated admission receipt owner is unavailable")
    module_name = "_cemm_reviewed_validation_gate"
    module = _load_reviewed_source(gate_path, module_name)

    error_type = vars(module).get("AdmissionValidationError")
    loader = vars(module).get("load_verified_admission_receipt")
    current_source_config_verifier = vars(module).get(
        "verify_current_source_config"
    )
    cache_reset = vars(module).get("reset_admission_verification_cache")
    if (
        type(error_type) is not type
        or error_type.__name__ != "AdmissionValidationError"
        or error_type.__module__ != module_name
        or not issubclass(error_type, Exception)
    ):
        raise TypeError("Task 4 must define its exact AdmissionValidationError class")
    if (
        not callable(loader)
        or getattr(loader, "__name__", None) != "load_verified_admission_receipt"
        or getattr(loader, "__module__", None) != module_name
    ):
        raise TypeError("Task 4 must define its exact admission receipt loader")
    if (
        not callable(current_source_config_verifier)
        or getattr(current_source_config_verifier, "__name__", None)
        != "verify_current_source_config"
        or getattr(current_source_config_verifier, "__module__", None)
        != module_name
    ):
        raise TypeError("Task 4 must define its exact current source config verifier")
    if (
        not callable(cache_reset)
        or getattr(cache_reset, "__name__", None)
        != "reset_admission_verification_cache"
        or getattr(cache_reset, "__module__", None) != module_name
    ):
        raise TypeError("Task 4 must define its exact verification-cache reset")
    return AdmissionOwner(
        error_type, loader, current_source_config_verifier, cache_reset
    )


def _validated_admission(
    phase: str,
    ledger_status: str,
    *,
    run_ref: str | None,
    owner: AdmissionOwner | None = None,
    authenticated_ledger: bool = False,
) -> tuple[object, tuple[str, ...]]:
    if ledger_status not in {"green", "externally_blocked"}:
        raise TypeError("validated admission requires an admission ledger status")
    selected = (
        owner
        if owner is not None
        else _load_admission_owner(
            phase=phase,
            run_ref=run_ref,
            authenticated_ledger=authenticated_ledger,
        )
    )
    try:
        result = selected.loader(
            root=ROOT,
            phase=phase,
            expected_status="passed",
            run_ref=run_ref,
        )
    except selected.validation_error_type as exc:
        raise GovernanceError("validated admission receipt was rejected") from exc
    if type(result) is not tuple or len(result) != 2:
        raise TypeError("Task 4 admission seam did not return (GateReceipt, paths)")
    receipt, evidence_paths = result
    if type(evidence_paths) is not tuple or any(
        type(path) is not str for path in evidence_paths
    ):
        raise TypeError("Task 4 admission seam returned malformed evidence paths")

    gate_ref = getattr(receipt, "gate_result_ref", None)
    exact_run_ref = getattr(receipt, "run_ref", None)
    if type(gate_ref) is not str or _GATE_RESULT_REF_RE.fullmatch(gate_ref) is None:
        raise TypeError("reconstructed GateReceipt has invalid gate_result_ref")
    if type(exact_run_ref) is not str or _RUN_REF_RE.fullmatch(exact_run_ref) is None:
        raise TypeError("reconstructed GateReceipt has invalid run_ref")
    if getattr(receipt, "phase", None) != phase:
        raise GovernanceError("reconstructed admission receipt phase mismatch")
    if getattr(receipt, "tier", None) != "admission":
        raise GovernanceError("reconstructed receipt is not admission tier")
    if getattr(receipt, "fresh", None) is not True:
        raise GovernanceError("reconstructed admission receipt is not fresh")
    step_results = getattr(receipt, "step_results", None)
    if type(step_results) is not tuple or not step_results:
        raise TypeError("reconstructed GateReceipt lacks immutable step results")
    if any(getattr(step, "disposition", None) != "passed" for step in step_results):
        raise GovernanceError("reconstructed admission contains a non-passed step")
    if run_ref is not None and exact_run_ref != run_ref:
        raise GovernanceError("reconstructed admission run_ref mismatch")
    return receipt, evidence_paths


def _verify_receipt_ledger_binding(
    receipt: object,
    *,
    predecessor_ref: object,
    source_base: object,
) -> None:
    if (
        getattr(receipt, "pre_admission_status_head_ref", None)
        != predecessor_ref
    ):
        raise GovernanceError("admission receipt predecessor binding mismatch")
    if getattr(receipt, "source_ref", None) != source_base:
        raise GovernanceError("admission receipt source binding mismatch")


def _verify_new_admission_current_source_config(
    owner: AdmissionOwner,
    receipt: object,
) -> None:
    try:
        result = owner.current_source_config_verifier(ROOT, receipt)
    except owner.validation_error_type as exc:
        raise GovernanceError(
            "admission receipt current source config was rejected"
        ) from exc
    if result is not None:
        raise TypeError("Task 4 current source config verifier must return None")


def _verify_admitted_runs(
    records: tuple[dict[str, object], ...] | list[dict[str, object]],
    *,
    owner: AdmissionOwner | None = None,
    dirty_paths: frozenset[str] | None = None,
    require_evidence_files: bool = True,
) -> frozenset[str]:
    admitted = tuple(
        record
        for record in records[9:]
        if record["status"] in {"green", "externally_blocked"}
    )
    selected = owner
    if admitted and selected is None:
        first = admitted[0]
        selected = _load_admission_owner(
            phase=str(first["phase"]),
            run_ref=str(first["admission_run_ref"]),
            authenticated_ledger=True,
        )

    exact_paths: set[str] = set()
    if selected is not None:
        selected.cache_reset()
    for record in admitted:
        phase = str(record["phase"])
        receipt, paths = _validated_admission(
            phase,
            str(record["status"]),
            run_ref=str(record["admission_run_ref"]),
            owner=selected,
        )
        if getattr(receipt, "gate_result_ref", None) != record["admission_gate_result_ref"]:
            raise GovernanceError("admitted gate_result_ref reconstruction mismatch")
        if getattr(receipt, "run_ref", None) != record["admission_run_ref"]:
            raise GovernanceError("admitted run_ref reconstruction mismatch")
        _verify_receipt_ledger_binding(
            receipt,
            predecessor_ref=record["predecessor_ref"],
            source_base=record["source_base"],
        )
        historical_r4 = phase == "R4" and any(
            path
            in (
                _R4_HISTORICAL_ABI3_EVIDENCE_PATHS
                - _R4_CURRENT_ABI4_EVIDENCE_PATHS
            )
            for path in paths
        )
        normalized = _normalize_allowed_evidence_paths(
            paths,
            require_files=require_evidence_files and not historical_r4,
        )
        if len(normalized) != len(paths):
            raise GovernanceError("validated evidence paths must be unique")
        exact_paths.update(normalized)

    allowed = frozenset(exact_paths)
    if dirty_paths is not None:
        _reject_dirty_governed_inputs(
            dirty_paths,
            {*allowed, "governance/replay_status.jsonl"},
        )
    return allowed


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


def _run_git_probe(
    command: list[str],
    *,
    label: str,
    failure_message: str,
) -> bytes:
    if command[:2] != ["git", "--no-replace-objects"]:
        _fail(f"Git {label} probe lacks replacement-ref isolation")
    try:
        completed = capture_bounded_process(
            command,
            max_stdout_bytes=_MAX_GIT_PROBE_OUTPUT_BYTES,
            max_stderr_bytes=_MAX_GIT_PROBE_OUTPUT_BYTES,
            timeout_seconds=_GIT_PROBE_TIMEOUT_SECONDS,
            env=_sanitized_git_environment(),
        )
    except ProcessControlError as exc:
        raise GovernanceError(f"Git {label} probe failed closed") from exc
    if completed.stderr:
        _fail(f"Git {label} probe emitted stderr")
    if completed.returncode != 0:
        _fail(failure_message)
    return completed.stdout

def _git_head() -> str:
    output = _run_git_probe(
        ["git", "--no-replace-objects", "-C", str(REPOSITORY_ROOT), "rev-parse", "--verify", "HEAD^{commit}"],
        label="source_base",
        failure_message="cannot resolve the full source_base commit",
    )
    try:
        value = output.decode("ascii").strip()
    except UnicodeDecodeError:
        _fail("cannot resolve the full source_base commit")
    if len(value) not in {40, 64}:
        _fail("cannot resolve the full source_base commit")
    return value


def _committed_status_bytes(source_base: str) -> bytes:
    relative = STATUS_LEDGER.relative_to(REPOSITORY_ROOT).as_posix()
    return _run_git_probe(
        ["git", "--no-replace-objects", "-C", str(REPOSITORY_ROOT), "show", f"{source_base}:{relative}"],
        label="committed prior-head",
        failure_message="the replay status ledger has no committed prior-head bytes",
    )


def _require_committed_current_prefix() -> tuple[str, bytes]:
    source_base = _git_head()
    committed = _committed_status_bytes(source_base)
    current = STATUS_LEDGER.read_bytes()
    if current != committed:
        _fail(
            "replay status differs from source_base; commit the prior append before another"
        )
    return source_base, committed


def _normalize_allowed_evidence_paths(
    paths: tuple[str, ...],
    *,
    root: Path = ROOT,
    require_files: bool = True,
) -> frozenset[str]:
    normalized: set[str] = set()
    for value in paths:
        path = PurePosixPath(value)
        if (
            type(value) is not str
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in value
            or not (
                value in _FIXED_EVIDENCE_PATHS
                or _ADMISSION_PATH_RE.fullmatch(value) is not None
            )
        ):
            raise GovernanceError(f"unsafe validated evidence path: {value!r}")
        resolved = (root / value).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError as exc:
            raise GovernanceError("validated evidence path escapes hybrid root") from exc
        if require_files and not resolved.is_file():
            raise GovernanceError(f"validated evidence path is not a file: {value}")
        normalized.add(value)
    return frozenset(normalized)


def _dirty_hybrid_paths() -> frozenset[str]:
    output = _run_git_probe(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(REPOSITORY_ROOT),
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            "hybrid_mvp/",
        ],
        label="cleanliness",
        failure_message="cannot inspect governed checkout cleanliness",
    )
    entries = output.split(b"\0")
    dirty: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2:3] != b" ":
            _fail("Git returned malformed porcelain status")
        status = entry[:2]
        paths = [entry[3:]]
        if b"R" in status or b"C" in status:
            if index >= len(entries) or not entries[index]:
                _fail("Git returned a truncated rename status")
            paths.append(entries[index])
            index += 1
        for raw_path in paths:
            try:
                repository_relative = raw_path.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise GovernanceError("Git returned a non-UTF-8 governed path") from exc
            prefix = "hybrid_mvp/"
            if not repository_relative.startswith(prefix):
                _fail("Git returned a path outside hybrid_mvp")
            hybrid_relative = repository_relative[len(prefix) :]
            dirty.add(hybrid_relative)
    return frozenset(dirty)


def _reject_dirty_governed_inputs(
    dirty_paths: set[str] | frozenset[str],
    allowed_paths: set[str] | frozenset[str],
) -> None:
    unexpected = sorted(set(dirty_paths) - set(allowed_paths))
    if unexpected:
        raise GovernanceError(
            "dirty governed input is not validated admission evidence: "
            + ", ".join(unexpected)
        )


@contextmanager
def _exclusive_append_lock(path: Path = APPEND_LOCK) -> Iterator[None]:
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise GovernanceError("another status update holds the append lock") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _validate_transition_args(args: argparse.Namespace) -> None:
    if args.phase is None or args.status is None:
        _fail("--phase and --status are required for a transition")
    is_admission = args.status in {"green", "externally_blocked"}
    if is_admission and args.run_ref is None:
        _fail("green/externally_blocked status requires an exact --run-ref")
    if not is_admission and args.run_ref is not None:
        _fail("--run-ref is only valid for admission statuses")


def _make_post_write_validator(
    *,
    records: tuple[dict[str, object], ...] | list[dict[str, object]],
    evidence_paths: tuple[str, ...],
    source_base: str,
    prior_bytes: bytes,
    owner: AdmissionOwner | None,
    dirty_loader: Callable[[], frozenset[str]] = _dirty_hybrid_paths,
    head_loader: Callable[[], str] = _git_head,
    committed_loader: Callable[[str], bytes] = _committed_status_bytes,
    require_evidence_files: bool = True,
) -> Callable[[], None]:
    captured_records = tuple(dict(record) for record in records)
    captured_paths = tuple(evidence_paths)
    # These paths were already authenticated by _verify_admitted_runs and,
    # for a new transition, _validated_admission. Historical R4 ABI-3
    # evidence may be intentionally absent after the hard cut; the
    # revalidation closure below still enforces current evidence files.
    captured_allowed = _normalize_allowed_evidence_paths(
        captured_paths, require_files=False
    )
    if len(captured_allowed) != len(captured_paths):
        raise GovernanceError("validated evidence paths must be unique")
    has_admitted = any(
        record["status"] in {"green", "externally_blocked"}
        for record in captured_records[9:]
    )
    if has_admitted and owner is None:
        raise TypeError("admission post-write validation lacks its exact owner")
    if not has_admitted and owner is not None:
        raise TypeError("transition without admitted rows cannot carry an owner")

    def validate() -> None:
        current_allowed = _verify_admitted_runs(
            captured_records,
            owner=owner,
            require_evidence_files=require_evidence_files,
        )
        if current_allowed != captured_allowed:
            raise GovernanceError("post-write evidence path identity changed")

        allowed_dirty = set(current_allowed)
        allowed_dirty.add("governance/replay_status.jsonl")
        _reject_dirty_governed_inputs(dirty_loader(), allowed_dirty)
        if head_loader() != source_base:
            raise GovernanceError("source HEAD changed during status append")
        if committed_loader(source_base) != prior_bytes:
            raise GovernanceError("committed status prefix changed during status append")

    return validate


def _candidate(
    args: argparse.Namespace,
) -> tuple[dict[str, object], bytes, Callable[[], None]]:
    _validate_transition_args(args)
    is_admission = args.status in {"green", "externally_blocked"}
    records = read_hash_chain(STATUS_LEDGER)
    admitted = tuple(
        record
        for record in records[9:]
        if record["status"] in {"green", "externally_blocked"}
    )
    needs_owner = bool(admitted) or is_admission

    static_allowed: set[str] = set()
    for record in admitted:
        static_allowed.update(
            _static_evidence_candidates(
                str(record["phase"]), str(record["admission_run_ref"])
            )
        )
    if is_admission:
        static_allowed.update(_static_evidence_candidates(args.phase, args.run_ref))

    initial_dirty = _dirty_hybrid_paths()
    owner: AdmissionOwner | None = None
    if needs_owner:
        owner_phase = args.phase if is_admission else str(admitted[0]["phase"])
        owner_run_ref = (
            args.run_ref
            if is_admission
            else str(admitted[0]["admission_run_ref"])
        )
        owner = _load_admission_owner(
            phase=owner_phase,
            run_ref=owner_run_ref,
            preflight_dirty_paths=initial_dirty,
            preflight_allowed_paths=frozenset(static_allowed),
        )
    else:
        _reject_dirty_governed_inputs(initial_dirty, frozenset())

    allowed = set(_verify_admitted_runs(records, owner=owner))
    receipt = None
    if is_admission:
        receipt, evidence_paths = _validated_admission(
            args.phase,
            args.status,
            run_ref=args.run_ref,
            owner=owner,
        )
        new_allowed = _normalize_allowed_evidence_paths(evidence_paths)
        if len(new_allowed) != len(evidence_paths):
            raise GovernanceError("validated evidence paths must be unique")
        allowed.update(new_allowed)

    if needs_owner:
        _reject_dirty_governed_inputs(initial_dirty, allowed)
    source_base, prior_bytes = _require_committed_current_prefix()
    if receipt is not None:
        _verify_receipt_ledger_binding(
            receipt,
            predecessor_ref=records[-1]["record_ref"],
            source_base=source_base,
        )
        if owner is None:
            raise TypeError("new admission lacks its exact Task 4 owner")
        _verify_new_admission_current_source_config(owner, receipt)
    gate_ref = getattr(receipt, "gate_result_ref", None)
    run_ref = getattr(receipt, "run_ref", None)
    rationale = (
        f"Consumed fresh {args.phase} admission run {run_ref}."
        if receipt is not None
        else f"Invalidated {args.phase} pending a fresh admission receipt."
    )
    record = make_status_record(
        records,
        source_base=source_base,
        phase=args.phase,
        status=args.status,
        admission_gate_result_ref=gate_ref,
        admission_run_ref=run_ref,
        rationale=rationale,
    )
    post_write_validate = _make_post_write_validator(
        records=(*records, record),
        evidence_paths=tuple(sorted(allowed)),
        source_base=source_base,
        prior_bytes=prior_bytes,
        owner=owner,
    )
    return record, prior_bytes, post_write_validate


def _require_expected_record_ref(
    record: dict[str, object], expected: str | None
) -> None:
    if expected is None:
        _fail("--expect-record-ref is required for append")
    if expected != record["record_ref"]:
        _fail("reviewed candidate changed; run --dry-run again")


def _restore_prior_bytes(path: Path, prior_bytes: bytes) -> None:
    with path.open("r+b") as handle:
        handle.seek(0)
        handle.write(prior_bytes)
        handle.truncate(len(prior_bytes))
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != prior_bytes:
        raise GovernanceError("failed to restore exact prior ledger bytes")


def _append_exact(
    record: dict[str, object],
    prior_bytes: bytes,
    *,
    ledger_path: Path = STATUS_LEDGER,
    verifier: Callable[[Path], object] = read_hash_chain,
    post_write_validate: Callable[[], None],
) -> None:
    row = canonical_jsonl_row(record)
    expected_bytes = prior_bytes + row
    if ledger_path.read_bytes() != prior_bytes:
        _fail("replay status changed while the transition was being validated")
    try:
        with ledger_path.open("ab") as handle:
            handle.write(row)
            handle.flush()
            os.fsync(handle.fileno())
        post_write_validate()
        if ledger_path.read_bytes() != expected_bytes:
            raise GovernanceError("ledger changed from the exact candidate bytes")
        verifier(ledger_path)
        if ledger_path.read_bytes() != expected_bytes:
            raise GovernanceError(
                "structural verifier changed the exact candidate bytes"
            )
    except BaseException:
        _restore_prior_bytes(ledger_path, prior_bytes)
        raise


def verify_chains(*, owner: AdmissionOwner | None = None) -> tuple[dict[str, str], int]:
    status_records = read_hash_chain(STATUS_LEDGER)
    invalidations = read_hash_chain(INVALIDATION_LEDGER)
    for record in invalidations:
        verify_file_invalidation(ROOT, record)
    allowed_paths = _verify_admitted_runs(status_records, owner=owner)
    if any(
        record["status"] in {"green", "externally_blocked"}
        for record in status_records[9:]
    ):
        _reject_dirty_governed_inputs(
            _dirty_hybrid_paths(),
            {*allowed_paths, "governance/replay_status.jsonl"},
        )
    return effective_replay_status(status_records), len(invalidations)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-chain", action="store_true")
    parser.add_argument("--phase", choices=("G0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"))
    parser.add_argument("--status", choices=("red", "green", "externally_blocked"))
    parser.add_argument("--run-ref")
    parser.add_argument("--expect-record-ref")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.verify_chain:
            if any(
                (
                    args.phase,
                    args.status,
                    args.run_ref,
                    args.expect_record_ref,
                    args.dry_run,
                    args.append,
                )
            ):
                _fail("--verify-chain cannot be combined with transition arguments")
            status, invalidation_count = verify_chains()
            rendered = " ".join(f"{phase}={value}" for phase, value in status.items())
            print(f"{rendered} invalidations={invalidation_count}")
            return 0
        if args.dry_run == args.append:
            _fail("choose exactly one of --dry-run or --append")
        if args.dry_run and args.expect_record_ref is not None:
            _fail("--expect-record-ref is valid only with --append")
        if args.append:
            with _exclusive_append_lock():
                record, prior_bytes, post_write_validate = _candidate(args)
                _require_expected_record_ref(record, args.expect_record_ref)
                _append_exact(
                    record,
                    prior_bytes,
                    post_write_validate=post_write_validate,
                )
        else:
            record, _prior_bytes, _post_write_validate = _candidate(args)
        print(
            json.dumps(
                record,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except GovernanceError as exc:
        print(f"governance error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
