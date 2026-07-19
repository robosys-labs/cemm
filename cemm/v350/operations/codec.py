"""Deterministic codecs for Phase-16 operation records."""
from __future__ import annotations
from typing import Any, Mapping
from ..learning.codec import _pin
from ..schema.model import canonical_data
from .model import (
    IdempotencyMode, OperationAdapterContractRecord, OperationAuthorizationDecision,
    OperationAuthorizationRecord, OperationGateAssessmentRecord, OperationJournalRecord, OperationJournalStatus,
    OperationPlanRecord, OperationReconciliationRecord, OperationResultRecord,
    OperationResultStatus,
)


def operation_record_to_document(record: Any) -> dict[str, Any]:
    return dict(canonical_data(record))


def adapter_contract_from_document(v: Mapping[str, Any]) -> OperationAdapterContractRecord:
    d=dict(v); return OperationAdapterContractRecord(
        contract_ref=str(d['contract_ref']), action_schema_pins=tuple((str(x[0]),int(x[1])) for x in d.get('action_schema_pins',())),
        adapter_ref=str(d['adapter_ref']), adapter_revision=int(d['adapter_revision']), supported_port_refs=tuple(map(str,d.get('supported_port_refs',()))),
        result_schema_pins=tuple((str(x[0]),int(x[1])) for x in d.get('result_schema_pins',())), idempotency_mode=IdempotencyMode(str(d.get('idempotency_mode','none'))),
        retry_safe_on_unknown=bool(d.get('retry_safe_on_unknown',False)), cancellation_supported=bool(d.get('cancellation_supported',False)),
        timeout_semantics=str(d.get('timeout_semantics','outcome_unknown')), permission_ref=str(d.get('permission_ref','internal')),
        revision=int(d.get('revision',1)), supersedes_revision=None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),
        active=bool(d.get('active',False)), metadata=dict(d.get('metadata',{})))


def operation_plan_from_document(v: Mapping[str, Any]) -> OperationPlanRecord:
    d=dict(v); return OperationPlanRecord(
        plan_ref=str(d['plan_ref']), goal_decision_pin=_pin(dict(d['goal_decision_pin'])), goal_candidate_pin=_pin(dict(d['goal_candidate_pin'])),
        action_application_pin=_pin(dict(d['action_application_pin'])), action_schema_pin=_pin(dict(d['action_schema_pin'])),
        controlling_holder_ref=str(d['controlling_holder_ref']), bound_port_refs=tuple(map(str,d.get('bound_port_refs',()))), capability_pin=_pin(dict(d['capability_pin'])),
        adapter_contract_pin=_pin(dict(d['adapter_contract_pin'])), authorization_input_pins=tuple(_pin(dict(x)) for x in d.get('authorization_input_pins',())),
        predicted_effect_pins=tuple(_pin(dict(x)) for x in d.get('predicted_effect_pins',())), idempotency_key=d.get('idempotency_key'),
        context_ref=str(d.get('context_ref','actual')), permission_ref=str(d.get('permission_ref','conversation')), sensitivity=str(d.get('sensitivity','normal')),
        snapshot_revision=int(d.get('snapshot_revision',0)), snapshot_fingerprint=str(d.get('snapshot_fingerprint','')), revision=int(d.get('revision',1)), metadata=dict(d.get('metadata',{})))


def operation_gate_assessment_from_document(v: Mapping[str, Any]) -> OperationGateAssessmentRecord:
    d=dict(v); return OperationGateAssessmentRecord(
        assessment_ref=str(d['assessment_ref']), plan_pin=_pin(dict(d['plan_pin'])), gate_ref=str(d['gate_ref']), passed=bool(d['passed']),
        evaluator_ref=str(d['evaluator_ref']), evaluator_revision=str(d['evaluator_revision']), checked_pins=tuple(_pin(dict(x)) for x in d.get('checked_pins',())),
        authorization_refs=tuple(map(str,d.get('authorization_refs',()))), proof_refs=tuple(map(str,d.get('proof_refs',()))), reason_refs=tuple(map(str,d.get('reason_refs',()))),
        context_ref=str(d.get('context_ref','actual')), permission_ref=str(d.get('permission_ref','conversation')), snapshot_revision=int(d.get('snapshot_revision',0)),
        snapshot_fingerprint=str(d.get('snapshot_fingerprint','')), revision=int(d.get('revision',1)), metadata=dict(d.get('metadata',{})))


