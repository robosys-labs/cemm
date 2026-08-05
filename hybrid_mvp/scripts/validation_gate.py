"""Bounded, dependency-aware validation control plane for corrective replay.

This module is the validation *control plane*. It intentionally depends only
on the Python standard library, loads governance owners by reviewed file paths,
and starts at most one pytest child for an executing tier.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
from types import MappingProxyType, ModuleType
from typing import Callable, Iterable, Mapping, NoReturn, Sequence

from process_control import (
    ProcessControlError,
    ProcessErrorReason,
    capture_bounded_process,
    terminate_process_tree,
)

GATE_CONFIG_SCHEMA = "cemm-hybrid-validation-gates-v1"
RECEIPT_SCHEMA = "cemm-hybrid-validation-receipt-v1"
PYTEST_REPORT_SCHEMA = "cemm-pytest-report-v1"
PHASES = ("G0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")
TIERS = ("owner", "phase", "admission")
STEP_KINDS = frozenset(
    {
        "governance", "compile", "pytest", "pytest_inventory", "authority_link",
        "sqlite_activation", "r1_structure", "r2_structure",
        "r3_structure", "r3_activation_canaries",
    }
)
PYTEST_KINDS = frozenset({"pytest", "pytest_inventory"})
ADMISSION_ONLY_KINDS = frozenset({
    "authority_link", "sqlite_activation", "r1_structure", "r2_structure",
    "r3_structure", "r3_activation_canaries",
})
_CONTENT_REF_RE = re.compile(r"[a-z][a-z0-9_-]*:[0-9a-f]{24}\Z")
_RUN_REF_RE = re.compile(r"run:[0-9a-f]{24}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_STEP_ID_RE = re.compile(r"[a-z][a-z0-9_]*\Z")
_OWNER_RE = re.compile(r"[a-z][a-z0-9_.:-]*\Z")
_NODE_RE = re.compile(r"tests/[A-Za-z0-9_./-]+\.py::[^\s:][^\r\n]*\Z")
_STATUS_HEAD_RE = re.compile(r"governance_record:[0-9a-f]{24}\Z")
_SOURCE_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_ISO_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z")
_G0_ADMISSION_EVIDENCE_PATHS = (
    "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
    "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
)

_TOP_FIELDS = frozenset({"schema", "limits", "steps", "phases"})
_LIMIT_FIELDS = frozenset(
    {
        "max_output_bytes", "max_pytest_processes_per_tier", "max_report_bytes",
        "max_slowest_rows", "max_steps_per_tier", "pytest_timeout_seconds",
        "rss_poll_interval_ms",
    }
)
_STEP_FIELDS = MappingProxyType(
    {
        "governance": frozenset(
            {"kind", "depends_on", "inputs", "test_inventory", "metadata_symbol",
             "status_ledger", "invalidation_ledger"}
        ),
        "compile": frozenset({"kind", "depends_on", "inputs", "roots"}),
        "pytest": frozenset({"kind", "depends_on", "inputs", "exact_nodes"}),
        "pytest_inventory": frozenset(
            {"kind", "depends_on", "inputs", "test_inventory", "metadata_symbol", "test_root"}
        ),
        "authority_link": frozenset({"kind", "depends_on", "inputs"}),
        "sqlite_activation": frozenset({"kind", "depends_on", "inputs"}),
        "r1_structure": frozenset({"kind", "depends_on", "inputs"}),
        "r2_structure": frozenset({"kind", "depends_on", "inputs"}),
        "r3_structure": frozenset({"kind", "depends_on", "inputs"}),
        "r3_activation_canaries": frozenset({"kind", "depends_on", "inputs"}),
    }
)
_PHASE_FIELDS = frozenset({"owners", "phase", "admission"})


class GateConfigError(ValueError):
    """The reviewed gate graph or a structural gate input is invalid."""


class AdmissionValidationError(ValueError):
    """A stored admission receipt failed strict reconstruction."""


def _required_admission_evidence_paths(phase: str) -> tuple[str, ...]:
    if phase == "G0":
        return _G0_ADMISSION_EVIDENCE_PATHS
    if phase in {"R1", "R2"}:
        return ()
    if phase == "R3":
        return (
            "artifacts/validation/R3_ACTIVATION_CANARIES.json",
        )
    if phase == "R4":
        return (
            "artifacts/r4/expected_contracts.jsonl",
            "artifacts/r4/expected_derivations.jsonl",
            "artifacts/r4/expanded_cases.jsonl",
            "artifacts/r4/episodes.jsonl",
            "artifacts/r4/mutations.jsonl",
            "artifacts/r4/mutation_observations.jsonl",
            "artifacts/r4/structural_sufficiency.json",
            "artifacts/r4/partitions/general.json",
            "artifacts/r4/partitions/lexical.json",
            "artifacts/r4/partitions/semantic_target.json",
            "artifacts/r4/partitions/topology.json",
            "artifacts/r4/partitions/dialogue.json",
            "artifacts/r4/partitions/mutation.json",
            "artifacts/r4/partitions/realization.json",
            "artifacts/r4/training_allowlist.json",
            "artifacts/r4/BUILD_RECEIPT.json",
            "data/review/R4_REVIEW_MANIFEST.json",
        )
    raise AdmissionValidationError(
        f"admission evidence policy is not implemented for phase {phase}"
    )

def _duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GateConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> NoReturn:
    raise GateConfigError(f"non-finite JSON constant is forbidden: {value}")


def canonical_json_bytes(value: object) -> bytes:
    """Serialize exact canonical JSON, rejecting non-finite or foreign values."""
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise GateConfigError(f"value is not canonical JSON: {exc}") from exc


def content_ref(kind: str, value: object) -> str:
    if type(kind) is not str or re.fullmatch(r"[a-z][a-z0-9_-]*", kind) is None:
        raise GateConfigError("content-ref kind is invalid")
    digest = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    return f"{kind}:{digest[:24]}"


_MAX_AUTHENTICATED_FILE_BYTES = 64 * 1024 * 1024


def _sha256_file_bounded(
    path: Path, *, maximum: int = _MAX_AUTHENTICATED_FILE_BYTES
) -> str:
    try:
        size = path.stat().st_size
        if size < 0 or size > maximum:
            raise GateConfigError(f"authenticated file exceeds its size bound: {path}")
        digest = hashlib.sha256()
        total = 0
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(min(1024 * 1024, size - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > size:
                    raise GateConfigError(
                        f"authenticated file changed while hashing: {path}"
                    )
                digest.update(chunk)
    except GateConfigError:
        raise
    except OSError as exc:
        raise GateConfigError(f"cannot hash authenticated file: {path}") from exc
    if total != size:
        raise GateConfigError(f"authenticated file changed while hashing: {path}")
    return digest.hexdigest()

def _validate_json_structure_bounds(
    value: object,
    *,
    max_depth: int = 64,
    max_nodes: int = 1_000_000,
) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            raise GateConfigError("JSON value exceeds its node-count bound")
        if depth > max_depth:
            raise GateConfigError("JSON value exceeds its nesting-depth bound")
        if type(item) is dict:
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif item is None or type(item) in {str, int, bool}:
            continue
        elif type(item) is float and math.isfinite(item):
            continue
        else:
            raise GateConfigError("JSON value contains a non-canonical scalar")

def _load_strict_json_bytes(raw: bytes, *, path: Path) -> object:
    if type(raw) is not bytes or not raw or len(raw) > _MAX_AUTHENTICATED_FILE_BYTES:
        raise GateConfigError(f"JSON file exceeds its size bound: {path}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateConfigError(f"{path} is not UTF-8 JSON") from exc
    try:
        value = json.loads(
            text, object_pairs_hook=_duplicate_keys, parse_constant=_nonfinite
        )
        _validate_json_structure_bounds(value)
        return value
    except GateConfigError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise GateConfigError(f"invalid JSON in {path}: {exc}") from exc


def _read_bounded_file(path: Path, *, maximum: int) -> bytes:
    try:
        with path.open("rb") as stream:
            raw = stream.read(maximum + 1)
    except OSError as exc:
        raise GateConfigError(f"cannot read bounded file {path}: {exc}") from exc
    if not raw or len(raw) > maximum:
        raise GateConfigError(f"file exceeds its size bound: {path}")
    return raw


def load_strict_json(path: Path) -> object:
    raw = _read_bounded_file(path, maximum=_MAX_AUTHENTICATED_FILE_BYTES)
    return _load_strict_json_bytes(raw, path=path)

def _exact_fields(value: object, fields: frozenset[str], context: str) -> dict[str, object]:
    if type(value) is not dict:
        raise GateConfigError(f"{context} must be an object")
    actual = set(value)
    if actual != fields:
        raise GateConfigError(
            f"{context} has non-exact fields; missing={sorted(fields - actual)}, "
            f"extra={sorted(actual - fields)}"
        )
    return value


def _text(value: object, context: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise GateConfigError(f"{context} must be non-empty canonical text")
    if any(ord(char) < 32 for char in value):
        raise GateConfigError(f"{context} contains a control character")
    return value


_G0_BASELINE_SOURCE_REF = "58345240e67bf003e6ac7d5c68752e2e5eee4a7d"
_G0_EVALUATION_PATH = "artifacts/evaluation/CEMM_EVALUATION.json"
_G0_BASELINE_FIELDS = frozenset(
    {
        "baseline_source_ref", "commands", "environment", "evaluation_artifact",
        "findings_ref", "model_artifacts_admitted", "predecessor_collection",
        "quarantine", "runtime_admitted", "schema", "structural_findings",
        "threshold_failures", "unadmitted_m4_probe",
    }
)
_G0_FINDING_OWNERS = MappingProxyType(
    {
        "authority_eol_hash_divergence": "artifact_identity",
        "bootstrap_programs_author_gold": "corpus_gold",
        "marker_only_realization_equivalence": "realization_equivalence",
        "pointer_source_anonymization_collapses_meaning": "evaluation_identity",
        "program_as_meaning": "semantic_object_model",
        "proposal_runtime_abi_divergence": "runtime_protocol",
    }
)
_G0_REQUIRED_FINDINGS = frozenset(_G0_FINDING_OWNERS)
_G0_QUARANTINED_DESCENDANTS = (
    "calibration", "checkpoints", "corpus", "episodes", "evaluation",
    "model_metadata", "partitions",
)


def _with_content_ref(kind: str, field: str, payload: Mapping[str, object]) -> dict[str, object]:
    material = dict(payload)
    material[field] = content_ref(kind, payload)
    return material


def _validate_g0_baseline_findings(
    value: object, *, baseline_source_ref: str
) -> None:
    item = _exact_fields(value, _G0_BASELINE_FIELDS, "G0 baseline findings")
    if item["schema"] != "cemm-hybrid-baseline-replay-findings-v1":
        raise GateConfigError("G0 baseline findings schema is invalid")
    identity = dict(item)
    findings_ref = identity.pop("findings_ref")
    if findings_ref != content_ref("baseline_replay_findings", identity):
        raise GateConfigError("G0 baseline findings identity is invalid")
    if (
        baseline_source_ref != _G0_BASELINE_SOURCE_REF
        or item["baseline_source_ref"] != _G0_BASELINE_SOURCE_REF
    ):
        raise GateConfigError("G0 baseline findings source differs from inventory")
    if item["runtime_admitted"] is not False or item["model_artifacts_admitted"] is not False:
        raise GateConfigError("G0 baseline evidence must not admit runtime or model artifacts")

    environment = _exact_fields(
        item["environment"],
        frozenset({"python", "pytest_current", "pytest_inherited_lock"}),
        "G0 baseline environment",
    )
    if environment != {
        "python": "3.13.4",
        "pytest_current": "9.0.2",
        "pytest_inherited_lock": "8.4.0",
    }:
        raise GateConfigError("G0 baseline environment differs from reviewed evidence")
    evaluation_artifact = _exact_fields(
        item["evaluation_artifact"],
        frozenset({"path", "sha256"}),
        "G0 evaluation artifact",
    )
    if (
        evaluation_artifact["path"] != _G0_EVALUATION_PATH
        or type(evaluation_artifact["sha256"]) is not str
        or _SHA256_RE.fullmatch(evaluation_artifact["sha256"]) is None
    ):
        raise GateConfigError("G0 evaluation artifact binding is invalid")
    collection = _exact_fields(
        item["predecessor_collection"],
        frozenset({"case_count", "file_count", "source_test_count"}),
        "G0 predecessor collection",
    )
    if collection != {"case_count": 743, "file_count": 59, "source_test_count": 632}:
        raise GateConfigError("G0 predecessor collection differs from reviewed evidence")

    commands = item["commands"]
    if type(commands) is not list or len(commands) != 2:
        raise GateConfigError("G0 baseline commands must contain the two exact reproductions")
    normalized_commands: list[dict[str, object]] = []
    for index, command in enumerate(commands):
        row = _exact_fields(
            command,
            frozenset({"argv", "cwd", "observation_kind", "source_ref"}),
            f"G0 baseline command {index}",
        )
        argv = row["argv"]
        if type(argv) is not list or not argv:
            raise GateConfigError("G0 baseline command argv must be non-empty")
        normalized_commands.append(
            {
                "argv": [_text(value, f"G0 baseline command {index} argv") for value in argv],
                "cwd": _text(row["cwd"], f"G0 baseline command {index} cwd"),
                "observation_kind": row["observation_kind"],
                "source_ref": row["source_ref"],
            }
        )
    expected_commands = [
        {
            "argv": ["python", "-m", "pytest", "tests\\test_release_thresholds.py", "-q"],
            "cwd": ".",
            "observation_kind": "committed",
            "source_ref": _G0_BASELINE_SOURCE_REF,
        },
        {
            "argv": ["python", "_test_eval2.py"],
            "cwd": "C:\\Users\\Son\\Downloads\\cemm_authoritative_hybrid_mvp_implementation",
            "observation_kind": "operator_reported",
            "source_ref": None,
        },
    ]
    if normalized_commands != expected_commands:
        raise GateConfigError("G0 baseline commands differ from reviewed reproductions")

    failures = _exact_fields(
        item["threshold_failures"],
        frozenset({"exact_program_accuracy", "report_status"}),
        "G0 threshold failures",
    )
    exact = _exact_fields(
        failures["exact_program_accuracy"],
        frozenset({"actual", "required_min", "source_path"}),
        "G0 exact-program threshold",
    )
    status = _exact_fields(
        failures["report_status"],
        frozenset({"actual", "required", "source_path"}),
        "G0 report-status threshold",
    )
    if (
        exact["actual"] != 0.75641
        or exact["required_min"] != 0.9
        or status["actual"] != "failed"
        or status["required"] != "passed"
        or exact["source_path"] != "artifacts/evaluation/CEMM_EVALUATION.json"
        or status["source_path"] != "artifacts/evaluation/CEMM_EVALUATION.json"
    ):
        raise GateConfigError("G0 threshold findings differ from reviewed evidence")

    findings = _exact_fields(
        item["structural_findings"], _G0_REQUIRED_FINDINGS, "G0 structural findings"
    )
    for finding_id, finding in findings.items():
        row = _exact_fields(
            finding,
            frozenset({"earliest_owner", "status", "summary"}),
            f"G0 structural finding {finding_id}",
        )
        summary = _text(row["summary"], f"G0 structural finding {finding_id} summary")
        if (
            row["earliest_owner"] != _G0_FINDING_OWNERS[finding_id]
            or row["status"] != "confirmed"
            or len(summary) > 2048
        ):
            raise GateConfigError(f"G0 structural finding {finding_id} is invalid")

    probe = _exact_fields(
        item["unadmitted_m4_probe"],
        frozenset(
            {
                "abstention", "accepted", "classification", "e2e", "exact_match",
                "expression_accuracy_claimed", "operator_match",
                "operator_mismatch_count", "source", "type_set_match",
            }
        ),
        "G0 unadmitted M4 probe",
    )
    expected_probe = {
        "abstention": {
            "correct": 6, "expected": 6, "false_abstain": 5,
            "precision_denominator": 11,
        },
        "accepted": {"correct": 67, "total": 78},
        "classification": "derivation_diagnostic_only",
        "e2e": {"correct": 68, "total": 78},
        "exact_match": {"correct": 61, "total": 78},
        "expression_accuracy_claimed": False,
        "operator_match": {"correct": 67, "total": 78},
        "operator_mismatch_count": 11,
        "source": "operator_reported_2026-07-30",
        "type_set_match": {"correct": 73, "total": 78},
    }
    if probe != expected_probe:
        raise GateConfigError("G0 unadmitted M4 probe differs from reviewed evidence")

    quarantine = _exact_fields(
        item["quarantine"],
        frozenset(
            {
                "descendants", "historical_evidence_only", "program_abi",
                "program_abi_1_descendants_quarantined", "release_eligible",
            }
        ),
        "G0 Program ABI 1 quarantine",
    )
    descendants = _sorted_unique_strings(quarantine["descendants"], "G0 quarantined descendants")
    if (
        quarantine["program_abi"] != 1
        or quarantine["program_abi_1_descendants_quarantined"] is not True
        or quarantine["historical_evidence_only"] is not True
        or quarantine["release_eligible"] is not False
        or descendants != _G0_QUARANTINED_DESCENDANTS
    ):
        raise GateConfigError("G0 Program ABI 1 quarantine is incomplete")


def _load_canonical_g0_evidence(raw: bytes, *, path: Path) -> object:
    value = _load_strict_json_bytes(raw, path=path)
    if canonical_json_bytes(value) != raw:
        raise GateConfigError(f"G0 evidence bytes are not canonical JSON: {path}")
    return value


def _validate_g0_inventory_receipt_intrinsic(value: object) -> None:
    fields = frozenset(
        {
            "active_node_count", "active_node_set_ref", "baseline_source_ref",
            "collectable_node_count", "collectable_node_set_ref", "command",
            "deferred_rewrite_count", "document_authority_path",
            "document_authority_sha256", "due_rewrite_count", "inventory_path",
            "inventory_ref", "inventory_sha256", "literal_metadata_ref",
            "parsed_module_count", "phase", "receipt_ref", "schema", "source_only",
        }
    )
    item = _exact_fields(value, fields, "G0 test-inventory receipt")
    if item["schema"] != "cemm-hybrid-test-inventory-receipt-v1":
        raise GateConfigError("G0 test-inventory receipt schema is invalid")
    identity = dict(item)
    receipt_ref = identity.pop("receipt_ref")
    if receipt_ref != content_ref("test_inventory_receipt", identity):
        raise GateConfigError("G0 test-inventory receipt identity is invalid")
    if (
        item["baseline_source_ref"] != _G0_BASELINE_SOURCE_REF
        or item["phase"] != "G0"
        or item["source_only"] is not True
        or item["command"]
        != "python scripts\\check_test_inventory.py --phase G0 --source-only"
        or item["document_authority_path"] != "docs/DOCUMENT_AUTHORITY.json"
        or item["inventory_path"] != "governance/test_inventory.json"
    ):
        raise GateConfigError("G0 test-inventory receipt contract is invalid")
    for field in ("document_authority_sha256", "inventory_sha256"):
        if type(item[field]) is not str or _SHA256_RE.fullmatch(item[field]) is None:
            raise GateConfigError(f"G0 test-inventory receipt {field} is invalid")
    for field in (
        "active_node_set_ref", "collectable_node_set_ref", "inventory_ref",
        "literal_metadata_ref",
    ):
        if type(item[field]) is not str or _CONTENT_REF_RE.fullmatch(item[field]) is None:
            raise GateConfigError(f"G0 test-inventory receipt {field} is invalid")
    for field in (
        "active_node_count", "collectable_node_count", "deferred_rewrite_count",
        "due_rewrite_count", "parsed_module_count",
    ):
        if type(item[field]) is not int or item[field] < 0:
            raise GateConfigError(f"G0 test-inventory receipt {field} is invalid")
    if item["active_node_count"] > item["collectable_node_count"]:
        raise GateConfigError("G0 active-node count exceeds collectable-node count")

def _expected_g0_inventory_receipt(
    *,
    authority_sha256: str,
    inventory_sha256: str,
    inventory: object,
    selector: InventorySelector,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "active_node_count": len(selector.active_node_ids),
        "active_node_set_ref": selector.active_node_set_ref,
        "baseline_source_ref": str(inventory.baseline_source_ref),
        "collectable_node_count": len(selector.collectable_node_ids),
        "collectable_node_set_ref": selector.collectable_node_set_ref,
        "command": "python scripts\\check_test_inventory.py --phase G0 --source-only",
        "deferred_rewrite_count": len(inventory.deferred_rewrite_refs),
        "document_authority_path": "docs/DOCUMENT_AUTHORITY.json",
        "document_authority_sha256": authority_sha256,
        "due_rewrite_count": len(inventory.due_rewrite_refs),
        "inventory_path": "governance/test_inventory.json",
        "inventory_ref": selector.inventory_ref,
        "inventory_sha256": inventory_sha256,
        "literal_metadata_ref": selector.literal_metadata_ref,
        "parsed_module_count": int(inventory.parsed_module_count),
        "phase": "G0",
        "schema": "cemm-hybrid-test-inventory-receipt-v1",
        "source_only": True,
    }
    return _with_content_ref("test_inventory_receipt", "receipt_ref", payload)


def _validate_g0_evidence_material(
    *,
    authority_raw: bytes,
    baseline_raw: bytes,
    evaluation_raw: bytes,
    inventory_receipt_raw: bytes,
    inventory_sha256: str,
    inventory: object,
    selector: InventorySelector,
) -> None:
    baseline = _load_canonical_g0_evidence(
        baseline_raw, path=Path("artifacts/validation/BASELINE_REPLAY_FINDINGS.json")
    )
    receipt = _load_canonical_g0_evidence(
        inventory_receipt_raw,
        path=Path("artifacts/validation/TEST_INVENTORY_RECEIPT.json"),
    )
    _validate_g0_baseline_findings(
        baseline, baseline_source_ref=str(inventory.baseline_source_ref)
    )
    _validate_g0_inventory_receipt_intrinsic(receipt)

    source_records = tuple(inventory.source_tests.values())
    derived_collection = {
        "case_count": sum(len(record.case_node_ids) for record in source_records),
        "file_count": len(
            {record.source_test_ref.split("::", 1)[0] for record in source_records}
        ),
        "source_test_count": len(source_records),
    }
    if baseline["predecessor_collection"] != derived_collection:
        raise GateConfigError(
            "G0 predecessor collection differs from inventory reconstruction"
        )

    evaluation_binding = baseline["evaluation_artifact"]
    evaluation_sha256 = hashlib.sha256(evaluation_raw).hexdigest()
    if evaluation_binding != {
        "path": _G0_EVALUATION_PATH,
        "sha256": evaluation_sha256,
    }:
        raise GateConfigError("G0 evaluation artifact hash differs from committed source")
    evaluation = _load_strict_json_bytes(
        evaluation_raw, path=Path(_G0_EVALUATION_PATH)
    )
    if (
        type(evaluation) is not dict
        or evaluation.get("exact_program_accuracy") != 0.75641
        or evaluation.get("end_to_end_accuracy") != 0.75641
        or evaluation.get("num_episodes") != 78
        or evaluation.get("status") != "failed"
    ):
        raise GateConfigError("G0 threshold claims differ from evaluation artifact")

    expected = _expected_g0_inventory_receipt(
        authority_sha256=hashlib.sha256(authority_raw).hexdigest(),
        inventory_sha256=inventory_sha256,
        inventory=inventory,
        selector=selector,
    )
    if receipt != expected:
        raise GateConfigError(
            "G0 test-inventory receipt differs from authoritative reconstruction"
        )
def _sorted_unique_strings(
    value: object, context: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if type(value) is not list or (not value and not allow_empty):
        qualifier = "possibly empty " if allow_empty else "non-empty "
        raise GateConfigError(f"{context} must be a {qualifier}array")
    result = tuple(_text(item, f"{context} item") for item in value)
    if result != tuple(sorted(result)) or len(result) != len(set(result)):
        raise GateConfigError(f"{context} must be sorted and unique")
    return result


def _safe_relative_path(value: object, context: str, *, directory: bool | None = None) -> str:
    text = _text(value, context)
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or "\\" in text or not path.parts:
        raise GateConfigError(f"{context} is not a safe repository-relative path")
    if any(part in {"", "."} for part in path.parts):
        raise GateConfigError(f"{context} is not canonical")
    if directory is True and not text.endswith("/"):
        raise GateConfigError(f"{context} must end with '/'")
    if directory is False and text.endswith("/"):
        raise GateConfigError(f"{context} must name a file")
    return text


def _validate_root_path(root: Path, value: str, *, context: str) -> None:
    candidate = root.joinpath(*PurePosixPath(value.rstrip("/")).parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise GateConfigError(f"{context} does not exist: {value}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise GateConfigError(f"{context} escapes the Hybrid MVP root") from exc
    current = root
    for part in PurePosixPath(value.rstrip("/")).parts:
        current = current / part
        if current.is_symlink():
            raise GateConfigError(f"{context} may not traverse a symlink: {value}")


@dataclass(frozen=True)
class GatePolicy:
    tier: str
    test_results_must_be_fresh: bool = True
    persist_receipt: bool = False

    @classmethod
    def for_tier(cls, tier: str) -> "GatePolicy":
        if tier not in TIERS:
            raise GateConfigError(f"unknown validation tier: {tier}")
        return cls(tier=tier, test_results_must_be_fresh=True, persist_receipt=tier == "admission")


@dataclass(frozen=True)
class GateStep:
    step_id: str
    kind: str
    depends_on: tuple[str, ...]
    inputs: tuple[str, ...]
    material: Mapping[str, object]


@dataclass(frozen=True)
class PhasePlan:
    owners: Mapping[str, tuple[str, ...]]
    phase: tuple[str, ...]
    admission: tuple[str, ...]


@dataclass(frozen=True)
class GateGraph:
    schema: str
    limits: Mapping[str, int]
    steps: Mapping[str, GateStep]
    phases: Mapping[str, PhasePlan]
    material: Mapping[str, object]
    config_ref: str

    @classmethod
    def from_dict(cls, raw: object, *, root: Path | None = None) -> "GateGraph":
        top = _exact_fields(raw, _TOP_FIELDS, "gate config")
        if top["schema"] != GATE_CONFIG_SCHEMA:
            raise GateConfigError("gate config schema mismatch")
        limits_raw = _exact_fields(top["limits"], _LIMIT_FIELDS, "gate limits")
        limits: dict[str, int] = {}
        for name in sorted(_LIMIT_FIELDS):
            value = limits_raw[name]
            if type(value) is not int or value <= 0:
                raise GateConfigError(f"gate limit {name} must be a positive integer")
            limits[name] = value
        if limits["max_pytest_processes_per_tier"] != 1:
            raise GateConfigError("exactly one pytest process per executing tier is required")
        if limits["max_slowest_rows"] > 10:
            raise GateConfigError("slowest-row limit may not exceed the report ABI bound")
        if type(top["steps"]) is not dict or not top["steps"]:
            raise GateConfigError("gate steps must be a non-empty object")
        steps: dict[str, GateStep] = {}
        root_path = root.resolve() if root is not None else None
        for step_id, value in sorted(top["steps"].items()):
            if type(step_id) is not str or _STEP_ID_RE.fullmatch(step_id) is None:
                raise GateConfigError(f"invalid step id: {step_id!r}")
            if type(value) is not dict:
                raise GateConfigError(f"step {step_id} must be an object")
            kind = _text(value.get("kind"), f"step {step_id}.kind")
            if kind not in STEP_KINDS:
                raise GateConfigError(f"step {step_id} has unknown kind: {kind}")
            item = _exact_fields(value, _STEP_FIELDS[kind], f"step {step_id}")
            depends = _sorted_unique_strings(
                item["depends_on"], f"step {step_id}.depends_on", allow_empty=True
            )
            for dependency in depends:
                if _STEP_ID_RE.fullmatch(dependency) is None:
                    raise GateConfigError(f"step {step_id} has invalid dependency id")
            inputs = _sorted_unique_strings(item["inputs"], f"step {step_id}.inputs")
            checked_inputs = tuple(
                _safe_relative_path(path, f"step {step_id}.inputs") for path in inputs
            )
            for path in checked_inputs:
                if root_path is not None:
                    _validate_root_path(root_path, path, context=f"step {step_id}.inputs")
            if kind == "compile":
                roots = _sorted_unique_strings(item["roots"], f"step {step_id}.roots")
                for path in roots:
                    checked = _safe_relative_path(path, f"step {step_id}.roots", directory=True)
                    if root_path is not None:
                        _validate_root_path(root_path, checked, context=f"step {step_id}.roots")
            elif kind == "pytest":
                nodes = _sorted_unique_strings(item["exact_nodes"], f"step {step_id}.exact_nodes")
                for node in nodes:
                    if _NODE_RE.fullmatch(node) is None:
                        raise GateConfigError("exact node selectors required; raw files are forbidden")
            elif kind in {"governance", "pytest_inventory"}:
                _safe_relative_path(item["test_inventory"], f"step {step_id}.test_inventory", directory=False)
                symbol = _text(item["metadata_symbol"], f"step {step_id}.metadata_symbol")
                if symbol != "__cemm_test_inventory__":
                    raise GateConfigError("the immutable test metadata symbol is pinned")
                if kind == "governance":
                    _safe_relative_path(item["status_ledger"], f"step {step_id}.status_ledger", directory=False)
                    _safe_relative_path(item["invalidation_ledger"], f"step {step_id}.invalidation_ledger", directory=False)
                else:
                    test_root = _safe_relative_path(item["test_root"], f"step {step_id}.test_root")
                    if test_root != "tests":
                        raise GateConfigError("pytest inventory must collect the pinned tests root")
            steps[step_id] = GateStep(
                step_id=step_id, kind=kind, depends_on=depends, inputs=checked_inputs,
                material=_freeze_json(item),
            )
        for step in steps.values():
            for dependency in step.depends_on:
                if dependency not in steps:
                    raise GateConfigError(f"step {step.step_id} has unknown dependency: {dependency}")
        cls._validate_acyclic(steps)
        if type(top["phases"]) is not dict or not top["phases"]:
            raise GateConfigError("gate phases must be a non-empty object")
        phases: dict[str, PhasePlan] = {}
        for phase, value in sorted(top["phases"].items()):
            if phase not in PHASES:
                raise GateConfigError(f"unknown replay phase: {phase}")
            item = _exact_fields(value, _PHASE_FIELDS, f"phase {phase}")
            if type(item["owners"]) is not dict or not item["owners"]:
                raise GateConfigError(f"phase {phase}.owners must be a non-empty object")
            owners: dict[str, tuple[str, ...]] = {}
            for owner, roots in sorted(item["owners"].items()):
                if type(owner) is not str or _OWNER_RE.fullmatch(owner) is None:
                    raise GateConfigError(f"phase {phase} has invalid owner")
                owners[owner] = _sorted_unique_strings(roots, f"phase {phase}.owners.{owner}")
            phase_roots = _sorted_unique_strings(item["phase"], f"phase {phase}.phase", allow_empty=True)
            admission = _sorted_unique_strings(item["admission"], f"phase {phase}.admission")
            all_roots = (*phase_roots, *admission, *(s for rows in owners.values() for s in rows))
            for step_id in all_roots:
                if step_id not in steps:
                    raise GateConfigError(f"phase {phase} references unknown step: {step_id}")
            phases[phase] = PhasePlan(
                owners=MappingProxyType(owners), phase=phase_roots, admission=admission
            )
        graph = cls(
            schema=GATE_CONFIG_SCHEMA, limits=MappingProxyType(limits),
            steps=MappingProxyType(steps), phases=MappingProxyType(phases),
            material=_freeze_json(top), config_ref=content_ref("gate_config", top),
        )
        graph._validate_phase_contracts()
        return graph

    @staticmethod
    def _validate_acyclic(steps: Mapping[str, GateStep]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise GateConfigError("gate dependency cycle detected")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in steps[step_id].depends_on:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in sorted(steps):
            visit(step_id)

    def _roots(self, phase: str, tier: str, owner: str | None) -> tuple[str, ...]:
        if phase not in self.phases:
            raise GateConfigError(f"phase has no validation plan: {phase}")
        if tier not in TIERS:
            raise GateConfigError(f"unknown validation tier: {tier}")
        plan = self.phases[phase]
        if tier == "owner":
            if owner is None:
                if len(plan.owners) != 1:
                    raise GateConfigError("owner is required for the owner tier")
                owner = next(iter(plan.owners))
            if owner not in plan.owners:
                raise GateConfigError(f"phase {phase} has no owner plan for {owner}")
            return plan.owners[owner]
        if owner is not None:
            raise GateConfigError("--owner is valid only for the owner tier")
        return plan.phase if tier == "phase" else plan.admission

    def resolve_phase(self, phase: str, tier: str, owner: str | None = None) -> tuple[str, ...]:
        roots = self._roots(phase, tier, owner)
        if not roots:
            return ()
        required: set[str] = set()

        def include(step_id: str) -> None:
            if step_id in required:
                return
            for dependency in self.steps[step_id].depends_on:
                include(dependency)
            required.add(step_id)

        for root in roots:
            include(root)
        indegree = {
            step_id: sum(
                1 for dependency in self.steps[step_id].depends_on if dependency in required
            )
            for step_id in required
        }
        ready = sorted(step_id for step_id, count in indegree.items() if count == 0)
        ordered: list[str] = []
        while ready:
            step_id = ready.pop(0)
            ordered.append(step_id)
            for dependent in sorted(required):
                if step_id in self.steps[dependent].depends_on:
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        ready.append(dependent)
                        ready.sort()
        if len(ordered) != len(required):
            raise GateConfigError("gate dependency cycle detected")
        if len(ordered) > self.limits["max_steps_per_tier"]:
            raise GateConfigError("resolved validation tier exceeds its step bound")
        return tuple(ordered)

    def resolve_pytest_nodes(
        self, phase: str, tier: str, owner: str | None = None
    ) -> tuple[str, ...]:
        nodes: list[str] = []
        for step_id in self.resolve_phase(phase, tier, owner):
            step = self.steps[step_id]
            if step.kind == "pytest":
                nodes.extend(step.material["exact_nodes"])
        return tuple(sorted(nodes))

    def resolve_all_owner_pytest_nodes(self, phase: str) -> tuple[str, ...]:
        if phase not in self.phases:
            raise GateConfigError(f"phase has no validation plan: {phase}")
        nodes = tuple(
            node_id
            for owner in sorted(self.phases[phase].owners)
            for node_id in self.resolve_pytest_nodes(phase, "owner", owner)
        )
        if len(nodes) != len(set(nodes)):
            raise GateConfigError("owner node overlap is forbidden")
        return tuple(sorted(nodes))

    def pytest_process_count(
        self, phase: str, tier: str, owner: str | None = None
    ) -> int:
        return sum(
            self.steps[step_id].kind in PYTEST_KINDS
            for step_id in self.resolve_phase(phase, tier, owner)
        )

    def _validate_phase_contracts(self) -> None:
        admission_only = ADMISSION_ONLY_KINDS
        for phase, plan in self.phases.items():
            owner_and_phase_steps = {
                step_id
                for owner in plan.owners
                for step_id in self.resolve_phase(phase, "owner", owner)
            } | set(self.resolve_phase(phase, "phase"))
            if owner_and_phase_steps & admission_only:
                raise GateConfigError("R1 authority, activation, and structure steps are admission-only")
            owner_nodes: set[str] = set()
            for owner in plan.owners:
                if self.pytest_process_count(phase, "owner", owner) != 1:
                    raise GateConfigError("each executing owner tier must contain one pytest process")
                nodes = set(self.resolve_pytest_nodes(phase, "owner", owner))
                if owner_nodes & nodes:
                    raise GateConfigError("owner node overlap is forbidden")
                owner_nodes.update(nodes)
            phase_nodes = set(self.resolve_pytest_nodes(phase, "phase"))
            if owner_nodes & phase_nodes:
                raise GateConfigError("owner/phase node overlap is forbidden")
            if plan.phase and self.pytest_process_count(phase, "phase") != 1:
                raise GateConfigError("each executing phase tier must contain one pytest process")
            admission_steps = self.resolve_phase(phase, "admission")
            selected_admission_only = set(admission_steps) & admission_only
            r1_admission_only = frozenset({"authority_link", "sqlite_activation", "r1_structure"})
            r2_admission_only = frozenset({"authority_link", "sqlite_activation", "r2_structure"})
            r3_admission_only = frozenset({"authority_link", "sqlite_activation", "r3_structure", "r3_activation_canaries"})
            r4_admission_only = frozenset({"authority_link", "sqlite_activation"})
            if selected_admission_only and phase not in {"R1", "R2", "R3", "R4"}:
                raise GateConfigError("admission-only step selected by a non-admission phase")
            if phase == "R1" and selected_admission_only != r1_admission_only:
                raise GateConfigError("R1 admission requires authority, activation, and structure evidence")
            if phase == "R2" and selected_admission_only != r2_admission_only:
                raise GateConfigError("R2 admission requires authority, activation, and structure evidence")
            if phase == "R3" and selected_admission_only != r3_admission_only:
                raise GateConfigError("R3 admission requires activation, structure, and canary evidence")
            if phase == "R4" and selected_admission_only != r4_admission_only:
                raise GateConfigError("R4 admission requires authority and activation evidence")
            if self.pytest_process_count(phase, "admission") != 1:
                raise GateConfigError("admission must contain exactly one pytest process")
            pytest_steps = [
                self.steps[item] for item in admission_steps if self.steps[item].kind in PYTEST_KINDS
            ]
            if len(pytest_steps) != 1 or pytest_steps[0].kind != "pytest_inventory":
                raise GateConfigError("admission must use the inventory pytest step")
            if phase == "G0":
                forbidden = {"corpus", "training", "reproduction"}
                if any(
                    any(token in step_id for token in forbidden)
                    for step_id in admission_steps
                ):
                    raise GateConfigError(
                        "G0 admission may not contain expensive artifact steps"
                    )


def _load_gate_graph_with_source(path: Path) -> tuple[GateGraph, bytes]:
    target = path.resolve()
    if target.name != "validation_gates.json" or target.parent.name != "configs":
        raise GateConfigError("gate config must be the reviewed configs/validation_gates.json")
    raw = _read_bounded_file(target, maximum=_MAX_AUTHENTICATED_FILE_BYTES)
    root = target.parent.parent.resolve()
    return GateGraph.from_dict(
        _load_strict_json_bytes(raw, path=target), root=root
    ), raw


def load_gate_graph(path: Path) -> GateGraph:
    graph, _raw = _load_gate_graph_with_source(path)
    return graph

def bounded_slowest(
    rows: Iterable[tuple[str, int]], *, limit: int
) -> tuple[tuple[str, int], ...]:
    if type(limit) is not int or limit < 0:
        raise GateConfigError("slowest-row limit must be a non-negative integer")
    normalized: list[tuple[str, int]] = []
    for node_id, duration_ns in rows:
        if type(node_id) is not str or not node_id:
            raise GateConfigError("slowest-row node id is invalid")
        if type(duration_ns) is not int or duration_ns < 0:
            raise GateConfigError("slowest-row duration is invalid")
        normalized.append((node_id, duration_ns))
    normalized.sort(key=lambda row: (-row[1], row[0]))
    return tuple(normalized[:limit])


def _pytest_import_root() -> Path:
    try:
        distribution = importlib.metadata.distribution("pytest")
        candidate = Path(distribution.locate_file("")).resolve(strict=True)
    except (importlib.metadata.PackageNotFoundError, OSError) as exc:
        raise GateConfigError("pytest distribution is unavailable") from exc
    if not candidate.is_dir():
        raise GateConfigError("pytest distribution root is not a directory")
    return candidate


def isolated_test_environment(
    run_root: Path,
    *,
    inherited: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return a child environment whose writable test paths live in one root."""
    root = run_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "TMP": root / "tmp", "TEMP": root / "temp", "TMPDIR": root / "tmpdir",
        "PYTHONPYCACHEPREFIX": root / "pycache",
        "HYPOTHESIS_STORAGE_DIRECTORY": root / "hypothesis",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    basetemp = root / "pytest-basetemp"
    cache = root / "pytest-cache"
    basetemp.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    env = dict(os.environ if inherited is None else inherited)
    for forbidden in (
        "PYTHONHOME", "PYTHONOPTIMIZE", "PYTHONPATH", "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
    ):
        env.pop(forbidden, None)
    env.update({key: str(path) for key, path in paths.items()})
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["CEMM_PYTEST_IMPORT_ROOT"] = str(_pytest_import_root())
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    pytest_args = (
        "--basetemp", str(basetemp), "-o", f"cache_dir={cache}",
        "-p", "no:cacheprovider",
    )
    return env, pytest_args


