"""DEPRECATED: Replaced by cemm.kernel.learning.coordinator.LearningCoordinator.

This module is retained for legacy compatibility only. The v3.4 canonical
learning path uses LearningCoordinator for transaction lifecycle management.
Do not use for new code — redirect to LearningCoordinator.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from typing import Any

from ..types.learning_episode import EpisodeStatus, LearningEpisode, LearningObligation
from ..types.learning_evidence import EvidenceKind, EvidenceStance, LearningEvidenceEvent
from ..types.learning_hypothesis import HypothesisTargetKind, LearningHypothesis
from ..types.semantic_gap import SemanticGap


class LearningEpisodeManager:
    def __init__(self) -> None:
        self._episodes: dict[str, LearningEpisode] = {}
        self._gaps: dict[str, SemanticGap] = {}
        self._hypotheses: dict[str, LearningHypothesis] = {}
        self._evidence_events: dict[str, LearningEvidenceEvent] = {}
        self._obligations: dict[str, LearningObligation] = {}

    def create_episode(
        self,
        context_id: str,
        gaps: list[SemanticGap],
        target_scope: str = "session",
        recursion_depth: int = 0,
    ) -> LearningEpisode:
        # A gap has one owner. Reuse an active owner instead of duplicating the
        # acquisition thread on every user turn.
        requested = {gap.gap_id for gap in gaps}
        for episode in self.get_active_episodes(context_id):
            if requested & set(episode.target_gap_ids):
                for gap in gaps:
                    self._gaps[gap.gap_id] = gap
                    if gap.gap_id not in episode.target_gap_ids:
                        episode.target_gap_ids.append(gap.gap_id)
                episode.updated_at = time.time()
                return episode
        now = time.time()
        episode = LearningEpisode(
            episode_id=uuid.uuid4().hex[:16],
            context_id=context_id,
            target_scope=target_scope,
            target_gap_ids=[gap.gap_id for gap in gaps],
            recursion_depth=max(0, recursion_depth),
            status=EpisodeStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._episodes[episode.episode_id] = episode
        for gap in gaps:
            self._gaps[gap.gap_id] = gap
        return episode

    def get_episode(self, episode_id: str) -> LearningEpisode | None:
        return self._episodes.get(episode_id)

    def get_active_episodes(self, context_id: str) -> list[LearningEpisode]:
        now = time.time()
        active: list[LearningEpisode] = []
        for episode in self._episodes.values():
            if episode.context_id != context_id:
                continue
            if episode.expires_at is not None and episode.expires_at <= now:
                episode.status = EpisodeStatus.EXPIRED
                continue
            if episode.is_active:
                active.append(episode)
        active.sort(key=lambda item: (item.created_at, item.episode_id))
        return active

    def register_obligation(
        self,
        episode_id: str,
        obligation: LearningObligation,
    ) -> LearningObligation:
        episode = self._episodes.get(episode_id)
        if episode is None:
            raise KeyError(f"unknown learning episode: {episode_id}")
        if obligation.episode_id and obligation.episode_id != episode_id:
            raise ValueError("learning obligation belongs to another episode")
        normalized = LearningObligation(
            obligation_id=obligation.obligation_id,
            episode_id=episode_id,
            gap_ids=obligation.gap_ids,
            question_act=obligation.question_act,
            expected_answer_schema=dict(obligation.expected_answer_schema),
            resumes_obligation_ids=obligation.resumes_obligation_ids,
            utility=obligation.utility,
            created_turn_signal_id=obligation.created_turn_signal_id,
        )
        self._obligations[normalized.obligation_id] = normalized
        if normalized.obligation_id not in episode.pending_obligation_ids:
            episode.pending_obligation_ids.append(normalized.obligation_id)
        if normalized.obligation_id not in episode.asked_question_ids:
            episode.asked_question_ids.append(normalized.obligation_id)
        expected_field = self._expected_field(normalized)
        if expected_field:
            episode.unresolved_fields.add(expected_field)
        episode.status = EpisodeStatus.AWAITING_EVIDENCE
        episode.updated_at = time.time()
        return normalized

    def pending_obligations(self, context_id: str) -> list[tuple[LearningEpisode, LearningObligation]]:
        pending: list[tuple[LearningEpisode, LearningObligation]] = []
        for episode in self.get_active_episodes(context_id):
            for obligation_id in episode.pending_obligation_ids:
                obligation = self._obligations.get(obligation_id)
                if obligation is not None:
                    pending.append((episode, obligation))
        return pending

    def apply_answer_fields(
        self,
        episode_id: str,
        obligation_id: str,
        fields: list[tuple[str, Any]],
        *,
        evidence_signal_id: str = "",
    ) -> bool:
        episode = self._episodes.get(episode_id)
        obligation = self._obligations.get(obligation_id)
        if episode is None or obligation is None or not fields:
            return False
        accepted_fields: dict[str, Any] = {}
        for field_name, value in fields:
            name = str(field_name or "").strip()
            if not name or value in (None, "", [], {}):
                continue
            accepted_fields[name] = value
            episode.resolved_fields[name] = value
            episode.unresolved_fields.discard(name)
        if not accepted_fields:
            return False
        for hypothesis_id in episode.hypothesis_ids:
            hypothesis = self._hypotheses.get(hypothesis_id)
            if hypothesis is None:
                continue
            updated = hypothesis.with_satisfied_fields(accepted_fields)
            evidence_ids = tuple(dict.fromkeys([
                *updated.evidence_event_ids,
                *([evidence_signal_id] if evidence_signal_id else []),
            ]))
            self._hypotheses[hypothesis_id] = replace(
                updated,
                confidence=max(float(updated.confidence or 0.0), 0.35),
                evidence_event_ids=evidence_ids,
            )
        if evidence_signal_id and evidence_signal_id not in episode.evidence_event_ids:
            episode.evidence_event_ids.append(evidence_signal_id)
        episode.pending_obligation_ids = [
            item for item in episode.pending_obligation_ids if item != obligation_id
        ]
        episode.status = (
            EpisodeStatus.MINIMALLY_GROUNDED
            if not episode.unresolved_fields
            else EpisodeStatus.ACTIVE
        )
        episode.updated_at = time.time()
        return True

    def record_evidence(
        self,
        episode_id: str,
        hypothesis_id: str,
        evidence_kind: EvidenceKind,
        stance: EvidenceStance = EvidenceStance.SUPPORT,
        weight: float = 0.5,
        source_id: str = "",
    ) -> LearningEvidenceEvent:
        event = LearningEvidenceEvent(
            event_id=uuid.uuid4().hex[:16],
            target_hypothesis_id=hypothesis_id,
            evidence_kind=evidence_kind,
            stance=stance,
            weight=weight,
            source_id=source_id,
            observed_at=time.time(),
        )
        self._evidence_events[event.event_id] = event
        episode = self._episodes.get(episode_id)
        if episode is not None:
            episode.evidence_event_ids.append(event.event_id)
            episode.updated_at = time.time()
        return event

    def create_hypothesis(
        self,
        episode_id: str,
        target_kind: HypothesisTargetKind,
        proposed_artifact: dict[str, Any] | None = None,
    ) -> LearningHypothesis:
        hypothesis = LearningHypothesis(
            hypothesis_id=uuid.uuid4().hex[:16],
            target_kind=target_kind,
            proposed_artifact=proposed_artifact or {},
        )
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        episode = self._episodes.get(episode_id)
        if episode is not None:
            episode.hypothesis_ids.append(hypothesis.hypothesis_id)
            episode.updated_at = time.time()
        return hypothesis

    def mark_question_asked(self, episode_id: str, field: str) -> None:
        episode = self._episodes.get(episode_id)
        if episode is not None and field not in episode.asked_question_ids:
            episode.asked_question_ids.append(field)
            episode.updated_at = time.time()

    def has_question_been_asked(self, episode_id: str, field: str) -> bool:
        episode = self._episodes.get(episode_id)
        return bool(episode and field in episode.asked_question_ids)

    def update_episode_status(self, episode_id: str, status: EpisodeStatus) -> None:
        episode = self._episodes.get(episode_id)
        if episode is not None:
            episode.status = status
            episode.updated_at = time.time()

    def context_to_dict(self, context_id: str) -> dict[str, Any]:
        episodes = {
            key: value.to_dict()
            for key, value in self._episodes.items()
            if value.context_id == context_id
        }
        episode_ids = set(episodes)
        obligations = {
            key: value.to_dict()
            for key, value in self._obligations.items()
            if value.episode_id in episode_ids
        }
        hypothesis_ids = {
            hypothesis_id
            for episode in self._episodes.values()
            if episode.episode_id in episode_ids
            for hypothesis_id in episode.hypothesis_ids
        }
        hypotheses = {
            key: value.to_dict()
            for key, value in self._hypotheses.items()
            if key in hypothesis_ids
        }
        return {"episodes": episodes, "obligations": obligations, "hypotheses": hypotheses}

    def restore_context(self, context_id: str, data: dict[str, Any] | None) -> None:
        if not data:
            return
        for key, item in (data.get("episodes", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            episode = LearningEpisode.from_dict(item)
            if not episode.episode_id:
                episode.episode_id = str(key)
            episode.context_id = context_id
            self._episodes[episode.episode_id] = episode
        for key, item in (data.get("obligations", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            obligation = LearningObligation.from_dict(item)
            if not obligation.obligation_id:
                continue
            if obligation.episode_id in self._episodes:
                self._obligations[obligation.obligation_id] = obligation
        for key, item in (data.get("hypotheses", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            hypothesis = LearningHypothesis.from_dict(item)
            if hypothesis.hypothesis_id:
                self._hypotheses[hypothesis.hypothesis_id] = hypothesis

    def to_dict(self) -> dict[str, Any]:
        return {
            "episodes": {key: value.to_dict() for key, value in self._episodes.items()},
            "obligations": {key: value.to_dict() for key, value in self._obligations.items()},
            "gaps": {
                key: {
                    "gap_id": value.gap_id,
                    "gap_kind": value.gap_kind.value,
                    "surface_form": getattr(value, "surface_form", ""),
                }
                for key, value in self._gaps.items()
            },
            "hypotheses": {key: value.to_dict() for key, value in self._hypotheses.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningEpisodeManager":
        manager = cls()
        for key, item in (data.get("episodes", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            episode = LearningEpisode.from_dict(item)
            if not episode.episode_id:
                episode.episode_id = str(key)
            manager._episodes[episode.episode_id] = episode
        for key, item in (data.get("obligations", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            obligation = LearningObligation.from_dict(item)
            if obligation.obligation_id and obligation.episode_id in manager._episodes:
                manager._obligations[obligation.obligation_id] = obligation
        for key, item in (data.get("hypotheses", {}) or {}).items():
            if not isinstance(item, dict):
                continue
            hypothesis = LearningHypothesis.from_dict(item)
            if hypothesis.hypothesis_id:
                manager._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return manager

    @staticmethod
    def _expected_field(obligation: LearningObligation) -> str:
        answer_kind = str(obligation.expected_answer_schema.get("answer_kind", "") or "")
        return {
            "semantic_type": "semantic_type",
            "entity_reference": "entity_ref",
            "state_change": "effect_description",
            "dimension_name": "dimension",
            "value_description": "value",
            "direction": "direction",
            "time_description": "description",
            "spatial_relation": "description",
            "free_form": "description",
        }.get(answer_kind, answer_kind)
