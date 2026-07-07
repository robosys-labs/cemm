"""Extract budget and distillation strategy learning patches."""

from __future__ import annotations

from .patch_factory import LearningPatchFactory
from .learning_types import LearningObservation, LearningPatchCandidate


class BudgetLearningExtractor:
    def __init__(self) -> None:
        self._factory = LearningPatchFactory()

    def extract(self, observation: LearningObservation) -> list[LearningPatchCandidate]:
        patches: list[LearningPatchCandidate] = []
        outcome = observation.outcome.outcome_type
        success_delta = 1.0 if outcome == "success" else 0.0
        failure_delta = 1.0 if outcome in {"failure", "coverage_complaint"} else 0.0
        coverage_complaint_delta = 1.0 if outcome == "coverage_complaint" else 0.0
        pressure_bucket = self._pressure_bucket(observation.budget_pressure)

        patches.append(self._factory.make(
            target="budget_allocation_stats",
            key=(observation.obligation_kind, pressure_bucket, observation.selector_mode),
            delta={
                "turns": 1.0,
                "success": success_delta,
                "failure": failure_delta,
                "coverage_complaint": coverage_complaint_delta,
            },
            confidence=max(0.3, observation.outcome.confidence),
            source_refs=observation.source_refs,
            payload={
                "candidate_count": observation.candidate_count,
                "rejected_count": observation.rejected_count,
                "evidence_ref_count": observation.evidence_ref_count,
            },
        ))

        if observation.coverage_estimate is not None:
            patches.append(self._factory.make(
                target="distillation_strategy_stats",
                key=(observation.obligation_kind, pressure_bucket, "partial" if observation.partial_coverage else "complete"),
                delta={
                    "turns": 1.0,
                    "coverage_sum": float(observation.coverage_estimate),
                    "partial": 1.0 if observation.partial_coverage else 0.0,
                    "coverage_complaint": coverage_complaint_delta,
                },
                confidence=max(0.3, observation.outcome.confidence),
                source_refs=observation.source_refs,
                payload={"coverage_estimate": observation.coverage_estimate},
            ))
        return patches

    @staticmethod
    def _pressure_bucket(pressure: float) -> str:
        if pressure >= 0.75:
            return "high_pressure"
        if pressure >= 0.4:
            return "medium_pressure"
        return "low_pressure"
