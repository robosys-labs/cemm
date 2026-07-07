"""Outcome interpretation from already-structured reaction signals.

No natural-language cue matching belongs here. A reaction detector or runtime
component must provide structured outcome fields before Phase 9 runs.
"""

from __future__ import annotations

from typing import Any

from .learning_types import OutcomeSignal


_NEGATIVE_OUTCOMES = frozenset({"failure", "correction", "complaint", "coverage_complaint", "repair"})
_POSITIVE_OUTCOMES = frozenset({"success", "accepted", "resolved", "safety_ok"})


class OutcomeInterpreter:
    def interpret(self, reaction_signal: Any | None = None, explicit_outcome: OutcomeSignal | None = None) -> OutcomeSignal:
        if explicit_outcome is not None:
            return self._normalize(explicit_outcome)
        if reaction_signal is None:
            return OutcomeSignal(outcome_type="unknown", confidence=0.3)

        outcome_type = (
            getattr(reaction_signal, "outcome_type", "")
            or getattr(reaction_signal, "reaction_type", "")
            or getattr(reaction_signal, "error_type", "")
            or "unknown"
        )
        features = dict(getattr(reaction_signal, "features", {}) or {})
        for attr in ("coverage_complaint", "task_success", "repair_requested", "safety_acknowledged"):
            if hasattr(reaction_signal, attr):
                features[attr] = getattr(reaction_signal, attr)
        return self._normalize(OutcomeSignal(
            outcome_type=str(outcome_type),
            confidence=float(getattr(reaction_signal, "confidence", 0.5) or 0.5),
            source_refs=_object_refs(reaction_signal),
            features=features,
        ))

    @staticmethod
    def _normalize(outcome: OutcomeSignal) -> OutcomeSignal:
        normalized = str(outcome.outcome_type or "unknown")
        if normalized in _POSITIVE_OUTCOMES:
            normalized = "success"
        elif normalized in _NEGATIVE_OUTCOMES:
            # Keep coverage complaint distinct because it teaches budget/distillation.
            normalized = "coverage_complaint" if normalized == "coverage_complaint" else "failure"
        return OutcomeSignal(
            outcome_type=normalized,
            confidence=max(0.0, min(1.0, float(outcome.confidence or 0.0))),
            source_refs=list(outcome.source_refs or []),
            features=dict(outcome.features or {}),
        )


def _object_refs(obj: Any) -> list[str]:
    refs: list[str] = []
    for attr in ("id", "signal_id", "reaction_id", "turn_id", "source_id"):
        value = getattr(obj, attr, "")
        if value:
            refs.append(str(value))
    for attr in ("source_refs", "evidence_refs"):
        refs.extend(str(v) for v in (getattr(obj, attr, []) or []) if v)
    return _dedupe(refs)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
