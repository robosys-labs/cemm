"""Deterministic document codec for CEMM v3.5 UOL records.

The codec is intentionally explicit.  It rejects unknown structural values
instead of silently dropping them, and it preserves schema revision pins,
contexts, ordering, proof references, and all orthogonal semantic axes.
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
    CoordinationKind,
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
    ScopeKind,
    ScopeRelation,
    SemanticApplication,
    SemanticVariable,
    StateDelta,
    UOLGraph,
    Valence,
    canonical_data,
)


class UOLDecodeError(ValueError):
    pass


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise UOLDecodeError("expected an array of references, not one string")
    return tuple(str(item) for item in value)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise UOLDecodeError(f"{label} must be an object")
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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


def variable_from_document(value: Mapping[str, Any]) -> SemanticVariable:
    data = dict(value)
    try:
        return SemanticVariable(
            variable_ref=str(data["variable_ref"]),
            expected_schema_classes=frozenset(SchemaClass(item) for item in data.get("expected_schema_classes", ())),
            expected_type_refs=_tuple_str(data.get("expected_type_refs")),
            restriction_refs=_tuple_str(data.get("restriction_refs")),
            projection_ref=None if data.get("projection_ref") is None else str(data["projection_ref"]),
            scope_ref=str(data.get("scope_ref", "local")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise UOLDecodeError(str(exc)) from exc


def coordination_from_document(value: Mapping[str, Any]) -> CoordinationGroup:
    data = dict(value)
    try:
        members = tuple(filler_from_document(_mapping(item, "coordination member")) for item in data.get("members", ()))
        if not all(isinstance(item, FillerRef) for item in members):
            raise UOLDecodeError("coordination members cannot be quoted literals")
        return CoordinationGroup(
            group_ref=str(data["group_ref"]),
            coordination_kind=CoordinationKind(data["coordination_kind"]),
            members=tuple(item for item in members if isinstance(item, FillerRef)),
            scope_ref=str(data.get("scope_ref", "local")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, UOLDecodeError):
            raise
        raise UOLDecodeError(str(exc)) from exc


def proposition_from_document(value: Mapping[str, Any]) -> PropositionReferent:
    data = dict(value)
    try:
        content = tuple(filler_from_document(_mapping(item, "proposition content")) for item in data.get("content_refs", ()))
        if not all(isinstance(item, FillerRef) for item in content):
            raise UOLDecodeError("proposition content cannot be quoted literals")
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
        if isinstance(exc, UOLDecodeError):
            raise
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


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
        raise UOLDecodeError(str(exc)) from exc


def scope_relation_from_document(value: Mapping[str, Any]) -> ScopeRelation:
    data = dict(value)
    try:
        scoped = filler_from_document(_mapping(data["scoped_ref"], "scoped reference"))
        if not isinstance(scoped, FillerRef):
            raise UOLDecodeError("scope relation cannot directly scope a quoted literal")
        return ScopeRelation(
            scope_relation_ref=str(data["scope_relation_ref"]),
            operator_application_ref=str(data["operator_application_ref"]),
            scoped_ref=scoped,
            scope_kind=ScopeKind(data["scope_kind"]),
            order=int(data.get("order", 0)),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, UOLDecodeError):
            raise
        raise UOLDecodeError(str(exc)) from exc


def uol_graph_from_document(value: Mapping[str, Any]) -> UOLGraph:
    data = dict(value)
    try:
        referents = {
            str(key): referent_from_document(_mapping(item, "referent"))
            for key, item in _mapping(data.get("referents", {}), "referents").items()
        }
        applications = {
            str(key): application_from_document(_mapping(item, "application"))
            for key, item in _mapping(data.get("applications", {}), "applications").items()
        }
        variables = {
            str(key): variable_from_document(_mapping(item, "variable"))
            for key, item in _mapping(data.get("variables", {}), "variables").items()
        }
        groups = {
            str(key): coordination_from_document(_mapping(item, "coordination group"))
            for key, item in _mapping(data.get("coordination_groups", {}), "coordination_groups").items()
        }
        propositions = {
            str(key): proposition_from_document(_mapping(item, "proposition"))
            for key, item in _mapping(data.get("propositions", {}), "propositions").items()
        }
        claims = {
            str(key): claim_from_document(_mapping(item, "claim"))
            for key, item in _mapping(data.get("claims", {}), "claims").items()
        }
        events = {
            str(key): event_from_document(_mapping(item, "event"))
            for key, item in _mapping(data.get("events", {}), "events").items()
        }
        roots = tuple(filler_from_document(_mapping(item, "root reference")) for item in data.get("root_refs", ()))
        if not all(isinstance(item, FillerRef) for item in roots):
            raise UOLDecodeError("UOL roots cannot be quoted literals")
        return UOLGraph(
            graph_ref=str(data["graph_ref"]),
            referents=referents,
            applications=applications,
            variables=variables,
            coordination_groups=groups,
            propositions=propositions,
            claims=claims,
            events=events,
            scope_relations=tuple(scope_relation_from_document(_mapping(item, "scope relation")) for item in data.get("scope_relations", ())),
            state_deltas=tuple(state_delta_from_document(_mapping(item, "state delta")) for item in data.get("state_deltas", ())),
            capability_deltas=tuple(capability_delta_from_document(_mapping(item, "capability delta")) for item in data.get("capability_deltas", ())),
            impact_assessments=tuple(impact_from_document(_mapping(item, "impact assessment")) for item in data.get("impact_assessments", ())),
            importance_assessments=tuple(importance_from_document(_mapping(item, "importance assessment")) for item in data.get("importance_assessments", ())),
            root_refs=tuple(item for item in roots if isinstance(item, FillerRef)),
            unresolved_refs=_tuple_str(data.get("unresolved_refs")),
            assumptions=_tuple_str(data.get("assumptions")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, UOLDecodeError):
            raise
        raise UOLDecodeError(str(exc)) from exc


def uol_to_document(value: Any) -> dict[str, Any]:
    if isinstance(value, (FillerRef, QuotedLiteral)):
        return filler_to_document(value)
    document = canonical_data(value)
    if not isinstance(document, dict):
        raise TypeError(f"unsupported UOL document type: {type(value)!r}")
    if isinstance(value, ApplicationBinding):
        document["fillers"] = [filler_to_document(item) for item in value.fillers]
    elif isinstance(value, SemanticApplication):
        document["bindings"] = [uol_to_document(item) for item in value.bindings]
    elif isinstance(value, CoordinationGroup):
        document["members"] = [filler_to_document(item) for item in value.members]
    elif isinstance(value, PropositionReferent):
        document["referent"] = uol_to_document(value.referent)
        document["content_refs"] = [filler_to_document(item) for item in value.content_refs]
    elif isinstance(value, ClaimOccurrence):
        document["referent"] = uol_to_document(value.referent)
    elif isinstance(value, EventOccurrence):
        document["referent"] = uol_to_document(value.referent)
    elif isinstance(value, ScopeRelation):
        document["scoped_ref"] = filler_to_document(value.scoped_ref)
    elif isinstance(value, UOLGraph):
        document["referents"] = {key: uol_to_document(item) for key, item in value.referents.items()}
        document["applications"] = {key: uol_to_document(item) for key, item in value.applications.items()}
        document["variables"] = {key: uol_to_document(item) for key, item in value.variables.items()}
        document["coordination_groups"] = {key: uol_to_document(item) for key, item in value.coordination_groups.items()}
        document["propositions"] = {key: uol_to_document(item) for key, item in value.propositions.items()}
        document["claims"] = {key: uol_to_document(item) for key, item in value.claims.items()}
        document["events"] = {key: uol_to_document(item) for key, item in value.events.items()}
        document["scope_relations"] = [uol_to_document(item) for item in value.scope_relations]
        document["state_deltas"] = [uol_to_document(item) for item in value.state_deltas]
        document["capability_deltas"] = [uol_to_document(item) for item in value.capability_deltas]
        document["impact_assessments"] = [uol_to_document(item) for item in value.impact_assessments]
        document["importance_assessments"] = [uol_to_document(item) for item in value.importance_assessments]
        document["root_refs"] = [filler_to_document(item) for item in value.root_refs]
    return document
