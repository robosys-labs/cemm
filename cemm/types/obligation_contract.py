"""ObligationContract — authoritative decision contract for one turn.

The ObligationContract replaces broad instruction-kind routing as the source
of query/write/reaction behavior. It is compiled from selected
OperationalMeaningFrames, OperationalEffects, and StateTransmutationFrames.

Sub-contracts (QueryContract, WriteContract, ReactionContract, SafetyContract)
are attached to the ObligationContract and consumed by their respective engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


OBLIGATION_KINDS_3_2 = frozenset({
    "answer_user_profile",
    "answer_self_identity",
    "answer_self_capability",
    "answer_self_knowledge",
    "answer_concept_definition",
    "answer_world_fact",
    "store_profile",
    "store_teaching",
    "store_correction",
    "memory_command",
    "acknowledge_emotional_context",
    "apply_style_feedback",
    "apply_response_feedback",
    "social_reply",
    "exit",
    "ask_clarification",
    "abstain",
    "safety_refusal",
    "repair",
})

RESPONSE_MODES = frozenset({
    "answer",
    "confirm_write",
    "acknowledge",
    "clarify",
    "abstain",
    "refuse",
    "exit",
    "repair",
    "social",
})

QUERY_KINDS = frozenset({
    "none",
    "profile_dimension",
    "concept_definition",
    "self_identity",
    "self_capability",
    "self_knowledge",
    "relation_lookup",
    "fresh_world",
    "clarification",
})

WRITE_KINDS = frozenset({
    "none",
    "profile_upsert",
    "concept_upsert",
    "relation_upsert",
    "state_upsert",
    "correction_apply",
    "memory_command",
})

REACTION_KINDS = frozenset({
    "none",
    "style_adjust",
    "temperature_adjust",
    "repair_debt_update",
    "exit_signal",
    "safety_refusal",
})

COMMIT_POLICIES = frozenset({
    "no_commit",
    "validate_only",
    "commit_if_valid",
    "require_confirmation",
})

EVIDENCE_POLICIES = frozenset({
    "none",
    "required",
    "optional",
    "suppressed",
})

AMBIGUITY_POLICIES = frozenset({
    "abstain",
    "clarify",
    "best_effort",
})


@dataclass
class QueryContract:
    """Strict query contract — consumed by SemanticQueryEngine."""

    query_kind: str
    target_scope: str

    subject_entity_id: str = ""
    subject_concept_id: str = ""
    relation_key: str = ""
    relation_family: str = ""
    dimension: str = ""

    object_entity_id: str = ""
    object_concept_id: str = ""

    projection_policy: str = "object"
    target_required: bool = True
    ambiguity_policy: str = "abstain"
    evidence_policy: str = "required"
    freshness_required: bool = False
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.query_kind and self.query_kind not in QUERY_KINDS:
            raise ValueError(f"unknown query kind: {self.query_kind!r}")
        if self.ambiguity_policy and self.ambiguity_policy not in AMBIGUITY_POLICIES:
            raise ValueError(f"unknown ambiguity policy: {self.ambiguity_policy!r}")
        if self.evidence_policy and self.evidence_policy not in EVIDENCE_POLICIES:
            raise ValueError(f"unknown evidence policy: {self.evidence_policy!r}")


@dataclass
class WriteContract:
    """Write contract — only from writable operational meaning frames."""

    write_kind: str
    target: str
    persistence_policy: str
    allowed_patch_targets: list[str] = field(default_factory=list)
    required_features: list[str] = field(default_factory=list)
    required_evidence_refs: list[str] = field(default_factory=list)
    permission_scope: str = ""
    commit_policy: str = "validate_only"
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.write_kind and self.write_kind not in WRITE_KINDS:
            raise ValueError(f"unknown write kind: {self.write_kind!r}")
        if self.commit_policy and self.commit_policy not in COMMIT_POLICIES:
            raise ValueError(f"unknown commit policy: {self.commit_policy!r}")

    @property
    def is_writable(self) -> bool:
        return self.write_kind != "none" and self.commit_policy != "no_commit"


@dataclass
class ReactionContract:
    """Style/temperature/session reaction contract from feedback and affect."""

    reaction_kind: str
    target: str
    style_delta: dict[str, float] = field(default_factory=dict)
    temperature_delta: dict[str, float] = field(default_factory=dict)
    repair_debt_delta: float = 0.0
    persistence_policy: str = "session_state"
    source_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.reaction_kind and self.reaction_kind not in REACTION_KINDS:
            raise ValueError(f"unknown reaction kind: {self.reaction_kind!r}")


@dataclass
class SafetyContract:
    """Safety contract — preempts competing obligations."""

    safety_kind: str = "none"
    blocked_obligation_ids: list[str] = field(default_factory=list)
    refusal_reason: str = ""
    risk_level: float = 0.0
    requires_human_confirmation: bool = False
    source_refs: list[str] = field(default_factory=list)


@dataclass
class ObligationContract:
    """The authoritative decision contract for one turn.

    Replaces broad instruction-kind routing. Compiled from selected
    OperationalMeaningFrames, OperationalEffects, and StateTransmutationFrames.
    """

    contract_id: str
    primary_meaning_frame_id: str
    child_meaning_frame_ids: list[str] = field(default_factory=list)

    obligation_kind: str = "abstain"
    response_mode: str = "abstain"

    query_policy: str = "none"
    write_policy: str = "none"
    reaction_policy: str = "none"
    safety_policy: str = "none"

    query_contract: QueryContract | None = None
    write_contract: WriteContract | None = None
    reaction_contract: ReactionContract | None = None
    safety_contract: SafetyContract | None = None

    required_state_transmutations: list[str] = field(default_factory=list)
    allowed_state_transmutations: list[str] = field(default_factory=list)

    blocked_by: list[str] = field(default_factory=list)
    confidence: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.obligation_kind and self.obligation_kind not in OBLIGATION_KINDS_3_2:
            raise ValueError(f"unknown obligation kind: {self.obligation_kind!r}")
        if self.response_mode and self.response_mode not in RESPONSE_MODES:
            raise ValueError(f"unknown response mode: {self.response_mode!r}")

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked_by)

    @property
    def has_write(self) -> bool:
        return self.write_contract is not None and self.write_contract.is_writable

    @property
    def has_query(self) -> bool:
        return self.query_contract is not None

    @property
    def has_reaction(self) -> bool:
        return self.reaction_contract is not None and self.reaction_contract.reaction_kind != "none"

    @property
    def has_safety_preemption(self) -> bool:
        return self.safety_contract is not None and self.safety_contract.safety_kind != "none"
