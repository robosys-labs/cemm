#!/usr/bin/env python3
"""Execute persisted public-runtime R3 activation canaries.

This command never invents semantic owners or expected artifact refs.  Every
passing row must be a real ``HybridRuntime.process`` result containing selected
VerifiedMeaning lineage, SituationContext, Decision, Effect/No-Effect receipt,
ResponseMeaning, six phase materials, and the exact R5 realization gap.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import CycleResult, SemanticPhase

DEFAULT_CASES = (
    ("observe", "Alice likes Bob."),
    ("query", "Who likes Bob?"),
    ("request", "Set the lamp power to on."),
    ("simulate", "If the lamp power is set to on, will it be on?"),
)


def _load_cases(path: Path | None) -> tuple[tuple[str, str], ...]:
    if path is None:
        return DEFAULT_CASES
    rows: list[tuple[str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if type(value) is not dict or set(value) != {"case_ref", "text"}:
            raise ValueError(f"case line {number} must contain only case_ref/text")
        if type(value["case_ref"]) is not str or not value["case_ref"]:
            raise TypeError(f"case line {number} has invalid case_ref")
        if type(value["text"]) is not str:
            raise TypeError(f"case line {number} has invalid text")
        rows.append((value["case_ref"], value["text"]))
    if not rows:
        raise ValueError("canary case source is empty")
    return tuple(rows)


def _verify_result(case_ref: str, result: CycleResult) -> dict[str, object]:
    if type(result) is not CycleResult:
        raise TypeError(f"{case_ref}: runtime returned non-canonical CycleResult")
    if result.verification is None or result.verification.status != "selected":
        raise ValueError(f"{case_ref}: canary did not select VerifiedMeaning")
    if result.evaluation is None:
        raise ValueError(f"{case_ref}: EVALUATE artifact is absent")
    if result.effect_receipt is None:
        raise ValueError(f"{case_ref}: effect/no-effect receipt is absent")
    if result.response_meaning is None:
        raise ValueError(f"{case_ref}: ResponseMeaning is absent")
    phases = tuple(row.phase for row in result.phase_material)
    if phases != tuple(SemanticPhase):
        raise ValueError(f"{case_ref}: cycle does not contain all six phases")
    gap = result.gap_receipt
    if (
        gap is None
        or gap.status != "later_owner_not_admitted"
        or gap.missing_contract_refs != ("contract:r5:realize_surface",)
    ):
        raise ValueError(f"{case_ref}: exact R5 realization boundary is absent")
    meaning = result.verification.selected_meaning
    assert meaning is not None
    return {
        "case_ref": case_ref,
        "cycle_ref": result.cycle_ref,
        "verified_meaning_ref": meaning.verified_meaning_ref,
        "expression_ref": meaning.expression.expression_ref,
        "evaluation_ref": result.evaluation.evaluation_ref,
        "decision_ref": result.evaluation.decision.decision_ref,
        "effect_receipt_ref": result.effect_receipt.receipt_ref,
        "response_meaning_ref": result.response_meaning.response_meaning_ref,
        "gap_ref": gap.gap_ref,
        "final_revision_pin": result.final_revision_pin.as_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime = load_runtime(
        args.root.resolve(),
        profile="development",
        store_path=args.store.resolve(),
    )
    rows: list[dict[str, object]] = []
    try:
        for index, (case_ref, text) in enumerate(_load_cases(args.cases)):
            result = runtime.process(f"r3-canary:{index}:{case_ref}", text, trace=True)
            rows.append(_verify_result(case_ref, result))
    finally:
        runtime.stores.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        {"schema": "cemm-r3-activation-canaries-v1", "cases": rows},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    args.output.write_text(raw, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
