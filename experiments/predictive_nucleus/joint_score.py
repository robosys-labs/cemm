"""Separate historical clipped diagnostics from represented-world log loss."""
from __future__ import annotations

from math import fsum, isfinite, log

LEGACY_FLOOR = 1e-12


def joint_log_loss(probability: float) -> dict:
    """Return a JSON-safe uncapped loss and explicit zero/floor indicators.

    A zero is a zero in the numerical forecast representation; it may result
    from genuine zero support or numerical underflow. Do not silently replace
    its infinite log loss with a finite value.
    """
    if type(probability) not in (float, int) or not isfinite(probability) or not 0 <= probability <= 1 + 1e-6:
        raise ValueError("invalid represented joint probability")
    p = min(1.0, float(probability))
    return {"clipped_log_loss": -log(max(p, LEGACY_FLOOR)),
            "uncapped_log_loss": -log(p) if p else None,
            "zero_probability": p == 0.0,
            "floor_applied": p < LEGACY_FLOOR}


def summarize_joint_log_loss(scores: list[dict]) -> dict:
    if not scores:
        raise ValueError("no joint scores")
    zero_count = sum(s["zero_probability"] for s in scores)
    return {"clipped_mean": fsum(s["clipped_log_loss"] for s in scores) / len(scores),
            "floor_applied_count": sum(s["floor_applied"] for s in scores),
            "zero_probability_count": zero_count,
            "uncapped_mean_is_infinite": zero_count > 0,
            "uncapped_mean": None if zero_count else
                fsum(s["uncapped_log_loss"] for s in scores) / len(scores)}
