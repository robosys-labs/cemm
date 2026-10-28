"""Unsealed G1d stress: new contact physics, occlusion, noise and cost-matched probes.

The oracle in stress_world is evaluator-only, never a learner input. This is a
public development experiment, NOT independent challenge custody or G1 success.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import random
import statistics
import time

from .evidence_guard import EpisodeEvidenceGuard
from .evidence_monitor import PredictiveAdequacyMonitor
from .stress_world import draw_world, change, choose_visibility, sensor_reading
from .uncertainty import EvidenceBelief
from .world import make_episode

WORLD_SEEDS = (601, 607, 613, 617, 619)  # NOT any frozen original challenge seeds
SCENARIOS = {
    "reference_clean": ("reference", 0.0, 0.0, 0.0),
    "reference_partial": ("reference", 0.0, .65, 0.0),
    "reference_noisy": ("reference", .08, 0.0, .08),
    "reference_sensor_misspecified": ("reference", .20, 0.0, .01),
    "bilateral_flip": ("bilateral_flip", 0.0, 0.0, 0.0),
    "conditional_flip": ("conditional_flip", 0.0, 0.0, 0.0),
    "switch_orientation": ("switch_orientation", 0.0, 0.0, 0.0),
}


def learning_data(split, count):
    from .latent_model import build_samples
    seeds = {"train": (101, 103, 107, 109, 113),
             "calibration": (307, 311, 313, 317, 331)}[split]
    return build_samples([make_episode(split, seeds[i % 5], i,
                        ("single_contact", "two_contacts")[i % 2]) for i in range(count)])


def joint_map_world(forecast):
    """MAP complete world and its *own* joint probability; ties are stable."""
    worlds = defaultdict(float)
    for (_, bits), mass in forecast.states.items():
        worlds[bits] += mass
    # Lexicographically smallest world breaks equal-probability ties.
    bits = min(worlds, key=lambda state: (-worlds[state], state))
    return bits, worlds[bits]


def evaluate_pair(belief, world, pair, *, last_alarm=False, guard=None):
    """Evaluator reads hidden truth only after two read-only predictions."""
    rows = []
    for ids in (pair, tuple(reversed(pair))):
        action = {"kind": "contact", "participants": list(ids)}
        decision = belief.assess(action)
        forecast = belief.preview(action)
        next_world = change(world, action)
        truth = tuple(next_world.bits[next_world.ids.index(name)] for name in belief.ids)
        predicted = tuple(int(forecast.state_probability[name] >= .5) for name in belief.ids)
        map_world, map_confidence = joint_map_world(forecast)
        probability = sum(mass for (_, bits), mass in forecast.states.items() if bits == truth)
        brier = statistics.mean((forecast.state_probability[name] - truth[i]) ** 2
                                for i, name in enumerate(belief.ids))
        rows.append({"correct": truth == predicted,
                     "eligible": decision["status"] == "PREDICT_WITH_EVIDENCE" and not last_alarm,
                     "joint_map_correct": truth == map_world,
                     "joint_map_confidence": map_confidence,
                     "target_action": action,
                     "world_ids": list(belief.ids),
                     "joint_map_world": list(map_world),
                     "truth_world": list(truth),
                     "guard_eligible": decision["status"] == "PREDICT_WITH_EVIDENCE" and
                         (guard is None or not guard.blocked),
                     "confidence": forecast.full_world_certainty,
                     "joint_nll": -math.log(max(probability, 1e-12)),
                     "bit_brier": brier, "decision": decision["status"]})
    return rows


def rollout(initial_world, kernel, *, scenario, policy, seed, budget=2):
    """Identical initial hidden world and public action budget for every policy."""
    physics, actual_noise, missing_rate, assumed_noise = SCENARIOS[scenario]
    if physics != initial_world.physics:
        raise ValueError("scenario and evaluator world mismatch")
    rng = random.Random(seed)
    world = initial_world
    # The starting state is a separately verified complete sensor anchor.
    first = {"t": 0, "measurements": [{"id": name, "bit": world.bits[j]}
                                       for j, name in enumerate(world.ids)]}
    belief = EvidenceBelief(kernel, first, sensor_error_rate=assumed_noise)
    monitor = PredictiveAdequacyMonitor({"lab-sensor": assumed_noise}, alpha=.05)
    guard = EpisodeEvidenceGuard(alpha=.05)
    contacts = [{"kind": "contact", "participants": [a, b]}
                for a in world.ids for b in world.ids if a != b]
    preparations = [{"kind": "set", "participants": [world.ids[0]], "value": bit}
                    for bit in (0, 1)]
    target_rng = random.Random(seed + 79)
    pair = tuple(target_rng.choice(contacts)["participants"])
    steps = []
    latencies = []
    guard_latencies = []
    for i in range(budget):
        t0 = time.perf_counter()
        verification_action = False
        if policy in ("active", "active_validate"):
            if policy == "active_validate" and i > 0 and max(belief.mechanism_masses()) >= .85:
                suggestion = belief.choose_validation_probe(contacts)
                verification_action = suggestion["action"] is not None
            else:
                suggestion = belief.choose_probe(contacts, interventions=preparations,
                                                 cost=.02, sensor_ids="participants")
            action = suggestion["action"]
            if action is None:
                break
        elif policy == "random_contact":
            action = rng.choice(contacts)
        elif policy == "random_any":
            action = rng.choice(contacts + preparations)
        elif policy == "passive":
            break
        else:
            raise ValueError("unknown evaluation policy")
        latencies.append((time.perf_counter() - t0) * 1000)
        # Sensor coverage is fixed independently of bit outcomes, before action.
        planned = tuple(action["participants"])
        visible = choose_visibility(planned, rng, missing_rate)
        reset_forecast = belief.preview_mechanism_reset(action, sensor_ids=planned) if policy == "active_validate" else None
        forecast = belief.commit_action(action)
        monitor.commit(forecast, source_id="lab-sensor", next_time=i + 1,
                       intended_sensor_ids=planned, alternative_forecast=reset_forecast)
        world = change(world, action)
        observed = sensor_reading(world, i + 1, visible, rng, actual_noise)
        checked = monitor.observe(observed, evidence_id=f"lab-{seed}-{i}", source_id="lab-sensor")
        update = belief.receive(observed, f"world-{seed}-{i}")
        guard_start = time.perf_counter()
        guard.record(monitor, belief, update)
        guard_latencies.append((time.perf_counter() - guard_start) * 1000)
        steps.append({"action": action, "observed_likelihood": checked.observed_likelihood,
                      "observed_count": checked.observed_bits, "monitor_status": checked.status,
                      "belief_status": update.status, "alarm": checked.alarm,
                      "change_point_alarm": checked.change_point_alarm,
                      "observation": observed, "guard_blocked": guard.blocked,
                      "verification": verification_action})
    rows = evaluate_pair(belief, world, pair, last_alarm=any(x["alarm"] for x in steps), guard=guard)
    return {"probes": len(steps), "set_probes": sum(s["action"]["kind"] == "set" for s in steps),
            "verification_probes": sum(s["verification"] for s in steps),
            "belief_conflict": any(s["belief_status"] in ("CONFLICTING_EVIDENCE", "MODEL_MISMATCH_CANDIDATE") for s in steps),
            "change_point_alarm": any(s["change_point_alarm"] for s in steps),
            "observed_bits": sum(s["observed_count"] for s in steps),
            "alarm": any(x["alarm"] for x in steps), "rows": rows,
            "guard_conflicts": sorted(guard.conflicts),
            "guard_portfolio_alarm": guard.portfolio_alarm,
            "guard_record_latency_ms": guard_latencies,
            "initial_anchor": first, "probe_trace": steps,
            "probe_statuses": [s["monitor_status"] for s in steps],
            "latency_ms": latencies}


def summarize(trials):
    rows = [row for t in trials for row in t["rows"]]
    accepted = [row for row in rows if row["eligible"]]
    by_bin = defaultdict(list)
    for row in rows:
        by_bin[min(9, int(row["confidence"] * 10))].append(row)
    ece = sum(len(g) * abs(statistics.mean(x["confidence"] for x in g) -
                              statistics.mean(x["correct"] for x in g))
              for g in by_bin.values()) / len(rows)
    durations = sorted(n for t in trials for n in t["latency_ms"])
    return {"worlds": len(trials), "target_queries": len(rows),
            "full_world_exact": statistics.mean(x["correct"] for x in rows),
            "pair_both_exact": statistics.mean(all(x["correct"] for x in t["rows"]) for t in trials),
            "bit_brier": statistics.mean(x["bit_brier"] for x in rows),
            "joint_nll": statistics.mean(x["joint_nll"] for x in rows),
            "full_world_ece10": ece,
            "coverage": len(accepted) / len(rows),
            "exact_if_covered": statistics.mean(x["correct"] for x in accepted) if accepted else None,
            "alarm_world_rate": statistics.mean(t["alarm"] for t in trials),
            "change_point_alarm_rate": statistics.mean(t["change_point_alarm"] for t in trials),
            "belief_conflict_rate": statistics.mean(t["belief_conflict"] for t in trials),
            "mean_validation_probe_steps": statistics.mean(t["verification_probes"] for t in trials),
            "probes_mean": statistics.mean(t["probes"] for t in trials),
            "intervention_mean": statistics.mean(t["set_probes"] for t in trials),
            "observed_bits_mean": statistics.mean(t["observed_bits"] for t in trials),
            "latency_p95_ms": durations[int(.95 * (len(durations) - 1))] if durations else None}


def experiment(model_seed: int, train_count: int, calib_count: int,
               n: int, steps: int, scenarios=tuple(SCENARIOS)):
    from .calibration import calibrate
    from .latent_model import fit_kernel
    train, calib = learning_data("train", train_count), learning_data("calibration", calib_count)
    model, train_report = fit_kernel(train, model_seed, steps=steps)
    kernel, calibration = calibrate(model, calib)
    results = {}
    for scenario in scenarios:
        physics, _, _, _ = SCENARIOS[scenario]
        cases = defaultdict(list)
        ids = []
        for i in range(n):
            seed = WORLD_SEEDS[i % 5]
            initial = draw_world(seed, i, physics)
            external_seed = int(initial.ids[0], 16)  # opaque public identity, never latent/gold
            active = rollout(initial, kernel, scenario=scenario, policy="active", seed=external_seed)
            random_contact = rollout(initial, kernel, scenario=scenario, policy="random_contact",
                                     seed=external_seed, budget=active["probes"])
            random_any = rollout(initial, kernel, scenario=scenario, policy="random_any",
                                 seed=external_seed, budget=active["probes"])
            passive = rollout(initial, kernel, scenario=scenario, policy="passive",
                              seed=external_seed, budget=0)
            for name, data in (("active", active), ("random_contact_cost_matched", random_contact),
                               ("random_any_cost_matched", random_any), ("passive", passive)):
                cases[name].append(data)
            if active["probes"] != random_contact["probes"] or active["probes"] != random_any["probes"]:
                raise RuntimeError("matched controls consumed different physical action counts")
            ids.append({"case_id": f"{scenario}:{seed}:{i}",
                        "active_probe_count": active["probes"],
                        "active_alarm": active["alarm"], "active_pair_exact": all(x["correct"] for x in active["rows"]),
                        "random_contact_pair_exact": all(x["correct"] for x in random_contact["rows"])})
        results[scenario] = {
            "policy": {policy: summarize(trials) for policy, trials in cases.items()},
            "paired_cases": len(ids),
            "active_wins_over_random_contact": [r["case_id"] for r in ids
                if r["active_pair_exact"] and not r["random_contact_pair_exact"]],
            "active_losses_to_random_contact": [r["case_id"] for r in ids
                if not r["active_pair_exact"] and r["random_contact_pair_exact"]],
            "examples": ids[:10]}
    return {"seed": model_seed, "train": train_report, "calibration": calibration,
            "status": "PUBLIC_DEVELOPMENT_DIAGNOSTIC_NOT_G1", "scenarios": results}


def main():
    import torch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=int, default=600)
    parser.add_argument("--calibration", type=int, default=200)
    parser.add_argument("--worlds", type=int, default=20)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seeds", default="7,11,23,37,53")
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    args = parser.parse_args()
    chosen = [s for s in args.scenarios.split(",") if s]
    from .protocol import read_protocol, verify_protocol
    from .stress_protocol import verify as verify_stress_protocol
    verify_protocol(read_protocol())
    frozen = verify_stress_protocol()
    if list(SCENARIOS) != list(frozen["stress_development"]["scenarios"]):
        raise ValueError("stress family inventory differs from locked version")
    if any(list(value) != frozen["stress_development"]["scenarios"][key]
           for key, value in SCENARIOS.items()):
        raise ValueError("stress physics/noise parameters differ from locked version")
    if (not chosen or any(c not in SCENARIOS for c in chosen) or min(args.train, args.calibration, args.worlds, args.steps) <= 0):
        raise ValueError("invalid diagnostic budget or scenario")
    seeds = [int(s) for s in args.seeds.split(",")]
    if not seeds or any(s not in frozen["learning"]["model_seeds"] for s in seeds):
        raise ValueError("unregistered optimizer seed")
    torch.set_num_threads(1)
    start = time.perf_counter()
    results = [experiment(seed, args.train, args.calibration, args.worlds, args.steps, chosen) for seed in seeds]
    print(json.dumps({"gate": "NOT_RUN", "status": "PUBLIC_DEV_NOT_BLIND",
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "model_seeds": seeds, "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
