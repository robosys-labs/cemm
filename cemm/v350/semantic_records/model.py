"""Canonical v3.5 semantic/durable record contracts required by the CSIR runtime.

This module is mechanically dependency-closed from the exact migration-era record definitions. It deliberately excludes the legacy cognitive graph type and unrelated legacy cognitive types.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import hashlib
import json
from math import isfinite
from typing import Any, Iterable, Mapping
from ..schema.model import (
    OpenBindingPurpose, PortFillerClass, SchemaClass, StorageKind, UseOperation,
)

class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value

class IdentityStatus(StrEnum):
    CANDIDATE = "candidate"
    PROVISIONAL = "provisional"
    RESOLVED = "resolved"
    DISPUTED = "disputed"
    MERGED = "merged"
    SPLIT = "split"
    RETIRED = "retired"

class Polarity(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class CoordinationKind(StrEnum):
    AND = "and"
    OR = "or"
    LIST = "list"
    ALTERNATIVE = "alternative"

class ScopeKind(StrEnum):
    LOGICAL = "logical"
    MODAL = "modal"
    TEMPORAL = "temporal"
    QUANTIFIER = "quantifier"
    DISCOURSE = "discourse"
    NEGATION = "negation"

class ClaimForce(StrEnum):
    ASSERTED = "asserted"
    SUGGESTED = "suggested"
    SPECULATED = "speculated"
    QUOTED = "quoted"
    DENIED = "denied"
    CORRECTED = "corrected"
    RETRACTED = "retracted"

class OccurrenceStatus(StrEnum):
    MENTIONED = "mentioned"
    CLAIMED = "claimed"
    REPORTED = "reported"
    OBSERVED = "observed"
    ADMITTED = "admitted"
    PLANNED = "planned"
    ATTEMPTED = "attempted"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    FAILED = "failed"
    PREVENTED = "prevented"
    HYPOTHETICAL = "hypothetical"
    COUNTERFACTUAL = "counterfactual"
    FICTIONAL = "fictional"
    NON_OCCURRING = "non_occurring"

class ChangeOperation(StrEnum):
    SET = "set"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    INCREASE = "increase"
    DECREASE = "decrease"
    TERMINATE = "terminate"
    RESTORE = "restore"
    GAIN = "gain"
    LOSE = "lose"
    ENABLE = "enable"
    DISABLE = "disable"

_STATE_DELTA_OPERATIONS = frozenset({
    ChangeOperation.SET,
    ChangeOperation.ACTIVATE,
    ChangeOperation.DEACTIVATE,
    ChangeOperation.INCREASE,
    ChangeOperation.DECREASE,
    ChangeOperation.TERMINATE,
    ChangeOperation.RESTORE,
})

class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    CONDITIONAL = "conditional"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"

class Valence(StrEnum):
    BENEFICIAL = "beneficial"
    HARMFUL = "harmful"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"

class ImportanceClass(StrEnum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class Reversibility(StrEnum):
    REVERSIBLE = "reversible"
    PARTIALLY_REVERSIBLE = "partially_reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class QuotedLiteral:
    literal_ref: str
    surface: str
    language_tag: str = "und"
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.literal_ref, "literal_ref")
        if not isinstance(self.surface, str):
            raise TypeError("quoted literal surface must be text")

@dataclass(frozen=True, slots=True)
class FillerRef:
    filler_class: PortFillerClass
    ref: str

    def __post_init__(self) -> None:
        _require_ref(self.ref, "filler ref")
        if self.filler_class == PortFillerClass.QUOTED_LITERAL:
            raise ValueError("quoted literals use QuotedLiteral, not FillerRef")

PortFiller = FillerRef | QuotedLiteral

@dataclass(frozen=True, slots=True)
class ApplicationBinding:
    port_ref: str
    fillers: tuple[PortFiller, ...] = ()
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    ordered: bool = False
    open_binding_purpose: OpenBindingPurpose | None = None

    def __post_init__(self) -> None:
        _require_ref(self.port_ref, "port_ref")
        _confidence(self.confidence, "binding confidence")
        _require_unique(tuple(_filler_key(item) for item in self.fillers), f"fillers of {self.port_ref}")
        has_variable = any(
            isinstance(item, FillerRef)
            and item.filler_class == PortFillerClass.SEMANTIC_VARIABLE
            for item in self.fillers
        )
        if has_variable and self.open_binding_purpose is None:
            raise ValueError("semantic-variable binding requires an explicit open_binding_purpose")
        if not has_variable and self.open_binding_purpose is not None:
            raise ValueError("open_binding_purpose requires a semantic-variable filler")

@dataclass(frozen=True, slots=True)
class Referent:
    referent_ref: str
    storage_kind: StorageKind = StorageKind.ORDINARY
    identity_status: IdentityStatus = IdentityStatus.CANDIDATE
    type_refs: tuple[str, ...] = ()
    identity_facet_refs: tuple[str, ...] = ()
    scope_ref: str = "global"
    context_refs: tuple[str, ...] = ("actual",)
    valid_time_ref: str | None = None
    provenance_refs: tuple[str, ...] = ()
    permission_ref: str = "conversation"
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_ref(self.referent_ref, "referent_ref")
        _require_ref(self.scope_ref, "scope_ref")
        _require_ref(self.permission_ref, "permission_ref")
        if self.revision < 1:
            raise ValueError("referent revision must be positive")
        _require_unique(self.type_refs, f"types of {self.referent_ref}")
        _require_unique(self.identity_facet_refs, f"identity facets of {self.referent_ref}")
        _require_unique(self.context_refs, f"contexts of {self.referent_ref}")
        if not self.context_refs:
            raise ValueError("referent requires at least one context")

    @property
    def record_fingerprint(self) -> str:
        return fingerprint("uol-referent-record", canonical_data(self))

@dataclass(frozen=True, slots=True)
class SemanticVariable:
    variable_ref: str
    expected_schema_classes: frozenset[SchemaClass] = frozenset()
    expected_type_refs: tuple[str, ...] = ()
    restriction_refs: tuple[str, ...] = ()
    projection_ref: str | None = None
    scope_ref: str = "local"
    evidence_refs: tuple[str, ...] = ()
    expected_filler_classes: frozenset[PortFillerClass] = frozenset()
    open_binding_purpose: OpenBindingPurpose | None = None
    projection_revision: int | None = None
    projection_candidates: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.variable_ref, "variable_ref")
        _require_ref(self.scope_ref, "scope_ref")
        _require_unique(self.expected_type_refs, f"expected types of {self.variable_ref}")
        _require_unique(self.restriction_refs, f"restrictions of {self.variable_ref}")
        if self.projection_ref is not None:
            _require_ref(self.projection_ref, "projection_ref")
        if self.projection_revision is not None and self.projection_revision < 1:
            raise ValueError("projection_revision must be positive")
        _require_unique(self.projection_candidates, f"projection candidates of {self.variable_ref}")
        for ref, revision in self.projection_candidates:
            _require_ref(ref, "projection candidate ref")
            if revision < 1:
                raise ValueError("projection candidate revision must be positive")
        if self.open_binding_purpose is not None and not isinstance(
            self.open_binding_purpose, OpenBindingPurpose
        ):
            raise TypeError("open_binding_purpose must be OpenBindingPurpose")

@dataclass(frozen=True, slots=True)
class SemanticApplication:
    application_ref: str
    schema_ref: str
    schema_revision: int
    bindings: tuple[ApplicationBinding, ...]
    context_ref: str
    use_operation: UseOperation = UseOperation.COMPOSE
    valid_time_ref: str | None = None
    polarity: Polarity = Polarity.POSITIVE
    confidence: float = 1.0
    assumptions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_ref(self.application_ref, "application_ref")
        _require_ref(self.schema_ref, "schema_ref")
        _require_ref(self.context_ref, "context_ref")
        if self.schema_revision < 1:
            raise ValueError("application schema revision must be positive")
        _confidence(self.confidence, "application confidence")
        _require_unique(tuple(item.port_ref for item in self.bindings), f"bindings of {self.application_ref}")

    def binding(self, port_ref: str) -> ApplicationBinding | None:
        return next((item for item in self.bindings if item.port_ref == port_ref), None)

@dataclass(frozen=True, slots=True)
class ScopeRelation:
    scope_relation_ref: str
    operator_application_ref: str
    scoped_ref: FillerRef
    scope_kind: ScopeKind
    order: int = 0
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.scope_relation_ref, "scope_relation_ref")
        _require_ref(self.operator_application_ref, "operator_application_ref")

@dataclass(frozen=True, slots=True)
class CoordinationGroup:
    group_ref: str
    coordination_kind: CoordinationKind
    members: tuple[FillerRef, ...]
    scope_ref: str = "local"
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.group_ref, "group_ref")
        _require_ref(self.scope_ref, "scope_ref")
        if len(self.members) < 2:
            raise ValueError("coordination requires at least two members")
        _require_unique(tuple(_filler_key(item) for item in self.members), f"members of {self.group_ref}")

@dataclass(frozen=True, slots=True)
class PropositionReferent:
    referent: Referent
    content_refs: tuple[FillerRef, ...]
    context_ref: str
    polarity: Polarity = Polarity.POSITIVE
    modality_application_refs: tuple[str, ...] = ()
    attribution_refs: tuple[str, ...] = ()
    valid_time_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.referent.storage_kind != StorageKind.PROPOSITION:
            raise ValueError("proposition referent must use proposition storage kind")
        _require_ref(self.context_ref, "context_ref")
        if not self.content_refs:
            raise ValueError("proposition requires truth-evaluable content")
        allowed = {PortFillerClass.SEMANTIC_APPLICATION, PortFillerClass.COORDINATION_GROUP}
        if any(item.filler_class not in allowed for item in self.content_refs):
            raise ValueError("proposition content must reference applications or coordination groups")
        _require_unique(tuple(_filler_key(item) for item in self.content_refs), f"content of {self.proposition_ref}")

    @property
    def proposition_ref(self) -> str:
        return self.referent.referent_ref

@dataclass(frozen=True, slots=True)
class ClaimOccurrence:
    referent: Referent
    claimant_ref: str
    audience_refs: tuple[str, ...]
    proposition_ref: str
    claim_force: ClaimForce
    source_context_ref: str
    reported_context_ref: str
    time_ref: str | None = None
    certainty_expression_ref: str | None = None
    evidence_offered_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.referent.storage_kind != StorageKind.EVENT_OCCURRENCE:
            raise ValueError("claim occurrence must use event_occurrence storage kind")
        for value, label in (
            (self.claimant_ref, "claimant_ref"),
            (self.proposition_ref, "proposition_ref"),
            (self.source_context_ref, "source_context_ref"),
            (self.reported_context_ref, "reported_context_ref"),
        ):
            _require_ref(value, label)
        _require_unique(self.audience_refs, f"audiences of {self.claim_ref}")
        if self.source_context_ref == self.reported_context_ref:
            raise ValueError("claim content must remain in a source-attributed context")

    @property
    def claim_ref(self) -> str:
        return self.referent.referent_ref

@dataclass(frozen=True, slots=True)
class EventOccurrence:
    referent: Referent
    event_schema_ref: str
    event_schema_revision: int
    participant_application_ref: str
    context_ref: str
    occurrence_status: OccurrenceStatus = OccurrenceStatus.MENTIONED
    time_ref: str | None = None
    place_ref: str | None = None
    cause_refs: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    admission_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.referent.storage_kind != StorageKind.EVENT_OCCURRENCE:
            raise ValueError("event occurrence must use event_occurrence storage kind")
        for value, label in (
            (self.event_schema_ref, "event_schema_ref"),
            (self.participant_application_ref, "participant_application_ref"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        if self.event_schema_revision < 1:
            raise ValueError("event schema revision must be positive")
        _require_unique(self.cause_refs, f"causes of {self.event_ref}")
        _require_unique(self.result_refs, f"results of {self.event_ref}")
        _require_unique(self.admission_refs, f"admissions of {self.event_ref}")

    @property
    def event_ref(self) -> str:
        return self.referent.referent_ref

@dataclass(frozen=True, slots=True)
class StateDelta:
    delta_ref: str
    trigger_ref: str
    holder_ref: str
    dimension_ref: str
    operation: ChangeOperation
    context_ref: str
    effective_time_ref: str
    dimension_revision: int = 1
    from_value_ref: str | None = None
    from_value_revision: int | None = None
    to_value_ref: str | None = None
    to_value_revision: int | None = None
    magnitude_ref: str | None = None
    duration_ref: str | None = None
    confidence: float = 1.0
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.delta_ref, "delta_ref"),
            (self.trigger_ref, "trigger_ref"),
            (self.holder_ref, "holder_ref"),
            (self.dimension_ref, "dimension_ref"),
            (self.context_ref, "context_ref"),
            (self.effective_time_ref, "effective_time_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.confidence, "state-delta confidence")
        if self.dimension_revision < 1:
            raise ValueError("state-delta dimension revision must be positive")
        for value_ref, revision, label in (
            (self.from_value_ref, self.from_value_revision, "from value"),
            (self.to_value_ref, self.to_value_revision, "to value"),
        ):
            if value_ref is None and revision is not None:
                raise ValueError(f"{label} revision requires a value reference")
            if revision is not None and revision < 1:
                raise ValueError(f"{label} revision must be positive")
        if not self.proof_refs:
            raise ValueError("state delta requires proof references")
        if self.operation not in _STATE_DELTA_OPERATIONS:
            raise ValueError(
                f"{self.operation.value} is not a state-dimension operation; "
                "use a relation or capability delta"
            )
        if self.operation in {ChangeOperation.SET, ChangeOperation.ACTIVATE, ChangeOperation.RESTORE} and self.to_value_ref is None:
            raise ValueError(f"{self.operation.value} state delta requires to_value_ref")
        if self.operation in {ChangeOperation.INCREASE, ChangeOperation.DECREASE} and self.magnitude_ref is None and self.to_value_ref is None:
            raise ValueError("scalar delta requires magnitude_ref or to_value_ref")

@dataclass(frozen=True, slots=True)
class CapabilityDelta:
    delta_ref: str
    trigger_ref: str
    holder_ref: str
    action_schema_ref: str
    prior_status: CapabilityStatus
    new_status: CapabilityStatus
    context_ref: str
    effective_time_ref: str
    dependency_ref: str
    action_schema_revision: int = 1
    confidence: float = 1.0
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.delta_ref, "delta_ref"),
            (self.trigger_ref, "trigger_ref"),
            (self.holder_ref, "holder_ref"),
            (self.action_schema_ref, "action_schema_ref"),
            (self.context_ref, "context_ref"),
            (self.effective_time_ref, "effective_time_ref"),
            (self.dependency_ref, "dependency_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.confidence, "capability-delta confidence")
        if self.action_schema_revision < 1:
            raise ValueError("capability action schema revision must be positive")
        if not self.proof_refs:
            raise ValueError("capability delta requires proof references")
        if self.prior_status == self.new_status:
            raise ValueError("capability delta must change status")

@dataclass(frozen=True, slots=True)
class ImpactAssessment:
    assessment_ref: str
    source_event_or_state_ref: str
    affected_ref: str
    stakeholder_ref: str
    affected_facet_refs: tuple[str, ...]
    direction: ChangeOperation
    valence: Valence
    context_ref: str
    reversibility: Reversibility = Reversibility.UNKNOWN
    magnitude_ref: str | None = None
    duration_ref: str | None = None
    confidence: float = 1.0
    importance_ref: str | None = None
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.assessment_ref, "assessment_ref"),
            (self.source_event_or_state_ref, "source_event_or_state_ref"),
            (self.affected_ref, "affected_ref"),
            (self.stakeholder_ref, "stakeholder_ref"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.confidence, "impact confidence")
        _require_unique(self.affected_facet_refs, f"affected facets of {self.assessment_ref}")
        if not self.affected_facet_refs:
            raise ValueError("impact assessment requires at least one affected facet")
        if not self.proof_refs:
            raise ValueError("impact assessment requires proof references")

@dataclass(frozen=True, slots=True)
class ImportanceAssessment:
    assessment_ref: str
    subject_ref: str
    stakeholder_ref: str
    context_ref: str
    score: float
    importance_class: ImportanceClass
    evidence_refs: tuple[str, ...]
    reasons: tuple[str, ...]
    valid_time_ref: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.assessment_ref, "assessment_ref"),
            (self.subject_ref, "subject_ref"),
            (self.stakeholder_ref, "stakeholder_ref"),
            (self.context_ref, "context_ref"),
        ):
            _require_ref(value, label)
        _confidence(self.score, "importance score")
        _require_unique(self.evidence_refs, f"importance evidence of {self.assessment_ref}")
        _require_unique(self.reasons, f"importance reasons of {self.assessment_ref}")
        if not self.evidence_refs or not self.reasons:
            raise ValueError("importance assessment requires evidence and reasons")

def canonical_data(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: canonical_data(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): canonical_data(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [canonical_data(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((canonical_data(item) for item in value), key=_canonical_sort_key)
    return value

def fingerprint(prefix: str, value: Any, length: int = 32) -> str:
    payload = json.dumps(canonical_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()[:length]}"

def _filler_key(value: PortFiller) -> tuple[str, str]:
    if isinstance(value, FillerRef):
        return value.filler_class.value, value.ref
    return PortFillerClass.QUOTED_LITERAL.value, value.literal_ref

def _confidence(value: float, label: str) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be within [0, 1]")

def _require_ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")

def _require_unique(values: Iterable[Any], label: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"duplicate {label}")

def _canonical_sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


CANONICAL_RECORD_EXPORTS = ('ApplicationBinding', 'CapabilityDelta', 'CapabilityStatus', 'ChangeOperation', 'ClaimForce', 'ClaimOccurrence', 'CoordinationGroup', 'CoordinationKind', 'EventOccurrence', 'FillerRef', 'IdentityStatus', 'ImpactAssessment', 'ImportanceAssessment', 'ImportanceClass', 'OccurrenceStatus', 'Polarity', 'PropositionReferent', 'QuotedLiteral', 'Referent', 'Reversibility', 'ScopeKind', 'ScopeRelation', 'SemanticApplication', 'SemanticVariable', 'StateDelta', 'StrEnum', 'Valence', 'canonical_data', 'fingerprint')
