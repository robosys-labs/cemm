"""G1b unsealed train/validation diagnostics: not a G1 acceptance result.

Run: python -m experiments.predictive_nucleus.train --episodes 30 --seeds 7,11
No frozen challenge split is read. The learner consumes sensor feedback only.
"""
from __future__ import annotations

import argparse
import json
import random
import resource
import statistics
import sys
import time

import torch

from .evaluate import score_predictions
from .model import SharedWorldModel
from .protocol import read_protocol, verify_protocol
from .world import make_episode


def run(model: SharedWorldModel, episode, optimizer=None, latencies=None):
    model.reset(episode.sensors[0])
    predicted, truth, baseline = [], [], []
    # Fully independent persistence control; no neural model state is reused.
    control = {item["id"]: float(item["bit"]) for item in episode.sensors[0]["measurements"]}
    for idx in range(len(episode.actions)):
        turn = episode.learner_turn(idx)
        for item in turn["observation"]["measurements"]:
            control[item["id"]] = float(item["bit"])
        t0 = time.perf_counter()
        outcome = model.predict(turn)
        if latencies is not None:
            latencies.append((time.perf_counter() - t0) * 1000)
        # Gold is accessed ONLY in no-grad validation, after prediction. During
        # training the optimizer sees only the subsequently delivered sensors.
        if optimizer is None and episode.actions[idx].kind == "contact":
            case_id = f"{episode.lineage_id}:{idx}"
            predicted.append({"case_id": case_id, "p1": {k: float(v.detach()) for k, v in outcome.items()}})
            truth.append({"case_id": case_id, "family": episode.family, "seed": episode.seed,
                          "truth": episode.gold_after(idx)})
            baseline.append({"case_id": case_id, "p1": control.copy()})
        feedback = episode.reveal_after_prediction(idx)
        model.receive(feedback)
        for item in feedback["measurements"]:
            control[item["id"]] = float(item["bit"])
    if optimizer:
        optimizer.zero_grad()
        model.episode_loss().backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.)
        optimizer.step()
    return truth, predicted, baseline


def diagnostic(seed: int, episodes: int = 30, validations: int = 20):
    torch.manual_seed(seed)
    random.seed(seed)
    model = SharedWorldModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    t0 = time.perf_counter()
    for i in range(episodes):
        family = ("single_contact", "two_contacts")[i % 2]
        episode = make_episode("train", 101, i, family)
        run(model, episode, optimizer)
    train_seconds = time.perf_counter() - t0
    truth, predicted, baseline = [], [], []
    model.eval()
    ms = []
    with torch.no_grad():
        for i in range(validations):
            episode = make_episode("validation", 211, i, ("single_contact", "two_contacts")[i % 2])
            a, b, c = run(model, episode, latencies=ms)
            truth.extend(a)
            predicted.extend(b)
            baseline.extend(c)
    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform.startswith("linux") else 1024**2)
    return {"seed": seed, "status": "VALIDATION_DIAGNOSTIC_ONLY", "train_episodes": episodes,
            "parameters": model.parameter_count(), "seconds": round(train_seconds, 3),
            "peak_rss_mb": round(peak_rss_mb, 3),
            "torch_version": torch.__version__, "hardware": "cpu", "training_updates": episodes,
            "validation_step_ms_p50": statistics.median(ms),
            "validation_step_ms_p95": sorted(ms)[int(.95 * (len(ms) - 1))],
            "model": score_predictions(truth, predicted)["aggregate"],
            "no_change_control": score_predictions(truth, baseline)["aggregate"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--episodes", type=int, default=30)
    p.add_argument("--validation-episodes", type=int, default=20)
    p.add_argument("--seeds", default="7,11,23,37,53")
    a = p.parse_args()
    verify_protocol(read_protocol())
    conf = read_protocol()
    seeds = [int(s) for s in a.seeds.split(",")]
    if any(s not in conf["model_seeds"] for s in seeds) or a.episodes < 1 or a.validation_episodes < 1:
        raise ValueError("unknown seed or non-positive budget")
    torch.set_num_threads(1)
    print(json.dumps({"scientific_gate": "NOT_RUN", "split": "validation_only",
                      "results": [diagnostic(seed, a.episodes, a.validation_episodes) for seed in seeds]}, sort_keys=True))


if __name__ == "__main__":
    main()
