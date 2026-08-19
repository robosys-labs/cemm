#!/usr/bin/env python3
"""Repository-owned trust resolver for future R4-authorized release training.

The parent controller is intentionally a control-plane process.  It verifies the
append-only replay ledger and the exact R4 admission receipt before making any
training evidence visible to a child process.  The child receives only one
private snapshot containing the train authorization, train capability, and
train payload plus the independently authenticated authorization ref/SHA.

The controller never imports trainer/model/torch code and cannot make R4 green.
On the current corrective replay, where effective R4 is red, it fails before
reading or staging replacement R4 training artifacts.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Callable, Mapping, NoReturn, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cemm_authoritative_hybrid.governance import (  # noqa: E402
    GovernanceError,
    effective_replay_status,
    parse_and_validate_records,
)
from cemm_authoritative_hybrid.process_control import (  # noqa: E402
    BoundedProcessResult,
    ProcessControlError,
    capture_bounded_process,
)

__all__ = [
    "ReleaseTrainingError",
    "R4TrainingTrust",
    "resolve_r4_training_trust",
    "run_release_training",
]

_RECEIPT_SCHEMA = "cemm-hybrid-validation-receipt-v1"
_INTEGRITY_SCHEMA = "cemm-r4-artifact-integrity-step-report-v1"
_OUTPUT_SCHEMA = "cemm-r4-release-training-parent-v1"
_RUN_RE = re.compile(r"run:[0-9a-f]{24}\Z")
_GATE_RE = re.compile(r"gate_result:[0-9a-f]{24}\Z")
_RECORD_RE = re.compile(r"governance_record:[0-9a-f]{24}\Z")
_AUTH_RE = re.compile(r"r4_class_authorization_v1:[0-9a-f]{24}\Z")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_MAX_RUN_RECEIPT_BYTES = 32 * 1024 * 1024
_MAX_SMALL_EVIDENCE_BYTES = 64 * 1024
_MAX_PAYLOAD_BYTES = 32 * 1024 * 1024
_MAX_CHILD_OUTPUT_BYTES = 2 * 1024 * 1024
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)

_LEDGER = Path("governance/replay_status.jsonl")
_RUNS = Path("artifacts/validation/runs")
_AUTHORIZATION = Path("artifacts/r4/authorizations/train.json")
_CAPABILITY = Path("artifacts/r4/capabilities/train.json")
_PAYLOAD = Path("artifacts/r4/splits/train.jsonl")
_PRIVATE_INVENTORY = tuple(
    sorted(
        (
            _AUTHORIZATION.as_posix(),
            _CAPABILITY.as_posix(),
            _PAYLOAD.as_posix(),
        )
    )
)

_RECEIPT_FIELDS = frozenset(
    {
        "config",
        "config_ref",
        "environment",
        "environment_ref",
        "evidence_files",
        "fresh",
        "gate_result_ref",
        "phase",
        "pre_admission_status_head_ref",
        "run_nonce",
        "run_ref",
        "schema",
        "source_ref",
        "started_at_utc",
        "step_results",
        "tier",
    }
)
_INTEGRITY_FIELDS = frozenset(
    {
        "schema",
        "artifact_count",
        "artifact_set_ref",
        "build_receipt_ref",
        "build_receipt_abi_version",
        "source_revision",
        "authority_generation",
        "integrity_ref",
        "train_authorization_ref",
        "train_authorization_sha256",
    }
)


class ReleaseTrainingError(RuntimeError):
    """Fail-closed release-training trust or execution error."""


@dataclass(frozen=True)
class R4TrainingTrust:
    admission_run_ref: str
    admission_gate_result_ref: str
    admitted_source_ref: str
    authorization_ref: str
    authorization_sha256: str


@dataclass(frozen=True)
class _ChildArtifacts:
    manifest_sha256: str
    report_sha256: str


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ReleaseTrainingError(f"non-canonical JSON value: {exc}") from exc


def _content_ref(kind: str, value: object) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(value)).hexdigest()
    return f"{kind}:{digest[:24]}"


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseTrainingError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> NoReturn:
    raise ReleaseTrainingError(f"non-finite JSON constant: {value}")


def _validate_json_bounds(value: object, *, maximum_nodes: int = 1_000_000) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > maximum_nodes or depth > 64:
            raise ReleaseTrainingError("JSON structure exceeds admitted bounds")
        if type(item) is dict:
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif item is None or type(item) in {str, int, bool}:
            continue
        elif type(item) is float and math.isfinite(item):
            continue
        else:
            raise ReleaseTrainingError("JSON contains a non-canonical scalar")


def _read_bounded(path: Path, *, maximum: int, label: str) -> bytes:
    try:
        size = path.stat(follow_symlinks=False).st_size
        if size <= 0 or size > maximum:
            raise ReleaseTrainingError(f"{label} violates byte bounds")
        with path.open("rb") as handle:
            raw = handle.read(maximum + 1)
    except ReleaseTrainingError:
        raise
    except OSError as exc:
        raise ReleaseTrainingError(f"cannot read {label}: {path}") from exc
    if len(raw) != size or len(raw) > maximum:
        raise ReleaseTrainingError(f"{label} changed while being read")
    return raw


def _strict_json(raw: bytes, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_nonfinite,
        )
    except ReleaseTrainingError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ReleaseTrainingError(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ReleaseTrainingError(f"{label} must contain one JSON object")
    _validate_json_bounds(value)
    return value


def _exact_fields(value: object, expected: frozenset[str], label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ReleaseTrainingError(f"{label} must be an exact object")
    actual = frozenset(value)
    if actual != expected:
        raise ReleaseTrainingError(
            f"{label} fields mismatch; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    return value


def _latest_effective_r4_record(root: Path) -> dict[str, object]:
    ledger_path = root / _LEDGER
    try:
        records = parse_and_validate_records(ledger_path.read_bytes())
        effective = effective_replay_status(records)
    except (OSError, GovernanceError, TypeError, ValueError) as exc:
        raise ReleaseTrainingError("cannot reconstruct replay governance") from exc
    if effective.get("R4") != "green":
        raise ReleaseTrainingError("effective R4 status is not green")
    candidates = [dict(row) for row in records if row.get("phase") == "R4"]
    if not candidates:
        raise ReleaseTrainingError("replay ledger contains no R4 record")
    record = candidates[-1]
    if record.get("status") != "green":
        raise ReleaseTrainingError("effective R4 green is not owned by the latest R4 record")
    run_ref = record.get("admission_run_ref")
    gate_ref = record.get("admission_gate_result_ref")
    predecessor_ref = record.get("predecessor_ref")
    source_ref = record.get("source_base")
    if type(run_ref) is not str or _RUN_RE.fullmatch(run_ref) is None:
        raise ReleaseTrainingError("R4 green record lacks an exact admission run ref")
    if type(gate_ref) is not str or _GATE_RE.fullmatch(gate_ref) is None:
        raise ReleaseTrainingError("R4 green record lacks an exact admission gate ref")
    if type(predecessor_ref) is not str or _RECORD_RE.fullmatch(predecessor_ref) is None:
        raise ReleaseTrainingError("R4 green record lacks an exact predecessor ref")
    if type(source_ref) is not str or _SOURCE_RE.fullmatch(source_ref) is None:
        raise ReleaseTrainingError("R4 green record lacks an exact source ref")
    return record


def _integrity_step(receipt: Mapping[str, object]) -> dict[str, object]:
    rows = receipt.get("step_results")
    if type(rows) is not list:
        raise ReleaseTrainingError("admission receipt step_results must be a list")
    matches: list[dict[str, object]] = []
    for item in rows:
        if type(item) is not dict:
            raise ReleaseTrainingError("admission receipt contains a non-object step result")
        if item.get("step_id") == "r4_artifact_integrity":
            matches.append(item)
    if len(matches) != 1:
        raise ReleaseTrainingError("R4 admission must contain exactly one artifact-integrity step")
    step = matches[0]
    if (
        step.get("kind") != "r4_artifact_integrity"
        or step.get("disposition") != "passed"
        or step.get("exit_code") != 0
        or step.get("error_code") is not None
    ):
        raise ReleaseTrainingError("R4 artifact-integrity step is not a clean pass")
    report = _exact_fields(step.get("report"), _INTEGRITY_FIELDS, "R4 integrity report")
    if report["schema"] != _INTEGRITY_SCHEMA:
        raise ReleaseTrainingError("R4 integrity report schema mismatch")
    if report["build_receipt_abi_version"] != 4:
        raise ReleaseTrainingError("release training requires admitted R4 Build Receipt ABI 4")
    return report


def _load_admission_trust(root: Path, record: Mapping[str, object]) -> R4TrainingTrust:
    run_ref = str(record["admission_run_ref"])
    run_id = run_ref.split(":", 1)[1]
    receipt_path = root / _RUNS / f"{run_id}.json"
    raw = _read_bounded(
        receipt_path,
        maximum=_MAX_RUN_RECEIPT_BYTES,
        label="R4 admission receipt",
    )
    receipt = _strict_json(raw, label="R4 admission receipt")
    _exact_fields(receipt, _RECEIPT_FIELDS, "R4 admission receipt")
    if receipt["schema"] != _RECEIPT_SCHEMA:
        raise ReleaseTrainingError("R4 admission receipt schema mismatch")
    if receipt["run_ref"] != run_ref:
        raise ReleaseTrainingError("R4 admission receipt run ref differs from ledger")
    material = dict(receipt)
    material.pop("run_ref")
    if _content_ref("run", material) != run_ref:
        raise ReleaseTrainingError("R4 admission receipt content identity is invalid")
    if receipt["tier"] != "admission" or receipt["phase"] != "R4" or receipt["fresh"] is not True:
        raise ReleaseTrainingError("R4 release trust requires one fresh admission receipt")
    if receipt["gate_result_ref"] != record["admission_gate_result_ref"]:
        raise ReleaseTrainingError("R4 admission gate binding differs from ledger")
    if receipt["pre_admission_status_head_ref"] != record["predecessor_ref"]:
        raise ReleaseTrainingError("R4 admission predecessor binding differs from ledger")
    if receipt["source_ref"] != record["source_base"]:
        raise ReleaseTrainingError("R4 admission source binding differs from ledger")

    report = _integrity_step(receipt)
    authorization_ref = report["train_authorization_ref"]
    authorization_sha = report["train_authorization_sha256"]
    if type(authorization_ref) is not str or _AUTH_RE.fullmatch(authorization_ref) is None:
        raise ReleaseTrainingError("R4 admission carries an invalid train authorization ref")
    if type(authorization_sha) is not str or _SHA_RE.fullmatch(authorization_sha) is None:
        raise ReleaseTrainingError("R4 admission carries an invalid train authorization SHA")
    return R4TrainingTrust(
        admission_run_ref=run_ref,
        admission_gate_result_ref=str(record["admission_gate_result_ref"]),
        admitted_source_ref=str(record["source_base"]),
        authorization_ref=authorization_ref,
        authorization_sha256=authorization_sha,
    )


def resolve_r4_training_trust(root: str | Path = ROOT) -> R4TrainingTrust:
    """Resolve the one admitted train authorization or fail before artifact access."""
    project = Path(root).resolve(strict=True)
    record = _latest_effective_r4_record(project)
    return _load_admission_trust(project, record)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise ReleaseTrainingError(f"cannot inspect evidence path: {path}") from exc
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _WINDOWS_REPARSE_POINT)


def _regular_evidence_path(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ReleaseTrainingError("release evidence path is not repository-relative")
    current = root
    if _is_link_or_reparse(current):
        raise ReleaseTrainingError("repository root may not be a link/reparse point")
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise ReleaseTrainingError("release evidence may not traverse a link/reparse point")
    try:
        metadata = os.stat(current, follow_symlinks=False)
    except OSError as exc:
        raise ReleaseTrainingError(f"release evidence is unavailable: {relative}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ReleaseTrainingError(f"release evidence is not a regular file: {relative}")
    return current


def _copy_train_evidence(project: Path, private_root: Path) -> tuple[str, ...]:
    sources = (
        (_AUTHORIZATION, _MAX_SMALL_EVIDENCE_BYTES),
        (_CAPABILITY, _MAX_SMALL_EVIDENCE_BYTES),
        (_PAYLOAD, _MAX_PAYLOAD_BYTES),
    )
    for relative, maximum in sources:
        source = _regular_evidence_path(project, relative)
        raw = _read_bounded(source, maximum=maximum, label=relative.as_posix())
        target = private_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise ReleaseTrainingError(f"cannot stage private train evidence: {relative}") from exc
    inventory = tuple(
        sorted(
            path.relative_to(private_root).as_posix()
            for path in private_root.rglob("*")
            if path.is_file()
        )
    )
    if inventory != _PRIVATE_INVENTORY:
        raise ReleaseTrainingError("private release snapshot inventory is not exactly train-only")
    return inventory


def _private_root(project: Path) -> Path:
    path = Path(tempfile.mkdtemp(prefix="cemm-r4-release-train-")).resolve(strict=True)
    try:
        path.relative_to(project)
    except ValueError:
        return path
    shutil.rmtree(path, ignore_errors=True)
    raise ReleaseTrainingError("private release snapshot must be outside the repository")


def _hash_output(path: Path, label: str) -> str:
    raw = _read_bounded(path, maximum=32 * 1024 * 1024, label=label)
    return hashlib.sha256(raw).hexdigest()


def _child_artifacts(output: Path) -> _ChildArtifacts:
    return _ChildArtifacts(
        manifest_sha256=_hash_output(output / "model_manifest.json", "model manifest"),
        report_sha256=_hash_output(output / "training_report.json", "training report"),
    )


def _child_command(
    *,
    project: Path,
    model_kind: str,
    private_root: Path,
    output: Path,
    trust: R4TrainingTrust,
) -> tuple[str, ...]:
    if model_kind not in {"proposal", "realizer"}:
        raise ReleaseTrainingError("model kind must be proposal or realizer")
    script = project / "scripts" / ("train_proposer.py" if model_kind == "proposal" else "train_realizer.py")
    config = project / "configs" / ("proposal_release.json" if model_kind == "proposal" else "realizer_release.json")
    return (
        sys.executable,
        str(script),
        "--config",
        str(config),
        "--output",
        str(output),
        "--release-isolated-root",
        str(private_root),
        "--expected-authorization-ref",
        trust.authorization_ref,
        "--expected-authorization-sha256",
        trust.authorization_sha256,
    )


def run_release_training(
    model_kind: str,
    *,
    root: str | Path = ROOT,
    output: str | Path | None = None,
    timeout_seconds: float = 900.0,
    process_runner: Callable[..., BoundedProcessResult] = capture_bounded_process,
) -> dict[str, object]:
    """Resolve R4 trust, stage train-only evidence, and run one bounded child."""
    project = Path(root).resolve(strict=True)
    trust = resolve_r4_training_trust(project)
    output_path = (
        project / "artifacts" / ("proposal_release" if model_kind == "proposal" else "realizer_release")
        if output is None
        else Path(output).resolve()
    )
    private = _private_root(project)
    try:
        inventory = _copy_train_evidence(project, private)
        command = _child_command(
            project=project,
            model_kind=model_kind,
            private_root=private,
            output=output_path,
            trust=trust,
        )
        try:
            result = process_runner(
                command,
                cwd=str(project),
                env=dict(os.environ),
                timeout_seconds=timeout_seconds,
                max_stdout_bytes=_MAX_CHILD_OUTPUT_BYTES,
                max_stderr_bytes=_MAX_CHILD_OUTPUT_BYTES,
                max_combined_output_bytes=_MAX_CHILD_OUTPUT_BYTES,
            )
        except (ProcessControlError, OSError, ValueError) as exc:
            raise ReleaseTrainingError("release training child failed process containment") from exc
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:4096]
            raise ReleaseTrainingError(
                f"release training child exited {result.returncode}: {stderr}"
            )
        artifacts = _child_artifacts(output_path)
        report: dict[str, object] = {
            "schema": _OUTPUT_SCHEMA,
            "model_kind": model_kind,
            "admission_run_ref": trust.admission_run_ref,
            "admission_gate_result_ref": trust.admission_gate_result_ref,
            "admitted_source_ref": trust.admitted_source_ref,
            "train_authorization_ref": trust.authorization_ref,
            "train_authorization_sha256": trust.authorization_sha256,
            "private_evidence_file_count": len(inventory),
            "child_manifest_sha256": artifacts.manifest_sha256,
            "child_training_report_sha256": artifacts.report_sha256,
        }
        report["release_training_ref"] = _content_ref("r4_release_training", report)
        return report
    finally:
        if private.exists() and private.name.startswith("cemm-r4-release-train-"):
            shutil.rmtree(private, ignore_errors=False)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_kind", choices=("proposal", "realizer"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = run_release_training(
            args.model_kind,
            output=args.output,
            timeout_seconds=args.timeout_seconds,
        )
    except ReleaseTrainingError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(_canonical_json_bytes(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
