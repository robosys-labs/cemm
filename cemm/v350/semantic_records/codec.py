"""Deterministic codecs for canonical v3.5 semantic/durable record contracts.
Legacy cognitive graph serialization is intentionally absent.
"""
from __future__ import annotations

from typing import Any, Mapping
from ..schema.model import OpenBindingPurpose, PortFillerClass, SchemaClass, StorageKind, UseOperation
from .model import (
    ApplicationBinding,
    CapabilityDelta,
    CapabilityStatus,
    ChangeOperation,
    ClaimForce,
    ClaimOccurrence,
    CoordinationGroup,
    EventOccurrence,
    FillerRef,
    IdentityStatus,
    ImpactAssessment,
    ImportanceAssessment,
    ImportanceClass,
    OccurrenceStatus,
    Polarity,
    PropositionReferent,
    QuotedLiteral,
    Referent,
    Reversibility,
    ScopeRelation,
    SemanticApplication,
    StateDelta,
    Valence,
    canonical_data,
)

class SemanticRecordDecodeError(ValueError):
    pass

def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise SemanticRecordDecodeError("expected an array of references, not one string")
    return tuple(str(item) for item in value)

def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SemanticRecordDecodeError(f"{label} must be an object")
    return value

def filler_from_document(value: Mapping[str, Any]) -> FillerRef | QuotedLiteral:
    data = dict(value)
    try:
        filler_class = PortFillerClass(data.get("filler_class", PortFillerClass.REFERENT.value))
        if filler_class == PortFillerClass.QUOTED_LITERAL:
            return QuotedLiteral(
                literal_ref=str(data["literal_ref"]),
                surface=str(data.get("surface", "")),
                language_tag=str(data.get("language_tag", "und")),
                evidence_refs=_tuple_str(data.get("evidence_refs")),
            )
        return FillerRef(filler_class=filler_class, ref=str(data["ref"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def filler_to_document(value: FillerRef | QuotedLiteral) -> dict[str, Any]:
    if isinstance(value, QuotedLiteral):
        return {
            "filler_class": PortFillerClass.QUOTED_LITERAL.value,
            "literal_ref": value.literal_ref,
            "surface": value.surface,
            "language_tag": value.language_tag,
            "evidence_refs": list(value.evidence_refs),
        }
    return {"filler_class": value.filler_class.value, "ref": value.ref}

def referent_from_document(value: Mapping[str, Any]) -> Referent:
    data = dict(value)
    try:
        return Referent(
            referent_ref=str(data["referent_ref"]),
            storage_kind=StorageKind(data.get("storage_kind", StorageKind.ORDINARY.value)),
            identity_status=IdentityStatus(data.get("identity_status", IdentityStatus.CANDIDATE.value)),
            type_refs=_tuple_str(data.get("type_refs")),
            identity_facet_refs=_tuple_str(data.get("identity_facet_refs")),
            scope_ref=str(data.get("scope_ref", "global")),
            context_refs=_tuple_str(data.get("context_refs", ("actual",))),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
            provenance_refs=_tuple_str(data.get("provenance_refs")),
            permission_ref=str(data.get("permission_ref", "conversation")),
            revision=int(data.get("revision", 1)),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def binding_from_document(value: Mapping[str, Any]) -> ApplicationBinding:
    data = dict(value)
    try:
        purpose = data.get("open_binding_purpose")
        return ApplicationBinding(
            port_ref=str(data["port_ref"]),
            fillers=tuple(filler_from_document(_mapping(item, "binding filler")) for item in data.get("fillers", ())),
            confidence=float(data.get("confidence", 1.0)),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            assumptions=_tuple_str(data.get("assumptions")),
            ordered=bool(data.get("ordered", False)),
            open_binding_purpose=None if purpose is None else OpenBindingPurpose(str(purpose)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def application_from_document(value: Mapping[str, Any]) -> SemanticApplication:
    data = dict(value)
    try:
        return SemanticApplication(
            application_ref=str(data["application_ref"]),
            schema_ref=str(data["schema_ref"]),
            schema_revision=int(data["schema_revision"]),
            bindings=tuple(binding_from_document(_mapping(item, "application binding")) for item in data.get("bindings", ())),
            context_ref=str(data["context_ref"]),
            use_operation=UseOperation(data.get("use_operation", UseOperation.COMPOSE.value)),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
            polarity=Polarity(data.get("polarity", Polarity.POSITIVE.value)),
            confidence=float(data.get("confidence", 1.0)),
            assumptions=_tuple_str(data.get("assumptions")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def proposition_from_document(value: Mapping[str, Any]) -> PropositionReferent:
    data = dict(value)
    try:
        content = tuple(filler_from_document(_mapping(item, "proposition content")) for item in data.get("content_refs", ()))
        if not all(isinstance(item, FillerRef) for item in content):
            raise SemanticRecordDecodeError("proposition content cannot be quoted literals")
        return PropositionReferent(
            referent=referent_from_document(_mapping(data["referent"], "proposition referent")),
            content_refs=tuple(item for item in content if isinstance(item, FillerRef)),
            context_ref=str(data["context_ref"]),
            polarity=Polarity(data.get("polarity", Polarity.POSITIVE.value)),
            modality_application_refs=_tuple_str(data.get("modality_application_refs")),
            attribution_refs=_tuple_str(data.get("attribution_refs")),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, SemanticRecordDecodeError):
            raise
        raise SemanticRecordDecodeError(str(exc)) from exc

def claim_from_document(value: Mapping[str, Any]) -> ClaimOccurrence:
    data = dict(value)
    try:
        return ClaimOccurrence(
            referent=referent_from_document(_mapping(data["referent"], "claim referent")),
            claimant_ref=str(data["claimant_ref"]),
            audience_refs=_tuple_str(data.get("audience_refs")),
            proposition_ref=str(data["proposition_ref"]),
            claim_force=ClaimForce(data["claim_force"]),
            source_context_ref=str(data["source_context_ref"]),
            reported_context_ref=str(data["reported_context_ref"]),
            time_ref=None if data.get("time_ref") is None else str(data["time_ref"]),
            certainty_expression_ref=None if data.get("certainty_expression_ref") is None else str(data["certainty_expression_ref"]),
            evidence_offered_refs=_tuple_str(data.get("evidence_offered_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def event_from_document(value: Mapping[str, Any]) -> EventOccurrence:
    data = dict(value)
    try:
        return EventOccurrence(
            referent=referent_from_document(_mapping(data["referent"], "event referent")),
            event_schema_ref=str(data["event_schema_ref"]),
            event_schema_revision=int(data["event_schema_revision"]),
            participant_application_ref=str(data["participant_application_ref"]),
            context_ref=str(data["context_ref"]),
            occurrence_status=OccurrenceStatus(data.get("occurrence_status", OccurrenceStatus.MENTIONED.value)),
            time_ref=None if data.get("time_ref") is None else str(data["time_ref"]),
            place_ref=None if data.get("place_ref") is None else str(data["place_ref"]),
            cause_refs=_tuple_str(data.get("cause_refs")),
            result_refs=_tuple_str(data.get("result_refs")),
            provenance_refs=_tuple_str(data.get("provenance_refs")),
            admission_refs=_tuple_str(data.get("admission_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def state_delta_from_document(value: Mapping[str, Any]) -> StateDelta:
    data = dict(value)
    try:
        return StateDelta(
            delta_ref=str(data["delta_ref"]),
            trigger_ref=str(data["trigger_ref"]),
            holder_ref=str(data["holder_ref"]),
            dimension_ref=str(data["dimension_ref"]),
            operation=ChangeOperation(data["operation"]),
            context_ref=str(data["context_ref"]),
            effective_time_ref=str(data["effective_time_ref"]),
            dimension_revision=int(data.get("dimension_revision", 1)),
            from_value_ref=None if data.get("from_value_ref") is None else str(data["from_value_ref"]),
            from_value_revision=None if data.get("from_value_revision") is None else int(data["from_value_revision"]),
            to_value_ref=None if data.get("to_value_ref") is None else str(data["to_value_ref"]),
            to_value_revision=None if data.get("to_value_revision") is None else int(data["to_value_revision"]),
            magnitude_ref=None if data.get("magnitude_ref") is None else str(data["magnitude_ref"]),
            duration_ref=None if data.get("duration_ref") is None else str(data["duration_ref"]),
            confidence=float(data.get("confidence", 1.0)),
            proof_refs=_tuple_str(data.get("proof_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def capability_delta_from_document(value: Mapping[str, Any]) -> CapabilityDelta:
    data = dict(value)
    try:
        return CapabilityDelta(
            delta_ref=str(data["delta_ref"]),
            trigger_ref=str(data["trigger_ref"]),
            holder_ref=str(data["holder_ref"]),
            action_schema_ref=str(data["action_schema_ref"]),
            prior_status=CapabilityStatus(data["prior_status"]),
            new_status=CapabilityStatus(data["new_status"]),
            context_ref=str(data["context_ref"]),
            effective_time_ref=str(data["effective_time_ref"]),
            dependency_ref=str(data["dependency_ref"]),
            action_schema_revision=int(data.get("action_schema_revision", 1)),
            confidence=float(data.get("confidence", 1.0)),
            proof_refs=_tuple_str(data.get("proof_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def impact_from_document(value: Mapping[str, Any]) -> ImpactAssessment:
    data = dict(value)
    try:
        return ImpactAssessment(
            assessment_ref=str(data["assessment_ref"]),
            source_event_or_state_ref=str(data["source_event_or_state_ref"]),
            affected_ref=str(data["affected_ref"]),
            stakeholder_ref=str(data["stakeholder_ref"]),
            affected_facet_refs=_tuple_str(data.get("affected_facet_refs")),
            direction=ChangeOperation(data["direction"]),
            valence=Valence(data["valence"]),
            context_ref=str(data["context_ref"]),
            reversibility=Reversibility(data.get("reversibility", Reversibility.UNKNOWN.value)),
            magnitude_ref=None if data.get("magnitude_ref") is None else str(data["magnitude_ref"]),
            duration_ref=None if data.get("duration_ref") is None else str(data["duration_ref"]),
            confidence=float(data.get("confidence", 1.0)),
            importance_ref=None if data.get("importance_ref") is None else str(data["importance_ref"]),
            proof_refs=_tuple_str(data.get("proof_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def importance_from_document(value: Mapping[str, Any]) -> ImportanceAssessment:
    data = dict(value)
    try:
        return ImportanceAssessment(
            assessment_ref=str(data["assessment_ref"]),
            subject_ref=str(data["subject_ref"]),
            stakeholder_ref=str(data["stakeholder_ref"]),
            context_ref=str(data["context_ref"]),
            score=float(data["score"]),
            importance_class=ImportanceClass(data["importance_class"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            reasons=_tuple_str(data.get("reasons")),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRecordDecodeError(str(exc)) from exc

def semantic_record_to_document(value: Any) -> dict[str, Any]:
    if isinstance(value, (FillerRef, QuotedLiteral)):
        return filler_to_document(value)
    document = canonical_data(value)
    if not isinstance(document, dict):
        raise TypeError(f"unsupported UOL document type: {type(value)!r}")
    if isinstance(value, ApplicationBinding):
        document["fillers"] = [filler_to_document(item) for item in value.fillers]
    elif isinstance(value, SemanticApplication):
        document["bindings"] = [semantic_record_to_document(item) for item in value.bindings]
    elif isinstance(value, CoordinationGroup):
        document["members"] = [filler_to_document(item) for item in value.members]
    elif isinstance(value, PropositionReferent):
        document["referent"] = semantic_record_to_document(value.referent)
        document["content_refs"] = [filler_to_document(item) for item in value.content_refs]
    elif isinstance(value, ClaimOccurrence):
        document["referent"] = semantic_record_to_document(value.referent)
    elif isinstance(value, EventOccurrence):
        document["referent"] = semantic_record_to_document(value.referent)
    elif isinstance(value, ScopeRelation):
        document["scoped_ref"] = filler_to_document(value.scoped_ref)
    return document

