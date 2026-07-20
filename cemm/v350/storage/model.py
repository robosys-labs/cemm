"""Typed durable-record and atomic-patch contracts for CEMM v3.5.

The storage layer owns stable record classes and transaction metadata only.  It
must not become a semantic ontology: learned types, facets, actions, events,
relations, and state values remain data-driven schema records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Generic, Iterable, Mapping, TypeVar

from ..schema.model import SchemaLifecycleStatus, semantic_fingerprint
from ..uol.model import CapabilityStatus


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class RecordKind(StrEnum):
    SCHEMA = "schema"
    FACET_ENTITLEMENT = "facet_entitlement"
    REFERENT = "referent"
    TYPE_ASSERTION = "type_assertion"
    IDENTITY_FACET = "identity_facet"
    SEMANTIC_APPLICATION = "semantic_application"
    PROPOSITION = "proposition"
    CLAIM_OCCURRENCE = "claim_occurrence"
    CLAIM_RECORD = "claim_record"
    CLAIM_HISTORY = "claim_history"
    EPISTEMIC_ADMISSION = "epistemic_admission"
    EVENT_OCCURRENCE = "event_occurrence"
    STATE_ASSIGNMENT = "state_assignment"
    STATE_DELTA = "state_delta"
    CAPABILITY_INSTANCE = "capability_instance"
    CAPABILITY_DELTA = "capability_delta"
    TRANSITION_CONTRACT = "transition_contract"
    CAPABILITY_DEPENDENCY = "capability_dependency"
    TRANSITION_PROOF = "transition_proof"
    KNOWLEDGE = "knowledge"
    EVIDENCE = "evidence"
    SOURCE_ASSESSMENT = "source_assessment"
    IMPACT_ASSESSMENT = "impact_assessment"
    IMPORTANCE_ASSESSMENT = "importance_assessment"
    IMPACT_RULE = "impact_rule"
    IMPACT_PROOF = "impact_proof"
    IMPORTANCE_EVIDENCE = "importance_evidence"
    IMPORTANCE_POLICY = "importance_policy"
    SIGNIFICANCE_ASSESSMENT = "significance_assessment"
    RESPONSE_POLICY_RULE = "response_policy_rule"
    SEMANTIC_OBLIGATION = "semantic_obligation"
    GOAL_CANDIDATE = "goal_candidate"
    GOAL_CONFLICT = "goal_conflict"
    GOAL_DECISION = "goal_decision"
    OPERATION_ADAPTER_CONTRACT = "operation_adapter_contract"
    OPERATION_GATE_ASSESSMENT = "operation_gate_assessment"
    OPERATION_PLAN = "operation_plan"
    OPERATION_AUTHORIZATION = "operation_authorization"
    OPERATION_JOURNAL = "operation_journal"
    OPERATION_RESULT = "operation_result"
    OPERATION_RECONCILIATION = "operation_reconciliation"
    RESPONSE_TRANSFORM_RULE = "response_transform_rule"
    RESPONSE_TRANSFORMATION_PROOF = "response_transformation_proof"
    RESPONSE_OMISSION = "response_omission"
    RESPONSE_UOL = "response_uol"
    REALIZATION_REQUEST = "realization_request"
    ARGUMENT_FRAME = "argument_frame"
    MORPHOLOGY_RULE = "morphology_rule"
    LINEARIZATION_RULE = "linearization_rule"
    DEEP_CLAUSE_PLAN = "deep_clause_plan"
    REFERENCE_PLAN = "reference_plan"
    SURFACE_CANDIDATE = "surface_candidate"
    SEMANTIC_ROUNDTRIP = "semantic_roundtrip"
    SEMANTIC_ANALYZER_CONTRACT = "semantic_analyzer_contract"
    CHANNEL_ADAPTER_CONTRACT = "channel_adapter_contract"
    LITERAL_EMISSION_POLICY = "literal_emission_policy"
    EMISSION_GATE_ASSESSMENT = "emission_gate_assessment"
    EMISSION_AUTHORIZATION = "emission_authorization"
    EMISSION_JOURNAL = "emission_journal"
    EMISSION = "emission"
    EMISSION_ANOMALY = "emission_anomaly"
    SILENCE_OUTCOME = "silence_outcome"
    OUTPUT_DISCOURSE_ACT = "output_discourse_act"
    OUTPUT_COMMITMENT = "output_commitment"
    COMMON_GROUND = "common_ground"
    OUTPUT_REFERENCE_ANCHOR = "output_reference_anchor"
    OUTPUT_CORRECTION = "output_correction"
    MIGRATION_SOURCE = "migration_source"
    MIGRATION_RULE = "migration_rule"
    MIGRATION_TARGET_MAP = "migration_target_map"
    MIGRATION_DECISION = "migration_decision"
    MIGRATION_BATCH = "migration_batch"
    MIGRATION_QUARANTINE = "migration_quarantine"
    MIGRATION_INTENTIONAL_CHANGE = "migration_intentional_change"
    SEMANTIC_EQUIVALENCE = "semantic_equivalence"
    MIGRATION_ROLLBACK = "migration_rollback"
    DEFAULT_RULE = "default_rule"
    DEPENDENCY = "dependency"
    LANGUAGE_PACK = "language_pack"
    LANGUAGE_FORM = "language_form"
    LEXEME = "lexeme"
    FORM_LEXEME_LINK = "form_lexeme_link"
    LEXICAL_SENSE = "lexical_sense"
    LEXEME_SENSE_LINK = "lexeme_sense_link"
    FORM_SENSE_LINK = "form_sense_link"
    SEMANTIC_CONTRIBUTION_SPEC = "semantic_contribution_spec"
    MORPHOLOGY_ANALYSIS_RULE = "morphology_analysis_rule"
    CONSTRUCTION = "construction"
    CONSTRUCTION_PROGRAM = "construction_program"
    MATERIALIZED_VIEW = "materialized_view"
    LEARNING_PACKAGE = "learning_package"
    LEARNING_FRONTIER = "learning_frontier"
    LEARNING_EVIDENCE_LINK = "learning_evidence_link"
    COMPETENCE_RESULT = "competence_result"
    PROMOTION_DECISION = "promotion_decision"
    LEARNING_INVALIDATION = "learning_invalidation"


class AssertionStatus(StrEnum):
    SUPPORTED = "supported"
    OPPOSED = "opposed"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class KnowledgeStatus(StrEnum):
    SUPPORTED = "supported"
    OPPOSED = "opposed"
    BOTH = "both"
    UNDETERMINED = "undetermined"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"




class ClaimHistoryAction(StrEnum):
    ASSERT = "assert"
    CORRECT = "correct"
    RETRACT = "retract"
    SUPERSEDE = "supersede"


class AdmissionDecision(StrEnum):
    PRESERVE_ATTRIBUTED = "preserve_attributed"
    ADMIT_SUPPORT = "admit_support"
    ADMIT_OPPOSITION = "admit_opposition"
    DEFER = "defer"
    DENY = "deny"
    RETRACT = "retract"


class AdmissionLifecycleStatus(StrEnum):
    ACTIVE = "active"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class AssignmentStatus(StrEnum):
    ACTIVE = "active"
    OPPOSED = "opposed"
    CONTRADICTED = "contradicted"
    TERMINATED = "terminated"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class ConditionTruth(StrEnum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class PatchOperationKind(StrEnum):
    UPSERT = "upsert"
    TOMBSTONE = "tombstone"
    MATERIALIZE = "materialize"
    INVALIDATE = "invalidate"


class PatchCommitStatus(StrEnum):
    COMMITTED = "committed"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    IDEMPOTENT = "idempotent"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_ref: str
    source_ref: str
    confidence: float
    lineage_ref: str
    context_ref: str = "actual"
    observed_at: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    permission_ref: str = "conversation"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.evidence_ref, "evidence_ref"),
            (self.source_ref, "source_ref"),
            (self.lineage_ref, "lineage_ref"),
            (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.confidence, "evidence confidence")
        if (self.span_start is None) != (self.span_end is None):
            raise ValueError("evidence span requires both start and end")
        if self.span_start is not None and (self.span_start < 0 or self.span_end < self.span_start):
            raise ValueError("invalid evidence span")


@dataclass(frozen=True, slots=True)
class SourceAssessmentRecord:
    assessment_ref: str
    source_ref: str
    authority: float
    reliability: float
    access_quality: float
    bias_risk: float
    context_ref: str
    evidence_refs: tuple[str, ...]
    revision: int = 1
    supersedes_revision: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    permission_ref: str = "conversation"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.assessment_ref, "source assessment_ref"),
            (self.source_ref, "source assessment source_ref"),
            (self.context_ref, "source assessment context_ref"),
            (self.permission_ref, "source assessment permission_ref"),
        ):
            _require_ref(value, label)
        if self.revision < 1:
            raise ValueError("source assessment revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("source assessment supersedes_revision must target an older revision")
        for value, label in (
            (self.authority, "source authority"),
            (self.reliability, "source reliability"),
            (self.access_quality, "source access quality"),
            (self.bias_risk, "source bias risk"),
        ):
            _confidence(value, label)
        _require_unique(self.evidence_refs, "source-assessment evidence")
        if not self.evidence_refs:
            raise ValueError("source assessment requires evidence")
        _interval(self.valid_from, self.valid_to, "source assessment")


@dataclass(frozen=True, slots=True)
class ReferentTypeAssertion:
    assertion_ref: str
    referent_ref: str
    type_schema_ref: str
    type_revision: int
    status: AssertionStatus
    confidence: float
    context_ref: str
    valid_from: str | None = None
    valid_to: str | None = None
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    permission_ref: str = "conversation"

    def __post_init__(self) -> None:
        for value, label in (
            (self.assertion_ref, "assertion_ref"),
            (self.referent_ref, "referent_ref"),
            (self.type_schema_ref, "type_schema_ref"),
            (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _require_ref(value, label)
        if self.type_revision < 1:
            raise ValueError("type assertion revision pin must be positive")
        _confidence(self.confidence, "type assertion confidence")
        _require_unique(self.evidence_refs, "type assertion evidence")
        _require_unique(self.source_refs, "type assertion sources")
        _require_unique(self.proof_refs, "type assertion proofs")
        _interval(self.valid_from, self.valid_to, "type assertion")


@dataclass(frozen=True, slots=True)
class IdentityFacetRecord:
    identity_facet_ref: str
    referent_ref: str
    facet_schema_ref: str
    normalized_value: str
    anchor_ref: str | None = None
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()
    context_ref: str = "actual"

    def __post_init__(self) -> None:
        for value, label in (
            (self.identity_facet_ref, "identity_facet_ref"),
            (self.referent_ref, "referent_ref"),
            (self.facet_schema_ref, "facet_schema_ref"),
            (self.normalized_value, "normalized_value"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.confidence, "identity-facet confidence")
        _require_unique(self.evidence_refs, "identity-facet evidence")


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    claim_record_ref: str
    claim_occurrence_ref: str
    proposition_ref: str
    source_ref: str
    source_context_ref: str
    reported_context_ref: str
    commitment_strength: float
    permission_ref: str = "conversation"
    evidence_refs: tuple[str, ...] = ()
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.claim_record_ref, "claim_record_ref"),
            (self.claim_occurrence_ref, "claim_occurrence_ref"),
            (self.proposition_ref, "proposition_ref"),
            (self.source_ref, "source_ref"),
            (self.source_context_ref, "source_context_ref"),
            (self.reported_context_ref, "reported_context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.commitment_strength, "claim commitment strength")
        _require_unique(self.evidence_refs, "claim-record evidence")
        if self.source_context_ref == self.reported_context_ref:
            raise ValueError("claim record must preserve source-attributed content context")


@dataclass(frozen=True, slots=True)
class ClaimHistoryRecord:
    history_ref: str
    claim_record_ref: str
    action: ClaimHistoryAction
    source_ref: str
    context_ref: str
    evidence_refs: tuple[str, ...]
    target_claim_record_ref: str | None = None
    occurred_at: str | None = None
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.history_ref, "history_ref"),
            (self.claim_record_ref, "claim_record_ref"),
            (self.source_ref, "source_ref"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        if self.revision < 1:
            raise ValueError("claim history revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("claim history supersedes_revision must target an older revision")
        _require_unique(self.evidence_refs, "claim-history evidence")
        if not self.evidence_refs:
            raise ValueError("claim history requires evidence")
        if self.action in {ClaimHistoryAction.CORRECT, ClaimHistoryAction.RETRACT, ClaimHistoryAction.SUPERSEDE}:
            if not self.target_claim_record_ref:
                raise ValueError(f"{self.action.value} claim history requires a target claim")


@dataclass(frozen=True, slots=True)
class EpistemicAdmissionRecord:
    admission_ref: str
    proposition_ref: str
    source_context_ref: str
    target_context_ref: str
    decision: AdmissionDecision
    truth_status: KnowledgeStatus
    confidence: float
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    policy_ref: str
    source_assessment_pins: tuple[tuple[str, int], ...] = ()
    authorization_ref: str | None = None
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    lifecycle_status: AdmissionLifecycleStatus = AdmissionLifecycleStatus.ACTIVE
    valid_time_ref: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    retracts_admission_ref: str | None = None
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.admission_ref, "admission_ref"),
            (self.proposition_ref, "proposition_ref"),
            (self.source_context_ref, "source_context_ref"),
            (self.target_context_ref, "target_context_ref"),
            (self.policy_ref, "policy_ref"),
            (self.permission_ref, "permission_ref"),
            (self.sensitivity, "sensitivity"),
        ):
            _require_ref(value, label)
        if self.revision < 1:
            raise ValueError("epistemic admission revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("epistemic admission supersedes_revision must target an older revision")
        _confidence(self.confidence, "epistemic admission confidence")
        _require_unique(self.source_refs, "epistemic admission sources")
        _require_unique(self.source_assessment_pins, "epistemic admission source assessments")
        for assessment_ref, assessment_revision in self.source_assessment_pins:
            _require_ref(assessment_ref, "epistemic admission source assessment ref")
            if assessment_revision < 1:
                raise ValueError("epistemic admission source assessment revision must be positive")
        _require_unique(self.evidence_refs, "epistemic admission evidence")
        _require_unique(self.proof_refs, "epistemic admission proofs")
        _interval(self.valid_from, self.valid_to, "epistemic admission")
        admitted = {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION}
        if self.decision in admitted:
            if not self.authorization_ref or not self.authorization_ref.strip():
                raise ValueError("actual-world admission requires explicit authorization")
            if not self.source_refs or not self.source_assessment_pins or not self.evidence_refs or not self.proof_refs:
                raise ValueError("actual-world admission requires source assessments, source, evidence, and proof")
            expected = KnowledgeStatus.SUPPORTED if self.decision == AdmissionDecision.ADMIT_SUPPORT else KnowledgeStatus.OPPOSED
            if self.truth_status != expected:
                raise ValueError("admission decision and truth status disagree")
            if self.lifecycle_status != AdmissionLifecycleStatus.ACTIVE:
                raise ValueError("new admitted support/opposition must be active")
        elif self.decision == AdmissionDecision.RETRACT:
            if not self.retracts_admission_ref:
                raise ValueError("retraction must identify the admission being retracted")
            if not self.authorization_ref or not self.authorization_ref.strip():
                raise ValueError("actual-world admission retraction requires explicit authorization")
            if not self.source_refs or not self.evidence_refs or not self.proof_refs:
                raise ValueError("actual-world admission retraction requires source, evidence, and proof")
            if self.truth_status != KnowledgeStatus.UNDETERMINED:
                raise ValueError("retraction is not itself support or opposition")
        elif self.truth_status != KnowledgeStatus.UNDETERMINED:
            raise ValueError("non-admission decisions cannot assert truth support")
        if self.truth_status == KnowledgeStatus.BOTH:
            raise ValueError("four-state BOTH is derived from independent admissions, never one admission record")


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    knowledge_ref: str
    proposition_ref: str
    truth_status: KnowledgeStatus
    confidence: float
    context_ref: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    valid_time_ref: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    support_lineage_refs: tuple[str, ...] = ()
    derivation_refs: tuple[str, ...] = ()
    superseded_by: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.knowledge_ref, "knowledge_ref"),
            (self.proposition_ref, "proposition_ref"),
            (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
            (self.sensitivity, "sensitivity"),
        ):
            _require_ref(value, label)
        _confidence(self.confidence, "knowledge confidence")
        _require_unique(self.source_refs, "knowledge sources")
        _require_unique(self.evidence_refs, "knowledge evidence")
        _require_unique(self.support_lineage_refs, "knowledge support lineage")
        _require_unique(self.derivation_refs, "knowledge derivations")
        if not self.source_refs:
            raise ValueError("knowledge requires source attribution")
        _interval(self.valid_from, self.valid_to, "knowledge")


@dataclass(frozen=True, slots=True)
class StateAssignment:
    assignment_ref: str
    holder_ref: str
    dimension_ref: str
    dimension_revision: int
    value_ref: str
    value_revision: int
    status: AssignmentStatus
    context_ref: str
    confidence: float
    valid_from: str | None = None
    valid_to: str | None = None
    evidence_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.assignment_ref, "assignment_ref"),
            (self.holder_ref, "holder_ref"),
            (self.dimension_ref, "dimension_ref"),
            (self.value_ref, "value_ref"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        if self.dimension_revision < 1 or self.value_revision < 1:
            raise ValueError("state assignment schema revisions must be positive")
        _confidence(self.confidence, "state assignment confidence")
        _require_unique(self.evidence_refs, "state assignment evidence")
        _require_unique(self.proof_refs, "state assignment proofs")
        _require_unique(self.source_refs, "state assignment sources")
        _interval(self.valid_from, self.valid_to, "state assignment")
        if self.status == AssignmentStatus.ACTIVE and not (self.evidence_refs or self.proof_refs):
            raise ValueError("active state assignment requires evidence or proof")


@dataclass(frozen=True, slots=True)
class CapabilityInstance:
    capability_ref: str
    holder_ref: str
    action_schema_ref: str
    action_schema_revision: int
    status: CapabilityStatus
    confidence: float
    context_ref: str
    revision: int = 1
    supersedes_revision: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    dependency_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.capability_ref, "capability_ref"),
            (self.holder_ref, "holder_ref"),
            (self.action_schema_ref, "action_schema_ref"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        if self.action_schema_revision < 1:
            raise ValueError("capability action schema revision must be positive")
        if self.revision < 1:
            raise ValueError("capability revision must be positive")
        if self.supersedes_revision is not None and self.supersedes_revision >= self.revision:
            raise ValueError("capability supersedes_revision must be lower than revision")
        _confidence(self.confidence, "capability confidence")
        _require_unique(self.dependency_refs, "capability dependencies")
        _require_unique(self.evidence_refs, "capability evidence")
        _require_unique(self.proof_refs, "capability proofs")
        _interval(self.valid_from, self.valid_to, "capability")
        if self.status != CapabilityStatus.UNKNOWN and not (self.evidence_refs or self.proof_refs):
            raise ValueError("non-unknown capability requires evidence or proof")


@dataclass(frozen=True, slots=True)
class DefaultRuleRecord:
    rule_ref: str
    target_facet_ref: str
    expected_dimension_ref: str | None = None
    expected_dimension_revision: int | None = None
    expected_value_ref: str | None = None
    expected_value_revision: int | None = None
    holder_type_refs: tuple[str, ...] = ()
    condition_refs: tuple[str, ...] = ()
    defeater_refs: tuple[str, ...] = ()
    context_constraints: tuple[str, ...] = ()
    temporal_constraints: tuple[str, ...] = ()
    priority: int = 0
    confidence: float = 0.5
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    revision: int = 1
    supersedes_revision: int | None = None
    scope_ref: str = "global"
    permission_ref: str = "public"
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.rule_ref, "rule_ref"),
            (self.target_facet_ref, "target_facet_ref"),
            (self.scope_ref, "scope_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _require_ref(value, label)
        if self.revision < 1:
            raise ValueError("default-rule revision must be positive")
        if self.supersedes_revision is not None:
            if self.supersedes_revision < 1 or self.supersedes_revision >= self.revision:
                raise ValueError("default-rule supersedes_revision must identify an earlier revision")
        _confidence(self.confidence, "default-rule confidence")
        for label, values in (
            ("holder types", self.holder_type_refs),
            ("conditions", self.condition_refs),
            ("defeaters", self.defeater_refs),
            ("context constraints", self.context_constraints),
            ("temporal constraints", self.temporal_constraints),
            ("evidence", self.evidence_refs),
        ):
            _require_unique(values, f"default-rule {label}")
        if (self.expected_dimension_ref is None) != (self.expected_dimension_revision is None):
            raise ValueError("default dimension reference and revision must be supplied together")
        if (self.expected_value_ref is None) != (self.expected_value_revision is None):
            raise ValueError("default value reference and revision must be supplied together")
        if self.expected_value_ref is not None and self.expected_dimension_ref is None:
            raise ValueError("default state value requires an expected dimension")
        for revision in (self.expected_dimension_revision, self.expected_value_revision):
            if revision is not None and revision < 1:
                raise ValueError("default-rule schema revision must be positive")


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    dependency_ref: str
    dependent_kind: RecordKind
    dependent_ref: str
    dependent_revision: int
    prerequisite_kind: RecordKind | None
    prerequisite_ref: str
    prerequisite_revision: int | None = None
    prerequisite_fingerprint: str | None = None
    dependency_kind: str = "semantic"
    active: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.dependency_ref, "dependency_ref"),
            (self.dependent_ref, "dependent_ref"),
            (self.prerequisite_ref, "prerequisite_ref"),
            (self.dependency_kind, "dependency_kind"),
        ):
            _require_ref(value, label)
        if self.dependent_revision < 1:
            raise ValueError("dependent revision must be positive")
        if self.prerequisite_revision is not None and self.prerequisite_revision < 1:
            raise ValueError("prerequisite revision must be positive")


@dataclass(frozen=True, slots=True)
class MaterializedViewRecord:
    view_ref: str
    view_kind: str
    subject_ref: str
    context_ref: str
    payload: Mapping[str, Any]
    dependency_refs: tuple[str, ...]
    dependency_fingerprint: str
    snapshot_revision: int

    def __post_init__(self) -> None:
        for value, label in (
            (self.view_ref, "view_ref"),
            (self.view_kind, "view_kind"),
            (self.subject_ref, "subject_ref"),
            (self.context_ref, "context_ref"),
            (self.dependency_fingerprint, "dependency_fingerprint"),
        ):
            _require_ref(value, label)
        if self.snapshot_revision < 0:
            raise ValueError("view snapshot revision cannot be negative")
        _require_unique(self.dependency_refs, "materialized-view dependencies")


@dataclass(frozen=True, slots=True)
class RecordDependency:
    record_kind: RecordKind | None
    record_ref: str
    revision: int | None = None
    fingerprint: str | None = None
    dependency_kind: str = "semantic"

    def __post_init__(self) -> None:
        _require_ref(self.record_ref, "record_ref")
        _require_ref(self.dependency_kind, "dependency_kind")
        if self.revision is not None and self.revision < 1:
            raise ValueError("dependency revision must be positive")


@dataclass(frozen=True, slots=True)
class PatchOperation:
    operation_ref: str
    operation_kind: PatchOperationKind
    record_kind: RecordKind
    target_ref: str
    record_revision: int = 1
    payload: Mapping[str, Any] = field(default_factory=dict)
    expected_record_revision: int | None = None
    expected_record_fingerprint: str | None = None
    dependencies: tuple[RecordDependency, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        for value, label in (
            (self.operation_ref, "operation_ref"),
            (self.target_ref, "target_ref"),
        ):
            _require_ref(value, label)
        if self.record_revision < 1:
            raise ValueError("operation record revision must be positive")
        if self.expected_record_revision is not None and self.expected_record_revision < 1:
            raise ValueError("expected record revision must be positive")
        if self.operation_kind in {PatchOperationKind.UPSERT, PatchOperationKind.MATERIALIZE} and not self.payload:
            raise ValueError("upsert/materialize operation requires a payload")
        if self.operation_kind in {PatchOperationKind.TOMBSTONE, PatchOperationKind.INVALIDATE} and self.payload:
            raise ValueError("tombstone/invalidate operation cannot carry a record payload")
        _require_unique(
            tuple((
                None if item.record_kind is None else item.record_kind.value,
                item.record_ref, item.revision, item.fingerprint, item.dependency_kind
            ) for item in self.dependencies),
            "operation dependency identities",
        )


@dataclass(frozen=True, slots=True)
class GraphPatch:
    patch_ref: str
    context_ref: str
    scope_ref: str
    source_ref: str
    permission_ref: str
    operations: tuple[PatchOperation, ...]
    expected_store_revision: int | None = None
    evidence_refs: tuple[str, ...] = ()
    validation_requirements: tuple[str, ...] = ()
    rollback_hint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.patch_ref, "patch_ref"),
            (self.context_ref, "context_ref"),
            (self.scope_ref, "scope_ref"),
            (self.source_ref, "source_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _require_ref(value, label)
        if self.expected_store_revision is not None and self.expected_store_revision < 0:
            raise ValueError("expected store revision cannot be negative")
        _require_unique(tuple(item.operation_ref for item in self.operations), "patch operation refs")
        _require_unique(self.evidence_refs, "patch evidence")
        _require_unique(self.validation_requirements, "patch validation requirements")
        if not self.operations:
            raise ValueError("graph patch requires at least one operation")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("graph-patch", self)


@dataclass(frozen=True, slots=True)
class PatchCommitResult:
    patch_ref: str
    status: PatchCommitStatus
    committed: bool
    store_revision_before: int
    store_revision_after: int
    applied_operation_refs: tuple[str, ...] = ()
    invalidated_view_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class StoredRecord(Generic[T]):
    record_kind: RecordKind
    record_ref: str
    revision: int
    payload: T
    content_fingerprint: str
    record_fingerprint: str
    layer: str
    store_revision: int
    lifecycle_status: str | None = None
    context_ref: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    permission_ref: str | None = None

    def __post_init__(self) -> None:
        _require_ref(self.record_ref, "record_ref")
        _require_ref(self.layer, "layer")
        if self.revision < 1 or self.store_revision < 0:
            raise ValueError("stored record revisions must be non-negative/positive")


@dataclass(frozen=True, slots=True)
class StoreSnapshot:
    store_revision: int
    boot_fingerprint: str
    overlay_fingerprint: str
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            "store-snapshot",
            (self.store_revision, self.boot_fingerprint, self.overlay_fingerprint),
            64,
        )


def _confidence(value: float, label: str) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be within [0, 1]")


def _interval(start: str | None, end: str | None, label: str) -> None:
    if start is None or end is None:
        return
    try:
        start_value = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_value = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} interval must use ISO-8601 values") from exc
    if end_value <= start_value:
        raise ValueError(f"{label} valid_to must be after valid_from")


def _require_ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


def _require_unique(values: Iterable[Any], label: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"duplicate {label}")
