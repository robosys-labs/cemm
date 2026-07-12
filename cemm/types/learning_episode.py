from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EpisodeStatus(str, Enum):
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
    """Persistent ownership container for one or more dependent semantic gaps."""

    episode_id: str
    context_id: str = ""
    target_scope: str = "session"
    target_gap_ids: list[str] = field(default_factory=list)
    hypothesis_ids: list[str] = field(default_factory=list)
    evidence_event_ids: list[str] = field(default_factory=list)
    asked_question_ids: list[str] = field(default_factory=list)
    pending_obligation_ids: list[str] = field(default_factory=list)
    resolved_fields: dict[str, Any] = field(default_factory=dict)
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

    def has_asked(self, question_id: str) -> bool:
        return question_id in self.asked_question_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "context_id": self.context_id,
            "target_scope": self.target_scope,
            "target_gap_ids": list(self.target_gap_ids),
            "hypothesis_ids": list(self.hypothesis_ids),
            "evidence_event_ids": list(self.evidence_event_ids),
            "asked_question_ids": list(self.asked_question_ids),
            "pending_obligation_ids": list(self.pending_obligation_ids),
            "resolved_fields": dict(self.resolved_fields),
            "unresolved_fields": sorted(self.unresolved_fields),
            "provisional_binding_ids": list(self.provisional_binding_ids),
            "recursion_depth": self.recursion_depth,
            "status": self.status.value,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningEpisode":
        status_value = str(data.get("status", EpisodeStatus.ACTIVE.value) or EpisodeStatus.ACTIVE.value)
        try:
            status = EpisodeStatus(status_value)
        except ValueError:
            status = EpisodeStatus.ACTIVE
        return cls(
            episode_id=str(data.get("episode_id", "") or ""),
            context_id=str(data.get("context_id", "") or ""),
            target_scope=str(data.get("target_scope", "session") or "session"),
            target_gap_ids=[str(v) for v in data.get("target_gap_ids", []) or [] if v],
            hypothesis_ids=[str(v) for v in data.get("hypothesis_ids", []) or [] if v],
            evidence_event_ids=[str(v) for v in data.get("evidence_event_ids", []) or [] if v],
            asked_question_ids=[str(v) for v in data.get("asked_question_ids", []) or [] if v],
            pending_obligation_ids=[str(v) for v in data.get("pending_obligation_ids", []) or [] if v],
            resolved_fields=dict(data.get("resolved_fields", {}) or {}),
            unresolved_fields={str(v) for v in data.get("unresolved_fields", []) or [] if v},
            provisional_binding_ids=[str(v) for v in data.get("provisional_binding_ids", []) or [] if v],
            recursion_depth=max(0, int(data.get("recursion_depth", 0) or 0)),
            status=status,
            expires_at=data.get("expires_at"),
            created_at=float(data.get("created_at", 0.0) or 0.0),
            updated_at=float(data.get("updated_at", 0.0) or 0.0),
        )


class QuestionActKind(str, Enum):
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
    obligation_id: str
    episode_id: str
    gap_ids: tuple[str, ...]
    question_act: QuestionActKind
    expected_answer_schema: dict[str, Any] = field(default_factory=dict)
    resumes_obligation_ids: tuple[str, ...] = ()
    utility: float = 0.0
    created_turn_signal_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "episode_id": self.episode_id,
            "gap_ids": list(self.gap_ids),
            "question_act": self.question_act.value,
            "expected_answer_schema": dict(self.expected_answer_schema),
            "resumes_obligation_ids": list(self.resumes_obligation_ids),
            "utility": self.utility,
            "created_turn_signal_id": self.created_turn_signal_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningObligation":
        act_value = str(data.get("question_act", QuestionActKind.ASK_SEMANTIC_KIND.value) or QuestionActKind.ASK_SEMANTIC_KIND.value)
        try:
            act = QuestionActKind(act_value)
        except ValueError:
            act = QuestionActKind.ASK_SEMANTIC_KIND
        return cls(
            obligation_id=str(data.get("obligation_id", "") or ""),
            episode_id=str(data.get("episode_id", "") or ""),
            gap_ids=tuple(str(v) for v in data.get("gap_ids", []) or [] if v),
            question_act=act,
            expected_answer_schema=dict(data.get("expected_answer_schema", {}) or {}),
            resumes_obligation_ids=tuple(str(v) for v in data.get("resumes_obligation_ids", []) or [] if v),
            utility=float(data.get("utility", 0.0) or 0.0),
            created_turn_signal_id=str(data.get("created_turn_signal_id", "") or ""),
        )
