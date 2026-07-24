"""Atomic local journaling and observation persistence for Phase 16 operations."""
from __future__ import annotations
from dataclasses import replace

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
from ..storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordDependency, RecordKind
from .model import (
    OperationAuthorizationDecision, OperationAuthorizationRecord, OperationGateAssessmentRecord, OperationJournalRecord,
    OperationJournalStatus, OperationPlanRecord, OperationReconciliationRecord, OperationResultRecord,
)


def _pin(kind: RecordKind, record) -> PinnedRecord:
    return PinnedRecord(kind, record_ref(kind, record), record_revision(kind, record), record_fingerprints(kind, record)[1])


_ALLOWED_JOURNAL_TRANSITIONS = {
    OperationJournalStatus.PREPARED: {OperationJournalStatus.SUBMITTED, OperationJournalStatus.CANCELLED_BEFORE_SUBMIT},
    OperationJournalStatus.SUBMITTED: {OperationJournalStatus.ACKNOWLEDGED, OperationJournalStatus.OUTCOME_UNKNOWN},
    OperationJournalStatus.ACKNOWLEDGED: {OperationJournalStatus.OBSERVED_SUCCESS, OperationJournalStatus.OBSERVED_FAILURE, OperationJournalStatus.OBSERVED_PARTIAL, OperationJournalStatus.OUTCOME_UNKNOWN},
    OperationJournalStatus.OUTCOME_UNKNOWN: {OperationJournalStatus.ACKNOWLEDGED, OperationJournalStatus.OBSERVED_SUCCESS, OperationJournalStatus.OBSERVED_FAILURE, OperationJournalStatus.OBSERVED_PARTIAL},
    OperationJournalStatus.OBSERVED_SUCCESS: {OperationJournalStatus.RECONCILED},
    OperationJournalStatus.OBSERVED_FAILURE: {OperationJournalStatus.RECONCILED},
    OperationJournalStatus.OBSERVED_PARTIAL: {OperationJournalStatus.RECONCILED},
    OperationJournalStatus.CANCELLED_BEFORE_SUBMIT: set(),
    OperationJournalStatus.RECONCILED: set(),
}


