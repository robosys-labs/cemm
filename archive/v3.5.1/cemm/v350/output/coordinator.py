"""Atomic persistence boundaries for Phase-18 emission and output discourse."""
from __future__ import annotations
from dataclasses import replace

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record,record_fingerprints,record_ref,record_revision
from ..storage.model import GraphPatch,PatchOperation,PatchOperationKind,RecordDependency,RecordKind
from .gate import pin
from .model import *


def _dep(p:PinnedRecord,kind:str): return RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,kind)

def _upsert(kind,record,deps,reason,*,expected_revision=None,expected_fingerprint=None):
    return PatchOperation(operation_ref="patch-operation:phase18:"+semantic_fingerprint("phase18-op",(kind.value,record_ref(kind,record),record_revision(kind,record),reason),20),operation_kind=PatchOperationKind.UPSERT,record_kind=kind,target_ref=record_ref(kind,record),record_revision=record_revision(kind,record),payload=encode_record(kind,record),dependencies=tuple(deps),reason=reason,expected_record_revision=expected_revision,expected_record_fingerprint=expected_fingerprint)


_ALLOWED={
    EmissionJournalStatus.PREPARED:{EmissionJournalStatus.SUBMITTED,EmissionJournalStatus.CANCELLED_BEFORE_SUBMIT,EmissionJournalStatus.FAILED_BEFORE_EMIT},
    EmissionJournalStatus.SUBMITTED:{EmissionJournalStatus.CHANNEL_ACKNOWLEDGED,EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.DELIVERY_UNKNOWN,EmissionJournalStatus.FAILED_AFTER_SUBMIT},
    EmissionJournalStatus.CHANNEL_ACKNOWLEDGED:{EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.DELIVERY_UNKNOWN,EmissionJournalStatus.FAILED_AFTER_SUBMIT,EmissionJournalStatus.FINALIZED},
    EmissionJournalStatus.DELIVERY_CONFIRMED:{EmissionJournalStatus.FINALIZED},
    EmissionJournalStatus.DELIVERY_UNKNOWN:{EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.FAILED_AFTER_SUBMIT,EmissionJournalStatus.FINALIZED},
    EmissionJournalStatus.FAILED_BEFORE_EMIT:{EmissionJournalStatus.FINALIZED},EmissionJournalStatus.FAILED_AFTER_SUBMIT:{EmissionJournalStatus.FINALIZED},
    EmissionJournalStatus.CANCELLED_BEFORE_SUBMIT:{EmissionJournalStatus.FINALIZED},EmissionJournalStatus.FINALIZED:set(),
}


