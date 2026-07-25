#!/usr/bin/env python3
"""Quarantine tests that explicitly encode removed pre-final contracts.

Files are preserved as `.legacy` text with an inventory. Tests are not retired
merely because they fail; only explicit compatibility signatures qualify.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

PATTERNS = {
    r"\b(?:learn|teach)\s*=": "removed Runtime.process learn/teach switch",
    r"from\s+cemm\.selfstate\s+import|\bSessionSelf\b": "removed global SessionSelf",
    r"\bResponsePlanner\b": "removed outcome-to-response planner",
    r"\.v1\.json": "removed language-pack sidecar",
    r"\binfer_state_dimension\b": "removed compiler dimension completion",
    r"[\"']mode[\"']\s*:\s*[\"'](?:ask|learn|teach)[\"']": "removed Ask/Learn/Teach web mode",
    r"\bvalue:(?:ready|processing|confused)\b": "removed global self outcome values",
    r"self\.(?:response|interpretation|epistemic)_state_dimension": "removed global self dimensions",
    r"packet\s*\[\s*[\"']query[\"']\s*\]\s*\[\s*[\"']operator[\"']": "removed bare query application contract",
}


def retire(repo: Path):
    tests = repo / "tests"
    destination = tests / "legacy_contracts"
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    for path in sorted(tests.glob("test*.py")):
        if path.name == "test_v1_final_phases_10_16.py":
            continue
        text = path.read_text(encoding="utf-8")
        reasons = [description for pattern, description in PATTERNS.items() if re.search(pattern, text)]
        if not reasons:
            continue
        target = destination / f"{path.name}.legacy"
        shutil.move(str(path), str(target))
        inventory.append({
            "source": str(path.relative_to(repo)),
            "preserved_as": str(target.relative_to(repo)),
            "reasons": sorted(set(reasons)),
        })
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (destination / "README.md").write_text(
        "# Retired pre-final contracts\n\n"
        "These files are preserved as historical evidence but are not executable acceptance authority. "
        "Each was retired only because it explicitly invokes a compatibility path removed by final CEMM v1.\n",
        encoding="utf-8",
    )
    return inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(retire(args.repo.resolve()), indent=2))


if __name__ == "__main__":
    main()