class OperationJournalCoordinator:
    def __init__(self, store) -> None: self.store=store

    def prepare(self, plan: OperationPlanRecord, authorization: OperationAuthorizationRecord, gate_assessments: tuple[OperationGateAssessmentRecord, ...]):
        if authorization.decision != OperationAuthorizationDecision.ALLOW:
            raise ValueError("cannot prepare denied/deferred operation")
        plan_pin=_pin(RecordKind.OPERATION_PLAN, plan)
        if authorization.plan_pin != plan_pin:
            raise ValueError("authorization does not pin exact operation plan")
        assessment_pins=tuple(_pin(RecordKind.OPERATION_GATE_ASSESSMENT,item) for item in gate_assessments)
        if set(assessment_pins)!=set(authorization.gate_assessment_pins):
            raise ValueError("authorization gate assessment pins do not match supplied durable assessments")
        with self.store.snapshot() as snapshot:
            # Authorization is a point-in-time execution authority. Any intervening
            # semantic-store commit, even unrelated, requires a fresh authorization
            # cycle rather than silently reusing an older snapshot decision.
            if snapshot.store_revision != authorization.snapshot_revision or snapshot.fingerprint != authorization.snapshot_fingerprint:
                raise ValueError("store changed after operation authorization; re-authorize before PREPARED journal")
            if plan.snapshot_revision != authorization.snapshot_revision or plan.snapshot_fingerprint != authorization.snapshot_fingerprint:
                raise ValueError("operation plan and authorization do not share one exact snapshot")
            # Exact pins must still resolve. Do not equate raw latest revision with
            # semantic authority: a newer candidate schema must not shadow an older
            # effective ACTIVE revision. Operation-specific gates already re-check
            # effective schema/capability authority.
            for pin in (plan.goal_decision_pin, plan.goal_candidate_pin, plan.action_application_pin, plan.action_schema_pin,
                        plan.capability_pin, plan.adapter_contract_pin, *plan.authorization_input_pins, *plan.predicted_effect_pins, *authorization.checked_pins):
                stored=self.store.get_record(pin.record_kind,pin.record_ref,pin.revision)
                if stored is None or stored.record_fingerprint != pin.record_fingerprint:
                    raise ValueError(f"stale operation dependency before journal prepare: {pin.key}")
            for assessment in gate_assessments:
                if assessment.plan_pin!=plan_pin or assessment.snapshot_revision!=authorization.snapshot_revision or assessment.snapshot_fingerprint!=authorization.snapshot_fingerprint:
                    raise ValueError("gate assessment does not match exact authorization substrate")
            auth_pin=_pin(RecordKind.OPERATION_AUTHORIZATION, authorization)
            journal=OperationJournalRecord(
                journal_ref="operation-journal:"+semantic_fingerprint("operation-journal-ref",(plan.plan_ref,authorization.authorization_ref),24),
                plan_pin=plan_pin, authorization_pin=auth_pin, status=OperationJournalStatus.PREPARED,
                idempotency_key=plan.idempotency_key, adapter_ref=self._adapter(plan).adapter_ref,
                adapter_revision=self._adapter(plan).adapter_revision, context_ref=plan.context_ref,
                permission_ref=plan.permission_ref, sensitivity=plan.sensitivity,
            )
            deps_plan=self._deps((plan.goal_decision_pin,plan.goal_candidate_pin,plan.action_application_pin,plan.action_schema_pin,
                                  plan.capability_pin,plan.adapter_contract_pin,*plan.authorization_input_pins,*plan.predicted_effect_pins),"operation_plan_input")
            gate_ops=[]
            for assessment in gate_assessments:
                deps=(RecordDependency(RecordKind.OPERATION_PLAN,plan.plan_ref,1,plan_pin.record_fingerprint,"operation_plan"),)+self._deps(assessment.checked_pins,"operation_gate_input")
                gate_ops.append(self._upsert(RecordKind.OPERATION_GATE_ASSESSMENT,assessment,deps,f"persist hard-gate assessment {assessment.gate_ref}"))
            deps_auth=(RecordDependency(RecordKind.OPERATION_PLAN,plan.plan_ref,1,plan_pin.record_fingerprint,"operation_plan"),)+self._deps(authorization.checked_pins,"operation_authorization_input")+self._deps(authorization.gate_assessment_pins,"operation_gate_assessment")
            deps_journal=(RecordDependency(RecordKind.OPERATION_PLAN,plan.plan_ref,1,plan_pin.record_fingerprint,"operation_plan"),
                          RecordDependency(RecordKind.OPERATION_AUTHORIZATION,authorization.authorization_ref,1,auth_pin.record_fingerprint,"operation_authorization"))
            ops=(self._upsert(RecordKind.OPERATION_PLAN,plan,deps_plan,"persist exact immutable operation plan"),
                 *tuple(gate_ops),
                 self._upsert(RecordKind.OPERATION_AUTHORIZATION,authorization,deps_auth,"persist fresh hard-gate authorization"),
                 self._upsert(RecordKind.OPERATION_JOURNAL,journal,deps_journal,"journal PREPARED before external side effect"))
            patch=GraphPatch(
                patch_ref="graph-patch:operation-prepare:"+semantic_fingerprint("operation-prepare",(journal.journal_ref,snapshot.fingerprint),24),
                context_ref=plan.context_ref,scope_ref="phase16:operation",source_ref="source:phase16:operation-journal",
                permission_ref=plan.permission_ref,operations=ops,expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase16_journal_before_side_effect","phase16_exact_execution_authority"),metadata={"phase":16,"external_side_effect":False})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("operation prepare commit failed: "+"; ".join(result.errors))
        return journal

    def advance(self, journal: OperationJournalRecord, status: OperationJournalStatus, *, request_evidence_refs=(), response_evidence_refs=(), external_correlation_refs=(), submitted_at=None, observed_at=None):
        allowed = _ALLOWED_JOURNAL_TRANSITIONS.get(journal.status, set())
        if status not in allowed:
            raise ValueError(f"illegal operation journal transition: {journal.status.value}->{status.value}")
        latest=self.store.get_record(RecordKind.OPERATION_JOURNAL,journal.journal_ref)
        if latest is None or latest.revision != journal.revision or latest.record_fingerprint != record_fingerprints(RecordKind.OPERATION_JOURNAL,journal)[1]:
            raise ValueError("stale journal lifecycle transition")
        prior=_pin(RecordKind.OPERATION_JOURNAL,journal)
        next_record=replace(journal,revision=journal.revision+1,supersedes_revision=journal.revision,prior_journal_pin=prior,status=status,
                            submission_attempt=journal.submission_attempt+(1 if status==OperationJournalStatus.SUBMITTED else 0),
                            request_evidence_refs=tuple(sorted(set((*journal.request_evidence_refs,*request_evidence_refs)))),
                            response_evidence_refs=tuple(sorted(set((*journal.response_evidence_refs,*response_evidence_refs)))),
                            external_correlation_refs=tuple(sorted(set((*journal.external_correlation_refs,*external_correlation_refs)))),
                            submitted_at=submitted_at or journal.submitted_at,observed_at=observed_at or journal.observed_at)
        with self.store.snapshot() as snapshot:
            op=self._upsert(RecordKind.OPERATION_JOURNAL,next_record,(RecordDependency(RecordKind.OPERATION_JOURNAL,journal.journal_ref,journal.revision,prior.record_fingerprint,"journal_prior"),),
                            f"advance operation journal to {status.value}",expected_revision=journal.revision,expected_fingerprint=prior.record_fingerprint)
            patch=GraphPatch(patch_ref="graph-patch:operation-journal:"+semantic_fingerprint("operation-journal-advance",(journal.journal_ref,next_record.revision,snapshot.fingerprint),24),
                             context_ref=journal.context_ref,scope_ref="phase16:operation",source_ref="source:phase16:operation-journal",permission_ref=journal.permission_ref,
                             operations=(op,),expected_store_revision=snapshot.store_revision,metadata={"phase":16,"external_side_effect":False})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("journal advance failed: "+"; ".join(result.errors))
        return next_record

    def persist_result(self,result_record: OperationResultRecord):
        journal=self._exact(result_record.journal_pin)
        with self.store.snapshot() as snapshot:
            op=self._upsert(RecordKind.OPERATION_RESULT,result_record,(RecordDependency(RecordKind.OPERATION_JOURNAL,journal.record_ref,journal.revision,journal.record_fingerprint,"operation_journal"),),"persist observed operation result")
            patch=GraphPatch(patch_ref="graph-patch:operation-result:"+semantic_fingerprint("operation-result-patch",(result_record.result_ref,snapshot.fingerprint),24),
                             context_ref=result_record.context_ref,scope_ref="phase16:operation",source_ref="source:phase16:operation-result",permission_ref=result_record.permission_ref,
                             operations=(op,),expected_store_revision=snapshot.store_revision,metadata={"phase":16,"observation_only":True})
        commit=self.store.apply_patch(patch)
        if not commit.committed: raise RuntimeError("operation result commit failed: "+"; ".join(commit.errors))
        return commit

    def persist_observation(self,journal: OperationJournalRecord,result_record: OperationResultRecord,status: OperationJournalStatus, *, response_evidence_refs=(),external_correlation_refs=(),observed_at=None):
        """Atomically persist a durable adapter observation and its journal state.

        The external call has already happened.  This method guarantees that local
        success/failure/partial evidence cannot become durable without the matching
        journal lifecycle transition in the same GraphPatch. OUTCOME_UNKNOWN may
        remain on the existing journal revision while the observation record is
        persisted, because no stronger outcome has been established.
        """
        latest=self.store.get_record(RecordKind.OPERATION_JOURNAL,journal.journal_ref)
        current_fp=record_fingerprints(RecordKind.OPERATION_JOURNAL,journal)[1]
        if latest is None or latest.revision!=journal.revision or latest.record_fingerprint!=current_fp:
            raise ValueError("stale journal before observation persistence")
        if result_record.journal_pin != _pin(RecordKind.OPERATION_JOURNAL,journal):
            raise ValueError("operation result does not pin exact current observation journal")
        if status==journal.status:
            if status!=OperationJournalStatus.OUTCOME_UNKNOWN:
                raise ValueError("same-state observation persistence is allowed only for OUTCOME_UNKNOWN")
            return self.persist_result(result_record),journal
        if status not in _ALLOWED_JOURNAL_TRANSITIONS.get(journal.status,set()):
            raise ValueError(f"illegal observed journal transition: {journal.status.value}->{status.value}")
        prior=_pin(RecordKind.OPERATION_JOURNAL,journal)
        next_record=replace(
            journal,revision=journal.revision+1,supersedes_revision=journal.revision,prior_journal_pin=prior,status=status,
            response_evidence_refs=tuple(sorted(set((*journal.response_evidence_refs,*response_evidence_refs)))),
            external_correlation_refs=tuple(sorted(set((*journal.external_correlation_refs,*external_correlation_refs)))),
            observed_at=observed_at or journal.observed_at,
        )
        result_fp=record_fingerprints(RecordKind.OPERATION_RESULT,result_record)[1]
        with self.store.snapshot() as snapshot:
            result_op=self._upsert(
                RecordKind.OPERATION_RESULT,result_record,
                (RecordDependency(RecordKind.OPERATION_JOURNAL,journal.journal_ref,journal.revision,prior.record_fingerprint,"operation_journal"),),
                "persist observed operation result",
            )
            journal_op=self._upsert(
                RecordKind.OPERATION_JOURNAL,next_record,
                (RecordDependency(RecordKind.OPERATION_JOURNAL,journal.journal_ref,journal.revision,prior.record_fingerprint,"journal_prior"),
                 RecordDependency(RecordKind.OPERATION_RESULT,result_record.result_ref,result_record.revision,result_fp,"operation_result_observation")),
                f"atomically advance journal to observed outcome {status.value}",
                expected_revision=journal.revision,expected_fingerprint=prior.record_fingerprint,
            )
            patch=GraphPatch(
                patch_ref="graph-patch:operation-observation:"+semantic_fingerprint("operation-observation-patch",(result_record.result_ref,status.value,snapshot.fingerprint),24),
                context_ref=result_record.context_ref,scope_ref="phase16:operation",source_ref="source:phase16:operation-result",permission_ref=result_record.permission_ref,
                operations=(result_op,journal_op),expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase16_atomic_local_observation",),metadata={"phase":16,"observation_only":True,"external_side_effect":False},
            )
        commit=self.store.apply_patch(patch)
        if not commit.committed: raise RuntimeError("operation observation commit failed: "+"; ".join(commit.errors))
        return commit,next_record

    def persist_reconciliation(self,record: OperationReconciliationRecord):
        plan_stored=self._exact(record.plan_pin)
        result_stored=self._exact(record.result_pin)
        observed_journal_stored=self._exact(record.observed_journal_pin)
        plan=plan_stored.payload
        result=result_stored.payload
        journal=observed_journal_stored.payload
        if not isinstance(journal,OperationJournalRecord):
            raise ValueError("reconciliation observed_journal_pin must resolve an operation journal")
        if journal.journal_ref != result.journal_pin.record_ref:
            raise ValueError("reconciliation journal/result operation identity mismatch")
        if journal.status not in {OperationJournalStatus.OBSERVED_SUCCESS,OperationJournalStatus.OBSERVED_FAILURE,OperationJournalStatus.OBSERVED_PARTIAL}:
            raise ValueError("reconciliation requires exact observed terminal journal")
        # The observed journal revision must have been created by the exact result.
        result_edge=False
        for stored in self.store.records(RecordKind.DEPENDENCY):
            edge=stored.payload
            if (getattr(edge,'active',False) and getattr(edge,'dependent_kind',None)==RecordKind.OPERATION_JOURNAL
                and getattr(edge,'dependent_ref',None)==journal.journal_ref and getattr(edge,'dependent_revision',None)==journal.revision
                and getattr(edge,'prerequisite_kind',None)==RecordKind.OPERATION_RESULT and getattr(edge,'prerequisite_ref',None)==record.result_pin.record_ref
                and getattr(edge,'prerequisite_revision',None)==record.result_pin.revision and getattr(edge,'prerequisite_fingerprint',None)==record.result_pin.record_fingerprint):
                result_edge=True;break
        if not result_edge:
            raise ValueError("observed journal is not lineage-bound to the exact operation result")
        latest=self.store.get_record(RecordKind.OPERATION_JOURNAL,journal.journal_ref)
        if latest is None or latest.revision!=journal.revision or latest.record_fingerprint!=record.observed_journal_pin.record_fingerprint:
            raise ValueError("reconciliation requires current exact observed journal; retry/recovery advanced it")
        prior_journal=record.observed_journal_pin
        reconciled_journal=replace(journal,revision=journal.revision+1,supersedes_revision=journal.revision,prior_journal_pin=prior_journal,status=OperationJournalStatus.RECONCILED)
        deps=[RecordDependency(record.plan_pin.record_kind,record.plan_pin.record_ref,record.plan_pin.revision,record.plan_pin.record_fingerprint,"reconciliation_plan"),
              RecordDependency(record.result_pin.record_kind,record.result_pin.record_ref,record.result_pin.revision,record.result_pin.record_fingerprint,"reconciliation_result"),
              RecordDependency(record.observed_journal_pin.record_kind,record.observed_journal_pin.record_ref,record.observed_journal_pin.revision,record.observed_journal_pin.record_fingerprint,"reconciliation_observed_journal")]
        deps += [RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,"reconciliation_observation") for p in (*record.predicted_effect_pins,*record.observed_pins)]
        reconciliation_fp=record_fingerprints(RecordKind.OPERATION_RECONCILIATION,record)[1]
        with self.store.snapshot() as snapshot:
            reconcile_op=self._upsert(RecordKind.OPERATION_RECONCILIATION,record,tuple(deps),"persist exact result/journal-bound operation reconciliation; state mutation remains ordinary epistemic/transition work")
            journal_op=self._upsert(RecordKind.OPERATION_JOURNAL,reconciled_journal,
                (RecordDependency(RecordKind.OPERATION_JOURNAL,journal.journal_ref,journal.revision,prior_journal.record_fingerprint,"journal_prior"),
                 RecordDependency(RecordKind.OPERATION_RECONCILIATION,record.reconciliation_ref,1,reconciliation_fp,"operation_reconciliation")),
                "atomically mark journal reconciled after exact reconciliation",expected_revision=journal.revision,expected_fingerprint=prior_journal.record_fingerprint)
            decision_pin=plan.goal_decision_pin
            operations=[reconcile_op,journal_op]
            decision_current=self.store.get_record(decision_pin.record_kind,decision_pin.record_ref,decision_pin.revision)
            if decision_current is not None:
                if decision_current.record_fingerprint!=decision_pin.record_fingerprint:
                    raise ValueError("pre-operation goal decision identity changed unexpectedly")
                operations.append(PatchOperation(
                    operation_ref="patch-operation:operation-invalidates-goal:"+semantic_fingerprint("operation-invalidates-goal",(record.reconciliation_ref,decision_pin.key),20),
                    operation_kind=PatchOperationKind.TOMBSTONE,record_kind=decision_pin.record_kind,target_ref=decision_pin.record_ref,
                    record_revision=decision_pin.revision,expected_record_revision=decision_pin.revision,expected_record_fingerprint=decision_pin.record_fingerprint,
                    dependencies=(RecordDependency(RecordKind.OPERATION_RECONCILIATION,record.reconciliation_ref,1,reconciliation_fp,"operation_reconciliation"),),
                    reason="operation outcome consumed pre-operation goal decision; re-enter Phase15 before response planning"))
            # If the exact decision is already tombstoned/invalidated, refresh has already been forced;
            # reconciliation history and journal completion must not be stranded by a redundant tombstone.
            patch=GraphPatch(patch_ref="graph-patch:operation-reconcile:"+semantic_fingerprint("operation-reconcile",(record.reconciliation_ref,snapshot.fingerprint),24),
                context_ref=record.context_ref,scope_ref="phase16:reconciliation",source_ref="source:phase16:reconciliation",permission_ref=record.permission_ref,
                operations=tuple(operations),expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase16_reconcile_before_goal_refresh","phase16_result_observed_journal_exact_lineage"),
                metadata={"phase":16,"direct_state_mutation":False,"requires_phase15_refresh":True})
        commit=self.store.apply_patch(patch)
        if not commit.committed: raise RuntimeError("operation reconciliation commit failed: "+"; ".join(commit.errors))
        return commit,reconciled_journal



    def _adapter(self,plan): return self._exact(plan.adapter_contract_pin).payload
    def _exact(self,pin):
        s=self.store.get_record(pin.record_kind,pin.record_ref,pin.revision)
        if s is None or s.record_fingerprint!=pin.record_fingerprint: raise ValueError(f"stale exact operation pin: {pin.key}")
        return s
    @staticmethod
    def _deps(pins,kind): return tuple(RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,kind) for p in pins)
    @staticmethod
    def _upsert(kind,record,deps,reason,expected_revision=None,expected_fingerprint=None):
        return PatchOperation(operation_ref="patch-operation:phase16-operation:"+semantic_fingerprint("phase16-operation-op",(kind.value,record_ref(kind,record),record_revision(kind,record),reason),20),
                              operation_kind=PatchOperationKind.UPSERT,record_kind=kind,target_ref=record_ref(kind,record),record_revision=record_revision(kind,record),payload=encode_record(kind,record),
                              expected_record_revision=expected_revision,expected_record_fingerprint=expected_fingerprint,dependencies=deps,reason=reason)
