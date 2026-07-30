#!/usr/bin/env python3
"""Calibrate the release proposal and realizer models on validation data only.

Usage:
    python scripts/calibrate_models.py --proposal artifacts/proposal_release \
        --realizer artifacts/realizer_release \
        --validation data/partitions/validation.jsonl \
        --output artifacts/calibration.json
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
        description="Calibrate release models on validation data only."
    )
    parser.add_argument(
        "--proposal",
        default="artifacts/proposal_release",
        help="Path to the proposal release artifact directory.",
    )
    parser.add_argument(
        "--realizer",
        default="artifacts/realizer_release",
        help="Path to the realizer release artifact directory.",
    )
    parser.add_argument(
        "--validation",
        default="data/partitions/validation.jsonl",
        help="Path to the validation partition JSONL.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/calibration.json",
        help="Path to write the calibration receipt JSON.",
    )
    args = parser.parse_args()

    proposal_dir = ROOT / args.proposal
    realizer_dir = ROOT / args.realizer
    validation_path = ROOT / args.validation
    output_path = ROOT / args.output

    print(f"Calibrating release models")
    print(f"  Proposal: {proposal_dir}")
    print(f"  Realizer: {realizer_dir}")
    print(f"  Validation: {validation_path}")
    print(f"  Output: {output_path}")
    print()

    from cemm_authoritative_hybrid.training import calibrate_models

    receipt = calibrate_models(
        proposal_dir=proposal_dir,
        realizer_dir=realizer_dir,
        validation_path=validation_path,
        root=ROOT,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    print(f"Calibration complete!")
    print(f"  Input hash: {receipt['input_hash']}")
    print(f"  Expected calibration error: {receipt['expected_calibration_error']}")
    print(f"  Proposal model identity: {receipt['proposal_model_identity']}")
    print(f"  Realizer model identity: {receipt['realizer_model_identity']}")
    print(f"  Episodes: {receipt['num_episodes']}")
    print(f"  Receipt written to: {output_path}")


if __name__ == "__main__":
    main()