def operation_authorization_from_document(v: Mapping[str, Any]) -> OperationAuthorizationRecord:
    d=dict(v); return OperationAuthorizationRecord(
        authorization_ref=str(d['authorization_ref']), plan_pin=_pin(dict(d['plan_pin'])), decision=OperationAuthorizationDecision(str(d['decision'])),
        checked_pins=tuple(_pin(dict(x)) for x in d.get('checked_pins',())), gate_assessment_pins=tuple(_pin(dict(x)) for x in d.get('gate_assessment_pins',())),
        passed_gates=tuple(map(str,d.get('passed_gates',()))), failed_gates=tuple(map(str,d.get('failed_gates',()))),
        authorization_refs=tuple(map(str,d.get('authorization_refs',()))), context_ref=str(d.get('context_ref','actual')), permission_ref=str(d.get('permission_ref','conversation')),
        snapshot_revision=int(d.get('snapshot_revision',0)), snapshot_fingerprint=str(d.get('snapshot_fingerprint','')), revision=int(d.get('revision',1)), metadata=dict(d.get('metadata',{})))


def operation_journal_from_document(v: Mapping[str, Any]) -> OperationJournalRecord:
    d=dict(v); prior=d.get('prior_journal_pin'); return OperationJournalRecord(
        journal_ref=str(d['journal_ref']), plan_pin=_pin(dict(d['plan_pin'])), authorization_pin=_pin(dict(d['authorization_pin'])), status=OperationJournalStatus(str(d['status'])),
        idempotency_key=d.get('idempotency_key'), adapter_ref=str(d['adapter_ref']), adapter_revision=int(d['adapter_revision']), submission_attempt=int(d.get('submission_attempt',0)),
        request_evidence_refs=tuple(map(str,d.get('request_evidence_refs',()))), response_evidence_refs=tuple(map(str,d.get('response_evidence_refs',()))),
        external_correlation_refs=tuple(map(str,d.get('external_correlation_refs',()))), prior_journal_pin=None if prior is None else _pin(dict(prior)),
        submitted_at=d.get('submitted_at'), observed_at=d.get('observed_at'), context_ref=str(d.get('context_ref','actual')), permission_ref=str(d.get('permission_ref','conversation')),
        sensitivity=str(d.get('sensitivity','normal')), revision=int(d.get('revision',1)), supersedes_revision=None if d.get('supersedes_revision') is None else int(d['supersedes_revision']), metadata=dict(d.get('metadata',{})))


def operation_result_from_document(v: Mapping[str, Any]) -> OperationResultRecord:
    d=dict(v); return OperationResultRecord(
        result_ref=str(d['result_ref']), journal_pin=_pin(dict(d['journal_pin'])), status=OperationResultStatus(str(d['status'])), transport_acknowledged=bool(d.get('transport_acknowledged',False)),
        domain_result_refs=tuple(map(str,d.get('domain_result_refs',()))), observed_effect_refs=tuple(map(str,d.get('observed_effect_refs',()))), evidence_refs=tuple(map(str,d.get('evidence_refs',()))),
        proof_refs=tuple(map(str,d.get('proof_refs',()))), retryable=bool(d.get('retryable',False)), uncertainty_refs=tuple(map(str,d.get('uncertainty_refs',()))),
        context_ref=str(d.get('context_ref','actual')), permission_ref=str(d.get('permission_ref','conversation')), revision=int(d.get('revision',1)), metadata=dict(d.get('metadata',{})))


def operation_reconciliation_from_document(v: Mapping[str, Any]) -> OperationReconciliationRecord:
    d=dict(v); return OperationReconciliationRecord(
        reconciliation_ref=str(d['reconciliation_ref']), plan_pin=_pin(dict(d['plan_pin'])), result_pin=_pin(dict(d['result_pin'])),
        predicted_effect_pins=tuple(_pin(dict(x)) for x in d.get('predicted_effect_pins',())), observed_pins=tuple(_pin(dict(x)) for x in d.get('observed_pins',())),
        generated_evidence_refs=tuple(map(str,d.get('generated_evidence_refs',()))), replay_required_refs=tuple(map(str,d.get('replay_required_refs',()))),
        contradiction_refs=tuple(map(str,d.get('contradiction_refs',()))), invalidated_goal_decision_refs=tuple(map(str,d.get('invalidated_goal_decision_refs',()))), frontier_refs=tuple(map(str,d.get('frontier_refs',()))),
        context_ref=str(d.get('context_ref','actual')), permission_ref=str(d.get('permission_ref','conversation')), revision=int(d.get('revision',1)), metadata=dict(d.get('metadata',{})))