class EmissionJournalCoordinator:
    def __init__(self,store): self.store=store

    def prepare(self,authorization:EmissionAuthorizationRecord,assessments:tuple[EmissionGateAssessmentRecord,...],channel:ChannelAdapterContractRecord,*,idempotency_key:str|None=None):
        if authorization.decision!=EmissionAuthorizationDecision.ALLOW: raise ValueError("cannot prepare non-allowed emission")
        if channel.idempotency_mode==EmissionIdempotencyMode.CLIENT_KEY and not idempotency_key: raise ValueError("client-key channel contract requires durable idempotency key before submit")
        if channel.idempotency_mode==EmissionIdempotencyMode.NONE and idempotency_key is not None: raise ValueError("idempotency key supplied to channel contract that declares no idempotency semantics")
        ap=pin(RecordKind.EMISSION_AUTHORIZATION,authorization); cp=pin(RecordKind.CHANNEL_ADAPTER_CONTRACT,channel)
        supplied=tuple(pin(RecordKind.EMISSION_GATE_ASSESSMENT,x) for x in assessments)
        if set(supplied)!=set(authorization.gate_assessment_pins): raise ValueError("gate assessment set differs from authorization")
        if authorization.channel_contract_pin!=cp: raise ValueError("authorization channel pin mismatch")
        if set(authorization.passed_gates)!={x.gate_ref for x in assessments if x.passed} or any(not x.passed for x in assessments): raise ValueError("ALLOW requires exactly passing supplied hard gates")
        with self.store.snapshot() as snapshot:
            if snapshot.store_revision!=authorization.snapshot_revision or snapshot.fingerprint!=authorization.snapshot_fingerprint: raise ValueError("store changed after emission authorization; re-authorize")
            for p in (authorization.response_uol_pin,authorization.realization_request_pin,authorization.surface_candidate_pin,authorization.semantic_roundtrip_pin,authorization.goal_decision_pin,authorization.channel_contract_pin,*authorization.operation_result_pins,*authorization.operation_reconciliation_pins):
                self._exact(p)
            journal=EmissionJournalRecord(journal_ref="emission-journal:"+semantic_fingerprint("emission-journal-ref",(authorization.authorization_ref,authorization.surface_sha256,channel.channel_ref),24),authorization_pin=ap,status=EmissionJournalStatus.PREPARED,idempotency_key=idempotency_key,adapter_ref=channel.adapter_ref,adapter_revision=channel.adapter_revision,surface_sha256=authorization.surface_sha256,context_ref=authorization.context_ref,permission_ref=authorization.permission_ref,sensitivity=authorization.sensitivity)
            ops=[]
            for a in assessments:
                deps=tuple(_dep(p,"emission_gate_input") for p in a.checked_pins)
                ops.append(_upsert(RecordKind.EMISSION_GATE_ASSESSMENT,a,deps,"persist proof-bearing emission hard gate"))
            authdeps=tuple(_dep(p,"emission_authorization_input") for p in (authorization.response_uol_pin,authorization.realization_request_pin,authorization.surface_candidate_pin,authorization.semantic_roundtrip_pin,authorization.goal_decision_pin,authorization.channel_contract_pin,*authorization.operation_result_pins,*authorization.operation_reconciliation_pins,*authorization.gate_assessment_pins))
            if authorization.literal_policy_pin is not None: authdeps=(*authdeps,_dep(authorization.literal_policy_pin,"literal_emission_policy"))
            ops.append(_upsert(RecordKind.EMISSION_AUTHORIZATION,authorization,authdeps,"persist exact emission authorization"))
            ops.append(_upsert(RecordKind.EMISSION_JOURNAL,journal,(_dep(ap,"emission_authorization"),),"journal PREPARED before channel side effect"))
            patch=GraphPatch(patch_ref="graph-patch:emission-prepare:"+semantic_fingerprint("emission-prepare",(journal.journal_ref,snapshot.fingerprint),24),context_ref=authorization.context_ref,scope_ref="phase18:emission",source_ref="source:phase18:emission-gate",permission_ref=authorization.permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,validation_requirements=("phase18_no_emission_without_authorization","phase18_gate_assessments_exact"),metadata={"phase":18,"external_side_effect":False})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("emission prepare failed: "+"; ".join(result.errors))
        return journal

    def advance(self,journal:EmissionJournalRecord,status:EmissionJournalStatus,*,request_evidence_refs=(),response_evidence_refs=(),external_correlation_refs=(),submitted_at=None,observed_at=None):
        if status not in _ALLOWED.get(journal.status,set()): raise ValueError(f"illegal emission journal transition: {journal.status.value}->{status.value}")
        latest=self.store.get_record(RecordKind.EMISSION_JOURNAL,journal.journal_ref)
        fp=record_fingerprints(RecordKind.EMISSION_JOURNAL,journal)[1]
        if latest is None or latest.revision!=journal.revision or latest.record_fingerprint!=fp: raise ValueError("stale emission journal transition")
        prior=pin(RecordKind.EMISSION_JOURNAL,journal)
        nxt=replace(journal,revision=journal.revision+1,supersedes_revision=journal.revision,prior_journal_pin=prior,status=status,submission_attempt=journal.submission_attempt+(1 if status==EmissionJournalStatus.SUBMITTED else 0),request_evidence_refs=tuple(sorted(set((*journal.request_evidence_refs,*request_evidence_refs)))),response_evidence_refs=tuple(sorted(set((*journal.response_evidence_refs,*response_evidence_refs)))),external_correlation_refs=tuple(sorted(set((*journal.external_correlation_refs,*external_correlation_refs)))),submitted_at=submitted_at or journal.submitted_at,observed_at=observed_at or journal.observed_at)
        with self.store.snapshot() as snapshot:
            op=_upsert(RecordKind.EMISSION_JOURNAL,nxt,(_dep(prior,"emission_journal_prior"),_dep(journal.authorization_pin,"emission_authorization")),f"advance emission journal to {status.value}",expected_revision=journal.revision,expected_fingerprint=fp)
            patch=GraphPatch(patch_ref="graph-patch:emission-journal:"+semantic_fingerprint("emission-journal-transition",(prior.key,status.value,snapshot.fingerprint),24),context_ref=journal.context_ref,scope_ref="phase18:emission",source_ref="source:phase18:channel-executor",permission_ref=journal.permission_ref,operations=(op,),expected_store_revision=snapshot.store_revision,metadata={"phase":18,"journal_status":status.value})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("emission journal transition failed: "+"; ".join(result.errors))
        return nxt

    def persist_observation(self,journal:EmissionJournalRecord,emission:EmissionRecord,observed_status:EmissionJournalStatus):
        if observed_status not in {EmissionJournalStatus.CHANNEL_ACKNOWLEDGED,EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.DELIVERY_UNKNOWN}: raise ValueError("emission observation requires an observed channel/delivery status")
        if observed_status not in _ALLOWED.get(journal.status,set()): raise ValueError("illegal observed emission transition")
        jp=pin(RecordKind.EMISSION_JOURNAL,journal)
        if emission.journal_pin!=jp: raise ValueError("emission record does not pin exact pre-observation journal")
        auth=self._exact(emission.authorization_pin).payload
        if emission.surface_sha256!=auth.surface_sha256 or emission.response_uol_pin!=auth.response_uol_pin or emission.surface_candidate_pin!=auth.surface_candidate_pin: raise ValueError("emission observation differs from exact authorization")
        next_journal=replace(journal,revision=journal.revision+1,supersedes_revision=journal.revision,prior_journal_pin=jp,status=observed_status,response_evidence_refs=tuple(sorted(set((*journal.response_evidence_refs,*emission.evidence_refs)))),external_correlation_refs=tuple(sorted(set((*journal.external_correlation_refs,*emission.external_correlation_refs)))),observed_at=emission.emitted_at or journal.observed_at)
        with self.store.snapshot() as snapshot:
            efp=record_fingerprints(RecordKind.EMISSION_JOURNAL,journal)[1]
            deps=(_dep(jp,"emission_journal"),_dep(emission.authorization_pin,"emission_authorization"),_dep(emission.response_uol_pin,"emission_response_uol"),_dep(emission.surface_candidate_pin,"emission_surface"))
            eop=_upsert(RecordKind.EMISSION,emission,deps,"persist actual channel emission observation")
            jop=_upsert(RecordKind.EMISSION_JOURNAL,next_journal,(_dep(jp,"emission_journal_prior"),_dep(journal.authorization_pin,"emission_authorization"),_dep(pin(RecordKind.EMISSION,emission),"emission_observation")),f"advance journal atomically to {observed_status.value}",expected_revision=journal.revision,expected_fingerprint=efp)
            patch=GraphPatch(patch_ref="graph-patch:emission-observation:"+semantic_fingerprint("emission-observation",(emission.emission_ref,jp.key,observed_status.value),24),context_ref=emission.context_ref,scope_ref="phase18:emission",source_ref="source:phase18:channel-observation",permission_ref=emission.permission_ref,operations=(eop,jop),expected_store_revision=snapshot.store_revision,validation_requirements=("phase18_observation_and_journal_atomic",),metadata={"phase":18})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("emission observation commit failed: "+"; ".join(result.errors))
        return next_journal

    def persist_anomaly(self,journal:EmissionJournalRecord,anomaly:EmissionAnomalyRecord,observed_status:EmissionJournalStatus=EmissionJournalStatus.DELIVERY_UNKNOWN):
        if observed_status not in {EmissionJournalStatus.DELIVERY_UNKNOWN,EmissionJournalStatus.FAILED_AFTER_SUBMIT}:
            raise ValueError("emission anomaly requires unknown/failure journal status")
        if observed_status not in _ALLOWED.get(journal.status,set()):raise ValueError("illegal anomaly journal transition")
        jp=pin(RecordKind.EMISSION_JOURNAL,journal)
        if anomaly.journal_pin!=jp:raise ValueError("emission anomaly must pin exact pre-observation journal")
        auth=self._exact(anomaly.authorization_pin).payload
        if anomaly.authorized_surface_sha256!=auth.surface_sha256:raise ValueError("anomaly authorized surface differs from authorization")
        if anomaly.channel_contract_pin!=auth.channel_contract_pin:raise ValueError("anomaly channel contract differs from authorization")
        next_journal=replace(journal,revision=journal.revision+1,supersedes_revision=journal.revision,prior_journal_pin=jp,status=observed_status,response_evidence_refs=tuple(sorted(set((*journal.response_evidence_refs,*anomaly.evidence_refs)))),external_correlation_refs=tuple(sorted(set((*journal.external_correlation_refs,*anomaly.external_correlation_refs)))),observed_at=anomaly.detected_at or journal.observed_at)
        with self.store.snapshot() as snapshot:
            jfp=record_fingerprints(RecordKind.EMISSION_JOURNAL,journal)[1]
            ap=pin(RecordKind.EMISSION_ANOMALY,anomaly)
            adeps=(_dep(jp,"emission_anomaly_journal"),_dep(anomaly.authorization_pin,"emission_anomaly_authorization"),_dep(anomaly.channel_contract_pin,"emission_anomaly_channel_contract"))
            aop=_upsert(RecordKind.EMISSION_ANOMALY,anomaly,adeps,"persist observed unauthorized/ambiguous channel emission anomaly; no discourse authority")
            jop=_upsert(RecordKind.EMISSION_JOURNAL,next_journal,(_dep(jp,"emission_journal_prior"),_dep(journal.authorization_pin,"emission_authorization"),_dep(ap,"emission_anomaly")),f"advance journal atomically to {observed_status.value} after anomaly",expected_revision=journal.revision,expected_fingerprint=jfp)
            patch=GraphPatch(patch_ref="graph-patch:emission-anomaly:"+semantic_fingerprint("emission-anomaly-patch",(anomaly.anomaly_ref,jp.key,observed_status.value),24),context_ref=anomaly.context_ref,scope_ref="phase18:emission",source_ref="source:phase18:channel-anomaly",permission_ref=anomaly.permission_ref,operations=(aop,jop),expected_store_revision=snapshot.store_revision,validation_requirements=("phase18_anomaly_audited_without_discourse_authority",),metadata={"phase":18,"content_left_system":anomaly.content_left_system,"authorized_emission":False})
        result=self.store.apply_patch(patch)
        if not result.committed:raise RuntimeError("emission anomaly commit failed: "+"; ".join(result.errors))
        return next_journal

    def _exact(self,p):
        s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        if s is None or s.record_fingerprint!=p.record_fingerprint: raise ValueError(f"stale exact Phase18 dependency: {p.key}")
        return s