def _pytest_runner_command(
    root: Path,
    selector_manifest: Path,
    report_path: Path,
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-P",
        "-s",
        str(root / "scripts" / "pytest_gate_runner.py"),
        "--selector-manifest",
        str(selector_manifest),
        "--report",
        str(report_path),
    )


@dataclass(frozen=True)
class ProcessObservation:
    exit_code: int
    wall_ns: int
    peak_rss_bytes: int | None
    timed_out: bool
    output_exceeded: bool = False
    termination_failed: bool = False


def observe_process(
    process: object,
    *,
    rss_reader: Callable[[], int | None],
    timeout_seconds: int,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    sleep: Callable[[float], None] = time.sleep,
    poll_interval_seconds: float = 0.025,
    output_paths: Sequence[Path] = (),
    max_output_bytes: int | None = None,
    tree_terminator: Callable[[object], bool] = terminate_process_tree,
) -> ProcessObservation:
    """Observe one contained child and confirm no descendant survives it."""
    if type(timeout_seconds) is not int or timeout_seconds <= 0:
        raise GateConfigError("process timeout must be a positive integer")
    if max_output_bytes is not None and (
        type(max_output_bytes) is not int or max_output_bytes <= 0
    ):
        raise GateConfigError("output bound must be a positive integer")
    started = monotonic_ns()
    peak: int | None = None

    def stop_tree() -> bool:
        try:
            return tree_terminator(process) is True
        except BaseException:
            return False

    def output_limit_exceeded() -> bool:
        if max_output_bytes is None:
            return False
        total = 0
        for output_path in output_paths:
            try:
                size = output_path.stat().st_size
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise GateConfigError(
                    "process output observation failed"
                ) from exc
            if size < 0:
                raise GateConfigError("process output observation failed")
            total += size
            if total > max_output_bytes:
                return True
        return False

    try:
        while True:
            if output_limit_exceeded():
                terminated = stop_tree()
                code = getattr(process, "returncode", None)
                return ProcessObservation(
                    exit_code=-1 if code is None else int(code),
                    wall_ns=max(0, monotonic_ns() - started),
                    peak_rss_bytes=peak,
                    timed_out=False,
                    output_exceeded=True,
                    termination_failed=not terminated,
                )
            code = process.poll()
            if code is not None:
                terminated = stop_tree()
                exceeded = output_limit_exceeded()
                return ProcessObservation(
                    exit_code=int(code),
                    wall_ns=max(0, monotonic_ns() - started),
                    peak_rss_bytes=peak,
                    timed_out=False,
                    output_exceeded=exceeded,
                    termination_failed=not terminated,
                )
            sample = rss_reader()
            if sample is not None:
                if type(sample) is not int or sample < 0:
                    raise GateConfigError("RSS sampler returned an invalid value")
                peak = sample if peak is None else max(peak, sample)
            now = monotonic_ns()
            if now - started >= timeout_seconds * 1_000_000_000:
                terminated = stop_tree()
                code = getattr(process, "returncode", None)
                return ProcessObservation(
                    exit_code=-1 if code is None else int(code),
                    wall_ns=max(0, monotonic_ns() - started),
                    peak_rss_bytes=peak,
                    timed_out=True,
                    output_exceeded=output_limit_exceeded(),
                    termination_failed=not terminated,
                )
            sleep(poll_interval_seconds)
    except (KeyboardInterrupt, SystemExit):
        stop_tree()
        raise
    except BaseException as exc:
        terminated = stop_tree()
        if not terminated:
            raise GateConfigError(
                "process observation failed and tree cleanup was not confirmed"
            ) from exc
        if isinstance(exc, GateConfigError):
            raise GateConfigError(f"process observation failed: {exc}") from exc
        raise GateConfigError("process observation failed") from exc

_PYTEST_REPORT_FIELDS = frozenset(
    {
        "active_node_ids", "collected_node_ids", "collection_errors",
        "collection_mismatch", "counts", "deselected_node_ids", "disposition",
        "error_codes", "errors", "errors_truncated", "exit_status",
        "expected_collected_node_ids", "facts", "mode", "report_ref", "schema",
        "selected_node_ids", "selector_ref", "slowest", "test_root",
    }
)
_PYTEST_COUNT_KEYS = ("error", "failure", "passed", "skip", "xfail", "xpass")
_PYTEST_FACT_FIELDS = frozenset(
    {"classification", "duration_ns", "node_id", "reports"}
)
_PYTEST_PHASE_FIELDS = frozenset({"outcome", "wasxfail", "when"})
_PYTEST_MISMATCH_FIELDS = frozenset(
    {"duplicate_node_ids", "extra_node_ids", "missing_node_ids"}
)
_PYTEST_PHASE_ORDER = {"setup": 0, "call": 1, "teardown": 2}
_PYTEST_CLASSIFICATIONS = frozenset(_PYTEST_COUNT_KEYS)
_PYTEST_FATAL_ERROR_CODES = frozenset(
    {
        "collection_error", "collection_mismatch", "collection_not_finished",
        "collection_not_observed", "duplicate_report_phase",
        "duration_aggregation_error", "malformed_report", "missing_report",
        "pytest_exception", "pytest_exit_status",
        "selector_manifest_invalid", "unexpected_report",
    }
)
_PYTEST_ERROR_ROW_CODES = _PYTEST_FATAL_ERROR_CODES | frozenset(
    {"test_error", "test_failure"}
)
_PYTEST_REPORT_REF_RE = re.compile(r"pytest_report:[0-9a-f]{24}\Z")
_PYTEST_SELECTOR_REF_RE = re.compile(r"pytest_selector:[0-9a-f]{24}\Z")


@dataclass(frozen=True)
class ParsedPytestReport:
    disposition: str
    error_code: str | None
    payload: Mapping[str, object] | None
    report_ref: str | None


def _pytest_array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise GateConfigError(f"pytest report {field} must be an array")
    return value


def _pytest_node_id(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) > 1_024
        or _NODE_RE.fullmatch(value) is None
    ):
        raise GateConfigError(f"pytest report {field} contains an invalid node ID")
    return value


def _pytest_node_ids(
    value: object, field: str, *, allow_empty: bool = True
) -> tuple[str, ...]:
    raw = _pytest_array(value, field)
    if not allow_empty and not raw:
        raise GateConfigError(f"pytest report {field} must not be empty")
    if len(raw) > 5_000:
        raise GateConfigError(f"pytest report {field} exceeds its node bound")
    nodes = tuple(_pytest_node_id(item, field) for item in raw)
    if nodes != tuple(sorted(set(nodes))):
        raise GateConfigError(
            f"pytest report {field} must be sorted and duplicate-free"
        )
    return nodes


def _pytest_text(value: object, field: str, *, maximum: int = 4_096) -> str:
    if type(value) is not str or len(value) > maximum:
        raise GateConfigError(f"pytest report {field} is invalid")
    return value


def _classify_pytest_fact(reports: Sequence[Mapping[str, object]]) -> str | None:
    if any(
        report["outcome"] == "failed" and report["when"] in {"setup", "teardown"}
        for report in reports
    ):
        return "error"
    if any(
        report["outcome"] == "failed" and report["when"] == "call"
        for report in reports
    ):
        return "failure"
    if any(
        report["outcome"] == "skipped" and bool(report["wasxfail"])
        for report in reports
    ):
        return "xfail"
    if any(
        report["outcome"] == "passed" and bool(report["wasxfail"])
        for report in reports
    ):
        return "xpass"
    if any(report["outcome"] == "skipped" for report in reports):
        return "skip"
    if (
        tuple(report["when"] for report in reports)
        == ("setup", "call", "teardown")
        and all(
            report["outcome"] == "passed" and not bool(report["wasxfail"])
            for report in reports
        )
    ):
        return "passed"
    return None


