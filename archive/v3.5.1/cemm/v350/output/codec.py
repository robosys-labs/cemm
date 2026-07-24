"""Deterministic codecs for Phase-18 output authority records."""
from __future__ import annotations
from typing import Any, Mapping

from ..learning.codec import _pin
from ..schema.model import canonical_data
from .model import *


def output_record_to_document(record: Any) -> dict[str, Any]:
    return dict(canonical_data(record))


def _pins(values):
    return tuple(_pin(dict(x)) for x in values or ())


def channel_adapter_contract_from_document(value: Mapping[str, Any]) -> ChannelAdapterContractRecord:
    d=dict(value); return ChannelAdapterContractRecord(
        contract_ref=str(d['contract_ref']),channel_ref=str(d['channel_ref']),adapter_ref=str(d['adapter_ref']),adapter_revision=int(d['adapter_revision']),
        max_payload_bytes=int(d['max_payload_bytes']),allowed_language_tags=tuple(map(str,d.get('allowed_language_tags',()))),transformation_refs=tuple(map(str,d.get('transformation_refs',()))),
        content_preserving_transform_only=bool(d.get('content_preserving_transform_only',True)),requires_post_transform_roundtrip=bool(d.get('requires_post_transform_roundtrip',False)),
        idempotency_mode=EmissionIdempotencyMode(str(d.get('idempotency_mode',EmissionIdempotencyMode.NONE.value))),retry_safe_on_unknown=bool(d.get('retry_safe_on_unknown',False)),supports_recovery_query=bool(d.get('supports_recovery_query',False)),
        delivery_ack_semantics_ref=str(d.get('delivery_ack_semantics_ref','delivery:unknown')),delivery_ack_proves_recipient_receipt=bool(d.get('delivery_ack_proves_recipient_receipt',False)),retention_policy_ref=str(d.get('retention_policy_ref','retention:channel_default')),
        security_scope_ref=str(d.get('security_scope_ref','security:channel_default')),permission_ref=str(d.get('permission_ref','internal')),revision=int(d.get('revision',1)),
        supersedes_revision=None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),active=bool(d.get('active',False)),metadata=dict(d.get('metadata',{})))


def literal_emission_policy_from_document(value):
    d=dict(value); return LiteralEmissionPolicyRecord(str(d['policy_ref']),tuple((str(x[0]),int(x[1])) for x in d.get('response_goal_schema_pins',())),str(d['language_tag']),str(d['surface_sha256']),str(d['expected_graph_fingerprint']),_pins(d.get('trigger_pins',())),str(d.get('permission_ref','public')),int(d.get('revision',1)),None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),bool(d.get('active',False)),dict(d.get('metadata',{})))


def emission_gate_assessment_from_document(value):
    d=dict(value); return EmissionGateAssessmentRecord(str(d['assessment_ref']),str(d['gate_ref']),bool(d['passed']),str(d['evaluator_ref']),str(d['evaluator_revision']),_pins(d.get('checked_pins',())),tuple(map(str,d.get('authorization_refs',()))),tuple(map(str,d.get('proof_refs',()))),tuple(map(str,d.get('reason_refs',()))),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),int(d.get('snapshot_revision',0)),str(d.get('snapshot_fingerprint','')),int(d.get('revision',1)),dict(d.get('metadata',{})))


