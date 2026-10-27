"""G1c unsealed evidence/probe diagnostic. NOT a sealed G1 science gate.

Usage: python -m experiments.predictive_nucleus.probe_trial --train 1600 --validation 80
Learner training/calibration reads only public observations. A separate lab
owns simulation ground truth, executing actions AFTER the predictor commits.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from collections import defaultdict

import torch

from .world import Action, make_episode, observe, step
from .latent_model import ContactKernel, build_samples, fit_kernel, shuffle_contact_outcomes
from .calibration import calibrate
from .uncertainty import EvidenceBelief

WORLD_SEEDS = {
    "train": (101, 103, 107, 109, 113),
    "calibration": (307, 311, 313, 317, 331),
    "validation": (211, 223, 227, 229, 233),
}


def _episode_list(split, count):
    if count < 1:
        raise ValueError("episode count must be positive")
    return [make_episode(split, WORLD_SEEDS[split][i % 5], i,
                         ("single_contact", "two_contacts")[i % 2]) for i in range(count)]


def _execute(belief, world, action, sequence):
    prediction = belief.commit_action(action)
    actual = Action(action["kind"], tuple(action["participants"]), action.get("value"))
    changed = step(world, actual)
    feedback = observe(changed, belief.t + 1, tuple(reversed(changed.ids)))
    receipt = belief.receive(feedback, f"lab-{sequence}")
    return changed, receipt, prediction


def _query_metrics(belief, world, target):
    original = target["participants"]
    outcomes = []
    for pair in (original, list(reversed(original))):
        action = {"kind": "contact", "participants": pair}
        forecast = belief.preview(action)
        actual = step(world, Action("contact", tuple(pair)))
        gold = tuple(actual.bits[actual.ids.index(name)] for name in belief.ids)
        joint_prob = sum(prob for (_, bits), prob in forecast.states.items() if bits == gold)
        predicted = tuple(int(forecast.state_probability[name] >= .5) for name in belief.ids)
        exact = predicted == gold
        brier = statistics.mean((forecast.state_probability[name] - gold[i]) ** 2
                                for i, name in enumerate(belief.ids))
        outcomes.append({"exact": exact, "brier": brier, "nll": -math.log(max(joint_prob, 1e-12)),
                         "confidence": forecast.full_world_certainty,
                         "eligible": forecast.full_world_certainty >= .95})
    return outcomes


def run_policy(world, kernel, policy: str, seed: int, max_probe_actions=2, query_cost=.02, forget_orientation=False):
    """Three controlled policies share world initialization, target, sensor API."""
    belief = EvidenceBelief(kernel, observe(world, 0, tuple(reversed(world.ids))))
    rng = random.Random(seed)
    contacts = [{"kind": "contact", "participants": [a, b]}
                for a in world.ids for b in world.ids if a != b]
    interventions = [{"kind": "set", "participants": [world.ids[0]], "value": bit} for bit in (0, 1)]
    initial_entropy = belief.preview(contacts[0]).mechanism_entropy
    results = []
    durations = []
    for i in range(max_probe_actions if policy != "passive" else 0):
        t0 = time.perf_counter()
        if policy == "active":
            choice = belief.choose_probe(contacts, cost=query_cost, interventions=interventions)
            action = choice["action"]
            if action is None:
                break
        elif policy == "random":
            action = rng.choice(contacts)
        else:
            raise ValueError("unknown probe policy")
        world, receipt, prediction = _execute(belief, world, action, i)
        durations.append((time.perf_counter() - t0) * 1000)
        results.append({"kind": action["kind"], "status": receipt.status,
                        "expected_ig": prediction.expected_info_gain})
        if policy == "active" and receipt.mechanism_entropy <= .2:
            break
    if forget_orientation:
        # Matched observed physical state and probes; erase only the learned
        # latent-mechanism posterior before issuing the two target queries.
        belief = EvidenceBelief(kernel, observe(world, belief.t, tuple(reversed(world.ids))))
    target_rng = random.Random(seed + 997)
    target = target_rng.choice(contacts)
    t0 = time.perf_counter()
    predictions = _query_metrics(belief, world, target)
    durations.append((time.perf_counter() - t0) * 1000)
    return {"probe_actions": len(results), "probe_interventions": sum(x["kind"] == "set" for x in results),
            "initial_entropy": initial_entropy, "posterior_entropy": entropy_of_belief(belief),
            "mismatch_flags": sum(x["status"] == "MODEL_MISMATCH_CANDIDATE" for x in results),
            "queries": predictions, "probe_trace": results, "latency_ms": durations}


def entropy_of_belief(belief):
    from .uncertainty import entropy
    return entropy(belief.mechanism_masses())


def summarize(trials):
    pairs = [t["queries"] for t in trials]
    outcomes = [x for pair in pairs for x in pair]
    accepted = [x for x in outcomes if x["eligible"]]
    ece = (sum(abs(sum(x["confidence"] for x in group) / len(group) -
                   sum(x["exact"] for x in group) / len(group)) * len(group)
               for b in range(10) if (group := [x for x in outcomes if min(9, int(x["confidence"] * 10)) == b]))
           / len(outcomes))
    all_latency = sorted(n for trial in trials for n in trial["latency_ms"])
    return {"worlds": len(trials), "queries": len(outcomes),
            "exact": statistics.mean(x["exact"] for x in outcomes),
            "role_pair_exact": statistics.mean(all(x["exact"] for x in pair) for pair in pairs),
            "brier": statistics.mean(x["brier"] for x in outcomes),
            "joint_nll": statistics.mean(x["nll"] for x in outcomes),
            "ece10_full_world": ece,
            "covered_fraction_at_95_percent": len(accepted) / len(outcomes),
            "exact_if_covered": statistics.mean(x["exact"] for x in accepted) if accepted else None,
            "mean_posterior_orientation_entropy": statistics.mean(t["posterior_entropy"] for t in trials),
            "mean_probe_actions": statistics.mean(t["probe_actions"] for t in trials),
            "mean_probe_interventions": statistics.mean(t["probe_interventions"] for t in trials),
            "mismatch_flags": sum(t["mismatch_flags"] for t in trials),
            "p50_plan_or_query_ms": statistics.median(all_latency),
            "p95_plan_or_query_ms": all_latency[int(.95 * (len(all_latency) - 1))]}


def diagnostic(model_seed, train_count, calibration_count, validation_count, updates):
    torch.manual_seed(model_seed)
    t0 = time.perf_counter()
    torch.manual_seed(model_seed)
    untrained = ContactKernel().freeze()
    train_data = build_samples(_episode_list("train", train_count))
    trained, fit_report = fit_kernel(train_data, model_seed, updates)
    corrupted, _ = fit_kernel(shuffle_contact_outcomes(train_data, model_seed + 880), model_seed, updates)
    calib_samples = build_samples(_episode_list("calibration", calibration_count))
    kernel, calibration_report = calibrate(trained, calib_samples)
    corrupted_kernel, corrupted_calibration = calibrate(corrupted, calib_samples)
    trials = defaultdict(list)
    for ep in _episode_list("validation", validation_count):
        world = ep.states[0]  # External evaluator only; never given to learner.
        for policy in ("active", "random", "passive", "no_learning_active", "shuffled_outcomes_active", "memoryless_active"):
            applied = {"no_learning_active": untrained,
                       "shuffled_outcomes_active": corrupted_kernel}.get(policy, kernel)
            action_policy = "active" if policy.endswith("_active") else policy
            trials[policy].append(run_policy(world, applied, action_policy,
                        seed=int(ep.lineage_id[:10], 16), forget_orientation=(policy == "memoryless_active")))
    import resource
    from pathlib import Path
    import sys
    codebase = Path(__file__).resolve().parent
    loc = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in codebase.rglob("*.py"))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform.startswith("linux") else 1024**2)
    return {"model_seed": model_seed, "status": "DIAGNOSTIC_UNADMITTED",
            "training": fit_report, "calibration": calibration_report,
            "shuffled_calibration_temperature": corrupted_calibration["temperature"],
            "source_python_loc_including_tests": loc, "peak_process_rss_mb": peak,
            "latency_train_calibrate_validate_seconds": round(time.perf_counter() - t0, 3),
            "policy": {name: summarize(trials[name]) for name in ("active", "random", "passive", "no_learning_active", "shuffled_outcomes_active", "memoryless_active")}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train", type=int, default=1600)
    p.add_argument("--calibration", type=int, default=300)
    p.add_argument("--validation", type=int, default=80)
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--seeds", default="7,11,23,37,53")
    args = p.parse_args()
    from .protocol import read_protocol, verify_protocol
    verify_protocol(read_protocol())
    torch.set_num_threads(1)
    seeds = [int(s) for s in args.seeds.split(",")]
    if not set(seeds) <= set(read_protocol()["model_seeds"]):
        raise ValueError("unknown model seed")
    print(json.dumps({"gate": "G1_NOT_RUN", "split": "validation_diagnostics_only",
        "results": [diagnostic(s, args.train, args.calibration, args.validation, args.steps) for s in seeds]}, sort_keys=True))


if __name__ == "__main__":
    main()
