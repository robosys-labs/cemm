#!/usr/bin/env python3
"""Verify that re-training reproduces the release models exactly.

Usage:
    python scripts/reproduce_models.py --expected artifacts --temporary \
        --receipt artifacts/validation/REPRODUCIBILITY.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify release model reproducibility."
    )
    parser.add_argument(
        "--expected",
        default="artifacts",
        help="Path to the expected artifacts root directory.",
    )
    parser.add_argument(
        "--temporary",
        action="store_true",
        help="Use an OS temporary directory for scratch (outside the repository).",
    )
    parser.add_argument(
        "--receipt",
        default="artifacts/validation/REPRODUCIBILITY.json",
        help="Path to write the reproducibility receipt JSON.",
    )
    args = parser.parse_args()

    expected_root = (ROOT / args.expected).resolve()
    receipt_path = (ROOT / args.receipt).resolve()

    print(f"Reproducing release models")
    print(f"  Expected root: {expected_root}")
    print(f"  Temporary: {args.temporary}")
    print(f"  Receipt: {receipt_path}")
    print()

    from cemm_authoritative_hybrid.training import reproduce_models

    receipt = reproduce_models(
        expected_root=ROOT,
        temporary=args.temporary,
        receipt_path=receipt_path,
    )

    print(f"Reproducibility status: {receipt['status']}")
    print(f"  Scratch outside repository: {receipt['scratch_outside_repository']}")
    print(f"  Proposal identity reproduced: {receipt['proposal']['model_identity_reproduced']}")
    print(f"  Realizer identity reproduced: {receipt['realizer']['model_identity_reproduced']}")
    print(f"  Receipt written to: {receipt_path}")

    if receipt["status"] != "reproduced":
        sys.exit(1)


if __name__ == "__main__":
    main()
