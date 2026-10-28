"""Paired context-support diagnostic on open and new public worlds; not G1."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
from time import perf_counter

from .guard_trial import frozen_config_v5, summarize_paired
from .protocol import read_protocol
from .stress_trial import SCENARIOS, learning_data, rollout
from .stress_world import draw_world

HERE = Path(__file__).resolve().parent


def frozen_config_v6():
    path = HERE / "context_protocol_v6.json"
    lock = (HERE / "snapshots" / "context_protocol_v6.sha256").read_text().split()[0]
    if hashlib.sha256(path.read_bytes()).hexdigest() != lock:
        raise ValueError("context protocol checksum mismatch")
    cfg = json.loads(path.read_text())
    prior = frozen_config_v5()
    base = read_protocol()
    if (cfg["schema_version"] != 6 or cfg["decision"] != "G1_NOT_ADMITTED" or
            cfg["strata"] != list(SCENARIOS) or cfg["opened_v5_world_seeds"] != prior["new_public_world_seeds"] or
            cfg["model_seeds"] != prior["model_seeds"] or
            cfg["context_contract"] != {"context_fields": ["action_kind", "ordered_observed_input_bits"],
                "min_completed_events": 1, "scope": "episode", "cross_entity_sharing": True,
                "input_source": "verified initial anchor or subsequent received sensor reading",
                "postcondition": "both action participants observed after actual contact",
                "affected_scope": "assumed action participants only", "unobserved_input": "abstain",
                "no_oracle_or_future_feedback": True} or
            cfg["canonical_budget"]["max_physical_probes"] != 2):
        raise ValueError("context protocol inventory drift")
    forbidden = {s for split in base["splits"].values() for s in split["seeds"]}
    forbidden.update((601, 607, 613, 617, 619))
    forbidden.update(prior["opened_v4_world_seeds"])
    forbidden.update(prior["new_public_world_seeds"])
    fresh = cfg["new_public_world_seeds"]
    if len(fresh) != 5 or len(set(fresh)) != 5 or set(fresh) & forbidden:
        raise ValueError("new context worlds overlap prior lineages")
    return cfg


def summarize_context(cases):
    paired = []
    statuses = Counter()
    update_latencies, assess_latencies = [], []
    for case in cases:
        rollout_data = case["rollout"]
        adjusted = dict(rollout_data)
        adjusted_rows = []
        for row in rollout_data["rows"]:
            if row["context_eligible"] and not row["guard_eligible"]:
                raise ValueError("context policy cannot add covered predictions")
            if row["guard_eligible"]:
                statuses[row["context_status"]] += 1
            assess_latencies.append(row["context_assess_latency_ms"])
            adjusted_rows.append({**row, "eligible": row["guard_eligible"],
                                   "guard_eligible": row["context_eligible"]})
        adjusted["rows"] = adjusted_rows
        update_latencies.extend(rollout_data["context_update_latency_ms"])
        paired.append({"case_id": case["case_id"], "rollout": adjusted})
    out = summarize_paired(paired)
    out["baseline_guard"] = out.pop("legacy")
    out["context_guard"] = out.pop("guard")
    out["baseline_covered_context_reasons"] = dict(sorted(statuses.items()))
    def p95(values):
        values = sorted(values)
        return values[int(.95 * (len(values) - 1))] if values else None
    out["context_update_p95_ms"] = p95(update_latencies)
    out["context_assess_p95_ms"] = p95(assess_latencies)
    return out


def evaluate_kernel(kernel, cfg, worlds):
    result = {}
    for split, seeds in (("opened_v5", cfg["opened_v5_world_seeds"]),
                         ("new_public_v6", cfg["new_public_world_seeds"])):
        result[split] = {}
        for scenario in cfg["strata"]:
            cases = []
            for index in range(worlds):
                seed = seeds[index % len(seeds)]
                world = draw_world(seed, index, SCENARIOS[scenario][0])
                trial = rollout(world, kernel, scenario=scenario, policy="active_validate",
                                seed=int(world.ids[0], 16), budget=2)
                cases.append({"case_id": f"{split}:{scenario}:{seed}:{index}", "rollout": trial})
            result[split][scenario] = summarize_context(cases)
    return result


def main():
    import torch
    from .calibration import calibrate
    from .latent_model import fit_kernel

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train", type=int, default=600)
    p.add_argument("--calibration", type=int, default=200)
    p.add_argument("--worlds", type=int, default=10)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--seeds", default="7,11,23,37,53")
    args = p.parse_args()
    cfg = frozen_config_v6()
    seeds = [int(x) for x in args.seeds.split(",")]
    if (not seeds or len(seeds) != len(set(seeds)) or any(s not in cfg["model_seeds"] for s in seeds) or
            min(args.train, args.calibration, args.worlds, args.steps) < 1):
        raise ValueError("invalid development budget or seeds")
    budget = cfg["canonical_budget"]
    canonical = (seeds == cfg["model_seeds"] and args.train == budget["train"] and
                 args.calibration == budget["calibration"] and args.worlds == budget["worlds_per_stratum"]
                 and args.steps == budget["steps"])
    torch.set_num_threads(1)
    started = perf_counter()
    train, calibration = learning_data("train", args.train), learning_data("calibration", args.calibration)
    results = []
    for seed in seeds:
        model, fit = fit_kernel(train, seed, steps=args.steps)
        kernel, calibrated = calibrate(model, calibration)
        results.append({"model_seed": seed, "training": fit, "calibration": calibrated,
                        "splits": evaluate_kernel(kernel, cfg, args.worlds)})
    print(json.dumps({"status": "PUBLIC_DEVELOPMENT_NOT_G1", "canonical_budget": canonical,
                      "elapsed_seconds": round(perf_counter() - started, 3), "results": results},
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
