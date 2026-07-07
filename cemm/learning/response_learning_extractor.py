"""Extract response-construction and framing learning patches."""

from __future__ import annotations

from .patch_factory import LearningPatchFactory
from .learning_types import LearningObservation, LearningPatchCandidate


class ResponseLearningExtractor:
    def __init__(self) -> None:
        self._factory = LearningPatchFactory()

    def extract(self, observation: LearningObservation) -> list[LearningPatchCandidate]:
        patches: list[LearningPatchCandidate] = []
        outcome = observation.outcome.outcome_type
        confidence = observation.outcome.confidence
        success_delta = 1.0 if outcome == "success" else 0.0
        failure_delta = 1.0 if outcome in {"failure", "coverage_complaint"} else 0.0
        unknown_delta = 1.0 if outcome == "unknown" else 0.0

        move_key = tuple([observation.obligation_kind, observation.framing_variant, *observation.move_types])
        if observation.move_types:
            patches.append(self._factory.make(
                target="response_construction_stats",
                key=move_key,
                delta={"selected": 1.0, "success": success_delta, "failure": failure_delta, "unknown": unknown_delta},
                confidence=max(0.3, confidence),
                source_refs=observation.source_refs,
                payload={
                    "language": observation.realized_language,
                    "evidence_ref_count": observation.evidence_ref_count,
                },
            ))

        if observation.framing_variant:
            patches.append(self._factory.make(
                target="framing_success_stats",
                key=(observation.obligation_kind, observation.framing_variant),
                delta={"selected": 1.0, "success": success_delta, "failure": failure_delta, "unknown": unknown_delta},
                confidence=max(0.3, confidence),
                source_refs=observation.source_refs,
                payload={"selector_mode": observation.selector_mode},
            ))

        if outcome == "failure" and ("repair_prior_response" in observation.move_types or observation.selected_plan_id):
            patches.append(self._factory.make(
                target="repair_failure_trace",
                key=(observation.obligation_kind, observation.framing_variant, observation.selected_plan_id),
                delta={"failure": 1.0},
                confidence=max(0.4, confidence),
                source_refs=observation.source_refs,
                payload={"move_types": observation.move_types},
            ))

        if observation.safety_categories:
            patches.append(self._factory.make(
                target="safety_response_trace",
                key=(observation.obligation_kind, *observation.safety_categories, observation.framing_variant),
                delta={"selected": 1.0, "success": success_delta, "failure": failure_delta},
                confidence=max(0.5, confidence),
                source_refs=observation.source_refs,
                payload={"move_types": observation.move_types},
            ))
        return patches
