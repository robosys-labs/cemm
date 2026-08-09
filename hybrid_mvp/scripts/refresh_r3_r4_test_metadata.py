#!/usr/bin/env python3
"""Regenerate literal R3/R4 test AST hashes after an admitted-source rewrite.

This updates only the per-test canonical AST digest already enforced by
verify_r3_r4_test_metadata.py; it does not change assertion identity, phase,
role, owner, supersession lineage, or rewrite-obligation metadata.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import pprint

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def _digest(node: ast.AST) -> str:
    return hashlib.sha256(
        ast.dump(node, annotate_fields=True, include_attributes=False).encode()
    ).hexdigest()


def _refresh(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    assignment = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__cemm_test_inventory__"
        ),
        None,
    )
    if assignment is None:
        raise ValueError(f"{path.name} lacks literal __cemm_test_inventory__")
    metadata = ast.literal_eval(assignment.value)
    if type(metadata) is not dict:
        raise TypeError(f"{path.name} inventory metadata must be a literal dict")
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    changed = 0
    for node_id, row in metadata.items():
        if type(row) is not dict:
            raise TypeError(f"{node_id} metadata must be a literal dict")
        function_name = node_id.rsplit("::", 1)[-1].split("[", 1)[0]
        function = functions.get(function_name)
        if function is None:
            raise ValueError(f"{node_id} has no source function")
        digest = _digest(function)
        if row.get("source_ast_sha256") != digest:
            row["source_ast_sha256"] = digest
            changed += 1
    if changed:
        lines = text.splitlines(keepends=True)
        replacement = (
            "__cemm_test_inventory__ = "
            + pprint.pformat(metadata, width=120, sort_dicts=False)
            + "\n"
        )
        lines[assignment.lineno - 1 : assignment.end_lineno] = [replacement]
        path.write_text("".join(lines), encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    changed = 0
    files = 0
    for path in sorted(TESTS.glob("test_r[34]_*.py")):
        changed += _refresh(path)
        files += 1
    print(f"refreshed {changed} AST hashes across {files} R3/R4 test modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
