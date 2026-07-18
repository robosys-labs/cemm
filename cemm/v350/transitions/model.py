"""Phase-11 declarative transition and capability-dependency contracts.

These records describe *how* an admitted event may produce state effects and
how projected state may change capability availability.  They deliberately do
not encode domain concepts in Python.  Event/state/action/type identities remain
revisioned data references.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..schema.model import SchemaLifecycleStatus
from ..uol.model import CapabilityDelta, CapabilityStatus, ChangeOperation, StateDelta


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ConditionOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    KNOWN = "known"
    UNKNOWN = "unknown"


class UnknownConditionPolicy(StrEnum):
    BLOCK = "block"
    PRESERVE_FRONTIER = "preserve_frontier"


@dataclass(frozen=True, slots=True)
class StateConditionSpec:
    condition_ref: str
    holder_port_ref: str
    dimension_ref: str
    dimension_revision: int
    operator: ConditionOperator
    value_ref: str | None = None
    value_revision: int | None = None
    unknown_policy: UnknownConditionPolicy = UnknownConditionPolicy.PRESERVE_FRONTIER

    def __post_init__(self) -> None:
        for value, label in (
            (self.condition_ref, "condition_ref"),
            (self.holder_port_ref, "holder_port_ref"),
            (self.dimension_ref, "dimension_ref"),
        ):
            _ref(value, label)
        if self.dimension_revision < 1:
            raise ValueError("condition dimension revision must be positive")
        needs_value = self.operator in {ConditionOperator.EQUALS, ConditionOperator.NOT_EQUALS}
        if needs_value != (self.value_ref is not None):
            raise ValueError("equals/not_equals require exactly one pinned state value")
        if self.value_ref is None and self.value_revision is not None:
            raise ValueError("condition value revision requires value_ref")
        if self.value_ref is not None:
            _ref(self.value_ref, "condition value_ref")
            if self.value_revision is None or self.value_revision < 1:
                raise ValueError("condition state value requires a positive revision")


@dataclass(frozen=True, slots=True)
class StateEffectSpec:
    effect_ref: str
    holder_port_ref: str
    dimension_ref: str
    dimension_revision: int
    operation: ChangeOperation
    from_value_ref: str | None = None
    from_value_revision: int | None = None
    to_value_ref: str | None = None
    to_value_revision: int | None = None
    magnitude_port_ref: str | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        for value, label in (
            (self.effect_ref, "effect_ref"),
            (self.holder_port_ref, "holder_port_ref"),
            (self.dimension_ref, "dimension_ref"),
        ):
            _ref(value, label)
        if self.dimension_revision < 1:
            raise ValueError("effect dimension revision must be positive")
        _probability(self.confidence, "effect confidence")
        for value_ref, revision, label in (
            (self.from_value_ref, self.from_value_revision, "from value"),
            (self.to_value_ref, self.to_value_revision, "to value"),
        ):
            if value_ref is None and revision is not None:
                raise ValueError(f"{label} revision requires a reference")
            if value_ref is not None:
                _ref(value_ref, f"effect {label} ref")
                if revision is None or revision < 1:
                    raise ValueError(f"effect {label} requires a positive revision")
        if self.magnitude_port_ref is not None:
            _ref(self.magnitude_port_ref, "magnitude_port_ref")
        if self.operation in {ChangeOperation.SET, ChangeOperation.ACTIVATE, ChangeOperation.RESTORE}:
            if self.to_value_ref is None:
                raise ValueError(f"{self.operation.value} effect requires to_value_ref")
        if self.operation in {ChangeOperation.INCREASE, ChangeOperation.DECREASE}:
            if self.to_value_ref is None:
                raise ValueError(
                    "Phase-11 scalar effects require an explicit target value; "
                    "a magnitude may be evidence but is not interpreted as arithmetic by the kernel"
                )
        if self.operation in {ChangeOperation.GAIN, ChangeOperation.LOSE, ChangeOperation.ENABLE, ChangeOperation.DISABLE}:
            raise ValueError(
                f"{self.operation.value} is not a state-dimension effect; use a dedicated dependency/lifecycle contract"
            )


@dataclass(frozen=True, slots=True)
class TransitionContractRecord:
    contract_ref: str
    trigger_schema_ref: str
    trigger_schema_revision: int
    state_conditions: tuple[StateConditionSpec, ...]
    state_effects: tuple[StateEffectSpec, ...]
    evidence_refs: tuple[str, ...]
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    revision: int = 1
    supersedes_revision: int | None = None
    context_policy: str = "same_as_event"
    permission_ref: str = "conversation"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.contract_ref, "contract_ref"),
            (self.trigger_schema_ref, "trigger_schema_ref"),
            (self.context_policy, "context_policy"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.trigger_schema_revision < 1 or self.revision < 1:
            raise ValueError("transition contract revisions must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("transition contract supersedes_revision must target an older revision")
        if self.context_policy != "same_as_event":
            raise ValueError("Phase 11 transition contracts must preserve the admitted event context")
        _unique(tuple(item.condition_ref for item in self.state_conditions), "transition condition refs")
        _unique(tuple(item.effect_ref for item in self.state_effects), "transition effect refs")
        _unique(self.evidence_refs, "transition contract evidence")
        if not self.state_effects:
            raise ValueError("transition contract requires at least one explicit effect")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.evidence_refs:
            raise ValueError("active transition contract requires reviewed evidence")


@dataclass(frozen=True, slots=True)
class CapabilityDependencyRecord:
    dependency_ref: str
    holder_type_refs: tuple[str, ...]
    action_schema_ref: str
    action_schema_revision: int
    state_conditions: tuple[StateConditionSpec, ...]
    status_if_satisfied: CapabilityStatus
    status_if_unsatisfied: CapabilityStatus
    status_if_unknown: CapabilityStatus
    evidence_refs: tuple[str, ...]
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    revision: int = 1
    supersedes_revision: int | None = None
    permission_ref: str = "conversation"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.dependency_ref, "dependency_ref"),
            (self.action_schema_ref, "action_schema_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.action_schema_revision < 1 or self.revision < 1:
            raise ValueError("capability dependency revisions must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("capability dependency supersedes_revision must target an older revision")
        _unique(self.holder_type_refs, "capability dependency holder types")
        _unique(tuple(item.condition_ref for item in self.state_conditions), "capability dependency conditions")
        _unique(self.evidence_refs, "capability dependency evidence")
        if not self.state_conditions:
            raise ValueError("capability dependency requires at least one state condition")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.evidence_refs:
            raise ValueError("active capability dependency requires reviewed evidence")


@dataclass(frozen=True, slots=True)
class TransitionProofRecord:
    proof_ref: str
    event_ref: str
    transition_contract_ref: str
    transition_contract_revision: int
    admission_pins: tuple[tuple[str, int], ...]
    condition_evidence_refs: tuple[str, ...]
    input_assignment_pins: tuple[tuple[str, int], ...]
    derived_state_delta_refs: tuple[str, ...]
    context_ref: str
    effective_time_ref: str
    confidence: float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.proof_ref, "proof_ref"),
            (self.event_ref, "event_ref"),
            (self.transition_contract_ref, "transition_contract_ref"),
            (self.context_ref, "context_ref"),
            (self.effective_time_ref, "effective_time_ref"),
        ):
            _ref(value, label)
        if self.transition_contract_revision < 1:
            raise ValueError("transition proof contract revision must be positive")
        _probability(self.confidence, "transition proof confidence")
        for values, label in (
            (self.admission_pins, "transition proof admissions"),
            (self.condition_evidence_refs, "transition proof condition evidence"),
            (self.input_assignment_pins, "transition proof assignments"),
            (self.derived_state_delta_refs, "transition proof deltas"),
            (self.evidence_refs, "transition proof evidence"),
        ):
            _unique(values, label)
        for ref, revision in self.admission_pins:
            _ref(ref, "transition proof admission ref")
            if revision < 1:
                raise ValueError("transition proof admission revision must be positive")
        for ref, revision in self.input_assignment_pins:
            _ref(ref, "transition proof assignment ref")
            if revision < 1:
                raise ValueError("transition proof assignment revision must be positive")
        if not self.admission_pins:
            raise ValueError("transition proof requires independent epistemic admission lineage")
        if not self.derived_state_delta_refs:
            raise ValueError("transition proof must identify at least one derived state delta")


    @property
    def admission_refs(self) -> tuple[str, ...]:
        return tuple(ref for ref, _revision in self.admission_pins)

    @property
    def input_assignment_refs(self) -> tuple[str, ...]:
        return tuple(ref for ref, _revision in self.input_assignment_pins)


@dataclass(frozen=True, slots=True)
class CompiledTransitionContract:
    contract: TransitionContractRecord
    trigger_port_refs: frozenset[str]


@dataclass(frozen=True, slots=True)
class TransitionFrontier:
    frontier_ref: str
    reason: str
    dependency_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TransitionPreview:
    event_ref: str
    contract_ref: str
    contract_revision: int
    state_deltas: tuple[StateDelta, ...]
    proof: TransitionProofRecord | None
    frontiers: tuple[TransitionFrontier, ...]
    blocked_reasons: tuple[str, ...]

    @property
    def authorized(self) -> bool:
        return bool(self.proof and self.state_deltas and not self.blocked_reasons)


@dataclass(frozen=True, slots=True)
class AssignmentMutation:
    assignment_ref: str
    record_revision: int
    expected_record_revision: int | None
    projected: Any


@dataclass(frozen=True, slots=True)
class StateTimelineProjection:
    holder_ref: str
    dimension_ref: str
    context_ref: str
    mutations: tuple[AssignmentMutation, ...]
    active_assignments: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class CapabilityProjection:
    delta: CapabilityDelta
    projected_instance: Any
    record_revision: int
    expected_record_revision: int | None


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _probability(value: float, label: str) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be within [0, 1]")
