"""Public paired flat-GRU reference; approximate CPU budget, not G1 admission."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import statistics
from time import perf_counter

from .context_trial import frozen_config_v6
from .joint_score import joint_log_loss, summarize_joint_log_loss
from .protocol import read_protocol
from .stress_trial import SCENARIOS, rollout
from .stress_world import draw_world
from .world import make_episode

HERE = Path(__file__).resolve().parent


def frozen_config_v7():
    path = HERE / "flat_protocol_v7.json"
    lock = (HERE / "snapshots" / "flat_protocol_v7.sha256").read_text().split()[0]
    if hashlib.sha256(path.read_bytes()).hexdigest() != lock:
        raise ValueError("flat reference protocol checksum mismatch")
    cfg = json.loads(path.read_text())
    v6 = frozen_config_v6()
    if (cfg["schema_version"] != 7 or cfg["decision"] != "G1_NOT_ADMITTED" or
            cfg["opened_v6_world_seeds"] != v6["new_public_world_seeds"] or
            cfg["model_seeds"] != v6["model_seeds"] or cfg["strata"] != list(SCENARIOS) or
            cfg["flat_architecture"]["input_width"] != 36 or
            cfg["flat_architecture"]["hidden_units"] != 7 or
            cfg["flat_architecture"]["joint_output_states"] != 64 or
            cfg["flat_architecture"]["parameters_expected"] != 1457 or
            cfg["flat_architecture"]["structured_parameters_expected"] != 1446 or
            cfg["canonical_budget"]["max_physical_probes"] != 2 or
            cfg["canonical_budget"]["cpu_threads"] != 1):
        raise ValueError("flat reference protocol inventory drift")
    forbidden = {s for split in read_protocol()["splits"].values() for s in split["seeds"]}
    forbidden.update((601, 607, 613, 617, 619, 701, 709, 719, 727, 733))
    forbidden.update(v6["opened_v5_world_seeds"])
    forbidden.update(v6["new_public_world_seeds"])
    fresh = cfg["new_public_world_seeds"]
    if len(fresh) != 5 or len(set(fresh)) != 5 or set(fresh) & forbidden:
        raise ValueError("flat reference world seed overlap")
    return cfg


def reference_episodes(split, count):
    seeds = read_protocol()["splits"][split]["seeds"]
    return [make_episode(split, seeds[i % len(seeds)], i,
                         ("single_contact", "two_contacts")[i % 2]) for i in range(count)]


def replay_observed(flat_model, anchor, probe_trace, *, sensor_error_rate, temperature):
    """Pass only public actions and received readings into the baseline."""
    flat_model.reset(anchor, sensor_error_rate=sensor_error_rate)
    for step in probe_trace:
        flat_model.commit(step["action"], temperature=temperature)
        flat_model.receive(step["observation"])


def _score(rows, eligibility):
    covered = [r for r in rows if r[eligibility]]
    bins = [[] for _ in range(10)]
    for r in rows:
        bins[min(9, int(r["confidence"] * 10))].append(r)
    ece = sum(len(g) * abs(statistics.mean(r["confidence"] for r in g) -
                           statistics.mean(r["correct"] for r in g)) for g in bins if g) / len(rows)
    wrong = sum(not r["correct"] for r in covered)
    return {"queries": len(rows), "joint_map_exact": statistics.mean(r["correct"] for r in rows),
            "joint_nll": statistics.mean(r["joint_nll"] for r in rows),
            "joint_log_score": summarize_joint_log_loss([r["joint_log_score"] for r in rows]),
            "bit_brier": statistics.mean(r["bit_brier"] for r in rows), "joint_map_ece10": ece,
            "coverage": len(covered) / len(rows), "covered_wrong_per_query": wrong / len(rows),
            "error_given_coverage": wrong / len(covered) if covered else None}


def _p95(values):
    values = sorted(values)
    return values[int(.95 * (len(values) - 1))] if values else None


def evaluate_models(kernel, flat, temperature, cfg, world_count,
                    split_names=("opened_v6", "new_public_v7")):
    results = {}
    for split, seeds in ((split_names[0], cfg["opened_v6_world_seeds"]),
                         (split_names[1], cfg["new_public_world_seeds"])):
        results[split] = {}
        for scenario in cfg["strata"]:
            structured, flat_rows, paired = [], [], []
            costs = []
            trajectory_digests = []
            replay_latency, flat_latency, structured_latency = [], [], []
            for index in range(world_count):
                seed = seeds[index % len(seeds)]
                world = draw_world(seed, index, SCENARIOS[scenario][0])
                case_id = f"{split}:{scenario}:{seed}:{index}"
                trial = rollout(world, kernel, scenario=scenario, policy="active_validate",
                                seed=int(world.ids[0], 16), budget=2)
                public_trace = {"anchor": trial["initial_anchor"],
                                "probes": [{"action": p["action"], "observation": p["observation"]}
                                           for p in trial["probe_trace"]],
                                "targets": [row["target_action"] for row in trial["rows"]],
                                "supplied_sensor_error": SCENARIOS[scenario][-1]}
                digest = hashlib.sha256(json.dumps(public_trace, sort_keys=True,
                                                    separators=(",", ":")).encode()).hexdigest()
                trajectory_digests.append({"case_id": case_id, "sha256": digest})
                costs.append(trial["probes"])
                started = perf_counter()
                replay_observed(flat, trial["initial_anchor"], trial["probe_trace"],
                                sensor_error_rate=SCENARIOS[scenario][-1], temperature=temperature)
                replay_latency.append((perf_counter() - started) * 1000)
                world_pair = []
                for direction, row in enumerate(trial["rows"]):
                    if tuple(row["world_ids"]) != flat.ids:
                        raise ValueError("different entity ordering")
                    started = perf_counter()
                    distribution, _ = flat.preview(row["target_action"], temperature=temperature)
                    flat_latency.append((perf_counter() - started) * 1000)
                    # Evaluator truth is read strictly AFTER the flat forecast.
                    truth = tuple(row["truth_world"])
                    best = min(distribution, key=lambda state: (-distribution[state], state))
                    confidence = distribution[best]
                    p_truth = distribution.get(truth, 0.0)
                    marginals = [sum(p for bits, p in distribution.items() if bits[i])
                                 for i in range(len(flat.ids))]
                    brier = statistics.mean((p - actual) ** 2 for p, actual in zip(marginals, truth))
                    f = {"case_id": case_id + f":direction-{direction}", "correct": best == truth,
                         "confidence": confidence, "joint_nll": -math.log(max(p_truth, 1e-12)),
                         "joint_log_score": joint_log_loss(p_truth),
                         "bit_brier": brier, "eligible": confidence >= .95}
                    s = {"case_id": f["case_id"], "correct": row["joint_map_correct"],
                         "confidence": row["joint_map_confidence"], "joint_nll": row["joint_nll"],
                         "joint_log_score": row["joint_log_score"],
                         "bit_brier": row["bit_brier"], "eligible": row["guard_eligible"],
                         "context_eligible": row["context_eligible"]}
                    structured_latency.append(row["structured_target_latency_ms"])
                    structured.append(s)
                    flat_rows.append(f)
                    world_pair.append((s, f))
                paired.append(world_pair)
            results[split][scenario] = {
                "worlds": world_count,
                "structured": _score(structured, "eligible"),
                "structured_context": _score(structured, "context_eligible"),
                "flat": _score(flat_rows, "eligible"),
                "structured_pair_both_exact": statistics.mean(all(s["correct"] for s, _ in pair) for pair in paired),
                "flat_pair_both_exact": statistics.mean(all(f["correct"] for _, f in pair) for pair in paired),
                "structured_correct_case_ids": [s["case_id"] for pair in paired for s, _ in pair if s["correct"]],
                "flat_correct_case_ids": [f["case_id"] for pair in paired for _, f in pair if f["correct"]],
                "structured_zero_probability_case_ids": [s["case_id"] for pair in paired for s, _ in pair
                                                         if s["joint_log_score"]["zero_probability"]],
                "flat_zero_probability_case_ids": [f["case_id"] for pair in paired for _, f in pair
                                                   if f["joint_log_score"]["zero_probability"]],
                "structured_floor_applied_case_ids": [s["case_id"] for pair in paired for s, _ in pair
                                                      if s["joint_log_score"]["floor_applied"]],
                "flat_floor_applied_case_ids": [f["case_id"] for pair in paired for _, f in pair
                                                if f["joint_log_score"]["floor_applied"]],
                "public_trajectory_digests": trajectory_digests,
                "structured_correct_flat_wrong": [s["case_id"] for pair in paired for s, f in pair
                                                  if s["correct"] and not f["correct"]],
                "flat_correct_structured_wrong": [s["case_id"] for pair in paired for s, f in pair
                                                  if f["correct"] and not s["correct"]],
                "mean_physical_probes": statistics.mean(costs),
                "flat_probe_replay_p95_ms": _p95(replay_latency),
                "flat_target_preview_p95_ms": _p95(flat_latency),
                "structured_target_decision_and_forecast_p95_ms": _p95(structured_latency),
            }
    return results


def main():
    import torch
    from .calibration import calibrate
    from .flat_reference import batch_episodes, calibrate_flat, fit_flat
    from .latent_model import build_samples, fit_kernel

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train", type=int, default=600)
    p.add_argument("--calibration", type=int, default=200)
    p.add_argument("--worlds", type=int, default=10)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--seeds", default="7,11,23,37,53")
    p.add_argument("--flat-steps", help="replay recorded flat steps, one per model seed")
    args = p.parse_args()
    cfg = frozen_config_v7()
    seeds = [int(x) for x in args.seeds.split(",")]
    schedule = [int(x) for x in args.flat_steps.split(",")] if args.flat_steps else None
    if (not seeds or len(seeds) != len(set(seeds)) or any(s not in cfg["model_seeds"] for s in seeds) or
            min(args.train, args.calibration, args.worlds, args.steps) < 1 or
            (schedule is not None and (len(schedule) != len(seeds) or any(x < 1 or x > args.steps for x in schedule)))):
        raise ValueError("invalid reference budget, seeds or replay schedule")
    budget = cfg["canonical_budget"]
    canonical = (schedule is None and seeds == cfg["model_seeds"] and args.train == budget["train"] and
                 args.calibration == budget["calibration"] and args.worlds == budget["worlds_per_stratum"] and
                 args.steps == budget["structured_steps"])
    torch.set_num_threads(1)
    # Warm optimizer initialization outside both separately recorded budgets.
    warm = torch.nn.Linear(1, 1)
    opt = torch.optim.Adam(warm.parameters(), lr=.02)
    opt.zero_grad()
    warm(torch.ones(1, 1)).sum().backward()
    opt.step()
    train_episodes = reference_episodes("train", args.train)
    calibration_episodes = reference_episodes("calibration", args.calibration)
    started = perf_counter(); structured_train = build_samples(train_episodes); structured_calib = build_samples(calibration_episodes)
    structured_preprocess_seconds = perf_counter() - started
    started = perf_counter(); flat_train = batch_episodes(train_episodes); flat_calib = batch_episodes(calibration_episodes)
    flat_preprocess_seconds = perf_counter() - started
    results = []
    for i, seed in enumerate(seeds):
        started = perf_counter(); model, fit = fit_kernel(structured_train, seed, steps=args.steps)
        structured_fit_seconds = perf_counter() - started
        started = perf_counter(); kernel, calibrated = calibrate(model, structured_calib)
        structured_calibration_seconds = perf_counter() - started
        flat, flat_fit = fit_flat(flat_train, seed, max_steps=args.steps, wall_budget_seconds=structured_fit_seconds,
                                  fixed_steps=schedule[i] if schedule is not None else None)
        started = perf_counter(); temperature, flat_calibration = calibrate_flat(flat, flat_calib)
        flat_calibration_seconds = perf_counter() - started
        if (fit["parameters"] != cfg["flat_architecture"]["structured_parameters_expected"] or
                flat_fit["parameters"] != cfg["flat_architecture"]["parameters_expected"]):
            raise ValueError("parameter budget drift")
        results.append({"model_seed": seed, "structured_training": fit, "structured_fit_seconds": structured_fit_seconds,
                        "structured_calibration": calibrated, "structured_calibration_seconds": structured_calibration_seconds,
                        "flat_training": flat_fit, "flat_calibration": flat_calibration,
                        "flat_calibration_seconds": flat_calibration_seconds,
                        "splits": evaluate_models(kernel, flat, temperature, cfg, args.worlds)})
    print(json.dumps({"status": "PUBLIC_DEVELOPMENT_NOT_G1", "canonical_budget": canonical,
                      "hardware": {"machine": platform.machine(), "processor": platform.processor(),
                                   "python": platform.python_version(), "torch": torch.__version__,
                                   "threads": torch.get_num_threads()},
                      "structured_preprocess_seconds": structured_preprocess_seconds,
                      "flat_preprocess_seconds": flat_preprocess_seconds, "results": results},
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