class OutputDiscourseCoordinator:
    def __init__(self,store): self.store=store

    def commit_emitted(self,emission:EmissionRecord,*,speaker_ref:str,commitment_kind_ref:str,acknowledgement_target_refs:tuple[str,...]=(),operation_result_pins:tuple[PinnedRecord,...]=(),reason_refs:tuple[str,...]=()):
        ep=pin(RecordKind.EMISSION,emission); stored=self._exact(ep)
        auth=self._exact(emission.authorization_pin).payload; response=self._exact(emission.response_uol_pin).payload
        if auth.decision!=EmissionAuthorizationDecision.ALLOW: raise ValueError("output discourse requires allowed emission")
        if emission.status not in {EmissionStatus.CHANNEL_ACCEPTED,EmissionStatus.DELIVERED,EmissionStatus.UNKNOWN_DELIVERY}: raise ValueError("invalid emission observation status")
        goals=response.selected_goal_pins; roots=tuple(x.ref for x in response.graph.root_refs)
        if not roots: raise ValueError("emitted output requires semantic response roots")
        goal_records=[self._exact(p).payload for p in goals]
        goal_targets={target for g in goal_records for target in getattr(g,"target_refs",())}
        if not set(acknowledgement_target_refs).issubset(goal_targets):raise ValueError("acknowledgement target is not authorized by selected target-bearing goals")
        response_operation_pins=tuple(p for p in response.source_pins if p.record_kind==RecordKind.OPERATION_RESULT)
        if operation_result_pins and set(operation_result_pins)!=set(response_operation_pins):raise ValueError("output operation-result lineage differs from exact Response-UOL sources")
        operation_result_pins=response_operation_pins
        for p in operation_result_pins:self._exact(p)
        speaker_stored=self.store.get_record(RecordKind.REFERENT,speaker_ref)
        if speaker_stored is None:raise ValueError("output speaker must resolve to a durable referent")
        speaker_pin=PinnedRecord(speaker_stored.record_kind,speaker_stored.record_ref,speaker_stored.revision,speaker_stored.record_fingerprint)
        addressee_pins=[]
        for ref in emission.audience_refs:
            stored_addressee=self.store.get_record(RecordKind.REFERENT,ref)
            if stored_addressee is None:raise ValueError(f"output addressee must resolve to a durable referent: {ref}")
            addressee_pins.append(PinnedRecord(stored_addressee.record_kind,stored_addressee.record_ref,stored_addressee.revision,stored_addressee.record_fingerprint))
        discourse=OutputDiscourseActRecord(discourse_ref="output-discourse:"+semantic_fingerprint("output-discourse",(ep.key,response.response_ref,goals,speaker_pin.key),24),emission_pin=ep,response_uol_pin=emission.response_uol_pin,goal_candidate_pins=goals,speaker_ref=speaker_ref,addressee_refs=emission.audience_refs,response_root_refs=roots,acknowledgement_target_refs=acknowledgement_target_refs,operation_result_pins=operation_result_pins,reason_refs=reason_refs,evidence_refs=emission.evidence_refs,context_ref=emission.context_ref,permission_ref=emission.permission_ref,emitted_at=emission.emitted_at)
        dp=pin(RecordKind.OUTPUT_DISCOURSE_ACT,discourse)
        commitments=[]; grounds=[]; anchors=[]
        channel_contract=self._exact(auth.channel_contract_pin).payload
        if emission.status==EmissionStatus.UNKNOWN_DELIVERY:
            initial=CommonGroundStatus.UNKNOWN_DELIVERY
        elif emission.status==EmissionStatus.DELIVERED and bool(getattr(channel_contract,"delivery_ack_proves_recipient_receipt",False)):
            initial=CommonGroundStatus.RECEIVED_EVIDENCE
        else:
            initial=CommonGroundStatus.EMITTED
        participants=tuple(dict.fromkeys((speaker_ref,*emission.audience_refs)))
        if len(participants)<2: raise ValueError("output common ground requires speaker and at least one addressee")
        for ordinal,target in enumerate(roots):
            commitment=OutputCommitmentRecord(commitment_ref="output-commitment:"+semantic_fingerprint("output-commitment",(dp.key,target,commitment_kind_ref),24),discourse_pin=dp,target_refs=(target,),commitment_kind_ref=commitment_kind_ref,common_ground_proposal=True,context_ref=emission.context_ref,permission_ref=emission.permission_ref)
            commitments.append(commitment)
            ground=CommonGroundRecord(ground_ref="common-ground:"+semantic_fingerprint("common-ground",(emission.context_ref,participants,target),24),subject_ref=target,participant_refs=participants,status=initial,supporting_discourse_pins=(dp,),supporting_emission_pins=(ep,),evidence_refs=emission.evidence_refs,context_ref=emission.context_ref,permission_ref=emission.permission_ref,valid_time_ref=emission.emitted_at)
            grounds.append(ground)
            candidates=self.store.resolve_any(target)
            exact=None
            if len(candidates)==1: exact=PinnedRecord(candidates[0].record_kind,candidates[0].record_ref,candidates[0].revision,candidates[0].record_fingerprint)
            anchors.append(OutputReferenceAnchorRecord(anchor_ref="output-anchor:"+semantic_fingerprint("output-reference-anchor",(dp.key,target,ordinal),24),target_kind_ref="response_root",target_ref=target,target_pin=exact,response_uol_pin=emission.response_uol_pin,discourse_pin=dp,goal_refs=tuple(p.record_ref for p in goals),audience_refs=emission.audience_refs,salience=max(0.0,1.0-(ordinal*0.05)),ordinal=ordinal,context_ref=emission.context_ref,permission_ref=emission.permission_ref,time_ref=emission.emitted_at))
        with self.store.snapshot() as snapshot:
            ops=[_upsert(RecordKind.OUTPUT_DISCOURSE_ACT,discourse,(_dep(ep,"emitted_output"),_dep(emission.response_uol_pin,"response_uol"),_dep(speaker_pin,"output_speaker"),*tuple(_dep(p,"output_addressee") for p in addressee_pins),*tuple(_dep(p,"response_goal") for p in goals),*tuple(_dep(p,"operation_result") for p in operation_result_pins)),"persist emitted semantic discourse event")]
            for c in commitments: ops.append(_upsert(RecordKind.OUTPUT_COMMITMENT,c,(_dep(dp,"output_discourse"),),"persist system output commitment; not world truth"))
            for g in grounds: ops.append(_upsert(RecordKind.COMMON_GROUND,g,(_dep(dp,"common_ground_discourse"),_dep(ep,"common_ground_emission")),"persist evidence-relative common-ground projection"))
            for a in anchors:
                deps=[_dep(dp,"reference_discourse"),_dep(emission.response_uol_pin,"reference_response_uol")]
                if a.target_pin is not None: deps.append(_dep(a.target_pin,"reference_target"))
                ops.append(_upsert(RecordKind.OUTPUT_REFERENCE_ANCHOR,a,tuple(deps),"persist semantic output reference anchor"))
            patch=GraphPatch(patch_ref="graph-patch:output-discourse:"+semantic_fingerprint("output-discourse-patch",(ep.key,dp.key),24),context_ref=emission.context_ref,scope_ref="phase18:output-discourse",source_ref="source:phase18:output-discourse",permission_ref=emission.permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,validation_requirements=("phase18_no_emission_no_common_ground","phase18_common_ground_not_truth"),metadata={"phase":18})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("output discourse commit failed: "+"; ".join(result.errors))
        return discourse,tuple(commitments),tuple(grounds),tuple(anchors)

    def _exact(self,p):
        s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        if s is None or s.record_fingerprint!=p.record_fingerprint: raise ValueError(f"stale output dependency: {p.key}")
        return s


