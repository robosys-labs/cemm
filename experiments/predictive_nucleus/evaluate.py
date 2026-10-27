"""Strict complete-state scorer; only the evaluator receives oracle outcomes.

Model predictions are joined by case ID and opaque entity identity, never by
iteration order. Probability scores are on all observable and hidden entities.
The `smoke` command uses two hand-authored cases, NOT a scientific challenge.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from collections import defaultdict
from typing import Any


def _validate_truth(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["case_id"]
        if key in cases:
            raise ValueError("duplicate oracle case ID")
        truth = row["truth"]
        if not truth or not all(type(x) is int and x in (0, 1) for x in truth.values()):
            raise ValueError("oracle must contain the complete binary world")
        if "family" not in row or "seed" not in row:
            raise ValueError("missing oracle stratum/seed")
        cases[key] = row
    if not cases:
        raise ValueError("no oracle cases")
    return cases


def _validate_predictions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["case_id"]
        if key in predictions:
            raise ValueError("duplicate model case ID")
        predictions[key] = row
    return predictions


def _summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    answered = [x for x in items if not x["abstain"]]
    bits = [pair for x in answered for pair in x["bits"]]
    bin_counts = [0] * 10
    bin_conf = [0.0] * 10
    bin_true = [0.0] * 10
    for probability, truth in bits:
        bucket = min(9, int(probability * 10))
        bin_counts[bucket] += 1
        bin_conf[bucket] += probability
        bin_true[bucket] += truth
    ece = sum(abs(bin_conf[i] - bin_true[i]) for i in range(10)) / len(bits) if bits else None
    paired: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for x in items:
        if x["pair_id"] is not None:
            paired[x["pair_id"]].append(x)
    for key, members in paired.items():
        if len(members) != 2 or {x["direction"] for x in members} != {0, 1}:
            raise ValueError(f"incomplete / non-reversed oracle pair {key}")
    pair_exact = sum(all(not x["abstain"] and x["exact"] for x in pair) for pair in paired.values())
    return {
        "cases": total,
        "answered": len(answered),
        "answered_coverage": len(answered) / total,
        "abstention_rate": 1 - len(answered) / total,
        "full_world_exact": sum(x["exact"] for x in answered) / len(answered) if answered else None,
        "unconditional_full_world_exact": sum(x["exact"] for x in answered) / total,
        "per_entity_brier": sum((p - t) ** 2 for p, t in bits) / len(bits) if bits else None,
        "per_entity_nll": -sum(t * math.log(max(p, 1e-12)) + (1 - t) * math.log(max(1 - p, 1e-12)) for p, t in bits) / len(bits) if bits else None,
        "ece_10": ece,
        "role_pairs": len(paired),
        "role_pair_exact": pair_exact / len(paired) if paired else None,
    }


def score_predictions(
    oracle_rows: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    previous_predictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """No learner invoked here: oracle and predictions come from distinct inputs."""
    oracle = _validate_truth(oracle_rows)
    predictions = _validate_predictions(prediction_rows)
    if predictions.keys() != oracle.keys():
        raise ValueError("missing or extra prediction case ID")
    evaluated = []
    for key, gold in oracle.items():
        prediction = predictions[key]
        abstain = prediction.get("abstain", False)
        if type(abstain) is not bool:
            raise ValueError("abstain must be a boolean")
        if abstain:
            if prediction.get("p1") not in (None, {}):
                raise ValueError("abstaining prediction cannot assert state")
            bits = []
            exact = False
        else:
            probability = prediction["p1"]
            if probability.keys() != gold["truth"].keys():
                raise ValueError(f"identity alias, extra or missing entity: {key}")
            if not all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in probability.values()):
                raise ValueError("invalid probability")
            bits = [(float(probability[e]), gold["truth"][e]) for e in sorted(gold["truth"])]
            exact = all((p >= 0.5) == bool(truth) for p, truth in bits)
        evaluated.append({"case_id": key, "seed": gold["seed"], "family": gold["family"],
                          "pair_id": gold.get("pair_id"), "direction": gold.get("direction"),
                          "abstain": abstain, "bits": bits, "exact": exact})
    role_pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evaluated:
        if item["pair_id"] is not None:
            role_pairs[item["pair_id"]].append(item)
    for label, pair in role_pairs.items():
        if len(pair) != 2 or len({(x["family"], x["seed"]) for x in pair}) != 1:
            raise ValueError(f"role pair spans different strata or is incomplete: {label}")
    result = {"aggregate": _summarize(evaluated),
              "by_family": {name: _summarize([x for x in evaluated if x["family"] == name])
                            for name in sorted({x["family"] for x in evaluated})},
              "by_seed": {str(name): _summarize([x for x in evaluated if x["seed"] == name])
                          for name in sorted({x["seed"] for x in evaluated})}}
    if previous_predictions is not None:
        previous = score_predictions(oracle_rows, previous_predictions)
        # Count case-level repairs and regressions; never silently change the gold.
        prev_by_key = _validate_predictions(previous_predictions)
        def _is_exact(p: dict[str, Any], gold: dict[str, Any]) -> bool:
            if p.get("abstain", False):
                return False
            return all((p["p1"][e] >= 0.5) == bool(v) for e, v in gold["truth"].items())
        now = {x["case_id"]: x["exact"] for x in evaluated}
        result["regressions"] = {
            "previously_correct_now_wrong": [k for k in oracle if _is_exact(prev_by_key[k], oracle[k]) and not now[k]],
            "previously_wrong_now_correct": [k for k in oracle if not _is_exact(prev_by_key[k], oracle[k]) and now[k]],
            "prior_aggregate": previous["aggregate"],
        }
    return result


def smoke() -> None:
    # Deliberately mixed exact/wrong pair: exercises AND pairing, not a model result.
    oracle = [
        {"case_id": "toy-forward", "family": "synthetic", "seed": 0,
         "pair_id": "toy-pair", "direction": 0, "truth": {"A": 1, "B": 0, "C": 1}},
        {"case_id": "toy-reverse", "family": "synthetic", "seed": 0,
         "pair_id": "toy-pair", "direction": 1, "truth": {"A": 0, "B": 1, "C": 1}},
    ]
    predictions = [
        {"case_id": "toy-forward", "p1": {"A": 0.8, "B": 0.2, "C": 0.7}},
        {"case_id": "toy-reverse", "p1": {"A": 0.8, "B": 0.8, "C": 0.7}},
    ]
    print(json.dumps({"kind": "SCORER_SMOKE_ONLY_NOT_G1", "result": score_predictions(oracle, predictions)}, sort_keys=True))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"expected object in {path}:{line_number}")
        records.append(obj)
    return records


def main() -> None:
    from .protocol import LOCK, read_protocol, verify_protocol
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="command", required=True)
    cmd.add_parser("smoke", help="hand-authored scoring-fixture only")
    scoring = cmd.add_parser("score", help="score a frozen oracle JSONL against a separate model JSONL")
    scoring.add_argument("--oracle", type=Path, required=True)
    scoring.add_argument("--predictions", type=Path, required=True)
    scoring.add_argument("--previous", type=Path)
    args = parser.parse_args()
    if args.command == "smoke":
        smoke()
        return
    digest = LOCK.read_text(encoding="ascii").split()[0]
    verify_protocol(read_protocol(), digest)
    result = score_predictions(_read_jsonl(args.oracle), _read_jsonl(args.predictions),
                               _read_jsonl(args.previous) if args.previous else None)
    print(json.dumps({"protocol_sha256": digest, "status": "DIAGNOSTIC_UNADMITTED",
                      "metrics": result}, sort_keys=True))


if __name__ == "__main__":
    main()
