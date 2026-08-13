#!/usr/bin/env python3
"""Run the exact authenticated R5 active test union in one pytest process."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from types import MappingProxyType
from typing import Callable, ContextManager, Mapping, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
_SOURCE_DIR = _SCRIPT_DIR.parent / "src"
if str(_SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(_SOURCE_DIR))
from cemm_authoritative_hybrid import process_control as _process_control
sys.modules.setdefault("process_control", _process_control)

if __package__:
    from scripts.test_inventory_core import (
        InventoryResult,
        PHASES,
        content_ref,
        load_and_verify,
        verify_document_authority_pin,
    )
    from scripts import validation_gate
else:
    from test_inventory_core import (
        InventoryResult,
        PHASES,
        content_ref,
        load_and_verify,
        verify_document_authority_pin,
    )
    import validation_gate


PHASE = "R5"
SELECTOR_SCHEMA = "cemm-pytest-selector-v1"
SUMMARY_SCHEMA = "cemm-r5-active-suite-result-v1"
INACTIVE_REASONS = (
    "disposition_deferred",
    "disposition_retired",
    "future_phase",
    "lifecycle_historical",
    "lifecycle_rewritten",
    "superseded",
)


class ActiveSuiteError(RuntimeError):
    """The governed active-suite contract or its execution failed closed."""


class ActiveSuiteFailure(ActiveSuiteError):
    """The authenticated suite executed and reported a test failure."""


@dataclass(frozen=True)
class ActiveSuiteContract:
    root_path: str
    source_ref: str
    source_tree_ref: str
    phase: str
    inventory_ref: str
    inventory_sha256: str
    literal_metadata_ref: str
    active_node_set_ref: str
    active_node_ids: tuple[str, ...]
    collectable_node_set_ref: str
    collectable_node_ids: tuple[str, ...]
    r5_disposition_receipt_ref: str
    inactive_node_ids_by_reason: Mapping[str, tuple[str, ...]]


def _git_source_identity(root: Path) -> tuple[str, bool, str]:
    """Bind one checkout to its commit and complete regular-file tree."""

    source_ref, dirty = validation_gate._clean_git_snapshot(root)
    blobs = validation_gate._tracked_source_blobs(root, source_ref)
    tree_ref = content_ref(
        "source_tree",
        {"blobs": [[path, object_id] for path, object_id in sorted(blobs.items())]},
    )
    return source_ref, dirty, tree_ref


def _authenticate_snapshot_files(root: Path, source_ref: str) -> None:
    """Reconstruct every executable checkout byte from the committed blob map."""

    blobs = validation_gate._tracked_source_blobs(root, source_ref)
    manifest = validation_gate._InputManifestCache(root, committed_blobs=blobs)
    validation_gate._authenticate_complete_source_snapshot(root, manifest, blobs)


def _set_snapshot_writable(root: Path, writable: bool) -> None:
    """Seal/unseal every regular source file while keeping directories usable."""

    for directory, _names, filenames in os.walk(root):
        for filename in filenames:
            path = Path(directory) / filename
            if path.is_symlink():
                raise ActiveSuiteError("authenticated snapshot contains a symlink")
            mode = path.stat().st_mode
            if writable:
                path.chmod(mode | stat.S_IWRITE)
            else:
                path.chmod(mode & ~(stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH))


def _git_worktree_command(root: Path, arguments: Sequence[str]):
    try:
        return validation_gate.capture_bounded_process(
            ["git", "--no-replace-objects", "-C", str(root), *arguments],
            max_stdout_bytes=2 * 1024 * 1024,
            max_stderr_bytes=2 * 1024 * 1024,
            max_combined_output_bytes=2 * 1024 * 1024,
            timeout_seconds=120,
            env=validation_gate._sanitized_git_environment(),
        )
    except (OSError, ValueError, validation_gate.ProcessControlError) as exc:
        reason = getattr(getattr(exc, "reason", None), "value", "start_failed")
        raise ActiveSuiteError(f"bounded Git worktree error: {reason}") from exc


def _phase_index(phase: str) -> int:
    try:
        return PHASES.index(phase)
    except ValueError as exc:
        raise ActiveSuiteError(f"unknown activation phase: {phase}") from exc


def classify_inactive_nodes(
    result: InventoryResult | object,
    *,
    phase: str,
) -> Mapping[str, tuple[str, ...]]:
    """Partition every physically collectable inactive node by governed cause."""

    active = set(getattr(result, "active_node_ids", ()))
    collectable = set(getattr(result, "collectable_node_ids", ()))
    if not active.issubset(collectable):
        raise ActiveSuiteError("active node set is not collectable")
    source_tests = getattr(result, "source_tests", {})
    later_nodes = getattr(result, "later_nodes", {})
    source_by_node = {
        node_id: record
        for record in source_tests.values()
        for node_id in record.case_node_ids
    }
    superseded = {
        record.supersedes_node_id
        for record in later_nodes.values()
        if record.supersedes_node_id is not None
    }
    deferred = set(getattr(result, "deferred_r5_assertion_refs", ()))
    retired = set(getattr(result, "retired_r5_assertion_refs", ()))
    buckets: dict[str, list[str]] = {reason: [] for reason in INACTIVE_REASONS}
    unclassified: list[str] = []

    for node_id in sorted(collectable - active):
        source = source_by_node.get(node_id)
        later = later_nodes.get(node_id)
        assertion_ref = (
            later.assertion_ref if later is not None
            else source.assertion_ref if source is not None
            else None
        )
        if node_id in superseded:
            reason = "superseded"
        elif assertion_ref in deferred:
            reason = "disposition_deferred"
        elif assertion_ref in retired:
            reason = "disposition_retired"
        elif source is not None and source.classification == "historical":
            reason = "lifecycle_historical"
        elif source is not None and source.classification == "rewritten":
            reason = "lifecycle_rewritten"
        else:
            activation = (
                later.activation_phase if later is not None
                else source.activation_phase if source is not None
                else None
            )
            if (
                isinstance(activation, str)
                and _phase_index(activation) > _phase_index(phase)
            ):
                reason = "future_phase"
            else:
                unclassified.append(node_id)
                continue
        buckets[reason].append(node_id)

    if unclassified:
        raise ActiveSuiteError(
            "unclassified collectable inactive nodes: "
            + ", ".join(unclassified[:16])
        )
    normalized = {
        reason: tuple(nodes)
        for reason, nodes in sorted(buckets.items())
    }
    classified_count = sum(len(nodes) for nodes in normalized.values())
    if classified_count != len(collectable - active):
        raise ActiveSuiteError("inactive classification is not an exact partition")
    return MappingProxyType(normalized)


def authenticate_r5_active_suite(
    root: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
    source_identity_provider: Callable[[Path], tuple[str, bool, str]] = _git_source_identity,
) -> ActiveSuiteContract:
    """Authenticate the immutable inventory and its complete R5 overlay."""

    root_path = root.resolve()
    source_ref, dirty, source_tree_ref = source_identity_provider(root_path)
    if dirty:
        raise ActiveSuiteError("R5 active suite requires a clean committed source")
    inventory_path = root_path / "governance" / "test_inventory.json"
    inventory_sha256 = verify_document_authority_pin(
        root_path,
        inventory_path,
        source_reader=source_reader,
    )
    result = load_and_verify(
        root_path,
        inventory_path,
        phase=PHASE,
        enforce_reviewed_counts=True,
        expected_sha256=inventory_sha256,
        source_reader=source_reader,
    )
    if result.r5_disposition_receipt_ref is None:
        raise ActiveSuiteError("R5 disposition receipt is unavailable")
    inactive = classify_inactive_nodes(result, phase=PHASE)
    return ActiveSuiteContract(
        root_path=str(root_path),
        source_ref=source_ref,
        source_tree_ref=source_tree_ref,
        phase=PHASE,
        inventory_ref=result.inventory_ref,
        inventory_sha256=inventory_sha256,
        literal_metadata_ref=result.literal_metadata_ref,
        active_node_set_ref=result.active_node_set_ref,
        active_node_ids=result.active_node_ids,
        collectable_node_set_ref=result.collectable_node_set_ref,
        collectable_node_ids=result.collectable_node_ids,
        r5_disposition_receipt_ref=result.r5_disposition_receipt_ref,
        inactive_node_ids_by_reason=inactive,
    )


def _contracts_match_snapshot(
    expected: ActiveSuiteContract,
    observed: ActiveSuiteContract,
) -> bool:
    return replace(expected, root_path=observed.root_path) == observed


@contextmanager
def _detached_git_snapshot(
    root: Path,
    source_ref: str,
    temporary_parent: Path | None,
):
    """Materialize and remove a detached worktree at the authenticated commit."""

    if temporary_parent is None:
        raise ActiveSuiteError("detached source snapshot requires a temporary parent")
    raw_prefix = validation_gate._bounded_git_probe(
        root,
        ("rev-parse", "--show-prefix"),
        context="resolve the Hybrid MVP project prefix",
        timeout_seconds=30,
    )
    try:
        prefix = raw_prefix.decode("utf-8", errors="strict").rstrip("\n")
    except UnicodeDecodeError as exc:
        raise ActiveSuiteError("Hybrid MVP project prefix is not UTF-8") from exc
    if (
        not raw_prefix.endswith(b"\n")
        or raw_prefix.count(b"\n") != 1
        or not prefix
        or not prefix.endswith("/")
        or "\\" in prefix
        or any(part in {"", ".", ".."} for part in Path(prefix).parts)
    ):
        raise ActiveSuiteError("Hybrid MVP project prefix is not canonical")

    worktree = temporary_parent / "source-worktree"
    added = False
    add_attempted = False
    try:
        add_attempted = True
        completed = _git_worktree_command(
            root,
            ("worktree", "add", "--detach", "--force", str(worktree), source_ref),
        )
        if completed.returncode != 0:
            raise ActiveSuiteError("cannot materialize authenticated source snapshot")
        added = True
        snapshot_root = worktree.joinpath(*prefix.rstrip("/").split("/"))
        try:
            resolved = snapshot_root.resolve(strict=True)
            resolved.relative_to(worktree.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise ActiveSuiteError("authenticated source snapshot root is unavailable") from exc
        yield resolved
    finally:
        cleanup_errors: list[str] = []
        if add_attempted:
            if added and worktree.exists():
                try:
                    _set_snapshot_writable(worktree, True)
                except (OSError, ActiveSuiteError):
                    cleanup_errors.append("restore-write")
            try:
                removed = _git_worktree_command(
                    root, ("worktree", "remove", "--force", str(worktree))
                )
                if added and removed.returncode != 0:
                    cleanup_errors.append("remove")
            except ActiveSuiteError:
                cleanup_errors.append("remove")
            if worktree.exists():
                try:
                    resolved_worktree = worktree.resolve(strict=True)
                    parent_path = temporary_parent.resolve(strict=True)
                    if resolved_worktree.parent != parent_path:
                        raise ValueError("worktree is not the exact cleanup target")
                    shutil.rmtree(resolved_worktree)
                except (OSError, ValueError):
                    cleanup_errors.append("fallback-delete")
            try:
                pruned = _git_worktree_command(
                    root, ("worktree", "prune", "--expire", "now")
                )
                if pruned.returncode != 0:
                    cleanup_errors.append("prune")
            except ActiveSuiteError:
                cleanup_errors.append("prune")
        if cleanup_errors:
            raise ActiveSuiteError(
                "cannot clean authenticated source snapshot: "
                + ",".join(sorted(set(cleanup_errors)))
            )


def build_selector(
    contract: ActiveSuiteContract,
    *,
    candidate: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build or authenticate the exact content-addressed admission selector."""

    expected_material: dict[str, object] = {
        "active_node_ids": list(contract.active_node_ids),
        "collectable_node_ids": list(contract.collectable_node_ids),
        "mode": "admission",
        "schema": SELECTOR_SCHEMA,
        "test_root": "tests",
    }
    supplied = dict(expected_material if candidate is None else candidate)
    supplied_ref = supplied.pop("selector_ref", None)
    if set(supplied) != set(expected_material):
        raise ActiveSuiteError("selector fields are not exact")
    if supplied.get("active_node_ids") != expected_material["active_node_ids"]:
        raise ActiveSuiteError("selector active node set differs from R5 authority")
    if supplied.get("collectable_node_ids") != expected_material["collectable_node_ids"]:
        raise ActiveSuiteError("selector collectable node set differs from R5 authority")
    for field in ("mode", "schema", "test_root"):
        if supplied.get(field) != expected_material[field]:
            raise ActiveSuiteError(f"selector {field} differs from R5 authority")
    expected_ref = content_ref("pytest_selector", expected_material)
    if supplied_ref is not None and supplied_ref != expected_ref:
        raise ActiveSuiteError("selector identity does not match its content")
    return {**expected_material, "selector_ref": expected_ref}


