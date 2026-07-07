"""Deadline extraction from semantic time atoms only.

No language regex lives here. Upstream perception is responsible for turning
surface language into TimeAtom/metadata. This component only reads those
semantic time objects and normalizes them into a budget hint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cemm.response.types import BudgetFrame


@dataclass(frozen=True)
class DeadlineHint:
    deadline_ms: float = 0.0
    source: str = ""
    confidence: float = 0.0


class DeadlineParser:
    def parse(self, *, percept: Any | None = None, signal: Any | None = None, kernel: Any | None = None) -> DeadlineHint:
        # Preferred: explicit normalized metadata from signal/percept.
        for obj_name, obj in (("signal", signal), ("percept", percept)):
            metadata = getattr(obj, "metadata", None) or getattr(obj, "features", None) or {}
            if isinstance(metadata, dict):
                for key in ("deadline_ms", "time_budget_ms", "requested_latency_ms"):
                    value = metadata.get(key)
                    if isinstance(value, (int, float)) and value > 0:
                        return DeadlineHint(float(value), f"{obj_name}.{key}", 0.9)

        # Semantic TimeAtom support: accept numeric duration/value fields when
        # upstream supplies them. Do not inspect atom.surface.
        for atom in list(getattr(percept, "times", []) or []):
            value = getattr(atom, "value", None)
            unit = str(getattr(atom, "unit", "") or getattr(atom, "time_key", "") or "").lower()
            if isinstance(value, (int, float)) and value > 0:
                factor = 1.0
                if unit in {"s", "sec", "second", "seconds"}:
                    factor = 1000.0
                elif unit in {"m", "min", "minute", "minutes"}:
                    factor = 60000.0
                elif unit in {"h", "hour", "hours"}:
                    factor = 3600000.0
                return DeadlineHint(float(value) * factor, "percept.time_atom", float(getattr(atom, "confidence", 0.6) or 0.6))
        return DeadlineHint()

    def apply(self, budget: BudgetFrame, hint: DeadlineHint) -> BudgetFrame:
        if hint.deadline_ms <= 0:
            return budget
        total = min(float(budget.total_time_ms), hint.deadline_ms) if budget.total_time_ms > 0 else hint.deadline_ms
        remaining = min(float(budget.remaining_time_ms), hint.deadline_ms) if budget.remaining_time_ms > 0 else hint.deadline_ms
        return BudgetFrame(
            total_time_ms=total,
            remaining_time_ms=remaining,
            latency_target_ms=min(float(budget.latency_target_ms), max(20.0, remaining / 10.0)),
            max_recursive_steps=budget.max_recursive_steps,
            max_candidate_plans=budget.max_candidate_plans,
            max_realized_candidates=budget.max_realized_candidates,
            risk_level=budget.risk_level,
            required_confidence=budget.required_confidence,
            coverage_target=budget.coverage_target,
            allow_partial_answer=budget.allow_partial_answer,
            allow_recursive_distillation=budget.allow_recursive_distillation,
        )
