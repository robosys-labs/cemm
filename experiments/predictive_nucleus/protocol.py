"""Frozen G0 preregistration checks; no predictive model or production imports."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
LOCK = HERE / "snapshots" / "protocol.sha256"
REQUIRED_SPLITS = ("train", "validation", "calibration", "in_family_challenge", "ood_challenge")


def read_protocol(path: Path = PROTOCOL) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest_protocol(path: Path = PROTOCOL) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_protocol(config: dict[str, Any], expected_digest: str | None = None) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("unsupported protocol schema")
    if tuple(config.get("splits", {})) != REQUIRED_SPLITS:
        raise ValueError("unexpected split inventory or order")
    if config.get("world_contract", {}).get("version") != "binary-contact-v1":
        raise ValueError("unreviewed world contract")
    if config.get("gate_g1", {}).get("status") != "NOT_RUN":
        raise ValueError("protocol must not claim an unevaluated G1 gate")
    if len(set(config.get("model_seeds", []))) < 5:
        raise ValueError("need at least five independent model seeds")
    seen_seeds: set[int] = set()
    for name in REQUIRED_SPLITS:
        split = config["splits"][name]
        seeds = split["seeds"]
        if len(seeds) < 5 or len(set(seeds)) != len(seeds) or not all(type(x) is int for x in seeds):
            raise ValueError(f"bad world seeds: {name}")
        if seen_seeds.intersection(seeds):
            raise ValueError(f"world seed leaks across splits: {name}")
        seen_seeds.update(seeds)
        if not split["families"] or len(set(split["families"])) != len(split["families"]):
            raise ValueError(f"duplicate or missing families: {name}")
    train_families = set(config["splits"]["train"]["families"])
    if set(config["splits"]["ood_challenge"]["families"]) & train_families:
        raise ValueError("OOD topology may not overlap training")
    if set(config["splits"]["in_family_challenge"]["families"]) != train_families:
        raise ValueError("in-family challenge must cover all training topologies")
    if config.get("evaluation_policy", {}).get("never_fit_on") != list(REQUIRED_SPLITS[3:]):
        raise ValueError("challenges are not selection/training data")
    if not set(("full_world_exact", "per_entity_brier", "per_entity_nll", "role_pair_exact")) <= set(config["metrics"]):
        raise ValueError("missing primary exact/probabilistic metrics")
    budgets = config["budgets"]
    if budgets["n_agents_min"] < 3 or budgets["n_agents_max"] > 6 or budgets["test_worlds_per_seed_family"] < 100:
        raise ValueError("invalid bounds or insufficient preregistered challenges")
    if expected_digest is not None and expected_digest != digest_protocol():
        raise ValueError("frozen protocol bytes differ from committed SHA256")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify"])
    args = parser.parse_args()
    expected = LOCK.read_text(encoding="ascii").strip().split()[0]
    config = read_protocol()
    verify_protocol(config, expected_digest=expected)
    print(json.dumps({"status": config["status"], "sha256": expected,
                      "challenge_family_count": len(config["splits"]["ood_challenge"]["families"]),
                      "G1": "NOT_RUN"}, sort_keys=True))


if __name__ == "__main__":
    main()