class CommonGroundCoordinator:
    _ALLOWED={
      CommonGroundStatus.PROPOSED:{CommonGroundStatus.EMITTED,CommonGroundStatus.RETRACTED},
      CommonGroundStatus.EMITTED:{CommonGroundStatus.RECEIVED_EVIDENCE,CommonGroundStatus.UNKNOWN_DELIVERY,CommonGroundStatus.OPPOSED,CommonGroundStatus.RETRACTED},
      CommonGroundStatus.UNKNOWN_DELIVERY:{CommonGroundStatus.RECEIVED_EVIDENCE,CommonGroundStatus.OPPOSED,CommonGroundStatus.RETRACTED},
      CommonGroundStatus.RECEIVED_EVIDENCE:{CommonGroundStatus.ACKNOWLEDGED,CommonGroundStatus.OPPOSED,CommonGroundStatus.DISPUTED,CommonGroundStatus.RETRACTED},
      CommonGroundStatus.ACKNOWLEDGED:{CommonGroundStatus.SHARED,CommonGroundStatus.OPPOSED,CommonGroundStatus.DISPUTED,CommonGroundStatus.RETRACTED},
      CommonGroundStatus.SHARED:{CommonGroundStatus.OPPOSED,CommonGroundStatus.DISPUTED,CommonGroundStatus.RETRACTED,CommonGroundStatus.SUPERSEDED},
      CommonGroundStatus.OPPOSED:{CommonGroundStatus.DISPUTED,CommonGroundStatus.RETRACTED,CommonGroundStatus.SUPERSEDED},
      CommonGroundStatus.DISPUTED:{CommonGroundStatus.ACKNOWLEDGED,CommonGroundStatus.OPPOSED,CommonGroundStatus.RETRACTED,CommonGroundStatus.SUPERSEDED},
      CommonGroundStatus.RETRACTED:set(),CommonGroundStatus.SUPERSEDED:set(),
    }
    def __init__(self,store):self.store=store
    def advance(self,current:CommonGroundRecord,status:CommonGroundStatus,*,evidence_refs:tuple[str,...],supporting_discourse_pins:tuple[PinnedRecord,...]=(),opposing_pins:tuple[PinnedRecord,...]=()):
        if status not in self._ALLOWED.get(current.status,set()): raise ValueError(f"illegal common-ground transition {current.status.value}->{status.value}")
        if status in {CommonGroundStatus.RECEIVED_EVIDENCE,CommonGroundStatus.ACKNOWLEDGED,CommonGroundStatus.SHARED,CommonGroundStatus.OPPOSED,CommonGroundStatus.DISPUTED} and not evidence_refs: raise ValueError("evidence-bearing common-ground transition requires evidence")
        latest=self.store.get_record(RecordKind.COMMON_GROUND,current.ground_ref); fp=record_fingerprints(RecordKind.COMMON_GROUND,current)[1]
        if latest is None or latest.revision!=current.revision or latest.record_fingerprint!=fp: raise ValueError("stale common-ground transition")
        prior=pin(RecordKind.COMMON_GROUND,current)
        nxt=replace(current,revision=current.revision+1,supersedes_revision=current.revision,status=status,supporting_discourse_pins=tuple(sorted(set((*current.supporting_discourse_pins,*supporting_discourse_pins)),key=lambda p:p.key)),opposing_pins=tuple(sorted(set((*current.opposing_pins,*opposing_pins)),key=lambda p:p.key)),evidence_refs=tuple(sorted(set((*current.evidence_refs,*evidence_refs)))))
        with self.store.snapshot() as snapshot:
            deps=[_dep(prior,"common_ground_prior"),*(_dep(p,"common_ground_support") for p in supporting_discourse_pins),*(_dep(p,"common_ground_opposition") for p in opposing_pins)]
            op=_upsert(RecordKind.COMMON_GROUND,nxt,tuple(deps),f"advance common ground to {status.value}",expected_revision=current.revision,expected_fingerprint=fp)
            patch=GraphPatch(patch_ref="graph-patch:common-ground:"+semantic_fingerprint("common-ground-transition",(prior.key,status.value,tuple(evidence_refs)),24),context_ref=current.context_ref,scope_ref="phase18:common-ground",source_ref="source:phase18:common-ground",permission_ref=current.permission_ref,operations=(op,),expected_store_revision=snapshot.store_revision,metadata={"phase":18})
        result=self.store.apply_patch(patch)
        if not result.committed: raise RuntimeError("common-ground update failed: "+"; ".join(result.errors))
        return nxt

