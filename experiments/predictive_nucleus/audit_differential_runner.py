"""Same-host before/after regression fingerprints; not a scientific test."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import torch

from .calibration import calibrate
from .flat_reference import batch_episodes, calibrate_flat, fit_flat
from .flat_trial import reference_episodes
from .latent_model import build_samples, fit_kernel
from .stress_trial import SCENARIOS, rollout
from .stress_world import draw_world


def tensor_fingerprint(tensors):
    """Hash ordered names, dtypes, shapes and raw CPU tensor bytes."""
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        value = tensor.detach().cpu().contiguous()
        metadata = json.dumps([name, str(value.dtype), list(value.shape)], separators=(",", ":")).encode()
        raw = bytes(value.view(torch.uint8).reshape(-1).tolist())
        digest.update(len(metadata).to_bytes(8, "big"))
        digest.update(metadata)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def cpu_model():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def cpu_flags_hash():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("flags"):
                flags = " ".join(sorted(line.split(":", 1)[1].split()))
                return hashlib.sha256(flags.encode()).hexdigest()
    except OSError:
        pass
    return None


def main():
    torch.set_num_threads(1)
    training = reference_episodes("train", 600)
    calibration = reference_episodes("calibration", 200)
    flat_train, flat_calibration = batch_episodes(training), batch_episodes(calibration)
    structured_train, structured_calibration = build_samples(training), build_samples(calibration)
    records = []
    for seed in (7, 53):
        model, _ = fit_kernel(structured_train, seed, steps=200)
        kernel, calibrated = calibrate(model, structured_calibration)
        flat, _ = fit_flat(flat_train, seed, max_steps=200, wall_budget_seconds=60, fixed_steps=200)
        flat_temperature, flat_calibrated = calibrate_flat(flat, flat_calibration)
        trajectories = []
        flat_forecasts = []
        for scenario, definition in SCENARIOS.items():
            for index in (0, 1):
                # Synthetic public fixture; no frozen challenge lineage is run.
                world = draw_world(901, index, definition[0])
                trial = rollout(world, kernel, scenario=scenario, policy="active_validate", seed=71 + index, budget=2)
                # Feed only the public anchor, committed actions and received
                # observations; evaluator truth never enters the flat model.
                flat.reset(trial["initial_anchor"], sensor_error_rate=definition[-1])
                for step in trial["probe_trace"]:
                    flat.commit(step["action"], temperature=flat_temperature)
                    flat.receive(step["observation"])
                for direction, row in enumerate(trial["rows"]):
                    distribution, _ = flat.preview(row["target_action"], temperature=flat_temperature)
                    flat_forecasts.append({"scenario": scenario, "index": index, "direction": direction,
                                           "states": [[list(bits), distribution[bits]] for bits in sorted(distribution)]})
                common = ("probes", "set_probes", "verification_probes", "belief_conflict",
                          "change_point_alarm", "observed_bits", "alarm", "guard_conflicts", "guard_portfolio_alarm")
                row_fields = ("correct", "eligible", "joint_map_correct", "joint_map_confidence", "guard_eligible",
                              "context_eligible", "context_status", "context_observed_events", "confidence",
                              "joint_nll", "bit_brier", "decision")
                trace_fields = ("action", "observation", "observed_likelihood", "observed_count", "monitor_status",
                                "belief_status", "alarm", "change_point_alarm", "guard_blocked", "verification")
                trajectories.append({"scenario": scenario, "index": index,
                                     "state": {key: trial[key] for key in common},
                                     "rows": [{key: row[key] for key in row_fields} for row in trial["rows"]],
                                     "trace": [{key: step[key] for key in trace_fields} for step in trial["probe_trace"]]})
        encoded = json.dumps(trajectories, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        flat_encoded = json.dumps(flat_forecasts, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        records.append({"seed": seed, "structured_weights": tensor_fingerprint(model.state_dict()),
                        "flat_weights": tensor_fingerprint(flat.state_dict()),
                        "structured_temperature": calibrated["temperature"],
                        "flat_temperature": flat_temperature,
                        "flat_calibration": flat_calibrated["nll_by_temperature"],
                        "legacy_trajectory_sha256": hashlib.sha256(encoded).hexdigest(),
                        "legacy_flat_forecasts_sha256": hashlib.sha256(flat_encoded).hexdigest()})
    result = {"status": "SAME_HOST_REGRESSION_ONLY_NOT_G1", "cpu_model": cpu_model(),
              "cpu_flags_sha256": cpu_flags_hash(),
              "torch_cpu_capability": torch.backends.cpu.get_cpu_capability(),
              "mkl_available": torch.backends.mkl.is_available(),
              "mkldnn_available": torch.backends.mkldnn.is_available(),
              "mkldnn_enabled": torch.backends.mkldnn.enabled,
              "deterministic_algorithms_enabled": torch.are_deterministic_algorithms_enabled(),
              "python": platform.python_version(), "torch": str(torch.__version__),
              "torch_config_sha256": hashlib.sha256(torch.__config__.show().encode()).hexdigest(),
              "torch_parallel_info_sha256": hashlib.sha256(torch.__config__.parallel_info().encode()).hexdigest(),
              "threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
              "flat_training_batch": tensor_fingerprint(dict(zip(("features", "targets", "valid"), flat_train))),
              "flat_calibration_batch": tensor_fingerprint(dict(zip(("features", "targets", "valid"), flat_calibration))),
              "structured_training_batch": tensor_fingerprint({"contact": structured_train.contact,
                  "episode_id": structured_train.episode_id, "intervention": structured_train.intervention}),
              "structured_calibration_batch": tensor_fingerprint({"contact": structured_calibration.contact,
                  "episode_id": structured_calibration.episode_id, "intervention": structured_calibration.intervention}),
              "models": records}
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
