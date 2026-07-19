"""Thin external adapter boundary, recovery and reconciliation helpers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from .coordinator import OperationJournalCoordinator
from .model import (
    IdempotencyMode, OperationAdapterContractRecord, OperationJournalStatus, OperationPlanRecord,
    OperationReconciliationRecord, OperationResultRecord, OperationResultStatus,
)


@dataclass(frozen=True,slots=True)
class AdapterObservation:
    transport_acknowledged: bool
    status: OperationResultStatus
    domain_result_refs: tuple[str,...]=()
    observed_effect_refs: tuple[str,...]=()
    evidence_refs: tuple[str,...]=()
    proof_refs: tuple[str,...]=()
    uncertainty_refs: tuple[str,...]=()
    external_correlation_refs: tuple[str,...]=()
    retryable: bool=False


class OperationAdapter(Protocol):
    adapter_ref: str
    adapter_revision: int
    def submit(self, plan: OperationPlanRecord, *, idempotency_key: str|None) -> AdapterObservation: ...
    def recover(self, *, idempotency_key: str|None, external_correlation_refs: tuple[str,...]) -> AdapterObservation|None: ...


class OperationExecutionCoordinator:
    """Never holds a DB transaction across adapter invocation."""
    def __init__(self,store): self.store=store; self.journals=OperationJournalCoordinator(store)

    def execute_prepared(self,journal,plan:OperationPlanRecord,adapter:OperationAdapter):
        if journal.status != OperationJournalStatus.PREPARED: raise ValueError("only PREPARED journal may submit")
        contract_stored=self.store.get_record(RecordKind.OPERATION_ADAPTER_CONTRACT,plan.adapter_contract_pin.record_ref,plan.adapter_contract_pin.revision)
        if contract_stored is None or contract_stored.record_fingerprint!=plan.adapter_contract_pin.record_fingerprint: raise ValueError("stale adapter contract")
        contract=contract_stored.payload
        if not isinstance(contract,OperationAdapterContractRecord) or (adapter.adapter_ref,adapter.adapter_revision)!=(contract.adapter_ref,contract.adapter_revision):
            raise ValueError("adapter implementation does not match exact contract")
        submitted=self.journals.advance(journal,OperationJournalStatus.SUBMITTED)
        try:
            obs=adapter.submit(plan,idempotency_key=plan.idempotency_key)
        except Exception:
            unknown=self.journals.advance(submitted,OperationJournalStatus.OUTCOME_UNKNOWN)
            return unknown,None
        state=(OperationJournalStatus.ACKNOWLEDGED if obs.transport_acknowledged else OperationJournalStatus.OUTCOME_UNKNOWN)
        advanced=self.journals.advance(submitted,state,response_evidence_refs=obs.evidence_refs,external_correlation_refs=obs.external_correlation_refs)
        result=OperationResultRecord(
            result_ref="operation-result:"+semantic_fingerprint("operation-result-ref",(advanced.journal_ref,advanced.revision,obs),24),
            journal_pin=PinnedRecord(RecordKind.OPERATION_JOURNAL,advanced.journal_ref,advanced.revision,record_fingerprints(RecordKind.OPERATION_JOURNAL,advanced)[1]),
            status=obs.status,transport_acknowledged=obs.transport_acknowledged,domain_result_refs=obs.domain_result_refs,observed_effect_refs=obs.observed_effect_refs,
            evidence_refs=obs.evidence_refs,proof_refs=obs.proof_refs,retryable=obs.retryable,uncertainty_refs=obs.uncertainty_refs,context_ref=plan.context_ref,permission_ref=plan.permission_ref)
        terminal=(OperationJournalStatus.OBSERVED_SUCCESS if obs.status==OperationResultStatus.SUCCESS else OperationJournalStatus.OBSERVED_FAILURE if obs.status==OperationResultStatus.FAILURE else OperationJournalStatus.OBSERVED_PARTIAL if obs.status==OperationResultStatus.PARTIAL else OperationJournalStatus.OUTCOME_UNKNOWN)
        _,final=self.journals.persist_observation(advanced,result,terminal,response_evidence_refs=obs.evidence_refs,external_correlation_refs=obs.external_correlation_refs)
        return final,result


class OperationRecoveryCoordinator:
    def __init__(self,store): self.store=store
    def recoverable(self):
        terminals={OperationJournalStatus.OBSERVED_SUCCESS,OperationJournalStatus.OBSERVED_FAILURE,OperationJournalStatus.OBSERVED_PARTIAL,OperationJournalStatus.RECONCILED,OperationJournalStatus.CANCELLED_BEFORE_SUBMIT}
        return tuple(s.payload for s in self.store.records(RecordKind.OPERATION_JOURNAL) if getattr(s.payload,'status',None) not in terminals)
    def may_retry_unknown(self,journal) -> bool:
        plan_stored=self.store.get_record(RecordKind.OPERATION_PLAN,journal.plan_pin.record_ref,journal.plan_pin.revision)
        if plan_stored is None or plan_stored.record_fingerprint!=journal.plan_pin.record_fingerprint:return False
        contract_pin=plan_stored.payload.adapter_contract_pin
        c=self.store.get_record(RecordKind.OPERATION_ADAPTER_CONTRACT,contract_pin.record_ref,contract_pin.revision)
        if c is None or c.record_fingerprint!=contract_pin.record_fingerprint:return False
        contract=c.payload
        return bool(contract.retry_safe_on_unknown and contract.idempotency_mode!=IdempotencyMode.NONE and journal.idempotency_key)

    def recover_observation(self, journal, plan: OperationPlanRecord, adapter: OperationAdapter) -> AdapterObservation | None:
        if journal.status not in {OperationJournalStatus.SUBMITTED, OperationJournalStatus.OUTCOME_UNKNOWN, OperationJournalStatus.ACKNOWLEDGED}:
            raise ValueError("recovery is only valid for unresolved submitted operations")
        contract_stored = self.store.get_record(RecordKind.OPERATION_ADAPTER_CONTRACT,plan.adapter_contract_pin.record_ref,plan.adapter_contract_pin.revision)
        if contract_stored is None or contract_stored.record_fingerprint != plan.adapter_contract_pin.record_fingerprint:
            raise ValueError("stale adapter contract during recovery")
        contract = contract_stored.payload
        if not isinstance(contract,OperationAdapterContractRecord): raise ValueError("invalid adapter contract during recovery")
        if (adapter.adapter_ref,adapter.adapter_revision)!=(contract.adapter_ref,contract.adapter_revision):
            raise ValueError("recovery adapter implementation does not match exact contract")
        return adapter.recover(idempotency_key=journal.idempotency_key,external_correlation_refs=journal.external_correlation_refs)

    def recover_and_persist(self, journal, plan: OperationPlanRecord, adapter: OperationAdapter):
        obs=self.recover_observation(journal,plan,adapter); coordinator=OperationJournalCoordinator(self.store)
        if obs is None:
            if journal.status==OperationJournalStatus.SUBMITTED:return coordinator.advance(journal,OperationJournalStatus.OUTCOME_UNKNOWN),None
            return journal,None
        current=journal
        if current.status==OperationJournalStatus.SUBMITTED:
            state=OperationJournalStatus.ACKNOWLEDGED if obs.transport_acknowledged else OperationJournalStatus.OUTCOME_UNKNOWN
            current=coordinator.advance(current,state,response_evidence_refs=obs.evidence_refs,external_correlation_refs=obs.external_correlation_refs)
        result=OperationResultRecord(
            result_ref="operation-result:"+semantic_fingerprint("operation-recovery-result-ref",(current.journal_ref,current.revision,obs),24),
            journal_pin=PinnedRecord(RecordKind.OPERATION_JOURNAL,current.journal_ref,current.revision,record_fingerprints(RecordKind.OPERATION_JOURNAL,current)[1]),
            status=obs.status,transport_acknowledged=obs.transport_acknowledged,domain_result_refs=obs.domain_result_refs,observed_effect_refs=obs.observed_effect_refs,
            evidence_refs=obs.evidence_refs,proof_refs=obs.proof_refs,retryable=obs.retryable,uncertainty_refs=obs.uncertainty_refs,context_ref=plan.context_ref,permission_ref=plan.permission_ref)
        terminal=(OperationJournalStatus.OBSERVED_SUCCESS if obs.status==OperationResultStatus.SUCCESS else OperationJournalStatus.OBSERVED_FAILURE if obs.status==OperationResultStatus.FAILURE else OperationJournalStatus.OBSERVED_PARTIAL if obs.status==OperationResultStatus.PARTIAL else OperationJournalStatus.OUTCOME_UNKNOWN)
        _,final=coordinator.persist_observation(current,result,terminal,response_evidence_refs=obs.evidence_refs,external_correlation_refs=obs.external_correlation_refs)
        return final,result

    def automatic_retry_forbidden(self, journal) -> bool:
        return True


class ReconciliationCoordinator:
    """Build reconciliation lineage only; observed effects re-enter epistemics/transitions separately."""
    def __init__(self,store): self.store=store
    def build(self,plan_pin:PinnedRecord,result_pin:PinnedRecord,*,observed_journal_pin:PinnedRecord,observed_pins=(),generated_evidence_refs=(),replay_required_refs=(),contradiction_refs=(),frontier_refs=()):
        plan=self._exact(plan_pin).payload
        result=self._exact(result_pin).payload
        journal=self._exact(observed_journal_pin).payload
        if observed_journal_pin.record_kind != RecordKind.OPERATION_JOURNAL:
            raise ValueError("reconciliation requires exact observed operation-journal pin")
        if result.journal_pin.record_ref != observed_journal_pin.record_ref:
            raise ValueError("reconciliation result/journal identity mismatch")
        if observed_journal_pin.revision < result.journal_pin.revision:
            raise ValueError("reconciliation journal predates result observation")
        for pin in observed_pins:
            self._exact(pin)
        return OperationReconciliationRecord(
            reconciliation_ref="operation-reconciliation:"+semantic_fingerprint("operation-reconciliation-ref",(plan_pin.key,result_pin.key,observed_journal_pin.key,tuple(p.key for p in observed_pins)),24),
            plan_pin=plan_pin,result_pin=result_pin,observed_journal_pin=observed_journal_pin,
            predicted_effect_pins=plan.predicted_effect_pins,observed_pins=tuple(observed_pins),generated_evidence_refs=tuple(generated_evidence_refs),
            replay_required_refs=tuple(replay_required_refs),contradiction_refs=tuple(contradiction_refs),invalidated_goal_decision_refs=(plan.goal_decision_pin.record_ref,),frontier_refs=tuple(frontier_refs),
            context_ref=plan.context_ref,permission_ref=plan.permission_ref)
    def _exact(self,p):
        s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        if s is None or s.record_fingerprint!=p.record_fingerprint: raise ValueError(f"stale reconciliation pin: {p.key}")
        return s