def _default_process_runner(
    *,
    root: Path,
    run_root: Path,
    manifest_path: Path,
    report_path: Path,
    limits: Mapping[str, int],
):
    environment, _pytest_args = validation_gate.isolated_test_environment(
        run_root,
    )
    command = validation_gate._pytest_runner_command(
        root,
        manifest_path,
        report_path,
    )
    return validation_gate.capture_bounded_process(
        command,
        cwd=root,
        env=environment,
        max_stdout_bytes=limits["max_output_bytes"],
        max_stderr_bytes=limits["max_output_bytes"],
        max_combined_output_bytes=limits["max_output_bytes"],
        timeout_seconds=limits["pytest_timeout_seconds"],
        rss_reader_factory=validation_gate._rss_reader_for,
    )


def _validate_passed_report(
    contract: ActiveSuiteContract,
    selector: Mapping[str, object],
    process_result: object,
    parsed: object,
) -> None:
    payload = getattr(parsed, "payload", None)
    if getattr(parsed, "error_code", None) is not None or not isinstance(payload, Mapping):
        raise ActiveSuiteError(
            "structured report authentication failed: "
            f"{getattr(parsed, 'error_code', 'missing payload')}"
        )
    if payload.get("selector_ref") != selector["selector_ref"]:
        raise ActiveSuiteError("report selector identity differs from authenticated selector")
    if tuple(payload.get("active_node_ids", ())) != contract.active_node_ids:
        raise ActiveSuiteError("report active node set differs from authenticated R5 set")
    if tuple(payload.get("collected_node_ids", ())) != contract.collectable_node_ids:
        raise ActiveSuiteError("report collection differs from authenticated R5 collection")
    if tuple(payload.get("selected_node_ids", ())) != contract.active_node_ids:
        raise ActiveSuiteError("report selected nodes differ from authenticated R5 set")
    expected_deselected = tuple(
        sorted(set(contract.collectable_node_ids) - set(contract.active_node_ids))
    )
    if tuple(payload.get("deselected_node_ids", ())) != expected_deselected:
        raise ActiveSuiteError("report inactive-node deselection is incomplete")
    counts = payload.get("counts")
    expected_counts = {
        "error": 0,
        "failure": 0,
        "passed": len(contract.active_node_ids),
        "skip": 0,
        "xfail": 0,
        "xpass": 0,
    }
    if counts != expected_counts:
        raw_facts = payload.get("facts", ())
        failed_nodes: list[str] = []
        if isinstance(raw_facts, (list, tuple)):
            for fact in raw_facts:
                if (
                    isinstance(fact, Mapping)
                    and fact.get("classification") in {"error", "failure", "skip", "xfail", "xpass"}
                    and isinstance(fact.get("node_id"), str)
                ):
                    failed_nodes.append(str(fact["node_id"]))
                if len(failed_nodes) == 16:
                    break
        detail = ", ".join(failed_nodes) if failed_nodes else "no bounded node detail"
        raise ActiveSuiteFailure(
            f"active suite did not pass exactly: {counts}; nodes={detail}"
        )
    disposition = getattr(parsed, "disposition", None)
    returncode = getattr(process_result, "returncode", None)
    if disposition != "passed" or returncode != 0:
        if disposition == "failed" or returncode == 1:
            raise ActiveSuiteFailure("authenticated R5 active suite failed")
        raise ActiveSuiteError("pytest process and authenticated report disagree")


