"""Deterministic document codecs for Phase-11 transition authorities."""
from __future__ import annotations

from typing import Any, Mapping

from ..schema.model import SchemaLifecycleStatus, canonical_data
from ..uol.model import CapabilityStatus, ChangeOperation
from .model import (
    CapabilityDependencyRecord,
    ConditionOperator,
    StateConditionSpec,
    StateEffectSpec,
    TransitionContractRecord,
    TransitionProofRecord,
    UnknownConditionPolicy,
)


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise ValueError("expected array, not string")
    return tuple(str(item) for item in value)


def condition_from_document(value: Mapping[str, Any]) -> StateConditionSpec:
    data = dict(value)
    return StateConditionSpec(
        condition_ref=str(data["condition_ref"]),
        holder_port_ref=str(data["holder_port_ref"]),
        dimension_ref=str(data["dimension_ref"]),
        dimension_revision=int(data["dimension_revision"]),
        operator=ConditionOperator(data["operator"]),
        value_ref=None if data.get("value_ref") is None else str(data["value_ref"]),
        value_revision=None if data.get("value_revision") is None else int(data["value_revision"]),
        unknown_policy=UnknownConditionPolicy(data.get("unknown_policy", UnknownConditionPolicy.PRESERVE_FRONTIER.value)),
    )


def effect_from_document(value: Mapping[str, Any]) -> StateEffectSpec:
    data = dict(value)
    return StateEffectSpec(
        effect_ref=str(data["effect_ref"]),
        holder_port_ref=str(data["holder_port_ref"]),
        dimension_ref=str(data["dimension_ref"]),
        dimension_revision=int(data["dimension_revision"]),
        operation=ChangeOperation(data["operation"]),
        from_value_ref=None if data.get("from_value_ref") is None else str(data["from_value_ref"]),
        from_value_revision=None if data.get("from_value_revision") is None else int(data["from_value_revision"]),
        to_value_ref=None if data.get("to_value_ref") is None else str(data["to_value_ref"]),
        to_value_revision=None if data.get("to_value_revision") is None else int(data["to_value_revision"]),
        magnitude_port_ref=None if data.get("magnitude_port_ref") is None else str(data["magnitude_port_ref"]),
        confidence=float(data.get("confidence", 1.0)),
    )


def transition_contract_from_document(value: Mapping[str, Any]) -> TransitionContractRecord:
    data = dict(value)
    return TransitionContractRecord(
        contract_ref=str(data["contract_ref"]),
        trigger_schema_ref=str(data["trigger_schema_ref"]),
        trigger_schema_revision=int(data["trigger_schema_revision"]),
        state_conditions=tuple(condition_from_document(item) for item in data.get("state_conditions", ())),
        state_effects=tuple(effect_from_document(item) for item in data.get("state_effects", ())),
        evidence_refs=_tuple_str(data.get("evidence_refs")),
        lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value)),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        context_policy=str(data.get("context_policy", "same_as_event")),
        permission_ref=str(data.get("permission_ref", "conversation")),
        metadata=dict(data.get("metadata", {})),
    )


def capability_dependency_from_document(value: Mapping[str, Any]) -> CapabilityDependencyRecord:
    data = dict(value)
    return CapabilityDependencyRecord(
        dependency_ref=str(data["dependency_ref"]),
        holder_type_refs=_tuple_str(data.get("holder_type_refs")),
        action_schema_ref=str(data["action_schema_ref"]),
        action_schema_revision=int(data["action_schema_revision"]),
        state_conditions=tuple(condition_from_document(item) for item in data.get("state_conditions", ())),
        status_if_satisfied=CapabilityStatus(data["status_if_satisfied"]),
        status_if_unsatisfied=CapabilityStatus(data["status_if_unsatisfied"]),
        status_if_unknown=CapabilityStatus(data["status_if_unknown"]),
        evidence_refs=_tuple_str(data.get("evidence_refs")),
        lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value)),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        permission_ref=str(data.get("permission_ref", "conversation")),
        metadata=dict(data.get("metadata", {})),
    )


def transition_proof_from_document(value: Mapping[str, Any]) -> TransitionProofRecord:
    data = dict(value)
    return TransitionProofRecord(
        proof_ref=str(data["proof_ref"]),
        event_ref=str(data["event_ref"]),
        event_revision=int(data["event_revision"]),
        participant_application_ref=str(data["participant_application_ref"]),
        participant_application_revision=int(data["participant_application_revision"]),
        transition_contract_ref=str(data["transition_contract_ref"]),
        transition_contract_revision=int(data["transition_contract_revision"]),
        admission_pins=tuple((str(item[0]), int(item[1])) for item in data.get("admission_pins", ())),
        condition_evidence_refs=_tuple_str(data.get("condition_evidence_refs")),
        input_assignment_pins=tuple((str(item[0]), int(item[1])) for item in data.get("input_assignment_pins", ())),
        derived_state_delta_refs=_tuple_str(data.get("derived_state_delta_refs")),
        context_ref=str(data["context_ref"]),
        effective_time_ref=str(data["effective_time_ref"]),
        confidence=float(data["confidence"]),
        evidence_refs=_tuple_str(data.get("evidence_refs")),
    )


def transition_record_to_document(value: Any) -> Mapping[str, Any]:
    return canonical_data(value)
