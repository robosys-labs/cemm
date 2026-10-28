"""Opt-in normalization of an already represented joint forecast.

This helper does not change historical scorers or learners. It accepts only
small nonnegative mass drift, rescales the whole distribution, and returns a
complete record of the transformation. It neither repairs a materially
invalid forecast nor infers support that disappeared through underflow. A
later post-hoc replay retained eight masses that satisfy the helper's bound;
the original failed forecast and host remain unknown. This observation does
not establish a general fix.
"""
from __future__ import annotations

from math import fsum, isfinite

MASS_TOLERANCE = 1e-6
NORMALIZED_TOLERANCE = 1e-12


def normalize_joint(distribution, *, n_ids):
    """Return (new distribution, audit), accepting only a near-unit mass.

    Worlds must be nonempty tuples of equal-length binary integers, with at
    most six bits. Probabilities must be finite nonnegative Python int/float
    values, excluding bool. Values are all divided by the same accurately
    summed mass: there is no per-world clipping or support completion. A
    near-unit raw total may contain a value slightly over one, which is
    recorded and not accepted when the aggregate error exceeds tolerance.
    The input is never modified. Any positive-to-zero underflow is rejected.
    """
    if type(n_ids) is not int or not 1 <= n_ids <= 6:
        raise ValueError("expected one to six identity slots")
    if type(distribution) is not dict or not distribution:
        raise ValueError("expected a nonempty joint distribution")
    states = list(distribution)
    first = states[0]
    if type(first) is not tuple or len(first) != n_ids:
        raise ValueError("invalid world dimension")
    raw = {}
    for world, value in distribution.items():
        if (type(world) is not tuple or len(world) != n_ids or
                any(type(bit) is not int or bit not in (0, 1) for bit in world)):
            raise ValueError("invalid represented world")
        if type(value) not in (float, int):
            raise ValueError("invalid represented probability type")
        try:
            probability = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError("invalid represented probability") from exc
        if not isfinite(probability) or probability < 0:
            raise ValueError("probability must be finite and nonnegative")
        raw[world] = probability
    try:
        total = fsum(raw.values())
    except OverflowError as exc:
        raise ValueError("probability mass is not finite") from exc
    if not isfinite(total) or total <= 0 or abs(total - 1.0) > MASS_TOLERANCE:
        raise ValueError("joint mass is not within tolerance of one")

    normalized = {world: probability / total for world, probability in raw.items()}
    for world, value in normalized.items():
        if (not isfinite(value) or not 0 <= value <= 1 or
                (raw[world] > 0 and value == 0)):
            raise ValueError("normalization produced invalid probability or lost support")
    normalized_total = fsum(normalized.values())
    if abs(normalized_total - 1.0) > NORMALIZED_TOLERANCE:
        raise ValueError("normalized mass is not sufficiently close to one")

    changes = [{"world": list(world), "before": raw[world], "after": normalized[world],
                "delta": normalized[world] - raw[world]} for world in sorted(raw)]
    max_raw = max(raw.values())
    max_normalized = max(normalized.values())
    raw_maximizers = [list(world) for world in sorted(raw) if raw[world] == max_raw]
    normalized_maximizers = [list(world) for world in sorted(normalized)
                             if normalized[world] == max_normalized]
    return normalized, {
        "raw_total": total,
        "normalized_total": normalized_total,
        "mass_tolerance": MASS_TOLERANCE,
        "normalized_tolerance": NORMALIZED_TOLERANCE,
        "raw_max_probability": max_raw,
        "raw_max_overshoot": max(0.0, max_raw - 1.0),
        "raw_over_one_count": sum(value > 1.0 for value in raw.values()),
        "raw_maximizers": raw_maximizers,
        "normalized_maximizers": normalized_maximizers,
        "maximizer_set_changed": raw_maximizers != normalized_maximizers,
        "raw_lexicographic_map": raw_maximizers[0],
        "normalized_lexicographic_map": normalized_maximizers[0],
        "lexicographic_map_changed": raw_maximizers[0] != normalized_maximizers[0],
        "max_absolute_correction": max(abs(row["delta"]) for row in changes),
        "total_absolute_correction": fsum(abs(row["delta"]) for row in changes),
        "per_world": changes,
    }