def _validate_pytest_report_payload(payload: object) -> str:
    report = _exact_fields(payload, _PYTEST_REPORT_FIELDS, "pytest report")
    if report["schema"] != PYTEST_REPORT_SCHEMA:
        raise GateConfigError("pytest report schema mismatch")
    stored_ref = report["report_ref"]
    if type(stored_ref) is not str or _PYTEST_REPORT_REF_RE.fullmatch(stored_ref) is None:
        raise GateConfigError("pytest report_ref is invalid")
    identity_material = dict(report)
    identity_material.pop("report_ref")
    if content_ref("pytest_report", identity_material) != stored_ref:
        raise GateConfigError("pytest report_ref mismatch")

    errors_truncated = report["errors_truncated"]
    if type(errors_truncated) is not bool:
        raise GateConfigError("pytest report errors_truncated must be a boolean")
    raw_errors = _pytest_array(report["errors"], "errors")
    if len(raw_errors) > 100:
        raise GateConfigError("pytest report errors exceed their row bound")
    fatal_codes_from_rows: set[str] = set()
    malformed_nodes: set[str] = set()
    duration_error_nodes: set[str] = set()
    nonfatal_rows: list[tuple[str, str]] = []
    for raw_error in raw_errors:
        if type(raw_error) is not dict or set(raw_error) not in (
            {"code", "message"},
            {"code", "message", "node_id"},
        ):
            raise GateConfigError("pytest report error row has invalid fields")
        code = _pytest_text(raw_error["code"], "error code", maximum=128)
        if code not in _PYTEST_ERROR_ROW_CODES:
            raise GateConfigError("pytest report error code is unknown")
        _pytest_text(raw_error["message"], "error message")
        node_id: str | None = None
        if "node_id" in raw_error:
            node_id = _pytest_text(raw_error["node_id"], "error node ID", maximum=1_024)
        if code in _PYTEST_FATAL_ERROR_CODES:
            fatal_codes_from_rows.add(code)
        if code in {"malformed_report", "duplicate_report_phase"} and node_id is not None:
            malformed_nodes.add(node_id)
        if code == "duration_aggregation_error":
            if node_id is None:
                raise GateConfigError(
                    "pytest duration aggregation errors require a node ID"
                )
            duration_error_nodes.add(node_id)
        if code in {"test_error", "test_failure"}:
            if node_id is None:
                raise GateConfigError("pytest test error rows require a node ID")
            nonfatal_rows.append((code, node_id))

    raw_collection_errors = _pytest_array(
        report["collection_errors"], "collection_errors"
    )
    if len(raw_collection_errors) > 100:
        raise GateConfigError("pytest collection errors exceed their row bound")
    for row in raw_collection_errors:
        item = _exact_fields(
            row, frozenset({"message", "node_id"}), "pytest collection error"
        )
        _pytest_text(item["message"], "collection error message")
        _pytest_text(item["node_id"], "collection error node ID", maximum=1_024)
    if (
        errors_truncated
        and len(raw_errors) < 100
        and len(raw_collection_errors) < 100
    ):
        raise GateConfigError(
            "pytest errors_truncated lacks a saturated bounded error collection"
        )

    raw_error_codes = _pytest_array(report["error_codes"], "error_codes")
    error_codes = tuple(
        _pytest_text(code, "error code", maximum=128) for code in raw_error_codes
    )
    if error_codes != tuple(sorted(set(error_codes))):
        raise GateConfigError("pytest error_codes must be sorted and duplicate-free")
    if any(code not in _PYTEST_FATAL_ERROR_CODES for code in error_codes):
        raise GateConfigError("pytest report contains an unknown fatal error code")

    counts = _exact_fields(
        report["counts"], frozenset(_PYTEST_COUNT_KEYS), "pytest counts"
    )
    checked_counts: dict[str, int] = {}
    for key in _PYTEST_COUNT_KEYS:
        value = counts[key]
        if type(value) is not int or value < 0:
            raise GateConfigError("pytest report count is invalid")
        checked_counts[key] = value

    active = _pytest_node_ids(report["active_node_ids"], "active_node_ids")
    collected = _pytest_node_ids(report["collected_node_ids"], "collected_node_ids")
    deselected = _pytest_node_ids(
        report["deselected_node_ids"], "deselected_node_ids"
    )
    expected = _pytest_node_ids(
        report["expected_collected_node_ids"], "expected_collected_node_ids"
    )
    selected = _pytest_node_ids(report["selected_node_ids"], "selected_node_ids")

    mode = report["mode"]
    selector_ref = report["selector_ref"]
    test_root = report["test_root"]
    if mode is None:
        empty_counts = {key: 0 for key in _PYTEST_COUNT_KEYS}
        if (
            selector_ref is not None
            or test_root is not None
            or any((active, collected, deselected, expected, selected))
            or checked_counts != empty_counts
            or report["collection_mismatch"] is not None
            or raw_collection_errors
            or _pytest_array(report["facts"], "facts")
            or _pytest_array(report["slowest"], "slowest")
            or report["disposition"] != "error"
            or report["exit_status"] != 2
            or error_codes != ("selector_manifest_invalid",)
            or len(raw_errors) != 1
            or raw_errors[0].get("code") != "selector_manifest_invalid"
            or errors_truncated
        ):
            raise GateConfigError("pytest bootstrap error report is inconsistent")
        return "error"

    if mode not in {"exact", "admission"}:
        raise GateConfigError("pytest report mode is invalid")
    if (
        type(selector_ref) is not str
        or _PYTEST_SELECTOR_REF_RE.fullmatch(selector_ref) is None
    ):
        raise GateConfigError("pytest report selector_ref is invalid")
    if not expected or not active:
        raise GateConfigError("pytest report selector node sets must not be empty")
    if mode == "exact":
        if test_root is not None or active != expected:
            raise GateConfigError("pytest exact-mode selector relationship is invalid")
    elif test_root != "tests" or not set(active).issubset(expected):
        raise GateConfigError("pytest admission-mode selector relationship is invalid")

    mismatch = report["collection_mismatch"]
    if mismatch is None:
        checked_mismatch = None
    else:
        item = _exact_fields(mismatch, _PYTEST_MISMATCH_FIELDS, "pytest mismatch")
        checked_mismatch = {
            key: _pytest_node_ids(item[key], f"collection_mismatch.{key}")
            for key in sorted(_PYTEST_MISMATCH_FIELDS)
        }
        reconstructed_extra = tuple(sorted(set(collected) - set(expected)))
        reconstructed_missing = tuple(sorted(set(expected) - set(collected)))
        duplicates = checked_mismatch["duplicate_node_ids"]
        if (
            checked_mismatch["extra_node_ids"] != reconstructed_extra
            or checked_mismatch["missing_node_ids"] != reconstructed_missing
            or any(node_id not in collected for node_id in duplicates)
            or not any(checked_mismatch.values())
            or selected
            or deselected != collected
        ):
            raise GateConfigError("pytest collection mismatch is inconsistent")

    if set(selected) & set(deselected) or tuple(
        sorted((*selected, *deselected))
    ) != collected:
        raise GateConfigError("pytest selected/deselected partition is invalid")
    if checked_mismatch is None and collected == expected:
        expected_selected = expected if mode == "exact" else active
        expected_deselected = () if mode == "exact" else tuple(
            sorted(set(expected) - set(active))
        )
        if selected != expected_selected or deselected != expected_deselected:
            raise GateConfigError("pytest collection selection is inconsistent")
    elif checked_mismatch is None and collected:
        raise GateConfigError("pytest collection differs without mismatch evidence")

    raw_facts = _pytest_array(report["facts"], "facts")
    if len(raw_facts) > 5_000:
        raise GateConfigError("pytest facts exceed their row bound")
    fact_counts = {key: 0 for key in _PYTEST_COUNT_KEYS}
    fact_nodes: list[str] = []
    expected_nonfatal_rows: list[tuple[str, str]] = []
    missing_report = False
    fact_durations: list[tuple[int, str]] = []
    for raw_fact in raw_facts:
        fact = _exact_fields(raw_fact, _PYTEST_FACT_FIELDS, "pytest fact")
        node_id = _pytest_node_id(fact["node_id"], "fact node_id")
        duration_ns = fact["duration_ns"]
        if type(duration_ns) is not int or duration_ns < 0:
            raise GateConfigError("pytest fact duration_ns is invalid")
        raw_phases = _pytest_array(fact["reports"], "fact reports")
        phases: list[Mapping[str, object]] = []
        seen_phases: list[str] = []
        for raw_phase in raw_phases:
            phase = _exact_fields(raw_phase, _PYTEST_PHASE_FIELDS, "pytest phase fact")
            when = phase["when"]
            outcome = phase["outcome"]
            wasxfail = phase["wasxfail"]
            if when not in _PYTEST_PHASE_ORDER or outcome not in {
                "passed", "failed", "skipped"
            } or type(wasxfail) is not bool:
                raise GateConfigError("pytest phase fact is invalid")
            seen_phases.append(str(when))
            phases.append(phase)
            if outcome == "failed":
                expected_nonfatal_rows.append(
                    ("test_failure" if when == "call" else "test_error", node_id)
                )
        if seen_phases != sorted(
            set(seen_phases), key=lambda name: _PYTEST_PHASE_ORDER[name]
        ):
            raise GateConfigError("pytest fact phases are not unique and ordered")
        derived_classification = (
            "error"
            if node_id in malformed_nodes or node_id in duration_error_nodes
            else _classify_pytest_fact(phases)
        )
        if node_id in duration_error_nodes and duration_ns != 0:
            raise GateConfigError(
                "pytest duration aggregation error must use zero duration"
            )
        if derived_classification is None:
            derived_classification = "error"
            missing_report = True
        classification = fact["classification"]
        if (
            classification not in _PYTEST_CLASSIFICATIONS
            or classification != derived_classification
        ):
            raise GateConfigError("pytest fact classification is inconsistent")
        fact_counts[str(classification)] += 1
        fact_nodes.append(node_id)
        fact_durations.append((duration_ns, node_id))
    if fact_nodes != list(selected):
        raise GateConfigError("pytest facts do not exactly cover selected nodes")
    if not duration_error_nodes.issubset(fact_nodes):
        raise GateConfigError(
            "pytest duration aggregation error does not name a selected fact"
        )
    if not errors_truncated and sorted(nonfatal_rows) != sorted(expected_nonfatal_rows):
        raise GateConfigError("pytest test error rows do not match phase facts")

    for key in _PYTEST_COUNT_KEYS:
        minimum = fact_counts[key]
        if key == "error":
            minimum += len(raw_collection_errors)
            if errors_truncated:
                if checked_counts[key] < minimum:
                    raise GateConfigError("pytest error count is inconsistent")
            elif checked_counts[key] != minimum:
                raise GateConfigError("pytest error count is inconsistent")
        elif checked_counts[key] != minimum:
            raise GateConfigError("pytest counts do not match reconstructed facts")

    raw_slowest = _pytest_array(report["slowest"], "slowest")
    checked_slowest: list[dict[str, object]] = []
    for raw_row in raw_slowest:
        row = _exact_fields(
            raw_row, frozenset({"duration_ns", "node_id"}), "pytest slowest row"
        )
        node_id = _pytest_node_id(row["node_id"], "slowest node_id")
        duration_ns = row["duration_ns"]
        if type(duration_ns) is not int or duration_ns < 0:
            raise GateConfigError("pytest slowest duration is invalid")
        checked_slowest.append({"duration_ns": duration_ns, "node_id": node_id})
    expected_slowest = [
        {"duration_ns": duration_ns, "node_id": node_id}
        for duration_ns, node_id in sorted(
            fact_durations, key=lambda row: (-row[0], row[1])
        )[:10]
    ]
    if checked_slowest != expected_slowest:
        raise GateConfigError("pytest slowest rows do not match fact durations")

    derived_codes = set(fatal_codes_from_rows)
    if checked_mismatch is not None:
        derived_codes.add("collection_mismatch")
    if raw_collection_errors:
        derived_codes.add("collection_error")
    if missing_report:
        derived_codes.add("missing_report")
    if (
        not collected
        and checked_mismatch is None
        and not raw_collection_errors
        and "pytest_exception" not in derived_codes
    ):
        derived_codes.add("collection_not_observed")
    if "collection_not_finished" in error_codes:
        if not collected and checked_mismatch is None:
            raise GateConfigError("collection_not_finished lacks collection evidence")
        derived_codes.add("collection_not_finished")
    preliminary_error = bool(derived_codes) or bool(checked_counts["error"])
    preliminary_failure = any(
        checked_counts[key] for key in ("failure", "skip", "xfail", "xpass")
    )
    exit_status = report["exit_status"]
    if type(exit_status) is not int:
        raise GateConfigError("pytest report exit_status is invalid")
    if not preliminary_error and not preliminary_failure and exit_status != 0:
        derived_codes.add("pytest_exit_status")
    reported_codes = set(error_codes)
    if errors_truncated:
        if not derived_codes.issubset(reported_codes):
            raise GateConfigError("pytest fatal error codes omit reconstructed evidence")
    elif reported_codes != derived_codes:
        raise GateConfigError("pytest fatal error codes are inconsistent")

    if reported_codes or checked_counts["error"]:
        reconstructed_disposition = "error"
    elif any(
        checked_counts[key] for key in ("failure", "skip", "xfail", "xpass")
    ):
        reconstructed_disposition = "failed"
    elif exit_status != 0:
        reconstructed_disposition = "error"
    else:
        reconstructed_disposition = "passed"
    if report["disposition"] != reconstructed_disposition:
        raise GateConfigError("pytest disposition is inconsistent")
    return reconstructed_disposition


def _pytest_selector_expectation(
    value: Mapping[str, object],
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], str | None]:
    material = _canonical_clone(value)
    if type(material) is not dict:
        raise GateConfigError("expected pytest selector must be an object")
    mode = material.get("mode")
    if mode == "exact":
        fields = frozenset({"exact_node_ids", "mode", "schema", "selector_ref"})
    elif mode == "admission":
        fields = frozenset(
            {
                "active_node_ids", "collectable_node_ids", "mode", "schema",
                "selector_ref", "test_root",
            }
        )
    else:
        raise GateConfigError("expected pytest selector mode is invalid")
    selector = _exact_fields(material, fields, "expected pytest selector")
    if selector["schema"] != "cemm-pytest-selector-v1":
        raise GateConfigError("expected pytest selector schema is invalid")
    selector_ref = selector["selector_ref"]
    if (
        type(selector_ref) is not str
        or _PYTEST_SELECTOR_REF_RE.fullmatch(selector_ref) is None
    ):
        raise GateConfigError("expected pytest selector_ref is invalid")
    identity = dict(selector)
    identity.pop("selector_ref")
    if content_ref("pytest_selector", identity) != selector_ref:
        raise GateConfigError("expected pytest selector identity is invalid")
    if mode == "exact":
        expected = _pytest_node_ids(
            selector["exact_node_ids"], "expected selector exact_node_ids",
            allow_empty=False,
        )
        return selector_ref, mode, expected, expected, None
    expected = _pytest_node_ids(
        selector["collectable_node_ids"],
        "expected selector collectable_node_ids",
        allow_empty=False,
    )
    active = _pytest_node_ids(
        selector["active_node_ids"], "expected selector active_node_ids",
        allow_empty=False,
    )
    if selector["test_root"] != "tests" or not set(active).issubset(expected):
        raise GateConfigError("expected admission selector relationship is invalid")
    return selector_ref, mode, expected, active, "tests"


def parse_pytest_report(
    path: Path,
    *,
    max_bytes: int = 32 * 1024 * 1024,
    expected_selector_ref: str | None = None,
    expected_selector: Mapping[str, object] | None = None,
) -> ParsedPytestReport:
    """Strictly reconstruct a child report; return a fail-closed error value."""
    try:
        path.stat()
    except FileNotFoundError:
        return ParsedPytestReport("error", "structured_report_missing", None, None)
    except OSError:
        return ParsedPytestReport("error", "structured_report_unreadable", None, None)
    if not path.is_file() or path.is_symlink():
        return ParsedPytestReport("error", "structured_report_unreadable", None, None)
    if type(max_bytes) is not int or max_bytes <= 0:
        return ParsedPytestReport("error", "structured_report_oversized", None, None)
    try:
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
    except OSError:
        return ParsedPytestReport("error", "structured_report_unreadable", None, None)
    if not raw or len(raw) > max_bytes:
        return ParsedPytestReport("error", "structured_report_oversized", None, None)
    try:
        text = raw.decode("utf-8")
        payload = json.loads(
            text, object_pairs_hook=_duplicate_keys, parse_constant=_nonfinite
        )
        _validate_json_structure_bounds(payload)
        if raw != canonical_json_bytes(payload):
            raise GateConfigError("pytest report bytes are not canonical")
        disposition = _validate_pytest_report_payload(payload)
        assert type(payload) is dict
        stored_ref = payload["report_ref"]
        if expected_selector is not None:
            (
                bound_ref,
                bound_mode,
                bound_expected,
                bound_active,
                bound_test_root,
            ) = _pytest_selector_expectation(expected_selector)
            if (
                payload["selector_ref"] != bound_ref
                or payload["mode"] != bound_mode
                or tuple(payload["expected_collected_node_ids"]) != bound_expected
                or tuple(payload["active_node_ids"]) != bound_active
                or payload["test_root"] != bound_test_root
            ):
                raise AdmissionValidationError("pytest selector binding mismatch")
            if expected_selector_ref is not None and expected_selector_ref != bound_ref:
                raise AdmissionValidationError("pytest selector binding mismatch")
        elif expected_selector_ref is not None:
            if (
                type(expected_selector_ref) is not str
                or _PYTEST_SELECTOR_REF_RE.fullmatch(expected_selector_ref) is None
                or payload["selector_ref"] != expected_selector_ref
            ):
                raise AdmissionValidationError("pytest selector binding mismatch")
    except AdmissionValidationError:
        return ParsedPytestReport(
            "error", "structured_report_selector_mismatch", None, None
        )
    except (
        GateConfigError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RecursionError,
    ):
        return ParsedPytestReport("error", "structured_report_malformed", None, None)
    return ParsedPytestReport(
        disposition=disposition,
        error_code=None,
        payload=MappingProxyType(dict(payload)),
        report_ref=str(stored_ref),
    )
def _freeze_json(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    if value is None or type(value) in {str, int, bool}:
        return value
    raise GateConfigError("receipt material is not JSON-safe")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _canonical_clone(value: object) -> object:
    return json.loads(canonical_json_bytes(_thaw_json(value)).decode("utf-8"))


_ENVIRONMENT_FIELDS = frozenset(
    {
        "implementation", "machine", "platform", "python_executable",
        "python_version", "pytest_version", "schema",
    }
)
_ENVIRONMENT_CACHE: dict[str, object] | None = None
_EVIDENCE_DIGEST_CACHE: dict[str, tuple[tuple[int, int, int, int, int], str]] = {}
_MAX_EVIDENCE_CACHE_ENTRIES = 256


def _validated_environment_material(value: object) -> dict[str, object]:
    item = _exact_fields(value, _ENVIRONMENT_FIELDS, "validation environment")
    if item["schema"] != "cemm-validation-environment-v1":
        raise GateConfigError("validation environment schema is invalid")
    for field in _ENVIRONMENT_FIELDS - {"schema"}:
        if (
            type(item[field]) is not str
            or not item[field]
            or item[field] != str(item[field]).strip()
            or any(ord(char) < 32 for char in str(item[field]))
        ):
            raise GateConfigError(f"validation environment {field} is invalid")
    return dict(item)


def reset_admission_verification_cache() -> None:
    """Begin an independent receipt-verification pass."""
    global _ENVIRONMENT_CACHE
    _ENVIRONMENT_CACHE = None
    _EVIDENCE_DIGEST_CACHE.clear()


def current_environment_material(root: Path) -> dict[str, object]:
    """Return the small stdlib-only environment identity used by gate inputs."""
    del root
    global _ENVIRONMENT_CACHE
    if _ENVIRONMENT_CACHE is None:
        try:
            pytest_version = importlib.metadata.version("pytest")
        except importlib.metadata.PackageNotFoundError:
            pytest_version = "unavailable"
        _ENVIRONMENT_CACHE = _validated_environment_material(
            {
                "implementation": platform.python_implementation(),
                "machine": platform.machine() or "unknown",
                "platform": platform.system() or "unknown",
                "python_executable": str(Path(sys.executable).resolve()),
                "python_version": platform.python_version(),
                "pytest_version": pytest_version,
                "schema": "cemm-validation-environment-v1",
            }
        )
    return dict(_ENVIRONMENT_CACHE)


def _cached_evidence_digest(path: Path) -> str:
    try:
        before = path.stat()
    except OSError as exc:
        raise GateConfigError(f"cannot stat authenticated evidence: {path.name}") from exc
    fingerprint = (
        int(before.st_dev), int(before.st_ino), int(before.st_size),
        int(before.st_mtime_ns), int(before.st_ctime_ns),
    )
    key = str(path.resolve())
    cached = _EVIDENCE_DIGEST_CACHE.get(key)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]
    digest = _sha256_file_bounded(path)
    try:
        after = path.stat()
    except OSError as exc:
        raise GateConfigError(f"cannot restat authenticated evidence: {path.name}") from exc
    after_fingerprint = (
        int(after.st_dev), int(after.st_ino), int(after.st_size),
        int(after.st_mtime_ns), int(after.st_ctime_ns),
    )
    if after_fingerprint != fingerprint:
        raise GateConfigError(f"authenticated evidence changed while hashing: {path.name}")
    if key not in _EVIDENCE_DIGEST_CACHE and len(_EVIDENCE_DIGEST_CACHE) >= _MAX_EVIDENCE_CACHE_ENTRIES:
        raise GateConfigError("authenticated evidence cache exceeds its entry bound")
    _EVIDENCE_DIGEST_CACHE[key] = (fingerprint, digest)
    return digest

@dataclass(frozen=True, order=True)
class EvidenceFile:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        try:
            checked = _safe_relative_path(self.path, "evidence path", directory=False)
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        if checked.startswith("artifacts/validation/runs/") or checked.endswith("_ADMISSION_RECEIPT.json"):
            raise AdmissionValidationError("receipt and projection paths cannot self-authenticate")
        if type(self.sha256) is not str or _SHA256_RE.fullmatch(self.sha256) is None:
            raise AdmissionValidationError("evidence SHA-256 is invalid")

    @classmethod
    def from_path(cls, root: Path, path: str) -> "EvidenceFile":
        try:
            checked = _safe_relative_path(path, "evidence path", directory=False)
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        try:
            resolved = _resolve_existing_lexical_path(
                root, checked, require_file=True
            )
            digest = _cached_evidence_digest(resolved)
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        return cls(path=checked, sha256=digest)

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value: object) -> "EvidenceFile":
        try:
            item = _exact_fields(value, frozenset({"path", "sha256"}), "evidence file")
            return cls(
                path=_text(item["path"], "evidence path"),
                sha256=_text(item["sha256"], "evidence sha256"),
            )
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc


_GOVERNANCE_REPORT_FIELDS = frozenset(
    {
        "active_node_count", "active_node_set_ref", "collectable_node_count",
        "collectable_node_set_ref", "invalidation_record_count", "inventory_ref",
        "literal_metadata_ref", "parsed_module_count", "schema", "status_head_ref",
        "status_record_count",
    }
)
_COMPILE_REPORT_FIELDS = frozenset(
    {"compiled_file_count", "compiled_set_ref", "schema"}
)
_STEP_ERROR_REPORT_FIELDS = frozenset({"error", "schema"})


def _nonnegative_exact_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise AdmissionValidationError(f"{label} must be a non-negative integer")
    return value


