#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests" / "test_atomic_graph_stress.py")]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    receipt = {
        "command": command,
        "returncode": completed.returncode,
        "suite": "atomic_graph_stress",
        "positive_generated_cases": 576 + 24,
        "negative_or_partial_cases": 300,
        "total_generated_cases": 900,
    }
    (ROOT / "atomic_graph_stress_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
