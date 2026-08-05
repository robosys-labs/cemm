#!/usr/bin/env python3
"""Verify literal R3/R4 test metadata and canonical AST hashes without pytest."""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    count = 0
    for path in sorted((ROOT / "tests").glob("test_r[34]_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        metadata = None
        functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in tree.body:
            if isinstance(node, ast.Assign):
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == "__cemm_test_inventory__":
                    metadata = ast.literal_eval(node.value)
                    break
        if type(metadata) is not dict:
            raise ValueError(f"{path.name} lacks literal __cemm_test_inventory__")
        for node_id, row in metadata.items():
            name = node_id.split("::")[-1].split("[", 1)[0]
            node = functions.get(name)
            if node is None:
                raise ValueError(f"{node_id} has no source function")
            digest = hashlib.sha256(
                ast.dump(node, annotate_fields=True, include_attributes=False).encode()
            ).hexdigest()
            if row.get("source_ast_sha256") != digest:
                raise ValueError(f"{node_id} has stale source_ast_sha256")
            count += 1
    print(f"verified {count} R3/R4 test metadata records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
