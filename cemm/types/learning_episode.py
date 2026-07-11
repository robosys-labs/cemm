from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class EpisodeStatus(str, Enum):
    """Status lifecycle of a learning episode."""
    ACTIVE = "active"
    MINIMALLY_GROUNDED = "minimally_grounded"
    PROVISIONALLY_ACTIVE = "provisionally_active"
    AWAITING_EVIDENCE = "awaiting_evidence"
    CONSOLIDATED = "consolidated"
    ABANDONED = "abandoned"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(slots=True)
class LearningEpisode:
    """A persistent learning episode that recursively acquires missing semantics.

    Only one episode owns a gap. One episode may cover several dependent gaps
    when one answer can resolve them together.
    """
    episode_id: str
    context_id: str = ""
    target_scope: str = "session"
    target_gap_ids: list[str] = field(default_factory=list)
    hypothesis_ids: list[str] = field(default_factory=list)
    evidence_event_ids: list[str] = field(default_factory=list)
    asked_question_ids: list[str] = field(default_factory=list)
    unresolved_fields: set[str] = field(default_factory=set)
    provisional_binding_ids: list[str] = field(default_factory=list)
    recursion_depth: int = 0
    status: EpisodeStatus = EpisodeStatus.ACTIVE
    expires_at: float | None = None
    created_at: float = 0.0
    updated_at: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.status in {
            EpisodeStatus.ACTIVE,
            EpisodeStatus.MINIMALLY_GROUNDED,
            EpisodeStatus.PROVISIONALLY_ACTIVE,
            EpisodeStatus.AWAITING_EVIDENCE,
        }

    @property
    def is_resolved(self) -> bool:
        return self.status in {
            EpisodeStatus.CONSOLIDATED,
            EpisodeStatus.MINIMALLY_GROUNDED,
            EpisodeStatus.PROVISIONALLY_ACTIVE,
        }

    @property
    def is_terminated(self) -> bool:
        return self.status in {
            EpisodeStatus.CONSOLIDATED,
            EpisodeStatus.ABANDONED,
            EpisodeStatus.QUARANTINED,
            EpisodeStatus.REJECTED,
            EpisodeStatus.EXPIRED,
        }

    def has_asked(self, field: str) -> bool:
        return field in self.asked_question_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "context_id": self.context_id,
            "target_scope": self.target_scope,
            "target_gap_ids": list(self.target_gap_ids),
            "hypothesis_ids": list(self.hypothesis_ids),
            "evidence_event_ids": list(self.evidence_event_ids),
            "asked_question_ids": list(self.asked_question_ids),
            "unresolved_fields": list(self.unresolved_fields),
            "provisional_binding_ids": list(self.provisional_binding_ids),
            "recursion_depth": self.recursion_depth,
            "status": self.status.value,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class QuestionActKind(str, Enum):
    """Semantic question act kinds for learning clarification."""
    ASK_SEMANTIC_KIND = "ask_semantic_kind"
    ASK_REFERENT_IDENTITY = "ask_referent_identity"
    ASK_OPERATOR_ACTOR = "ask_operator_actor"
    ASK_OPERATOR_TARGET = "ask_operator_target"
    ASK_OPERATOR_EFFECT = "ask_operator_effect"
    ASK_RELATION_ORIENTATION = "ask_relation_orientation"
    ASK_STATE_DIMENSION = "ask_state_dimension"
    ASK_STATE_VALUE_OR_POLARITY = "ask_state_value_or_polarity"
    ASK_TEMPORAL_SCOPE = "ask_temporal_scope"
    ASK_GEOSPATIAL_RELATION = "ask_geospatial_relation"
    ASK_GRAMMATICAL_FUNCTION = "ask_grammatical_function"
    ASK_EXAMPLE = "ask_example"
    ASK_COUNTEREXAMPLE = "ask_counterexample"
    ASK_TRANSLATION_EQUIVALENT = "ask_translation_equivalent"
    ASK_CONFIRM_HYPOTHESIS = "ask_confirm_hypothesis"


@dataclass(frozen=True, slots=True)
class LearningObligation:
    """An obligation to ask a learning question for a blocking gap."""
    obligation_id: str
    episode_id: str
    gap_ids: tuple[str, ...]
    question_act: QuestionActKind
    expected_answer_schema: dict[str, Any] = field(default_factory=dict)
    resumes_obligation_ids: tuple[str, ...] = ()
    utility: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "episode_id": self.episode_id,
            "gap_ids": list(self.gap_ids),
            "question_act": self.question_act.value,
            "resumes_obligation_ids": list(self.resumes_obligation_ids),
            "utility": self.utility,
        }
