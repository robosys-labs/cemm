"""Durable Phase-14 significance contracts.

The module deliberately keeps impact/importance semantics data-driven.  It adds
revisioned rule/proof/evidence/assessment records without moving domain meaning
into Python control flow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..learning.model import PinnedRecord
from ..schema.model import SchemaLifecycleStatus, UseDecision, UseOperation, semantic_fingerprint
from ..storage.model import RecordKind
from ..uol.model import ChangeOperation, ImpactAssessment, ImportanceAssessment, Reversibility, Valence


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ImpactRuleStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    INVALIDATED = "invalidated"


class ImportanceEvidencePolarity(StrEnum):
    SUPPORT = "support"
    OPPOSE = "oppose"


@dataclass(frozen=True, slots=True)
class ImpactRuleRecord:
    """Generic structural impact rule.

    `source_schema_pins` are exact semantic-schema identities, never names used
    as control-flow labels.  Stakeholder/affected bindings are resolved only from
    explicit application ports or fixed refs.
    """

    rule_ref: str
    source_record_kinds: tuple[RecordKind, ...]
    source_schema_pins: tuple[tuple[str, int], ...] = ()
    stakeholder_port_refs: tuple[str, ...] = ()
    affected_port_refs: tuple[str, ...] = ()
    fixed_stakeholder_refs: tuple[str, ...] = ()
    fixed_affected_refs: tuple[str, ...] = ()
    affected_facet_refs: tuple[str, ...] = ()
    direction: ChangeOperation = ChangeOperation.ACTIVATE
    valence: Valence = Valence.NEUTRAL
    reversibility: Reversibility = Reversibility.UNKNOWN
    magnitude_ref: str | None = None
    duration_ref: str | None = None
    confidence: float = 1.0
    priority: int = 0
    context_constraints: tuple[str, ...] = ()
    prerequisite_proof_kinds: tuple[RecordKind, ...] = ()
    use_operation: UseOperation = UseOperation.IMPACT
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    use_decision: UseDecision = UseDecision.DENY
    permission_ref: str = "public"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.rule_ref, "impact rule_ref")
        _ref(self.permission_ref, "impact permission_ref")
        if self.revision < 1:
            raise ValueError("impact rule revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("impact rule supersedes_revision must target an older revision")
        if not self.source_record_kinds:
            raise ValueError("impact rule requires at least one structural source record kind")
        if not (self.stakeholder_port_refs or self.fixed_stakeholder_refs):
            raise ValueError("impact rule requires an explicit stakeholder binding contract")
        if not (self.affected_port_refs or self.fixed_affected_refs):
            raise ValueError("impact rule requires an explicit affected binding contract")
        if self.use_operation != UseOperation.IMPACT:
            raise ValueError("impact rule use_operation must be IMPACT")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("impact rule confidence must be finite in [0,1]")
        _unique(self.source_record_kinds, "impact source record kinds")
        _unique(self.source_schema_pins, "impact source schema pins")
        _unique(self.stakeholder_port_refs, "impact stakeholder ports")
        _unique(self.affected_port_refs, "impact affected ports")
        _unique(self.fixed_stakeholder_refs, "impact fixed stakeholders")
        _unique(self.fixed_affected_refs, "impact fixed affected refs")
        _unique(self.affected_facet_refs, "impact facets")
        _unique(self.context_constraints, "impact context constraints")
        _unique(self.prerequisite_proof_kinds, "impact prerequisite proof kinds")

    @property
    def executable(self) -> bool:
        return self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and self.use_decision == UseDecision.ALLOW


@dataclass(frozen=True, slots=True)
class ImpactProofRecord:
    proof_ref: str
    source_pin: PinnedRecord
    rule_pin: PinnedRecord
    stakeholder_ref: str
    affected_ref: str
    context_ref: str
    permission_ref: str
    binding_source_pins: tuple[PinnedRecord, ...] = ()
    prerequisite_proof_pins: tuple[PinnedRecord, ...] = ()
    binding_evidence_refs: tuple[str, ...] = ()
    prerequisite_proof_refs: tuple[str, ...] = ()
    confidence: float = 1.0
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.proof_ref, "impact proof_ref"),
            (self.stakeholder_ref, "impact stakeholder_ref"),
            (self.affected_ref, "impact affected_ref"),
            (self.context_ref, "impact context_ref"),
            (self.permission_ref, "impact permission_ref"),
        ):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("impact proofs are immutable; recomputation requires a new proof_ref")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("impact proof confidence must be finite in [0,1]")
        _unique(tuple(pin.key for pin in self.binding_source_pins), "impact proof binding source pins")
        _unique(tuple(pin.key for pin in self.prerequisite_proof_pins), "impact prerequisite proof pins")
        _unique(self.binding_evidence_refs, "impact proof binding evidence")
        _unique(self.prerequisite_proof_refs, "impact prerequisite proofs")


@dataclass(frozen=True, slots=True)
class ImportanceEvidenceRecord:
    evidence_ref: str
    subject_ref: str
    stakeholder_ref: str
    channel_schema_ref: str
    channel_schema_revision: int
    source_pin: PinnedRecord
    polarity: ImportanceEvidencePolarity
    weight: float
    context_ref: str
    permission_ref: str
    reason_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    valid_time_ref: str | None = None
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.evidence_ref, "importance evidence_ref"),
            (self.subject_ref, "importance subject_ref"),
            (self.stakeholder_ref, "importance stakeholder_ref"),
            (self.channel_schema_ref, "importance channel_schema_ref"),
            (self.context_ref, "importance context_ref"),
            (self.permission_ref, "importance permission_ref"),
        ):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("importance evidence is immutable; corrections require a new evidence_ref")
        if self.channel_schema_revision < 1:
            raise ValueError("importance channel revision must be positive")
        if not isfinite(self.weight) or self.weight < 0.0:
            raise ValueError("importance evidence weight must be finite and non-negative")
        _unique(self.reason_refs, "importance evidence reasons")
        _unique(self.proof_refs, "importance evidence proofs")


@dataclass(frozen=True, slots=True)
class ImportancePolicyRecord:
    policy_ref: str
    # Exact channel revision pins prevent semantic drift underneath stable refs.
    channel_weights: tuple[tuple[str, int, float], ...]
    low_threshold: float
    high_threshold: float
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    use_operation: UseOperation = UseOperation.IMPACT
    use_decision: UseDecision = UseDecision.DENY
    permission_ref: str = "public"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.policy_ref, "importance policy_ref")
        _ref(self.permission_ref, "importance policy permission_ref")
        if self.revision < 1:
            raise ValueError("importance policy revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("importance policy supersedes_revision must target an older revision")
        if self.use_operation != UseOperation.IMPACT:
            raise ValueError("importance policy use_operation must be IMPACT")
        if not 0.0 <= self.low_threshold <= self.high_threshold <= 1.0:
            raise ValueError("importance thresholds must satisfy 0 <= low <= high <= 1")
        keys = []
        for schema_ref, revision, weight in self.channel_weights:
            _ref(schema_ref, "importance policy channel ref")
            if revision < 1:
                raise ValueError("importance policy channel revision must be positive")
            if not isfinite(weight) or weight < 0.0:
                raise ValueError("importance policy channel weight must be finite and non-negative")
            keys.append((schema_ref, revision))
        _unique(tuple(keys), "importance policy channel pins")

    @property
    def executable(self) -> bool:
        return self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and self.use_decision == UseDecision.ALLOW


@dataclass(frozen=True, slots=True)
class SignificanceAssessmentRecord:
    assessment_ref: str
    source_pin: PinnedRecord
    rule_pin: PinnedRecord
    proof_ref: str
    impact: ImpactAssessment
    importance: ImportanceAssessment | None
    importance_evidence_refs: tuple[str, ...]
    importance_policy_pin: PinnedRecord | None
    frontier_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.assessment_ref, "significance assessment_ref"),
            (self.proof_ref, "significance proof_ref"),
            (self.context_ref, "significance context_ref"),
            (self.permission_ref, "significance permission_ref"),
        ):
            _ref(value, label)
        if self.revision < 1:
            raise ValueError("significance assessment revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("significance supersedes_revision must target an older revision")
        if self.impact.context_ref != self.context_ref:
            raise ValueError("significance impact context must match wrapper context")
        if self.importance is not None:
            if self.importance.subject_ref not in {self.impact.source_event_or_state_ref, self.impact.affected_ref, self.assessment_ref}:
                raise ValueError("importance subject must be structurally related to the impact")
            if self.importance.stakeholder_ref != self.impact.stakeholder_ref:
                raise ValueError("importance stakeholder must match impact stakeholder")
            if self.importance.context_ref != self.context_ref:
                raise ValueError("importance context must match significance context")
        _unique(self.importance_evidence_refs, "significance importance evidence refs")
        _unique(self.frontier_refs, "significance frontier refs")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("significance-assessment", self, 64)


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