def emission_authorization_from_document(value):
    d=dict(value); return EmissionAuthorizationRecord(
        authorization_ref=str(d['authorization_ref']),response_uol_pin=_pin(dict(d['response_uol_pin'])),realization_request_pin=_pin(dict(d['realization_request_pin'])),surface_candidate_pin=_pin(dict(d['surface_candidate_pin'])),
        semantic_roundtrip_pin=_pin(dict(d['semantic_roundtrip_pin'])),goal_decision_pin=_pin(dict(d['goal_decision_pin'])),channel_contract_pin=_pin(dict(d['channel_contract_pin'])),gate_assessment_pins=_pins(d.get('gate_assessment_pins',())),
        decision=EmissionAuthorizationDecision(str(d['decision'])),audience_refs=tuple(map(str,d.get('audience_refs',()))),surface_sha256=str(d['surface_sha256']),passed_gates=tuple(map(str,d.get('passed_gates',()))),failed_gates=tuple(map(str,d.get('failed_gates',()))),
        operation_result_pins=_pins(d.get('operation_result_pins',())),operation_reconciliation_pins=_pins(d.get('operation_reconciliation_pins',())),literal_policy_pin=None if d.get('literal_policy_pin') is None else _pin(dict(d['literal_policy_pin'])),authorization_refs=tuple(map(str,d.get('authorization_refs',()))),
        context_ref=str(d.get('context_ref','actual')),permission_ref=str(d.get('permission_ref','conversation')),sensitivity=str(d.get('sensitivity','normal')),snapshot_revision=int(d.get('snapshot_revision',0)),snapshot_fingerprint=str(d.get('snapshot_fingerprint','')),revision=int(d.get('revision',1)),metadata=dict(d.get('metadata',{})))


def emission_journal_from_document(value):
    d=dict(value); return EmissionJournalRecord(str(d['journal_ref']),_pin(dict(d['authorization_pin'])),EmissionJournalStatus(str(d['status'])),d.get('idempotency_key'),str(d['adapter_ref']),int(d['adapter_revision']),str(d['surface_sha256']),int(d.get('submission_attempt',0)),tuple(map(str,d.get('request_evidence_refs',()))),tuple(map(str,d.get('response_evidence_refs',()))),tuple(map(str,d.get('external_correlation_refs',()))),None if d.get('prior_journal_pin') is None else _pin(dict(d['prior_journal_pin'])),d.get('submitted_at'),d.get('observed_at'),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),str(d.get('sensitivity','normal')),int(d.get('revision',1)),None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),dict(d.get('metadata',{})))


def emission_from_document(value):
    d=dict(value); return EmissionRecord(str(d['emission_ref']),_pin(dict(d['journal_pin'])),_pin(dict(d['authorization_pin'])),_pin(dict(d['response_uol_pin'])),_pin(dict(d['surface_candidate_pin'])),EmissionStatus(str(d['status'])),str(d['surface_sha256']),tuple(map(str,d.get('audience_refs',()))),tuple(map(str,d.get('evidence_refs',()))),tuple(map(str,d.get('proof_refs',()))),str(d['channel_ref']),tuple(map(str,d.get('external_correlation_refs',()))),d.get('emitted_bytes_ref'),d.get('emitted_at'),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),str(d.get('sensitivity','normal')),int(d.get('revision',1)),dict(d.get('metadata',{})))


def emission_anomaly_from_document(value):
    d=dict(value); return EmissionAnomalyRecord(
        anomaly_ref=str(d['anomaly_ref']),anomaly_kind_ref=str(d['anomaly_kind_ref']),journal_pin=_pin(dict(d['journal_pin'])),authorization_pin=_pin(dict(d['authorization_pin'])),channel_contract_pin=_pin(dict(d['channel_contract_pin'])),
        authorized_surface_sha256=str(d['authorized_surface_sha256']),observed_surface_sha256=None if d.get('observed_surface_sha256') is None else str(d['observed_surface_sha256']),content_left_system=bool(d.get('content_left_system',False)),
        evidence_refs=tuple(map(str,d.get('evidence_refs',()))),proof_refs=tuple(map(str,d.get('proof_refs',()))),reason_refs=tuple(map(str,d.get('reason_refs',()))),external_correlation_refs=tuple(map(str,d.get('external_correlation_refs',()))),
        channel_ref=str(d.get('channel_ref','channel:unknown')),detected_at=d.get('detected_at'),context_ref=str(d.get('context_ref','actual')),permission_ref=str(d.get('permission_ref','conversation')),sensitivity=str(d.get('sensitivity','normal')),
        no_output_discourse_authority=bool(d.get('no_output_discourse_authority',True)),revision=int(d.get('revision',1)),metadata=dict(d.get('metadata',{})))


