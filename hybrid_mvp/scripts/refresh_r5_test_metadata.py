#!/usr/bin/env python3
"""Refresh only literal R5 ``source_ast_sha256`` metadata values."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import stat
import sys
import tempfile


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


class R5MetadataRefreshError(ValueError):
    """Raised when bounded transactional metadata refresh fails."""


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & marker)


def _read_bounded(path: Path) -> bytes:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        raise R5MetadataRefreshError(f"cannot read R5 test module: {path.name}") from exc
    if len(raw) > MAX_SOURCE_BYTES:
        raise R5MetadataRefreshError(f"{path.name} exceeds the R5 source byte bound")
    return raw


def _atomic_write(path: Path, data: bytes) -> None:
    if type(data) is not bytes:
        raise R5MetadataRefreshError("atomic metadata payload must be bytes")
    if _is_reparse_point(path.parent) or _is_reparse_point(path):
        raise R5MetadataRefreshError("metadata path cannot cross a reparse point")
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
    except OSError as exc:
        raise R5MetadataRefreshError(
            f"cannot stage atomic metadata write: {path.name}"
        ) from exc
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    except BaseException as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, OSError):
            raise R5MetadataRefreshError(
                f"atomic replace failed for metadata: {path.name}"
            ) from exc
        raise


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

    if _is_reparse_point(path):
        raise R5MetadataRefreshError(f"R5 test module is a reparse point: {path}")
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"R5 test module is not a regular file: {path}")
    hashes, _nodes = _metadata_nodes(resolved, _read_bounded(resolved))
    return hashes


def _offsets(raw: bytes) -> list[int]:
    starts = [0]
    total = 0
    for line in raw.splitlines(keepends=True):
        total += len(line)
        starts.append(total)
    return starts


def _build_candidate(path: Path) -> tuple[bytes, bytes, int]:
    raw = _read_bounded(path)
    original = raw
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
    candidate_hashes, candidate_nodes = _metadata_nodes(path, raw)
    for node_id, digest in candidate_hashes.items():
        if ast.literal_eval(candidate_nodes[node_id]) != digest:
            raise R5MetadataRefreshError(
                f"candidate metadata hash is stale after refresh: {node_id}"
            )
    return original, raw, len(replacements)


def refresh_r5_test_metadata(root: Path = ROOT) -> tuple[int, int]:
    """Refresh exact R5 modules and return ``(changed_hashes, file_count)``."""

    root_input = Path(os.path.abspath(root))
    if _is_reparse_point(root_input):
        raise R5MetadataRefreshError("Hybrid MVP root cannot be a reparse point")
    root_path = root_input.resolve()
    tests_input = root_input / "tests"
    if _is_reparse_point(tests_input):
        raise R5MetadataRefreshError("tests directory cannot be a junction or reparse point")
    tests = tests_input.resolve()
    try:
        tests.relative_to(root_path)
    except ValueError as exc:
        raise R5MetadataRefreshError("resolved tests directory escapes the root") from exc
    if not tests.is_dir():
        raise ValueError("tests directory must be a contained regular directory")
    files = tuple(sorted(tests.glob("test_r5_*.py")))
    if len(files) > MAX_R5_MODULES:
        raise ValueError("R5 test module count exceeds its bound")
    candidates: list[tuple[Path, bytes, bytes, int]] = []
    for path in files:
        if _is_reparse_point(path):
            raise R5MetadataRefreshError(
                f"R5 test module cannot be a junction or reparse point: {path.name}"
            )
        resolved = path.resolve()
        try:
            resolved.relative_to(tests)
        except ValueError as exc:
            raise ValueError(f"R5 test module escapes tests: {path.name}") from exc
        original, candidate, changed = _build_candidate(resolved)
        candidates.append((resolved, original, candidate, changed))

    replaced: list[tuple[Path, bytes]] = []
    try:
        for path, original, candidate, changed in candidates:
            if not changed:
                continue
            _atomic_write(path, candidate)
            replaced.append((path, original))
    except BaseException as exc:
        rollback_errors: list[str] = []
        for path, original in reversed(replaced):
            try:
                _atomic_write(path, original)
            except BaseException as rollback_exc:
                rollback_errors.append(f"{path.name}: {rollback_exc}")
        if rollback_errors:
            raise R5MetadataRefreshError(
                f"metadata rollback failed: {rollback_errors}"
            ) from exc
        raise
    changed = sum(candidate[3] for candidate in candidates)
    return changed, len(files)


def main() -> int:
    changed, files = refresh_r5_test_metadata(ROOT)
    print(f"refreshed {changed} AST hashes across {files} R5 test modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
