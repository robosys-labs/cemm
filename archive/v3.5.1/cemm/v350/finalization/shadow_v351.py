"""Typed old/new shadow comparison for Phase 18 migration closure."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping


SEMANTIC_DIMENSIONS = (
    "grounding", "canonical_meaning", "query_bindings", "epistemic_placement",
    "durable_deltas", "frontiers", "response_semantics", "realization",
)
METRIC_DIMENSIONS = ("latency", "storage_volume")
REQUIRED_SHADOW_DIMENSIONS = (*SEMANTIC_DIMENSIONS, *METRIC_DIMENSIONS)
_MISSING = object()


def _normalize(value: Any):
    if value is _MISSING:
        return {"__missing__": True}
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _normalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list, set, frozenset)):
        normalized = [_normalize(item) for item in value]
        return sorted(normalized, key=repr) if isinstance(value, (set, frozenset)) else normalized
    if hasattr(value, "value") and isinstance(getattr(value, "value"), (str, int, float, bool)):
        return value.value
    return value


def compare_shadow_capture_v351(
    old: Mapping[str, Any],
    new: Mapping[str, Any],
    *,
    maximum_latency_ratio: float = 1.25,
    maximum_storage_ratio: float = 1.20,
):
    comparisons = {}
    passed = True
    for name in SEMANTIC_DIMENSIONS:
        left = _normalize(old.get(name, _MISSING))
        right = _normalize(new.get(name, _MISSING))
        equal = left == right
        comparisons[name] = {"equal": equal, "old": left, "new": right}
        passed = passed and equal
    for name, limit in (("latency", maximum_latency_ratio), ("storage_volume", maximum_storage_ratio)):
        left = old.get(name, _MISSING)
        right = new.get(name, _MISSING)
        valid = left is not _MISSING and right is not _MISSING and float(left) >= 0.0 and float(right) >= 0.0
        ratio = None if not valid else (float("inf") if float(left) == 0.0 and float(right) > 0.0 else (1.0 if float(left) == 0.0 else float(right) / float(left)))
        equal = bool(valid and ratio <= limit)
        comparisons[name] = {"within_gate": equal, "old": _normalize(left), "new": _normalize(right), "ratio": ratio, "limit": limit}
        passed = passed and equal
    return {
        "gate": "shadow_equivalence",
        "status": "pass" if passed else "fail",
        "pass": passed,
        "required_dimensions": REQUIRED_SHADOW_DIMENSIONS,
        "comparisons": comparisons,
    }


__all__ = ["REQUIRED_SHADOW_DIMENSIONS", "compare_shadow_capture_v351"]