def silence_outcome_from_document(value):
    d=dict(value); return SilenceOutcomeRecord(str(d['silence_ref']),_pin(dict(d['goal_decision_pin'])),_pins(d.get('selected_goal_pins',())),tuple(map(str,d.get('target_refs',()))),_pins(d.get('policy_pins',())),tuple(map(str,d.get('reason_refs',()))),str(d['context_ref']),str(d['permission_ref']),int(d['snapshot_revision']),str(d['snapshot_fingerprint']),int(d.get('revision',1)))


def output_discourse_act_from_document(value):
    d=dict(value); return OutputDiscourseActRecord(str(d['discourse_ref']),_pin(dict(d['emission_pin'])),_pin(dict(d['response_uol_pin'])),_pins(d.get('goal_candidate_pins',())),str(d['speaker_ref']),tuple(map(str,d.get('addressee_refs',()))),tuple(map(str,d.get('response_root_refs',()))),tuple(map(str,d.get('acknowledgement_target_refs',()))),_pins(d.get('operation_result_pins',())),tuple(map(str,d.get('reason_refs',()))),tuple(map(str,d.get('evidence_refs',()))),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),d.get('emitted_at'),int(d.get('revision',1)),dict(d.get('metadata',{})))


def output_commitment_from_document(value):
    d=dict(value); return OutputCommitmentRecord(str(d['commitment_ref']),_pin(dict(d['discourse_pin'])),tuple(map(str,d.get('target_refs',()))),str(d['commitment_kind_ref']),OutputCommitmentStatus(str(d.get('status',OutputCommitmentStatus.ACTIVE.value))),bool(d.get('common_ground_proposal',True)),tuple(map(str,d.get('acceptance_evidence_refs',()))),_pins(d.get('correction_pins',())),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),int(d.get('revision',1)),None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),dict(d.get('metadata',{})))


def common_ground_from_document(value):
    d=dict(value); return CommonGroundRecord(str(d['ground_ref']),str(d['subject_ref']),tuple(map(str,d.get('participant_refs',()))),CommonGroundStatus(str(d['status'])),_pins(d.get('supporting_discourse_pins',())),_pins(d.get('supporting_emission_pins',())),_pins(d.get('opposing_pins',())),tuple(map(str,d.get('evidence_refs',()))),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),d.get('valid_time_ref'),int(d.get('revision',1)),None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),dict(d.get('metadata',{})))


def output_reference_anchor_from_document(value):
    d=dict(value); return OutputReferenceAnchorRecord(str(d['anchor_ref']),str(d['target_kind_ref']),str(d['target_ref']),None if d.get('target_pin') is None else _pin(dict(d['target_pin'])),_pin(dict(d['response_uol_pin'])),_pin(dict(d['discourse_pin'])),tuple(map(str,d.get('goal_refs',()))),tuple(map(str,d.get('audience_refs',()))),float(d['salience']),int(d['ordinal']),str(d['context_ref']),str(d['permission_ref']),d.get('time_ref'),int(d.get('revision',1)),dict(d.get('metadata',{})))


def output_correction_from_document(value):
    d=dict(value); return OutputCorrectionRecord(str(d['correction_ref']),_pin(dict(d['correcting_discourse_pin'])),_pins(d.get('prior_commitment_pins',())),_pins(d.get('prior_common_ground_pins',())),tuple(map(str,d.get('replacement_target_refs',()))),tuple(map(str,d.get('opposition_target_refs',()))),tuple(map(str,d.get('invalidated_projection_refs',()))),tuple(map(str,d.get('evidence_refs',()))),tuple(map(str,d.get('proof_refs',()))),str(d.get('context_ref','actual')),str(d.get('permission_ref','conversation')),int(d.get('revision',1)))
