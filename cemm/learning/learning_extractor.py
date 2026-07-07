"""Phase 9 learning orchestrator.

This component turns structured response outcomes into graph-patch candidates.
It never commits them and never stores raw transcript text.
"""

from __future__ import annotations

from cemm.response.types import ResponseBundle, ResponseSituation

from .budget_learning_extractor import BudgetLearningExtractor
from .observation_builder import LearningObservationBuilder
from .response_learning_extractor import ResponseLearningExtractor
from .learning_types import LearningExtractionResult, LearningPatchCandidate, OutcomeSignal


class ResponseBudgetLearningExtractor:
    def __init__(self) -> None:
        self._observation_builder = LearningObservationBuilder()
        self._response_extractor = ResponseLearningExtractor()
        self._budget_extractor = BudgetLearningExtractor()

    def extract(
        self,
        *,
        situation: ResponseSituation,
        bundle: ResponseBundle,
        explicit_outcome: OutcomeSignal | None = None,
    ) -> LearningExtractionResult:
        observation = self._observation_builder.build(
            situation=situation,
            bundle=bundle,
            explicit_outcome=explicit_outcome,
        )
        candidates = [
            *self._response_extractor.extract(observation),
            *self._budget_extractor.extract(observation),
        ]
        accepted, rejected = self._partition(candidates)
        return LearningExtractionResult(
            observation=observation,
            patch_candidates=accepted,
            rejected_candidates=rejected,
            diagnostics={
                "phase": "learning_v3_1_phase9",
                "patch_candidate_count": len(accepted),
                "rejected_candidate_count": len(rejected),
                "targets": sorted({patch.target for patch in accepted}),
                "outcome_type": observation.outcome.outcome_type,
                "raw_text_persisted": False,
                "commit_performed": False,
            },
        )

    @staticmethod
    def _partition(candidates: list[LearningPatchCandidate]) -> tuple[list[LearningPatchCandidate], list[LearningPatchCandidate]]:
        accepted: list[LearningPatchCandidate] = []
        rejected: list[LearningPatchCandidate] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.patch_id in seen or not candidate.is_allowed_target() or _contains_denied_payload(candidate.payload):
                rejected.append(candidate)
                continue
            accepted.append(candidate)
            seen.add(candidate.patch_id)
        return accepted, rejected


def _contains_denied_payload(payload: dict) -> bool:
    denied = {"text", "raw_text", "surface", "user_text", "assistant_text", "content", "transcript", "message"}
    for key, value in payload.items():
        if key in denied:
            return True
        if isinstance(value, dict) and _contains_denied_payload(value):
            return True
    return False
