"""Post-v3 public development evaluation of falsifying temporal probe policies.

Uses new public deterministic worlds; **not** independent challenge custody.
No training from these worlds, no oracle physics passed to learner.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .stress_trial import SCENARIOS, rollout, summarize, learning_data
from .stress_world import draw_world

HERE = Path(__file__).resolve().parent


def frozen_config():
    source = HERE / "stability_protocol_v4.json"
    lock = (HERE / "snapshots" / "stability_protocol_v4.sha256").read_text().split()[0]
    if hashlib.sha256(source.read_bytes()).hexdigest() != lock:
        raise ValueError("temporal validation manifest differs from frozen checksum")
    data = json.loads(source.read_text())
    if data["schema_version"] != 4 or data["decision"] != "NOT_RUN_NO_G1_ADMISSION":
        raise ValueError("invalid preregistered scientific admission status")
    if list(SCENARIOS) != data["strata"]:
        raise ValueError("scenario inventory drift")
    if data["gates"]["max_physical_probes"] != 2:
        raise ValueError("unreviewed temporal verification budget")
    return data


def evaluate(seed, train_count, calib_count, world_count, steps, cfg):
    from .latent_model import fit_kernel
    from .calibration import calibrate
    train = learning_data("train", train_count)
    calibration = learning_data("calibration", calib_count)
    model, fit = fit_kernel(train, seed, steps=steps)
    kernel, calibrated = calibrate(model, calibration)
    results = {}
    for scenario in cfg["strata"]:
        physics = SCENARIOS[scenario][0]
        trials = {k: [] for k in ("active_validate", "active",
                                 "random_contact", "random_any", "passive")}
        comparisons = []
        for index in range(world_count):
            wseed = cfg["gates"]["new_world_seeds"][index % 5]
            world = draw_world(wseed, index, physics)
            sequence_seed = int(world.ids[0], 16)
            verified = rollout(world, kernel, scenario=scenario, policy="active_validate",
                               seed=sequence_seed, budget=2)
            original = rollout(world, kernel, scenario=scenario, policy="active",
                               seed=sequence_seed, budget=2)
            rnd_contact = rollout(world, kernel, scenario=scenario, policy="random_contact",
                                  seed=sequence_seed, budget=verified["probes"])
            rnd_any = rollout(world, kernel, scenario=scenario, policy="random_any",
                              seed=sequence_seed, budget=verified["probes"])
            passive = rollout(world, kernel, scenario=scenario, policy="passive",
                              seed=sequence_seed, budget=0)
            if verified["probes"] != rnd_contact["probes"] or verified["probes"] != rnd_any["probes"]:
                raise ValueError("physical probe cost was not matched")
            for name, value in (("active_validate", verified), ("active", original),
                                ("random_contact", rnd_contact), ("random_any", rnd_any),
                                ("passive", passive)):
                trials[name].append(value)
            comparisons.append({
                "case_id": f"v4:{scenario}:{wseed}:{index}",
                "verification_steps": verified["verification_probes"],
                "validating_pair_exact": all(row["correct"] for row in verified["rows"]),
                "original_pair_exact": all(row["correct"] for row in original["rows"]),
                "random_contact_pair_exact": all(row["correct"] for row in rnd_contact["rows"]),
                "belief_conflict": verified["belief_conflict"],
                "change_point_alarm": verified["change_point_alarm"]
            })
        results[scenario] = {
            "policy": {name: summarize(group) for name, group in trials.items()},
            "validation_wins_over_random_cost_matched": [r["case_id"] for r in comparisons
                if r["validating_pair_exact"] and not r["random_contact_pair_exact"]],
            "validation_losses_to_random_cost_matched": [r["case_id"] for r in comparisons
                if not r["validating_pair_exact"] and r["random_contact_pair_exact"]],
            "validation_repairs_original_policy": [r["case_id"] for r in comparisons
                if r["validating_pair_exact"] and not r["original_pair_exact"]],
            "validation_breaks_original_policy": [r["case_id"] for r in comparisons
                if not r["validating_pair_exact"] and r["original_pair_exact"]],
            "case_count": len(comparisons)
        }
    return {"model_seed": seed, "train": fit, "calibration": calibrated,
            "status": "PUBLIC_TEMPORAL_DEVELOPMENT_NOT_G1", "scenarios": results}


def main():
    import torch
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train", type=int, default=600)
    p.add_argument("--calibration", type=int, default=200)
    p.add_argument("--worlds", type=int, default=10)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--seeds", default="7,11,23,37,53")
    args = p.parse_args()
    from .protocol import read_protocol, verify_protocol
    verify_protocol(read_protocol())
    cfg = frozen_config()
    seeds = [int(s) for s in args.seeds.split(",")]
    if not seeds or any(s not in cfg["gates"]["model_seeds"] for s in seeds):
        raise ValueError("unregistered optimizer seed")
    if min(args.train, args.calibration, args.worlds, args.steps) < 1:
        raise ValueError("nonpositive development budget")
    torch.set_num_threads(1)
    before = perf_counter()
    results = [evaluate(seed, args.train, args.calibration, args.worlds, args.steps, cfg)
               for seed in seeds]
    print(json.dumps({"gate": "G1_NOT_ADMITTED", "challenge": "PUBLIC_DEVELOPMENT",
                      "elapsed_seconds": round(perf_counter() - before, 3),
                      "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