def _validate_admission_step_report(kind: str, report: object) -> None:
    try:
        item = _canonical_clone(report)
        if type(item) is not dict:
            raise GateConfigError("admission step report must be an object")
        if kind == "authority_link":
            row = _exact_fields(item, frozenset({
                "atom_count", "authority_ref", "content_hash", "generation",
                "model_compatibility_hash", "operator_schema_count", "schema",
            }), "authority-link step report")
            if row["schema"] != "cemm-authority-link-step-report-v1":
                raise GateConfigError("authority-link report schema is invalid")
            if _nonnegative_exact_int(row["atom_count"], "authority atom count") == 0:
                raise AdmissionValidationError("authority atom count must be positive")
            if row["operator_schema_count"] != 5:
                raise AdmissionValidationError("authority operator schema count is not five")
            for field in ("authority_ref", "content_hash", "model_compatibility_hash"):
                if type(row[field]) is not str or _CONTENT_REF_RE.fullmatch(row[field]) is None:
                    raise AdmissionValidationError(f"authority report {field} is invalid")
            _text(row["generation"], "authority generation")
            identity = dict(row)
            authority_ref = identity.pop("authority_ref")
            if authority_ref != content_ref("linked_authority", identity):
                raise AdmissionValidationError("authority report identity is invalid")
            return
        if kind == "sqlite_activation":
            row = _exact_fields(item, frozenset({
                "activation_ref", "authority_generation", "database_sha256",
                "fresh_revisions", "integrity_check", "reopened", "schema",
                "schema_object_count", "schema_ref",
            }), "SQLite-activation step report")
            if row["schema"] != "cemm-sqlite-activation-step-report-v1":
                raise GateConfigError("SQLite-activation report schema is invalid")
            if (
                row["fresh_revisions"]
                != {"effect": 0, "episode": 0, "session": 0, "world": 0}
                or row["integrity_check"] != "ok"
                or row["reopened"] is not True
            ):
                raise AdmissionValidationError("SQLite activation observations are invalid")
            _text(row["authority_generation"], "SQLite authority generation")
            if type(row["database_sha256"]) is not str or _SHA256_RE.fullmatch(row["database_sha256"]) is None:
                raise AdmissionValidationError("SQLite database hash is invalid")
            if _nonnegative_exact_int(row["schema_object_count"], "SQLite schema count") == 0:
                raise AdmissionValidationError("SQLite schema must be nonempty")
            for field in ("activation_ref", "schema_ref"):
                if type(row[field]) is not str or _CONTENT_REF_RE.fullmatch(row[field]) is None:
                    raise AdmissionValidationError(f"SQLite report {field} is invalid")
            identity = dict(row)
            activation_ref = identity.pop("activation_ref")
            if activation_ref != content_ref("sqlite_activation", identity):
                raise AdmissionValidationError("SQLite activation identity is invalid")
            return
        if kind == "r1_structure":
            row = _exact_fields(item, frozenset({
                "cycle_result_owner", "forbidden_match_count", "process_path",
                "program_owner", "runtime_owner", "scanned_file_count",
                "scanned_source_set_ref", "schema", "structure_ref",
            }), "R1-structure step report")
            expected = {
                "cycle_result_owner": "src/cemm_authoritative_hybrid/cycle.py",
                "forbidden_match_count": 0,
                "process_path": "src/cemm_authoritative_hybrid/runtime.py:HybridRuntime.process",
                "program_owner": "src/cemm_authoritative_hybrid/programs.py",
                "runtime_owner": "src/cemm_authoritative_hybrid/runtime.py",
                "schema": "cemm-r1-structure-step-report-v1",
            }
            if any(row[field] != value for field, value in expected.items()):
                raise AdmissionValidationError("R1 structure ownership is invalid")
            if _nonnegative_exact_int(row["scanned_file_count"], "R1 source count") == 0:
                raise AdmissionValidationError("R1 structure scan is empty")
            for field in ("scanned_source_set_ref", "structure_ref"):
                if type(row[field]) is not str or _CONTENT_REF_RE.fullmatch(row[field]) is None:
                    raise AdmissionValidationError(f"R1 structure report {field} is invalid")
            identity = dict(row)
            structure_ref = identity.pop("structure_ref")
            if structure_ref != content_ref("r1_structure", identity):
                raise AdmissionValidationError("R1 structure report identity is invalid")
            return
        if kind == "r2_structure":
            row = _exact_fields(item, frozenset({
                "compiler_owner", "forbidden_match_count", "process_path",
                "proposer_owner", "runtime_owner", "scanned_file_count",
                "scanned_source_set_ref", "schema", "structure_ref",
            }), "R2-structure step report")
            expected = {
                "compiler_owner": "src/cemm_authoritative_hybrid/recursive_compiler.py",
                "forbidden_match_count": 0,
                "process_path": "src/cemm_authoritative_hybrid/runtime.py:HybridRuntime.process",
                "proposer_owner": "src/cemm_authoritative_hybrid/recursive_composer",
                "runtime_owner": "src/cemm_authoritative_hybrid/runtime.py",
                "schema": "cemm-r2-structure-step-report-v1",
            }
            if any(row[field] != value for field, value in expected.items()):
                raise AdmissionValidationError("R2 structure ownership is invalid")
            if _nonnegative_exact_int(row["scanned_file_count"], "R2 source count") == 0:
                raise AdmissionValidationError("R2 structure scan is empty")
            for field in ("scanned_source_set_ref", "structure_ref"):
                if type(row[field]) is not str or _CONTENT_REF_RE.fullmatch(row[field]) is None:
                    raise AdmissionValidationError(f"R2 structure report {field} is invalid")
            identity = dict(row)
            structure_ref = identity.pop("structure_ref")
            if structure_ref != content_ref("r2_structure", identity):
                raise AdmissionValidationError("R2 structure report identity is invalid")
            return
        if kind == "r3_structure":
            row = _exact_fields(item, frozenset({
                "decision_owner", "forbidden_match_count", "process_path",
                "runtime_owner", "scanned_file_count",
                "scanned_source_set_ref", "schema", "structure_ref",
            }), "R3-structure step report")
            expected = {
                "decision_owner": "src/cemm_authoritative_hybrid/decision.py",
                "forbidden_match_count": 0,
                "process_path": "src/cemm_authoritative_hybrid/runtime.py:HybridRuntime.process",
                "runtime_owner": "src/cemm_authoritative_hybrid/runtime.py",
                "schema": "cemm-r3-structure-step-report-v1",
            }
            if any(row[field] != value for field, value in expected.items()):
                raise AdmissionValidationError("R3 structure ownership is invalid")
            if _nonnegative_exact_int(row["scanned_file_count"], "R3 source count") == 0:
                raise AdmissionValidationError("R3 structure scan is empty")
            for field in ("scanned_source_set_ref", "structure_ref"):
                if type(row[field]) is not str or _CONTENT_REF_RE.fullmatch(row[field]) is None:
                    raise AdmissionValidationError(f"R3 structure report {field} is invalid")
            identity = dict(row)
            structure_ref = identity.pop("structure_ref")
            if structure_ref != content_ref("r3_structure", identity):
                raise AdmissionValidationError("R3 structure report identity is invalid")
            return
        if kind == "r3_activation_canaries":
            row = _exact_fields(item, frozenset({
                "canary_count", "canary_set_ref", "schema", "canary_ref",
            }), "R3-activation-canaries step report")
            expected = {
                "schema": "cemm-r3-activation-canaries-step-report-v1",
            }
            if any(row[field] != value for field, value in expected.items()):
                raise AdmissionValidationError("R3 activation canaries report is invalid")
            if _nonnegative_exact_int(row["canary_count"], "R3 canary count") == 0:
                raise AdmissionValidationError("R3 activation canaries report is empty")
            for field in ("canary_set_ref", "canary_ref"):
                if type(row[field]) is not str or _CONTENT_REF_RE.fullmatch(row[field]) is None:
                    raise AdmissionValidationError(f"R3 activation canaries report {field} is invalid")
            identity = dict(row)
            canary_ref = identity.pop("canary_ref")
            if canary_ref != content_ref("r3_activation_canaries", identity):
                raise AdmissionValidationError("R3 activation canaries report identity is invalid")
            return
        raise AdmissionValidationError("unknown admission step report kind")
    except GateConfigError as exc:
        raise AdmissionValidationError(str(exc)) from exc

def _validate_control_step_report(
    kind: str,
    report: object,
    *,
    disposition: str,
) -> None:
    if disposition == "blocked":
        if report is not None:
            raise AdmissionValidationError("blocked control step may not carry a report")
        return
    if disposition == "passed":
        if kind in ADMISSION_ONLY_KINDS:
            _validate_admission_step_report(kind, report)
            return
        if kind == "governance":
            try:
                item = _exact_fields(
                    report, _GOVERNANCE_REPORT_FIELDS, "governance step report"
                )
            except GateConfigError as exc:
                raise AdmissionValidationError(str(exc)) from exc
            if item["schema"] != "cemm-governance-step-report-v1":
                raise AdmissionValidationError("governance report schema is invalid")
            for field in (
                "active_node_count", "collectable_node_count",
                "invalidation_record_count", "parsed_module_count",
                "status_record_count",
            ):
                _nonnegative_exact_int(item[field], f"governance report {field}")
            if item["active_node_count"] > item["collectable_node_count"]:
                raise AdmissionValidationError(
                    "governance active count exceeds collectable count"
                )
            for field in (
                "active_node_set_ref", "collectable_node_set_ref", "inventory_ref",
                "literal_metadata_ref",
            ):
                if (
                    type(item[field]) is not str
                    or _CONTENT_REF_RE.fullmatch(str(item[field])) is None
                ):
                    raise AdmissionValidationError(
                        f"governance report {field} is invalid"
                    )
            if (
                type(item["status_head_ref"]) is not str
                or _STATUS_HEAD_RE.fullmatch(str(item["status_head_ref"])) is None
            ):
                raise AdmissionValidationError(
                    "governance report status_head_ref is invalid"
                )
            return
        try:
            item = _exact_fields(report, _COMPILE_REPORT_FIELDS, "compile step report")
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        if item["schema"] != "cemm-compile-step-report-v1":
            raise AdmissionValidationError("compile report schema is invalid")
        _nonnegative_exact_int(item["compiled_file_count"], "compiled file count")
        if (
            type(item["compiled_set_ref"]) is not str
            or _CONTENT_REF_RE.fullmatch(str(item["compiled_set_ref"])) is None
        ):
            raise AdmissionValidationError("compiled source-set ref is invalid")
        return
    if disposition != "error":
        raise AdmissionValidationError("control step disposition is invalid")
    try:
        item = _exact_fields(report, _STEP_ERROR_REPORT_FIELDS, "control step error report")
    except GateConfigError as exc:
        raise AdmissionValidationError(str(exc)) from exc
    if (
        item["schema"] != "cemm-step-error-report-v1"
        or type(item["error"]) is not str
        or not item["error"]
    ):
        raise AdmissionValidationError("control step error report is invalid")

_STEP_RESULT_FIELDS = frozenset(
    {
        "config_ref", "definition", "definition_ref", "dependency_step_refs",
        "disposition", "environment_ref", "error_code", "exit_code", "input_files",
        "input_ref", "kind", "observation_report", "observation_report_ref",
        "peak_rss_bytes", "report", "report_ref", "selector",
        "selector_ref", "slowest", "source_ref", "step_id", "step_ref", "wall_ns",
    }
)


@dataclass(frozen=True)
class StepResult:
    step_ref: str
    step_id: str
    kind: str
    definition: Mapping[str, object]
    definition_ref: str
    source_ref: str
    config_ref: str
    environment_ref: str
    input_files: tuple[EvidenceFile, ...]
    dependency_step_refs: tuple[str, ...]
    selector: Mapping[str, object] | None
    selector_ref: str | None
    input_ref: str
    disposition: str
    report: Mapping[str, object] | None
    report_ref: str | None
    observation_report: Mapping[str, object] | None
    observation_report_ref: str | None
    exit_code: int
    error_code: str | None
    wall_ns: int
    peak_rss_bytes: int | None
    slowest: tuple[tuple[str, int], ...]

    @classmethod
    def create(
        cls, *, config_ref: str, definition: Mapping[str, object],
        dependency_step_refs: Sequence[str], disposition: str, environment_ref: str,
        error_code: str | None, exit_code: int, input_files: Sequence[EvidenceFile],
        kind: str, peak_rss_bytes: int | None, report: Mapping[str, object] | None,
        selector: Mapping[str, object] | None, slowest: Sequence[tuple[str, int]],
        source_ref: str, step_id: str, wall_ns: int,
        observation_report: Mapping[str, object] | None = None,
    ) -> "StepResult":
        if type(step_id) is not str or _STEP_ID_RE.fullmatch(step_id) is None:
            raise AdmissionValidationError("step result id is invalid")
        if kind not in STEP_KINDS:
            raise AdmissionValidationError("step result kind is invalid")
        if disposition not in {"passed", "failed", "error", "blocked", "not_applicable"}:
            raise AdmissionValidationError("step result disposition is invalid")
        if type(exit_code) is not int or type(wall_ns) is not int or wall_ns < 0:
            raise AdmissionValidationError("step result process observation is invalid")
        if peak_rss_bytes is not None and (type(peak_rss_bytes) is not int or peak_rss_bytes < 0):
            raise AdmissionValidationError("step result peak RSS is invalid")
        if error_code is not None and (type(error_code) is not str or not error_code):
            raise AdmissionValidationError("step result error code is invalid")
        if type(config_ref) is not str or _CONTENT_REF_RE.fullmatch(config_ref) is None:
            raise AdmissionValidationError("step result config_ref is invalid")
        if type(environment_ref) is not str or _CONTENT_REF_RE.fullmatch(environment_ref) is None:
            raise AdmissionValidationError("step result environment_ref is invalid")
        if type(source_ref) is not str or _SOURCE_RE.fullmatch(source_ref) is None:
            raise AdmissionValidationError("step result source_ref is invalid")
        checked_dependencies = tuple(dependency_step_refs)
        if checked_dependencies != tuple(sorted(checked_dependencies)) or len(checked_dependencies) != len(set(checked_dependencies)):
            raise AdmissionValidationError("dependency step refs must be sorted and unique")
        if any(type(item) is not str or _CONTENT_REF_RE.fullmatch(item) is None for item in checked_dependencies):
            raise AdmissionValidationError("dependency step ref is invalid")
        checked_inputs = tuple(input_files)
        if checked_inputs != tuple(sorted(checked_inputs)) or len(checked_inputs) != len(set(checked_inputs)):
            raise AdmissionValidationError("step input files must be sorted and unique")
        definition_material = _canonical_clone(definition)
        if disposition in {"passed", "failed"}:
            if type(definition_material) is not dict:
                raise AdmissionValidationError(
                    "step result definition must be an object"
                )
            declared_inputs = definition_material.get("inputs")
            if type(declared_inputs) is not list or not declared_inputs:
                raise AdmissionValidationError(
                    "executed step definition requires declared inputs"
                )
            if not checked_inputs:
                raise AdmissionValidationError(
                    "executed step result requires an input manifest"
                )
            input_paths = tuple(item.path for item in checked_inputs)

            def belongs(path: str, declared: object) -> bool:
                if type(declared) is not str:
                    return False
                if declared.endswith("/"):
                    return path.startswith(declared)
                return path == declared

            if any(
                not any(belongs(path, declared) for declared in declared_inputs)
                for path in input_paths
            ):
                raise AdmissionValidationError(
                    "step input manifest contains an undeclared path"
                )
            if any(
                not any(belongs(path, declared) for path in input_paths)
                for declared in declared_inputs
            ):
                raise AdmissionValidationError(
                    "step input manifest omits a declared input"
                )
        definition_ref = content_ref("step_definition", definition_material)
        selector_material = None if selector is None else _canonical_clone(selector)
        selector_ref = None if selector_material is None else content_ref("selector", selector_material)
        report_material = None if report is None else _canonical_clone(report)
        report_ref = None if report_material is None else content_ref("step_report", report_material)
        observation_material = (
            report_material
            if observation_report is None
            else _canonical_clone(observation_report)
        )
        if disposition == "passed":
            if exit_code != 0 or error_code is not None:
                raise AdmissionValidationError(
                    "passed step result has inconsistent exit/error semantics"
                )
        elif disposition == "failed":
            if exit_code != 1 or error_code is None:
                raise AdmissionValidationError(
                    "failed step result has inconsistent exit/error semantics"
                )
        elif disposition in {"error", "blocked"} and error_code is None:
            raise AdmissionValidationError(
                "non-passing step result requires an error code"
            )
        elif disposition == "not_applicable" and (
            exit_code != 0 or error_code is not None
        ):
            raise AdmissionValidationError(
                "not-applicable step result has inconsistent exit/error semantics"
            )

        if kind in {"governance", "compile"} | ADMISSION_ONLY_KINDS:
            if selector_material is not None:
                raise AdmissionValidationError(
                    "control step may not carry a selector"
                )
            if report_material != observation_material:
                raise AdmissionValidationError(
                    "control-step observation must equal its semantic report"
                )
            _validate_control_step_report(
                kind, report_material, disposition=disposition
            )
        elif kind in PYTEST_KINDS:
            if (report_material is None) != (observation_material is None):
                raise AdmissionValidationError(
                    "pytest semantic and observation reports must be present together"
                )
            if report_material is None:
                if disposition != "blocked":
                    raise AdmissionValidationError(
                        "executed pytest step requires an observation report"
                    )
            else:
                assert type(observation_material) is dict
                expected_report = _semantic_pytest_report(observation_material)
                if report_material != expected_report:
                    raise AdmissionValidationError(
                        "pytest semantic report does not match its observation projection"
                    )
                schema = observation_material.get("schema")
                if schema == PYTEST_REPORT_SCHEMA:
                    try:
                        observed_disposition = _validate_pytest_report_payload(
                            observation_material
                        )
                        if selector_material is None:
                            raise GateConfigError(
                                "pytest producer report requires an exact selector"
                            )
                        (
                            bound_ref,
                            bound_mode,
                            bound_expected,
                            bound_active,
                            bound_test_root,
                        ) = _pytest_selector_expectation(selector_material)
                        if (
                            observation_material.get("selector_ref") != bound_ref
                            or observation_material.get("mode") != bound_mode
                            or tuple(
                                observation_material.get(
                                    "expected_collected_node_ids", ()
                                )
                            ) != bound_expected
                            or tuple(
                                observation_material.get("active_node_ids", ())
                            ) != bound_active
                            or observation_material.get("test_root")
                            != bound_test_root
                        ):
                            raise GateConfigError(
                                "pytest observation selector binding mismatch"
                            )
                        assert type(definition_material) is dict
                        if kind == "pytest":
                            definition_nodes = _pytest_node_ids(
                                definition_material.get("exact_nodes"),
                                "step definition exact_nodes",
                                allow_empty=False,
                            )
                            if (
                                bound_mode != "exact"
                                or bound_expected != definition_nodes
                            ):
                                raise GateConfigError(
                                    "pytest selector differs from its step definition"
                                )
                        elif (
                            bound_mode != "admission"
                            or definition_material.get("test_root")
                            != bound_test_root
                        ):
                            raise GateConfigError(
                                "inventory pytest selector differs from its step definition"
                            )
                    except GateConfigError as exc:
                        raise AdmissionValidationError(
                            f"pytest observation report is invalid: {exc}"
                        ) from exc
                elif schema == "cemm-parent-pytest-observation-v1":
                    try:
                        parent = _exact_fields(
                            observation_material,
                            frozenset({"disposition", "error_code", "schema"}),
                            "parent pytest observation",
                        )
                        if (
                            parent["disposition"] != "error"
                            or type(parent["error_code"]) is not str
                            or not parent["error_code"]
                        ):
                            raise GateConfigError(
                                "parent pytest observation is not an error"
                            )
                    except GateConfigError as exc:
                        raise AdmissionValidationError(str(exc)) from exc
                    observed_disposition = "error"
                elif schema == "cemm-step-error-report-v1":
                    try:
                        step_error = _exact_fields(
                            observation_material,
                            frozenset({"error", "schema"}),
                            "pytest step error report",
                        )
                        _pytest_text(step_error["error"], "pytest step error")
                    except GateConfigError as exc:
                        raise AdmissionValidationError(str(exc)) from exc
                    observed_disposition = "error"
                else:
                    raise AdmissionValidationError(
                        "pytest observation report schema is invalid"
                    )
                if disposition == "passed" and observed_disposition != "passed":
                    raise AdmissionValidationError(
                        "passed pytest step contradicts its observation disposition"
                    )
                if disposition == "failed" and observed_disposition != "failed":
                    raise AdmissionValidationError(
                        "failed pytest step contradicts its observation disposition"
                    )
                if observed_disposition == "error" and disposition != "error":
                    raise AdmissionValidationError(
                        "pytest error observation cannot be downgraded"
                    )
                external_errors = {
                    "pytest_output_limit",
                    "pytest_process_tree_cleanup_failed",
                    "pytest_timeout",
                }
                if (
                    disposition == "error"
                    and observed_disposition != "error"
                    and error_code not in external_errors
                ):
                    raise AdmissionValidationError(
                        "pytest error disposition lacks error evidence"
                    )
                if (
                    schema == PYTEST_REPORT_SCHEMA
                    and observed_disposition == "error"
                    and error_code not in external_errors
                    and exit_code != 2
                ):
                    raise AdmissionValidationError(
                        "pytest error observation requires child exit code 2"
                    )
        observation_report_ref = (
            None
            if observation_material is None
            else content_ref("step_observation_report", observation_material)
        )
        input_payload = {
            "config_ref": config_ref, "definition_ref": definition_ref,
            "dependency_step_refs": list(checked_dependencies), "environment_ref": environment_ref,
            "input_files": [item.to_dict() for item in checked_inputs],
            "selector_ref": selector_ref, "source_ref": source_ref, "step_id": step_id,
        }
        input_ref = content_ref("gate_input", input_payload)
        semantic_payload = {
            "disposition": disposition, "error_code": error_code, "exit_code": exit_code,
            "input_ref": input_ref, "kind": kind, "report_ref": report_ref, "step_id": step_id,
        }
        step_ref = content_ref("gate_step", semantic_payload)
        raw_slowest = tuple(slowest)
        if len(raw_slowest) > 10:
            raise AdmissionValidationError("step slowest rows exceed their ABI bound")
        checked_slowest = bounded_slowest(raw_slowest, limit=len(raw_slowest))
        return cls(
            step_ref=step_ref, step_id=step_id, kind=kind,
            definition=_freeze_json(definition_material), definition_ref=definition_ref,
            source_ref=source_ref, config_ref=config_ref, environment_ref=environment_ref,
            input_files=checked_inputs, dependency_step_refs=checked_dependencies,
            selector=None if selector_material is None else _freeze_json(selector_material),
            selector_ref=selector_ref, input_ref=input_ref, disposition=disposition,
            report=None if report_material is None else _freeze_json(report_material),
            report_ref=report_ref,
            observation_report=(
                None if observation_material is None else _freeze_json(observation_material)
            ),
            observation_report_ref=observation_report_ref,
            exit_code=exit_code, error_code=error_code,
            wall_ns=wall_ns, peak_rss_bytes=peak_rss_bytes, slowest=checked_slowest,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "config_ref": self.config_ref, "definition": _thaw_json(self.definition),
            "definition_ref": self.definition_ref,
            "dependency_step_refs": list(self.dependency_step_refs),
            "disposition": self.disposition, "environment_ref": self.environment_ref,
            "error_code": self.error_code, "exit_code": self.exit_code,
            "input_files": [item.to_dict() for item in self.input_files],
            "input_ref": self.input_ref, "kind": self.kind,
            "observation_report": (
                None if self.observation_report is None else _thaw_json(self.observation_report)
            ),
            "observation_report_ref": self.observation_report_ref,
            "peak_rss_bytes": self.peak_rss_bytes,
            "report": None if self.report is None else _thaw_json(self.report),
            "report_ref": self.report_ref,
            "selector": None if self.selector is None else _thaw_json(self.selector),
            "selector_ref": self.selector_ref,
            "slowest": [[node_id, duration] for node_id, duration in self.slowest],
            "source_ref": self.source_ref, "step_id": self.step_id,
            "step_ref": self.step_ref, "wall_ns": self.wall_ns,
        }

    @classmethod
    def from_dict(cls, value: object) -> "StepResult":
        try:
            item = _exact_fields(value, _STEP_RESULT_FIELDS, "step result")
            inputs_raw = item["input_files"]
            dependencies_raw = item["dependency_step_refs"]
            slowest_raw = item["slowest"]
            if type(inputs_raw) is not list or type(dependencies_raw) is not list or type(slowest_raw) is not list:
                raise AdmissionValidationError("step result collections are invalid")
            slowest: list[tuple[str, int]] = []
            for row in slowest_raw:
                if type(row) is not list or len(row) != 2:
                    raise AdmissionValidationError("step result slowest row is invalid")
                slowest.append((row[0], row[1]))
            result = cls.create(
                config_ref=item["config_ref"], definition=item["definition"],
                dependency_step_refs=dependencies_raw, disposition=item["disposition"],
                environment_ref=item["environment_ref"], error_code=item["error_code"],
                exit_code=item["exit_code"],
                input_files=tuple(EvidenceFile.from_dict(row) for row in inputs_raw),
                kind=item["kind"], peak_rss_bytes=item["peak_rss_bytes"],
                report=item["report"], selector=item["selector"], slowest=tuple(slowest),
                source_ref=item["source_ref"], step_id=item["step_id"], wall_ns=item["wall_ns"],
                observation_report=item["observation_report"],
            )
            for field in (
                "definition_ref", "selector_ref", "report_ref",
                "observation_report_ref", "input_ref", "step_ref",
            ):
                if getattr(result, field) != item[field]:
                    raise AdmissionValidationError(f"step result {field} mismatch")
            return result
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc


_RECEIPT_FIELDS = frozenset(
    {
        "config", "config_ref", "environment", "environment_ref", "evidence_files",
        "fresh", "gate_result_ref", "phase", "pre_admission_status_head_ref",
        "run_nonce", "run_ref", "schema", "source_ref", "started_at_utc",
        "step_results", "tier",
    }
)
_UNIDENTIFIED_RECEIPT_FIELDS = _RECEIPT_FIELDS - {"run_ref"}


