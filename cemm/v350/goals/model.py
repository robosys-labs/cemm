"""Durable Phase-15 obligation, goal and policy contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..learning.model import PinnedRecord
from ..schema.model import SchemaLifecycleStatus, UseDecision, UseOperation, semantic_fingerprint
from ..storage.model import RecordKind


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class TargetSelectorMode(StrEnum):
    SOURCE = "source"
    SOURCE_PROPOSITION = "source_proposition"
    FRONTIER_TARGET = "frontier_target"
    SIGNIFICANCE_STAKEHOLDER = "significance_stakeholder"
    SIGNIFICANCE_AFFECTED = "significance_affected"
    APPLICATION_PORT = "application_port"
    FIXED = "fixed"


class GoalDisposition(StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class GoalTargetBinding:
    role_ref: str
    target_ref: str

    def __post_init__(self) -> None:
        _ref(self.role_ref, "goal target role_ref")
        _ref(self.target_ref, "goal target target_ref")


@dataclass(frozen=True, slots=True)
class TargetSelector:
    mode: TargetSelectorMode
    port_ref: str | None = None
    fixed_ref: str | None = None

    def __post_init__(self) -> None:
        if self.mode == TargetSelectorMode.APPLICATION_PORT and not self.port_ref:
            raise ValueError("application-port target selector requires port_ref")
        if self.mode == TargetSelectorMode.FIXED and not self.fixed_ref:
            raise ValueError("fixed target selector requires fixed_ref")


@dataclass(frozen=True, slots=True)
class ResponsePolicyRuleRecord:
    """Structural policy rule; goal class identity remains data."""

    rule_ref: str
    trigger_record_kinds: tuple[RecordKind, ...]
    trigger_schema_pins: tuple[tuple[str, int], ...]
    goal_schema_ref: str
    goal_schema_revision: int
    goal_operation: UseOperation
    target_selectors: tuple[TargetSelector, ...]
    priority: int = 0
    require_permission: bool = True
    require_epistemic_support: bool = False
    require_capability: bool = False
    block_on_open_frontier: bool = False
    conflict_key_refs: tuple[str, ...] = ()
    prohibition: bool = False
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    use_operation: UseOperation = UseOperation.RESPONSE_POLICY
    use_decision: UseDecision = UseDecision.DENY
    permission_ref: str = "public"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.rule_ref, "response policy rule_ref"),
            (self.goal_schema_ref, "goal schema_ref"),
            (self.permission_ref, "response policy permission_ref"),
        ):
            _ref(value, label)
        if self.revision < 1 or self.goal_schema_revision < 1:
            raise ValueError("response-policy revisions must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("response-policy supersedes_revision must target an older revision")
        if self.use_operation != UseOperation.RESPONSE_POLICY:
            raise ValueError("response-policy rule must use RESPONSE_POLICY axis")
        if not self.trigger_record_kinds:
            raise ValueError("response-policy rule requires structural trigger record kinds")
        if not self.target_selectors and not self.prohibition:
            raise ValueError("positive response-policy rule requires explicit target selectors")
        _unique(self.trigger_record_kinds, "response policy trigger kinds")
        _unique(self.trigger_schema_pins, "response policy trigger schema pins")
        _unique(self.conflict_key_refs, "response policy conflict keys")

    @property
    def executable(self) -> bool:
        return self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and self.use_decision == UseDecision.ALLOW


@dataclass(frozen=True, slots=True)
class SemanticObligationRecord:
    obligation_ref: str
    policy_rule_pin: PinnedRecord
    source_pins: tuple[PinnedRecord, ...]
    target_refs: tuple[str, ...]
    goal_schema_ref: str
    goal_schema_revision: int
    required_operation: UseOperation
    priority: int
    permission_ref: str
    sensitivity: str = "normal"
    prerequisite_frontier_refs: tuple[str, ...] = ()
    impact_refs: tuple[str, ...] = ()
    importance_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)
    target_bindings: tuple[GoalTargetBinding, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.obligation_ref, "obligation_ref"),
            (self.goal_schema_ref, "obligation goal_schema_ref"),
            (self.permission_ref, "obligation permission_ref"),
            (self.sensitivity, "obligation sensitivity"),
        ):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("obligations are immutable derivations; recomputation requires a new obligation_ref")
        if self.goal_schema_revision < 1:
            raise ValueError("obligation goal schema revision must be positive")
        if not self.source_pins:
            raise ValueError("obligation requires source lineage")
        if not self.target_refs:
            raise ValueError("positive obligation requires at least one semantic target")
        _unique(tuple(pin.key for pin in self.source_pins), "obligation source pins")
        for values, label in (
            (self.target_refs, "obligation targets"),
            (self.prerequisite_frontier_refs, "obligation frontiers"),
            (self.impact_refs, "obligation impacts"),
            (self.importance_refs, "obligation importance refs"),
            (self.reason_refs, "obligation reasons"),
            (self.proof_refs, "obligation proofs"),
            (tuple((item.role_ref, item.target_ref) for item in self.target_bindings), "obligation target bindings"),
        ):
            _unique(values, label)


@dataclass(frozen=True, slots=True)
class GoalCandidateRecord:
    goal_ref: str
    goal_schema_ref: str
    goal_schema_revision: int
    operation: UseOperation
    target_refs: tuple[str, ...]
    obligation_refs: tuple[str, ...]
    policy_rule_pins: tuple[PinnedRecord, ...]
    source_pins: tuple[PinnedRecord, ...]
    authorization_refs: tuple[str, ...]
    authorization_pins: tuple[PinnedRecord, ...] = ()
    prerequisite_frontier_refs: tuple[str, ...] = ()
    impact_refs: tuple[str, ...] = ()
    importance_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    authorized: bool = False
    denial_reasons: tuple[str, ...] = ()
    priority: int = 0
    utility_score: float = 0.0
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)
    target_bindings: tuple[GoalTargetBinding, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.goal_ref, "goal_ref"),
            (self.goal_schema_ref, "goal schema_ref"),
            (self.permission_ref, "goal permission_ref"),
            (self.sensitivity, "goal sensitivity"),
        ):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("goal candidates are immutable; rebuild after upstream change")
        if self.goal_schema_revision < 1:
            raise ValueError("goal schema revision must be positive")
        if not self.target_refs:
            raise ValueError("targetless goal candidate is forbidden")
        if not self.obligation_refs or not self.policy_rule_pins:
            raise ValueError("goal candidate requires obligation and policy lineage")
        if not isfinite(self.utility_score):
            raise ValueError("goal utility score must be finite")
        for values, label in (
            (self.target_refs, "goal targets"),
            (self.obligation_refs, "goal obligations"),
            (tuple(pin.key for pin in self.policy_rule_pins), "goal policy pins"),
            (tuple(pin.key for pin in self.source_pins), "goal source pins"),
            (self.authorization_refs, "goal authorization refs"),
            (tuple(pin.key for pin in self.authorization_pins), "goal authorization pins"),
            (self.prerequisite_frontier_refs, "goal frontier refs"),
            (self.impact_refs, "goal impact refs"),
            (self.importance_refs, "goal importance refs"),
            (self.risk_refs, "goal risk refs"),
            (self.reason_refs, "goal reasons"),
            (self.proof_refs, "goal proofs"),
            (self.denial_reasons, "goal denial reasons"),
            (tuple((item.role_ref, item.target_ref) for item in self.target_bindings), "goal target bindings"),
        ):
            _unique(values, label)


@dataclass(frozen=True, slots=True)
class GoalConflictRecord:
    conflict_ref: str
    competing_goal_refs: tuple[str, ...]
    target_refs: tuple[str, ...]
    conflict_key_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]
    unresolved_frontier_refs: tuple[str, ...] = ()
    revision: int = 1

    def __post_init__(self) -> None:
        _ref(self.conflict_ref, "goal conflict_ref")
        if self.revision != 1:
            raise ValueError("goal conflicts are immutable")
        if len(self.competing_goal_refs) < 2:
            raise ValueError("goal conflict requires at least two candidates")
        _unique(self.competing_goal_refs, "conflicting goals")
        _unique(self.target_refs, "conflict targets")
        _unique(self.conflict_key_refs, "conflict keys")
        _unique(self.reason_refs, "conflict reasons")
        _unique(self.unresolved_frontier_refs, "conflict frontiers")


@dataclass(frozen=True, slots=True)
class GoalDecisionRecord:
    decision_ref: str
    candidate_pins: tuple[PinnedRecord, ...]
    selected_goal_refs: tuple[str, ...]
    rejected_goal_refs: tuple[str, ...]
    deferred_goal_refs: tuple[str, ...]
    conflict_refs: tuple[str, ...]
    arbitration_policy_ref: str
    authorization_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]
    snapshot_revision: int
    snapshot_fingerprint: str
    boot_fingerprint: str
    overlay_fingerprint: str
    context_ref: str
    permission_ref: str
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_ref, "goal decision_ref"),
            (self.arbitration_policy_ref, "arbitration policy_ref"),
            (self.snapshot_fingerprint, "goal snapshot fingerprint"),
            (self.context_ref, "goal context_ref"),
            (self.permission_ref, "goal permission_ref"),
        ):
            _ref(value, label)
        # Empty boot fingerprint is valid for overlay-only/in-memory stores.
        if self.revision < 1 or self.snapshot_revision < 0:
            raise ValueError("goal decision revisions must be valid")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("goal decision supersedes_revision must target an older revision")
        _unique(tuple(pin.key for pin in self.candidate_pins), "goal decision candidate pins")
        selected = set(self.selected_goal_refs)
        rejected = set(self.rejected_goal_refs)
        deferred = set(self.deferred_goal_refs)
        if selected & rejected or selected & deferred or rejected & deferred:
            raise ValueError("goal decision dispositions must be disjoint")
        for values, label in (
            (self.selected_goal_refs, "selected goals"),
            (self.rejected_goal_refs, "rejected goals"),
            (self.deferred_goal_refs, "deferred goals"),
            (self.conflict_refs, "goal conflicts"),
            (self.authorization_refs, "goal decision authorizations"),
            (self.reason_refs, "goal decision reasons"),
        ):
            _unique(values, label)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("goal-decision", self, 64)


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
