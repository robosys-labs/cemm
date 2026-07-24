"""CEMM v3.5 Phase-16 operation-boundary durable contracts.

The operation layer separates semantic goal selection, execution authorization,
external side effects, observations, and reconciliation.  External effects are
never represented as rollback-safe GraphPatch mutations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class OperationAuthorizationDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    DEFER = "defer"


class OperationJournalStatus(StrEnum):
    PLANNED = "planned"
    PREAUTHORIZED = "preauthorized"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    OBSERVED_SUCCESS = "observed_success"
    OBSERVED_FAILURE = "observed_failure"
    OBSERVED_PARTIAL = "observed_partial"
    OUTCOME_UNKNOWN = "outcome_unknown"
    RECONCILED = "reconciled"
    CANCELLED_BEFORE_SUBMIT = "cancelled_before_submit"


class OperationResultStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class IdempotencyMode(StrEnum):
    NONE = "none"
    CLIENT_KEY = "client_key"
    ADAPTER_KEY = "adapter_key"
    EXTERNAL_CORRELATION = "external_correlation"


@dataclass(frozen=True, slots=True)
class OperationAdapterContractRecord:
    contract_ref: str
    action_schema_pins: tuple[tuple[str, int], ...]
    adapter_ref: str
    adapter_revision: int
    supported_port_refs: tuple[str, ...]
    result_schema_pins: tuple[tuple[str, int], ...] = ()
    idempotency_mode: IdempotencyMode = IdempotencyMode.NONE
    retry_safe_on_unknown: bool = False
    cancellation_supported: bool = False
    timeout_semantics: str = "outcome_unknown"
    permission_ref: str = "internal"
    revision: int = 1
    supersedes_revision: int | None = None
    active: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.contract_ref, "adapter contract_ref"), (self.adapter_ref, "adapter_ref"),
                             (self.timeout_semantics, "timeout semantics"), (self.permission_ref, "permission_ref")):
            _ref(value, label)
        if min(self.adapter_revision, self.revision) < 1:
            raise ValueError("adapter contract revisions must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("adapter supersedes_revision must target an older revision")
        if not self.action_schema_pins:
            raise ValueError("adapter contract requires exact compatible action schema pins")
        _unique(self.action_schema_pins, "adapter action schema pins")
        _unique(self.supported_port_refs, "adapter supported ports")
        _unique(self.result_schema_pins, "adapter result schema pins")
        if self.retry_safe_on_unknown and self.idempotency_mode == IdempotencyMode.NONE:
            raise ValueError("unknown-outcome retries require an idempotency contract")


@dataclass(frozen=True, slots=True)
class OperationPlanRecord:
    plan_ref: str
    goal_decision_pin: PinnedRecord
    goal_candidate_pin: PinnedRecord
    action_application_pin: PinnedRecord
    action_schema_pin: PinnedRecord
    controlling_holder_ref: str
    bound_port_refs: tuple[str, ...]
    capability_pin: PinnedRecord
    adapter_contract_pin: PinnedRecord
    authorization_input_pins: tuple[PinnedRecord, ...]
    predicted_effect_pins: tuple[PinnedRecord, ...] = ()
    idempotency_key: str | None = None
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    snapshot_revision: int = 0
    snapshot_fingerprint: str = ""
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.plan_ref, "operation plan_ref"), (self.controlling_holder_ref, "controlling holder"),
                             (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
                             (self.sensitivity, "sensitivity"), (self.snapshot_fingerprint, "snapshot fingerprint")):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("operation plans are immutable; replanning requires a new plan_ref")
        if self.snapshot_revision < 0:
            raise ValueError("operation plan snapshot revision cannot be negative")
        _unique(self.bound_port_refs, "operation bound ports")
        _unique(tuple(pin.key for pin in self.authorization_input_pins), "operation authorization input pins")
        _unique(tuple(pin.key for pin in self.predicted_effect_pins), "operation predicted effect pins")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("operation-plan", self, 64)




@dataclass(frozen=True, slots=True)
class OperationGateAssessmentRecord:
    assessment_ref: str
    plan_pin: PinnedRecord
    gate_ref: str
    passed: bool
    evaluator_ref: str
    evaluator_revision: str
    checked_pins: tuple[PinnedRecord, ...]
    authorization_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    snapshot_revision: int = 0
    snapshot_fingerprint: str = ""
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.assessment_ref, "gate assessment_ref"), (self.gate_ref, "gate_ref"),
                             (self.evaluator_ref, "gate evaluator_ref"), (self.evaluator_revision, "gate evaluator_revision"),
                             (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
                             (self.snapshot_fingerprint, "snapshot fingerprint")):
            _ref(value, label)
        if self.revision != 1 or self.snapshot_revision < 0:
            raise ValueError("gate assessments are immutable and snapshot revision must be valid")
        _unique(tuple(pin.key for pin in self.checked_pins), "gate checked pins")
        _unique(self.authorization_refs, "gate authorization refs")
        _unique(self.proof_refs, "gate proof refs")
        _unique(self.reason_refs, "gate reason refs")
        if self.passed and not self.checked_pins:
            raise ValueError("passing hard-gate assessment requires exact checked substrate")

@dataclass(frozen=True, slots=True)
class OperationAuthorizationRecord:
    authorization_ref: str
    plan_pin: PinnedRecord
    decision: OperationAuthorizationDecision
    checked_pins: tuple[PinnedRecord, ...]
    gate_assessment_pins: tuple[PinnedRecord, ...]
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    authorization_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    snapshot_revision: int = 0
    snapshot_fingerprint: str = ""
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.authorization_ref, "operation authorization_ref"), (self.context_ref, "context_ref"),
                             (self.permission_ref, "permission_ref"), (self.snapshot_fingerprint, "snapshot fingerprint")):
            _ref(value, label)
        if self.revision != 1 or self.snapshot_revision < 0:
            raise ValueError("operation authorization is immutable and snapshot revision must be valid")
        _unique(tuple(pin.key for pin in self.checked_pins), "operation checked pins")
        _unique(tuple(pin.key for pin in self.gate_assessment_pins), "operation gate assessment pins")
        _unique(self.passed_gates, "operation passed gates")
        _unique(self.failed_gates, "operation failed gates")
        _unique(self.authorization_refs, "operation authorization refs")
        if self.decision == OperationAuthorizationDecision.ALLOW and self.failed_gates:
            raise ValueError("allowed operation cannot contain failed gates")
        if self.decision != OperationAuthorizationDecision.ALLOW and not self.failed_gates:
            raise ValueError("non-allowed operation authorization requires explicit failed/deferred gates")


@dataclass(frozen=True, slots=True)
class OperationJournalRecord:
    journal_ref: str
    plan_pin: PinnedRecord
    authorization_pin: PinnedRecord
    status: OperationJournalStatus
    idempotency_key: str | None
    adapter_ref: str
    adapter_revision: int
    submission_attempt: int = 0
    request_evidence_refs: tuple[str, ...] = ()
    response_evidence_refs: tuple[str, ...] = ()
    external_correlation_refs: tuple[str, ...] = ()
    prior_journal_pin: PinnedRecord | None = None
    submitted_at: str | None = None
    observed_at: str | None = None
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.journal_ref, "operation journal_ref"), (self.adapter_ref, "adapter_ref"),
                             (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
                             (self.sensitivity, "sensitivity")):
            _ref(value, label)
        if min(self.adapter_revision, self.revision) < 1 or self.submission_attempt < 0:
            raise ValueError("operation journal revisions/attempts must be valid")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("journal supersedes_revision must target an older revision")
        if self.revision > 1 and self.prior_journal_pin is None:
            raise ValueError("journal lifecycle revisions require exact prior_journal_pin")
        _unique(self.request_evidence_refs, "journal request evidence")
        _unique(self.response_evidence_refs, "journal response evidence")
        _unique(self.external_correlation_refs, "journal external correlations")


@dataclass(frozen=True, slots=True)
class OperationResultRecord:
    result_ref: str
    journal_pin: PinnedRecord
    status: OperationResultStatus
    transport_acknowledged: bool
    domain_result_refs: tuple[str, ...]
    observed_effect_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    retryable: bool = False
    uncertainty_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.result_ref, "operation result_ref"), (self.context_ref, "context_ref"),
                             (self.permission_ref, "permission_ref")):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("operation results are immutable observations")
        for values, label in ((self.domain_result_refs, "domain result refs"), (self.observed_effect_refs, "observed effect refs"),
                              (self.evidence_refs, "operation result evidence"), (self.proof_refs, "operation result proofs"),
                              (self.uncertainty_refs, "operation result uncertainty")):
            _unique(values, label)
        if self.status in {OperationResultStatus.SUCCESS, OperationResultStatus.FAILURE, OperationResultStatus.PARTIAL} and not (self.evidence_refs or self.proof_refs):
            raise ValueError("terminal operation outcome requires observed evidence/proof; transport status alone is insufficient")


@dataclass(frozen=True, slots=True)
class OperationReconciliationRecord:
    reconciliation_ref: str
    plan_pin: PinnedRecord
    result_pin: PinnedRecord
    observed_journal_pin: PinnedRecord
    predicted_effect_pins: tuple[PinnedRecord, ...]
    observed_pins: tuple[PinnedRecord, ...]
    generated_evidence_refs: tuple[str, ...]
    replay_required_refs: tuple[str, ...]
    contradiction_refs: tuple[str, ...]
    invalidated_goal_decision_refs: tuple[str, ...]
    frontier_refs: tuple[str, ...]
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.reconciliation_ref, "operation reconciliation_ref"), (self.context_ref, "context_ref"),
                             (self.permission_ref, "permission_ref")):
            _ref(value, label)
        if self.revision != 1:
            raise ValueError("operation reconciliation records are immutable")
        _unique(tuple(pin.key for pin in self.predicted_effect_pins), "predicted effect pins")
        _unique(tuple(pin.key for pin in self.observed_pins), "observed pins")
        for values, label in ((self.generated_evidence_refs, "reconciliation evidence"), (self.replay_required_refs, "replay refs"),
                              (self.contradiction_refs, "contradiction refs"), (self.invalidated_goal_decision_refs, "invalidated decisions"),
                              (self.frontier_refs, "reconciliation frontiers")):
            _unique(values, label)


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