class SilenceOutcomeCoordinator:
    def __init__(self,store):self.store=store
    def commit(self,record:SilenceOutcomeRecord):
        with self.store.snapshot() as snapshot:
            if snapshot.store_revision!=record.snapshot_revision or snapshot.fingerprint!=record.snapshot_fingerprint:
                raise ValueError("stale silence decision snapshot")
            deps=[_dep(record.goal_decision_pin,"silence_goal_decision"),*(_dep(p,"silence_selected_goal") for p in record.selected_goal_pins),*(_dep(p,"silence_policy") for p in record.policy_pins)]
            op=_upsert(RecordKind.SILENCE_OUTCOME,record,tuple(deps),"persist auditable selected no-output outcome; no fake emission")
            patch=GraphPatch(patch_ref="graph-patch:silence:"+semantic_fingerprint("silence-patch",(record.silence_ref,snapshot.fingerprint),24),context_ref=record.context_ref,scope_ref="phase18:silence",source_ref="source:phase18:silence",permission_ref=record.permission_ref,operations=(op,),expected_store_revision=snapshot.store_revision,validation_requirements=("phase18_silence_not_emission",),metadata={"phase":18,"emitted":False})
        result=self.store.apply_patch(patch)
        if not result.committed:raise RuntimeError("silence outcome commit failed: "+"; ".join(result.errors))
        return result


