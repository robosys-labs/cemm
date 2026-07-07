"""Skill induction — detect repeated patterns and create candidate procedure models.

From cemm_original_work_subplans.md §7.6:

Trigger candidate procedure model when:
- similar goal repeats
- same slot pattern repeats
- same tool sequence repeats
- outcome succeeds often enough
- user correction converges on same defaults

Candidate remains inactive until validated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InductionRecord:
    """A record of an observed execution trace for induction."""
    goal_key: str
    slot_pattern: tuple[str, ...]
    tool_sequence: tuple[str, ...]
    success: bool
    confidence: float
    timestamp: float = 0.0


@dataclass
class InductionCandidate:
    """A candidate procedure model produced by induction."""
    goal_key: str
    registry_key: str
    required_slots: list[str] = field(default_factory=list)
    optional_slots: list[str] = field(default_factory=list)
    tool_sequence: list[str] = field(default_factory=list)
    observed_count: int = 0
    success_count: int = 0
    reliability: float = 0.0
    validated: bool = False


class SkillInductor:
    """Watches for repeated patterns and produces candidate procedure models.

    MVP: rule-based induction from a stream of InductionRecords.
    """

    def __init__(self, min_observations: int = 3, min_success_rate: float = 0.6) -> None:
        self._min_observations = min_observations
        self._min_success_rate = min_success_rate
        self._records: list[InductionRecord] = []
        self._candidates: dict[str, InductionCandidate] = {}

    def observe(self, record: InductionRecord) -> None:
        """Record an execution trace for induction."""
        self._records.append(record)
        self._update_candidates(record)

    def _update_candidates(self, record: InductionRecord) -> None:
        """Update candidate procedure models based on new observations."""
        import hashlib
        slot_hash = hashlib.sha256(str(record.slot_pattern).encode()).hexdigest()[:16]
        tool_hash = hashlib.sha256(str(record.tool_sequence).encode()).hexdigest()[:16]
        key = f"{record.goal_key}::{slot_hash}::{tool_hash}"

        if key not in self._candidates:
            self._candidates[key] = InductionCandidate(
                goal_key=record.goal_key,
                registry_key=self._derive_registry_key(record),
                required_slots=list(record.slot_pattern),
                tool_sequence=list(record.tool_sequence),
            )

        cand = self._candidates[key]
        cand.observed_count += 1
        if record.success:
            cand.success_count += 1
        cand.reliability = cand.success_count / max(cand.observed_count, 1)

        # Activate candidate when thresholds are met
        if (cand.observed_count >= self._min_observations
                and cand.reliability >= self._min_success_rate
                and not cand.validated):
            cand.validated = True

    @staticmethod
    def _derive_registry_key(record: InductionRecord) -> str:
        """Derive a registry key from the goal key."""
        return record.goal_key.replace(" ", "_").lower()

    def active_candidates(self) -> list[InductionCandidate]:
        """Return candidates that have been validated (passed thresholds)."""
        return [c for c in self._candidates.values() if c.validated]

    def pending_candidates(self) -> list[InductionCandidate]:
        """Return candidates that haven't yet reached thresholds."""
        return [c for c in self._candidates.values() if not c.validated]

    def to_candidate_procedure(
        self,
        candidate: InductionCandidate,
        model_id: str,
    ) -> dict[str, Any]:
        """Convert a validated candidate to a ProcedureModel-like dict."""
        from ..types.procedure_model import ConfirmationPolicy
        risk = 1.0 - candidate.reliability
        policy = ConfirmationPolicy.RISKY_ONLY if risk > 0.2 else ConfirmationPolicy.NEVER
        return {
            "model_id": model_id,
            "registry_key": candidate.registry_key,
            "required_slots": candidate.required_slots,
            "tool_sequence": candidate.tool_sequence,
            "confirmation_policy": policy.value,
            "reliability_log_odds": round(candidate.reliability, 4),
        }

    def export_records(self, path: str | Path) -> None:
        """Export observation records to JSONL."""
        with open(path, "w") as f:
            for r in self._records:
                f.write(json.dumps({
                    "goal_key": r.goal_key,
                    "slot_pattern": list(r.slot_pattern),
                    "tool_sequence": list(r.tool_sequence),
                    "success": r.success,
                    "confidence": r.confidence,
                    "timestamp": r.timestamp,
                }) + "\n")
