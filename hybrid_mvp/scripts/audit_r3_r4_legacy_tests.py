#!/usr/bin/env python3
"""Inventory predecessor-era R3/R4 tests that cannot remain admission-active.

A legacy-named module is exempt from the filename diagnostic only when every
remaining pytest node in it is explicitly named as a required successor by the
immutable test inventory. Forbidden imports/constructors are always findings.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
LEGACY_FILES = frozenset({
    "test_query_engine.py", "test_recursive_inference.py", "test_inference_bounds.py",
    "test_epistemic_admission.py", "test_temporal_state.py", "test_transition_simulation.py",
    "test_capability_derivation.py", "test_effect_gateway.py", "test_effect_recovery.py",
    "test_learning_distinctions.py", "test_learning_security.py", "test_synonym_acquisition.py",
    "test_dialogue_reference.py", "test_response_meaning.py",
})
FORBIDDEN_IMPORTS = frozenset({"legacy_propositions", "cemm_authoritative_hybrid.propositions"})


def _required_rewrite_successors() -> frozenset[str]:
    inventory = json.loads((ROOT / "governance/test_inventory.json").read_text(encoding="utf-8"))
    result: set[str] = set()
    for source in inventory["source_tests"]:
        if source.get("classification") != "rewritten":
            continue
        for obligation in source.get("rewrite_obligations", ()):
            result.update(obligation.get("required_successor_node_ids", ()))
    return frozenset(result)


def _pytest_nodes(path: Path, tree: ast.Module) -> frozenset[str]:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    nodes: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            nodes.add(f"{rel}::{node.name}")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test"):
                    nodes.add(f"{rel}::{node.name}::{child.name}")
    return frozenset(nodes)


def _rewrite_successor_only(path: Path, tree: ast.Module) -> bool:
    nodes = _pytest_nodes(path, tree)
    return bool(nodes) and nodes <= _required_rewrite_successors()


def _findings(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    rows.add(f"legacy_import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module in FORBIDDEN_IMPORTS:
                rows.add(f"legacy_import:{node.module}")
        elif isinstance(node, ast.Attribute) and node.attr == "graph":
            rows.add("program_graph_access")
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else None
            if name in {"SemanticSwitchProgram", "PropositionGraph"}:
                rows.add(f"legacy_constructor:{name}")
    if path.name in LEGACY_FILES and not _rewrite_successor_only(path, tree):
        rows.add("predecessor_r3_r4_test_file")
    return tuple(sorted(rows))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    findings = []
    for path in sorted(TESTS.glob("test_*.py")):
        if path.name.startswith(("test_r3_", "test_r4_")):
            continue
        reasons = _findings(path)
        if reasons:
            findings.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "reasons": list(reasons)})
    report = {
        "schema": "cemm-r3-r4-legacy-test-migration-v1",
        "finding_count": len(findings),
        "findings": findings,
        "required_action": "review and supersede/rewrite every finding in the immutable test inventory" if findings else "none",
    }
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8", newline="\n")
    print(raw, end="")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
