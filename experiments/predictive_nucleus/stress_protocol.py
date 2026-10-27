"""Exact byte lock and split/condition safeguards for public G1d diagnostics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verify(path: Path | None = None, lock: Path | None = None) -> dict:
    path = path or HERE / "stress_protocol_v3.json"
    lock = lock or HERE / "snapshots" / "stress_protocol_v3.sha256"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != lock.read_text(encoding="ascii").split()[0]:
        raise ValueError("stress protocol bytes differ from preregistered lock")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema_version") != 3 or cfg.get("decision") != "KEEP_DIAGNOSTIC_G1_UNADMITTED":
        raise ValueError("unexpected protocol or admission state")
    s = cfg["stress_development"]
    all_seeds = [*cfg["learning"]["fit_seeds"], *cfg["learning"]["calibration_seeds"], *s["world_seeds"]]
    if len(all_seeds) != len(set(all_seeds)) or not cfg["learning"]["no_retraining_after_stress_results"]:
        raise ValueError("split lineage overlap or post-outcome fitting")
    if len(cfg["learning"]["model_seeds"]) < 5 or len(s["world_seeds"]) < 5:
        raise ValueError("insufficient model/world seeds")
    if s["max_physical_probe_steps_per_world"] != 2 or s["per_action_sensor_coverage"] != "action_participants_only":
        raise ValueError("unreviewed probe budget or observation scope")
    if s["anytime_e_process_alpha"] != .05 or not s["all_sensors_precommitted_before_outcomes"]:
        raise ValueError("unreviewed statistical test")
    return cfg
