#!/usr/bin/env python3
"""Execute persisted public-runtime R3 activation canaries.

This command never invents semantic owners or expected artifact refs. Every
passing row is produced by a real ``HybridRuntime.process`` result containing
selected VerifiedMeaning lineage, SituationContext, Decision, Effect/No-Effect
receipt, ResponseMeaning, six phase materials, and the exact R5 realization
gap. The output is deterministic for the supplied authority/runtime revision
and is suitable for committed R3 admission evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import SemanticPhase
from cemm_authoritative_hybrid.r3_cycle import CycleResult

DEFAULT_CASES = (
    ("observe", "Alice likes Bob."),
    ("query", "Who likes Bob?"),
    ("request", "Set the lamp power to on."),
    ("simulate", "If the lamp power is set to on, will it be on?"),
)
_REQUIRED_MODES = frozenset({"observe", "query", "request", "simulate"})


def _load_cases(path: Path | None) -> tuple[tuple[str, str], ...]:
    if path is None:
        return DEFAULT_CASES
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if type(value) is not dict or set(value) != {"case_ref", "text"}:
            raise ValueError(f"case line {number} must contain only case_ref/text")
        case_ref = value["case_ref"]
        text = value["text"]
        if type(case_ref) is not str or not case_ref or case_ref != case_ref.strip():
            raise TypeError(f"case line {number} has invalid case_ref")
        if case_ref in seen:
            raise ValueError(f"case line {number} duplicates case_ref {case_ref}")
        if type(text) is not str or not text or text != text.strip():
            raise TypeError(f"case line {number} has invalid text")
        seen.add(case_ref)
        rows.append((case_ref, text))
    if not rows:
        raise ValueError("canary case source is empty")
    return tuple(rows)


def _verify_result(case_ref: str, result: CycleResult) -> dict[str, object]:
    if type(result) is not CycleResult:
        raise TypeError(f"{case_ref}: runtime returned non-canonical R3 CycleResult")
    if result.verification is None or result.verification.status != "selected":
        raise ValueError(f"{case_ref}: canary did not select VerifiedMeaning")
    if result.evaluation is None:
        raise ValueError(f"{case_ref}: EVALUATE artifact is absent")
    if result.effect_receipt is None:
        raise ValueError(f"{case_ref}: effect/no-effect receipt is absent")
    if result.response_meaning is None:
        raise ValueError(f"{case_ref}: ResponseMeaning is absent")
    if result.orientation is None:
        raise ValueError(f"{case_ref}: Orientation is absent")
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
    situation = result.evaluation.situation
    if situation.mode is not result.orientation.mode:
        raise ValueError(f"{case_ref}: situation/orientation semantic mode mismatch")
    return {
        "case_ref": case_ref,
        "semantic_mode": situation.mode.value,
        "cycle_ref": result.cycle_ref,
        "verified_meaning_ref": meaning.verified_meaning_ref,
        "expression_ref": meaning.expression.expression_ref,
        "situation_ref": situation.situation_ref,
        "evaluation_ref": result.evaluation.evaluation_ref,
        "decision_ref": result.evaluation.decision.decision_ref,
        "effect_receipt_ref": result.effect_receipt.receipt_ref,
        "response_meaning_ref": result.response_meaning.response_meaning_ref,
        "gap_ref": gap.gap_ref,
        "final_revision_pin": result.final_revision_pin.as_dict(),
    }


def execute_canaries(
    root: Path,
    store: Path,
    *,
    cases_path: Path | None = None,
) -> tuple[dict[str, object], ...]:
    """Execute the canonical development runtime and return exact canary rows."""
    runtime = load_runtime(
        root.resolve(),
        profile="development",
        store_path=store.resolve(),
    )
    rows: list[dict[str, object]] = []
    try:
        for index, (case_ref, text) in enumerate(_load_cases(cases_path)):
            result = runtime.process(f"r3-canary:{index}:{case_ref}", text, trace=True)
            rows.append(_verify_result(case_ref, result))
    finally:
        runtime.stores.close()
    modes = {str(row["semantic_mode"]) for row in rows}
    if modes != _REQUIRED_MODES:
        raise ValueError(
            "R3 canaries must authentically cover observe/query/request/simulate; "
            f"observed={sorted(modes)}"
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = execute_canaries(
        args.root.resolve(),
        args.store.resolve(),
        cases_path=args.cases,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        {"schema": "cemm-r3-activation-canaries-v1", "cases": list(rows)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    args.output.write_text(raw, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
