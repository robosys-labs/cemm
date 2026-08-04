#!/usr/bin/env python3
"""Evaluate CEMM semantic accuracy, safety, and limitations (M4 Task 4).

Usage:
    python scripts/evaluate_cemm.py --runtime release \
        --episodes data/partitions/test.jsonl \
        --output artifacts/evaluation/CEMM_EVALUATION.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate CEMM semantic accuracy and safety on the test partition."
    )
    parser.add_argument(
        "--runtime",
        default="release",
        help="Runtime profile to evaluate (default: release).",
    )
    parser.add_argument(
        "--episodes",
        default="data/partitions/test.jsonl",
        help="Path to the test partition JSONL.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/evaluation/CEMM_EVALUATION.json",
        help="Path to write the evaluation report JSON.",
    )
    parser.add_argument(
        "--calibration",
        default="artifacts/calibration.json",
        help="Path to the calibration artifact JSON.",
    )
    args = parser.parse_args()

    episodes_path = ROOT / args.episodes
    output_path = ROOT / args.output
    calibration_path = ROOT / args.calibration

    print("CEM Evaluation")
    print(f"  Episodes: {episodes_path}")
    print(f"  Output:   {output_path}")
    print(f"  Calibration: {calibration_path}")
    print()

    from cemm_authoritative_hybrid.bootstrap import load_runtime
    from cemm_authoritative_hybrid.evaluation import Evaluator

    runtime = load_runtime(ROOT, profile=args.runtime)
    evaluator = Evaluator(
        runtime=runtime,
        test_episodes_path=episodes_path,
        root=ROOT,
        calibration_path=calibration_path,
    )

    report = evaluator.evaluate()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.to_json(), encoding="utf-8")

    print(f"Evaluation complete! Status: {report.status}")
    print(f"  Episodes: {report.num_episodes}")
    print()
    print("Metrics:")
    print(f"  illegal_program_rejection:      {report.illegal_program_rejection}")
    print(f"  effect_safety_accuracy:         {report.effect_safety_accuracy}")
    print(f"  exact_program_accuracy:         {report.exact_program_accuracy}")
    print(f"  end_to_end_accuracy:            {report.end_to_end_accuracy}")
    print(f"  abstention_precision:           {report.abstention_precision}")
    print(f"  abstention_recall:              {report.abstention_recall}")
    print(f"  expected_calibration_error:     {report.expected_calibration_error}")
    print(f"  realization_equivalence:        {report.realization_equivalence}")
    print(f"  proposal_zero_weight_accuracy:  {report.proposal_zero_weight_accuracy}")
    print(f"  proposal_weight_accuracy_drop:  {report.proposal_weight_accuracy_drop}")
    print(f"  realizer_zero_weight_accuracy:  {report.realizer_zero_weight_accuracy}")
    print(f"  realizer_weight_accuracy_drop:  {report.realizer_weight_accuracy_drop}")
    print(f"  bootstrap_delegate_calls:       {report.bootstrap_delegate_calls}")
    print(f"  unreviewed_atom_creations:      {report.unreviewed_atom_creations}")
    print(f"  raw_surface_dispatches:         {report.raw_surface_dispatches}")
    print()
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