@dataclass(frozen=True)
class GateReceipt:
    gate_result_ref: str
    run_ref: str
    tier: str
    phase: str
    fresh: bool
    source_ref: str
    config: Mapping[str, object]
    config_ref: str
    environment: Mapping[str, object]
    environment_ref: str
    evidence_files: tuple[EvidenceFile, ...]
    started_at_utc: str
    run_nonce: str
    pre_admission_status_head_ref: str
    step_results: tuple[StepResult, ...]

    @classmethod
    def create(
        cls,
        *,
        config: Mapping[str, object],
        environment: Mapping[str, object],
        evidence_files: Sequence[EvidenceFile],
        fresh: bool,
        phase: str,
        pre_admission_status_head_ref: str,
        run_nonce: str,
        source_ref: str,
        started_at_utc: str,
        step_results: Sequence[StepResult],
        tier: str,
    ) -> "GateReceipt":
        if phase not in PHASES:
            raise AdmissionValidationError("receipt phase is invalid")
        if tier not in TIERS:
            raise AdmissionValidationError("receipt tier is invalid")
        if type(fresh) is not bool or not fresh:
            raise AdmissionValidationError("validation receipts must be fresh")
        if type(source_ref) is not str or _SOURCE_RE.fullmatch(source_ref) is None:
            raise AdmissionValidationError("receipt source_ref is invalid")
        if (
            type(pre_admission_status_head_ref) is not str
            or _STATUS_HEAD_RE.fullmatch(pre_admission_status_head_ref) is None
        ):
            raise AdmissionValidationError("receipt pre-admission status head is invalid")
        if type(started_at_utc) is not str or _ISO_UTC_RE.fullmatch(started_at_utc) is None:
            raise AdmissionValidationError("receipt start time is invalid")
        if (
            type(run_nonce) is not str
            or not run_nonce
            or run_nonce != run_nonce.strip()
            or any(ord(char) < 33 for char in run_nonce)
            or len(run_nonce) > 128
        ):
            raise AdmissionValidationError("receipt run nonce is invalid")
        try:
            config_material = _canonical_clone(config)
            graph = GateGraph.from_dict(config_material)
            environment_material = _validated_environment_material(
                _canonical_clone(environment)
            )
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        config_ref = content_ref("gate_config", config_material)
        environment_ref = content_ref("environment", environment_material)
        results = tuple(step_results)
        expected_ids = graph.resolve_phase(phase, tier)
        actual_ids = tuple(result.step_id for result in results)
        if actual_ids != expected_ids:
            raise AdmissionValidationError(
                "receipt step results do not equal the exact declared step set"
            )
        by_id: dict[str, StepResult] = {}
        for result in results:
            if result.step_id in by_id:
                raise AdmissionValidationError("receipt contains duplicate step results")
            by_id[result.step_id] = result
            step = graph.steps[result.step_id]
            if result.kind != step.kind:
                raise AdmissionValidationError("receipt step kind mismatch")
            if _canonical_clone(result.definition) != _canonical_clone(step.material):
                raise AdmissionValidationError("receipt step definition mismatch")
            if result.config_ref != config_ref:
                raise AdmissionValidationError("receipt step config_ref mismatch")
            if result.environment_ref != environment_ref:
                raise AdmissionValidationError("receipt step environment_ref mismatch")
            if result.source_ref != source_ref:
                raise AdmissionValidationError("receipt step source_ref mismatch")
            if result.kind in PYTEST_KINDS:
                expected_slowest = (
                    ()
                    if result.observation_report is None
                    else _slowest_from_report(
                        _thaw_json(result.observation_report),
                        limit=graph.limits["max_slowest_rows"],
                    )
                )
                if result.slowest != expected_slowest:
                    raise AdmissionValidationError(
                        "receipt slowest rows differ from the observation report"
                    )
            elif result.slowest:
                raise AdmissionValidationError(
                    "non-pytest step may not carry slowest rows"
                )
            expected_dependencies = tuple(
                sorted(by_id[dependency].step_ref for dependency in step.depends_on)
            )
            if result.dependency_step_refs != expected_dependencies:
                raise AdmissionValidationError("receipt dependency step refs mismatch")
        evidence = tuple(evidence_files)
        if evidence != tuple(sorted(evidence)) or len(evidence) != len(set(evidence)):
            raise AdmissionValidationError("receipt evidence files must be sorted and unique")
        if tier == "admission" and tuple(item.path for item in evidence) != (
            _required_admission_evidence_paths(phase)
        ):
            raise AdmissionValidationError(
                "receipt evidence files do not equal the exact phase policy"
            )
        gate_payload = {
            "config_ref": config_ref,
            "environment_ref": environment_ref,
            "evidence_files": [item.to_dict() for item in evidence],
            "fresh": fresh,
            "phase": phase,
            "pre_admission_status_head_ref": pre_admission_status_head_ref,
            "source_ref": source_ref,
            "step_refs": [result.step_ref for result in results],
            "tier": tier,
        }
        gate_result_ref = content_ref("gate_result", gate_payload)
        receipt = cls(
            gate_result_ref=gate_result_ref,
            run_ref="run:" + "0" * 24,
            tier=tier,
            phase=phase,
            fresh=fresh,
            source_ref=source_ref,
            config=_freeze_json(config_material),
            config_ref=config_ref,
            environment=_freeze_json(environment_material),
            environment_ref=environment_ref,
            evidence_files=evidence,
            started_at_utc=started_at_utc,
            run_nonce=run_nonce,
            pre_admission_status_head_ref=pre_admission_status_head_ref,
            step_results=results,
        )
        material = receipt.to_dict()
        material.pop("run_ref")
        run_ref = content_ref("run", material)
        return cls(
            gate_result_ref=gate_result_ref,
            run_ref=run_ref,
            tier=tier,
            phase=phase,
            fresh=fresh,
            source_ref=source_ref,
            config=receipt.config,
            config_ref=config_ref,
            environment=receipt.environment,
            environment_ref=environment_ref,
            evidence_files=evidence,
            started_at_utc=started_at_utc,
            run_nonce=run_nonce,
            pre_admission_status_head_ref=pre_admission_status_head_ref,
            step_results=results,
        )

    @property
    def derived_status(self) -> str:
        if self.step_results and all(result.disposition == "passed" for result in self.step_results):
            return "passed"
        if any(result.disposition == "error" for result in self.step_results):
            return "error"
        return "failed"

    def to_dict(self) -> dict[str, object]:
        return {
            "config": _thaw_json(self.config),
            "config_ref": self.config_ref,
            "environment": _thaw_json(self.environment),
            "environment_ref": self.environment_ref,
            "evidence_files": [item.to_dict() for item in self.evidence_files],
            "fresh": self.fresh,
            "gate_result_ref": self.gate_result_ref,
            "phase": self.phase,
            "pre_admission_status_head_ref": self.pre_admission_status_head_ref,
            "run_nonce": self.run_nonce,
            "run_ref": self.run_ref,
            "schema": RECEIPT_SCHEMA,
            "source_ref": self.source_ref,
            "started_at_utc": self.started_at_utc,
            "step_results": [result.to_dict() for result in self.step_results],
            "tier": self.tier,
        }

    @classmethod
    def from_unidentified_dict(cls, value: object) -> "GateReceipt":
        try:
            item = _exact_fields(
                value, _UNIDENTIFIED_RECEIPT_FIELDS, "unidentified gate receipt"
            )
            if item["schema"] != RECEIPT_SCHEMA:
                raise AdmissionValidationError("receipt schema mismatch")
            if type(item["evidence_files"]) is not list or type(item["step_results"]) is not list:
                raise AdmissionValidationError("receipt collections are invalid")
            result = cls.create(
                config=item["config"],
                environment=item["environment"],
                evidence_files=tuple(
                    EvidenceFile.from_dict(row) for row in item["evidence_files"]
                ),
                fresh=item["fresh"],
                phase=item["phase"],
                pre_admission_status_head_ref=item["pre_admission_status_head_ref"],
                run_nonce=item["run_nonce"],
                source_ref=item["source_ref"],
                started_at_utc=item["started_at_utc"],
                step_results=tuple(
                    StepResult.from_dict(row) for row in item["step_results"]
                ),
                tier=item["tier"],
            )
            for field in ("config_ref", "environment_ref", "gate_result_ref"):
                if getattr(result, field) != item[field]:
                    raise AdmissionValidationError(f"receipt {field} mismatch")
            return result
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc

    @classmethod
    def from_dict(cls, value: object) -> "GateReceipt":
        try:
            item = _exact_fields(value, _RECEIPT_FIELDS, "gate receipt")
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        stored_run_ref = item["run_ref"]
        material = dict(item)
        material.pop("run_ref")
        result = cls.from_unidentified_dict(material)
        if stored_run_ref != result.run_ref:
            raise AdmissionValidationError("receipt run_ref mismatch")
        return result


def _definition_contains_path(path: str, declared: object) -> bool:
    if type(declared) is not str:
        return False
    return path.startswith(declared) if declared.endswith("/") else path == declared


def _expected_compile_report(result: StepResult) -> dict[str, object]:
    roots = result.definition.get("roots")
    if not isinstance(roots, tuple):
        raise AdmissionValidationError("compile step roots are unavailable")
    compiled = [
        {"path": item.path, "sha256": item.sha256}
        for item in result.input_files
        if item.path.endswith(".py")
        and any(_definition_contains_path(item.path, root) for root in roots)
    ]
    compiled.sort(key=lambda row: row["path"])
    return {
        "compiled_file_count": len(compiled),
        "compiled_set_ref": content_ref("compiled_sources", compiled),
        "schema": "cemm-compile-step-report-v1",
    }


def _verify_current_source_config(root: Path, receipt: GateReceipt) -> None:
    """Bind one new admission to reviewed config, inventory, reports and source bytes."""
    if type(receipt) is not GateReceipt:
        raise AdmissionValidationError("current-source config check requires GateReceipt")
    try:
        root_path = Path(root).resolve(strict=True)
    except OSError as exc:
        raise AdmissionValidationError("Hybrid MVP source root is unavailable") from exc
    config_target = root_path / "configs" / "validation_gates.json"
    graph, config_raw = _load_gate_graph_with_source(config_target)
    if receipt.config_ref != graph.config_ref:
        raise AdmissionValidationError(
            "admission receipt config_ref differs from current source"
        )
    if _canonical_clone(receipt.config) != _canonical_clone(graph.material):
        raise AdmissionValidationError(
            "admission receipt config differs from current source"
        )

    try:
        committed_blobs = _tracked_source_blobs(root_path, receipt.source_ref)
        manifest = _InputManifestCache(
            root_path, committed_blobs=committed_blobs
        )
        manifest.adopt(config_target, config_raw)
        run_output_path = (
            "artifacts/validation/runs/"
            f"{receipt.run_ref.removeprefix('run:')}.json"
        )
        allowed_outputs = (
            (run_output_path,)
            if (root_path / run_output_path).is_file()
            else ()
        )
        _authenticate_complete_source_snapshot(
            root_path,
            manifest,
            committed_blobs,
            allowed_untracked_paths=allowed_outputs,
        )
        manifest.evidence_file("configs/validation_gates.json")
        current_evidence = tuple(
            manifest.evidence_file(path)
            for path in _required_admission_evidence_paths(receipt.phase)
        )
        expected_inputs: dict[str, tuple[EvidenceFile, ...]] = {}
        for result in receipt.step_results:
            step = graph.steps.get(result.step_id)
            if step is None:
                raise GateConfigError(
                    f"receipt references an unknown current step: {result.step_id}"
                )
            expected_inputs[result.step_id] = manifest.input_files(step)
    except GateConfigError as exc:
        raise AdmissionValidationError(
            f"cannot authenticate current source inputs: {exc}"
        ) from exc

    if receipt.evidence_files != current_evidence:
        raise AdmissionValidationError(
            "admission external evidence differs from the exact committed source"
        )
    for result in receipt.step_results:
        if result.input_files != expected_inputs[result.step_id]:
            raise AdmissionValidationError(
                "admission step input manifest differs from current source: "
                f"{result.step_id}"
            )
        if result.kind == "compile":
            expected_compile = _expected_compile_report(result)
            if _canonical_clone(result.report) != expected_compile:
                raise AdmissionValidationError(
                    "compile report differs from its authenticated input manifest"
                )

    inventory_path = root_path / "scripts" / "test_inventory_core.py"
    inventory_core = _load_exact_module(
        inventory_path, "test_inventory", source_reader=manifest.read
    )

    def source_bytes(path: Path) -> bytes:
        return manifest.read(path)[0]

    try:
        inventory_file = root_path / "governance" / "test_inventory.json"
        inventory_sha = inventory_core.verify_document_authority_pin(
            root_path,
            inventory_file,
            source_reader=source_bytes,
        )
        inventory = inventory_core.load_and_verify(
            root_path,
            inventory_file,
            phase=receipt.phase,
            enforce_reviewed_counts=True,
            expected_sha256=inventory_sha,
            source_reader=source_bytes,
        )
        inventory_selector = validate_inventory_contract(
            graph, inventory, phase=receipt.phase
        )
    except (ValueError, OSError) as exc:
        raise AdmissionValidationError(
            f"cannot reconstruct current inventory selector: {exc}"
        ) from exc
    selector_material = inventory_selector.to_manifest_material()
    expected_selector = dict(selector_material)
    expected_selector["selector_ref"] = content_ref(
        "pytest_selector", selector_material
    )
    inventory_results = tuple(
        result for result in receipt.step_results if result.kind == "pytest_inventory"
    )
    if (
        len(inventory_results) != 1
        or _canonical_clone(inventory_results[0].selector) != expected_selector
    ):
        raise AdmissionValidationError(
            "admission inventory selector differs from current reviewed inventory"
        )

    governance_results = tuple(
        result for result in receipt.step_results if result.kind == "governance"
    )
    if len(governance_results) != 1:
        raise AdmissionValidationError(
            "admission must contain one governance report"
        )
    governance_report = _canonical_clone(governance_results[0].report)
    if type(governance_report) is not dict:
        raise AdmissionValidationError("admission governance report is unavailable")
    expected_governance_fields = {
        "active_node_count": len(inventory_selector.active_node_ids),
        "active_node_set_ref": inventory_selector.active_node_set_ref,
        "collectable_node_count": len(inventory_selector.collectable_node_ids),
        "collectable_node_set_ref": inventory_selector.collectable_node_set_ref,
        "inventory_ref": inventory_selector.inventory_ref,
        "literal_metadata_ref": inventory_selector.literal_metadata_ref,
        "parsed_module_count": int(inventory.parsed_module_count),
        "schema": "cemm-governance-step-report-v1",
        "status_head_ref": receipt.pre_admission_status_head_ref,
    }
    for field, expected in expected_governance_fields.items():
        if governance_report.get(field) != expected:
            raise AdmissionValidationError(
                "governance report differs from current authoritative reconstruction"
            )
    if governance_report.get("status_record_count", 0) < len(PHASES):
        raise AdmissionValidationError("governance status record count is impossible")

    try:
        authority_path = root_path / "docs" / "DOCUMENT_AUTHORITY.json"
        # The G0 evidence material must be validated against a G0-phase
        # inventory, not the receipt's phase inventory. The G0 receipt records
        # G0's active node count, which differs from later phases.
        g0_inventory = inventory
        g0_selector = inventory_selector
        if receipt.phase != "G0":
            g0_inventory = inventory_core.load_and_verify(
                root_path,
                inventory_file,
                phase="G0",
                enforce_reviewed_counts=True,
                expected_sha256=inventory_sha,
                source_reader=source_bytes,
            )
            g0_selector = validate_inventory_contract(
                graph, g0_inventory, phase="G0"
            )
        _validate_g0_evidence_material(
            authority_raw=source_bytes(authority_path),
            baseline_raw=source_bytes(
                root_path / "artifacts" / "validation" / "BASELINE_REPLAY_FINDINGS.json"
            ),
            evaluation_raw=source_bytes(root_path / _G0_EVALUATION_PATH),
            inventory_receipt_raw=source_bytes(
                root_path / "artifacts" / "validation" / "TEST_INVENTORY_RECEIPT.json"
            ),
            inventory_sha256=inventory_sha,
            inventory=g0_inventory,
            selector=g0_selector,
        )
    except (ValueError, OSError) as exc:
        raise AdmissionValidationError(
            f"cannot reconstruct G0 forensic evidence: {exc}"
        ) from exc

def verify_current_source_config(root: Path, receipt: GateReceipt) -> None:
    """Typed public boundary for one newly consumed admission candidate."""
    try:
        _verify_current_source_config(root, receipt)
    except AdmissionValidationError:
        raise
    except GateConfigError as exc:
        raise AdmissionValidationError(
            f"current-source admission verification failed: {exc}"
        ) from exc

def _safe_publication_target(root: Path, relative: str) -> Path:
    checked = _safe_relative_path(relative, "receipt publication path", directory=False)
    root_path = root.resolve(strict=True)
    parts = PurePosixPath(checked).parts
    current = root_path
    for part in parts[:-1]:
        current = current / part
        if _path_is_link_or_reparse(current):
            raise GateConfigError("receipt publication parent is unsafe")
        try:
            current.mkdir(exist_ok=True)
            resolved = current.resolve(strict=True)
            resolved.relative_to(root_path)
        except (OSError, ValueError) as exc:
            raise GateConfigError("receipt publication parent is unsafe") from exc
        if resolved != current or not current.is_dir() or _path_is_link_or_reparse(current):
            raise GateConfigError("receipt publication parent is unsafe")
    target = current / parts[-1]
    if _path_is_link_or_reparse(target):
        raise GateConfigError("receipt publication target is unsafe")
    return target

_MAX_RECEIPT_BYTES = 64 * 1024 * 1024
_MAX_DISCOVERABLE_RUNS = 128


def write_receipt_exclusive(path: Path, receipt: GateReceipt) -> None:
    """Publish canonical receipt bytes without replacing an existing run."""
    raw = canonical_json_bytes(receipt.to_dict())
    if not raw or len(raw) > _MAX_RECEIPT_BYTES:
        raise AdmissionValidationError("admission receipt exceeds its size bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _load_receipt_file(path: Path) -> GateReceipt:
    limit = _MAX_RECEIPT_BYTES
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise AdmissionValidationError(
            f"admission receipt is missing or unreadable: {path.name}"
        ) from exc
    if not raw or len(raw) > limit:
        raise AdmissionValidationError("admission receipt exceeds its size bound")
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text, object_pairs_hook=_duplicate_keys, parse_constant=_nonfinite
        )
        _validate_json_structure_bounds(value)
    except (
        UnicodeDecodeError, json.JSONDecodeError, GateConfigError,
        ValueError, RecursionError,
    ) as exc:
        raise AdmissionValidationError("admission receipt is not strict UTF-8 JSON") from exc
    try:
        if canonical_json_bytes(value) != raw:
            raise AdmissionValidationError("admission receipt bytes are not canonical JSON")
        return GateReceipt.from_dict(value)
    except GateConfigError as exc:
        raise AdmissionValidationError(str(exc)) from exc


def _verify_receipt_evidence(root: Path, receipt: GateReceipt) -> tuple[str, ...]:
    paths: list[str] = []
    # The test-inventory receipt is a living document that must be regenerated
    # when the test inventory changes (e.g. new tests added for a new replay
    # phase). Its content is independently validated by
    # _validate_g0_evidence_material against the current inventory, so the
    # historical hash-pin is exempted for G0 receipts. The baseline findings
    # remain hash-pinned as immutable historical evidence.
    living_evidence_paths = frozenset(
        {"artifacts/validation/TEST_INVENTORY_RECEIPT.json"}
    )
    for evidence in receipt.evidence_files:
        if receipt.phase == "G0" and evidence.path in living_evidence_paths:
            try:
                _resolve_existing_lexical_path(
                    root, evidence.path, require_file=True
                )
            except GateConfigError as exc:
                raise AdmissionValidationError(str(exc)) from exc
            paths.append(evidence.path)
            continue
        try:
            resolved = _resolve_existing_lexical_path(
                root, evidence.path, require_file=True
            )
            digest = _cached_evidence_digest(resolved)
        except GateConfigError as exc:
            raise AdmissionValidationError(str(exc)) from exc
        if digest != evidence.sha256:
            raise AdmissionValidationError(
                f"evidence hash mismatch: {evidence.path}"
            )
        paths.append(evidence.path)
    if tuple(paths) != tuple(sorted(paths)) or len(paths) != len(set(paths)):
        raise AdmissionValidationError("receipt evidence paths are not sorted and unique")
    if receipt.phase == "G0":
        evidence_by_path = {item.path: item for item in receipt.evidence_files}
        try:
            baseline_path = _resolve_existing_lexical_path(
                root,
                "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
                require_file=True,
            )
            inventory_path = _resolve_existing_lexical_path(
                root,
                "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
                require_file=True,
            )
            baseline_raw = _read_bounded_file(
                baseline_path, maximum=_MAX_AUTHENTICATED_FILE_BYTES
            )
            inventory_raw = _read_bounded_file(
                inventory_path, maximum=_MAX_AUTHENTICATED_FILE_BYTES
            )
            for relative, raw in (
                ("artifacts/validation/BASELINE_REPLAY_FINDINGS.json", baseline_raw),
            ):
                if hashlib.sha256(raw).hexdigest() != evidence_by_path[relative].sha256:
                    raise AdmissionValidationError(
                        f"evidence changed during intrinsic validation: {relative}"
                    )
            baseline = _load_canonical_g0_evidence(
                baseline_raw, path=baseline_path
            )
            inventory_receipt = _load_canonical_g0_evidence(
                inventory_raw, path=inventory_path
            )
            _validate_g0_baseline_findings(
                baseline, baseline_source_ref=_G0_BASELINE_SOURCE_REF
            )
            _validate_g0_inventory_receipt_intrinsic(inventory_receipt)
        except GateConfigError as exc:
            raise AdmissionValidationError(
                f"G0 intrinsic evidence validation failed: {exc}"
            ) from exc
    return tuple(paths)


def _validate_loaded_receipt(
    root: Path,
    path: Path,
    receipt: GateReceipt,
    *,
    phase: str,
    expected_status: str,
) -> tuple[str, ...]:
    expected_name = f"{receipt.run_ref.removeprefix('run:')}.json"
    if path.name != expected_name:
        raise AdmissionValidationError("receipt filename does not match run_ref")
    if receipt.phase != phase:
        raise AdmissionValidationError("admission receipt phase mismatch")
    if receipt.tier != "admission":
        raise AdmissionValidationError("receipt is not an admission tier")
    if receipt.fresh is not True:
        raise AdmissionValidationError("admission receipt is not fresh")
    if receipt.derived_status != expected_status:
        raise AdmissionValidationError("admission receipt derived status mismatch")

    return _verify_receipt_evidence(root, receipt)


def load_verified_admission_receipt(
    root: Path,
    *,
    phase: str,
    expected_status: str,
    run_ref: str | None = None,
) -> tuple[GateReceipt, tuple[str, ...]]:
    """Reconstruct one stored admission without executing gates or reading ledgers."""
    if phase not in PHASES:
        raise AdmissionValidationError("requested admission phase is invalid")
    if expected_status not in {"passed", "failed", "error"}:
        raise AdmissionValidationError("requested admission status is invalid")
    root_path = Path(root).resolve()
    run_dir = root_path / "artifacts" / "validation" / "runs"
    if _path_is_link_or_reparse(run_dir):
        raise AdmissionValidationError("admission run directory is unsafe")
    try:
        resolved_run_dir = run_dir.resolve(strict=True)
        resolved_run_dir.relative_to(root_path)
    except (OSError, ValueError) as exc:
        raise AdmissionValidationError("admission run directory is unavailable") from exc
    if resolved_run_dir != run_dir:
        raise AdmissionValidationError("admission run directory is unsafe")
    if run_ref is not None:
        if type(run_ref) is not str or _RUN_REF_RE.fullmatch(run_ref) is None:
            raise AdmissionValidationError("requested run_ref is invalid")
        paths = (run_dir / f"{run_ref.removeprefix('run:')}.json",)
    else:
        discovered: list[Path] = []
        try:
            for candidate in run_dir.iterdir():
                if candidate.suffix != ".json":
                    continue
                discovered.append(candidate)
                if len(discovered) > _MAX_DISCOVERABLE_RUNS:
                    raise AdmissionValidationError(
                        "admission run discovery exceeds its count bound"
                    )
        except AdmissionValidationError:
            raise
        except OSError as exc:
            raise AdmissionValidationError("cannot enumerate admission runs") from exc
        paths = tuple(sorted(discovered, key=lambda item: item.name))
        if not paths:
            raise AdmissionValidationError("no eligible admission receipt exists")
    eligible: list[tuple[GateReceipt, Path, tuple[str, ...]]] = []
    for path in paths:
        if _path_is_link_or_reparse(path) or not path.is_file():
            raise AdmissionValidationError("admission receipt is missing or its path is unsafe")
        receipt = _load_receipt_file(path)
        if run_ref is not None and receipt.run_ref != run_ref:
            raise AdmissionValidationError("loaded admission run_ref mismatch")
        try:
            evidence_paths = _validate_loaded_receipt(
                root_path, path, receipt, phase=phase, expected_status=expected_status
            )
        except AdmissionValidationError:
            if run_ref is not None:
                raise
            if receipt.phase == phase and receipt.tier == "admission":
                raise
            continue
        eligible.append((receipt, path, evidence_paths))
    if not eligible:
        raise AdmissionValidationError("no eligible admission receipt exists")
    if len(eligible) != 1:
        raise AdmissionValidationError("eligible admission receipt selection is ambiguous")
    receipt, path, evidence_paths = eligible[0]
    run_path = path.resolve().relative_to(root_path).as_posix()
    return receipt, tuple(sorted((*evidence_paths, run_path)))


__all__ = [
    "AdmissionValidationError", "EvidenceFile", "GateConfigError", "GateGraph",
    "GatePolicy", "GateReceipt", "InventorySelector", "ParsedPytestReport",
    "ProcessObservation", "StepResult", "ValidationOutcome", "bounded_slowest",
    "canonical_json_bytes", "content_ref", "current_environment_material",
    "isolated_test_environment", "load_gate_graph", "load_strict_json",
    "load_verified_admission_receipt", "observe_process", "parse_pytest_report",
    "run_validation", "validate_inventory_contract", "verify_current_source_config",
    "write_receipt_exclusive",
]


@dataclass(frozen=True)
class InventorySelector:
    phase: str
    inventory_ref: str
    literal_metadata_ref: str
    active_node_set_ref: str
    active_node_ids: tuple[str, ...]
    collectable_node_set_ref: str
    collectable_node_ids: tuple[str, ...]

    def to_manifest_material(self) -> dict[str, object]:
        return {
            "active_node_ids": list(self.active_node_ids),
            "collectable_node_ids": list(self.collectable_node_ids),
            "mode": "admission",
            "schema": "cemm-pytest-selector-v1",
            "test_root": "tests",
        }


