"""StateTransmutationFrame — resolved state transition contract.

A StateTransmutationFrame is a runtime contract derived from UOL graph
state atoms, has_property edges, causes edges, and schema/operator deltas.
It is not a graph primitive — it is the authority unit for state changes.

State transmutation is not automatically durable. The persistence_policy
determines whether the change is ephemeral, session-level, a patch candidate,
a durable candidate, quarantined, or rejected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATE_FAMILIES = frozenset({
    "identity",
    "physical",
    "vital",
    "affective",
    "cognitive",
    "volitional",
    "capability",
    "resource",
    "geospatial",
    "possession",
    "social",
    "operational",
    "temporal",
    "contextual",
    "informational",
    "permission",
    "risk",
})

DIRECTIONS = frozenset({
    "set",
    "increase",
    "decrease",
    "clear",
    "decay",
    "strengthen",
    "weaken",
    "confirm",
    "contradict",
    "mark_stale",
    "mark_verified",
})

TRANSMUTATION_KINDS = frozenset({
    "observed",
    "reported",
    "inferred",
    "predicted",
    "desired",
    "commanded",
    "authorized",
    "committed",
    "rejected",
})

AUTHORITIES = frozenset({
    "self_authoritative",
    "user_asserted",
    "source_backed",
    "inferred",
    "policy_authorized",
    "tool_verified",
    "untrusted",
})

TRANSMUTATION_PERSISTENCE_POLICIES = frozenset({
    "ephemeral",
    "session_state",
    "graph_patch_candidate",
    "durable_candidate",
    "quarantine",
    "reject",
})

TEMPORAL_SCOPES = frozenset({
    "current_turn",
    "session",
    "persistent",
    "ephemeral",
})


@dataclass
class StateOccupancyFrame:
    """A current or reported state value on an entity, concept, or conversation."""

    target_ref: str
    # entity:user, entity:self, conversation:<id>, concept:<id>, claim:<id>

    state_family: str
    dimension: str

    current_value: Any | None = None
    confidence: float = 0.5
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    temporal_scope: str = "current_turn"
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateDeltaFrame:
    """A proposed change in state caused by an action, evidence update, or correction."""

    target_ref: str
    state_family: str
    dimension: str

    proposed_value: Any | None = None
    direction: str = "set"
    source_frame_id: str = ""
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateTransmutationFrame:
    """A resolved transition from prior state to next state.

    This is the authority unit for state changes. It is not automatically
    durable — the persistence_policy determines the write path.
    """

    transmutation_id: str
    source_frame_id: str

    target_ref: str
    # entity:user, entity:self, conversation:<id>, concept:<id>, claim:<id>

    state_family: str
    dimension: str

    prior_value: Any | None = None
    proposed_value: Any | None = None
    direction: str = "set"

    transmutation_kind: str = "observed"
    authority: str = "user_asserted"
    persistence_policy: str = "session_state"
    temporal_scope: str = "current_turn"

    freshness_required: bool = False
    reversible: bool = True

    authorization_status: str = "proposed"

    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.0
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.direction and self.direction not in DIRECTIONS:
            raise ValueError(f"unknown direction: {self.direction!r}")
        if self.transmutation_kind and self.transmutation_kind not in TRANSMUTATION_KINDS:
            raise ValueError(f"unknown transmutation kind: {self.transmutation_kind!r}")
        if self.authority and self.authority not in AUTHORITIES:
            raise ValueError(f"unknown authority: {self.authority!r}")
        if self.persistence_policy and self.persistence_policy not in TRANSMUTATION_PERSISTENCE_POLICIES:
            raise ValueError(f"unknown transmutation persistence policy: {self.persistence_policy!r}")
        if self.state_family and self.state_family not in STATE_FAMILIES:
            raise ValueError(f"unknown state family: {self.state_family!r}")

    @property
    def is_durable_candidate(self) -> bool:
        return self.persistence_policy in ("graph_patch_candidate", "durable_candidate")

    @property
    def is_rejected(self) -> bool:
        return self.persistence_policy == "reject"


@dataclass
class StateTransmutationPolicy:
    """Policy governing how a state transmutation is resolved."""

    requires_authority: bool = True
    requires_evidence: bool = False
    requires_confirmation: bool = False
    allows_ephemeral: bool = True
    allows_session_state: bool = True
    allows_patch_candidate: bool = False
    allows_durable_candidate: bool = False
    quarantine_on_conflict: bool = True


@dataclass
class SafetyTransmutationPolicy:
    """Policy for safety-relevant state transmutations.

    Safety-relevant transmutations are always quarantined — they are never
    persisted as state changes. They exist only to trigger safety effects.
    """

    requires_authority: bool = True
    requires_confirmation: bool = False
    persistence_policy: str = "quarantine"
    allows_ephemeral: bool = True
    allows_session_state: bool = False
    allows_patch_candidate: bool = False
    allows_durable_candidate: bool = False
    quarantine_on_conflict: bool = True
    must_report_safety: bool = True


@dataclass
class StateTransmutationResult:
    """Outcome of applying a state transmutation policy to a transmutation frame."""

    transmutation_id: str
    resolved_persistence: str
    applied: bool = False
    rejected_reason: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
