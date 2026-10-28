"""Public equal-update versus equal-wall flat ablation, not a G1 challenge."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

from .flat_trial import evaluate_models, frozen_config_v7, reference_episodes
from .protocol import read_protocol

HERE = Path(__file__).resolve().parent


def frozen_config_v8():
    path = HERE / "flat_updates_protocol_v8.json"
    lock = (HERE / "snapshots" / "flat_updates_protocol_v8.sha256").read_text().split()[0]
    if hashlib.sha256(path.read_bytes()).hexdigest() != lock:
        raise ValueError("flat update protocol checksum mismatch")
    cfg = json.loads(path.read_text())
    prior = frozen_config_v7()
    if (cfg["schema_version"] != 8 or cfg["decision"] != "G1_NOT_ADMITTED" or
            cfg["opened_v7_world_seeds"] != prior["new_public_world_seeds"] or
            cfg["model_seeds"] != prior["model_seeds"] or cfg["strata"] != prior["strata"] or
            cfg["canonical_budget"]["max_physical_probes"] != 2 or
            cfg["canonical_budget"]["cpu_threads"] != 1 or
            cfg["canonical_budget"]["structured_steps"] != cfg["canonical_budget"]["equal_flat_steps"] or
            not all(cfg["integrity"].values())):
        raise ValueError("flat update protocol inventory drift")
    forbidden = {s for split in read_protocol()["splits"].values() for s in split["seeds"]}
    forbidden.update((601, 607, 613, 617, 619, 701, 709, 719, 727, 733,
                      811, 821, 823, 827, 829, 911, 919, 929, 937, 941))
    forbidden.update(prior["new_public_world_seeds"])
    fresh = cfg["new_public_world_seeds"]
    if len(fresh) != 5 or len(set(fresh)) != 5 or set(fresh) & forbidden:
        raise ValueError("equal-update worlds overlap existing lineages")
    return cfg


def evaluate_pair(kernel, wall_flat, wall_temperature, equal_flat, equal_temperature, cfg, worlds):
    alias = {"opened_v6_world_seeds": cfg["opened_v7_world_seeds"],
             "new_public_world_seeds": cfg["new_public_world_seeds"], "strata": cfg["strata"]}
    labels = ("opened_v7", "new_public_v8")
    wall = evaluate_models(kernel, wall_flat, wall_temperature, alias, worlds, split_names=labels)
    equal = evaluate_models(kernel, equal_flat, equal_temperature, alias, worlds, split_names=labels)
    results = {}
    for split in labels:
        results[split] = {}
        for scenario in cfg["strata"]:
            a, b = wall[split][scenario], equal[split][scenario]
            if (a["public_trajectory_digests"] != b["public_trajectory_digests"] or
                    a["structured"] != b["structured"] or
                    a["structured_correct_case_ids"] != b["structured_correct_case_ids"] or
                    a["mean_physical_probes"] != b["mean_physical_probes"]):
                raise ValueError("paired comparison did not replay identical physical observations")
            wall_correct = set(a["flat_correct_case_ids"])
            equal_correct = set(b["flat_correct_case_ids"])
            results[split][scenario] = {
                "worlds": worlds, "structured": a["structured"],
                "structured_context": a["structured_context"],
                "wall_flat": a["flat"], "equal_update_flat": b["flat"],
                "wall_flat_pair_both_exact": a["flat_pair_both_exact"],
                "equal_flat_pair_both_exact": b["flat_pair_both_exact"],
                "equal_update_repairs": sorted(equal_correct - wall_correct),
                "equal_update_regressions": sorted(wall_correct - equal_correct),
                "structured_zero_probability_case_ids": a["structured_zero_probability_case_ids"],
                "wall_flat_zero_probability_case_ids": a["flat_zero_probability_case_ids"],
                "equal_flat_zero_probability_case_ids": b["flat_zero_probability_case_ids"],
                "structured_floor_applied_case_ids": a["structured_floor_applied_case_ids"],
                "wall_flat_floor_applied_case_ids": a["flat_floor_applied_case_ids"],
                "equal_flat_floor_applied_case_ids": b["flat_floor_applied_case_ids"],
                "public_trajectory_digests": a["public_trajectory_digests"],
                "mean_physical_probes": a["mean_physical_probes"],
                "wall_flat_target_p95_ms": a["flat_target_preview_p95_ms"],
                "equal_flat_target_p95_ms": b["flat_target_preview_p95_ms"],
            }
    return results


def main():
    import torch
    from .calibration import calibrate
    from .flat_reference import batch_episodes, calibrate_flat, fit_flat
    from .latent_model import build_samples, fit_kernel

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=int, default=600)
    parser.add_argument("--calibration", type=int, default=200)
    parser.add_argument("--worlds", type=int, default=10)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seeds", default="7,11,23,37,53")
    args = parser.parse_args()
    cfg = frozen_config_v8()
    seeds = [int(x) for x in args.seeds.split(",")]
    if (not seeds or len(seeds) != len(set(seeds)) or any(s not in cfg["model_seeds"] for s in seeds) or
            min(args.train, args.calibration, args.worlds, args.steps) < 1):
        raise ValueError("invalid development budget or seeds")
    budget = cfg["canonical_budget"]
    canonical = (seeds == cfg["model_seeds"] and args.train == budget["train"] and
                 args.calibration == budget["calibration"] and args.worlds == budget["worlds_per_stratum"] and
                 args.steps == budget["structured_steps"] == budget["equal_flat_steps"])
    torch.set_num_threads(1)
    warm = torch.nn.Linear(1, 1)
    optimizer = torch.optim.Adam(warm.parameters(), lr=.02)
    optimizer.zero_grad()
    warm(torch.ones(1, 1)).sum().backward()
    optimizer.step()
    training = reference_episodes("train", args.train)
    calibration = reference_episodes("calibration", args.calibration)
    start = perf_counter()
    structured_train, structured_calib = build_samples(training), build_samples(calibration)
    structured_preprocess = perf_counter() - start
    start = perf_counter()
    flat_train, flat_calib = batch_episodes(training), batch_episodes(calibration)
    flat_preprocess = perf_counter() - start
    results = []
    for seed in seeds:
        start = perf_counter()
        model, structured_fit = fit_kernel(structured_train, seed, steps=args.steps)
        structured_seconds = perf_counter() - start
        start = perf_counter()
        kernel, structured_calibration = calibrate(model, structured_calib)
        structured_calibration_seconds = perf_counter() - start
        wall_model, wall_fit = fit_flat(flat_train, seed, max_steps=args.steps,
                                        wall_budget_seconds=structured_seconds)
        start = perf_counter()
        wall_temp, wall_calibration = calibrate_flat(wall_model, flat_calib)
        wall_calibration_seconds = perf_counter() - start
        equal_model, equal_fit = fit_flat(flat_train, seed, max_steps=args.steps,
                                          wall_budget_seconds=structured_seconds, fixed_steps=args.steps)
        start = perf_counter()
        equal_temp, equal_calibration = calibrate_flat(equal_model, flat_calib)
        equal_calibration_seconds = perf_counter() - start
        if (structured_fit["parameters"] != 1446 or wall_fit["parameters"] != 1457 or
                equal_fit["parameters"] != 1457 or equal_fit["gradient_steps"] != args.steps):
            raise ValueError("unreviewed parameter or optimizer budget")
        results.append({"model_seed": seed, "structured_training": structured_fit,
                        "structured_fit_seconds": structured_seconds,
                        "structured_calibration": structured_calibration,
                        "structured_calibration_seconds": structured_calibration_seconds,
                        "wall_flat_training": wall_fit, "wall_flat_calibration": wall_calibration,
                        "wall_flat_calibration_seconds": wall_calibration_seconds,
                        "equal_flat_training": equal_fit, "equal_flat_calibration": equal_calibration,
                        "equal_flat_calibration_seconds": equal_calibration_seconds,
                        "equal_flat_to_structured_fit_time_ratio": equal_fit["fit_seconds"] / structured_seconds,
                        "splits": evaluate_pair(kernel, wall_model, wall_temp, equal_model, equal_temp,
                                                cfg, args.worlds)})
    print(json.dumps({"status": "PUBLIC_DEVELOPMENT_NOT_G1", "canonical_budget": canonical,
                      "hardware": {"machine": platform.machine(), "processor": platform.processor(),
                                   "python": platform.python_version(), "torch": torch.__version__,
                                   "threads": torch.get_num_threads()},
                      "structured_preprocess_seconds": structured_preprocess,
                      "flat_preprocess_seconds": flat_preprocess, "results": results},
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