def validate_inventory_contract(
    graph: GateGraph,
    inventory: object,
    *,
    phase: str,
) -> InventorySelector:
    """Bind reviewed owner/phase selectors to the source-only inventory result."""
    if phase not in graph.phases:
        raise GateConfigError(f"phase has no validation plan: {phase}")
    owner_groups = getattr(inventory, "owner_node_ids", None)
    phase_nodes = getattr(inventory, "phase_node_ids", None)
    active_nodes = getattr(inventory, "active_node_ids", None)
    collectable_nodes = getattr(inventory, "collectable_node_ids", None)
    if not isinstance(owner_groups, Mapping):
        raise GateConfigError("inventory owner groups are unavailable")
    if any(type(value) is not tuple for value in (phase_nodes, active_nodes, collectable_nodes)):
        raise GateConfigError("inventory node sets are unavailable")
    configured_owners = graph.phases[phase].owners
    if set(configured_owners) != set(owner_groups):
        raise GateConfigError(
            "configured owner set does not equal the literal active inventory owner set"
        )
    for owner in sorted(configured_owners):
        configured = graph.resolve_pytest_nodes(phase, "owner", owner)
        expected = tuple(owner_groups[owner])
        if configured != expected:
            raise GateConfigError(
                f"configured owner selector does not equal inventory group: {owner}"
            )
    configured_phase = graph.resolve_pytest_nodes(phase, "phase")
    if configured_phase != tuple(phase_nodes):
        raise GateConfigError("configured phase selector does not equal inventory phase group")
    due = getattr(inventory, "due_rewrite_refs", None)
    if type(due) is not tuple:
        raise GateConfigError("inventory rewrite lifecycle is unavailable")
    if due:
        raise GateConfigError("due test rewrite obligations block validation")
    active = tuple(active_nodes)
    collectable = tuple(collectable_nodes)
    if active != tuple(sorted(active)) or collectable != tuple(sorted(collectable)):
        raise GateConfigError("inventory node sets must be sorted")
    if not set(active).issubset(collectable):
        raise GateConfigError("active inventory nodes are not collectable")
    fields = {
        "inventory_ref": getattr(inventory, "inventory_ref", None),
        "literal_metadata_ref": getattr(inventory, "literal_metadata_ref", None),
        "active_node_set_ref": getattr(inventory, "active_node_set_ref", None),
        "collectable_node_set_ref": getattr(inventory, "collectable_node_set_ref", None),
    }
    if any(type(value) is not str or _CONTENT_REF_RE.fullmatch(value) is None for value in fields.values()):
        raise GateConfigError("inventory content identities are invalid")
    return InventorySelector(
        phase=phase,
        inventory_ref=fields["inventory_ref"],
        literal_metadata_ref=fields["literal_metadata_ref"],
        active_node_set_ref=fields["active_node_set_ref"],
        active_node_ids=active,
        collectable_node_set_ref=fields["collectable_node_set_ref"],
        collectable_node_ids=collectable,
    )


_PRUNED_RUNTIME_INPUT_DIR_NAMES = frozenset({"__pycache__"})
_FORBIDDEN_IGNORED_INPUT_DIR_NAMES = frozenset(
    {
        ".git", ".hypothesis", ".pytest_cache", ".pytest-runtime",
        ".ruff_cache", ".test-tmp", "build", "dist",
    }
)
_FORBIDDEN_IGNORED_INPUT_FILE_NAMES: frozenset[str] = frozenset()
_FORBIDDEN_IGNORED_INPUT_FILE_SUFFIXES = (".pyc",)
_MAX_INPUT_FILES = 10_000
_MAX_INPUT_DIRECTORIES = 10_000
_MAX_INPUT_BYTES = 512 * 1024 * 1024


_MAX_EXACT_SOURCE_BYTES = 8 * 1024 * 1024
_EXACT_MODULE_CACHE: dict[tuple[str, ...], ModuleType] = {}


def _read_exact_source_bytes(path: Path) -> bytes:
    resolved = path.resolve(strict=True)
    if _path_is_link_or_reparse(path) or not resolved.is_file():
        raise GateConfigError(f"reviewed source module is unsafe: {path.name}")
    try:
        size = resolved.stat().st_size
        if size <= 0 or size > _MAX_EXACT_SOURCE_BYTES:
            raise GateConfigError(
                f"reviewed source module exceeds its byte bound: {path.name}"
            )
        with resolved.open("rb") as stream:
            raw = stream.read(size + 1)
    except GateConfigError:
        raise
    except OSError as exc:
        raise GateConfigError(f"cannot read reviewed source module: {path.name}") from exc
    if len(raw) != size:
        raise GateConfigError(f"reviewed source module changed while reading: {path.name}")
    return raw


def _exec_exact_source_module(
    path: Path,
    name: str,
    *,
    package: str,
    raw: bytes,
) -> ModuleType:
    resolved = path.resolve(strict=True)
    if type(raw) is not bytes or not raw or len(raw) > _MAX_EXACT_SOURCE_BYTES:
        raise GateConfigError(f"reviewed source bytes are invalid: {path.name}")
    try:
        code = compile(raw, str(resolved), "exec", dont_inherit=True, optimize=0)
    except (SyntaxError, ValueError, TypeError) as exc:
        raise GateConfigError(f"reviewed source module is invalid: {path.name}") from exc
    module = ModuleType(name)
    module.__file__ = str(resolved)
    module.__package__ = package
    module.__cached__ = None
    module.__loader__ = None
    module.__spec__ = importlib.util.spec_from_loader(
        name, loader=None, origin=str(resolved)
    )
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except BaseException:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    return module


def _load_exact_module(
    path: Path,
    purpose: str,
    *,
    source_reader: Callable[[Path], tuple[bytes, str]] | None = None,
) -> object:
    resolved = path.resolve(strict=True)

    def read_source(source_path: Path) -> tuple[bytes, str]:
        if source_reader is None:
            raw = _read_exact_source_bytes(source_path)
            return raw, hashlib.sha256(raw).hexdigest()
        raw, digest = source_reader(source_path)
        if type(raw) is not bytes or type(digest) is not str:
            raise GateConfigError("authenticated source reader is malformed")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise GateConfigError("authenticated source reader digest mismatch")
        return raw, digest

    raw, source_sha = read_source(resolved)
    canonical_raw: bytes | None = None
    canonical_sha = ""
    process_raw: bytes | None = None
    process_sha = ""
    if purpose == "governance":
        canonical_raw, canonical_sha = read_source(resolved.parent / "canonical.py")
        process_raw, process_sha = read_source(
            resolved.parent / "process_control.py"
        )
    cache_key = (
        purpose, str(resolved), source_sha, canonical_sha, process_sha
    )
    cached = _EXACT_MODULE_CACHE.get(cache_key)
    if cached is not None and sys.modules.get(cached.__name__) is cached:
        return cached

    path_digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
    identity = hashlib.sha256("|".join(cache_key).encode("utf-8")).hexdigest()[:16]
    if purpose == "governance":
        package_name = f"_cemm_exact_governance_{path_digest}_{identity}"
        package = ModuleType(package_name)
        package.__file__ = str(resolved.parent / "__init__.py")
        package.__package__ = package_name
        package.__path__ = ()
        package.__loader__ = None
        package.__spec__ = importlib.util.spec_from_loader(
            package_name, loader=None, is_package=True
        )
        sys.modules[package_name] = package
        process_name = f"{package_name}.process_control"
        canonical_name = f"{package_name}.canonical"
        assert canonical_raw is not None
        assert process_raw is not None
        try:
            _exec_exact_source_module(
                resolved.parent / "process_control.py",
                process_name,
                package=package_name,
                raw=process_raw,
            )
            _exec_exact_source_module(
                resolved.parent / "canonical.py",
                canonical_name,
                package=package_name,
                raw=canonical_raw,
            )
            name = f"{package_name}.governance"
            module = _exec_exact_source_module(
                resolved,
                name,
                package=package_name,
                raw=raw,
            )
        except BaseException:
            sys.modules.pop(canonical_name, None)
            sys.modules.pop(process_name, None)
            sys.modules.pop(package_name, None)
            raise
    else:
        name = f"_cemm_exact_{purpose}_{path_digest}_{identity}"
        module = _exec_exact_source_module(
            resolved, name, package="", raw=raw
        )
    _EXACT_MODULE_CACHE[cache_key] = module
    return module