def run_authenticated_suite(
    root: Path,
    contract: ActiveSuiteContract,
    *,
    process_runner: Callable[..., object] = _default_process_runner,
    report_parser: Callable[..., object] = validation_gate.parse_pytest_report,
    temporary_parent: Path | None = None,
    snapshot_provider: Callable[[Path, str, Path | None], ContextManager[Path]] = _detached_git_snapshot,
    source_identity_provider: Callable[[Path], tuple[str, bool, str]] = _git_source_identity,
    snapshot_authenticator: Callable[[Path, str], None] = _authenticate_snapshot_files,
    snapshot_sealer: Callable[[Path, bool], None] = _set_snapshot_writable,
) -> dict[str, object]:
    """Run one immutable, manifest-bound pytest process and return only a summary."""

    root_path = root.resolve()
    if str(root_path) != contract.root_path:
        raise ActiveSuiteError("authenticated suite root differs from contract root")
    source_ref, dirty, source_tree_ref = source_identity_provider(root_path)
    if dirty or source_ref != contract.source_ref or source_tree_ref != contract.source_tree_ref:
        raise ActiveSuiteError("live source differs from authenticated suite contract")
    selector = build_selector(contract)
    parent = None if temporary_parent is None else str(temporary_parent.resolve())
    with tempfile.TemporaryDirectory(
        prefix="cemm-r5-active-suite-",
        dir=parent,
    ) as temporary:
        run_root = Path(temporary)
        with snapshot_provider(root_path, contract.source_ref, run_root) as snapshot_root:
            snapshot_path = snapshot_root.resolve()
            observed = authenticate_r5_active_suite(
                snapshot_path,
                source_identity_provider=source_identity_provider,
            )
            if not _contracts_match_snapshot(contract, observed):
                raise ActiveSuiteError("detached source snapshot differs from contract")
            snapshot_authenticator(snapshot_path, contract.source_ref)
            graph = validation_gate.load_gate_graph(
                snapshot_path / "configs" / "validation_gates.json"
            )
            limits = graph.limits
            snapshot_sealer(snapshot_path, False)
            snapshot_authenticator(snapshot_path, contract.source_ref)

            control_root = run_root / "control"
            control_root.mkdir()
            manifest_path = control_root / "selector.json"
            report_path = control_root / "pytest-report.json"
            manifest_path.write_bytes(validation_gate.canonical_json_bytes(selector))
            try:
                process_result = process_runner(
                    root=snapshot_path,
                    run_root=control_root,
                    manifest_path=manifest_path,
                    report_path=report_path,
                    limits=limits,
                )
            except validation_gate.ProcessControlError as exc:
                reason = getattr(exc.reason, "value", str(exc.reason))
                raise ActiveSuiteError(
                    f"bounded pytest process error: {reason}; "
                    f"termination_confirmed={exc.termination_confirmed}"
                ) from exc
            parsed = report_parser(
                report_path,
                max_bytes=limits["max_report_bytes"],
                expected_selector=selector,
            )
            _validate_passed_report(contract, selector, process_result, parsed)
            snapshot_authenticator(snapshot_path, contract.source_ref)
            report_ref = getattr(parsed, "report_ref", None)
            if (
                type(report_ref) is not str
                or not report_ref.startswith("pytest_report:")
                or len(report_ref) != len("pytest_report:") + 24
            ):
                raise ActiveSuiteError("authenticated pytest report identity is unavailable")

    inactive_counts = {
        reason: len(nodes)
        for reason, nodes in contract.inactive_node_ids_by_reason.items()
    }
    summary: dict[str, object] = {
        "active_node_count": len(contract.active_node_ids),
        "active_node_set_ref": contract.active_node_set_ref,
        "collectable_node_count": len(contract.collectable_node_ids),
        "collectable_node_set_ref": contract.collectable_node_set_ref,
        "disposition": "passed",
        "inactive_node_count": sum(inactive_counts.values()),
        "inactive_reason_counts": inactive_counts,
        "inventory_ref": contract.inventory_ref,
        "inventory_sha256": contract.inventory_sha256,
        "literal_metadata_ref": contract.literal_metadata_ref,
        "phase": contract.phase,
        "pytest_process_count": 1,
        "r5_disposition_receipt_ref": contract.r5_disposition_receipt_ref,
        "schema": SUMMARY_SCHEMA,
        "selector_ref": selector["selector_ref"],
        "source_ref": contract.source_ref,
        "source_tree_ref": contract.source_tree_ref,
        "pytest_report_ref": report_ref,
    }
    summary["result_ref"] = content_ref("r5_active_suite_result", summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args, unknown = parser.parse_known_args(list(argv) if argv is not None else None)
    del args
    if unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    root = Path(__file__).resolve().parents[1]
    try:
        contract = authenticate_r5_active_suite(root)
        summary = run_authenticated_suite(root, contract)
    except ActiveSuiteFailure as exc:
        print(json.dumps({
            "disposition": "failed",
            "error": str(exc)[:4096],
            "phase": PHASE,
            "schema": SUMMARY_SCHEMA,
        }, separators=(",", ":"), sort_keys=True), file=sys.stderr)
        return 1
    except (ActiveSuiteError, validation_gate.GateConfigError) as exc:
        print(json.dumps({
            "disposition": "error",
            "error": str(exc)[:4096],
            "phase": PHASE,
            "schema": SUMMARY_SCHEMA,
        }, separators=(",", ":"), sort_keys=True), file=sys.stderr)
        return 2
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
