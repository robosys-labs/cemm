#!/usr/bin/env python3
"""Run the exact authenticated R5 active test union in one pytest process."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

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
) -> ActiveSuiteContract:
    """Authenticate the immutable inventory and its complete R5 overlay."""

    root_path = root.resolve()
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
) -> dict[str, object]:
    """Run one ephemeral, manifest-bound pytest process and return only a summary."""

    root_path = root.resolve()
    graph = validation_gate.load_gate_graph(
        root_path / "configs" / "validation_gates.json"
    )
    limits = graph.limits
    selector = build_selector(contract)
    parent = None if temporary_parent is None else str(temporary_parent.resolve())
    with tempfile.TemporaryDirectory(
        prefix="cemm-r5-active-suite-",
        dir=parent,
    ) as temporary:
        run_root = Path(temporary)
        manifest_path = run_root / "selector.json"
        report_path = run_root / "pytest-report.json"
        manifest_path.write_bytes(validation_gate.canonical_json_bytes(selector))
        process_result = process_runner(
            root=root_path,
            run_root=run_root,
            manifest_path=manifest_path,
            report_path=report_path,
            limits=limits,
        )
        parsed = report_parser(
            report_path,
            max_bytes=limits["max_report_bytes"],
            expected_selector=selector,
        )
        _validate_passed_report(contract, selector, process_result, parsed)

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
        print(f"R5 active suite failed: {exc}", file=sys.stderr)
        return 1
    except (ActiveSuiteError, validation_gate.GateConfigError) as exc:
        print(f"R5 active suite error: {exc}", file=sys.stderr)
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
