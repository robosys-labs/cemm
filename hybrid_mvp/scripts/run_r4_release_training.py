#!/usr/bin/env python3
"""Resolve admitted R4 train trust and launch one isolated release-training child.

This is a governance/data-isolation controller, not a neural activation owner.
It fails closed unless R4 is effectively green and the exact consumed admission
receipt reconstructs.  The child receives only a private train authorization,
train capability and train payload snapshot plus the admission-projected
authorization ref/SHA.  It never receives a ledger, Build Receipt, split
manifest or sibling split identity.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_AUTHORIZATION_PATH = "artifacts/r4/authorizations/train.json"
_CAPABILITY_PATH = "artifacts/r4/capabilities/train.json"
_PAYLOAD_PATH = "artifacts/r4/splits/train.jsonl"
_RUN_REF_PREFIX = "run:"
_MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
_MAX_CHILD_STDOUT = 2 * 1024 * 1024
_MAX_CHILD_STDERR = 2 * 1024 * 1024
_MAX_CHILD_SECONDS = 900


class ReleaseTrainingError(RuntimeError):
    """Raised when release-training trust or isolation fails closed."""


@dataclass(frozen=True)
class TrainTrustProjection:
    admission_run_ref: str
    admission_gate_result_ref: str
    admission_source_ref: str
    authorization_ref: str
    authorization_sha256: str


@dataclass(frozen=True)
class ReleaseTrainingResult:
    model_kind: str
    admission_run_ref: str
    admission_gate_result_ref: str
    train_authorization_ref: str
    train_authorization_sha256: str
    model_manifest_ref: str
    model_manifest_sha256: str
    training_report_ref: str
    training_report_sha256: str
    child_wall_ns: int

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "cemm-r4-release-training-parent-report-v1",
            "model_kind": self.model_kind,
            "admission_run_ref": self.admission_run_ref,
            "admission_gate_result_ref": self.admission_gate_result_ref,
            "train_authorization_ref": self.train_authorization_ref,
            "train_authorization_sha256": self.train_authorization_sha256,
            "model_manifest_ref": self.model_manifest_ref,
            "model_manifest_sha256": self.model_manifest_sha256,
            "training_report_ref": self.training_report_ref,
            "training_report_sha256": self.training_report_sha256,
            "child_wall_ns": self.child_wall_ns,
        }


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
        raise ReleaseTrainingError(f"cannot read {label}") from exc
    if len(raw) != size or len(raw) > maximum:
        raise ReleaseTrainingError(f"{label} changed while being read")
    return raw


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _latest_effective_r4_record(
    records: Sequence[Mapping[str, object]],
    effective: Mapping[str, str],
) -> Mapping[str, object]:
    if effective.get("R4") != "green":
        raise ReleaseTrainingError("R4 is not effectively green; release training is forbidden")
    for record in reversed(tuple(records)):
        if record.get("phase") == "R4":
            if record.get("status") != "green":
                raise ReleaseTrainingError("effective R4 green does not match the latest R4 transition")
            run_ref = record.get("admission_run_ref")
            gate_ref = record.get("admission_gate_result_ref")
            if (
                type(run_ref) is not str
                or not run_ref.startswith(_RUN_REF_PREFIX)
                or len(run_ref) != len(_RUN_REF_PREFIX) + 24
                or type(gate_ref) is not str
                or not gate_ref.startswith("gate_result:")
                or len(gate_ref) != len("gate_result:") + 24
            ):
                raise ReleaseTrainingError("effective R4 green lacks exact admission refs")
            return record
    raise ReleaseTrainingError("effective R4 green has no R4 transition record")


def _default_admission_dependencies(root: Path):
    from cemm_authoritative_hybrid.governance import (
        effective_replay_status,
        read_hash_chain,
    )

    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import validation_gate

    records = read_hash_chain(root / "governance" / "replay_status.jsonl")
    return records, effective_replay_status(records), validation_gate.load_verified_admission_receipt


def _extract_train_projection(
    root: Path,
    record: Mapping[str, object],
    receipt: object,
) -> TrainTrustProjection:
    run_ref = record["admission_run_ref"]
    gate_ref = record["admission_gate_result_ref"]
    if getattr(receipt, "phase", None) != "R4" or getattr(receipt, "tier", None) != "admission":
        raise ReleaseTrainingError("R4 ledger points at a non-R4 admission receipt")
    if getattr(receipt, "fresh", None) is not True:
        raise ReleaseTrainingError("R4 ledger points at a non-fresh admission receipt")
    if getattr(receipt, "run_ref", None) != run_ref:
        raise ReleaseTrainingError("R4 admission run ref differs from the effective ledger")
    if getattr(receipt, "gate_result_ref", None) != gate_ref:
        raise ReleaseTrainingError("R4 admission gate ref differs from the effective ledger")
    if getattr(receipt, "pre_admission_status_head_ref", None) != record.get("predecessor_ref"):
        raise ReleaseTrainingError("R4 admission predecessor binding differs from the ledger")
    if getattr(receipt, "source_ref", None) != record.get("source_base"):
        raise ReleaseTrainingError("R4 admission source binding differs from the ledger")

    evidence_files = getattr(receipt, "evidence_files", None)
    if type(evidence_files) is not tuple:
        raise ReleaseTrainingError("R4 admission receipt lacks immutable evidence files")
    evidence: dict[str, str] = {}
    for item in evidence_files:
        path = getattr(item, "path", None)
        digest = getattr(item, "sha256", None)
        if type(path) is not str or type(digest) is not str:
            raise ReleaseTrainingError("R4 admission evidence row is malformed")
        if path in evidence:
            raise ReleaseTrainingError("R4 admission evidence contains duplicate paths")
        evidence[path] = digest
    admitted_sha = evidence.get(_AUTHORIZATION_PATH)
    if (
        type(admitted_sha) is not str
        or len(admitted_sha) != 64
        or any(char not in "0123456789abcdef" for char in admitted_sha)
    ):
        raise ReleaseTrainingError("R4 admission does not authenticate the train authorization")

    raw = _read_bounded(
        root / _AUTHORIZATION_PATH,
        maximum=64 * 1024,
        label="admitted R4 train authorization",
    )
    if _sha256(raw) != admitted_sha:
        raise ReleaseTrainingError("train authorization bytes differ from admitted evidence")
    from cemm_authoritative_hybrid.r4_partition_contracts import R4ClassAuthorization

    try:
        authorization = R4ClassAuthorization.from_json_bytes(raw)
    except (TypeError, ValueError) as exc:
        raise ReleaseTrainingError("admitted train authorization failed strict ABI decoding") from exc
    if authorization.purpose != "training":
        raise ReleaseTrainingError("admitted class authorization is not training-scoped")
    return TrainTrustProjection(
        admission_run_ref=str(run_ref),
        admission_gate_result_ref=str(gate_ref),
        admission_source_ref=str(record["source_base"]),
        authorization_ref=authorization.authorization_ref,
        authorization_sha256=admitted_sha,
    )


def resolve_r4_train_trust(
    root: Path = ROOT,
    *,
    dependency_loader: Callable[[Path], tuple[Sequence[Mapping[str, object]], Mapping[str, str], Callable[..., object]]] | None = None,
) -> TrainTrustProjection:
    """Resolve the exact train authorization trust from effective R4 admission."""
    selected = _default_admission_dependencies if dependency_loader is None else dependency_loader
    try:
        records, effective, receipt_loader = selected(root)
        record = _latest_effective_r4_record(records, effective)
        loaded = receipt_loader(
            root=root,
            phase="R4",
            expected_status="passed",
            run_ref=record["admission_run_ref"],
        )
    except ReleaseTrainingError:
        raise
    except Exception as exc:
        raise ReleaseTrainingError("R4 admission trust reconstruction failed") from exc
    if type(loaded) is not tuple or len(loaded) != 2:
        raise ReleaseTrainingError("R4 admission loader returned an invalid result")
    receipt, evidence_paths = loaded
    if type(evidence_paths) is not tuple or _AUTHORIZATION_PATH not in evidence_paths:
        raise ReleaseTrainingError("R4 admission evidence policy omitted train authorization")
    return _extract_train_projection(root, record, receipt)


def _atomic_private_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def create_private_train_root(
    root: Path,
    trust: TrainTrustProjection,
) -> tuple[Path, object]:
    """Create and independently re-authenticate the three-file child snapshot."""
    from cemm_authoritative_hybrid.r4_partition_access import load_r4_train_episodes
    from cemm_authoritative_hybrid.r4_partition_contracts import R4ClassAuthorization

    batch = load_r4_train_episodes(
        _AUTHORIZATION_PATH,
        _CAPABILITY_PATH,
        root,
        expected_authorization_ref=trust.authorization_ref,
        expected_authorization_sha256=trust.authorization_sha256,
    )
    authorization_raw = _read_bounded(
        root / _AUTHORIZATION_PATH, maximum=64 * 1024, label="train authorization"
    )
    if _sha256(authorization_raw) != trust.authorization_sha256:
        raise ReleaseTrainingError("train authorization changed after admission reconstruction")
    authorization = R4ClassAuthorization.from_json_bytes(authorization_raw)
    capability_raw = _read_bounded(
        root / _CAPABILITY_PATH, maximum=64 * 1024, label="train capability"
    )
    if _sha256(capability_raw) != authorization.expected_capability_sha256:
        raise ReleaseTrainingError("train capability changed after train authentication")
    payload_raw = batch.snapshot.payload_bytes
    if _sha256(payload_raw) != batch.snapshot.payload_sha256:
        raise ReleaseTrainingError("authenticated train payload snapshot hash mismatch")

    isolated = Path(tempfile.mkdtemp(prefix="cemm-r4-train-isolated-")).resolve()
    try:
        for relative, raw in (
            (_AUTHORIZATION_PATH, authorization_raw),
            (_CAPABILITY_PATH, capability_raw),
            (_PAYLOAD_PATH, payload_raw),
        ):
            _atomic_private_write(isolated / relative, raw)
        actual = {
            path.relative_to(isolated).as_posix()
            for path in isolated.rglob("*")
            if path.is_file()
        }
        expected = {_AUTHORIZATION_PATH, _CAPABILITY_PATH, _PAYLOAD_PATH}
        if actual != expected:
            raise ReleaseTrainingError("private train root contains unexpected files")
        rebuilt = load_r4_train_episodes(
            _AUTHORIZATION_PATH,
            _CAPABILITY_PATH,
            isolated,
            expected_authorization_ref=trust.authorization_ref,
            expected_authorization_sha256=trust.authorization_sha256,
        )
        if rebuilt.snapshot != batch.snapshot or rebuilt.episodes != batch.episodes:
            raise ReleaseTrainingError("private train snapshot differs after reconstruction")
        return isolated, rebuilt
    except BaseException:
        shutil.rmtree(isolated, ignore_errors=True)
        raise


def child_command(
    *,
    model_kind: str,
    isolated_root: Path,
    trust: TrainTrustProjection,
    output: Path | None = None,
) -> tuple[str, ...]:
    if model_kind not in {"proposal", "realizer"}:
        raise ReleaseTrainingError("model kind must be proposal or realizer")
    script = ROOT / "scripts" / ("train_proposer.py" if model_kind == "proposal" else "train_realizer.py")
    config = ROOT / "configs" / ("proposal_release.json" if model_kind == "proposal" else "realizer_release.json")
    command = [
        sys.executable,
        str(script),
        "--config",
        str(config),
        "--release-isolated-root",
        str(isolated_root),
        "--expected-authorization-ref",
        trust.authorization_ref,
        "--expected-authorization-sha256",
        trust.authorization_sha256,
    ]
    if output is not None:
        command.extend(("--output", str(output)))
    forbidden = ("replay_status", "BUILD_RECEIPT", "split_manifest", "frozen_test", "selection", "calibration")
    flattened = " ".join(command)
    if any(token in flattened for token in forbidden):
        raise ReleaseTrainingError("child command discloses non-train governance or sibling evidence")
    return tuple(command)


def _artifact_dir(model_kind: str, output: Path | None) -> Path:
    if output is not None:
        return output if output.is_absolute() else ROOT / output
    config_path = ROOT / "configs" / ("proposal_release.json" if model_kind == "proposal" else "realizer_release.json")
    try:
        row = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseTrainingError("release config cannot be read") from exc
    value = row.get("artifact_dir")
    if type(value) is not str or not value:
        raise ReleaseTrainingError("release config lacks artifact_dir")
    return ROOT / value


def run_release_training(
    *,
    model_kind: str,
    output: Path | None = None,
    max_seconds: int = _MAX_CHILD_SECONDS,
) -> ReleaseTrainingResult:
    if type(max_seconds) is not int or not 1 <= max_seconds <= _MAX_CHILD_SECONDS:
        raise ReleaseTrainingError("child time bound is invalid")
    trust = resolve_r4_train_trust(ROOT)
    isolated, _batch = create_private_train_root(ROOT, trust)
    try:
        from cemm_authoritative_hybrid.process_control import (
            ProcessControlError,
            capture_bounded_process,
        )

        command = child_command(
            model_kind=model_kind,
            isolated_root=isolated,
            trust=trust,
            output=output,
        )
        env = dict(os.environ)
        env["PYTHONNOUSERSITE"] = "1"
        try:
            result = capture_bounded_process(
                command,
                max_stdout_bytes=_MAX_CHILD_STDOUT,
                max_stderr_bytes=_MAX_CHILD_STDERR,
                max_combined_output_bytes=_MAX_CHILD_STDOUT + _MAX_CHILD_STDERR,
                timeout_seconds=max_seconds,
                cwd=str(ROOT),
                env=env,
            )
        except ProcessControlError as exc:
            raise ReleaseTrainingError("release-training child failed process containment") from exc
        if result.returncode != 0:
            raise ReleaseTrainingError(
                f"release-training child exited with code {result.returncode}"
            )
        artifact_dir = _artifact_dir(model_kind, output)
        manifest_raw = _read_bounded(
            artifact_dir / "model_manifest.json",
            maximum=1024 * 1024,
            label="release model manifest",
        )
        report_raw = _read_bounded(
            artifact_dir / "training_report.json",
            maximum=16 * 1024 * 1024,
            label="release training report",
        )
        manifest_sha = _sha256(manifest_raw)
        report_sha = _sha256(report_raw)
        return ReleaseTrainingResult(
            model_kind=model_kind,
            admission_run_ref=trust.admission_run_ref,
            admission_gate_result_ref=trust.admission_gate_result_ref,
            train_authorization_ref=trust.authorization_ref,
            train_authorization_sha256=trust.authorization_sha256,
            model_manifest_ref=f"release_model_manifest:{manifest_sha[:24]}",
            model_manifest_sha256=manifest_sha,
            training_report_ref=f"release_training_report:{report_sha[:24]}",
            training_report_sha256=report_sha,
            child_wall_ns=result.wall_ns,
        )
    finally:
        shutil.rmtree(isolated, ignore_errors=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("proposal", "realizer"), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-seconds", type=int, default=_MAX_CHILD_SECONDS)
    args = parser.parse_args(argv)
    try:
        report = run_release_training(
            model_kind=args.model,
            output=args.output,
            max_seconds=args.max_seconds,
        )
    except ReleaseTrainingError as exc:
        print(f"release training blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
