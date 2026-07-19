"""Commit-boundary invariants for Phase-16 operation/Response UOL authority."""
from __future__ import annotations
from ..storage.model import RecordKind
from .model import (OperationAuthorizationDecision,OperationAuthorizationRecord,OperationGateAssessmentRecord,OperationJournalRecord,OperationJournalStatus,OperationPlanRecord,OperationReconciliationRecord,OperationResultRecord,OperationResultStatus)
from .coordinator import _ALLOWED_JOURNAL_TRANSITIONS
from ..response.model import ResponseTransformationProof,ResponseUOLRecord
from ..schema.model import PortFillerClass
from ..uol.model import FillerRef

class Phase16CommitValidator:
 def __init__(self,resolver):self.r=resolver
 def validate_operation(self,op,record):
  k=op.record_kind
  if k==RecordKind.OPERATION_PLAN:
   if not isinstance(record,OperationPlanRecord):raise ValueError('operation plan type mismatch')
   for p in (record.goal_decision_pin,record.goal_candidate_pin,record.action_application_pin,record.action_schema_pin,record.capability_pin,record.adapter_contract_pin,*record.authorization_input_pins,*record.predicted_effect_pins):self._require(op,p)
  elif k==RecordKind.OPERATION_GATE_ASSESSMENT:
   if not isinstance(record,OperationGateAssessmentRecord):raise ValueError('operation gate assessment type mismatch')
   self._require(op,record.plan_pin)
   for p in record.checked_pins:self._require(op,p)
   if record.passed and not record.checked_pins:raise ValueError('passing gate assessment lacks exact checked substrate')
  elif k==RecordKind.OPERATION_AUTHORIZATION:
   if not isinstance(record,OperationAuthorizationRecord):raise ValueError('operation authorization type mismatch')
   self._require(op,record.plan_pin)
   for p in record.checked_pins:self._require(op,p)
   for p in record.gate_assessment_pins:self._require(op,p)
   required={'goal_current','target_complete','action_execute_authorized','live_capability','permission','resources','risk','preconditions','adapter_available','idempotency_recovery'}
   assessments=[]
   for p in record.gate_assessment_pins:
    stored=self.r.resolve(p.record_kind,p.record_ref,p.revision)
    if stored is None or not isinstance(stored.payload,OperationGateAssessmentRecord):raise ValueError('authorization gate assessment is missing')
    assessments.append(stored.payload)
   gate_refs=[a.gate_ref for a in assessments]
   if len(gate_refs)!=len(set(gate_refs)):raise ValueError('duplicate durable hard-gate assessment')
   if record.decision==OperationAuthorizationDecision.ALLOW:
    if record.failed_gates:raise ValueError('allowed operation has failed gates')
    if set(record.passed_gates)!=required:raise ValueError('allowed operation must contain exactly the required hard gates')
    if set(gate_refs)!=required or any(not a.passed for a in assessments):raise ValueError('allowed operation requires one passing durable assessment per hard gate')
  elif k==RecordKind.OPERATION_JOURNAL:
   if not isinstance(record,OperationJournalRecord):raise ValueError('operation journal type mismatch')
   self._require(op,record.plan_pin);self._require(op,record.authorization_pin)
   if record.revision==1 and record.status!=OperationJournalStatus.PREPARED:raise ValueError('initial durable journal revision must be PREPARED')
   a=self.r.resolve(record.authorization_pin.record_kind,record.authorization_pin.record_ref,record.authorization_pin.revision)
   if record.status not in {OperationJournalStatus.CANCELLED_BEFORE_SUBMIT} and (a is None or getattr(a.payload,'decision',None)!=OperationAuthorizationDecision.ALLOW):raise ValueError('journal lifecycle requires exact ALLOW authorization')
   if record.revision>1:
    if record.prior_journal_pin is None:raise ValueError('journal lifecycle revision requires prior pin')
    self._require(op,record.prior_journal_pin)
    prior=self.r.resolve(record.prior_journal_pin.record_kind,record.prior_journal_pin.record_ref,record.prior_journal_pin.revision)
    if prior is None or not isinstance(prior.payload,OperationJournalRecord):raise ValueError('journal prior revision missing')
    if record.status not in _ALLOWED_JOURNAL_TRANSITIONS.get(prior.payload.status,set()):raise ValueError(f'illegal durable journal transition: {prior.payload.status.value}->{record.status.value}')
   if record.status in {OperationJournalStatus.OBSERVED_SUCCESS,OperationJournalStatus.OBSERVED_FAILURE,OperationJournalStatus.OBSERVED_PARTIAL} and not any(d.record_kind==RecordKind.OPERATION_RESULT and d.revision is not None and d.fingerprint is not None for d in op.dependencies):raise ValueError('observed journal state requires exact operation result dependency')
   if record.status==OperationJournalStatus.RECONCILED and not any(d.record_kind==RecordKind.OPERATION_RECONCILIATION and d.revision is not None and d.fingerprint is not None for d in op.dependencies):raise ValueError('RECONCILED journal requires exact operation reconciliation dependency')
  elif k==RecordKind.OPERATION_RESULT:
   if not isinstance(record,OperationResultRecord):raise ValueError('operation result type mismatch')
   self._require(op,record.journal_pin)
   journal=self.r.resolve(record.journal_pin.record_kind,record.journal_pin.record_ref,record.journal_pin.revision)
   if journal is None or getattr(journal.payload,'status',None) not in {OperationJournalStatus.ACKNOWLEDGED,OperationJournalStatus.OUTCOME_UNKNOWN}:raise ValueError('operation result must pin an acknowledged/unknown submitted journal state')
  elif k==RecordKind.OPERATION_RECONCILIATION:
   if not isinstance(record,OperationReconciliationRecord):raise ValueError('operation reconciliation type mismatch')
   self._require(op,record.plan_pin);self._require(op,record.result_pin);self._require(op,record.observed_journal_pin)
   result=self.r.resolve(record.result_pin.record_kind,record.result_pin.record_ref,record.result_pin.revision)
   if result is None or getattr(result.payload,'status',None)==OperationResultStatus.UNKNOWN:raise ValueError('unknown operation outcome cannot be reconciled as terminal')
   observed_journal=self.r.resolve(record.observed_journal_pin.record_kind,record.observed_journal_pin.record_ref,record.observed_journal_pin.revision)
   if observed_journal is None or getattr(observed_journal.payload,'status',None) not in {OperationJournalStatus.OBSERVED_SUCCESS,OperationJournalStatus.OBSERVED_FAILURE,OperationJournalStatus.OBSERVED_PARTIAL}:raise ValueError('reconciliation requires exact observed terminal journal')
   if observed_journal.payload.journal_ref != result.payload.journal_pin.record_ref:raise ValueError('reconciliation journal/result operation identity mismatch')
   edges=[e.payload for e in self.r.records(RecordKind.DEPENDENCY) if getattr(e.payload,'active',False)]
   if not any(getattr(e,'dependent_kind',None)==RecordKind.OPERATION_JOURNAL and getattr(e,'dependent_ref',None)==observed_journal.payload.journal_ref and getattr(e,'dependent_revision',None)==observed_journal.payload.revision and getattr(e,'prerequisite_kind',None)==RecordKind.OPERATION_RESULT and getattr(e,'prerequisite_ref',None)==record.result_pin.record_ref and getattr(e,'prerequisite_revision',None)==record.result_pin.revision and getattr(e,'prerequisite_fingerprint',None)==record.result_pin.record_fingerprint for e in edges):raise ValueError('observed journal lacks exact operation-result lineage edge')
   plan=self.r.resolve(record.plan_pin.record_kind,record.plan_pin.record_ref,record.plan_pin.revision)
   if plan is None or tuple(record.invalidated_goal_decision_refs)!=(plan.payload.goal_decision_pin.record_ref,):raise ValueError('reconciliation must invalidate the exact pre-operation goal decision')
   for p in (*record.predicted_effect_pins,*record.observed_pins):self._require(op,p)
  elif k==RecordKind.RESPONSE_TRANSFORMATION_PROOF:
   if not isinstance(record,ResponseTransformationProof):raise ValueError('response proof type mismatch')
   self._require(op,record.goal_candidate_pin);self._require(op,record.rule_pin)
   for p in (*record.input_pins,*record.authorization_pins):self._require(op,p)
  elif k==RecordKind.RESPONSE_UOL:
   if not isinstance(record,ResponseUOLRecord):raise ValueError('Response UOL type mismatch')
   self._require(op,record.goal_decision_pin)
   for p in (*record.selected_goal_pins,*record.source_pins):self._require(op,p)
   if record.graph.root_refs and not record.transformation_proof_refs:raise ValueError('Response UOL roots require transformation proofs')
   reachable=self._reachable_applications(record.graph)
   if reachable!=set(record.graph.applications):raise ValueError('Response UOL contains unrooted or missing nested applications')
   if set(record.graph.unresolved_refs)!=set(record.unresolved_frontier_refs):raise ValueError('Response UOL unresolved frontiers must remain exact')
 @staticmethod
 def _reachable_applications(graph):
  seen=set();visiting=set()
  def visit(ref):
   if ref in seen:return
   if ref in visiting:raise ValueError('cyclic Response UOL application closure')
   app=graph.applications.get(ref)
   if app is None:raise ValueError(f'missing nested Response UOL application: {ref}')
   visiting.add(ref)
   for binding in app.bindings:
    for filler in binding.fillers:
     if isinstance(filler,FillerRef) and filler.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(filler.ref)
     elif isinstance(filler,FillerRef) and filler.filler_class==PortFillerClass.COORDINATION_GROUP:
      group=graph.coordination_groups.get(filler.ref)
      if group is None:raise ValueError(f'missing Response UOL coordination group: {filler.ref}')
      for member in group.members:
       if member.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(member.ref)
      for rel in graph.scope_relations:
       if rel.scoped_ref.ref==group.group_ref:visit(rel.operator_application_ref)
   for rel in graph.scope_relations:
    if rel.scoped_ref.ref==ref:visit(rel.operator_application_ref)
   visiting.remove(ref);seen.add(ref)
  for root in graph.root_refs:
   if root.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(root.ref)
   elif root.filler_class==PortFillerClass.COORDINATION_GROUP:
    group=graph.coordination_groups.get(root.ref)
    if group is None:raise ValueError(f'missing root Response UOL coordination group: {root.ref}')
    for member in group.members:
     if member.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(member.ref)
    for rel in graph.scope_relations:
     if rel.scoped_ref.ref==group.group_ref:visit(rel.operator_application_ref)
  return seen
 def _require(self,op,pin):
  if not any(d.record_kind==pin.record_kind and d.record_ref==pin.record_ref and d.revision==pin.revision and d.fingerprint==pin.record_fingerprint for d in op.dependencies):raise ValueError(f'Phase16 record missing exact dependency: {pin.key}')
