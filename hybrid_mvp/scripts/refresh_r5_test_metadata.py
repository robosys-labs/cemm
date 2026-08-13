#!/usr/bin/env python3
"""Refresh only literal R5 ``source_ast_sha256`` metadata values."""

from __future__ import annotations

import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_inventory_core import (  # noqa: E402
    InventoryError,
    _fixture_aliases,
    _iter_test_functions,
    _literal_case_ids,
    _reject_ambiguous_test_bindings,
    _reject_duplicate_literal_metadata_keys,
    source_ast_sha256,
)


MAX_R5_MODULES = 64
MAX_SOURCE_BYTES = 2 * 1024 * 1024


def _inventory_assignment(tree: ast.Module, path: Path) -> ast.Assign:
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "__cemm_test_inventory__"
    ]
    if len(assignments) != 1 or not isinstance(assignments[0].value, ast.Dict):
        raise ValueError(f"{path.name} must have one literal __cemm_test_inventory__")
    return assignments[0]


def _metadata_nodes(
    path: Path,
    raw: bytes,
) -> tuple[dict[str, str], dict[str, ast.AST]]:
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f"{path.name} exceeds the R5 source byte bound")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} is not strict UTF-8") from exc
    tree = ast.parse(text, filename=str(path))
    assignment = _inventory_assignment(tree, path)
    source_path = f"tests/{path.name}"
    _reject_duplicate_literal_metadata_keys(
        assignment.value,
        path=source_path,
    )
    metadata = ast.literal_eval(assignment.value)
    if type(metadata) is not dict:
        raise TypeError(f"{path.name} inventory metadata must be a literal dict")
    _reject_ambiguous_test_bindings(tree.body, path=source_path)
    fixture_module_aliases, fixture_function_aliases = _fixture_aliases(tree)
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for source_ref, node in _iter_test_functions(
        tree.body,
        path=source_path,
        fixture_module_aliases=fixture_module_aliases,
        fixture_function_aliases=fixture_function_aliases,
    ):
        for node_id in _literal_case_ids(source_ref, node):
            if node_id in functions:
                raise InventoryError(f"duplicate source test in {source_path}: {node_id}")
            functions[node_id] = node
    value_nodes: dict[str, ast.AST] = {}
    top = assignment.value
    assert isinstance(top, ast.Dict)
    for key_node, row_node in zip(top.keys, top.values, strict=True):
        if not isinstance(key_node, ast.Constant) or type(key_node.value) is not str:
            raise TypeError(f"{path.name} inventory keys must be literal strings")
        node_id = key_node.value
        if not isinstance(row_node, ast.Dict):
            raise TypeError(f"{node_id} metadata must be a literal dict")
        hash_nodes = [
            value
            for key, value in zip(row_node.keys, row_node.values, strict=True)
            if isinstance(key, ast.Constant) and key.value == "source_ast_sha256"
        ]
        if len(hash_nodes) != 1:
            raise ValueError(f"{node_id} must have one source_ast_sha256")
        value_nodes[node_id] = hash_nodes[0]
    if set(value_nodes) != set(metadata):
        raise ValueError(f"{path.name} metadata is not a literal exact mapping")
    hashes: dict[str, str] = {}
    for node_id in metadata:
        function = functions.get(node_id)
        if function is None:
            raise ValueError(f"{node_id} has no source function")
        hashes[node_id] = source_ast_sha256(function)
    return hashes, value_nodes


def metadata_hashes(path: Path) -> dict[str, str]:
    """Return canonical AST hashes for one literal R5 metadata module."""

    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise ValueError(f"R5 test module is not a regular file: {path}")
    hashes, _nodes = _metadata_nodes(resolved, resolved.read_bytes())
    return hashes


def _offsets(raw: bytes) -> list[int]:
    starts = [0]
    total = 0
    for line in raw.splitlines(keepends=True):
        total += len(line)
        starts.append(total)
    return starts


def _refresh(path: Path) -> int:
    if path.is_symlink():
        raise ValueError(f"R5 test module cannot be a symlink: {path.name}")
    raw = path.read_bytes()
    hashes, nodes = _metadata_nodes(path, raw)
    replacements: list[tuple[int, int, bytes]] = []
    starts = _offsets(raw)
    for node_id, digest in hashes.items():
        value_node = nodes[node_id]
        if None in (
            getattr(value_node, "lineno", None),
            getattr(value_node, "col_offset", None),
            getattr(value_node, "end_lineno", None),
            getattr(value_node, "end_col_offset", None),
        ):
            raise ValueError(f"{node_id} AST value lacks exact source geometry")
        current = ast.literal_eval(value_node)
        if current == digest:
            continue
        start = starts[value_node.lineno - 1] + value_node.col_offset
        end = starts[value_node.end_lineno - 1] + value_node.end_col_offset
        replacements.append((start, end, repr(digest).encode("ascii")))
    for start, end, replacement in sorted(replacements, reverse=True):
        raw = raw[:start] + replacement + raw[end:]
    if replacements:
        path.write_bytes(raw)
    return len(replacements)


def refresh_r5_test_metadata(root: Path = ROOT) -> tuple[int, int]:
    """Refresh exact R5 modules and return ``(changed_hashes, file_count)``."""

    root_path = Path(root).resolve()
    tests = root_path / "tests"
    if tests.is_symlink() or not tests.is_dir():
        raise ValueError("tests directory must be a contained regular directory")
    files = tuple(sorted(tests.glob("test_r5_*.py")))
    if len(files) > MAX_R5_MODULES:
        raise ValueError("R5 test module count exceeds its bound")
    changed = 0
    for path in files:
        resolved = path.resolve()
        try:
            resolved.relative_to(tests.resolve())
        except ValueError as exc:
            raise ValueError(f"R5 test module escapes tests: {path.name}") from exc
        changed += _refresh(path)
    return changed, len(files)


def main() -> int:
    changed, files = refresh_r5_test_metadata(ROOT)
    print(f"refreshed {changed} AST hashes across {files} R5 test modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
