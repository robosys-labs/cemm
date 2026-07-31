#!/usr/bin/env python
"""Verify or append corrective-replay status through reviewed admission evidence.

Task 4 owns ``AdmissionValidationError`` and this stable seam::

    load_verified_admission_receipt(
        root, *, phase, expected_status, run_ref
    ) -> tuple[GateReceipt, tuple[str, ...]]

The public seam may support ambiguity-safe discovery with ``run_ref=None``.
This CLI always supplies an exact run ref for candidate review and append.
The returned paths are the exact current run/admission/baseline/inventory files
that Task 4 validated in the current checkout.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Callable, Iterator, NoReturn

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cemm_authoritative_hybrid.governance import (  # noqa: E402
    GovernanceError,
    canonical_jsonl_row,
    effective_replay_status,
    make_status_record,
    read_hash_chain,
    verify_file_invalidation,
)


STATUS_LEDGER = ROOT / "governance" / "replay_status.jsonl"
INVALIDATION_LEDGER = ROOT / "governance" / "receipt_invalidations.jsonl"
APPEND_LOCK = ROOT / "governance" / "replay_status.lock"
_CONTENT_REF_RE = re.compile(
    r"[a-z][a-z0-9_-]*(?::[a-z0-9_-]+)*:[0-9a-f]{24}\Z"
)
_GATE_RESULT_REF_RE = re.compile(r"gate_result:[0-9a-f]{24}\Z")
_RUN_REF_RE = re.compile(r"run:[0-9a-f]{24}\Z")
_ADMISSION_PATH_RE = re.compile(
    r"artifacts/validation/(?:runs/[^/]+\.json|(?:G0|R[1-8])_ADMISSION_RECEIPT\.json)\Z"
)
_FIXED_EVIDENCE_PATHS = {
    "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
    "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
}


@dataclass(frozen=True)
class AdmissionOwner:
    validation_error_type: type[Exception]
    loader: Callable[..., tuple[object, tuple[str, ...]]]

    def __post_init__(self) -> None:
        if (
            type(self.validation_error_type) is not type
            or not issubclass(self.validation_error_type, Exception)
            or not callable(self.loader)
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
    if run_ref is None:
        return frozenset(_FIXED_EVIDENCE_PATHS)
    if _RUN_REF_RE.fullmatch(run_ref) is None:
        raise GovernanceError("admission run_ref must be an exact run: content ref")
    if phase not in {"G0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"}:
        raise GovernanceError("admission phase is invalid")
    digest = run_ref.removeprefix("run:")
    return frozenset(
        {
            *_FIXED_EVIDENCE_PATHS,
            f"artifacts/validation/runs/{digest}.json",
            f"artifacts/validation/{phase}_ADMISSION_RECEIPT.json",
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
    spec = importlib.util.spec_from_file_location(module_name, gate_path)
    if spec is None or spec.loader is None:
        raise TypeError("cannot create the reviewed Task 4 module identity")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    prior_bytecode_setting = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(module_name) is module:
            del sys.modules[module_name]
        raise
    finally:
        sys.dont_write_bytecode = prior_bytecode_setting

    error_type = vars(module).get("AdmissionValidationError")
    loader = vars(module).get("load_verified_admission_receipt")
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
    return AdmissionOwner(error_type, loader)


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
    for record in admitted:
        receipt, paths = _validated_admission(
            str(record["phase"]),
            str(record["status"]),
            run_ref=str(record["admission_run_ref"]),
            owner=selected,
        )
        if getattr(receipt, "gate_result_ref", None) != record["admission_gate_result_ref"]:
            raise GovernanceError("admitted gate_result_ref reconstruction mismatch")
        if getattr(receipt, "run_ref", None) != record["admission_run_ref"]:
            raise GovernanceError("admitted run_ref reconstruction mismatch")
        normalized = _normalize_allowed_evidence_paths(
            paths, require_files=require_evidence_files
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


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or len(value) not in {40, 64}:
        _fail("cannot resolve the full source_base commit")
    return value


def _committed_status_bytes(source_base: str) -> bytes:
    relative = STATUS_LEDGER.relative_to(REPOSITORY_ROOT).as_posix()
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "show", f"{source_base}:{relative}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        _fail("the replay status ledger has no committed prior-head bytes")
    return completed.stdout


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
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            "hybrid_mvp/",
        ],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        _fail("cannot inspect governed checkout cleanliness")
    entries = completed.stdout.split(b"\0")
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
            if hybrid_relative != "governance/replay_status.lock":
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
    captured_allowed = _normalize_allowed_evidence_paths(
        captured_paths, require_files=require_evidence_files
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
        _reject_dirty_governed_inputs(_dirty_hybrid_paths(), allowed)
    source_base, prior_bytes = _require_committed_current_prefix()
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