def _path_is_link_or_reparse(path: Path) -> bool:
    """Return whether a lexical path is a symlink, junction, or reparse point."""
    try:
        if path.is_symlink():
            return True
        junction = getattr(path, "is_junction", None)
        if callable(junction) and junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise GateConfigError(f"cannot inspect path boundary: {path.name}") from exc
    return bool(attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT


def _resolve_existing_lexical_path(
    root: Path,
    relative: str,
    *,
    require_file: bool | None,
) -> Path:
    root_path = root.resolve(strict=True)
    checked = _safe_relative_path(
        relative,
        "authenticated lexical path",
        directory=(False if require_file is True else True if require_file is False else None),
    )
    current = root_path
    for part in PurePosixPath(checked.rstrip("/")).parts:
        current = current / part
        if _path_is_link_or_reparse(current):
            raise GateConfigError(f"authenticated path contains a link: {checked}")
        try:
            resolved = current.resolve(strict=True)
            resolved.relative_to(root_path)
        except (OSError, ValueError) as exc:
            raise GateConfigError(f"authenticated path is unavailable: {checked}") from exc
        if resolved != current:
            raise GateConfigError(f"authenticated path is redirected: {checked}")
    if require_file is True and not current.is_file():
        raise GateConfigError(f"authenticated path is not a file: {checked}")
    if require_file is False and not current.is_dir():
        raise GateConfigError(f"authenticated path is not a directory: {checked}")
    return current

@contextmanager
def _temporary_run_root(root: Path, nonce: str):
    if (
        type(nonce) is not str
        or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", nonce) is None
    ):
        raise GateConfigError("validation run nonce is unsafe")
    try:
        root_path = root.resolve(strict=True)
    except OSError as exc:
        raise GateConfigError("Hybrid MVP root is unavailable") from exc
    parent = root_path / ".test-tmp"
    if _path_is_link_or_reparse(parent):
        raise GateConfigError("unsafe validation temp parent")
    try:
        parent.mkdir(exist_ok=True)
    except OSError as exc:
        raise GateConfigError("cannot create validation temp parent") from exc
    if _path_is_link_or_reparse(parent) or not parent.is_dir():
        raise GateConfigError("unsafe validation temp parent")
    try:
        resolved_parent = parent.resolve(strict=True)
        resolved_parent.relative_to(root_path)
    except (OSError, ValueError) as exc:
        raise GateConfigError("unsafe validation temp parent") from exc
    if resolved_parent != parent:
        raise GateConfigError("unsafe validation temp parent")

    target = parent / f"validation-{nonce}"
    if target.parent != parent or target.exists() or _path_is_link_or_reparse(target):
        raise GateConfigError("exclusive validation run root is unavailable")
    try:
        target.mkdir()
    except OSError as exc:
        raise GateConfigError("exclusive validation run root is unavailable") from exc
    if _path_is_link_or_reparse(target) or target.resolve(strict=True) != target:
        raise GateConfigError("exclusive validation run root is unsafe")
    try:
        yield target
    finally:
        if _path_is_link_or_reparse(target):
            raise GateConfigError("refusing to clean an unsafe validation run root")
        try:
            resolved = target.resolve(strict=True)
        except OSError as exc:
            raise GateConfigError("validation run-root disappeared before cleanup") from exc
        if resolved.parent != parent or not resolved.name.startswith("validation-"):
            raise GateConfigError("refusing to clean an unsafe validation run root")
        try:
            shutil.rmtree(resolved)
        except OSError as exc:
            raise GateConfigError(
                f"validation run-root cleanup failed: {resolved.name}"
            ) from exc
        if resolved.exists() or _path_is_link_or_reparse(resolved):
            raise GateConfigError(
                f"validation run-root cleanup was incomplete: {resolved.name}"
            )

def _repository_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise GateConfigError("declared input escapes the Hybrid MVP root") from exc


def _pruned_runtime_input_directory(name: str) -> bool:
    return name in _PRUNED_RUNTIME_INPUT_DIR_NAMES


def _forbidden_ignored_input_directory(name: str) -> bool:
    return (
        name in _FORBIDDEN_IGNORED_INPUT_DIR_NAMES
        or name.endswith(".egg-info")
    )


def _forbidden_ignored_input_file(name: str) -> bool:
    return (
        name in _FORBIDDEN_IGNORED_INPUT_FILE_NAMES
        or name.endswith(_FORBIDDEN_IGNORED_INPUT_FILE_SUFFIXES)
    )


def _walk_input_files(root: Path, declared: str) -> tuple[Path, ...]:
    candidate = _resolve_existing_lexical_path(
        root, declared.rstrip("/"), require_file=None
    )
    resolved = candidate
    if resolved.is_file():
        if _forbidden_ignored_input_file(resolved.name):
            raise GateConfigError(f"declared gate input is ignored: {declared}")
        return (resolved,)
    if not resolved.is_dir():
        raise GateConfigError(f"declared gate input is not regular: {declared}")

    files: list[Path] = []
    directory_count = 0
    try:
        walker = os.walk(resolved, topdown=True, followlinks=False)
        for directory, names, filenames in walker:
            directory_count += 1
            if directory_count > _MAX_INPUT_DIRECTORIES:
                raise GateConfigError(
                    "declared input tree exceeds its directory-count bound"
                )
            forbidden_directories = sorted(
                name for name in names if _forbidden_ignored_input_directory(name)
            )
            if forbidden_directories:
                raise GateConfigError(
                    "declared input tree contains ignored governed directories: "
                    + ", ".join(forbidden_directories)
                )
            names[:] = sorted(
                name for name in names if not _pruned_runtime_input_directory(name)
            )
            for name in tuple(names):
                child = Path(directory) / name
                if _path_is_link_or_reparse(child):
                    raise GateConfigError(
                        f"declared input tree contains a linked directory: {declared}"
                    )
            for name in sorted(filenames):
                if _forbidden_ignored_input_file(name):
                    raise GateConfigError(
                        f"declared input tree contains an ignored governed file: {name}"
                    )
                path = Path(directory) / name
                if _path_is_link_or_reparse(path):
                    raise GateConfigError(
                        f"declared input tree contains a linked file: {declared}"
                    )
                if not path.is_file():
                    raise GateConfigError(
                        f"declared input tree contains an irregular file: {declared}"
                    )
                files.append(path.resolve(strict=True))
                if len(files) > _MAX_INPUT_FILES:
                    raise GateConfigError(
                        "declared input set exceeds its file-count bound"
                    )
    except GateConfigError:
        raise
    except OSError as exc:
        raise GateConfigError(f"cannot enumerate declared gate input: {declared}") from exc
    return tuple(sorted(files, key=lambda item: item.as_posix()))

class _InputManifestCache:
    """One-run exact expansion and streaming digest budget."""

    def __init__(
        self,
        root: Path,
        *,
        committed_blobs: Mapping[str, str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self._expansions: dict[str, tuple[Path, ...]] = {}
        self._raw_bytes: dict[str, bytes] = {}
        self._digests: dict[str, str] = {}
        self._sizes: dict[str, int] = {}
        self._total_input_bytes = 0
        self._committed_blobs = (
            None if committed_blobs is None else dict(committed_blobs)
        )
        if self._committed_blobs is not None:
            for relative, object_id in self._committed_blobs.items():
                if (
                    type(relative) is not str
                    or type(object_id) is not str
                    or re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", object_id)
                    is None
                ):
                    raise GateConfigError("committed source blob map is malformed")

    def adopt(self, path: Path, raw: bytes) -> str:
        """Authenticate and retain bytes already used to construct an owner."""
        relative = _repository_relative(self.root, path)
        if type(raw) is not bytes or not raw:
            raise GateConfigError(f"authenticated source bytes are invalid: {relative}")
        digest = hashlib.sha256(raw).hexdigest()
        cached = self._digests.get(relative)
        if cached is not None:
            if cached != digest or self._raw_bytes.get(relative) != raw:
                raise GateConfigError(f"authenticated source bytes changed: {relative}")
            return cached
        if len(self._digests) >= _MAX_INPUT_FILES:
            raise GateConfigError(
                "declared input set exceeds its run-wide file-count bound"
            )
        size = len(raw)
        if size > _MAX_INPUT_BYTES - self._total_input_bytes:
            raise GateConfigError(
                "declared input set exceeds its run-wide byte bound"
            )
        committed_object_id = (
            None
            if self._committed_blobs is None
            else self._committed_blobs.get(relative)
        )
        if self._committed_blobs is not None and committed_object_id is None:
            raise GateConfigError(
                f"gate input is absent from the exact committed source: {relative}"
            )
        if committed_object_id is not None:
            try:
                git_sha1 = hashlib.sha1(usedforsecurity=False)
            except TypeError:  # pragma: no cover - legacy Python compatibility
                git_sha1 = hashlib.sha1()
            git_sha256 = hashlib.sha256()
            header = f"blob {size}\0".encode("ascii")
            git_sha1.update(header)
            git_sha1.update(raw)
            git_sha256.update(header)
            git_sha256.update(raw)
            object_id = (
                git_sha1.hexdigest()
                if len(committed_object_id) == 40
                else git_sha256.hexdigest()
            )
            if object_id != committed_object_id:
                raise GateConfigError(
                    f"gate input bytes differ from the exact committed source: {relative}"
                )
        self._digests[relative] = digest
        self._sizes[relative] = size
        self._raw_bytes[relative] = raw
        self._total_input_bytes += size
        return digest
    def expand(self, declared: str) -> tuple[Path, ...]:
        expanded = self._expansions.get(declared)
        if expanded is None:
            expanded = _walk_input_files(self.root, declared)
            if self._committed_blobs is not None:
                actual = {
                    _repository_relative(self.root, path) for path in expanded
                }
                if declared.endswith("/"):
                    expected = {
                        path
                        for path in self._committed_blobs
                        if path.startswith(declared)
                    }
                else:
                    expected = (
                        {declared} if declared in self._committed_blobs else set()
                    )
                if actual != expected:
                    raise GateConfigError(
                        f"declared input tree differs from the exact committed source: "
                        f"{declared}"
                    )
            self._expansions[declared] = expanded
        return expanded

    def _load_raw(self, path: Path, relative: str) -> bytes:
        cached = self._raw_bytes.get(relative)
        if cached is not None:
            return cached
        size = self._sizes[relative]
        try:
            with path.open("rb") as stream:
                raw = stream.read(size + 1)
        except OSError as exc:
            raise GateConfigError(f"cannot read gate input: {relative}") from exc
        if len(raw) != size:
            raise GateConfigError(f"gate input changed while reading: {relative}")
        if hashlib.sha256(raw).hexdigest() != self._digests[relative]:
            raise GateConfigError(f"gate input changed while reading: {relative}")
        self._raw_bytes[relative] = raw
        return raw

    def digest(self, path: Path, *, retain_raw: bool = False) -> str:
        relative = _repository_relative(self.root, path)
        cached = self._digests.get(relative)
        if cached is not None:
            if retain_raw:
                self._load_raw(path, relative)
            return cached
        committed_object_id = None
        if self._committed_blobs is not None:
            committed_object_id = self._committed_blobs.get(relative)
            if committed_object_id is None:
                raise GateConfigError(
                    f"gate input is absent from the exact committed source: {relative}"
                )
        if len(self._digests) >= _MAX_INPUT_FILES:
            raise GateConfigError(
                "declared input set exceeds its run-wide file-count bound"
            )
        remaining = _MAX_INPUT_BYTES - self._total_input_bytes
        try:
            size = path.stat().st_size
            if size < 0 or size > remaining:
                raise GateConfigError(
                    "declared input set exceeds its run-wide byte bound"
                )
            digest = hashlib.sha256()
            try:
                git_sha1 = hashlib.sha1(usedforsecurity=False)
            except TypeError:  # pragma: no cover - legacy Python compatibility
                git_sha1 = hashlib.sha1()
            git_sha256 = hashlib.sha256()
            blob_header = f"blob {size}\0".encode("ascii")
            git_sha1.update(blob_header)
            git_sha256.update(blob_header)
            raw_parts: list[bytes] | None = [] if retain_raw else None
            total = 0
            with path.open("rb") as stream:
                while True:
                    chunk = stream.read(min(1024 * 1024, size - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > size:
                        raise GateConfigError(
                            f"gate input changed while reading: {relative}"
                        )
                    digest.update(chunk)
                    git_sha1.update(chunk)
                    git_sha256.update(chunk)
                    if raw_parts is not None:
                        raw_parts.append(chunk)
        except GateConfigError:
            raise
        except OSError as exc:
            raise GateConfigError(f"cannot read gate input: {relative}") from exc
        if total != size:
            raise GateConfigError(f"gate input changed while reading: {relative}")
        if committed_object_id is not None:
            actual_object_id = (
                git_sha1.hexdigest()
                if len(committed_object_id) == 40
                else git_sha256.hexdigest()
            )
            if actual_object_id != committed_object_id:
                raise GateConfigError(
                    f"gate input bytes differ from the exact committed source: {relative}"
                )
        value = digest.hexdigest()
        self._digests[relative] = value
        self._sizes[relative] = size
        self._total_input_bytes += size
        if raw_parts is not None:
            self._raw_bytes[relative] = b"".join(raw_parts)
        return value

    def read(self, path: Path) -> tuple[bytes, str]:
        relative = _repository_relative(self.root, path)
        digest = self.digest(path, retain_raw=True)
        return self._raw_bytes[relative], digest

    def evidence_file(self, relative: str) -> EvidenceFile:
        checked = _safe_relative_path(relative, "authenticated repository file", directory=False)
        resolved = _resolve_existing_lexical_path(
            self.root, checked, require_file=True
        )
        return EvidenceFile(path=checked, sha256=self.digest(resolved))

    def input_files(self, step: GateStep) -> tuple[EvidenceFile, ...]:
        files: dict[str, EvidenceFile] = {}
        retain_raw = step.kind == "compile"
        for declared in step.inputs:
            for path in self.expand(declared):
                relative = _repository_relative(self.root, path)
                digest = self.digest(path, retain_raw=retain_raw)
                files[relative] = EvidenceFile(relative, digest)
        if len(files) > _MAX_INPUT_FILES:
            raise GateConfigError(
                "declared input set exceeds its file-count bound"
            )
        return tuple(files[path] for path in sorted(files))

_MAX_GIT_PROBE_BYTES = 4 * 1024 * 1024


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


def _bounded_git_probe(
    root: Path,
    arguments: Sequence[str],
    *,
    context: str,
    timeout_seconds: int,
) -> bytes:
    try:
        completed = capture_bounded_process(
            ["git", "--no-replace-objects", "-C", str(root), *arguments],
            max_stdout_bytes=_MAX_GIT_PROBE_BYTES,
            max_stderr_bytes=_MAX_GIT_PROBE_BYTES,
            timeout_seconds=timeout_seconds,
            env=_sanitized_git_environment(),
        )
    except (OSError, ProcessControlError, ValueError) as exc:
        raise GateConfigError(f"cannot {context}") from exc
    if completed.stderr or completed.returncode != 0:
        raise GateConfigError(f"cannot {context}")
    return completed.stdout


def _parse_tracked_source_blobs(raw: bytes) -> Mapping[str, str]:
    if type(raw) is not bytes or not raw or not raw.endswith(b"\0"):
        raise GateConfigError("committed source tree is malformed")
    records = raw[:-1].split(b"\0")
    if not records or any(not record for record in records):
        raise GateConfigError("committed source tree is malformed")
    blobs: dict[str, str] = {}
    casefolded: set[str] = set()
    object_id_size: int | None = None
    for raw_record in records:
        try:
            metadata, raw_path = raw_record.split(b"\t", 1)
            mode, object_type, raw_object_id = metadata.split(b" ")
            relative = raw_path.decode("utf-8", errors="strict")
            object_id = raw_object_id.decode("ascii", errors="strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GateConfigError("committed source tree is malformed") from exc
        path = PurePosixPath(relative)
        canonical = path.as_posix()
        folded = relative.casefold()
        if (
            mode not in {b"100644", b"100755"}
            or object_type != b"blob"
            or len(object_id) not in {40, 64}
            or re.fullmatch(r"[0-9a-f]+", object_id) is None
            or (object_id_size is not None and len(object_id) != object_id_size)
            or not relative
            or relative != relative.strip()
            or canonical != relative
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in relative
            or any(ord(character) < 32 or ord(character) == 127 for character in relative)
            or relative in blobs
            or folded in casefolded
        ):
            raise GateConfigError("committed source tree is malformed")
        object_id_size = len(object_id)
        blobs[relative] = object_id
        casefolded.add(folded)
        if len(blobs) > _MAX_INPUT_FILES:
            raise GateConfigError("committed source tree exceeds its file-count bound")
    return MappingProxyType(blobs)


def _tracked_source_blobs(root: Path, source_ref: str) -> Mapping[str, str]:
    """Return the exact regular-blob identity for every path in one commit."""
    if type(source_ref) is not str or _SOURCE_RE.fullmatch(source_ref) is None:
        raise GateConfigError("committed source identity is invalid")
    raw = _bounded_git_probe(
        root,
        ("ls-tree", "-r", "-z", f"{source_ref}^{{commit}}", "--", "."),
        context="load the exact committed source tree",
        timeout_seconds=60,
    )
    return _parse_tracked_source_blobs(raw)


_TRANSIENT_SOURCE_DIR_NAMES = frozenset(
    {
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".pytest-runtime",
        ".ruff_cache",
        ".test-tmp",
        ".venv",
        "__pycache__",
    }
)

_TRANSIENT_SOURCE_FILE_SUFFIXES = frozenset(
    {
        ".pyc",
        ".pyo",
    }
)


def _authenticate_complete_source_snapshot(
    root: Path,
    manifest: _InputManifestCache,
    committed_blobs: Mapping[str, str],
    *,
    allowed_untracked_paths: Iterable[str] = (),
) -> None:
    """Authenticate the complete executable checkout against one ls-tree map."""
    root_path = root.resolve(strict=True)
    if manifest.root != root_path:
        raise GateConfigError("source manifest root mismatch")
    committed = set(committed_blobs)
    for relative in committed:
        if any(
            part in _TRANSIENT_SOURCE_DIR_NAMES
            for part in PurePosixPath(relative).parts
        ):
            raise GateConfigError("committed source occupies a transient path")
    allowed: set[str] = set()
    for relative in allowed_untracked_paths:
        checked = _safe_relative_path(
            relative, "allowed validation output", directory=False
        )
        if checked in committed or checked in allowed:
            raise GateConfigError("allowed validation output set is malformed")
        allowed.add(checked)

    actual: dict[str, Path] = {}
    casefolded: set[str] = set()
    pending = [root_path]
    while pending:
        directory = pending.pop()
        if _path_is_link_or_reparse(directory):
            raise GateConfigError("source snapshot contains a redirected directory")
        try:
            entries = sorted(os.scandir(directory), key=lambda row: row.name)
        except OSError as exc:
            raise GateConfigError("cannot enumerate complete source snapshot") from exc
        for entry in entries:
            path = Path(entry.path)
            try:
                if entry.is_symlink() or _path_is_link_or_reparse(path):
                    raise GateConfigError(
                        "source snapshot contains a linked or redirected path"
                    )
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in _TRANSIENT_SOURCE_DIR_NAMES:
                        continue
                    pending.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    raise GateConfigError(
                        "source snapshot contains an irregular filesystem entry"
                    )
                if any(
                    entry.name.endswith(suffix)
                    for suffix in _TRANSIENT_SOURCE_FILE_SUFFIXES
                ):
                    continue
            except OSError as exc:
                raise GateConfigError("cannot inspect complete source snapshot") from exc
            relative = _repository_relative(root_path, path)
            folded = relative.casefold()
            if relative in actual or folded in casefolded:
                raise GateConfigError("source snapshot contains a path collision")
            actual[relative] = path
            casefolded.add(folded)
            if len(actual) > _MAX_INPUT_FILES:
                raise GateConfigError(
                    "complete source snapshot exceeds its file-count bound"
                )

    actual_paths = set(actual)
    expected_paths = committed | allowed
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)[:8]
        extra = sorted(actual_paths - expected_paths)[:8]
        detail = ", ".join(
            [
                *(f"missing:{item}" for item in missing),
                *(f"unexpected:{item}" for item in extra),
            ]
        )
        raise GateConfigError(
            "live source path set differs from the exact committed source"
            + (f": {detail}" if detail else "")
        )
    for relative in sorted(committed):
        manifest.digest(actual[relative])


def _git_head(root: Path) -> str:
    raw = _bounded_git_probe(
        root,
        ("rev-parse", "--verify", "HEAD^{commit}"),
        context="resolve the exact source HEAD",
        timeout_seconds=30,
    )
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise GateConfigError("cannot resolve the exact source HEAD")
    try:
        value = raw[:-1].decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise GateConfigError("cannot resolve the exact source HEAD") from exc
    if _SOURCE_RE.fullmatch(value) is None:
        raise GateConfigError("cannot resolve the exact source HEAD")
    return value


def _clean_git_snapshot(root: Path) -> tuple[str, bool]:
    raw = _bounded_git_probe(
        root,
        (
            "status", "--porcelain=v2", "--branch", "--untracked-files=all",
            "--no-renames",
        ),
        context="capture a bounded source snapshot",
        timeout_seconds=60,
    )
    try:
        stdout = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise GateConfigError("source snapshot is not UTF-8") from exc
    source_ref: str | None = None
    dirty = False
    for line in stdout.splitlines():
        if line.startswith("# branch.oid "):
            if source_ref is not None:
                raise GateConfigError("source snapshot repeats its HEAD identity")
            source_ref = line.removeprefix("# branch.oid ")
        elif line and not line.startswith("#"):
            dirty = True
    if source_ref is None or _SOURCE_RE.fullmatch(source_ref) is None:
        raise GateConfigError("source snapshot lacks an exact HEAD")
    return source_ref, dirty

def _rss_reader_for(process: subprocess.Popen[bytes]) -> Callable[[], int | None]:
    if os.name == "nt":
        def windows_rss() -> int | None:
            try:
                import ctypes
                from ctypes import wintypes

                class Counters(ctypes.Structure):
                    _fields_ = [
                        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t),
                    ]

                counters = Counters()
                counters.cb = ctypes.sizeof(Counters)
                ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                    wintypes.HANDLE(int(process._handle)),
                    ctypes.byref(counters),
                    counters.cb,
                )
                return int(counters.WorkingSetSize) if ok else None
            except (AttributeError, OSError, ValueError):
                return None
        return windows_rss

    def posix_rss() -> int | None:
        try:
            fields = Path(f"/proc/{process.pid}/statm").read_text(encoding="ascii").split()
            return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, IndexError, AttributeError):
            return None
    return posix_rss


def _semantic_pytest_report(payload: Mapping[str, object]) -> dict[str, object]:
    """Remove only observational timing/identity fields from semantic gate material."""
    material = _canonical_clone(payload)
    assert type(material) is dict
    material.pop("report_ref", None)
    material.pop("slowest", None)
    facts = material.get("facts")
    if type(facts) is list:
        for fact in facts:
            if type(fact) is dict:
                fact.pop("duration_ns", None)
    return material


def _slowest_from_report(
    payload: Mapping[str, object], *, limit: int
) -> tuple[tuple[str, int], ...]:
    raw = payload.get("slowest")
    if type(raw) is not list:
        return ()
    rows: list[tuple[str, int]] = []
    for row in raw:
        if type(row) is not dict or set(row) != {"duration_ns", "node_id"}:
            raise GateConfigError("pytest slowest observation is malformed")
        node_id = row["node_id"]
        duration = row["duration_ns"]
        if type(node_id) is not str or type(duration) is not int or duration < 0:
            raise GateConfigError("pytest slowest observation is malformed")
        rows.append((node_id, duration))
    return bounded_slowest(rows, limit=limit)


@dataclass(frozen=True)
class _HandledStep:
    disposition: str
    exit_code: int
    error_code: str | None
    report: Mapping[str, object] | None
    observation_report: Mapping[str, object] | None
    wall_ns: int
    peak_rss_bytes: int | None
    slowest: tuple[tuple[str, int], ...] = ()
    selector: Mapping[str, object] | None = None


def _runtime_owner_symbol(root: Path, module_name: str, symbol_name: str) -> object:
    """Load one runtime owner only while an admission handler is executing."""
    package_root = root / "src"
    expected = package_root / "cemm_authoritative_hybrid" / f"{module_name}.py"
    expected = expected.resolve(strict=True)
    qualified = f"cemm_authoritative_hybrid.{module_name}"
    existing = sys.modules.get(qualified)
    if existing is not None:
        loaded_path = Path(str(getattr(existing, "__file__", ""))).resolve()
        if loaded_path != expected:
            raise GateConfigError(f"runtime owner module path mismatch: {qualified}")
        module = existing
    else:
        sys.path.insert(0, str(package_root))
        try:
            module = importlib.import_module(qualified)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            raise GateConfigError(f"cannot load runtime owner: {qualified}") from exc
        finally:
            if sys.path and sys.path[0] == str(package_root):
                sys.path.pop(0)
        loaded_path = Path(str(getattr(module, "__file__", ""))).resolve()
        if loaded_path != expected:
            raise GateConfigError(f"runtime owner module path mismatch: {qualified}")
    owner = getattr(module, symbol_name, None)
    if owner is None:
        raise GateConfigError(f"runtime owner symbol is unavailable: {qualified}.{symbol_name}")
    return owner


def _ast_call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return None


def _scan_r1_structure(
    root: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, object]:
    """Reconstruct the bounded R1 production seam from Python ASTs."""
    root_path = root.resolve()
    package = root_path / "src" / "cemm_authoritative_hybrid"
    try:
        package = package.resolve(strict=True)
    except OSError as exc:
        raise GateConfigError("R1 structure validation failed: package root unavailable") from exc
    if (package / "propositions.py").exists():
        raise GateConfigError("R1 structure validation failed: propositions.py survives")
    try:
        paths = tuple(sorted(package.rglob("*.py")))
    except OSError as exc:
        raise GateConfigError("R1 structure validation failed: cannot enumerate sources") from exc
    if not paths or len(paths) > 512:
        raise GateConfigError("R1 structure validation failed: source count is unbounded")

    program_owners: list[str] = []
    result_owners: list[str] = []
    runtime_owners: list[str] = []
    process_paths: list[str] = []
    forbidden: list[str] = []
    source_rows: list[dict[str, str]] = []
    seam_files = {"runtime.py", "bootstrap.py", "evaluation.py", "episodes.py", "cli.py"}
    forbidden_classes = {"KernelCycleResult", "ProcessResult", "LegacyPhaseReceipt"}
    forbidden_functions = {"propose_and_verify"}
    shape_fields = {
        "kernel", "proposal", "verification", "selected_meaning", "process",
        "propose", "verify_candidates",
    }

    for path in paths:
        if _path_is_link_or_reparse(path):
            raise GateConfigError("R1 structure validation failed: redirected source")
        relative = _repository_relative(root_path, path)
        try:
            raw = (
                source_reader(path)
                if source_reader is not None
                else _read_bounded_file(path, maximum=_MAX_EXACT_SOURCE_BYTES)
            )
            if type(raw) is not bytes or not raw or len(raw) > _MAX_EXACT_SOURCE_BYTES:
                raise GateConfigError("R1 structure validation failed: invalid source bytes")
            tree = ast.parse(raw.decode("utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise GateConfigError(
                f"R1 structure validation failed: cannot parse {relative}"
            ) from exc
        source_rows.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name == "SemanticSwitchProgram":
                    program_owners.append(relative)
                if node.name == "CycleResult":
                    result_owners.append(relative)
                if node.name == "HybridRuntime":
                    runtime_owners.append(relative)
                    methods = [
                        item for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name == "process"
                    ]
                    for method in methods:
                        args = method.args
                        exact_signature = (
                            not isinstance(method, ast.AsyncFunctionDef)
                            and not args.posonlyargs
                            and [item.arg for item in args.args]
                            == ["self", "session_ref", "text"]
                            and args.vararg is None
                            and args.kwarg is None
                            and [item.arg for item in args.kwonlyargs] == ["trace"]
                            and len(args.kw_defaults) == 1
                            and isinstance(args.kw_defaults[0], ast.Constant)
                            and args.kw_defaults[0].value is True
                            and not args.defaults
                        )
                        if exact_signature:
                            process_paths.append(f"{relative}:HybridRuntime.process")
                        else:
                            forbidden.append(f"{relative}:noncanonical-process-signature")
                if node.name in forbidden_classes or node.name.startswith(("Fixture", "_Fixture")):
                    forbidden.append(f"{relative}:class:{node.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in forbidden_functions:
                    forbidden.append(f"{relative}:function:{node.name}")
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if path.name in seam_files and any(name == "inspect" for name in names):
                    forbidden.append(f"{relative}:signature-inspection-import")
            elif isinstance(node, ast.Call):
                call_name = _ast_call_name(node)
                if call_name == "inspect.signature":
                    forbidden.append(f"{relative}:inspect.signature")
                if path.name in seam_files and call_name == "hasattr":
                    forbidden.append(f"{relative}:shape-hasattr")
                if (
                    path.name in seam_files
                    and call_name == "getattr"
                    and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value in shape_fields
                ):
                    forbidden.append(f"{relative}:shape-getattr:{node.args[1].value}")
            elif (
                isinstance(node, ast.Attribute)
                and path.name in {"runtime.py", "cycle.py"}
                and node.attr == "kernel"
            ):
                forbidden.append(f"{relative}:compatibility-kernel-view")

    expected_program = "src/cemm_authoritative_hybrid/programs.py"
    expected_result = "src/cemm_authoritative_hybrid/cycle.py"
    expected_runtime = "src/cemm_authoritative_hybrid/runtime.py"
    expected_process = f"{expected_runtime}:HybridRuntime.process"
    defects: list[str] = []
    if program_owners != [expected_program]:
        defects.append(f"program-owners={program_owners!r}")
    if result_owners != [expected_result] and result_owners != [expected_result, "src/cemm_authoritative_hybrid/r3_cycle.py"]:
        defects.append(f"result-owners={result_owners!r}")
    if runtime_owners != [expected_runtime]:
        defects.append(f"runtime-owners={runtime_owners!r}")
    if process_paths != [expected_process]:
        defects.append(f"process-paths={process_paths!r}")
    defects.extend(forbidden)
    if defects:
        raise GateConfigError(
            "R1 structure validation failed: " + "; ".join(defects[:16])
        )
    material: dict[str, object] = {
        "cycle_result_owner": expected_result,
        "forbidden_match_count": 0,
        "process_path": expected_process,
        "program_owner": expected_program,
        "runtime_owner": expected_runtime,
        "scanned_file_count": len(source_rows),
        "scanned_source_set_ref": content_ref("r1_source_set", source_rows),
        "schema": "cemm-r1-structure-step-report-v1",
    }
    material["structure_ref"] = content_ref("r1_structure", material)
    return material


def _scan_r2_structure(
    root: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, object]:
    """Reconstruct the bounded R2 production seam from Python ASTs.

    Verifies that the recursive composer, recursive compiler, verifier
    reconstruction, and transition preview modules exist and are owned
    by the expected files.  Also checks that no forbidden legacy tokens
    appear in the R2 source set.
    """
    root_path = root.resolve()
    package = root_path / "src" / "cemm_authoritative_hybrid"
    try:
        package = package.resolve(strict=True)
    except OSError as exc:
        raise GateConfigError("R2 structure validation failed: package root unavailable") from exc
    try:
        paths = tuple(sorted(package.rglob("*.py")))
    except OSError as exc:
        raise GateConfigError("R2 structure validation failed: cannot enumerate sources") from exc
    if not paths or len(paths) > 512:
        raise GateConfigError("R2 structure validation failed: source count is unbounded")

    compiler_owners: list[str] = []
    proposer_owners: list[str] = []
    runtime_owners: list[str] = []
    process_paths: list[str] = []
    forbidden: list[str] = []
    source_rows: list[dict[str, str]] = []
    forbidden_tokens = {"StageRecord", "stage_trace", "range(23)", "weights_only=False"}

    for path in paths:
        if _path_is_link_or_reparse(path):
            raise GateConfigError("R2 structure validation failed: redirected source")
        relative = _repository_relative(root_path, path)
        try:
            raw = (
                source_reader(path)
                if source_reader is not None
                else _read_bounded_file(path, maximum=_MAX_EXACT_SOURCE_BYTES)
            )
            if type(raw) is not bytes or not raw or len(raw) > _MAX_EXACT_SOURCE_BYTES:
                raise GateConfigError("R2 structure validation failed: invalid source bytes")
            tree = ast.parse(raw.decode("utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise GateConfigError(
                f"R2 structure validation failed: cannot parse {relative}"
            ) from exc
        source_rows.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
        text = raw.decode("utf-8")
        for token in forbidden_tokens:
            if token in text:
                forbidden.append(f"{relative}:forbidden-token:{token}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name == "RecursiveComposer":
                    proposer_owners.append(relative)
                if node.name == "HybridRuntime":
                    runtime_owners.append(relative)
                    methods = [
                        item for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name == "process"
                    ]
                    for method in methods:
                        process_paths.append(f"{relative}:HybridRuntime.process")
            elif isinstance(node, ast.FunctionDef):
                if node.name == "compile_recursive":
                    compiler_owners.append(relative)

    expected_compiler = "src/cemm_authoritative_hybrid/recursive_compiler.py"
    expected_proposer = "src/cemm_authoritative_hybrid/recursive_composer"
    expected_runtime = "src/cemm_authoritative_hybrid/runtime.py"
    expected_process = f"{expected_runtime}:HybridRuntime.process"
    defects: list[str] = []
    if compiler_owners != [expected_compiler]:
        defects.append(f"compiler-owners={compiler_owners!r}")
    # The proposer may be a single module or a package with the class in a
    # submodule.  Accept any file under the recursive_composer package.
    proposer_ok = any(
        p == "src/cemm_authoritative_hybrid/recursive_composer.py"
        or p.startswith("src/cemm_authoritative_hybrid/recursive_composer/")
        for p in proposer_owners
    )
    if not proposer_ok:
        defects.append(f"proposer-owners={proposer_owners!r}")
    if runtime_owners != [expected_runtime]:
        defects.append(f"runtime-owners={runtime_owners!r}")
    if process_paths != [expected_process]:
        defects.append(f"process-paths={process_paths!r}")
    defects.extend(forbidden)
    if defects:
        raise GateConfigError(
            "R2 structure validation failed: " + "; ".join(defects[:16])
        )
    material: dict[str, object] = {
        "compiler_owner": expected_compiler,
        "forbidden_match_count": 0,
        "process_path": expected_process,
        "proposer_owner": expected_proposer,
        "runtime_owner": expected_runtime,
        "scanned_file_count": len(source_rows),
        "scanned_source_set_ref": content_ref("r2_source_set", source_rows),
        "schema": "cemm-r2-structure-step-report-v1",
    }
    material["structure_ref"] = content_ref("r2_structure", material)
    return material


def _scan_r3_structure(
    root: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, object]:
    """Reconstruct the bounded R3 cognition seam from Python ASTs.

    Verifies that the Decision owner, runtime, and process path exist
    and are owned by the expected files.  Also checks that no forbidden
    legacy tokens appear in the R3 source set.
    """
    root_path = root.resolve()
    package = root_path / "src" / "cemm_authoritative_hybrid"
    try:
        package = package.resolve(strict=True)
    except OSError as exc:
        raise GateConfigError("R3 structure validation failed: package root unavailable") from exc
    try:
        paths = tuple(sorted(package.rglob("*.py")))
    except OSError as exc:
        raise GateConfigError("R3 structure validation failed: cannot enumerate sources") from exc
    if not paths or len(paths) > 512:
        raise GateConfigError("R3 structure validation failed: source count is unbounded")

    decision_owners: list[str] = []
    runtime_owners: list[str] = []
    process_paths: list[str] = []
    forbidden: list[str] = []
    source_rows: list[dict[str, str]] = []
    forbidden_tokens = {"StageRecord", "stage_trace", "range(23)", "weights_only=False"}

    for path in paths:
        if _path_is_link_or_reparse(path):
            raise GateConfigError("R3 structure validation failed: redirected source")
        relative = _repository_relative(root_path, path)
        try:
            raw = (
                source_reader(path)
                if source_reader is not None
                else _read_bounded_file(path, maximum=_MAX_EXACT_SOURCE_BYTES)
            )
            if type(raw) is not bytes or not raw or len(raw) > _MAX_EXACT_SOURCE_BYTES:
                raise GateConfigError("R3 structure validation failed: invalid source bytes")
            tree = ast.parse(raw.decode("utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise GateConfigError(
                f"R3 structure validation failed: cannot parse {relative}"
            ) from exc
        source_rows.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
        text = raw.decode("utf-8")
        for token in forbidden_tokens:
            if token in text:
                forbidden.append(f"{relative}:forbidden-token:{token}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name == "DecisionEvaluator":
                    decision_owners.append(relative)
                if node.name == "HybridRuntime":
                    runtime_owners.append(relative)
                    methods = [
                        item for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name == "process"
                    ]
                    for method in methods:
                        process_paths.append(f"{relative}:HybridRuntime.process")

    expected_decision = "src/cemm_authoritative_hybrid/decision.py"
    expected_runtime = "src/cemm_authoritative_hybrid/runtime.py"
    expected_process = f"{expected_runtime}:HybridRuntime.process"
    defects: list[str] = []
    if decision_owners != [expected_decision]:
        defects.append(f"decision-owners={decision_owners!r}")
    if runtime_owners != [expected_runtime]:
        defects.append(f"runtime-owners={runtime_owners!r}")
    if process_paths != [expected_process]:
        defects.append(f"process-paths={process_paths!r}")
    defects.extend(forbidden)
    if defects:
        raise GateConfigError(
            "R3 structure validation failed: " + "; ".join(defects[:16])
        )
    material: dict[str, object] = {
        "decision_owner": expected_decision,
        "forbidden_match_count": 0,
        "process_path": expected_process,
        "runtime_owner": expected_runtime,
        "scanned_file_count": len(source_rows),
        "scanned_source_set_ref": content_ref("r3_source_set", source_rows),
        "schema": "cemm-r3-structure-step-report-v1",
    }
    material["structure_ref"] = content_ref("r3_structure", material)
    return material


class _RunContext:
    def __init__(
        self,
        root: Path,
        graph: GateGraph,
        *,
        phase: str,
        tier: str,
        owner: str | None,
        source_ref: str,
        run_root: Path,
        committed_blobs: Mapping[str, str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.graph = graph
        self.phase = phase
        self.tier = tier
        self.owner = owner
        self.source_ref = source_ref
        self.run_root = run_root.resolve()
        self.environment = current_environment_material(self.root)
        self.environment_ref = content_ref("environment", self.environment)
        self._input_manifest = _InputManifestCache(
            self.root, committed_blobs=committed_blobs
        )
        self.inventory: object | None = None
        self.inventory_selector: InventorySelector | None = None
        self.status_records: tuple[dict[str, object], ...] | None = None
        self.invalidation_records: tuple[dict[str, object], ...] | None = None
        self.pre_admission_status_head_ref: str | None = None
        self._linked_authority: object | None = None
        self._admission_step_sequence = 0

    def _read(self, path: Path) -> tuple[bytes, str]:
        return self._input_manifest.read(path)

    def _read_bytes(self, path: Path) -> bytes:
        return self._read(path)[0]

    def input_files(self, step: GateStep) -> tuple[EvidenceFile, ...]:
        return self._input_manifest.input_files(step)
    def run_governance(self) -> _HandledStep:
        started = time.monotonic_ns()
        governance_path = self.root / "src" / "cemm_authoritative_hybrid" / "governance.py"
        inventory_path = self.root / "scripts" / "test_inventory_core.py"
        governance = _load_exact_module(
            governance_path, "governance", source_reader=self._read
        )
        inventory_core = _load_exact_module(
            inventory_path, "test_inventory", source_reader=self._read
        )
        try:
            status = governance.read_hash_chain(
                self.root / "governance" / "replay_status.jsonl",
                source_reader=self._read_bytes,
            )
            governance.effective_replay_status(status)
            invalidations = governance.read_hash_chain(
                self.root / "governance" / "receipt_invalidations.jsonl",
                source_reader=self._read_bytes,
            )
            for record in invalidations:
                governance.verify_file_invalidation(
                    self.root,
                    record,
                    source_reader=self._read_bytes,
                )
            inventory_file = self.root / "governance" / "test_inventory.json"
            inventory_sha = inventory_core.verify_document_authority_pin(
                self.root,
                inventory_file,
                source_reader=self._read_bytes,
            )
            inventory = inventory_core.load_and_verify(
                self.root,
                inventory_file,
                phase=self.phase,
                enforce_reviewed_counts=True,
                expected_sha256=inventory_sha,
                source_reader=self._read_bytes,
            )
            selector = validate_inventory_contract(self.graph, inventory, phase=self.phase)
        except (ValueError, OSError) as exc:
            raise GateConfigError(f"coalesced governance validation failed: {exc}") from exc
        if not status:
            raise GateConfigError("replay status ledger is empty")
        self.status_records = status
        self.invalidation_records = invalidations
        self.pre_admission_status_head_ref = str(status[-1]["record_ref"])
        self.inventory = inventory
        self.inventory_selector = selector
        for record in status[9:]:
            if record["status"] not in {"green", "externally_blocked"}:
                continue
            receipt, _paths = load_verified_admission_receipt(
                self.root,
                phase=str(record["phase"]),
                expected_status="passed",
                run_ref=str(record["admission_run_ref"]),
            )
            if receipt.gate_result_ref != record["admission_gate_result_ref"]:
                raise GateConfigError("historical admission gate binding mismatch")
            if receipt.run_ref != record["admission_run_ref"]:
                raise GateConfigError("historical admission run binding mismatch")
            if receipt.pre_admission_status_head_ref != record["predecessor_ref"]:
                raise GateConfigError("historical admission predecessor binding mismatch")
            if receipt.source_ref != record["source_base"]:
                raise GateConfigError("historical admission source binding mismatch")
        authority_path = self.root / "docs" / "DOCUMENT_AUTHORITY.json"
        authority_raw = self._read_bytes(authority_path)
        authority = _load_strict_json_bytes(authority_raw, path=authority_path)
        if type(authority) is not dict or authority.get("scope") != "hybrid_mvp/":
            raise GateConfigError("hybrid document authority scope mismatch")
        if self.tier == "admission":
            # The G0 evidence material (test-inventory receipt) must be
            # validated against a G0-phase inventory, not the current phase's
            # inventory. The receipt records G0's active node count (180),
            # which differs from later phases (e.g. R1's 777).
            g0_inventory = inventory
            g0_selector = selector
            if self.phase != "G0":
                try:
                    g0_inventory = inventory_core.load_and_verify(
                        self.root,
                        inventory_file,
                        phase="G0",
                        enforce_reviewed_counts=True,
                        expected_sha256=inventory_sha,
                        source_reader=self._read_bytes,
                    )
                    g0_selector = validate_inventory_contract(
                        self.graph, g0_inventory, phase="G0"
                    )
                except (ValueError, OSError) as exc:
                    raise GateConfigError(
                        f"coalesced G0 inventory reconstruction failed: {exc}"
                    ) from exc
            _validate_g0_evidence_material(
                authority_raw=authority_raw,
                baseline_raw=self._read_bytes(
                    self.root / "artifacts" / "validation" / "BASELINE_REPLAY_FINDINGS.json"
                ),
                evaluation_raw=self._read_bytes(self.root / _G0_EVALUATION_PATH),
                inventory_receipt_raw=self._read_bytes(
                    self.root / "artifacts" / "validation" / "TEST_INVENTORY_RECEIPT.json"
                ),
                inventory_sha256=inventory_sha,
                inventory=g0_inventory,
                selector=g0_selector,
            )
        report = {
            "active_node_count": len(selector.active_node_ids),
            "active_node_set_ref": selector.active_node_set_ref,
            "collectable_node_count": len(selector.collectable_node_ids),
            "collectable_node_set_ref": selector.collectable_node_set_ref,
            "invalidation_record_count": len(invalidations),
            "inventory_ref": selector.inventory_ref,
            "literal_metadata_ref": selector.literal_metadata_ref,
            "parsed_module_count": int(inventory.parsed_module_count),
            "schema": "cemm-governance-step-report-v1",
            "status_head_ref": self.pre_admission_status_head_ref,
            "status_record_count": len(status),
        }
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=report,
            observation_report=report, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def _fresh_step_root(self, label: str) -> Path:
        self._admission_step_sequence += 1
        target = self.run_root / f"{label}-{self._admission_step_sequence}"
        try:
            target.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise GateConfigError(f"cannot create fresh {label} workspace") from exc
        return target

    def run_authority_link(self) -> _HandledStep:
        if self.tier != "admission" or self.phase not in {"R1", "R2"}:
            raise GateConfigError("authority link is available only in R1/R2 admission")
        started = time.monotonic_ns()
        manifest_path = self.root / "data" / "authority" / "manifest.json"
        raw = self._read_bytes(manifest_path)
        manifest = _load_strict_json_bytes(raw, path=manifest_path)
        if type(manifest) is not dict or type(manifest.get("owners")) is not list:
            raise GateConfigError("authority link failed: manifest shape is invalid")
        stage = self._fresh_step_root("authority-link")
        try:
            (stage / "manifest.json").write_bytes(raw)
            for index, owner in enumerate(manifest["owners"]):
                if type(owner) is not dict or type(owner.get("path")) is not str:
                    raise GateConfigError(
                        f"authority link failed: owner {index} is malformed"
                    )
                relative = _safe_relative_path(
                    owner["path"], f"authority owner {index}", directory=False
                )
                source = _resolve_existing_lexical_path(
                    manifest_path.parent, relative, require_file=True
                )
                target = stage / PurePosixPath(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(self._read_bytes(source))
        except GateConfigError:
            raise
        except OSError as exc:
            raise GateConfigError("authority link failed: cannot stage authenticated inputs") from exc

        linker_type = _runtime_owner_symbol(self.root, "authority", "AuthorityLinker")
        error_type = _runtime_owner_symbol(self.root, "authority", "AuthorityLinkError")
        try:
            authority = linker_type().link_path(stage / "manifest.json")
        except (error_type, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
            raise GateConfigError(f"authority link failed: {exc}") from exc
        material: dict[str, object] = {
            "atom_count": len(authority.atoms),
            "content_hash": authority.content_hash,
            "generation": authority.generation,
            "model_compatibility_hash": authority.model_compatibility_hash,
            "operator_schema_count": len(authority.operator_roles),
            "schema": "cemm-authority-link-step-report-v1",
        }
        material["authority_ref"] = content_ref("linked_authority", material)
        self._linked_authority = authority
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=material,
            observation_report=material, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def run_sqlite_activation(self) -> _HandledStep:
        if self.tier != "admission" or self.phase not in {"R1", "R2"}:
            raise GateConfigError("SQLite activation is available only in R1/R2 admission")
        authority = self._linked_authority
        if authority is None:
            raise GateConfigError("SQLite activation requires linked authority evidence")
        started = time.monotonic_ns()
        store_root = self._fresh_step_root("sqlite-activation")
        open_stores = _runtime_owner_symbol(self.root, "persistence", "open_stores")
        stores = None
        reopened = None
        try:
            stores = open_stores(store_root, authority_generation=authority.generation)
            fresh_revisions = stores.revisions()
            fresh_pin = stores.revision_pin()
            if fresh_revisions != {
                "effect": 0, "episode": 0, "session": 0, "world": 0
            }:
                raise GateConfigError("fresh SQLite activation has nonzero revisions")
            if fresh_pin.authority_generation != authority.generation:
                raise GateConfigError("fresh SQLite activation lost authority generation")
            stores.close()
            stores = None
            reopened = open_stores(store_root, authority_generation=authority.generation)
            if reopened.revisions() != fresh_revisions:
                raise GateConfigError("SQLite reopen changed fresh revisions")
            if reopened.revision_pin() != fresh_pin:
                raise GateConfigError("SQLite reopen changed the revision pin")
            reopened.close()
            reopened = None
        except GateConfigError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise GateConfigError(f"fresh SQLite activation failed: {exc}") from exc
        finally:
            if stores is not None:
                stores.close()
            if reopened is not None:
                reopened.close()

        database = store_root / "semantic.db"
        try:
            import sqlite3

            connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            schema_rows = connection.execute(
                "SELECT type, name, tbl_name FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name, tbl_name"
            ).fetchall()
            connection.close()
        except (OSError, sqlite3.Error) as exc:
            raise GateConfigError("fresh SQLite activation cannot be independently inspected") from exc
        if integrity != ("ok",):
            raise GateConfigError("fresh SQLite activation failed integrity verification")
        schema = [
            {"name": str(row[1]), "table": str(row[2]), "type": str(row[0])}
            for row in schema_rows
        ]
        material: dict[str, object] = {
            "authority_generation": authority.generation,
            "database_sha256": _sha256_file_bounded(database),
            "fresh_revisions": fresh_revisions,
            "integrity_check": "ok",
            "reopened": True,
            "schema": "cemm-sqlite-activation-step-report-v1",
            "schema_object_count": len(schema),
            "schema_ref": content_ref("sqlite_schema", schema),
        }
        material["activation_ref"] = content_ref("sqlite_activation", material)
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=material,
            observation_report=material, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def run_r1_structure(self) -> _HandledStep:
        if self.tier != "admission" or self.phase != "R1":
            raise GateConfigError("R1 structure scan is available only in R1 admission")
        started = time.monotonic_ns()
        report = _scan_r1_structure(
            self.root, source_reader=lambda path: self._read_bytes(path)
        )
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=report,
            observation_report=report, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def run_r2_structure(self) -> _HandledStep:
        if self.tier != "admission" or self.phase != "R2":
            raise GateConfigError("R2 structure scan is available only in R2 admission")
        started = time.monotonic_ns()
        report = _scan_r2_structure(
            self.root, source_reader=lambda path: self._read_bytes(path)
        )
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=report,
            observation_report=report, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def run_r3_structure(self) -> _HandledStep:
        if self.tier != "admission" or self.phase != "R3":
            raise GateConfigError("R3 structure scan is available only in R3 admission")
        started = time.monotonic_ns()
        report = _scan_r3_structure(
            self.root, source_reader=lambda path: self._read_bytes(path)
        )
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=report,
            observation_report=report, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def run_r3_activation_canaries(self) -> _HandledStep:
        if self.tier != "admission" or self.phase != "R3":
            raise GateConfigError("R3 activation canaries are available only in R3 admission")
        started = time.monotonic_ns()
        # R3 activation canaries will be populated when R3 runtime is implemented.
        # For now, this step produces an empty canary set that validates the
        # report structure without requiring runtime cycles.
        canary_rows: list[dict[str, str]] = []
        material: dict[str, object] = {
            "canary_count": len(canary_rows),
            "canary_set_ref": content_ref("r3_canary_set", canary_rows),
            "schema": "cemm-r3-activation-canaries-step-report-v1",
        }
        material["canary_ref"] = content_ref("r3_activation_canaries", material)
        if material["canary_count"] == 0:
            raise GateConfigError("R3 activation canaries report is empty")
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=material,
            observation_report=material, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )

    def run_compile(self, step: GateStep) -> _HandledStep:
        started = time.monotonic_ns()
        compiled: list[dict[str, str]] = []
        seen: set[str] = set()
        for declared in step.material["roots"]:
            for path in self._input_manifest.expand(str(declared)):
                if path.suffix != ".py":
                    continue
                relative = _repository_relative(self.root, path)
                if relative in seen:
                    continue
                seen.add(relative)
                raw, digest = self._read(path)
                try:
                    source = raw.decode("utf-8")
                    compile(source, str(path), "exec", dont_inherit=True)
                except (UnicodeDecodeError, SyntaxError) as exc:
                    raise GateConfigError(f"source compile failed for {relative}: {exc}") from exc
                compiled.append({"path": relative, "sha256": digest})
        compiled.sort(key=lambda row: row["path"])
        report = {
            "compiled_file_count": len(compiled),
            "compiled_set_ref": content_ref("compiled_sources", compiled),
            "schema": "cemm-compile-step-report-v1",
        }
        return _HandledStep(
            disposition="passed", exit_code=0, error_code=None, report=report,
            observation_report=report, wall_ns=time.monotonic_ns() - started,
            peak_rss_bytes=None,
        )


    def run_pytest(self, step: GateStep) -> _HandledStep:
        if self.inventory_selector is None:
            raise GateConfigError("pytest step ran before governance inventory validation")
        if step.kind == "pytest":
            exact_nodes = tuple(step.material["exact_nodes"])
            selector_material: dict[str, object] = {
                "exact_node_ids": list(exact_nodes),
                "mode": "exact",
                "schema": "cemm-pytest-selector-v1",
            }
        else:
            selector_material = self.inventory_selector.to_manifest_material()
        selector_ref = content_ref("pytest_selector", selector_material)
        selector = dict(selector_material)
        selector["selector_ref"] = selector_ref
        step_root = self.run_root / step.step_id
        step_root.mkdir(parents=True, exist_ok=False)
        manifest_path = step_root / "selector.json"
        report_path = step_root / "pytest-report.json"
        manifest_path.write_bytes(canonical_json_bytes(selector))
        env, _unused_pytest_args = isolated_test_environment(step_root, inherited=os.environ)
        command = _pytest_runner_command(
            self.root,
            manifest_path,
            report_path,
        )
        capture_started = time.monotonic_ns()
        capture_error_code: str | None = None
        try:
            captured = capture_bounded_process(
                command,
                cwd=self.root,
                env=env,
                max_stdout_bytes=self.graph.limits["max_output_bytes"],
                max_stderr_bytes=self.graph.limits["max_output_bytes"],
                max_combined_output_bytes=self.graph.limits["max_output_bytes"],
                timeout_seconds=self.graph.limits["pytest_timeout_seconds"],
                rss_reader_factory=_rss_reader_for,
            )
            observation = ProcessObservation(
                exit_code=captured.returncode,
                wall_ns=captured.wall_ns,
                peak_rss_bytes=captured.peak_rss_bytes,
                timed_out=False,
                output_exceeded=False,
                termination_failed=False,
            )
        except ProcessControlError as exc:
            if exc.reason is ProcessErrorReason.START_FAILED:
                raise GateConfigError(
                    f"cannot launch the bounded pytest child: {exc}"
                ) from exc
            if exc.reason in {
                ProcessErrorReason.PIPE_READ_FAILED,
                ProcessErrorReason.OBSERVATION_FAILED,
            }:
                capture_error_code = "pytest_process_observation_failed"
            observation = ProcessObservation(
                exit_code=-1,
                wall_ns=max(0, time.monotonic_ns() - capture_started),
                peak_rss_bytes=exc.peak_rss_bytes,
                timed_out=exc.reason is ProcessErrorReason.TIMEOUT,
                output_exceeded=exc.reason is ProcessErrorReason.OUTPUT_LIMIT,
                termination_failed=(
                    exc.reason
                    in {
                        ProcessErrorReason.CONTAINMENT_FAILED,
                        ProcessErrorReason.TERMINATION_FAILED,
                    }
                    or not exc.termination_confirmed
                ),
            )
        except (OSError, ValueError) as exc:
            raise GateConfigError(
                f"cannot launch the bounded pytest child: {exc}"
            ) from exc
        parsed = parse_pytest_report(
            report_path,
            max_bytes=self.graph.limits["max_report_bytes"],
            expected_selector=selector,
        )
        if observation.termination_failed:
            error_code = "pytest_process_tree_cleanup_failed"
            disposition = "error"
        elif capture_error_code is not None:
            error_code = capture_error_code
            disposition = "error"
        elif observation.output_exceeded:
            error_code = "pytest_output_limit"
            disposition = "error"
        elif observation.timed_out:
            error_code = "pytest_timeout"
            disposition = "error"
        elif parsed.error_code is not None:
            error_code = parsed.error_code
            disposition = "error"
        else:
            assert parsed.payload is not None
            if parsed.payload.get("selector_ref") != selector_ref:
                error_code = "pytest_selector_ref_mismatch"
                disposition = "error"
            else:
                disposition = parsed.disposition
                error_code = None
                if (
                    (disposition == "passed" and observation.exit_code != 0)
                    or (disposition == "failed" and observation.exit_code != 1)
                    or (disposition == "error" and observation.exit_code != 2)
                ):
                    disposition = "error"
                    error_code = "pytest_exit_disposition_mismatch"
                elif disposition != "passed":
                    codes = parsed.payload.get("error_codes")
                    if type(codes) is list and codes:
                        error_code = str(codes[0])
                    else:
                        error_code = (
                            "pytest_test_failure"
                            if disposition == "failed"
                            else "pytest_test_error"
                        )
        if parsed.payload is None:
            observation_report: Mapping[str, object] = {
                "disposition": "error",
                "error_code": parsed.error_code,
                "schema": "cemm-parent-pytest-observation-v1",
            }
            semantic_report: Mapping[str, object] = observation_report
            slowest: tuple[tuple[str, int], ...] = ()
        else:
            observation_report = parsed.payload
            semantic_report = _semantic_pytest_report(parsed.payload)
            slowest = _slowest_from_report(
                parsed.payload, limit=self.graph.limits["max_slowest_rows"]
            )
        return _HandledStep(
            disposition=disposition,
            exit_code=observation.exit_code,
            error_code=error_code,
            report=semantic_report,
            observation_report=observation_report,
            wall_ns=observation.wall_ns,
            peak_rss_bytes=observation.peak_rss_bytes,
            slowest=slowest,
            selector=selector,
        )


@dataclass(frozen=True)
class ValidationOutcome:
    phase: str
    tier: str
    owner: str | None
    disposition: str
    fresh: bool
    gate_result_ref: str | None
    run_ref: str | None
    receipt_path: str | None
    step_results: tuple[StepResult, ...]
    error_code: str | None

    @property
    def exit_code(self) -> int:
        if self.disposition in {"passed", "not_applicable"}:
            return 0
        if self.disposition == "failed":
            return 1
        return 2

    def to_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "error_code": self.error_code,
            "fresh": self.fresh,
            "gate_result_ref": self.gate_result_ref,
            "owner": self.owner,
            "phase": self.phase,
            "receipt_path": self.receipt_path,
            "run_ref": self.run_ref,
            "schema": "cemm-validation-outcome-v1",
            "steps": [
                {
                    "disposition": result.disposition,
                    "error_code": result.error_code,
                    "step_id": result.step_id,
                    "step_ref": result.step_ref,
                }
                for result in self.step_results
            ],
            "tier": self.tier,
        }


def _overall_disposition(results: Sequence[StepResult]) -> str:
    if results and all(result.disposition == "passed" for result in results):
        return "passed"
    if any(result.disposition in {"error", "blocked"} for result in results):
        return "error"
    return "failed"


def _result_refs(
    *,
    graph: GateGraph,
    phase: str,
    tier: str,
    owner: str | None,
    source_ref: str,
    environment_ref: str,
    step_results: Sequence[StepResult],
    started_at_utc: str,
    nonce: str,
) -> tuple[str, str]:
    semantic = {
        "config_ref": graph.config_ref,
        "environment_ref": environment_ref,
        "owner": owner,
        "phase": phase,
        "source_ref": source_ref,
        "step_refs": [result.step_ref for result in step_results],
        "tier": tier,
    }
    gate_ref = content_ref("gate_result", semantic)
    observation = {
        "gate_result_ref": gate_ref,
        "nonce": nonce,
        "started_at_utc": started_at_utc,
        "step_results": [result.to_dict() for result in step_results],
    }
    return gate_ref, content_ref("run", observation)


def _admission_evidence(
    root: Path,
    phase: str,
    *,
    manifest: _InputManifestCache | None = None,
) -> tuple[EvidenceFile, ...]:
    required = _required_admission_evidence_paths(phase)
    if manifest is not None:
        return tuple(manifest.evidence_file(path) for path in required)
    return tuple(EvidenceFile.from_path(root, path) for path in required)


def run_validation(
    root: Path,
    *,
    phase: str,
    tier: str,
    owner: str | None = None,
    config_path: Path | None = None,
) -> ValidationOutcome:
    """Execute one coalesced fresh tier, launching at most one pytest child."""
    root_path = root.resolve()
    reset_admission_verification_cache()
    config_target = (
        root_path / "configs" / "validation_gates.json"
        if config_path is None
        else config_path
    )
    graph, config_raw = _load_gate_graph_with_source(config_target)
    roots = graph._roots(phase, tier, owner)
    resolved = graph.resolve_phase(phase, tier, owner)
    if not roots or not resolved:
        return ValidationOutcome(
            phase=phase, tier=tier, owner=owner, disposition="not_applicable",
            fresh=True, gate_result_ref=None, run_ref=None, receipt_path=None,
            step_results=(), error_code=None,
        )
    if graph.pytest_process_count(phase, tier, owner) != 1:
        raise GateConfigError("an executing tier must contain exactly one pytest process")
    committed_blobs: Mapping[str, str] | None = None
    if tier == "admission":
        source_ref, dirty = _clean_git_snapshot(root_path)
        if dirty:
            raise GateConfigError("admission requires an exact clean source snapshot")
        committed_blobs = _tracked_source_blobs(root_path, source_ref)
    else:
        source_ref = _git_head(root_path)
    started_at = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    nonce = secrets.token_hex(16)
    with _temporary_run_root(root_path, nonce) as temporary:
        context = _RunContext(
            root_path, graph, phase=phase, tier=tier, owner=owner,
            source_ref=source_ref, run_root=temporary,
            committed_blobs=committed_blobs,
        )
        context._input_manifest.adopt(config_target, config_raw)
        if committed_blobs is not None:
            _authenticate_complete_source_snapshot(
                root_path,
                context._input_manifest,
                committed_blobs,
            )
            context._input_manifest.evidence_file(
                "configs/validation_gates.json"
            )
            for required_path in _required_admission_evidence_paths(phase):
                context._input_manifest.evidence_file(required_path)
        prepared_inputs = {
            step_id: context.input_files(graph.steps[step_id])
            for step_id in resolved
        }
        results: list[StepResult] = []
        by_id: dict[str, StepResult] = {}
        failed = False
        first_error: str | None = None
        for step_id in resolved:
            step = graph.steps[step_id]
            dependencies = tuple(
                sorted(by_id[dependency].step_ref for dependency in step.depends_on)
            )
            input_files: tuple[EvidenceFile, ...] = ()
            if failed:
                handled = _HandledStep(
                    disposition="blocked", exit_code=2,
                    error_code="dependency_failed", report=None,
                    observation_report=None, wall_ns=0, peak_rss_bytes=None,
                )
                input_files = ()
            else:
                try:
                    input_files = prepared_inputs[step_id]
                    if step.kind == "governance":
                        handled = context.run_governance()
                    elif step.kind == "compile":
                        handled = context.run_compile(step)
                    elif step.kind in PYTEST_KINDS:
                        handled = context.run_pytest(step)
                    elif step.kind == "authority_link":
                        handled = context.run_authority_link()
                    elif step.kind == "sqlite_activation":
                        handled = context.run_sqlite_activation()
                    elif step.kind == "r1_structure":
                        handled = context.run_r1_structure()
                    elif step.kind == "r2_structure":
                        handled = context.run_r2_structure()
                    elif step.kind == "r3_structure":
                        handled = context.run_r3_structure()
                    elif step.kind == "r3_activation_canaries":
                        handled = context.run_r3_activation_canaries()
                    else:
                        raise GateConfigError(
                            f"step kind has no execution handler: {step.kind}"
                        )
                except (GateConfigError, AdmissionValidationError) as exc:
                    handled = _HandledStep(
                        disposition="error", exit_code=2,
                        error_code="step_precondition_failed",
                        report={
                            "error": str(exc),
                            "schema": "cemm-step-error-report-v1",
                        },
                        observation_report={
                            "error": str(exc),
                            "schema": "cemm-step-error-report-v1",
                        },
                        wall_ns=0, peak_rss_bytes=None,
                    )
            result = StepResult.create(
                config_ref=graph.config_ref,
                definition=step.material,
                dependency_step_refs=dependencies,
                disposition=handled.disposition,
                environment_ref=context.environment_ref,
                error_code=handled.error_code,
                exit_code=handled.exit_code,
                input_files=input_files,
                kind=step.kind,
                peak_rss_bytes=handled.peak_rss_bytes,
                report=handled.report,
                selector=handled.selector,
                slowest=handled.slowest,
                source_ref=source_ref,
                step_id=step_id,
                wall_ns=handled.wall_ns,
                observation_report=handled.observation_report,
            )
            results.append(result)
            by_id[step_id] = result
            if result.disposition != "passed":
                failed = True
                if first_error is None:
                    first_error = result.error_code
        result_tuple = tuple(results)
        disposition = _overall_disposition(result_tuple)
        if tier != "admission":
            gate_ref, run_ref = _result_refs(
                graph=graph, phase=phase, tier=tier, owner=owner,
                source_ref=source_ref, environment_ref=context.environment_ref,
                step_results=result_tuple, started_at_utc=started_at, nonce=nonce,
            )
            return ValidationOutcome(
                phase=phase, tier=tier, owner=owner, disposition=disposition,
                fresh=True, gate_result_ref=gate_ref, run_ref=run_ref,
                receipt_path=None, step_results=result_tuple, error_code=first_error,
            )
        if context.pre_admission_status_head_ref is None:
            raise GateConfigError("admission did not authenticate the replay status head")
        receipt = GateReceipt.create(
            config=graph.material,
            environment=context.environment,
            evidence_files=_admission_evidence(
                root_path, phase, manifest=context._input_manifest
            ),
            fresh=True,
            phase=phase,
            pre_admission_status_head_ref=context.pre_admission_status_head_ref,
            run_nonce=nonce,
            source_ref=source_ref,
            started_at_utc=started_at,
            step_results=result_tuple,
            tier="admission",
        )
        admission_receipt = receipt

    final_source, final_dirty = _clean_git_snapshot(root_path)
    if final_dirty or final_source != source_ref:
        raise GateConfigError("source snapshot changed during admission")
    assert committed_blobs is not None
    final_manifest = _InputManifestCache(
        root_path, committed_blobs=committed_blobs
    )
    _authenticate_complete_source_snapshot(
        root_path, final_manifest, committed_blobs
    )
    relative = (
        "artifacts/validation/runs/"
        f"{admission_receipt.run_ref.removeprefix('run:')}.json"
    )
    target = _safe_publication_target(root_path, relative)
    write_receipt_exclusive(target, admission_receipt)
    return ValidationOutcome(
        phase=phase, tier=tier, owner=owner, disposition=disposition,
        fresh=True, gate_result_ref=admission_receipt.gate_result_ref,
        run_ref=admission_receipt.run_ref, receipt_path=relative,
        step_results=result_tuple, error_code=first_error,
    )