class OutputCorrectionCoordinator:
    def __init__(self,store):self.store=store
    def commit(self,correction:OutputCorrectionRecord):
        correcting=self._exact(correction.correcting_discourse_pin)
        correcting_payload=correcting.payload
        if not isinstance(correcting_payload,OutputDiscourseActRecord):raise ValueError("correction requires an exact correcting output discourse act")
        if not set(correction.replacement_target_refs).issubset(set(correcting_payload.response_root_refs)):raise ValueError("correction replacement targets must be asserted by the correcting discourse")
        cp=pin(RecordKind.OUTPUT_CORRECTION,correction)
        revised_commitments=[];revised_ground=[];prior_targets=set()
        for p in correction.prior_commitment_pins:
            stored=self._exact(p);item=stored.payload
            prior_targets.update(item.target_refs)
            latest=self.store.get_record(RecordKind.OUTPUT_COMMITMENT,item.commitment_ref)
            if latest is None or latest.revision!=p.revision or latest.record_fingerprint!=p.record_fingerprint:raise ValueError("correction may target only current exact output commitment")
            revised_commitments.append(replace(item,revision=item.revision+1,supersedes_revision=item.revision,status=OutputCommitmentStatus.CORRECTED,correction_pins=tuple(sorted(set((*item.correction_pins,cp)),key=lambda x:x.key))))
        if not set(correction.opposition_target_refs).issubset(prior_targets):raise ValueError("correction opposition targets must be prior committed targets")
        for p in correction.prior_common_ground_pins:
            stored=self._exact(p);item=stored.payload
            latest=self.store.get_record(RecordKind.COMMON_GROUND,item.ground_ref)
            if latest is None or latest.revision!=p.revision or latest.record_fingerprint!=p.record_fingerprint:raise ValueError("correction may target only current exact common-ground projection")
            status=CommonGroundStatus.DISPUTED if correction.opposition_target_refs else CommonGroundStatus.SUPERSEDED
            opposing=item.opposing_pins
            if correction.opposition_target_refs:
                opposing=tuple(sorted(set((*opposing,correction.correcting_discourse_pin)),key=lambda x:x.key))
            revised_ground.append(replace(item,revision=item.revision+1,supersedes_revision=item.revision,status=status,opposing_pins=opposing,evidence_refs=tuple(sorted(set((*item.evidence_refs,*correction.evidence_refs))))))
        with self.store.snapshot() as snapshot:
            deps=[_dep(correction.correcting_discourse_pin,"correction_discourse"),*(_dep(p,"correction_prior_commitment") for p in correction.prior_commitment_pins),*(_dep(p,"correction_prior_common_ground") for p in correction.prior_common_ground_pins)]
            ops=[_upsert(RecordKind.OUTPUT_CORRECTION,correction,tuple(deps),"persist immutable output correction lineage")]
            for prior,new in zip(correction.prior_commitment_pins,revised_commitments):
                ops.append(_upsert(RecordKind.OUTPUT_COMMITMENT,new,(_dep(prior,"output_commitment_prior"),_dep(cp,"output_correction")),"supersede corrected output commitment",expected_revision=prior.revision,expected_fingerprint=prior.record_fingerprint))
            for prior,new in zip(correction.prior_common_ground_pins,revised_ground):
                ops.append(_upsert(RecordKind.COMMON_GROUND,new,(_dep(prior,"common_ground_prior"),_dep(cp,"output_correction")),"recompute common ground after correction",expected_revision=prior.revision,expected_fingerprint=prior.record_fingerprint))
            patch=GraphPatch(patch_ref="graph-patch:output-correction:"+semantic_fingerprint("output-correction-patch",(correction.correction_ref,snapshot.fingerprint),24),context_ref=correction.context_ref,scope_ref="phase18:output-correction",source_ref="source:phase18:output-correction",permission_ref=correction.permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,validation_requirements=("phase18_correction_preserves_emission_history","phase18_correction_invalidates_projections"),metadata={"phase":18,"historical_emission_deleted":False})
        result=self.store.apply_patch(patch)
        if not result.committed:raise RuntimeError("output correction commit failed: "+"; ".join(result.errors))
        return correction,tuple(revised_commitments),tuple(revised_ground)
    def _exact(self,p):
        s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f"stale correction dependency: {p.key}")
        return s
