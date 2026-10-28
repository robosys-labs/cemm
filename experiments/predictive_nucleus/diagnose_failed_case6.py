"""Post-hoc validation of case 6 forecasts from the failed public study.

This never trains a neural model, scores a forecast, or calls `gold_after`.
The evaluator reads its own state to reconstruct sensor readings; this is an
in-process diagnostic, not a blind boundary. The script restores the saved
weights and empirical controls and checks the runner's probability contract.
Its host may differ from the original failure host; absence of a reproduced
violation therefore does not establish that the failure was spurious.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import permutations
import json
from math import fsum, isfinite
from pathlib import Path
import platform
from unittest.mock import patch

from .development_run import _fingerprint, _json
from .factorial_run import ARMS, MODELS, SEEDS, _replay, read_protocol
from .factorial_training_data import prepare_training, rename_full_history
from .full_sensor_evaluation import full_sensor_evaluation_view
from .history_memory import HistoryMemory
from .role_history_memory import RoleHistoryMemory
from .sensor_controls import EventMemory
from .two_pair_fixture import make_evaluator_episode
from .world import Episode

RUNNER_SHA256 = "ef2bcba62114d3a9809cfffc1406321b211930514dc8318ad3c793862cc2fba3"
FAILURE_SHA256 = "bbfba018d70c386c52898ee9678f78baf65110e8dc2ede552aaf0d9dbe2985c7"
PROGRESS_SHA256 = "1626d5fe9c2c2393ebd3c5afc5b48357578c47db8dd2c2ec019729c2ef02c0e7"


def inspect_forecast(forecast, n_ids):
    """Check the exact original forecast validation, without evaluator truth."""
    status, reason, distribution = forecast
    problems = []
    if status == "ABSTAIN":
        if distribution is not None:
            problems.append({"kind": "abstention_with_distribution"})
        return problems
    if status != "PREDICTED" or type(distribution) is not dict or not distribution:
        return [{"kind": "invalid_status_or_distribution", "status": repr(status),
                 "distribution_type": type(distribution).__name__}]
    valid_probabilities = []
    for state, probability in distribution.items():
        if (type(state) is not tuple or len(state) != n_ids or
                any(type(bit) is not int or bit not in (0, 1) for bit in state)):
            problems.append({"kind": "invalid_world", "world": repr(state)})
        if (type(probability) not in (float, int) or not isfinite(probability) or
                not 0 <= probability <= 1):
            problems.append({"kind": "invalid_probability", "world": repr(state),
                             "probability": repr(probability),
                             "probability_type": type(probability).__name__})
        else:
            valid_probabilities.append(probability)
    if len(valid_probabilities) == len(distribution):
        total = fsum(valid_probabilities)
        if abs(total - 1.0) > 1e-6:
            problems.append({"kind": "not_normalized", "sum": repr(total)})
    return problems


def _progress(directory):
    """Require the logged case-6 failure and unique verified checkpoint entries."""
    failure_bytes = (directory / "FAILED.json").read_bytes()
    progress_bytes = (directory / "progress.jsonl").read_bytes()
    if (sha256(failure_bytes).hexdigest() != FAILURE_SHA256 or
            sha256(progress_bytes).hexdigest() != PROGRESS_SHA256):
        raise ValueError("failure or progress log hash mismatch")
    failure = json.loads(failure_bytes)
    if (failure.get("status") != "INCOMPLETE" or failure.get("phase") != "evaluation" or
            failure.get("message") != "invalid represented world" or
            failure.get("completed_cases") != list(range(6)) or
            (directory / "COMPLETE").exists() or (directory / "report.json").exists()):
        raise ValueError("not the expected incomplete public study")
    checkpoints, controls, case_started = {}, {}, False
    for line in progress_bytes.decode("utf-8").splitlines():
        row = json.loads(line)
        if row.get("phase") == "case_started" and row.get("case") == 6:
            case_started = True
        if row.get("phase") == "checkpoint_verified":
            key = (row["arm"], row["model"])
            if key in checkpoints:
                raise ValueError("duplicate verified checkpoint")
            checkpoints[key] = row["checkpoint"]
        if row.get("phase") == "control_fit_finished":
            key = (row["id_arm"], row["model"])
            if key in controls:
                raise ValueError("duplicate verified control")
            controls[key] = row
    expected = {(f"{arm}/{target}/{seed}", model)
                for seed in SEEDS for arm, target in ARMS for model in ("structured", "flat")}
    if (not case_started or set(checkpoints) != expected or
            set(controls) != {(arm, name) for arm in ("repeated", "augmented")
                              for name in ("event", "literal", "role")}):
        raise ValueError("missing expected failure or verified model inventory")
    for (arm, model), row in checkpoints.items():
        expected_name = arm.replace("/", "-") + "-" + model + ".pt"
        if (row.get("path") != expected_name or
                sha256((directory / expected_name).read_bytes()).hexdigest() != row.get("sha256")):
            raise ValueError("checkpoint byte hash mismatch")
    return checkpoints, controls


def _restore_models(directory, checkpoints, torch):
    from .flat_reference import FlatWorldGRU
    from .latent_model import ContactKernel
    fits = {}
    for id_arm, target in ARMS:
        for seed in SEEDS:
            key = f"{id_arm}/{target}/{seed}"
            models = {}
            for name, factory in (("structured", ContactKernel), ("flat", FlatWorldGRU)):
                info = checkpoints[(key, name)]
                state = torch.load(directory / info["path"], map_location="cpu", weights_only=True)
                if _fingerprint(state) != info["weight_fingerprint"]:
                    raise ValueError("checkpoint semantic fingerprint mismatch")
                model = factory()
                model.load_state_dict(state, strict=True)
                if _fingerprint(model.state_dict()) != info["weight_fingerprint"]:
                    raise ValueError("restored model fingerprint mismatch")
                models[name] = model
            fits[(id_arm, target, seed)] = {"kernel": models["structured"].freeze(), "flat": models["flat"]}
    return fits


def _restore_controls(fits, logged):
    for id_arm in ("repeated", "augmented"):
        histories = [row.history for row in prepare_training(id_arm)]
        tables = {"event": EventMemory.fit(histories), "literal": HistoryMemory.fit_full_sensor(histories),
                  "role": RoleHistoryMemory.fit(histories)}
        for name, table in tables.items():
            rows = table.rows if name == "event" else (table._rows if name == "literal" else table._memory._rows)
            if sha256(_json(rows).encode()).hexdigest() != logged[(id_arm, name)]["table_sha256"]:
                raise ValueError("reconstructed control table hash mismatch")
        for target in ("masked", "full"):
            for seed in SEEDS:
                fits[(id_arm, target, seed)].update(tables)


def _forbid_truth(*args, **kwargs):
    raise RuntimeError("case-6 diagnostic must not read evaluator truth")


def run(directory):
    """Inspect only the original failed case using verified saved checkpoints."""
    import torch
    if (torch.__version__ != "2.10.0+cpu" or not platform.python_version().startswith("3.13.") or
            torch.version.cuda is not None or torch.version.hip is not None):
        raise RuntimeError("diagnostic requires the study's CPU PyTorch and Python versions")
    read_protocol()
    runner = Path(__file__).with_name("factorial_run.py")
    if sha256(runner.read_bytes()).hexdigest() != RUNNER_SHA256:
        raise ValueError("original reviewed runner hash mismatch")
    directory = Path(directory)
    checkpoints, controls = _progress(directory)
    threads, deterministic = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled()
    warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            torch.use_deterministic_algorithms(True)
            fits = _restore_models(directory, checkpoints, torch)
            _restore_controls(fits, controls)
            with patch.object(Episode, "gold_after", _forbid_truth):
                episode = make_evaluator_episode(6, block=0)
                history = full_sensor_evaluation_view(episode)
                ids = tuple(sorted(name for name, _ in history._observations[0]))
                anomalies, checked = [], 0
                for names in permutations(ids):
                    mapping = dict(zip(ids, names))
                    renamed = rename_full_history(history, mapping)
                    for id_arm, target in ARMS:
                        for seed in SEEDS:
                            agents, _ = _replay(renamed, fits[(id_arm, target, seed)])
                            for step in range(5):
                                for model, agent in zip(MODELS, agents, strict=True):
                                    checked += 1
                                    for item in inspect_forecast(agent.forecasts[step], len(ids)):
                                        anomalies.append({"case": 6, "mapping": mapping, "id_arm": id_arm,
                                                          "target": target, "seed": seed, "model": model,
                                                          "step": step, **item})
            if checked != 3600:
                raise RuntimeError("unexpected forecast inventory")
            try:
                cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                            if line.lower().startswith("model name")), platform.processor() or "unknown")
            except OSError:
                cpu = platform.processor() or "unknown"
            return {"status": "RAW_CONTRACT_VIOLATION_OBSERVED" if anomalies else "NO_VIOLATION_OBSERVED",
                    "case": 6, "checked_forecasts": checked, "anomalies": anomalies,
                    "verified_checkpoints": len(checkpoints), "verified_control_tables": len(controls),
                    "failure_sha256": FAILURE_SHA256, "progress_sha256": PROGRESS_SHA256,
                    "original_failure_environment": "not recorded; host equivalence is unknown",
                    "environment": {"cpu": cpu, "python": platform.python_version(), "torch": torch.__version__,
                                    "torch_config_sha256": sha256(torch.__config__.show().encode()).hexdigest(),
                                    "threads": torch.get_num_threads(),
                                    "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()},
                    "limitations": ["Post-hoc replay of one opened public case; no gold_after call or accuracy score.",
                                    "Evaluator state is read solely to construct sensors; no blind or custody boundary.",
                                    "Original failure did not record the violating forecast or value; an observed violation may differ.",
                                    "Different host/configuration may not reproduce the original failure."]}
    finally:
        torch.set_num_threads(threads)
        torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failed-output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.failed_output), sort_keys=True, allow_nan=False))
