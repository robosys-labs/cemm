#!/usr/bin/env python3
"""Fail closed on predecessor-era R3/R4 test dependencies.

The hard cut is semantic, not nominal: historical filenames are harmless when
the tests exercise current contracts, while a renamed test is still legacy if
it imports predecessor proposition or fixture-owner modules. Scan every test
module so naming cannot bypass the audit.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
FORBIDDEN_IMPORTS = frozenset({
    "legacy_propositions",
    "legacy_runtime_fixtures",
    "cemm_authoritative_hybrid.propositions",
})


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
    return tuple(sorted(rows))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    findings = []
    for path in sorted(TESTS.glob("test_*.py")):
        reasons = _findings(path)
        if reasons:
            findings.append(
                {
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "reasons": list(reasons),
                }
            )
    report = {
        "schema": "cemm-r3-r4-legacy-test-migration-v2",
        "finding_count": len(findings),
        "findings": findings,
        "required_action": (
            "remove every predecessor ABI dependency from active tests"
            if findings
            else "none"
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
