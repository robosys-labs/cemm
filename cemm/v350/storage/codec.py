"""Typed record codec registry used by the compiler and overlay store."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from ..schema.codec import record_from_document as schema_record_from_document
from ..schema.codec import record_to_document as schema_record_to_document
from ..schema.model import FacetEntitlement, MeaningSchema, canonical_data, semantic_fingerprint
from ..language.codec import (
    construction_from_document,
    form_sense_link_from_document,
    language_form_from_document,
    language_pack_from_document,
    language_record_to_document,
    lexical_sense_from_document,
)
from ..language.model import (
    ConstructionRecord,
    FormSenseLinkRecord,
    LanguageFormRecord,
    LanguagePackRecord,
    LexicalSenseRecord,
)
from ..uol.codec import (
    application_from_document,
    capability_delta_from_document,
    claim_from_document,
    event_from_document,
    impact_from_document,
    importance_from_document,
    proposition_from_document,
    referent_from_document,
    state_delta_from_document,
    uol_to_document,
)
from ..uol.model import (
    CapabilityDelta,
    ClaimOccurrence,
    EventOccurrence,
    ImpactAssessment,
    ImportanceAssessment,
    PropositionReferent,
    Referent,
    SemanticApplication,
    StateDelta,
)
from .model import (
    AssertionStatus,
    AssignmentStatus,
    CapabilityInstance,
    ClaimRecord,
    ConditionTruth,
    DefaultRuleRecord,
    DependencyEdge,
    EvidenceRecord,
    IdentityFacetRecord,
    KnowledgeRecord,
    KnowledgeStatus,
    MaterializedViewRecord,
    RecordKind,
    ReferentTypeAssertion,
    StateAssignment,
)


class RecordDecodeError(ValueError):
    pass


Decoder = Callable[[Mapping[str, Any]], Any]
Encoder = Callable[[Any], Mapping[str, Any]]


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise RecordDecodeError("expected an array, not one string")
    return tuple(str(item) for item in value)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RecordDecodeError(f"{label} must be an object")
    return value


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _dataclass_document(value: Any) -> Mapping[str, Any]:
    if not is_dataclass(value):
        raise TypeError(f"record is not a dataclass: {type(value)!r}")
    return canonical_data(value)


def _evidence(value: Mapping[str, Any]) -> EvidenceRecord:
    data = dict(value)
    try:
        return EvidenceRecord(
            evidence_ref=str(data["evidence_ref"]),
            source_ref=str(data["source_ref"]),
            confidence=float(data["confidence"]),
            lineage_ref=str(data["lineage_ref"]),
            context_ref=str(data.get("context_ref", "actual")),
            observed_at=None if data.get("observed_at") is None else str(data["observed_at"]),
            span_start=None if data.get("span_start") is None else int(data["span_start"]),
            span_end=None if data.get("span_end") is None else int(data["span_end"]),
            permission_ref=str(data.get("permission_ref", "conversation")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _type_assertion(value: Mapping[str, Any]) -> ReferentTypeAssertion:
    data = dict(value)
    try:
        return ReferentTypeAssertion(
            assertion_ref=str(data["assertion_ref"]),
            referent_ref=str(data["referent_ref"]),
            type_schema_ref=str(data["type_schema_ref"]),
            type_revision=int(data["type_revision"]),
            status=AssertionStatus(data["status"]),
            confidence=float(data["confidence"]),
            context_ref=str(data["context_ref"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            source_refs=_tuple_str(data.get("source_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
            permission_ref=str(data.get("permission_ref", "conversation")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _identity_facet(value: Mapping[str, Any]) -> IdentityFacetRecord:
    data = dict(value)
    try:
        return IdentityFacetRecord(
            identity_facet_ref=str(data["identity_facet_ref"]),
            referent_ref=str(data["referent_ref"]),
            facet_schema_ref=str(data["facet_schema_ref"]),
            normalized_value=str(data["normalized_value"]),
            anchor_ref=None if data.get("anchor_ref") is None else str(data["anchor_ref"]),
            confidence=float(data.get("confidence", 1.0)),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            context_ref=str(data.get("context_ref", "actual")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _claim_record(value: Mapping[str, Any]) -> ClaimRecord:
    data = dict(value)
    try:
        return ClaimRecord(
            claim_record_ref=str(data["claim_record_ref"]),
            claim_occurrence_ref=str(data["claim_occurrence_ref"]),
            proposition_ref=str(data["proposition_ref"]),
            source_ref=str(data["source_ref"]),
            source_context_ref=str(data["source_context_ref"]),
            reported_context_ref=str(data["reported_context_ref"]),
            commitment_strength=float(data["commitment_strength"]),
            permission_ref=str(data.get("permission_ref", "conversation")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            superseded_by=None if data.get("superseded_by") is None else str(data["superseded_by"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _knowledge(value: Mapping[str, Any]) -> KnowledgeRecord:
    data = dict(value)
    try:
        return KnowledgeRecord(
            knowledge_ref=str(data["knowledge_ref"]),
            proposition_ref=str(data["proposition_ref"]),
            truth_status=KnowledgeStatus(data["truth_status"]),
            confidence=float(data["confidence"]),
            context_ref=str(data["context_ref"]),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            permission_ref=str(data.get("permission_ref", "conversation")),
            sensitivity=str(data.get("sensitivity", "normal")),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            support_lineage_refs=_tuple_str(data.get("support_lineage_refs")),
            derivation_refs=_tuple_str(data.get("derivation_refs")),
            superseded_by=None if data.get("superseded_by") is None else str(data["superseded_by"]),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _state_assignment(value: Mapping[str, Any]) -> StateAssignment:
    data = dict(value)
    try:
        return StateAssignment(
            assignment_ref=str(data["assignment_ref"]),
            holder_ref=str(data["holder_ref"]),
            dimension_ref=str(data["dimension_ref"]),
            dimension_revision=int(data["dimension_revision"]),
            value_ref=str(data["value_ref"]),
            value_revision=int(data["value_revision"]),
            status=AssignmentStatus(data["status"]),
            context_ref=str(data["context_ref"]),
            confidence=float(data["confidence"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
            source_refs=_tuple_str(data.get("source_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _capability(value: Mapping[str, Any]) -> CapabilityInstance:
    from ..uol.model import CapabilityStatus

    data = dict(value)
    try:
        return CapabilityInstance(
            capability_ref=str(data["capability_ref"]),
            holder_ref=str(data["holder_ref"]),
            action_schema_ref=str(data["action_schema_ref"]),
            action_schema_revision=int(data["action_schema_revision"]),
            status=CapabilityStatus(data["status"]),
            confidence=float(data["confidence"]),
            context_ref=str(data["context_ref"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            dependency_refs=_tuple_str(data.get("dependency_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _default_rule(value: Mapping[str, Any]) -> DefaultRuleRecord:
    from ..schema.model import SchemaLifecycleStatus

    data = dict(value)
    try:
        return DefaultRuleRecord(
            rule_ref=str(data["rule_ref"]),
            target_facet_ref=str(data["target_facet_ref"]),
            expected_dimension_ref=None if data.get("expected_dimension_ref") is None else str(data["expected_dimension_ref"]),
            expected_dimension_revision=None if data.get("expected_dimension_revision") is None else int(data["expected_dimension_revision"]),
            expected_value_ref=None if data.get("expected_value_ref") is None else str(data["expected_value_ref"]),
            expected_value_revision=None if data.get("expected_value_revision") is None else int(data["expected_value_revision"]),
            holder_type_refs=_tuple_str(data.get("holder_type_refs")),
            condition_refs=_tuple_str(data.get("condition_refs")),
            defeater_refs=_tuple_str(data.get("defeater_refs")),
            context_constraints=_tuple_str(data.get("context_constraints")),
            temporal_constraints=_tuple_str(data.get("temporal_constraints")),
            priority=int(data.get("priority", 0)),
            confidence=float(data.get("confidence", 0.5)),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value)),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            scope_ref=str(data.get("scope_ref", "global")),
            permission_ref=str(data.get("permission_ref", "public")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _dependency(value: Mapping[str, Any]) -> DependencyEdge:
    data = dict(value)
    try:
        prerequisite_kind = data.get("prerequisite_kind")
        return DependencyEdge(
            dependency_ref=str(data["dependency_ref"]),
            dependent_kind=RecordKind(data["dependent_kind"]),
            dependent_ref=str(data["dependent_ref"]),
            dependent_revision=int(data["dependent_revision"]),
            prerequisite_kind=None if prerequisite_kind is None else RecordKind(prerequisite_kind),
            prerequisite_ref=str(data["prerequisite_ref"]),
            prerequisite_revision=None if data.get("prerequisite_revision") is None else int(data["prerequisite_revision"]),
            prerequisite_fingerprint=None if data.get("prerequisite_fingerprint") is None else str(data["prerequisite_fingerprint"]),
            dependency_kind=str(data.get("dependency_kind", "semantic")),
            active=bool(data.get("active", True)),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _view(value: Mapping[str, Any]) -> MaterializedViewRecord:
    data = dict(value)
    try:
        return MaterializedViewRecord(
            view_ref=str(data["view_ref"]),
            view_kind=str(data["view_kind"]),
            subject_ref=str(data["subject_ref"]),
            context_ref=str(data["context_ref"]),
            payload=dict(data.get("payload", {})),
            dependency_refs=_tuple_str(data.get("dependency_refs")),
            dependency_fingerprint=str(data["dependency_fingerprint"]),
            snapshot_revision=int(data["snapshot_revision"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


_DECODERS: Mapping[RecordKind, Decoder] = {
    RecordKind.SCHEMA: schema_record_from_document,
    RecordKind.FACET_ENTITLEMENT: schema_record_from_document,
    RecordKind.REFERENT: referent_from_document,
    RecordKind.TYPE_ASSERTION: _type_assertion,
    RecordKind.IDENTITY_FACET: _identity_facet,
    RecordKind.SEMANTIC_APPLICATION: application_from_document,
    RecordKind.PROPOSITION: proposition_from_document,
    RecordKind.CLAIM_OCCURRENCE: claim_from_document,
    RecordKind.CLAIM_RECORD: _claim_record,
    RecordKind.EVENT_OCCURRENCE: event_from_document,
    RecordKind.STATE_ASSIGNMENT: _state_assignment,
    RecordKind.STATE_DELTA: state_delta_from_document,
    RecordKind.CAPABILITY_INSTANCE: _capability,
    RecordKind.CAPABILITY_DELTA: capability_delta_from_document,
    RecordKind.KNOWLEDGE: _knowledge,
    RecordKind.EVIDENCE: _evidence,
    RecordKind.IMPACT_ASSESSMENT: impact_from_document,
    RecordKind.IMPORTANCE_ASSESSMENT: importance_from_document,
    RecordKind.DEFAULT_RULE: _default_rule,
    RecordKind.DEPENDENCY: _dependency,
    RecordKind.LANGUAGE_PACK: language_pack_from_document,
    RecordKind.LANGUAGE_FORM: language_form_from_document,
    RecordKind.LEXICAL_SENSE: lexical_sense_from_document,
    RecordKind.FORM_SENSE_LINK: form_sense_link_from_document,
    RecordKind.CONSTRUCTION: construction_from_document,
    RecordKind.MATERIALIZED_VIEW: _view,
}


def decode_record(record_kind: RecordKind | str, value: Mapping[str, Any]) -> Any:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    try:
        decoder = _DECODERS[resolved]
        record = decoder(value)
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, RecordDecodeError):
            raise
        raise RecordDecodeError(f"{resolved.value}: {exc}") from exc
    validate_record_kind(resolved, record)
    return record


def encode_record(record_kind: RecordKind | str, record: Any) -> dict[str, Any]:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    validate_record_kind(resolved, record)
    if resolved in {RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT}:
        document = schema_record_to_document(record)
    elif resolved in {
        RecordKind.LANGUAGE_PACK,
        RecordKind.LANGUAGE_FORM,
        RecordKind.LEXICAL_SENSE,
        RecordKind.FORM_SENSE_LINK,
        RecordKind.CONSTRUCTION,
    }:
        document = language_record_to_document(record)
    elif resolved in {
        RecordKind.REFERENT,
        RecordKind.SEMANTIC_APPLICATION,
        RecordKind.PROPOSITION,
        RecordKind.CLAIM_OCCURRENCE,
        RecordKind.EVENT_OCCURRENCE,
        RecordKind.STATE_DELTA,
        RecordKind.CAPABILITY_DELTA,
        RecordKind.IMPACT_ASSESSMENT,
        RecordKind.IMPORTANCE_ASSESSMENT,
    }:
        document = uol_to_document(record)
    else:
        document = dict(_dataclass_document(record))
    return dict(document)


def validate_record_kind(record_kind: RecordKind, record: Any) -> None:
    expected: Mapping[RecordKind, tuple[type[Any], ...]] = {
        RecordKind.SCHEMA: (MeaningSchema,),
        RecordKind.FACET_ENTITLEMENT: (FacetEntitlement,),
        RecordKind.REFERENT: (Referent,),
        RecordKind.TYPE_ASSERTION: (ReferentTypeAssertion,),
        RecordKind.IDENTITY_FACET: (IdentityFacetRecord,),
        RecordKind.SEMANTIC_APPLICATION: (SemanticApplication,),
        RecordKind.PROPOSITION: (PropositionReferent,),
        RecordKind.CLAIM_OCCURRENCE: (ClaimOccurrence,),
        RecordKind.CLAIM_RECORD: (ClaimRecord,),
        RecordKind.EVENT_OCCURRENCE: (EventOccurrence,),
        RecordKind.STATE_ASSIGNMENT: (StateAssignment,),
        RecordKind.STATE_DELTA: (StateDelta,),
        RecordKind.CAPABILITY_INSTANCE: (CapabilityInstance,),
        RecordKind.CAPABILITY_DELTA: (CapabilityDelta,),
        RecordKind.KNOWLEDGE: (KnowledgeRecord,),
        RecordKind.EVIDENCE: (EvidenceRecord,),
        RecordKind.IMPACT_ASSESSMENT: (ImpactAssessment,),
        RecordKind.IMPORTANCE_ASSESSMENT: (ImportanceAssessment,),
        RecordKind.DEFAULT_RULE: (DefaultRuleRecord,),
        RecordKind.DEPENDENCY: (DependencyEdge,),
        RecordKind.LANGUAGE_PACK: (LanguagePackRecord,),
        RecordKind.LANGUAGE_FORM: (LanguageFormRecord,),
        RecordKind.LEXICAL_SENSE: (LexicalSenseRecord,),
        RecordKind.FORM_SENSE_LINK: (FormSenseLinkRecord,),
        RecordKind.CONSTRUCTION: (ConstructionRecord,),
        RecordKind.MATERIALIZED_VIEW: (MaterializedViewRecord,),
    }
    if not isinstance(record, expected[record_kind]):
        names = ", ".join(item.__name__ for item in expected[record_kind])
        raise TypeError(f"{record_kind.value} requires {names}, got {type(record).__name__}")
    if record_kind == RecordKind.SCHEMA and isinstance(record, FacetEntitlement):
        raise TypeError("facet entitlement must use facet_entitlement record kind")


def record_ref(record_kind: RecordKind | str, record: Any) -> str:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    validate_record_kind(resolved, record)
    attributes: Mapping[RecordKind, str] = {
        RecordKind.SCHEMA: "schema_ref",
        RecordKind.FACET_ENTITLEMENT: "entitlement_ref",
        RecordKind.REFERENT: "referent_ref",
        RecordKind.TYPE_ASSERTION: "assertion_ref",
        RecordKind.IDENTITY_FACET: "identity_facet_ref",
        RecordKind.SEMANTIC_APPLICATION: "application_ref",
        RecordKind.PROPOSITION: "proposition_ref",
        RecordKind.CLAIM_OCCURRENCE: "claim_ref",
        RecordKind.CLAIM_RECORD: "claim_record_ref",
        RecordKind.EVENT_OCCURRENCE: "event_ref",
        RecordKind.STATE_ASSIGNMENT: "assignment_ref",
        RecordKind.STATE_DELTA: "delta_ref",
        RecordKind.CAPABILITY_INSTANCE: "capability_ref",
        RecordKind.CAPABILITY_DELTA: "delta_ref",
        RecordKind.KNOWLEDGE: "knowledge_ref",
        RecordKind.EVIDENCE: "evidence_ref",
        RecordKind.IMPACT_ASSESSMENT: "assessment_ref",
        RecordKind.IMPORTANCE_ASSESSMENT: "assessment_ref",
        RecordKind.DEFAULT_RULE: "rule_ref",
        RecordKind.DEPENDENCY: "dependency_ref",
        RecordKind.LANGUAGE_PACK: "pack_ref",
        RecordKind.LANGUAGE_FORM: "form_ref",
        RecordKind.LEXICAL_SENSE: "sense_ref",
        RecordKind.FORM_SENSE_LINK: "link_ref",
        RecordKind.CONSTRUCTION: "construction_ref",
        RecordKind.MATERIALIZED_VIEW: "view_ref",
    }
    return str(getattr(record, attributes[resolved]))


def record_revision(record_kind: RecordKind | str, record: Any, fallback: int = 1) -> int:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    validate_record_kind(resolved, record)
    if resolved in {
        RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT,
        RecordKind.REFERENT, RecordKind.DEFAULT_RULE,
        RecordKind.LANGUAGE_PACK, RecordKind.LANGUAGE_FORM,
        RecordKind.LEXICAL_SENSE, RecordKind.FORM_SENSE_LINK,
        RecordKind.CONSTRUCTION,
    }:
        return int(getattr(record, "revision"))
    if resolved == RecordKind.PROPOSITION:
        return int(record.referent.revision)
    if resolved in {RecordKind.CLAIM_OCCURRENCE, RecordKind.EVENT_OCCURRENCE}:
        return int(record.referent.revision)
    return int(fallback)


def record_context(record_kind: RecordKind | str, record: Any) -> str | None:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    if hasattr(record, "context_ref"):
        return str(getattr(record, "context_ref"))
    if resolved == RecordKind.REFERENT:
        return str(record.context_refs[0]) if record.context_refs else None
    if resolved == RecordKind.PROPOSITION:
        return str(record.context_ref)
    if resolved == RecordKind.CLAIM_OCCURRENCE:
        return str(record.source_context_ref)
    return None


def record_lifecycle(record_kind: RecordKind | str, record: Any) -> str | None:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    if resolved in {
        RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT, RecordKind.DEFAULT_RULE,
        RecordKind.LANGUAGE_PACK, RecordKind.LANGUAGE_FORM, RecordKind.LEXICAL_SENSE,
        RecordKind.FORM_SENSE_LINK, RecordKind.CONSTRUCTION,
    }:
        return str(record.lifecycle_status.value)
    if hasattr(record, "status"):
        return str(_enum_value(getattr(record, "status")))
    if resolved == RecordKind.EVENT_OCCURRENCE:
        return str(record.occurrence_status.value)
    return None


def record_permission(record_kind: RecordKind | str, record: Any) -> str | None:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    if hasattr(record, "permission_ref"):
        return str(getattr(record, "permission_ref"))
    if resolved == RecordKind.PROPOSITION:
        return str(record.referent.permission_ref)
    if resolved in {RecordKind.CLAIM_OCCURRENCE, RecordKind.EVENT_OCCURRENCE}:
        return str(record.referent.permission_ref)
    return None


def record_interval(record_kind: RecordKind | str, record: Any) -> tuple[str | None, str | None]:
    del record_kind
    return getattr(record, "valid_from", None), getattr(record, "valid_to", None)


def record_fingerprints(record_kind: RecordKind | str, record: Any) -> tuple[str, str]:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    document = encode_record(resolved, record)
    if resolved in {RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT}:
        return record.content_fingerprint, record.record_fingerprint
    content_document = dict(document)
    for key in (
        "evidence_refs", "proof_refs", "provenance_refs", "source_refs", "metadata",
        "confidence", "revision", "superseded_by",
    ):
        content_document.pop(key, None)
    return (
        semantic_fingerprint(f"{resolved.value}-content", content_document, 64),
        semantic_fingerprint(f"{resolved.value}-record", document, 64),
    )
