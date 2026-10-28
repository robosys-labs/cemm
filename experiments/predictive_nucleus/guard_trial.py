"""Paired public-development audit; neither a blind challenge nor G1 admission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from time import perf_counter

from .joint_score import summarize_joint_log_loss
from .protocol import read_protocol, verify_protocol
from .stability_trial import frozen_config
from .stress_protocol import verify as verify_stress_protocol
from .stress_trial import SCENARIOS, learning_data, rollout
from .stress_world import draw_world

HERE = Path(__file__).resolve().parent


def frozen_config_v5():
    source = HERE / "guard_protocol_v5.json"
    checksum = (HERE / "snapshots" / "guard_protocol_v5.sha256").read_text().split()[0]
    if hashlib.sha256(source.read_bytes()).hexdigest() != checksum:
        raise ValueError("guard protocol checksum mismatch")
    data = json.loads(source.read_text())
    g0 = read_protocol()
    verify_protocol(g0)
    old = verify_stress_protocol()
    v4 = frozen_config()
    if (data["schema_version"] != 5 or data["decision"] != "G1_NOT_ADMITTED" or
            list(SCENARIOS) != data["strata"] or
            any(list(v) != old["stress_development"]["scenarios"][k] for k, v in SCENARIOS.items()) or
            data["opened_v4_world_seeds"] != v4["gates"]["new_world_seeds"] or
            data["model_seeds"] != v4["gates"]["model_seeds"] or
            data["guard"] != {"mixture_weights": [0.5, 0.5], "alpha": 0.05,
                              "latch_conflicts_for_episode": True} or
            data["canonical_budget"]["max_physical_probes"] != 2):
        raise ValueError("guard protocol inventory drift")
    fresh = data["new_public_world_seeds"]
    forbidden = {seed for split in g0["splits"].values() for seed in split["seeds"]}
    forbidden.update(old["stress_development"]["world_seeds"])
    forbidden.update(data["opened_v4_world_seeds"])
    if len(fresh) != 5 or len(set(fresh)) != 5 or set(fresh) & forbidden:
        raise ValueError("new development seeds overlap existing lineages")
    return data


def summarize_paired(cases):
    if not cases or any(len(case["rollout"]["rows"]) != 2 for case in cases):
        raise ValueError("each physical trajectory requires both role directions")
    rows = [(case["case_id"] + f":direction-{direction}", row)
            for case in cases for direction, row in enumerate(case["rollout"]["rows"])]
    n = len(rows)
    bins = [[] for _ in range(10)]
    for _, row in rows:
        bins[min(9, int(row["joint_map_confidence"] * 10))].append(row)
    ece = sum(len(group) * abs(statistics.mean(r["joint_map_confidence"] for r in group) -
                               statistics.mean(r["joint_map_correct"] for r in group))
              for group in bins if group) / n
    latencies = sorted(t for case in cases for t in case["rollout"].get("guard_record_latency_ms", []))
    def score(key):
        covered = [row for _, row in rows if row[key]]
        wrong = sum(not row["joint_map_correct"] for row in covered)
        wrong_cases = []
        for case in cases:
            for direction, row in enumerate(case["rollout"]["rows"]):
                if row[key] and not row["joint_map_correct"]:
                    wrong_cases.append({
                        "case_id": case["case_id"] + f":direction-{direction}",
                        "target_action": row.get("target_action"), "world_ids": row.get("world_ids"),
                        "predicted_world": row.get("joint_map_world"), "truth_world": row.get("truth_world"),
                        "confidence": row["joint_map_confidence"],
                        "joint_log_score": row.get("joint_log_score"),
                        "initial_anchor": case["rollout"].get("initial_anchor"),
                        "probe_trace": case["rollout"].get("probe_trace", []),
                    })
        return {
            "coverage": len(covered) / n,
            "covered_wrong_per_query": wrong / n,
            "error_given_coverage": wrong / len(covered) if covered else None,
            "correct_abstained_per_query": sum(row["joint_map_correct"] and not row[key]
                                                for _, row in rows) / n,
            "covered_wrong_cases": wrong_cases,
            "correct_abstained_case_ids": [case for case, row in rows
                                           if row["joint_map_correct"] and not row[key]],
        }
    return {
        "worlds": len(cases), "target_queries": n,
        "unconditional_map_exact": statistics.mean(row["joint_map_correct"] for _, row in rows),
        "unconditional_wrong_case_ids": [case for case, row in rows if not row["joint_map_correct"]],
        "map_ece10": ece,
        "joint_nll": statistics.mean(row["joint_nll"] for _, row in rows) if "joint_nll" in rows[0][1] else None,
        "joint_log_score": summarize_joint_log_loss([row["joint_log_score"] for _, row in rows])
                           if "joint_log_score" in rows[0][1] else None,
        "bit_brier": statistics.mean(row["bit_brier"] for _, row in rows) if "bit_brier" in rows[0][1] else None,
        "legacy": score("eligible"), "guard": score("guard_eligible"),
        "previously_covered_wrong_now_abstained": [case for case, r in rows if r["eligible"] and
                                                    not r["guard_eligible"] and not r["joint_map_correct"]],
        "previously_covered_correct_now_abstained": [case for case, r in rows if r["eligible"] and
                                                      not r["guard_eligible"] and r["joint_map_correct"]],
        "newly_covered_wrong": [case for case, r in rows if not r["eligible"] and
                                r["guard_eligible"] and not r["joint_map_correct"]],
        "newly_covered_correct": [case for case, r in rows if not r["eligible"] and
                                  r["guard_eligible"] and r["joint_map_correct"]],
        "guard_portfolio_alarm_world_rate": statistics.mean(case["rollout"]["guard_portfolio_alarm"] for case in cases),
        "guard_conflict_world_rate": statistics.mean(bool(case["rollout"]["guard_conflicts"]) for case in cases),
        "mean_physical_probes": statistics.mean(case["rollout"]["probes"] for case in cases),
        "mean_set_probes": statistics.mean(case["rollout"]["set_probes"] for case in cases),
        "mean_observed_bits": statistics.mean(case["rollout"]["observed_bits"] for case in cases),
        "guard_record_p50_ms": statistics.median(latencies) if latencies else None,
        "guard_record_p95_ms": latencies[int(.95 * (len(latencies) - 1))] if latencies else None,
    }


def evaluate_kernel(kernel, cfg, world_count):
    result = {}
    for split, seeds in (("opened_v4", cfg["opened_v4_world_seeds"]),
                         ("fresh_public_v5", cfg["new_public_world_seeds"])):
        result[split] = {}
        for scenario in cfg["strata"]:
            cases = []
            for index in range(world_count):
                seed = seeds[index % len(seeds)]
                world = draw_world(seed, index, SCENARIOS[scenario][0])
                # A single rollout supplies both eligibility policies: neither
                # the guard nor evaluator truth changes a probe or posterior.
                trial = rollout(world, kernel, scenario=scenario, policy="active_validate",
                                seed=int(world.ids[0], 16), budget=2)
                cases.append({"case_id": f"{split}:{scenario}:{seed}:{index}", "rollout": trial})
            result[split][scenario] = summarize_paired(cases)
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
    cfg = frozen_config_v5()
    seeds = [int(x) for x in args.seeds.split(",")]
    if (not seeds or len(seeds) != len(set(seeds)) or any(s not in cfg["model_seeds"] for s in seeds) or
            min(args.train, args.calibration, args.worlds, args.steps) < 1):
        raise ValueError("invalid diagnostic seed or budget")
    canonical = cfg["canonical_budget"]
    canonical_run = (seeds == cfg["model_seeds"] and args.train == canonical["train"] and
                     args.calibration == canonical["calibration"] and
                     args.worlds == canonical["worlds_per_stratum"] and args.steps == canonical["steps"])
    torch.set_num_threads(1)
    start = perf_counter()
    train = learning_data("train", args.train)
    calibration = learning_data("calibration", args.calibration)
    results = []
    for seed in seeds:
        model, fit = fit_kernel(train, seed, steps=args.steps)
        kernel, calibration_report = calibrate(model, calibration)
        results.append({"model_seed": seed, "training": fit, "calibration": calibration_report,
                        "splits": evaluate_kernel(kernel, cfg, args.worlds)})
    print(json.dumps({"status": "PUBLIC_DEVELOPMENT_NOT_G1", "canonical_budget": canonical_run,
                      "elapsed_seconds": round(perf_counter() - start, 3), "results": results},
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
