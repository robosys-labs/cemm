"""OperationalMeaningFrame — planner-facing authority unit compiled from UOL graph.

An OperationalMeaningFrame is a runtime view compiled from UOL graph structure.
It is not a new UOL atom kind. It is the decision unit that feeds obligation
contract compilation, state transmutation, and causal/effect routing.

The frame_type determines which downstream contracts (query, write, reaction,
safety) are built. This replaces broad instruction-kind routing such as
``assertion -> store_patch`` with explicit, per-meaning contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


OPERATIONAL_MEANING_FRAME_TYPES = frozenset({
    "social_act",
    "phatic_act",
    "session_exit",
    "profile_assertion",
    "concept_definition_teaching",
    "concept_definition_query",
    "world_fact_claim",
    "response_feedback",
    "style_feedback",
    "correction",
    "user_state_report",
    "safety_candidate",
    "command",
    "memory_command",
    "self_identity_query",
    "self_capability_query",
    "self_knowledge_query",
    "user_profile_query",
    "clarification_request",
})

TARGET_SCOPES = frozenset({
    "user_profile",
    "self_model",
    "previous_response",
    "conversation_state",
    "concept_lattice",
    "external_world",
    "safety",
    "ephemeral_social",
})

PERSISTENCE_POLICIES = frozenset({
    "never_store",
    "ephemeral_trace",
    "session_state",
    "patch_candidate",
    "durable_candidate",
    "requires_confirmation",
    "quarantine",
})

QUERY_POLICIES = frozenset({
    "none",
    "relation_lookup",
    "profile_dimension_lookup",
    "concept_definition_lookup",
    "fresh_world_lookup",
    "clarification_required",
})

WRITABLE_FRAME_TYPES = frozenset({
    "profile_assertion",
    "concept_definition_teaching",
    "world_fact_claim",
    "correction",
    "memory_command",
    "command",
})

WRITABLE_PERSISTENCE_POLICIES = frozenset({
    "patch_candidate",
    "durable_candidate",
    "requires_confirmation",
})


def is_writable_frame(frame: OperationalMeaningFrame) -> bool:
    """Return True if the frame may produce durable patch candidates."""
    if frame.frame_type not in WRITABLE_FRAME_TYPES:
        return False
    return frame.persistence_policy in WRITABLE_PERSISTENCE_POLICIES


@dataclass
class OperationalEffect:
    """A causal/effect prediction derived from meaning frames and transmutations."""

    effect_id: str
    source_frame_id: str
    effect_type: str
    # activate_query, activate_write, increase_repair_debt,
    # decrease_response_detail, increase_directness, set_exit_requested,
    # activate_safety_refusal, require_fresh_source, quarantine_write,
    # mark_previous_response_failed

    target: str
    delta: dict[str, Any] = field(default_factory=dict)
    strength: float = 0.5
    reversible: bool = True
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class OperationalMeaningFrame:
    """Runtime view compiled from UOL graph structure.

    This is the planner-facing authority unit. It is not a UOL atom kind.
    It determines what downstream contracts (query, write, reaction, safety)
    are built for this turn.
    """

    frame_id: str
    graph_id: str
    group_id: str

    frame_type: str
    target_scope: str

    subject_atom_id: str = ""
    predicate_atom_id: str = ""
    object_atom_id: str = ""

    relation_key: str = ""
    relation_family: str = ""
    dimension: str = ""

    persistence_policy: str = "never_store"
    query_policy: str = "none"

    state_transmutations: list[Any] = field(default_factory=list)
    # list[StateTransmutationFrame] — uses Any to avoid circular import

    effects: list[OperationalEffect] = field(default_factory=list)

    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    source_atom_ids: list[str] = field(default_factory=list)
    source_edge_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.frame_type and self.frame_type not in OPERATIONAL_MEANING_FRAME_TYPES:
            raise ValueError(f"unknown operational meaning frame type: {self.frame_type!r}")
        if self.target_scope and self.target_scope not in TARGET_SCOPES:
            raise ValueError(f"unknown target scope: {self.target_scope!r}")
        if self.persistence_policy and self.persistence_policy not in PERSISTENCE_POLICIES:
            raise ValueError(f"unknown persistence policy: {self.persistence_policy!r}")
        if self.query_policy and self.query_policy not in QUERY_POLICIES:
            raise ValueError(f"unknown query policy: {self.query_policy!r}")

    @property
    def is_writable(self) -> bool:
        return is_writable_frame(self)

    @property
    def is_query(self) -> bool:
        return self.query_policy != "none"


@dataclass
class MeaningArbitrationResult:
    """Result of arbitrating multiple meaning frames without collapsing too early."""

    selected_frame_ids: list[str] = field(default_factory=list)
    suppressed_frame_ids: list[str] = field(default_factory=list)
    child_frame_ids: list[str] = field(default_factory=list)
    arbitration_reason: str = ""
    confidence: float = 0.5
    diagnostics: dict[str, Any] = field(default_factory=dict)
