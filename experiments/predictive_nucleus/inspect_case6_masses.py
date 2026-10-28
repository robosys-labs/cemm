"""Inspect eight raw masses for a single post-hoc case-6 anomaly.

The failed study's saved checkpoints are restored without neural fitting. The
evaluator reads state solely to reconstruct sensor observations; `gold_after`
is blocked. No forecast is scored against truth. Renormalization is reported
only as a numerical candidate, not applied to the frozen scorer or justified
as a general correction.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
from math import fsum, isfinite
from pathlib import Path
import platform
from unittest.mock import patch

from .diagnose_failed_case6 import (FAILURE_SHA256, PROGRESS_SHA256, RUNNER_SHA256,
                                    _forbid_truth, _progress, _restore_controls, _restore_models)
from .factorial_run import _replay, read_protocol
from .factorial_training_data import rename_full_history
from .full_sensor_evaluation import full_sensor_evaluation_view
from .two_pair_fixture import make_evaluator_episode
from .world import Episode

DIAGNOSTIC_SHA256 = "fd632e8a4be925fd4f97651d16d8715e2a54c45a4022e855ac6d761a27bfd4ce"
PRIOR_RESULT_SHA256 = "8ac484d4c78956e6a76bf7bdf0496037bce7c967d94e601dc04a7440e3193fa6"
PRIOR_RESULT = Path(__file__).with_name("results") / "case6-posthoc-274b2cf.json"
EXPECTED_MAPPING = {"6d783e2ee26d": "e005e6edb86c", "bdccd9186cbc": "6d783e2ee26d",
                    "e005e6edb86c": "bdccd9186cbc"}
WORLDS = tuple(product((0, 1), repeat=3))


def inspect_masses(forecast):
    """Record all raw masses and a conditional arithmetic-only normalization."""
    status, reason, distribution = forecast
    result = {"status": status, "reason": reason, "raw_masses": None,
              "normalization_eligible": False, "normalization_candidate": None}
    if status != "PREDICTED" or type(distribution) is not dict:
        result["ineligible_reason"] = "forecast has no predicted distribution"
        return result
    result["raw_masses"] = [{"world": repr(world), "probability": repr(value),
                             "probability_type": type(value).__name__}
                            for world, value in distribution.items()]
    if (len(distribution) != 8 or set(distribution) != set(WORLDS) or
            any(type(world) is not tuple or len(world) != 3 or
                any(type(bit) is not int or bit not in (0, 1) for bit in world)
                for world in distribution)):
        result["ineligible_reason"] = "world support is not exactly all eight tuples"
        return result
    values = []
    for world in WORLDS:
        value = distribution[world]
        if type(value) not in (float, int):
            result["ineligible_reason"] = "nonnumeric probability"
            return result
        try:
            valid = isfinite(value) and value >= 0
        except OverflowError:
            valid = False
        if not valid:
            result["ineligible_reason"] = "nonfinite or negative probability"
            return result
        values.append(float(value))
    try:
        total = fsum(values)
    except OverflowError:
        result["ineligible_reason"] = "probability sum overflow"
        return result
    result.update({"raw_sum": total, "raw_sum_minus_one": total - 1.0,
                   "raw_min": min(values), "raw_max": max(values),
                   "raw_max_above_one": max(0.0, max(values) - 1.0)})
    if not isfinite(total) or total <= 0 or abs(total - 1.0) > 1e-6:
        result["ineligible_reason"] = "sum is not positive and within 1e-6 of one"
        return result
    normalized = [value / total for value in values]
    raw_map = min(range(8), key=lambda i: (-values[i], WORLDS[i]))
    normalized_map = min(range(8), key=lambda i: (-normalized[i], WORLDS[i]))
    result["normalization_eligible"] = True
    result["normalization_candidate"] = {
        "masses": [{"world": list(world), "probability": value}
                   for world, value in zip(WORLDS, normalized, strict=True)],
        "sum": fsum(normalized),
        "max_absolute_change": max(abs(a - b) for a, b in zip(values, normalized, strict=True)),
        # Raw masses may not form a distribution; this is a half-L1 change,
        # not a probability total-variation distance.
        "half_l1_change": .5 * fsum(abs(a - b) for a, b in zip(values, normalized, strict=True)),
        "raw_map": list(WORLDS[raw_map]), "normalized_map": list(WORLDS[normalized_map]),
        "map_changed": raw_map != normalized_map,
    }
    return result


def _prior_finding():
    raw = PRIOR_RESULT.read_bytes()
    if sha256(raw).hexdigest() != PRIOR_RESULT_SHA256:
        raise ValueError("prior post-hoc result hash mismatch")
    result = json.loads(raw)
    anomalies = result.get("anomalies")
    if (result.get("status") != "RAW_CONTRACT_VIOLATION_OBSERVED" or
            not isinstance(anomalies, list) or len(anomalies) != 1):
        raise ValueError("prior anomaly inventory changed")
    anomaly = anomalies[0]
    if (anomaly.get("case"), anomaly.get("id_arm"), anomaly.get("target"), anomaly.get("seed"),
            anomaly.get("model"), anomaly.get("step"), anomaly.get("mapping"), anomaly.get("kind"),
            anomaly.get("world"), anomaly.get("probability")) != (
                6, "augmented", "masked", 37, "flat", 4, EXPECTED_MAPPING, "invalid_probability",
                "(1, 1, 1)", "1.00000003851976"):
        raise ValueError("prior anomaly context changed")
    return anomaly, result.get("environment")


def run(directory):
    """Inspect the selected case 6 forecast; never call `gold_after`."""
    import torch
    if (torch.__version__ != "2.10.0+cpu" or not platform.python_version().startswith("3.13.") or
            torch.version.cuda is not None or torch.version.hip is not None):
        raise RuntimeError("diagnostic requires the study's CPU PyTorch and Python versions")
    read_protocol()
    if sha256(Path(__file__).with_name("factorial_run.py").read_bytes()).hexdigest() != RUNNER_SHA256:
        raise ValueError("original reviewed runner hash mismatch")
    if sha256(Path(__file__).with_name("diagnose_failed_case6.py").read_bytes()).hexdigest() != DIAGNOSTIC_SHA256:
        raise ValueError("original post-hoc diagnostic hash mismatch")
    prior, prior_environment = _prior_finding()
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
                renamed = rename_full_history(history, EXPECTED_MAPPING)
                agents, _ = _replay(renamed, fits[("augmented", "masked", 37)])
                selected = agents[1].forecasts[4]  # _replay's second consumer is the flat model.
                analysis = inspect_masses(selected)
            try:
                cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                            if line.lower().startswith("model name")), platform.processor() or "unknown")
            except OSError:
                cpu = platform.processor() or "unknown"
            observed = selected[2].get((1, 1, 1)) if type(selected[2]) is dict else None
            return {"status": "POST_HOC_RAW_MASS_INSPECTION", "case": 6, "step": 4,
                    "id_arm": "augmented", "target": "masked", "seed": 37, "model": "flat",
                    "mapping": EXPECTED_MAPPING, "analysis": analysis,
                    "prior_probability": prior.get("probability"),
                    "same_probability_as_prior_diagnostic": repr(observed) == prior.get("probability"),
                    "prior_diagnostic_environment": prior_environment,
                    "verified_checkpoints": len(checkpoints), "verified_control_tables": len(controls),
                    "failure_sha256": FAILURE_SHA256, "progress_sha256": PROGRESS_SHA256,
                    "prior_result_sha256": PRIOR_RESULT_SHA256,
                    "original_failure_environment": "not recorded; host equivalence is unknown",
                    "environment": {"cpu": cpu, "python": platform.python_version(), "torch": torch.__version__,
                                    "torch_config_sha256": sha256(torch.__config__.show().encode()).hexdigest(),
                                    "threads": torch.get_num_threads(),
                                    "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()},
                    "limitations": ["Only one observed post-hoc anomaly context; no gold_after call or accuracy score.",
                                    "Evaluator state supplies sensors in-process; not a blind boundary.",
                                    "Original failure offender and host were not recorded; this context may differ.",
                                    "Normalization is an arithmetic candidate, not an approved scoring correction."]}
    finally:
        torch.set_num_threads(threads)
        torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failed-output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.failed_output), sort_keys=True, allow_nan=False))
