#!/usr/bin/env python3
"""Fail closed when an active R3 test depends on predecessor-era ABIs.

Historical frozen tests remain executable for earlier-phase replay.  The hard
cut therefore applies to the immutable inventory's active R3 lineage leaves,
not to every historical module still retained as evidence.  A renamed or moved
test cannot bypass this audit because module selection comes from the verified
inventory, never filename convention alone.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = frozenset({
    "legacy_propositions",
    "legacy_runtime_fixtures",
    "cemm_authoritative_hybrid.propositions",
})
sys.path.insert(0, str(ROOT / "scripts"))

from test_inventory_core import load_and_verify, verify_document_authority_pin


def _findings(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    rows.add(f"legacy_import:{alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_IMPORTS:
            rows.add(f"legacy_import:{node.module}")
    return tuple(sorted(rows))


def _active_r3_test_paths() -> tuple[Path, ...]:
    inventory = ROOT / "governance" / "test_inventory.json"
    expected_sha256 = verify_document_authority_pin(ROOT, inventory)
    result = load_and_verify(
        ROOT,
        inventory,
        phase="R3",
        enforce_reviewed_counts=True,
        expected_sha256=expected_sha256,
    )
    relative_paths = {
        node_id.split("::", 1)[0]
        for node_id in result.active_node_ids
        if node_id.startswith("tests/") and "::" in node_id
    }
    paths = tuple(ROOT / relative for relative in sorted(relative_paths))
    missing = tuple(str(path.relative_to(ROOT)) for path in paths if not path.is_file())
    if missing:
        raise RuntimeError(f"active R3 test modules are missing: {missing}")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    paths = _active_r3_test_paths()
    findings = []
    for path in paths:
        reasons = _findings(path)
        if reasons:
            findings.append({
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "reasons": list(reasons),
            })
    report = {
        "schema": "cemm-r3-r4-legacy-test-migration-v3",
        "phase": "R3",
        "selection": "verified_active_inventory_lineage_leaves",
        "scanned_module_count": len(paths),
        "finding_count": len(findings),
        "findings": findings,
        "required_action": (
            "supersede every predecessor ABI dependency from active R3 tests"
            if findings else "none"
        ),
    }
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8", newline="\n")
    print(raw, end="")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
