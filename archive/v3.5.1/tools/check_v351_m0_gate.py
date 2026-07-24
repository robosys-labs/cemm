#!/usr/bin/env python3
"""Execute the non-release M0 stabilization gate.

This tool never regenerates or patches signed artifacts. It fails on the first
behavior/architecture/performance gate that is not proven.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    [sys.executable, "tools/check_v351_legacy_boundaries.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase0_1_stabilization.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase2_3_runtime_substrate.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase4_residual_substrate.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase4_capabilities_effects.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase4_realization_proof.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase5_stage_abi.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_phase5_cutover_contract.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350/test_v351_legacy_boundaries.py"],
    [sys.executable, "tools/capture_v351_phase0_baseline.py", "--strict-hot-path"],
    [sys.executable, "tools/benchmark_v351_phase2_store.py", "--scales", "1000,10000,100000"],
    [sys.executable, "-m", "pytest", "-q", "tests/v350"],
)


def main() -> int:
    for command in COMMANDS:
        print("+", " ".join(command), flush=True)
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode:
            print("M0 NOT PROVEN; failing command above.", file=sys.stderr)
            return completed.returncode
    print("M0 substrate gates passed. Signed release artifacts are still a later gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
