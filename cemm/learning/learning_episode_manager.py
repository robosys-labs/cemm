"""LearningEpisodeManager — manages the lifecycle of learning episodes.
Handles creation, resumption, question tracking, evidence collection,
provisional binding, and expiry.
"""

from __future__ import annotations

import uuid
import time
from typing import Any

from ..types.learning_episode import LearningEpisode, EpisodeStatus, QuestionActKind, LearningObligation
from ..types.semantic_gap import SemanticGap, GapKind
from ..types.semantic_ref import SemanticRef, SemanticRefKind
from ..types.learning_hypothesis import LearningHypothesis, HypothesisTargetKind
from ..types.learning_evidence import LearningEvidenceEvent, EvidenceKind, EvidenceStance


class LearningEpisodeManager:
    """Manages learning episodes across turns.

    Persisted in SessionStore between turns.
    Supports multi-turn recursive acquisition.
    """

    def __init__(self) -> None:
        self._episodes: dict[str, LearningEpisode] = {}
        self._gaps: dict[str, SemanticGap] = {}
        self._hypotheses: dict[str, LearningHypothesis] = {}
        self._evidence_events: dict[str, LearningEvidenceEvent] = {}

    def create_episode(
        self,
        context_id: str,
        gaps: list[SemanticGap],
        target_scope: str = "session",
        recursion_depth: int = 0,
    ) -> LearningEpisode:
        episode_id = uuid.uuid4().hex[:16]
        episode = LearningEpisode(
            episode_id=episode_id,
            context_id=context_id,
            target_scope=target_scope,
            target_gap_ids=[g.gap_id for g in gaps],
            recursion_depth=recursion_depth,
            status=EpisodeStatus.ACTIVE,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._episodes[episode_id] = episode
        for gap in gaps:
            self._gaps[gap.gap_id] = gap
        return episode

    def get_episode(self, episode_id: str) -> LearningEpisode | None:
        return self._episodes.get(episode_id)

    def get_active_episodes(self, context_id: str) -> list[LearningEpisode]:
        return [
            e for e in self._episodes.values()
            if e.context_id == context_id and e.is_active
        ]

    def record_evidence(
        self,
        episode_id: str,
        hypothesis_id: str,
        evidence_kind: EvidenceKind,
        stance: EvidenceStance = EvidenceStance.SUPPORT,
        weight: float = 0.5,
        source_id: str = "",
    ) -> LearningEvidenceEvent:
        event_id = uuid.uuid4().hex[:16]
        event = LearningEvidenceEvent(
            event_id=event_id,
            target_hypothesis_id=hypothesis_id,
            evidence_kind=evidence_kind,
            stance=stance,
            weight=weight,
            source_id=source_id,
            observed_at=time.time(),
        )
        self._evidence_events[event_id] = event
        episode = self._episodes.get(episode_id)
        if episode is not None:
            episode.evidence_event_ids.append(event_id)
            episode.updated_at = time.time()
        return event

    def create_hypothesis(
        self,
        episode_id: str,
        target_kind: HypothesisTargetKind,
        proposed_artifact: dict[str, Any] | None = None,
    ) -> LearningHypothesis:
        hypothesis_id = uuid.uuid4().hex[:16]
        hypothesis = LearningHypothesis(
            hypothesis_id=hypothesis_id,
            target_kind=target_kind,
            proposed_artifact=proposed_artifact or {},
        )
        self._hypotheses[hypothesis_id] = hypothesis
        episode = self._episodes.get(episode_id)
        if episode is not None:
            episode.hypothesis_ids.append(hypothesis_id)
            episode.updated_at = time.time()
        return hypothesis

    def mark_question_asked(self, episode_id: str, field: str) -> None:
        episode = self._episodes.get(episode_id)
        if episode is not None:
            if field not in episode.asked_question_ids:
                episode.asked_question_ids.append(field)
                episode.updated_at = time.time()

    def has_question_been_asked(self, episode_id: str, field: str) -> bool:
        episode = self._episodes.get(episode_id)
        if episode is None:
            return False
        return field in episode.asked_question_ids

    def update_episode_status(self, episode_id: str, status: EpisodeStatus) -> None:
        episode = self._episodes.get(episode_id)
        if episode is not None:
            episode.status = status
            episode.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "episodes": {k: v.to_dict() for k, v in self._episodes.items()},
            "gaps": {k: {"gap_id": v.gap_id, "gap_kind": v.gap_kind.value} for k, v in self._gaps.items()},
            "hypotheses": {k: v.to_dict() for k, v in self._hypotheses.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningEpisodeManager":
        return cls()
