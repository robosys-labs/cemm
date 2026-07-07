"""Apply query budget limits to AnswerBinding-like results."""

from __future__ import annotations

import copy
from typing import Any

from .types import QueryBudgetPolicy


class AnswerBindingLimiter:
    def limit(self, binding: Any, policy: QueryBudgetPolicy) -> Any:
        if binding is None:
            return None
        limited = copy.copy(binding)
        fills = list(getattr(binding, "slot_fills", []) or [])
        fills.sort(key=lambda fill: (self._sufficient(fill, policy), float(getattr(fill, "confidence", 0.0) or 0.0)), reverse=True)
        if policy.stop_on_first_sufficient:
            sufficient = [fill for fill in fills if self._sufficient(fill, policy)]
            fills = sufficient[:1] or fills[:1]
        else:
            fills = fills[: max(1, policy.max_results)]
        for fill in fills:
            path = list(getattr(fill, "explanation_path", []) or [])
            if path and policy.explanation_depth >= 0:
                setattr(fill, "explanation_path", path[: policy.explanation_depth + 1])
        setattr(limited, "slot_fills", fills)
        setattr(limited, "has_answer", bool(fills))
        setattr(limited, "confidence", max((float(getattr(fill, "confidence", 0.0) or 0.0) for fill in fills), default=0.0))
        if hasattr(limited, "matched_frame_ids"):
            matched: list[str] = []
            for fill in fills:
                matched.extend(getattr(fill, "source_frame_ids", []) or [])
            setattr(limited, "matched_frame_ids", _dedupe(matched))
        if hasattr(limited, "explanation_paths"):
            setattr(limited, "explanation_paths", [list(getattr(fill, "explanation_path", []) or []) for fill in fills if getattr(fill, "explanation_path", [])])
        return limited

    @staticmethod
    def _sufficient(fill: Any, policy: QueryBudgetPolicy) -> bool:
        confidence = float(getattr(fill, "confidence", 0.0) or 0.0)
        if confidence < policy.min_confidence:
            return False
        if policy.require_evidence_refs and not (getattr(fill, "evidence_refs", []) or getattr(fill, "source_frame_ids", [])):
            return False
        return True


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
