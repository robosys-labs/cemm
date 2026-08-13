#!/usr/bin/env python3
"""Audit the R5 test hard cut without collecting or importing test modules."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import stat
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "governance" / "test_inventory.json"
INVENTORY_SHA256 = "7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_PYTHON_FILES = 10_000
MAX_AGGREGATE_SOURCE_BYTES = 128 * 1024 * 1024
MAX_TRAVERSED_ENTRIES = 20_000
REPLAY_PHASES = ("G0", "R1", "R2", "R3", "R4")
REVIEWED_CARRIER_PATH = "tests/test_six_phase_runtime.py"
REVIEWED_CARRIER_NODE = (
    "tests/test_six_phase_runtime.py::"
    "test_runtime_receipts_bind_exact_orientation_content_ref"
)
REVIEWED_CARRIER_ASSERTION = (
    "assertion:r1-slice-b-runtime-receipts-bind-orientation-content"
)
REVIEWED_CARRIER_AST_SHA256 = (
    "de2d0674187ce4a825f06888e73441f3c55a30754f63c3c30121147633fb1f16"
)

sys.path.insert(0, str(ROOT / "scripts"))
from test_inventory_core import InventoryError, load_and_verify  # noqa: E402


FORBIDDEN_SUPPORT_MODULES = (
    "legacy_propositions",
    "legacy_runtime_fixtures",
)
COMPATIBILITY_FIXTURES = frozenset(
    {"runtime_factory", "verified_observation_program"}
)
COMPATIBILITY_CONSTANTS = frozenset({"SIX_PHASES"})
DELETION_CANDIDATES = (
    "tests/legacy_propositions.py",
    "tests/legacy_runtime_fixtures.py",
    "tests/test_artifact_security.py",
    "tests/test_model_reproducibility.py",
    "tests/test_neural_realizer_weight_use.py",
    "tests/test_training_isolation.py",
    "tests/test_calibration.py",
    "tests/test_neural_weight_use.py",
    "tests/test_production_proposer_cutover.py",
    "tests/test_cognitive_loop_e2e.py",
    "tests/test_epistemic_admission.py",
    "tests/test_inference_bounds.py",
    "tests/test_learning_distinctions.py",
    "tests/test_query_engine.py",
    "tests/test_recursive_inference.py",
    "tests/test_restart_e2e.py",
    "tests/test_safety_and_contracts.py",
    "tests/test_synonym_acquisition.py",
    "tests/test_response_meaning.py",
)


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bounded_bytes(path: Path, limit: int) -> bytes:
    try:
        if _is_link_or_reparse(path):
            raise ValueError(f"untrusted redirected path: {path}")
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"source is not a regular file: {path}")
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if len(data) > limit:
        raise ValueError(f"source grew while reading or exceeds byte bound: {path}")
    before_identity = (before.st_dev, before.st_ino, before.st_size)
    after_identity = (after.st_dev, after.st_ino, after.st_size)
    if before_identity != after_identity:
        raise ValueError(f"source changed while reading: {path}")
    if len(data) != after.st_size:
        raise ValueError(f"short read or source changed while reading: {path}")
    return data


def _is_link_or_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect trusted path: {path}") from exc
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def _trusted_path(root: Path, path: Path) -> Path:
    root_absolute = root.absolute()
    path_absolute = path.absolute()
    try:
        relative = path_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise ValueError(f"path escapes audit root: {path}") from exc
    anchor = Path(root_absolute.anchor)
    current = anchor
    for part in root_absolute.parts[1:]:
        current = current / part
        if _is_link_or_reparse(current):
            raise ValueError(f"untrusted redirected audit root: {root}")
    resolved_root = root_absolute.resolve(strict=True)
    if resolved_root != root_absolute:
        raise ValueError(f"untrusted redirected audit root: {root}")
    current = root_absolute
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise ValueError(
                f"untrusted redirected path: {relative.as_posix()}"
            )
    resolved = path_absolute.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"resolved path escapes audit root: {relative.as_posix()}") from exc
    if resolved != path_absolute:
        raise ValueError(f"untrusted redirected path: {relative.as_posix()}")
    return path_absolute


def _strict_json(path: Path) -> object:
    raw = _bounded_bytes(path, MAX_CONFIG_BYTES)
    try:
        return json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid strict JSON {path}: {exc}") from exc


def _python_paths(root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    aggregate_bytes = 0
    traversed = 0
    for relative in ("tests", "scripts", "src"):
        base = _trusted_path(root, root / relative)
        if not base.is_dir():
            raise ValueError(f"missing source root: {base}")
        pending = [base]
        while pending:
            directory = pending.pop()
            try:
                entries = sorted(directory.iterdir(), key=lambda item: item.name)
            except OSError as exc:
                raise ValueError(f"cannot enumerate source root: {directory}") from exc
            for entry in entries:
                traversed += 1
                if traversed > MAX_TRAVERSED_ENTRIES:
                    raise ValueError("source traversal entry bound exceeded")
                trusted = _trusted_path(root, entry)
                if trusted.is_dir():
                    pending.append(trusted)
                elif trusted.is_file() and trusted.suffix == ".py":
                    paths.append(trusted)
                    if len(paths) > MAX_PYTHON_FILES:
                        raise ValueError("Python source file count bound exceeded")
                    aggregate_bytes += trusted.stat().st_size
                    if aggregate_bytes > MAX_AGGREGATE_SOURCE_BYTES:
                        raise ValueError("aggregate source byte bound exceeded")
    return tuple(sorted(paths))


def _tree(path: Path, raw: bytes | None = None) -> ast.Module:
    if raw is None:
        raw = _bounded_bytes(path, MAX_SOURCE_BYTES)
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"source is not UTF-8: {path}") from exc
    return ast.parse(source, filename=str(path))


def _support_reference_findings(
    root: Path,
    python_paths: tuple[Path, ...] | None = None,
) -> tuple[str, ...]:
    findings: set[str] = set()
    auditor = Path(__file__).resolve()
    for module in FORBIDDEN_SUPPORT_MODULES:
        support = root / "tests" / f"{module}.py"
        if support.exists():
            findings.add(f"forbidden_support_exists:{support.relative_to(root).as_posix()}")
    sources: list[tuple[Path, bytes]] = []
    aggregate_bytes = 0
    for path in python_paths if python_paths is not None else _python_paths(root):
        raw = _bounded_bytes(path, MAX_SOURCE_BYTES)
        aggregate_bytes += len(raw)
        if aggregate_bytes > MAX_AGGREGATE_SOURCE_BYTES:
            raise ValueError("aggregate source byte bound exceeded during read")
        sources.append((path, raw))
    for path, raw in sources:
        if path.resolve() == auditor:
            continue
        relative = path.relative_to(root).as_posix()
        tree = _tree(path, raw)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for module in alias.name.split("."):
                        if module in FORBIDDEN_SUPPORT_MODULES:
                            findings.add(
                                f"forbidden_support_import:{relative}:{module}"
                            )
            elif isinstance(node, ast.ImportFrom):
                for module in (node.module or "").split("."):
                    if module in FORBIDDEN_SUPPORT_MODULES:
                        findings.add(
                            f"forbidden_support_import:{relative}:{module}"
                        )
                for alias in node.names:
                    imported = alias.name.rsplit(".", 1)[-1]
                    if imported in FORBIDDEN_SUPPORT_MODULES:
                        findings.add(
                            f"forbidden_support_import:{relative}:{imported}"
                        )
            elif isinstance(node, ast.Call):
                for argument in (*node.args, *node.keywords):
                    value = argument.value if isinstance(argument, ast.keyword) else argument
                    if isinstance(value, ast.Constant) and value.value in FORBIDDEN_SUPPORT_MODULES:
                        findings.add(
                            f"forbidden_support_load:{relative}:{value.value}"
                        )
    return tuple(sorted(findings))


def _is_pytest_fixture(
    value: ast.expr,
    pytest_names: frozenset[str],
    fixture_names: frozenset[str],
) -> bool:
    return (
        (isinstance(value, ast.Name) and value.id in fixture_names)
        or (
            isinstance(value, ast.Attribute)
            and value.attr == "fixture"
            and isinstance(value.value, ast.Name)
            and value.value.id in pytest_names
        )
    )


def _fixture_export_name(
    value: ast.expr,
    default: str,
    *,
    pytest_names: frozenset[str],
    fixture_names: frozenset[str],
) -> str | None:
    registration: ast.Call | None = None
    if isinstance(value, ast.Call) and _is_pytest_fixture(
        value.func, pytest_names, fixture_names
    ):
        registration = value
    elif (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Call)
        and _is_pytest_fixture(value.func.func, pytest_names, fixture_names)
    ):
        registration = value.func
    if registration is None:
        return None
    for keyword in registration.keywords:
        if keyword.arg is None:
            return "<dynamic>"
        if (
            keyword.arg == "name"
            and isinstance(keyword.value, ast.Constant)
            and type(keyword.value.value) is str
        ):
            return keyword.value.value
        if keyword.arg == "name":
            return "<dynamic>"
    return default


def _module_statements(body: Iterable[ast.stmt]) -> tuple[ast.stmt, ...]:
    statements: list[ast.stmt] = []
    pending = list(reversed(tuple(body)))
    while pending:
        node = pending.pop()
        statements.append(node)
        nested: list[ast.stmt] = []
        if isinstance(node, ast.If):
            nested.extend(node.body)
            nested.extend(node.orelse)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            nested.extend(node.body)
            nested.extend(node.orelse)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            nested.extend(node.body)
        elif isinstance(node, (ast.Try, ast.TryStar)):
            nested.extend(node.body)
            for handler in node.handlers:
                nested.extend(handler.body)
            nested.extend(node.orelse)
            nested.extend(node.finalbody)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                nested.extend(case.body)
        pending.extend(reversed(nested))
    return tuple(statements)


def _compatibility_fixture_findings(root: Path) -> tuple[str, ...]:
    path = root / "tests" / "conftest.py"
    tree = _tree(path)
    findings: set[str] = set()
    statements = _module_statements(tree.body)
    pytest_names = frozenset(
        alias.asname or alias.name
        for node in statements
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "pytest"
    )
    fixture_names = frozenset(
        alias.asname or alias.name
        for node in statements
        if isinstance(node, ast.ImportFrom) and node.module == "pytest"
        for alias in node.names
        if alias.name == "fixture"
    )
    for node in statements:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in COMPATIBILITY_FIXTURES:
                findings.add(f"compatibility_fixture:{node.name}")
            for decorator in node.decorator_list:
                exported = _fixture_export_name(
                    decorator,
                    node.name,
                    pytest_names=pytest_names,
                    fixture_names=fixture_names,
                )
                if exported in COMPATIBILITY_FIXTURES:
                    findings.add(f"compatibility_fixture:{exported}")
                elif exported == "<dynamic>":
                    findings.add(f"dynamic_fixture_name:{node.name}")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: Iterable[ast.expr]
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            value = node.value
            for target in targets:
                if isinstance(target, ast.Name):
                    if target.id in COMPATIBILITY_CONSTANTS:
                        findings.add(f"compatibility_constant:{target.id}")
                    if (
                        target.id in COMPATIBILITY_FIXTURES
                        and _fixture_export_name(
                            value,
                            target.id,
                            pytest_names=pytest_names,
                            fixture_names=fixture_names,
                        )
                        is not None
                    ):
                        findings.add(f"compatibility_fixture:{target.id}")
                    exported = _fixture_export_name(
                        value,
                        target.id,
                        pytest_names=pytest_names,
                        fixture_names=fixture_names,
                    )
                    if exported in COMPATIBILITY_FIXTURES:
                        findings.add(f"compatibility_fixture:{exported}")
                    elif exported == "<dynamic>":
                        findings.add(f"dynamic_fixture_name:{target.id}")
        elif isinstance(node, ast.Expr):
            exported = _fixture_export_name(
                node.value,
                "",
                pytest_names=pytest_names,
                fixture_names=fixture_names,
            )
            if exported in COMPATIBILITY_FIXTURES:
                findings.add(f"compatibility_fixture:{exported}")
            elif exported == "<dynamic>":
                findings.add("dynamic_fixture_name:<expression>")
    return tuple(sorted(findings))


def _carrier_findings(root: Path) -> tuple[str, ...]:
    path = root / REVIEWED_CARRIER_PATH
    try:
        _trusted_path(root, path)
        if not path.is_file():
            return (f"lineage_carrier_missing:{REVIEWED_CARRIER_PATH}",)
        tree = _tree(path)
    except (OSError, SyntaxError, ValueError) as exc:
        return (f"lineage_carrier_invalid:{type(exc).__name__}:{exc}",)
    findings: set[str] = set()
    if (
        len(tree.body) != 4
        or not isinstance(tree.body[0], ast.Expr)
        or not isinstance(tree.body[0].value, ast.Constant)
        or tree.body[0].value.value
        != "Temporary non-executable lineage evidence pending inventory migration."
        or not isinstance(tree.body[1], ast.Assign)
        or not isinstance(tree.body[2], ast.FunctionDef)
        or not isinstance(tree.body[3], ast.Assign)
    ):
        findings.add("lineage_carrier_has_extra_content")
    if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)):
        findings.add("lineage_carrier_has_import")
    test_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__test__" for target in node.targets)
    ]
    if len(test_assignments) != 1 or not (
        isinstance(test_assignments[0].value, ast.Constant)
        and test_assignments[0].value.value is False
    ):
        findings.add("lineage_carrier_is_collectable")
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len(functions) != 1 or functions[0].name != REVIEWED_CARRIER_NODE.rsplit("::", 1)[1]:
        findings.add("lineage_carrier_function_set_mismatch")
    elif (
        isinstance(functions[0], ast.AsyncFunctionDef)
        or functions[0].decorator_list
        or functions[0].args.posonlyargs
        or functions[0].args.args
        or functions[0].args.kwonlyargs
        or functions[0].args.vararg is not None
        or functions[0].args.kwarg is not None
        or len(functions[0].body) != 2
        or not isinstance(functions[0].body[0], ast.Expr)
        or not isinstance(functions[0].body[0].value, ast.Constant)
        or not isinstance(functions[0].body[0].value.value, str)
        or functions[0].body[0].value.value
        != "Preserve one authenticated predecessor node; never execute this carrier."
        or not isinstance(functions[0].body[1], ast.Raise)
        or not isinstance(functions[0].body[1].exc, ast.Call)
        or not isinstance(functions[0].body[1].exc.func, ast.Name)
        or functions[0].body[1].exc.func.id != "AssertionError"
        or len(functions[0].body[1].exc.args) != 1
        or not isinstance(functions[0].body[1].exc.args[0], ast.Constant)
        or functions[0].body[1].exc.args[0].value
        != "lineage evidence is not executable"
        or functions[0].body[1].exc.keywords
        or functions[0].body[1].cause is not None
    ):
        findings.add("lineage_carrier_function_shape_mismatch")
    metadata_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__cemm_test_inventory__"
            for target in node.targets
        )
    ]
    if len(metadata_assignments) != 1:
        findings.add("lineage_carrier_metadata_missing")
    else:
        try:
            metadata = ast.literal_eval(metadata_assignments[0].value)
        except (TypeError, ValueError):
            metadata = None
        expected_keys = {
            "activation_phase",
            "assertion_ref",
            "diagnostic_role",
            "introduced_by_task",
            "owner_ref",
            "source_ast_sha256",
        }
        if (
            not isinstance(metadata, dict)
            or set(metadata) != {REVIEWED_CARRIER_NODE}
            or not isinstance(metadata[REVIEWED_CARRIER_NODE], dict)
            or set(metadata[REVIEWED_CARRIER_NODE]) != expected_keys
            or metadata[REVIEWED_CARRIER_NODE]["activation_phase"] != "R1"
            or metadata[REVIEWED_CARRIER_NODE]["assertion_ref"]
            != REVIEWED_CARRIER_ASSERTION
            or metadata[REVIEWED_CARRIER_NODE]["diagnostic_role"] != "owner"
            or metadata[REVIEWED_CARRIER_NODE]["introduced_by_task"] != "R1-Slice-B"
            or metadata[REVIEWED_CARRIER_NODE]["owner_ref"] != "runtime-path"
            or metadata[REVIEWED_CARRIER_NODE]["source_ast_sha256"]
            != REVIEWED_CARRIER_AST_SHA256
        ):
            findings.add("lineage_carrier_metadata_mismatch")
    return tuple(sorted(findings))


def _nonfrozen_predecessor_findings(result: object) -> tuple[str, ...]:
    frozen_nodes = {
        node_id
        for record in result.source_tests.values()
        for node_id in record.case_node_ids
    }
    findings: set[str] = set()
    deleted = set(DELETION_CANDIDATES)
    for record in result.later_nodes.values():
        predecessor = record.supersedes_node_id
        if predecessor is None or predecessor in frozen_nodes:
            continue
        predecessor_path = predecessor.split("::", 1)[0]
        if predecessor == REVIEWED_CARRIER_NODE:
            continue
        if predecessor_path in deleted:
            findings.add(
                f"deleted_nonfrozen_lineage_predecessor:{predecessor}:{record.node_id}"
            )
    return tuple(sorted(findings))


def _selector_step_names(config: dict[str, object]) -> tuple[str, ...]:
    phases = config.get("phases")
    if not isinstance(phases, dict) or not isinstance(phases.get("R5"), dict):
        raise ValueError("validation gates have no exact R5 phase object")
    r5 = phases["R5"]
    assert isinstance(r5, dict)
    names: list[str] = []
    for key in ("admission", "phase"):
        value = r5.get(key)
        if not isinstance(value, list) or any(type(item) is not str for item in value):
            raise ValueError(f"R5 {key} selectors are not an exact string array")
        names.extend(value)
    owners = r5.get("owners")
    if not isinstance(owners, dict):
        raise ValueError("R5 owners are not an exact object")
    for owner, value in owners.items():
        if type(owner) is not str or not isinstance(value, list) or any(
            type(item) is not str for item in value
        ):
            raise ValueError("R5 owner selectors are malformed")
        names.extend(value)
    return tuple(sorted(set(names)))


def _gate_input_findings(config: dict[str, object]) -> tuple[str, ...]:
    steps = config.get("steps")
    if not isinstance(steps, dict):
        raise ValueError("validation gates have no exact steps object")
    retired = set(DELETION_CANDIDATES)
    findings: set[str] = set()
    for step_name, step in steps.items():
        if type(step_name) is not str or not isinstance(step, dict):
            raise ValueError("validation gate step is malformed")
        inputs = step.get("inputs", [])
        if not isinstance(inputs, list) or any(type(item) is not str for item in inputs):
            raise ValueError(f"validation gate inputs are malformed: {step_name}")
        for input_path in inputs:
            if input_path in retired:
                findings.add(f"retired_gate_input:{step_name}:{input_path}")
    return tuple(sorted(findings))


def _selector_findings(root: Path, result: object) -> tuple[str, ...]:
    config = _strict_json(
        _trusted_path(root, root / "configs" / "validation_gates.json")
    )
    if not isinstance(config, dict) or not isinstance(config.get("steps"), dict):
        raise ValueError("validation gates have no exact steps object")
    steps = config["steps"]
    assert isinstance(steps, dict)
    forbidden = set(result.deferred_r5_assertion_refs) | set(
        result.retired_r5_assertion_refs
    )
    assertion_by_node = {
        record.source_test_ref: record.assertion_ref
        for record in result.source_tests.values()
    }
    assertion_by_node.update(
        {record.node_id: record.assertion_ref for record in result.later_nodes.values()}
    )
    findings: set[str] = set()
    for step_name in _selector_step_names(config):
        step = steps.get(step_name)
        if not isinstance(step, dict):
            raise ValueError(f"R5 selector step is missing: {step_name}")
        nodes = step.get("exact_nodes", [])
        if not isinstance(nodes, list) or any(type(node) is not str for node in nodes):
            raise ValueError(f"R5 selector exact_nodes are malformed: {step_name}")
        for node_id in nodes:
            assertion_ref = assertion_by_node.get(node_id)
            if assertion_ref in forbidden:
                findings.add(
                    f"disposed_assertion_selected:{step_name}:{node_id}:{assertion_ref}"
                )
    return tuple(sorted(findings))


def audit(root: Path = ROOT) -> tuple[str, ...]:
    findings: set[str] = set()
    try:
        root = root.absolute()
        _trusted_path(root, root)
        inventory_path = _trusted_path(
            root, root / "governance" / "test_inventory.json"
        )
        for relative in (
            "configs/validation_gates.json",
            "governance/r5_test_dispositions.json",
            "pyproject.toml",
            "schemas/r5_test_dispositions.schema.json",
            "scripts/r5_test_dispositions.py",
            "scripts/test_inventory_core.py",
            "tests/conftest.py",
        ):
            _trusted_path(root, root / relative)
        python_paths = _python_paths(root)
        candidate_set = set(DELETION_CANDIDATES)
        for phase in REPLAY_PHASES:
            replay = load_and_verify(
                root,
                inventory_path,
                phase=phase,
                enforce_reviewed_counts=True,
                expected_sha256=INVENTORY_SHA256,
            )
            for node_id in replay.active_node_ids:
                source_path = node_id.split("::", 1)[0]
                if source_path in candidate_set:
                    findings.add(f"active_{phase.lower()}_leaf:{node_id}")
        r5 = load_and_verify(
            root,
            inventory_path,
            phase="R5",
            enforce_reviewed_counts=True,
            expected_sha256=INVENTORY_SHA256,
        )
        config = _strict_json(
            _trusted_path(root, root / "configs" / "validation_gates.json")
        )
        if not isinstance(config, dict):
            raise ValueError("validation gates are not an exact object")
        findings.update(_gate_input_findings(config))
        findings.update(_selector_findings(root, r5))
        findings.update(_nonfrozen_predecessor_findings(r5))
        findings.update(_support_reference_findings(root, python_paths))
        findings.update(_compatibility_fixture_findings(root))
        findings.update(_carrier_findings(root))
        for relative in DELETION_CANDIDATES:
            if (root / relative).exists():
                findings.add(f"retired_candidate_exists:{relative}")
    except (InventoryError, OSError, SyntaxError, TypeError, ValueError) as exc:
        findings.add(f"audit_error:{type(exc).__name__}:{exc}")
    return tuple(sorted(findings))


def main() -> int:
    findings = audit(ROOT)
    report = {
        "schema": "cemm-r5-legacy-test-hard-cut-audit-v1",
        "phase": "R5",
        "status": "passed" if not findings else "failed",
        "finding_count": len(findings),
        "findings": list(findings),
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
