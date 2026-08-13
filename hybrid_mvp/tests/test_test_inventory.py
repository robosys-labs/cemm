from __future__ import annotations

import ast
import builtins
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "scripts" / "test_inventory_core.py"
CHECK_INVENTORY_PATH = ROOT / "scripts" / "check_test_inventory.py"
R5_DISPOSITIONS_PATH = ROOT / "scripts" / "r5_test_dispositions.py"
R5_DISPOSITIONS_SCHEMA_PATH = (
    ROOT / "schemas" / "r5_test_dispositions.schema.json"
)
BASELINE_SOURCE_REF = "58345240e67bf003e6ac7d5c68752e2e5eee4a7d"
PHASES = ("G0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")


def _load_core() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_cemm_test_inventory_core_for_tests",
        CORE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inventory core from {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_r5_dispositions() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_cemm_r5_test_dispositions_for_tests",
        R5_DISPOSITIONS_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"cannot load R5 test dispositions from {R5_DISPOSITIONS_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_check_inventory() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_cemm_check_test_inventory_for_tests",
        CHECK_INVENTORY_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inventory CLI from {CHECK_INVENTORY_PATH}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get("test_inventory_core")
    sys.modules["test_inventory_core"] = CORE
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("test_inventory_core", None)
        else:
            sys.modules["test_inventory_core"] = previous
    return module


_MODULES_BEFORE_CORE = frozenset(sys.modules)
CORE = _load_core()
_CORE_IMPORT_DELTA = frozenset(sys.modules) - _MODULES_BEFORE_CORE


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _content_ref(kind: str, value: object) -> str:
    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return f"{kind}:{digest[:24]}"


def _source_ast_sha256(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    assert len(matches) == 1
    material = ast.dump(
        matches[0],
        annotate_fields=True,
        include_attributes=False,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _source_ref(relative_path: str, function_name: str) -> str:
    return f"{relative_path}::{function_name}"


def _retained_record(
    relative_path: str,
    source: str,
    function_name: str,
    *,
    assertion_ref: str,
    activation_phase: str,
) -> dict[str, object]:
    node_id = _source_ref(relative_path, function_name)
    return {
        "source_test_ref": node_id,
        "classification": "retained",
        "activation_phase": activation_phase,
        "assertion_ref": assertion_ref,
        "source_ast_sha256": _source_ast_sha256(source, function_name),
        "case_node_ids": [node_id],
        "successor_node_ids": [],
    }


def _historical_record(
    relative_path: str,
    source: str,
    function_name: str,
    *,
    assertion_ref: str,
) -> dict[str, object]:
    node_id = _source_ref(relative_path, function_name)
    return {
        "source_test_ref": node_id,
        "classification": "historical",
        "activation_phase": None,
        "assertion_ref": assertion_ref,
        "source_ast_sha256": _source_ast_sha256(source, function_name),
        "case_node_ids": [node_id],
        "successor_node_ids": [],
        "historical_reason": "reviewed retired-path assertion",
    }



def _rewritten_record(
    relative_path: str,
    source: str,
    function_name: str,
    *,
    assertion_ref: str,
    replacement_phase: str,
    required_successor_node_ids: list[str],
) -> tuple[dict[str, object], str]:
    node_id = _source_ref(relative_path, function_name)
    required = sorted(required_successor_node_ids)
    obligation_material = {
        "predecessor_case_node_id": node_id,
        "required_successor_node_ids": required,
    }
    obligation_ref = _content_ref("rewrite_obligation", obligation_material)
    return (
        {
            "source_test_ref": node_id,
            "classification": "rewritten",
            "activation_phase": None,
            "assertion_ref": assertion_ref,
            "source_ast_sha256": _source_ast_sha256(source, function_name),
            "case_node_ids": [node_id],
            "successor_node_ids": required,
            "replacement_phase": replacement_phase,
            "rewrite_obligations": [
                {
                    "rewrite_ref": obligation_ref,
                    **obligation_material,
                }
            ],
        },
        obligation_ref,
    )


def _classification_counts(
    records: list[dict[str, object]],
) -> dict[str, int]:
    return {
        classification: sum(
            record["classification"] == classification for record in records
        )
        for classification in ("retained", "rewritten", "historical")
    }


def _inventory_payload(
    root: Path,
    records: list[dict[str, object]],
) -> dict[str, object]:
    records = sorted(records, key=lambda record: str(record["source_test_ref"]))
    source_paths = sorted(
        {str(record["source_test_ref"]).split("::", 1)[0] for record in records}
    )
    files = []
    for relative_path in source_paths:
        raw = (root / relative_path).read_bytes()
        files.append(
            {
                "path": relative_path,
                "baseline_blob_ref": f"sha256:{hashlib.sha256(raw).hexdigest()}",
            }
        )
    cases = sorted(
        case
        for record in records
        for case in record["case_node_ids"]  # type: ignore[index]
    )
    payload: dict[str, object] = {
        "schema": "cemm-hybrid-test-inventory-v1",
        "baseline_source_ref": BASELINE_SOURCE_REF,
        "file_count": len(files),
        "source_test_count": len(records),
        "case_count": len(cases),
        "classification_counts": _classification_counts(records),
        "files": files,
        "source_tests": records,
        "source_set_ref": _content_ref("source_set", records),
        "case_set_ref": _content_ref("case_set", cases),
    }
    payload["inventory_ref"] = _content_ref("test_inventory", payload)
    return payload


def _set_inventory_ref(payload: dict[str, object]) -> None:
    payload.pop("inventory_ref", None)
    payload["inventory_ref"] = _content_ref("test_inventory", payload)


def _write_inventory(root: Path, payload: dict[str, object]) -> Path:
    path = root / "governance" / "test_inventory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload) + b"\n")
    return path


def _write_frozen_module(
    root: Path,
    source: str,
    *,
    relative_path: str = "tests/test_frozen.py",
) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")
    return path


def _write_pytest_collection_contract(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """\
[tool.pytest.ini_options]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test*"]
python_classes = ["Test*"]
""",
        encoding="utf-8",
        newline="\n",
    )

def _new_project(
    tmp_path: Path,
    source: str,
    record_factory: Callable[[str], list[dict[str, object]]],
    *,
    name: str = "project",
) -> tuple[Path, Path, dict[str, object]]:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    _write_pytest_collection_contract(root)
    _write_frozen_module(root, source)
    records = record_factory(source)
    payload = _inventory_payload(root, records)
    return root, _write_inventory(root, payload), payload


def _later_metadata(
    *,
    assertion_ref: str,
    activation_phase: str,
    supersedes_node_id: str | None = None,
    contributes_to_rewrite_refs: list[str] | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "assertion_ref": assertion_ref,
        "activation_phase": activation_phase,
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
    }
    if supersedes_node_id is not None:
        metadata["supersedes_node_id"] = supersedes_node_id
    if contributes_to_rewrite_refs is not None:
        metadata["contributes_to_rewrite_refs"] = contributes_to_rewrite_refs
    return metadata


def _write_later_module(
    root: Path,
    entries: list[tuple[str, dict[str, object]]],
    *,
    relative_path: str = "tests/test_later.py",
) -> Path:
    functions = "\n\n".join(
        f"def {function_name}() -> None:\n    assert True"
        for function_name, _metadata in entries
    )
    node_metadata: dict[str, dict[str, object]] = {}
    for function_name, metadata in entries:
        node_id = _source_ref(relative_path, function_name)
        complete = dict(metadata)
        complete["source_ast_sha256"] = _source_ast_sha256(
            functions,
            function_name,
        )
        node_metadata[node_id] = complete
    lines = [functions, "", "", "__cemm_test_inventory__ = {"]
    for node_id, metadata in node_metadata.items():
        lines.append(f"    {node_id!r}: {metadata!r},")
    lines.append("}")
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def _verify(
    root: Path,
    inventory_path: Path,
    *,
    phase: str,
    parse_source: Callable[..., ast.AST] = ast.parse,
) -> Any:
    assert phase in PHASES
    return CORE.load_and_verify(
        root,
        inventory_path,
        phase=phase,
        enforce_reviewed_counts=False,
        parse_source=parse_source,
    )


def _write_r5_overlay(
    root: Path,
    inventory_payload: dict[str, object],
    rows: list[dict[str, object]],
) -> None:
    payload = {
        "schema": "cemm-r5-test-dispositions-v1",
        "phase": "R5",
        "inventory_ref": inventory_payload["inventory_ref"],
        "rows": rows,
    }
    (root / "governance" / "r5_test_dispositions.json").write_bytes(
        _canonical_bytes(payload) + b"\n"
    )


def _overlay_row(
    predecessor: str,
    assertion_ref: str,
    disposition: str,
    *,
    successor_node_ids: list[str] | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "predecessor_source_test_ref": predecessor,
        "assertion_ref": assertion_ref,
        "disposition": disposition,
    }
    if disposition == "successor":
        row["successor_node_ids"] = successor_node_ids or []
    elif disposition == "deferred":
        row["future_task_ref"] = "R5-Neural-Activation"
        row["future_owner_ref"] = "test-owner"
    else:
        row["retirement_reason"] = (
            "hybrid_mvp/AGENTS.md section 7 requires zero fallback paths in final "
            "release gates; preserving this requirement would reintroduce forbidden "
            "fallback behavior."
        )
    return row


def _one_retained_project(
    tmp_path: Path,
    *,
    activation_phase: str = "G0",
    name: str = "project",
) -> tuple[Path, Path, dict[str, object]]:
    source = "def test_frozen() -> None:\n    assert True\n"

    def records(text: str) -> list[dict[str, object]]:
        return [
            _retained_record(
                "tests/test_frozen.py",
                text,
                "test_frozen",
                assertion_ref="assertion:frozen",
                activation_phase=activation_phase,
            )
        ]

    return _new_project(tmp_path, source, records, name=name)


def test_reviewed_inventory_has_exact_predecessor_totals_and_g0_lifecycle() -> None:
    verified = CORE.load_and_verify(
        ROOT,
        ROOT / "governance" / "test_inventory.json",
        phase="G0",
        enforce_reviewed_counts=True,
    )

    classifications = [
        record.classification for record in verified.source_tests.values()
    ]
    assert verified.baseline_source_ref == BASELINE_SOURCE_REF
    assert len(classifications) == 632
    assert classifications.count("retained") == 609
    assert classifications.count("rewritten") == 10
    assert classifications.count("historical") == 13
    assert len(verified.deferred_rewrite_refs) == 10
    assert verified.due_rewrite_refs == ()

    non_executable_originals = {
        case_node_id
        for record in verified.source_tests.values()
        if record.classification in {"rewritten", "historical"}
        for case_node_id in record.case_node_ids
    }
    assert non_executable_originals.isdisjoint(verified.active_node_ids)



def test_literal_metadata_rejects_duplicate_node_keys(tmp_path: Path) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    path = _write_later_module(
        root,
        [
            (
                "test_later",
                _later_metadata(
                    assertion_ref="assertion:later",
                    activation_phase="G0",
                ),
            )
        ],
    )
    text = path.read_text(encoding="utf-8")
    metadata_line = next(
        line for line in text.splitlines() if "tests/test_later.py::test_later" in line
    )
    path.write_text(
        text.replace(metadata_line, metadata_line + "\n" + metadata_line),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(CORE.InventoryError, match="duplicate literal metadata"):
        _verify(root, inventory_path, phase="G0")

def test_strict_json_rejects_duplicate_object_keys(tmp_path: Path) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    raw = inventory_path.read_text(encoding="utf-8")
    inventory_path.write_text(
        raw.replace(
            '"schema":',
            '"schema":"duplicate","schema":',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(CORE.InventoryError, match="duplicate"):
        _verify(root, inventory_path, phase="G0")


def test_strict_json_rejects_non_finite_numbers(tmp_path: Path) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    raw = inventory_path.read_text(encoding="utf-8")
    inventory_path.write_text(
        raw.replace('"file_count":1', '"file_count":NaN', 1),
        encoding="utf-8",
    )

    with pytest.raises(CORE.InventoryError, match="finite|NaN"):
        _verify(root, inventory_path, phase="G0")


def test_inventory_recomputes_identity_sets_and_declared_counts(
    tmp_path: Path,
) -> None:
    root, inventory_path, payload = _one_retained_project(tmp_path)

    bad_count = copy.deepcopy(payload)
    bad_count["source_test_count"] = 2
    _set_inventory_ref(bad_count)
    _write_inventory(root, bad_count)
    with pytest.raises(CORE.InventoryError, match="source.*count|count"):
        _verify(root, inventory_path, phase="G0")

    bad_source_set = copy.deepcopy(payload)
    bad_source_set["source_set_ref"] = "source_set:" + "0" * 64
    _set_inventory_ref(bad_source_set)
    _write_inventory(root, bad_source_set)
    with pytest.raises(CORE.InventoryError, match="source.set|source_set"):
        _verify(root, inventory_path, phase="G0")

    bad_inventory_identity = copy.deepcopy(payload)
    bad_inventory_identity["baseline_source_ref"] = "0" * 40
    _write_inventory(root, bad_inventory_identity)
    with pytest.raises(CORE.InventoryError, match="inventory.*ref|identity"):
        _verify(root, inventory_path, phase="G0")

    _write_inventory(root, payload)
    with pytest.raises(CORE.InventoryError, match="authority pin|SHA-256"):
        CORE.load_and_verify(
            root,
            inventory_path,
            phase="G0",
            expected_sha256="0" * 64,
        )



def test_inventory_rejects_paths_that_escape_the_project_root(
    tmp_path: Path,
) -> None:
    root, inventory_path, payload = _one_retained_project(tmp_path)
    unsafe = copy.deepcopy(payload)
    unsafe["files"][0]["path"] = "../test_frozen.py"  # type: ignore[index]
    _set_inventory_ref(unsafe)
    _write_inventory(root, unsafe)

    with pytest.raises(CORE.InventoryError, match="path|relative"):
        _verify(root, inventory_path, phase="G0")


def test_frozen_ast_rejects_same_id_mutation_but_allows_unrelated_edits(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    frozen_path = root / "tests" / "test_frozen.py"

    frozen_path.write_text(
        "def test_frozen() -> None:\n    assert False\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(CORE.InventoryError, match="AST|digest|mutat"):
        _verify(root, inventory_path, phase="G0")

    frozen_path.write_text(
        "import math\n\nUNRELATED_HELPER = math.pi\n\n"
        "def test_frozen() -> None:\n    assert True\n",
        encoding="utf-8",
        newline="\n",
    )
    verified = _verify(root, inventory_path, phase="G0")
    assert verified.active_node_ids == ("tests/test_frozen.py::test_frozen",)


def test_g0_defers_rewrites_and_excludes_non_executable_originals(
    tmp_path: Path,
) -> None:
    source = (
        "def test_retained() -> None:\n    assert True\n\n"
        "def test_rewritten() -> None:\n    assert True\n\n"
        "def test_historical() -> None:\n    assert True\n"
    )
    future = "tests/test_future.py::test_replacement"
    obligation: dict[str, str] = {}

    def records(text: str) -> list[dict[str, object]]:
        rewritten, obligation_ref = _rewritten_record(
            "tests/test_frozen.py",
            text,
            "test_rewritten",
            assertion_ref="assertion:rewritten",
            replacement_phase="R2",
            required_successor_node_ids=[future],
        )
        obligation["ref"] = obligation_ref
        return [
            _retained_record(
                "tests/test_frozen.py",
                text,
                "test_retained",
                assertion_ref="assertion:retained",
                activation_phase="G0",
            ),
            rewritten,
            _historical_record(
                "tests/test_frozen.py",
                text,
                "test_historical",
                assertion_ref="assertion:historical",
            ),
        ]

    root, inventory_path, _payload = _new_project(tmp_path, source, records)
    verified = _verify(root, inventory_path, phase="G0")

    assert verified.active_node_ids == ("tests/test_frozen.py::test_retained",)
    assert verified.collectable_node_ids == (
        "tests/test_frozen.py::test_historical",
        "tests/test_frozen.py::test_retained",
        "tests/test_frozen.py::test_rewritten",
    )
    assert verified.collectable_node_set_ref == _content_ref(
        "collectable_test_nodes",
        list(verified.collectable_node_ids),
    )
    assert verified.deferred_rewrite_refs == (obligation["ref"],)
    assert "tests/test_frozen.py::test_rewritten" not in verified.active_node_ids
    assert "tests/test_frozen.py::test_historical" not in verified.active_node_ids

    with pytest.raises(CORE.InventoryError, match="successor|rewrite"):
        _verify(root, inventory_path, phase="R2")


def test_due_rewrite_requires_every_conjunctive_contributing_successor(
    tmp_path: Path,
) -> None:
    source = "def test_rewritten() -> None:\n    assert True\n"
    part_a = "tests/test_later.py::test_part_a"
    part_b = "tests/test_later.py::test_part_b"
    obligation: dict[str, str] = {}

    def records(text: str) -> list[dict[str, object]]:
        rewritten, obligation_ref = _rewritten_record(
            "tests/test_frozen.py",
            text,
            "test_rewritten",
            assertion_ref="assertion:conjunctive-rewrite",
            replacement_phase="R2",
            required_successor_node_ids=[part_a, part_b],
        )
        obligation["ref"] = obligation_ref
        return [rewritten]

    root, inventory_path, _payload = _new_project(tmp_path, source, records)
    contribution = [obligation["ref"]]
    _write_later_module(
        root,
        [
            (
                "test_part_a",
                _later_metadata(
                    assertion_ref="assertion:part-a",
                    activation_phase="R2",
                    contributes_to_rewrite_refs=contribution,
                ),
            )
        ],
    )
    with pytest.raises(CORE.InventoryError, match="test_part_b|successor"):
        _verify(root, inventory_path, phase="R2")

    _write_later_module(
        root,
        [
            (
                "test_part_a",
                _later_metadata(
                    assertion_ref="assertion:part-a",
                    activation_phase="R2",
                    contributes_to_rewrite_refs=contribution,
                ),
            ),
            (
                "test_part_b",
                _later_metadata(
                    assertion_ref="assertion:part-b",
                    activation_phase="R2",
                ),
            ),
        ],
    )
    with pytest.raises(CORE.InventoryError, match="contribut|rewrite"):
        _verify(root, inventory_path, phase="R2")

    _write_later_module(
        root,
        [
            (
                "test_part_a",
                _later_metadata(
                    assertion_ref="assertion:part-a",
                    activation_phase="R2",
                    contributes_to_rewrite_refs=contribution,
                ),
            ),
            (
                "test_part_b",
                _later_metadata(
                    assertion_ref="assertion:part-b",
                    activation_phase="R2",
                    contributes_to_rewrite_refs=contribution,
                ),
            ),
        ],
    )
    verified = _verify(root, inventory_path, phase="R2")
    assert verified.active_node_ids == (part_a, part_b)
    assert "tests/test_frozen.py::test_rewritten" not in verified.active_node_ids


def test_valid_new_id_supersession_selects_exactly_one_lineage_leaf(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(
        tmp_path,
        activation_phase="R1",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    successor = "tests/test_later.py::test_replacement"
    _write_later_module(
        root,
        [
            (
                "test_replacement",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R1",
                    supersedes_node_id=predecessor,
                ),
            )
        ],
    )

    verified = _verify(root, inventory_path, phase="R1")
    assert verified.active_node_ids == (successor,)
    assert predecessor not in verified.active_node_ids


def test_supersession_rejects_duplicate_leaves_and_cycles(tmp_path: Path) -> None:
    duplicate_root, duplicate_inventory, _payload = _one_retained_project(
        tmp_path,
        activation_phase="R1",
        name="duplicate",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    _write_later_module(
        duplicate_root,
        [
            (
                "test_replacement_a",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R1",
                    supersedes_node_id=predecessor,
                ),
            ),
            (
                "test_replacement_b",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R1",
                    supersedes_node_id=predecessor,
                ),
            ),
        ],
    )
    with pytest.raises(CORE.InventoryError, match="branch|duplicate|multiple|leaf"):
        _verify(duplicate_root, duplicate_inventory, phase="R1")

    cycle_root, cycle_inventory, _payload = _one_retained_project(
        tmp_path,
        activation_phase="R1",
        name="cycle",
    )
    node_a = "tests/test_later.py::test_cycle_a"
    node_b = "tests/test_later.py::test_cycle_b"
    _write_later_module(
        cycle_root,
        [
            (
                "test_cycle_a",
                _later_metadata(
                    assertion_ref="assertion:cycle",
                    activation_phase="R1",
                    supersedes_node_id=node_b,
                ),
            ),
            (
                "test_cycle_b",
                _later_metadata(
                    assertion_ref="assertion:cycle",
                    activation_phase="R1",
                    supersedes_node_id=node_a,
                ),
            ),
        ],
    )
    with pytest.raises(CORE.InventoryError, match="cycle|acyclic"):
        _verify(cycle_root, cycle_inventory, phase="R1")


def test_supersession_preserves_assertion_and_cannot_regress_phase(
    tmp_path: Path,
) -> None:
    assertion_root, assertion_inventory, _payload = _one_retained_project(
        tmp_path,
        activation_phase="R1",
        name="assertion",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    _write_later_module(
        assertion_root,
        [
            (
                "test_replacement",
                _later_metadata(
                    assertion_ref="assertion:different",
                    activation_phase="R1",
                    supersedes_node_id=predecessor,
                ),
            )
        ],
    )
    with pytest.raises(CORE.InventoryError, match="assertion"):
        _verify(assertion_root, assertion_inventory, phase="R1")

    phase_root, phase_inventory, _payload = _one_retained_project(
        tmp_path,
        activation_phase="R2",
        name="phase",
    )
    _write_later_module(
        phase_root,
        [
            (
                "test_replacement",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R1",
                    supersedes_node_id=predecessor,
                ),
            )
        ],
    )
    with pytest.raises(CORE.InventoryError, match="phase|regress"):
        _verify(phase_root, phase_inventory, phase="R2")


def test_custom_fixture_named_decorator_cannot_hide_later_test(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    relative_path = "tests/test_later.py"
    node_id = f"{relative_path}::test_visible"
    function_source = """\
class Passthrough:
    @staticmethod
    def fixture(function):
        return function

marker = Passthrough()

@marker.fixture
def test_visible() -> None:
    assert True
"""
    metadata = _later_metadata(
        assertion_ref="assertion:custom-fixture-name-is-not-pytest",
        activation_phase="G0",
    )
    metadata["source_ast_sha256"] = _source_ast_sha256(
        function_source,
        "test_visible",
    )
    source = (
        function_source
        + "\n__cemm_test_inventory__ = {\n"
        + f"    {node_id!r}: {metadata!r},\n"
        + "}\n"
    )
    _write_frozen_module(root, source, relative_path=relative_path)

    verified = _verify(root, inventory_path, phase="G0")

    assert node_id in verified.active_node_ids


def test_rebound_pytest_fixture_alias_cannot_hide_later_test(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    relative_path = "tests/test_later.py"
    node_id = f"{relative_path}::test_visible"
    function_source = """\
import pytest as p

def identity(function):
    return function

p.fixture = identity

@p.fixture
def test_visible() -> None:
    assert True
"""
    metadata = _later_metadata(
        assertion_ref="assertion:rebound-pytest-fixture-is-not-authority",
        activation_phase="G0",
    )
    metadata["source_ast_sha256"] = _source_ast_sha256(
        function_source,
        "test_visible",
    )
    source = (
        function_source
        + "\n__cemm_test_inventory__ = {\n"
        + f"    {node_id!r}: {metadata!r},\n"
        + "}\n"
    )
    _write_frozen_module(root, source, relative_path=relative_path)

    verified = _verify(root, inventory_path, phase="G0")

    assert node_id in verified.active_node_ids

def test_later_parametrize_requires_literal_matching_safe_ids(
    tmp_path: Path,
) -> None:
    variants = (
        ("mismatch", "[1, 2]", "['one']", "ids count"),
        ("dynamic", "VALUES", "['one']", "literal argvalues"),
        ("unicode", "[1]", "['é']", "safe ASCII"),
    )
    for name, argvalues, ids, error in variants:
        root, inventory_path, _payload = _one_retained_project(
            tmp_path,
            name=name,
        )
        source = f"""\
import pytest

VALUES = [1]

@pytest.mark.parametrize("value", {argvalues}, ids={ids})
def test_later(value: int) -> None:
    assert value

__cemm_test_inventory__ = {{}}
"""
        _write_frozen_module(
            root,
            source,
            relative_path="tests/test_later.py",
        )

        with pytest.raises(CORE.InventoryError, match=error):
            _verify(root, inventory_path, phase="G0")

def test_dynamic_test_classes_are_rejected_before_static_enumeration(
    tmp_path: Path,
) -> None:
    variants = (
        "class Base:\n    def test_inherited(self):\n        assert True\n\nclass TestChild(Base):\n    pass\n",
        "def decorate(cls):\n    return cls\n\n@decorate\nclass TestDecorated:\n    pass\n",
        "class Meta(type):\n    pass\n\nclass TestMeta(metaclass=Meta):\n    pass\n",
    )
    for index, body in enumerate(variants):
        root, inventory_path, _payload = _one_retained_project(
            tmp_path,
            name=f"dynamic-class-{index}",
        )
        _write_frozen_module(
            root,
            body + "\n__cemm_test_inventory__ = {}\n",
            relative_path="tests/test_later.py",
        )

        with pytest.raises(CORE.InventoryError, match="dynamic test class"):
            _verify(root, inventory_path, phase="G0")

def test_callable_test_alias_cannot_evade_literal_metadata(tmp_path: Path) -> None:
    variants = (
        (
            "function-alias",
            """\
def helper() -> None:
    assert True

test_hidden = helper
""",
        ),
        (
            "class-alias",
            """\
class Helper:
    def test_method(self) -> None:
        assert True

TestHidden = Helper
""",
        ),
    )
    for name, body in variants:
        root, inventory_path, _payload = _one_retained_project(
            tmp_path,
            name=name,
        )
        _write_frozen_module(
            root,
            body + "\n__cemm_test_inventory__ = {}\n",
            relative_path="tests/test_later.py",
        )

        with pytest.raises(CORE.InventoryError, match="ambiguous test binding"):
            _verify(root, inventory_path, phase="G0")

def test_source_scan_requires_pinned_pytest_collection_contract(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    config = root / "pyproject.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("test_*.py", "test*.py"),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(CORE.InventoryError, match="pytest collection contract"):
        _verify(root, inventory_path, phase="G0")

def test_source_scan_covers_default_pytest_file_and_function_patterns(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    node_id = "tests/later_test.py::testvisible"
    _write_later_module(
        root,
        [
            (
                "testvisible",
                _later_metadata(
                    assertion_ref="assertion:default-pytest-patterns",
                    activation_phase="G0",
                ),
            )
        ],
        relative_path="tests/later_test.py",
    )
    _write_frozen_module(
        root,
        "def testhelper() -> None:\n    assert True\n",
        relative_path="tests/testhelpers.py",
    )

    verified = _verify(root, inventory_path, phase="G0")

    assert node_id in verified.active_node_ids
    assert verified.parsed_module_count == 2

def test_source_only_verification_parses_each_module_once_without_heavy_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, inventory_path, _payload = _one_retained_project(tmp_path)
    _write_later_module(
        root,
        [
            (
                "test_later",
                _later_metadata(
                    assertion_ref="assertion:later",
                    activation_phase="G0",
                ),
            )
        ],
    )
    later_path = root / "tests" / "test_later.py"
    later_path.write_text(
        later_path.read_text(encoding="utf-8")
        + "\n\nimport pytest\n\n@pytest.fixture\ndef test_authority_factory():\n    return object()\n",
        encoding="utf-8",
        newline="\n",
    )

    parsed: list[str] = []

    def counting_parse(
        source: str | bytes,
        filename: str = "<unknown>",
        mode: str = "exec",
        **kwargs: object,
    ) -> ast.AST:
        parsed.append(Path(filename).as_posix())
        return ast.parse(source, filename=filename, mode=mode, **kwargs)

    def forbidden_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("source-only inventory verification invoked a process/test runner")

    blocked_roots = {
        "cemm_authoritative_hybrid",
        "model",
        "pytest",
        "torch",
        "training",
    }
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name.split(".", 1)[0] in blocked_roots:
            raise AssertionError(f"forbidden source-only import: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(subprocess, "run", forbidden_call)
    monkeypatch.setattr(subprocess, "Popen", forbidden_call)
    monkeypatch.setattr(pytest, "main", forbidden_call)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    before_verify = frozenset(sys.modules)
    verified = _verify(
        root,
        inventory_path,
        phase="G0",
        parse_source=counting_parse,
    )
    import_delta = _CORE_IMPORT_DELTA | (frozenset(sys.modules) - before_verify)

    expected_paths = ["tests/test_frozen.py", "tests/test_later.py"]
    assert sorted(parsed) == expected_paths
    assert len(parsed) == len(set(parsed)) == 2
    assert not {
        module_name
        for module_name in import_delta
        if module_name.split(".", 1)[0] in blocked_roots
    }
    assert verified.active_node_ids == (
        "tests/test_frozen.py::test_frozen",
        "tests/test_later.py::test_later",
    )


def test_r5_overlay_requires_a_disposition_for_each_missing_r5_leaf(
    tmp_path: Path,
) -> None:
    root, inventory_path, _payload = _one_retained_project(
        tmp_path,
        activation_phase="R5",
    )
    (root / "tests" / "test_frozen.py").unlink()

    with pytest.raises(CORE.InventoryError, match="disposition|coverage"):
        _verify(root, inventory_path, phase="R5")


def test_r5_overlay_defers_absent_leaf_without_admitting_it(
    tmp_path: Path,
) -> None:
    root, inventory_path, payload = _one_retained_project(
        tmp_path,
        activation_phase="R5",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    (root / "tests" / "test_frozen.py").unlink()
    _write_r5_overlay(
        root,
        payload,
        [_overlay_row(predecessor, "assertion:frozen", "deferred")],
    )

    for phase in ("R5", "R6", "R8"):
        verified = _verify(root, inventory_path, phase=phase)

        assert predecessor not in verified.active_node_ids
        assert predecessor not in verified.collectable_node_ids
        assert verified.deferred_r5_assertion_refs == ("assertion:frozen",)
        assert verified.retired_r5_assertion_refs == ()
        assert verified.r5_disposition_receipt_ref.startswith(
            "r5_test_disposition_receipt:"
        )
        assert not verified.owner_node_ids
        assert not verified.phase_node_ids
        assert not verified.admission_only_node_ids

    without_overlay = _verify(root, inventory_path, phase="R4")
    assert without_overlay.deferred_r5_assertion_refs == ()
    assert without_overlay.retired_r5_assertion_refs == ()
    assert without_overlay.r5_disposition_receipt_ref is None


def test_r5_overlay_retires_only_the_exact_absent_fallback_leaf(
    tmp_path: Path,
) -> None:
    source_ref = (
        "tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::"
        "test_failure_meaning_uses_safe_fallback"
    )
    assertion_ref = (
        "assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-"
        "failure-meaning-uses-safe-fallback"
    )
    source = (
        "class TestNeuralRealizerWeightUse:\n"
        "    def test_failure_meaning_uses_safe_fallback(self) -> None:\n"
        "        assert True\n"
    )

    def records(text: str) -> list[dict[str, object]]:
        record = _retained_record(
            "tests/test_neural_realizer_weight_use.py",
            text,
            "test_failure_meaning_uses_safe_fallback",
            assertion_ref=assertion_ref,
            activation_phase="R5",
        )
        record["source_test_ref"] = source_ref
        record["case_node_ids"] = [source_ref]
        return [record]

    root = tmp_path / "retired"
    root.mkdir()
    _write_pytest_collection_contract(root)
    _write_frozen_module(
        root,
        source,
        relative_path="tests/test_neural_realizer_weight_use.py",
    )
    payload = _inventory_payload(root, records(source))
    inventory_path = _write_inventory(root, payload)
    (root / "tests" / "test_neural_realizer_weight_use.py").unlink()
    _write_r5_overlay(
        root,
        payload,
        [_overlay_row(source_ref, assertion_ref, "retired")],
    )

    for phase in ("R5", "R6", "R8"):
        verified = _verify(root, inventory_path, phase=phase)

        assert source_ref not in verified.active_node_ids
        assert source_ref not in verified.collectable_node_ids
        assert verified.deferred_r5_assertion_refs == ()
        assert verified.retired_r5_assertion_refs == (assertion_ref,)
        assert verified.r5_disposition_receipt_ref.startswith(
            "r5_test_disposition_receipt:"
        )
        assert not verified.owner_node_ids
        assert not verified.phase_node_ids
        assert not verified.admission_only_node_ids


@pytest.mark.parametrize(
    "disposition",
    ["deferred", "retired"],
    ids=["deferred", "retired"],
)
def test_r5_deferred_and_retired_nodes_cannot_satisfy_due_rewrites(
    tmp_path: Path,
    disposition: str,
) -> None:
    target_source_ref = "tests/test_target.py::test_target"
    target_assertion = "assertion:target"
    target_source = "def test_target() -> None:\n    assert True\n"
    if disposition == "retired":
        target_source_ref = (
            "tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::"
            "test_failure_meaning_uses_safe_fallback"
        )
        target_assertion = (
            "assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-"
            "failure-meaning-uses-safe-fallback"
        )
        target_source = (
            "class TestNeuralRealizerWeightUse:\n"
            "    def test_failure_meaning_uses_safe_fallback(self) -> None:\n"
            "        assert True\n"
        )
    rewritten_source = "def test_rewritten() -> None:\n    assert True\n"
    root = tmp_path / disposition
    root.mkdir()
    _write_pytest_collection_contract(root)
    _write_frozen_module(root, rewritten_source)
    target_path = target_source_ref.split("::", 1)[0]
    _write_frozen_module(root, target_source, relative_path=target_path)
    rewritten, _rewrite_ref = _rewritten_record(
        "tests/test_frozen.py",
        rewritten_source,
        "test_rewritten",
        assertion_ref="assertion:rewritten",
        replacement_phase="R5",
        required_successor_node_ids=[target_source_ref],
    )
    target_record = _retained_record(
        target_path,
        target_source,
        target_source_ref.rsplit("::", 1)[-1],
        assertion_ref=target_assertion,
        activation_phase="R5",
    )
    target_record["source_test_ref"] = target_source_ref
    target_record["case_node_ids"] = [target_source_ref]
    payload = _inventory_payload(root, [rewritten, target_record])
    inventory_path = _write_inventory(root, payload)
    _write_later_module(
        root,
        [
            (
                "test_replacement",
                _later_metadata(
                    assertion_ref=target_assertion,
                    activation_phase="R5",
                    supersedes_node_id=target_source_ref,
                ),
            )
        ],
    )
    _write_r5_overlay(
        root,
        payload,
        [_overlay_row(target_source_ref, target_assertion, disposition)],
    )

    for phase in ("R5", "R6", "R8"):
        with pytest.raises(
            CORE.InventoryError,
            match="rewrite|non-executable|executable descendant",
        ):
            _verify(root, inventory_path, phase=phase)


def test_r5_deferred_predecessor_rejects_literal_executable_descendant(
    tmp_path: Path,
) -> None:
    root, inventory_path, payload = _one_retained_project(
        tmp_path,
        activation_phase="R5",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    descendant = "tests/test_later.py::test_descendant"
    (root / "tests" / "test_frozen.py").unlink()
    _write_later_module(
        root,
        [
            (
                "test_descendant",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R5",
                    supersedes_node_id=predecessor,
                ),
            )
        ],
    )
    _write_r5_overlay(
        root,
        payload,
        [_overlay_row(predecessor, "assertion:frozen", "deferred")],
    )

    for phase in ("R5", "R6", "R8"):
        with pytest.raises(
            CORE.InventoryError,
            match=(
                "deferred R5 predecessor .*test_frozen has executable descendant "
                ".*test_descendant"
            ),
        ):
            _verify(root, inventory_path, phase=phase)


def test_r5_retired_predecessor_rejects_multihop_executable_descendant(
    tmp_path: Path,
) -> None:
    predecessor = (
        "tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::"
        "test_failure_meaning_uses_safe_fallback"
    )
    assertion_ref = (
        "assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-"
        "failure-meaning-uses-safe-fallback"
    )
    source = (
        "class TestNeuralRealizerWeightUse:\n"
        "    def test_failure_meaning_uses_safe_fallback(self) -> None:\n"
        "        assert True\n"
    )
    root = tmp_path / "retired-descendant"
    root.mkdir()
    _write_pytest_collection_contract(root)
    source_path = "tests/test_neural_realizer_weight_use.py"
    _write_frozen_module(root, source, relative_path=source_path)
    record = _retained_record(
        source_path,
        source,
        "test_failure_meaning_uses_safe_fallback",
        assertion_ref=assertion_ref,
        activation_phase="R5",
    )
    record["source_test_ref"] = predecessor
    record["case_node_ids"] = [predecessor]
    payload = _inventory_payload(root, [record])
    inventory_path = _write_inventory(root, payload)
    (root / source_path).unlink()
    intermediate = "tests/test_later.py::test_intermediate"
    leaf = "tests/test_later.py::test_current_leaf"
    _write_later_module(
        root,
        [
            (
                "test_intermediate",
                _later_metadata(
                    assertion_ref=assertion_ref,
                    activation_phase="R5",
                    supersedes_node_id=predecessor,
                ),
            ),
            (
                "test_current_leaf",
                _later_metadata(
                    assertion_ref=assertion_ref,
                    activation_phase="R5",
                    supersedes_node_id=intermediate,
                ),
            ),
        ],
    )
    _write_r5_overlay(
        root,
        payload,
        [_overlay_row(predecessor, assertion_ref, "retired")],
    )

    for phase in ("R5", "R6", "R8"):
        with pytest.raises(
            CORE.InventoryError,
            match=(
                "retired R5 predecessor .*safe_fallback has executable descendant "
                ".*test_intermediate"
            ),
        ):
            _verify(root, inventory_path, phase=phase)


def test_r5_due_rewrite_cannot_use_descendant_of_deferred_predecessor(
    tmp_path: Path,
) -> None:
    predecessor_source = "def test_predecessor() -> None:\n    assert True\n"
    rewritten_source = "def test_rewritten() -> None:\n    assert True\n"
    predecessor = "tests/test_predecessor.py::test_predecessor"
    descendant = "tests/test_later.py::test_descendant"
    root = tmp_path / "rewrite-descendant"
    root.mkdir()
    _write_pytest_collection_contract(root)
    _write_frozen_module(
        root,
        predecessor_source,
        relative_path="tests/test_predecessor.py",
    )
    _write_frozen_module(root, rewritten_source)
    rewritten, rewrite_ref = _rewritten_record(
        "tests/test_frozen.py",
        rewritten_source,
        "test_rewritten",
        assertion_ref="assertion:rewritten",
        replacement_phase="R5",
        required_successor_node_ids=[descendant],
    )
    predecessor_record = _retained_record(
        "tests/test_predecessor.py",
        predecessor_source,
        "test_predecessor",
        assertion_ref="assertion:predecessor",
        activation_phase="R5",
    )
    payload = _inventory_payload(root, [rewritten, predecessor_record])
    inventory_path = _write_inventory(root, payload)
    (root / "tests" / "test_predecessor.py").unlink()
    _write_later_module(
        root,
        [
            (
                "test_descendant",
                _later_metadata(
                    assertion_ref="assertion:predecessor",
                    activation_phase="R5",
                    supersedes_node_id=predecessor,
                    contributes_to_rewrite_refs=[rewrite_ref],
                ),
            )
        ],
    )
    _write_r5_overlay(
        root,
        payload,
        [_overlay_row(predecessor, "assertion:predecessor", "deferred")],
    )

    for phase in ("R5", "R6", "R8"):
        with pytest.raises(
            CORE.InventoryError,
            match=(
                "deferred R5 predecessor .*test_predecessor has executable descendant "
                ".*test_descendant"
            ),
        ):
            _verify(root, inventory_path, phase=phase)


def test_r5_successor_requires_literal_executable_metadata(tmp_path: Path) -> None:
    root, inventory_path, payload = _one_retained_project(
        tmp_path,
        activation_phase="R5",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    successor = "tests/test_later.py::test_replacement"
    (root / "tests" / "test_frozen.py").unlink()
    _write_r5_overlay(
        root,
        payload,
        [
            _overlay_row(
                predecessor,
                "assertion:frozen",
                "successor",
                successor_node_ids=[successor],
            )
        ],
    )

    with pytest.raises(CORE.InventoryError, match="literal|successor|metadata"):
        _verify(root, inventory_path, phase="R5")


def test_r5_successor_uses_normal_lineage_to_current_executable_leaf(
    tmp_path: Path,
) -> None:
    root, inventory_path, payload = _one_retained_project(
        tmp_path,
        activation_phase="R5",
    )
    predecessor = "tests/test_frozen.py::test_frozen"
    successor = "tests/test_later.py::test_replacement"
    leaf = "tests/test_later.py::test_current_leaf"
    (root / "tests" / "test_frozen.py").unlink()
    _write_later_module(
        root,
        [
            (
                "test_replacement",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R5",
                    supersedes_node_id=predecessor,
                ),
            ),
            (
                "test_current_leaf",
                _later_metadata(
                    assertion_ref="assertion:frozen",
                    activation_phase="R5",
                    supersedes_node_id=successor,
                ),
            ),
        ],
    )
    _write_r5_overlay(
        root,
        payload,
        [
            _overlay_row(
                predecessor,
                "assertion:frozen",
                "successor",
                successor_node_ids=[successor],
            )
        ],
    )

    verified = _verify(root, inventory_path, phase="R5")

    assert verified.active_node_ids == (leaf,)
    assert predecessor not in verified.active_node_ids
    assert successor not in verified.active_node_ids


def test_r5_real_overlay_is_exact_and_g0_through_r4_are_unchanged() -> None:
    expected_refs = {
        "G0": "active_test_nodes:312d4c08c90e95c624b5204b",
        "R1": "active_test_nodes:614d9a53a12a2af9f8521553",
        "R2": "active_test_nodes:99397e3af1310ae238ebfada",
        "R3": "active_test_nodes:d207e42b5546fbcfb7f19a03",
        "R4": "active_test_nodes:a6b4bb6c542f13ffe4e70188",
    }
    inventory_path = ROOT / "governance" / "test_inventory.json"

    for phase, expected_ref in expected_refs.items():
        result = CORE.load_and_verify(
            ROOT,
            inventory_path,
            phase=phase,
            enforce_reviewed_counts=True,
        )
        assert result.active_node_set_ref == expected_ref
        assert result.r5_disposition_receipt_ref is None
        assert result.deferred_r5_assertion_refs == ()
        assert result.retired_r5_assertion_refs == ()

    dispositions = _load_r5_dispositions().load_r5_test_dispositions(
        ROOT,
        expected_inventory_ref=R5_TEST_INVENTORY_REF,
    )
    assert len(dispositions.rows) == 43
    assert dispositions.counts == {"successor": 17, "deferred": 25, "retired": 1}


def test_r5_real_disposition_partition_rejects_missing_or_extra_rows(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    reviewed = CORE.load_strict_json(
        ROOT / "governance" / "r5_test_dispositions.json"
    )
    assert isinstance(reviewed, dict)
    for name, mutate in (
        ("missing", lambda rows: rows.pop()),
        ("extra", lambda rows: rows.append(copy.deepcopy(rows[-1]))),
    ):
        root = tmp_path / name
        governance = root / "governance"
        governance.mkdir(parents=True)
        (governance / "test_inventory.json").write_bytes(
            (ROOT / "governance" / "test_inventory.json").read_bytes()
        )
        candidate = copy.deepcopy(reviewed)
        rows = candidate["rows"]
        assert isinstance(rows, list)
        mutate(rows)
        (governance / "r5_test_dispositions.json").write_bytes(
            _canonical_bytes(candidate) + b"\n"
        )

        with pytest.raises(
            dispositions_module.R5TestDispositionError,
            match="coverage|row count|duplicate",
        ):
            dispositions_module.load_r5_test_dispositions(
                root,
                expected_inventory_ref=R5_TEST_INVENTORY_REF,
            )


def test_inventory_cli_adds_only_r5_disposition_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _load_check_inventory()
    inventory = CORE.load_strict_json(ROOT / "governance" / "test_inventory.json")
    assert isinstance(inventory, dict)
    common = dict(
        inventory_ref=R5_TEST_INVENTORY_REF,
        baseline_source_ref=BASELINE_SOURCE_REF,
        active_node_ids=(),
        collectable_node_ids=(),
        deferred_rewrite_refs=(),
        due_rewrite_refs=(),
        owner_node_ids={},
        phase_node_ids=(),
        admission_only_node_ids=(),
        source_tests={},
        later_nodes={},
        parsed_module_count=0,
        literal_metadata_ref="literal_test_metadata:" + "0" * 24,
        active_node_set_ref="active_test_nodes:" + "0" * 24,
        collectable_node_set_ref="collectable_test_nodes:" + "0" * 24,
    )
    r4_result = CORE.InventoryResult(
        **common,
        r5_disposition_receipt_ref=None,
        deferred_r5_assertion_refs=(),
        retired_r5_assertion_refs=(),
    )
    r5_sources = {
        f"tests/test_{index}.py::test_{index}": CORE.SourceTestRecord(
            source_test_ref=f"tests/test_{index}.py::test_{index}",
            classification="retained",
            activation_phase="R5",
            assertion_ref=f"assertion:test-{index}",
            source_ast_sha256="0" * 64,
            case_node_ids=(f"tests/test_{index}.py::test_{index}",),
            successor_node_ids=(),
        )
        for index in range(43)
    }
    r5_result = replace(
        r4_result,
        source_tests=r5_sources,
        r5_disposition_receipt_ref="r5_test_disposition_receipt:" + "1" * 24,
        deferred_r5_assertion_refs=tuple(
            f"assertion:deferred-{index}" for index in range(25)
        ),
        retired_r5_assertion_refs=("assertion:retired",),
    )
    with patch.object(cli, "verify_document_authority_pin", return_value="0" * 64):
        with patch.object(cli, "load_and_verify", return_value=r4_result):
            assert cli.main(["--phase", "R4", "--source-only"]) == 0
        r4_payload = json.loads(capsys.readouterr().out)
        assert not {key for key in r4_payload if key.startswith("r5_")}

        with patch.object(cli, "load_and_verify", return_value=r5_result):
            assert cli.main(["--phase", "R5", "--source-only"]) == 0
        r5_payload = json.loads(capsys.readouterr().out)

        with patch.object(cli, "load_and_verify", return_value=r5_result):
            assert cli.main(["--phase", "R8", "--source-only"]) == 0
        r8_payload = json.loads(capsys.readouterr().out)
    for payload in (r5_payload, r8_payload):
        assert payload["r5_disposition_receipt_ref"] == (
            "r5_test_disposition_receipt:" + "1" * 24
        )
        assert payload["r5_successor_count"] == 17
        assert payload["r5_deferred_count"] == 25
        assert payload["r5_retired_count"] == 1


R5_TEST_INVENTORY_REF = "test_inventory:c715e262526c0ea26a6fef90"
R5_PREDECESSOR = "tests/test_x.py::test_x"


def _r5_inventory_record(
    *,
    source_test_ref: str = R5_PREDECESSOR,
    assertion_ref: str = "assertion:x",
    activation_phase: str = "R5",
) -> dict[str, object]:
    return {
        "source_test_ref": source_test_ref,
        "classification": "retained",
        "activation_phase": activation_phase,
        "assertion_ref": assertion_ref,
        "case_node_ids": [source_test_ref],
    }


def _r5_successor_row() -> dict[str, object]:
    return {
        "predecessor_source_test_ref": R5_PREDECESSOR,
        "assertion_ref": "assertion:x",
        "disposition": "successor",
        "successor_node_ids": ["tests/test_r5_x.py::test_x"],
    }


def _write_r5_disposition_project(
    tmp_path: Path,
    *,
    name: str = "r5-dispositions",
    rows: list[dict[str, object]] | None = None,
    inventory_records: list[dict[str, object]] | None = None,
    payload_updates: dict[str, object] | None = None,
) -> Path:
    root = tmp_path / name
    governance = root / "governance"
    governance.mkdir(parents=True)
    inventory = {
        "inventory_ref": R5_TEST_INVENTORY_REF,
        "source_tests": inventory_records or [_r5_inventory_record()],
    }
    (governance / "test_inventory.json").write_bytes(
        _canonical_bytes(inventory) + b"\n"
    )
    payload: dict[str, object] = {
        "schema": "cemm-r5-test-dispositions-v1",
        "phase": "R5",
        "inventory_ref": R5_TEST_INVENTORY_REF,
        "rows": rows or [_r5_successor_row()],
    }
    if payload_updates:
        payload.update(payload_updates)
    (governance / "r5_test_dispositions.json").write_bytes(
        _canonical_bytes(payload) + b"\n"
    )
    return root


def test_r5_disposition_schema_is_draft_2020_12_and_exact() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(R5_DISPOSITIONS_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    payload = {
        "schema": "cemm-r5-test-dispositions-v1",
        "phase": "R5",
        "inventory_ref": R5_TEST_INVENTORY_REF,
        "rows": [_r5_successor_row()],
    }

    validator.validate(payload)
    invalid = copy.deepcopy(payload)
    invalid["rows"][0]["future_task_ref"] = "R5-Neural-Activation"  # type: ignore[index]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(invalid)


def test_r5_disposition_loader_returns_immutable_typed_rows(tmp_path: Path) -> None:
    dispositions_module = _load_r5_dispositions()
    root = _write_r5_disposition_project(tmp_path)

    loaded = dispositions_module.load_r5_test_dispositions(
        root,
        expected_inventory_ref=R5_TEST_INVENTORY_REF,
    )

    assert loaded.schema == dispositions_module.DISPOSITION_SCHEMA
    assert loaded.phase == "R5"
    assert loaded.inventory_ref == R5_TEST_INVENTORY_REF
    assert loaded.rows[0].successor_node_ids == ("tests/test_r5_x.py::test_x",)
    assert loaded.counts == {"successor": 1, "deferred": 0, "retired": 0}
    assert len(loaded.source_sha256) == 64
    assert loaded.source_sha256 == loaded.source_sha256.lower()
    with pytest.raises(AttributeError):
        loaded.rows[0].assertion_ref = "assertion:changed"


def test_r5_disposition_loader_rejects_non_exact_successor_payloads(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    cases = [
        ({"unknown": True}, {}, "exact fields"),
        ({"successor_node_ids": []}, {}, "successor_node_ids"),
        ({"future_task_ref": "R5-Neural-Activation"}, {}, "exact fields"),
        ({}, {"unknown": True}, "exact fields"),
    ]
    for index, (row_update, payload_update, message) in enumerate(cases):
        row = _r5_successor_row()
        row.update(row_update)
        root = _write_r5_disposition_project(
            tmp_path,
            name=f"invalid-successor-{index}",
            rows=[row],
            payload_updates=payload_update,
        )
        with pytest.raises(dispositions_module.R5TestDispositionError, match=message):
            dispositions_module.load_r5_test_dispositions(
                root,
                expected_inventory_ref=R5_TEST_INVENTORY_REF,
            )


def test_r5_disposition_loader_rejects_incomplete_deferred_rows(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    for missing in ("future_task_ref", "future_owner_ref"):
        row = {
            "predecessor_source_test_ref": R5_PREDECESSOR,
            "assertion_ref": "assertion:x",
            "disposition": "deferred",
            "future_task_ref": "R5-Neural-Activation",
            "future_owner_ref": "proposal-contract",
        }
        del row[missing]
        root = _write_r5_disposition_project(
            tmp_path,
            name=f"missing-{missing}",
            rows=[row],
        )
        with pytest.raises(
            dispositions_module.R5TestDispositionError,
            match="exact fields",
        ):
            dispositions_module.load_r5_test_dispositions(
                root,
                expected_inventory_ref=R5_TEST_INVENTORY_REF,
            )


def test_r5_disposition_loader_requires_exact_deferred_task(tmp_path: Path) -> None:
    dispositions_module = _load_r5_dispositions()
    row = {
        "predecessor_source_test_ref": R5_PREDECESSOR,
        "assertion_ref": "assertion:x",
        "disposition": "deferred",
        "future_task_ref": "R5-Later",
        "future_owner_ref": "proposal-contract",
    }
    root = _write_r5_disposition_project(tmp_path, rows=[row])

    with pytest.raises(
        dispositions_module.R5TestDispositionError,
        match="R5-Neural-Activation",
    ):
        dispositions_module.load_r5_test_dispositions(
            root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


def test_r5_disposition_loader_requires_concrete_zero_fallback_retirement(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    row = {
        "predecessor_source_test_ref": R5_PREDECESSOR,
        "assertion_ref": "assertion:x",
        "disposition": "retired",
        "retirement_reason": "obsolete",
    }
    root = _write_r5_disposition_project(tmp_path, rows=[row])

    with pytest.raises(
        dispositions_module.R5TestDispositionError,
        match="zero fallback paths",
    ):
        dispositions_module.load_r5_test_dispositions(
            root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


def test_r5_disposition_loader_rejects_duplicates_non_r5_and_assertion_drift(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    duplicate_root = _write_r5_disposition_project(
        tmp_path,
        name="duplicate",
        rows=[_r5_successor_row(), _r5_successor_row()],
    )
    with pytest.raises(dispositions_module.R5TestDispositionError, match="duplicate"):
        dispositions_module.load_r5_test_dispositions(
            duplicate_root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )

    non_r5_root = _write_r5_disposition_project(
        tmp_path,
        name="non-r5",
        inventory_records=[_r5_inventory_record(activation_phase="R4")],
    )
    with pytest.raises(dispositions_module.R5TestDispositionError, match="non-R5"):
        dispositions_module.load_r5_test_dispositions(
            non_r5_root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )

    drifted = _r5_successor_row()
    drifted["assertion_ref"] = "assertion:drifted"
    drift_root = _write_r5_disposition_project(
        tmp_path,
        name="drifted",
        rows=[drifted],
    )
    with pytest.raises(
        dispositions_module.R5TestDispositionError,
        match="assertion mismatch",
    ):
        dispositions_module.load_r5_test_dispositions(
            drift_root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


def test_r5_disposition_loader_requires_exact_predecessor_coverage(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    second = "tests/test_y.py::test_y"
    root = _write_r5_disposition_project(
        tmp_path,
        inventory_records=[
            _r5_inventory_record(),
            _r5_inventory_record(
                source_test_ref=second,
                assertion_ref="assertion:y",
            ),
        ],
    )

    with pytest.raises(
        dispositions_module.R5TestDispositionError,
        match="coverage|row count",
    ):
        dispositions_module.load_r5_test_dispositions(
            root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


def test_r5_disposition_loader_bounds_reviewed_source(tmp_path: Path) -> None:
    dispositions_module = _load_r5_dispositions()
    root = _write_r5_disposition_project(tmp_path)
    (root / "governance" / "r5_test_dispositions.json").write_bytes(
        b" " * (dispositions_module.MAX_JSON_BYTES + 1)
    )

    with pytest.raises(dispositions_module.R5TestDispositionError, match="1 MiB"):
        dispositions_module.load_r5_test_dispositions(
            root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


def test_reviewed_r5_dispositions_are_exact_inventory_partition() -> None:
    dispositions_module = _load_r5_dispositions()
    loaded = dispositions_module.load_r5_test_dispositions(
        ROOT,
        expected_inventory_ref=R5_TEST_INVENTORY_REF,
    )

    assert len(loaded.rows) == 43
    assert loaded.counts == {"successor": 17, "deferred": 25, "retired": 1}
    assert {
        row.predecessor_source_test_ref for row in loaded.rows
    } == {
        source["source_test_ref"]
        for source in CORE.load_strict_json(
            ROOT / "governance" / "test_inventory.json"
        )["source_tests"]
        if source["classification"] == "retained"
        and source["activation_phase"] == "R5"
    }


def test_r5_disposition_receipt_rejects_forged_dataclasses(tmp_path: Path) -> None:
    dispositions_module = _load_r5_dispositions()
    root = _write_r5_disposition_project(tmp_path)
    reviewed = dispositions_module.load_r5_test_dispositions(
        root,
        expected_inventory_ref=R5_TEST_INVENTORY_REF,
    )
    row = reviewed.rows[0]
    for forged in (
        replace(reviewed, schema="forged-schema"),
        replace(reviewed, phase="R4"),
        replace(reviewed, inventory_ref="test_inventory:" + "0" * 24),
        replace(reviewed, rows=()),
        replace(reviewed, rows=(row, row)),
        replace(reviewed, source_sha256="0" * 64),
        replace(
            reviewed,
            rows=(
                replace(
                    row,
                    disposition="deferred",
                    successor_node_ids=(),
                    future_task_ref="R5-Neural-Activation",
                    future_owner_ref="forged-owner",
                ),
            ),
        ),
        replace(
            reviewed,
            rows=(
                replace(
                    row,
                    disposition="retired",
                    successor_node_ids=(),
                    retirement_reason="forged retirement reason",
                ),
            ),
        ),
    ):
        with pytest.raises(
            dispositions_module.R5TestDispositionError,
            match="reviewed source",
        ):
            dispositions_module.build_r5_test_disposition_receipt(root, forged)


def test_r5_disposition_loader_rejects_disposition_symlink_escape(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    root = _write_r5_disposition_project(tmp_path)
    disposition_path = root / "governance" / "r5_test_dispositions.json"
    external = tmp_path / "external-r5-test-dispositions.json"
    external.write_bytes(disposition_path.read_bytes())
    disposition_path.unlink()
    disposition_path.symlink_to(external)

    with pytest.raises(
        dispositions_module.R5TestDispositionError,
        match="escapes|symlink|contained",
    ):
        dispositions_module.load_r5_test_dispositions(
            root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


def test_r5_disposition_loader_rejects_inventory_symlink_escape(
    tmp_path: Path,
) -> None:
    dispositions_module = _load_r5_dispositions()
    root = _write_r5_disposition_project(tmp_path)
    inventory_path = root / "governance" / "test_inventory.json"
    external = tmp_path / "external-test-inventory.json"
    external.write_bytes(inventory_path.read_bytes())
    inventory_path.unlink()
    inventory_path.symlink_to(external)

    with pytest.raises(
        dispositions_module.R5TestDispositionError,
        match="escapes|symlink|contained",
    ):
        dispositions_module.load_r5_test_dispositions(
            root,
            expected_inventory_ref=R5_TEST_INVENTORY_REF,
        )


__cemm_test_inventory__ = {
    "tests/test_test_inventory.py::test_r5_overlay_requires_a_disposition_for_each_missing_r5_leaf": {
        "assertion_ref": "assertion:r5-test-inventory-missing-disposition-fails-closed",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "ce6c8386a441355906774c14e2ce050b6fbe96f0f675b2b6b91b8a69cef06877",
    },
    "tests/test_test_inventory.py::test_r5_overlay_defers_absent_leaf_without_admitting_it": {
        "assertion_ref": "assertion:r5-test-inventory-deferral-is-non-executable",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "dc7f38097fb55fac683cea8e568341df297b657ac22735035dd551c39adbd1a6",
    },
    "tests/test_test_inventory.py::test_r5_overlay_retires_only_the_exact_absent_fallback_leaf": {
        "assertion_ref": "assertion:r5-test-inventory-retirement-is-non-executable",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "4398977b1fc9f982736de78723d29bee17dacf0a1d3fba232e5559595f0e9641",
    },
    "tests/test_test_inventory.py::test_r5_deferred_and_retired_nodes_cannot_satisfy_due_rewrites[deferred]": {
        "assertion_ref": "assertion:r5-test-inventory-deferred-cannot-satisfy-rewrite",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "cae48d7ae9635193051a3471aef16d6fa6b77f6a4dd93d6a94ed12519f77150b",
    },
    "tests/test_test_inventory.py::test_r5_deferred_and_retired_nodes_cannot_satisfy_due_rewrites[retired]": {
        "assertion_ref": "assertion:r5-test-inventory-retired-cannot-satisfy-rewrite",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "cae48d7ae9635193051a3471aef16d6fa6b77f6a4dd93d6a94ed12519f77150b",
    },
    "tests/test_test_inventory.py::test_r5_deferred_predecessor_rejects_literal_executable_descendant": {
        "assertion_ref": "assertion:r5-test-inventory-deferred-lineage-has-no-descendant",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3-Review-Fix",
        "source_ast_sha256": "f164819d78eaa8af506fa18bda4e83f36d7c648098adacb36c35eb3e5afaa55c",
    },
    "tests/test_test_inventory.py::test_r5_retired_predecessor_rejects_multihop_executable_descendant": {
        "assertion_ref": "assertion:r5-test-inventory-retired-lineage-has-no-descendant",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3-Review-Fix",
        "source_ast_sha256": "2d25514d4d6af2e3d471a02eafb88ff260c5d2a4c048fb2e08966d9aa0ec8348",
    },
    "tests/test_test_inventory.py::test_r5_due_rewrite_cannot_use_descendant_of_deferred_predecessor": {
        "assertion_ref": "assertion:r5-test-inventory-deferred-descendant-cannot-satisfy-rewrite",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3-Review-Fix",
        "source_ast_sha256": "8f1f879c88173e5924bddcbb0b454241069cb811e6af9024b0657636cea10420",
    },
    "tests/test_test_inventory.py::test_r5_successor_requires_literal_executable_metadata": {
        "assertion_ref": "assertion:r5-test-inventory-successor-metadata-is-literal",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "730a5b05ac50430fe02c0483d524577b65d00ef7eea6f4ba5226e4d9ada5f20d",
    },
    "tests/test_test_inventory.py::test_r5_successor_uses_normal_lineage_to_current_executable_leaf": {
        "assertion_ref": "assertion:r5-test-inventory-successor-uses-normal-lineage",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "8713c725e90de3135e8e1eaba23ad083c2432b0ddb20a137885cfdbfd27b73fa",
    },
    "tests/test_test_inventory.py::test_r5_real_overlay_is_exact_and_g0_through_r4_are_unchanged": {
        "assertion_ref": "assertion:r5-test-inventory-overlay-is-exact-and-phase-local",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "32fed530b7f490ef4fa748f9066a969d0e59618a4a4a7362a8c450e8085bfdbc",
    },
    "tests/test_test_inventory.py::test_r5_real_disposition_partition_rejects_missing_or_extra_rows": {
        "assertion_ref": "assertion:r5-test-inventory-real-partition-is-exact",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "5492398c8dafd2ccb46beee6104d57d2d6323ed4fdb32fc0960eb929436a1a5d",
    },
    "tests/test_test_inventory.py::test_inventory_cli_adds_only_r5_disposition_fields": {
        "assertion_ref": "assertion:r5-test-inventory-cli-is-phase-local",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-3",
        "source_ast_sha256": "8afcb222b76a4a92af0fee7186b27dbdefe03a4d1c7241d4599850f0296dc40a",
    },
    "tests/test_test_inventory.py::test_r5_disposition_receipt_rejects_forged_dataclasses": {
        "assertion_ref": "assertion:r5-test-disposition-receipt-rejects-forgery",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "f5af295a30f7fe6847829afe83e035fde35d2d9d831cb7bd64650419735071c1",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_rejects_disposition_symlink_escape": {
        "assertion_ref": "assertion:r5-test-disposition-source-is-contained",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "0256de9b4e96af6c14c33161cf6f8505a5ee54bf902422533427071d20cb6f2d",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_rejects_inventory_symlink_escape": {
        "assertion_ref": "assertion:r5-test-disposition-inventory-is-contained",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "4e181ca06e346ce69a9fb06268e94715a9f42a88fd282c8540b05c779171d7e8",
    },
    "tests/test_test_inventory.py::test_r5_disposition_schema_is_draft_2020_12_and_exact": {
        "assertion_ref": "assertion:r5-test-disposition-schema-is-strict",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "908725882ff0bf3ea04f0a8addeed7c9db5efc166e4628da9fb8e2cb458b5022",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_returns_immutable_typed_rows": {
        "assertion_ref": "assertion:r5-test-disposition-loader-is-immutable",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "5a42f8cec5ab6643be7e91e7c2cb21a8357fe141d022a20a2f0dcfb39ebdc93c",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_rejects_non_exact_successor_payloads": {
        "assertion_ref": "assertion:r5-test-disposition-successors-are-exact",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "1c5b3f9a1220e9cb13fcd209e0c00c0e0669163faf650bb626c8be3754b5a57b",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_rejects_incomplete_deferred_rows": {
        "assertion_ref": "assertion:r5-test-disposition-deferrals-are-exact",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "7c935b4f441e87531c22ec4e233e7f55437fd0db66c0c2925f9118cd2a8b0bca",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_requires_exact_deferred_task": {
        "assertion_ref": "assertion:r5-test-disposition-deferral-task-is-pinned",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "e8e4bcb04b3894722dddb13fda386c064b3bdedb2ceec78ddac8469d20076f64",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_requires_concrete_zero_fallback_retirement": {
        "assertion_ref": "assertion:r5-test-disposition-retirement-is-concrete",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "6da13a0076ded9929dda328f617f7b7970ce06739003ff04d53530c7176c825b",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_rejects_duplicates_non_r5_and_assertion_drift": {
        "assertion_ref": "assertion:r5-test-disposition-identity-fails-closed",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "d4f0d564a9b95df610d86959e7827747a5dc178c06e358aad1b607dafac40d48",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_requires_exact_predecessor_coverage": {
        "assertion_ref": "assertion:r5-test-disposition-coverage-is-exact",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "084d7a5635e734747c5e1ac28175765ae46650c43cc8f173ce0c0d22dc00b3c6",
    },
    "tests/test_test_inventory.py::test_r5_disposition_loader_bounds_reviewed_source": {
        "assertion_ref": "assertion:r5-test-disposition-source-is-bounded",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "493fa734b2eaf12839d097ff752bf5fba154bc7c360635a49b0a1a6a3fef743d",
    },
    "tests/test_test_inventory.py::test_reviewed_r5_dispositions_are_exact_inventory_partition": {
        "assertion_ref": "assertion:r5-test-disposition-partition-is-exact",
        "activation_phase": "R5",
        "diagnostic_role": "owner",
        "owner_ref": "legacy-hard-cut",
        "introduced_by_task": "R5-Task-2",
        "source_ast_sha256": "e3067384b4f28af2adab0a7d42fa9432a245f0e684111c354612ee43347a44d8",
    },
    "tests/test_test_inventory.py::test_strict_json_rejects_duplicate_object_keys": {
        "assertion_ref": "assertion:test-inventory-strict-duplicate-json",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "73dd45f3778b7667729d66b3b2fc5051115f1d33c07400f73fe748d3379df2a5",
    },
    "tests/test_test_inventory.py::test_strict_json_rejects_non_finite_numbers": {
        "assertion_ref": "assertion:test-inventory-strict-nonfinite-json",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "65bf3180a293cef2d4e7031af253ce110758df241baad80a9e018fe9acf100c9",
    },
    "tests/test_test_inventory.py::test_inventory_recomputes_identity_sets_and_declared_counts": {
        "assertion_ref": "assertion:test-inventory-content-identities-and-counts",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "4d07ee096ee59b9c3b89ddbb47674f90be5a1696271499e19cdc2c42a26c8144",
    },
    "tests/test_test_inventory.py::test_inventory_rejects_paths_that_escape_the_project_root": {
        "assertion_ref": "assertion:test-inventory-safe-repository-paths",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "893a9324dac4f437f7d245ca6bb4b1247f3832874835272fa43295adc8e0d397",
    },
    "tests/test_test_inventory.py::test_frozen_ast_rejects_same_id_mutation_but_allows_unrelated_edits": {
        "assertion_ref": "assertion:test-inventory-frozen-source-ast-boundary",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "8edafd8776afcdd9597afb7b332e140ca5c5d65814ab3760346d3a0c94de5502",
    },
    "tests/test_test_inventory.py::test_g0_defers_rewrites_and_excludes_non_executable_originals": {
        "assertion_ref": "assertion:test-inventory-g0-deferred-rewrites",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "9daff4466467714b7a70566da4b5411e719f8a38fd41a414e1969720d82e9da8",
    },
    "tests/test_test_inventory.py::test_due_rewrite_requires_every_conjunctive_contributing_successor": {
        "assertion_ref": "assertion:test-inventory-conjunctive-rewrite-obligations",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "ce8c8807b5eedd47cb224891c5f39d061f83618717f5c86249ee4968964541fc",
    },
    "tests/test_test_inventory.py::test_valid_new_id_supersession_selects_exactly_one_lineage_leaf": {
        "assertion_ref": "assertion:test-inventory-one-supersession-leaf",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "6b23877021fc55b6a6296f6575fa3272a2d3ff38c10b7a3b3ddcbda67d9fbf0d",
    },
    "tests/test_test_inventory.py::test_supersession_rejects_duplicate_leaves_and_cycles": {
        "assertion_ref": "assertion:test-inventory-supersession-uniqueness-acyclicity",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "dd83829af56b0998b89416ff39da463c49dac2862bb3260cb3ea0e0589bd93f8",
    },
    "tests/test_test_inventory.py::test_supersession_preserves_assertion_and_cannot_regress_phase": {
        "assertion_ref": "assertion:test-inventory-supersession-assertion-phase",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "71e0846f8eeab32ecee6881a85c7b068e459d16d66c14e625f12b12619955aa9",
    },
    "tests/test_test_inventory.py::test_source_only_verification_parses_each_module_once_without_heavy_paths": {
        "assertion_ref": "assertion:test-inventory-one-ast-pass-lightweight",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "7470c148754fa217809f774f8eab1c4e1c2324871713ca749531d896756863ec",
    },
    "tests/test_test_inventory.py::test_reviewed_inventory_has_exact_predecessor_totals_and_g0_lifecycle": {
        "assertion_ref": "assertion:test-inventory-reviewed-predecessor-totals",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "1a0f32c0f76c80b71415450d6ef49d6e76e63fa69c3fe81f399ab79773110690",
    },
    "tests/test_test_inventory.py::test_literal_metadata_rejects_duplicate_node_keys": {
        "assertion_ref": "assertion:test-inventory-duplicate-literal-metadata",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "2c5106bda27e7205a997eba880a1f01eb43be65bc643b1339a27ec9e7d0b84b9",
    },
    "tests/test_test_inventory.py::test_custom_fixture_named_decorator_cannot_hide_later_test": {
        "assertion_ref": "assertion:test-inventory-resolved-fixture-identity",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "c00550d3d7da70acb65efb064f20776149c3d5a31577c557b02f16417b2d3c88",
    },
    "tests/test_test_inventory.py::test_later_parametrize_requires_literal_matching_safe_ids": {
        "assertion_ref": "assertion:test-inventory-exact-literal-parameter-cases",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "7aa9eaf9871e8f2989e7f57b8fa5b2d07e1840ce2aec932d11b47d92f4d947fd",
    },
    "tests/test_test_inventory.py::test_source_scan_covers_default_pytest_file_and_function_patterns": {
        "assertion_ref": "assertion:test-inventory-default-pytest-patterns",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "c10a6b36d6c2ae8ba0c60b81674e5d41a0265eeb2df5a034eb15bb69913362e5",
    },
    "tests/test_test_inventory.py::test_rebound_pytest_fixture_alias_cannot_hide_later_test": {
        "assertion_ref": "assertion:test-inventory-rebound-fixture-alias",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "d8e16fb9c10b51c8a1e3eb0baab977105a34eca38429ab233ee888f03363ecae",
    },
    "tests/test_test_inventory.py::test_callable_test_alias_cannot_evade_literal_metadata": {
        "assertion_ref": "assertion:test-inventory-rejects-callable-test-aliases",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "a178fc70684d3d0b616d1fc201cb662a670a0d8086a4585e5f303c5579a871fe",
    },
    "tests/test_test_inventory.py::test_source_scan_requires_pinned_pytest_collection_contract": {
        "assertion_ref": "assertion:test-inventory-pinned-pytest-collection",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "72971915cedab87349b0e4de32733a5675a6b653fae0a0e3a6476d3885d2b5c9",
    },
    "tests/test_test_inventory.py::test_dynamic_test_classes_are_rejected_before_static_enumeration": {
        "assertion_ref": "assertion:test-inventory-rejects-dynamic-test-classes",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-3",
        "source_ast_sha256": "fe181d0c6da01fcf4e1a9a761c0633598b8323d082fce55cca76d02a312227a9",
    },
}
