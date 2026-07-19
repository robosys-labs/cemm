"""CEMM v3.5 Phase-18 output/discourse authority contracts.

Authority is deliberately split:
Response UOL != surface candidate != semantic round-trip != emission authorization
!= transport observation != output discourse != common ground.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EmissionAuthorizationDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    DEFER = "defer"


class EmissionIdempotencyMode(StrEnum):
    NONE = "none"
    CLIENT_KEY = "client_key"
    ADAPTER_KEY = "adapter_key"
    EXTERNAL_CORRELATION = "external_correlation"


class EmissionJournalStatus(StrEnum):
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CHANNEL_ACKNOWLEDGED = "channel_acknowledged"
    DELIVERY_CONFIRMED = "delivery_confirmed"
    DELIVERY_UNKNOWN = "delivery_unknown"
    FAILED_BEFORE_EMIT = "failed_before_emit"
    FAILED_AFTER_SUBMIT = "failed_after_submit"
    CANCELLED_BEFORE_SUBMIT = "cancelled_before_submit"
    FINALIZED = "finalized"


class EmissionStatus(StrEnum):
    CHANNEL_ACCEPTED = "channel_accepted"
    DELIVERED = "delivered"
    UNKNOWN_DELIVERY = "unknown_delivery"


class OutputCommitmentStatus(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class CommonGroundStatus(StrEnum):
    PROPOSED = "proposed"
    EMITTED = "emitted"
    RECEIVED_EVIDENCE = "received_evidence"
    ACKNOWLEDGED = "acknowledged"
    SHARED = "shared"
    OPPOSED = "opposed"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"
    UNKNOWN_DELIVERY = "unknown_delivery"


@dataclass(frozen=True, slots=True)
class ChannelAdapterContractRecord:
    contract_ref: str
    channel_ref: str
    adapter_ref: str
    adapter_revision: int
    max_payload_bytes: int
    allowed_language_tags: tuple[str, ...] = ()
    transformation_refs: tuple[str, ...] = ()
    content_preserving_transform_only: bool = True
    requires_post_transform_roundtrip: bool = False
    idempotency_mode: EmissionIdempotencyMode = EmissionIdempotencyMode.NONE
    retry_safe_on_unknown: bool = False
    supports_recovery_query: bool = False
    delivery_ack_semantics_ref: str = "delivery:unknown"
    delivery_ack_proves_recipient_receipt: bool = False
    retention_policy_ref: str = "retention:channel_default"
    security_scope_ref: str = "security:channel_default"
    permission_ref: str = "internal"
    revision: int = 1
    supersedes_revision: int | None = None
    active: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.contract_ref, "channel contract_ref"), (self.channel_ref, "channel_ref"),
            (self.adapter_ref, "adapter_ref"), (self.delivery_ack_semantics_ref, "ack semantics"),
            (self.retention_policy_ref, "retention policy"), (self.security_scope_ref, "security scope"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if min(self.adapter_revision, self.revision, self.max_payload_bytes) < 1:
            raise ValueError("channel adapter revisions/payload limit must be positive")
        _supersession(self.revision, self.supersedes_revision, "channel adapter")
        if self.retry_safe_on_unknown and self.idempotency_mode == EmissionIdempotencyMode.NONE:
            raise ValueError("unknown-delivery retries require idempotency")
        if self.retry_safe_on_unknown and not self.supports_recovery_query:
            raise ValueError("unknown-delivery retry safety requires a reviewed recovery-query capability")
        if self.requires_post_transform_roundtrip and not self.transformation_refs:
            raise ValueError("post-transform roundtrip requires declared transformations")
        _unique(self.allowed_language_tags, "allowed language tags")
        _unique(self.transformation_refs, "channel transformations")


@dataclass(frozen=True, slots=True)
class LiteralEmissionPolicyRecord:
    """Exact reviewed exception for literal surface emission; never generic NLG authority."""
    policy_ref: str
    response_goal_schema_pins: tuple[tuple[str, int], ...]
    language_tag: str
    surface_sha256: str
    expected_graph_fingerprint: str
    trigger_pins: tuple[PinnedRecord, ...] = ()
    permission_ref: str = "public"
    revision: int = 1
    supersedes_revision: int | None = None
    active: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.policy_ref, "literal policy_ref"), (self.language_tag, "language_tag"),
            (self.surface_sha256, "surface_sha256"), (self.expected_graph_fingerprint, "graph fingerprint"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        _sha256(self.surface_sha256, "literal surface")
        if self.revision < 1 or not self.response_goal_schema_pins:
            raise ValueError("literal policy requires positive revision and exact goal-schema pins")
        _supersession(self.revision, self.supersedes_revision, "literal emission policy")
        _unique(self.response_goal_schema_pins, "literal goal schema pins")
        _unique(tuple(pin.key for pin in self.trigger_pins), "literal trigger pins")


@dataclass(frozen=True, slots=True)
class EmissionGateAssessmentRecord:
    assessment_ref: str
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
        for value, label in (
            (self.assessment_ref, "gate assessment_ref"), (self.gate_ref, "gate_ref"),
            (self.evaluator_ref, "evaluator_ref"), (self.evaluator_revision, "evaluator_revision"),
            (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
            (self.snapshot_fingerprint, "snapshot fingerprint"),
        ):
            _ref(value, label)
        if self.revision != 1 or self.snapshot_revision < 0:
            raise ValueError("emission gate assessments are immutable and snapshot-pinned")
        if self.passed and not self.checked_pins:
            raise ValueError("passing emission gate requires exact checked substrate")
        _unique(tuple(pin.key for pin in self.checked_pins), "emission gate checked pins")
        _unique(self.authorization_refs, "emission gate authorizations")
        _unique(self.proof_refs, "emission gate proofs")
        _unique(self.reason_refs, "emission gate reasons")


@dataclass(frozen=True, slots=True)
class EmissionAuthorizationRecord:
    authorization_ref: str
    response_uol_pin: PinnedRecord
    realization_request_pin: PinnedRecord
    surface_candidate_pin: PinnedRecord
    semantic_roundtrip_pin: PinnedRecord
    goal_decision_pin: PinnedRecord
    channel_contract_pin: PinnedRecord
    gate_assessment_pins: tuple[PinnedRecord, ...]
    decision: EmissionAuthorizationDecision
    audience_refs: tuple[str, ...]
    surface_sha256: str
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    operation_result_pins: tuple[PinnedRecord, ...] = ()
    operation_reconciliation_pins: tuple[PinnedRecord, ...] = ()
    literal_policy_pin: PinnedRecord | None = None
    authorization_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    snapshot_revision: int = 0
    snapshot_fingerprint: str = ""
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authorization_ref, "emission authorization_ref"), (self.surface_sha256, "surface_sha256"),
            (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
            (self.sensitivity, "sensitivity"), (self.snapshot_fingerprint, "snapshot fingerprint"),
        ):
            _ref(value, label)
        _sha256(self.surface_sha256, "authorized surface")
        if self.revision != 1 or self.snapshot_revision < 0:
            raise ValueError("emission authorizations are immutable and snapshot-pinned")
        if self.decision == EmissionAuthorizationDecision.ALLOW and self.failed_gates:
            raise ValueError("allowed emission cannot contain failed gates")
        if self.decision == EmissionAuthorizationDecision.ALLOW and not self.audience_refs:
            raise ValueError("allowed emission requires at least one explicit audience")
        if self.decision != EmissionAuthorizationDecision.ALLOW and not self.failed_gates:
            raise ValueError("non-allowed emission requires explicit failed/deferred gates")
        for values, label in (
            (tuple(pin.key for pin in self.gate_assessment_pins), "gate assessment pins"),
            (self.audience_refs, "audience refs"), (self.passed_gates, "passed gates"),
            (self.failed_gates, "failed gates"),
            (tuple(pin.key for pin in self.operation_result_pins), "operation result pins"),
            (tuple(pin.key for pin in self.operation_reconciliation_pins), "operation reconciliation pins"),
            (self.authorization_refs, "authorization refs"),
        ):
            _unique(values, label)


@dataclass(frozen=True, slots=True)
class EmissionJournalRecord:
    journal_ref: str
    authorization_pin: PinnedRecord
    status: EmissionJournalStatus
    idempotency_key: str | None
    adapter_ref: str
    adapter_revision: int
    surface_sha256: str
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
        for value, label in (
            (self.journal_ref, "emission journal_ref"), (self.adapter_ref, "adapter_ref"),
            (self.surface_sha256, "surface_sha256"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"), (self.sensitivity, "sensitivity"),
        ):
            _ref(value, label)
        _sha256(self.surface_sha256, "journal surface")
        if min(self.adapter_revision, self.revision) < 1 or self.submission_attempt < 0:
            raise ValueError("journal revisions/attempts must be valid")
        _supersession(self.revision, self.supersedes_revision, "emission journal")
        if self.revision > 1 and self.prior_journal_pin is None:
            raise ValueError("journal lifecycle revisions require exact prior pin")
        _unique(self.request_evidence_refs, "journal request evidence")
        _unique(self.response_evidence_refs, "journal response evidence")
        _unique(self.external_correlation_refs, "journal correlations")


@dataclass(frozen=True, slots=True)
class EmissionRecord:
    emission_ref: str
    journal_pin: PinnedRecord
    authorization_pin: PinnedRecord
    response_uol_pin: PinnedRecord
    surface_candidate_pin: PinnedRecord
    status: EmissionStatus
    surface_sha256: str
    audience_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    channel_ref: str
    external_correlation_refs: tuple[str, ...] = ()
    emitted_bytes_ref: str | None = None
    emitted_at: str | None = None
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.emission_ref, "emission_ref"), (self.surface_sha256, "surface_sha256"),
            (self.channel_ref, "channel_ref"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"), (self.sensitivity, "sensitivity"),
        ):
            _ref(value, label)
        _sha256(self.surface_sha256, "emitted surface")
        if self.revision != 1 or not (self.evidence_refs or self.proof_refs):
            raise ValueError("emission is immutable observed history and requires evidence/proof")
        if not self.audience_refs:
            raise ValueError("observed emission requires at least one explicit audience")
        _unique(self.audience_refs, "emission audiences")
        _unique(self.evidence_refs, "emission evidence")
        _unique(self.proof_refs, "emission proofs")
        _unique(self.external_correlation_refs, "emission correlations")


@dataclass(frozen=True, slots=True)
class EmissionAnomalyRecord:
    """Observed channel-side output anomaly that must never become discourse authority.

    Used when content may have left the system but cannot be represented as the
    exact authorized emission (surface mutation, contradictory adapter outcome,
    or other integrity failure). Historical evidence is preserved without
    pretending the output was semantically authorized.
    """
    anomaly_ref: str
    anomaly_kind_ref: str
    journal_pin: PinnedRecord
    authorization_pin: PinnedRecord
    channel_contract_pin: PinnedRecord
    authorized_surface_sha256: str
    observed_surface_sha256: str | None
    content_left_system: bool
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()
    external_correlation_refs: tuple[str, ...] = ()
    channel_ref: str = "channel:unknown"
    detected_at: str | None = None
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    no_output_discourse_authority: bool = True
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.anomaly_ref, "emission anomaly_ref"), (self.anomaly_kind_ref, "anomaly kind"),
            (self.authorized_surface_sha256, "authorized surface sha256"), (self.channel_ref, "channel_ref"),
            (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
            (self.sensitivity, "sensitivity"),
        ):
            _ref(value, label)
        _sha256(self.authorized_surface_sha256, "authorized surface")
        if self.observed_surface_sha256 is not None:
            _sha256(self.observed_surface_sha256, "observed surface")
        if self.revision != 1 or not self.no_output_discourse_authority:
            raise ValueError("emission anomalies are immutable non-discourse audit history")
        if self.content_left_system and not (self.evidence_refs or self.proof_refs):
            raise ValueError("content-left-system anomaly requires evidence/proof")
        _unique(self.evidence_refs, "anomaly evidence")
        _unique(self.proof_refs, "anomaly proofs")
        _unique(self.reason_refs, "anomaly reasons")
        _unique(self.external_correlation_refs, "anomaly correlations")


@dataclass(frozen=True, slots=True)
class SilenceOutcomeRecord:
    silence_ref: str
    goal_decision_pin: PinnedRecord
    selected_goal_pins: tuple[PinnedRecord, ...]
    target_refs: tuple[str, ...]
    policy_pins: tuple[PinnedRecord, ...]
    reason_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    snapshot_revision: int
    snapshot_fingerprint: str
    revision: int = 1

    def __post_init__(self) -> None:
        for value, label in (
            (self.silence_ref, "silence_ref"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"), (self.snapshot_fingerprint, "snapshot fingerprint"),
        ):
            _ref(value, label)
        if self.revision != 1 or self.snapshot_revision < 0:
            raise ValueError("silence outcomes are immutable and snapshot-pinned")
        if not self.selected_goal_pins or not self.target_refs or not self.reason_refs:
            raise ValueError("auditable silence requires selected goals, targets and reasons")
        _unique(tuple(pin.key for pin in self.selected_goal_pins), "silence goal pins")
        _unique(self.target_refs, "silence targets")
        _unique(tuple(pin.key for pin in self.policy_pins), "silence policy pins")
        _unique(self.reason_refs, "silence reasons")


@dataclass(frozen=True, slots=True)
class OutputDiscourseActRecord:
    discourse_ref: str
    emission_pin: PinnedRecord
    response_uol_pin: PinnedRecord
    goal_candidate_pins: tuple[PinnedRecord, ...]
    speaker_ref: str
    addressee_refs: tuple[str, ...]
    response_root_refs: tuple[str, ...]
    acknowledgement_target_refs: tuple[str, ...] = ()
    operation_result_pins: tuple[PinnedRecord, ...] = ()
    reason_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    emitted_at: str | None = None
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.discourse_ref, "discourse_ref"), (self.speaker_ref, "speaker_ref"),
            (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.revision != 1 or not self.goal_candidate_pins or not self.response_root_refs:
            raise ValueError("output discourse is immutable and requires exact goals/response roots")
        _unique(tuple(pin.key for pin in self.goal_candidate_pins), "output goal pins")
        _unique(self.addressee_refs, "addressee refs")
        _unique(self.response_root_refs, "response roots")
        _unique(self.acknowledgement_target_refs, "acknowledgement targets")
        _unique(tuple(pin.key for pin in self.operation_result_pins), "operation result pins")
        _unique(self.reason_refs, "discourse reasons")
        _unique(self.evidence_refs, "discourse evidence")


@dataclass(frozen=True, slots=True)
class OutputCommitmentRecord:
    commitment_ref: str
    discourse_pin: PinnedRecord
    target_refs: tuple[str, ...]
    commitment_kind_ref: str
    status: OutputCommitmentStatus = OutputCommitmentStatus.ACTIVE
    common_ground_proposal: bool = True
    acceptance_evidence_refs: tuple[str, ...] = ()
    correction_pins: tuple[PinnedRecord, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.commitment_ref, "commitment_ref"), (self.commitment_kind_ref, "commitment kind"),
            (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.revision < 1 or not self.target_refs:
            raise ValueError("output commitment requires positive revision and semantic targets")
        _supersession(self.revision, self.supersedes_revision, "output commitment")
        _unique(self.target_refs, "output commitment targets")
        _unique(self.acceptance_evidence_refs, "acceptance evidence")
        _unique(tuple(pin.key for pin in self.correction_pins), "correction pins")


@dataclass(frozen=True, slots=True)
class CommonGroundRecord:
    ground_ref: str
    subject_ref: str
    participant_refs: tuple[str, ...]
    status: CommonGroundStatus
    supporting_discourse_pins: tuple[PinnedRecord, ...]
    supporting_emission_pins: tuple[PinnedRecord, ...]
    opposing_pins: tuple[PinnedRecord, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    valid_time_ref: str | None = None
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.ground_ref, "common-ground ref"), (self.subject_ref, "common-ground subject"),
            (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.revision < 1 or len(self.participant_refs) < 2:
            raise ValueError("common ground requires positive revision and at least two participants")
        _supersession(self.revision, self.supersedes_revision, "common ground")
        if not self.supporting_discourse_pins or not self.supporting_emission_pins:
            raise ValueError("common ground requires exact emitted discourse support")
        _unique(self.participant_refs, "common-ground participants")
        _unique(tuple(pin.key for pin in self.supporting_discourse_pins), "common-ground discourse pins")
        _unique(tuple(pin.key for pin in self.supporting_emission_pins), "common-ground emission pins")
        _unique(tuple(pin.key for pin in self.opposing_pins), "common-ground opposing pins")
        _unique(self.evidence_refs, "common-ground evidence")


@dataclass(frozen=True, slots=True)
class OutputReferenceAnchorRecord:
    anchor_ref: str
    target_kind_ref: str
    target_ref: str
    target_pin: PinnedRecord | None
    response_uol_pin: PinnedRecord
    discourse_pin: PinnedRecord
    goal_refs: tuple[str, ...]
    audience_refs: tuple[str, ...]
    salience: float
    ordinal: int
    context_ref: str
    permission_ref: str
    time_ref: str | None = None
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.anchor_ref, "anchor_ref"), (self.target_kind_ref, "target kind"),
            (self.target_ref, "target_ref"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.revision != 1 or self.ordinal < 0 or not isfinite(self.salience) or self.salience < 0:
            raise ValueError("reference anchors are immutable with finite non-negative salience/ordinal")
        _unique(self.goal_refs, "reference goal refs")
        _unique(self.audience_refs, "reference audience refs")


@dataclass(frozen=True, slots=True)
class OutputCorrectionRecord:
    correction_ref: str
    correcting_discourse_pin: PinnedRecord
    prior_commitment_pins: tuple[PinnedRecord, ...]
    prior_common_ground_pins: tuple[PinnedRecord, ...]
    replacement_target_refs: tuple[str, ...]
    opposition_target_refs: tuple[str, ...]
    invalidated_projection_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    revision: int = 1

    def __post_init__(self) -> None:
        for value, label in (
            (self.correction_ref, "correction_ref"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.revision != 1 or not self.prior_commitment_pins:
            raise ValueError("output corrections are immutable and require exact prior commitments")
        if not (self.replacement_target_refs or self.opposition_target_refs):
            raise ValueError("correction must replace or oppose an exact semantic target")
        _unique(tuple(pin.key for pin in self.prior_commitment_pins), "prior commitment pins")
        _unique(tuple(pin.key for pin in self.prior_common_ground_pins), "prior common-ground pins")
        _unique(self.replacement_target_refs, "replacement targets")
        _unique(self.opposition_target_refs, "opposition targets")
        _unique(self.invalidated_projection_refs, "invalidated projections")
        _unique(self.evidence_refs, "correction evidence")
        _unique(self.proof_refs, "correction proofs")


def fingerprint(prefix: str, value: Any) -> str:
    return semantic_fingerprint(prefix, value, 64)


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError(f"{label} sha256 must be 64 hex characters")


def _unique(values, label: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{label} must be unique")


def _supersession(revision: int, supersedes: int | None, label: str) -> None:
    if supersedes is not None and not 1 <= supersedes < revision:
        raise ValueError(f"{label} supersedes_revision must target an older revision")
