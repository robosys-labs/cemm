"""Commit-boundary Phase-18 authority invariants."""
from __future__ import annotations

from ..realization.model import RoundTripDecision, SemanticRoundTripRecord
from ..storage.model import RecordKind
from .model import *


class Phase18CommitValidator:
    def __init__(self,resolver): self.r=resolver

    def validate_operation(self,op,record):
        k=op.record_kind
        if k==RecordKind.CHANNEL_ADAPTER_CONTRACT:
            if not isinstance(record,ChannelAdapterContractRecord):raise ValueError("channel adapter contract type mismatch")
            self._supersession(record,RecordKind.CHANNEL_ADAPTER_CONTRACT,record.contract_ref)
        elif k==RecordKind.LITERAL_EMISSION_POLICY:
            if not isinstance(record,LiteralEmissionPolicyRecord):raise ValueError("literal emission policy type mismatch")
            self._supersession(record,RecordKind.LITERAL_EMISSION_POLICY,record.policy_ref)
            for p in record.trigger_pins:self._require(op,p)
        elif k==RecordKind.EMISSION_GATE_ASSESSMENT:
            if not isinstance(record,EmissionGateAssessmentRecord):raise ValueError("emission gate assessment type mismatch")
            for p in record.checked_pins:self._require(op,p)
        elif k==RecordKind.EMISSION_AUTHORIZATION:
            if not isinstance(record,EmissionAuthorizationRecord):raise ValueError("emission authorization type mismatch")
            pins=(record.response_uol_pin,record.realization_request_pin,record.surface_candidate_pin,record.semantic_roundtrip_pin,record.goal_decision_pin,record.channel_contract_pin,*record.gate_assessment_pins,*record.operation_result_pins,*record.operation_reconciliation_pins)
            for p in pins:self._require(op,p)
            if record.literal_policy_pin is not None:self._require(op,record.literal_policy_pin)
            assessments=[self._exact(p).payload for p in record.gate_assessment_pins]
            if set(record.passed_gates)!={x.gate_ref for x in assessments if x.passed}:raise ValueError("emission authorization passed gates differ from exact assessments")
            if set(record.failed_gates)!={x.gate_ref for x in assessments if not x.passed}:raise ValueError("emission authorization failed gates differ from exact assessments")
            if record.decision==EmissionAuthorizationDecision.ALLOW and any(not x.passed for x in assessments):raise ValueError("ALLOW emission contains failed hard gate")
            rt=self._exact(record.semantic_roundtrip_pin).payload
            if not isinstance(rt,SemanticRoundTripRecord) or rt.decision!=RoundTripDecision.PASS or rt.additions or rt.losses or rt.drift_refs:raise ValueError("emission requires exact semantic round-trip PASS")
        elif k==RecordKind.EMISSION_JOURNAL:
            if not isinstance(record,EmissionJournalRecord):raise ValueError("emission journal type mismatch")
            self._require(op,record.authorization_pin)
            if record.revision>1:
                if record.prior_journal_pin is None:self._fail("journal revision lacks exact prior pin")
                self._require(op,record.prior_journal_pin)
                prior=self._exact(record.prior_journal_pin).payload
                allowed={
                  EmissionJournalStatus.PREPARED:{EmissionJournalStatus.SUBMITTED,EmissionJournalStatus.CANCELLED_BEFORE_SUBMIT,EmissionJournalStatus.FAILED_BEFORE_EMIT},
                  EmissionJournalStatus.SUBMITTED:{EmissionJournalStatus.CHANNEL_ACKNOWLEDGED,EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.DELIVERY_UNKNOWN,EmissionJournalStatus.FAILED_AFTER_SUBMIT},
                  EmissionJournalStatus.CHANNEL_ACKNOWLEDGED:{EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.DELIVERY_UNKNOWN,EmissionJournalStatus.FAILED_AFTER_SUBMIT,EmissionJournalStatus.FINALIZED},
                  EmissionJournalStatus.DELIVERY_CONFIRMED:{EmissionJournalStatus.FINALIZED},EmissionJournalStatus.DELIVERY_UNKNOWN:{EmissionJournalStatus.DELIVERY_CONFIRMED,EmissionJournalStatus.FAILED_AFTER_SUBMIT,EmissionJournalStatus.FINALIZED},
                  EmissionJournalStatus.FAILED_BEFORE_EMIT:{EmissionJournalStatus.FINALIZED},EmissionJournalStatus.FAILED_AFTER_SUBMIT:{EmissionJournalStatus.FINALIZED},EmissionJournalStatus.CANCELLED_BEFORE_SUBMIT:{EmissionJournalStatus.FINALIZED},EmissionJournalStatus.FINALIZED:set()}
                if record.status not in allowed.get(prior.status,set()):raise ValueError("illegal durable emission journal transition")
        elif k==RecordKind.EMISSION:
            if not isinstance(record,EmissionRecord):raise ValueError("emission type mismatch")
            for p in (record.journal_pin,record.authorization_pin,record.response_uol_pin,record.surface_candidate_pin):self._require(op,p)
            auth=self._exact(record.authorization_pin).payload
            if auth.decision!=EmissionAuthorizationDecision.ALLOW:raise ValueError("emission cannot depend on non-ALLOW authorization")
            if record.surface_sha256!=auth.surface_sha256 or record.response_uol_pin!=auth.response_uol_pin or record.surface_candidate_pin!=auth.surface_candidate_pin:raise ValueError("emission differs from authorized surface/meaning")
        elif k==RecordKind.EMISSION_ANOMALY:
            if not isinstance(record,EmissionAnomalyRecord):raise ValueError("emission anomaly type mismatch")
            for p in (record.journal_pin,record.authorization_pin,record.channel_contract_pin):self._require(op,p)
            auth=self._exact(record.authorization_pin).payload
            if record.authorized_surface_sha256!=auth.surface_sha256 or record.channel_contract_pin!=auth.channel_contract_pin:raise ValueError("emission anomaly differs from exact authorization/channel contract")
            if not record.no_output_discourse_authority:raise ValueError("emission anomaly may never become normal output discourse authority")
        elif k==RecordKind.SILENCE_OUTCOME:
            if not isinstance(record,SilenceOutcomeRecord):raise ValueError("silence outcome type mismatch")
            for p in (record.goal_decision_pin,*record.selected_goal_pins,*record.policy_pins):self._require(op,p)
        elif k==RecordKind.OUTPUT_DISCOURSE_ACT:
            if not isinstance(record,OutputDiscourseActRecord):raise ValueError("output discourse type mismatch")
            for p in (record.emission_pin,record.response_uol_pin,*record.goal_candidate_pins,*record.operation_result_pins):self._require(op,p)
            emission=self._exact(record.emission_pin).payload
            if not isinstance(emission,EmissionRecord):raise ValueError("output discourse requires actual authorized emission observation")
            speaker_deps=[d for d in op.dependencies if d.record_kind==RecordKind.REFERENT and d.record_ref==record.speaker_ref and d.dependency_kind=="output_speaker"]
            if len(speaker_deps)!=1:raise ValueError("output discourse requires one exact durable speaker dependency")
            d=speaker_deps[0]
            speaker=self.r.resolve(RecordKind.REFERENT,d.record_ref,d.revision)
            if speaker is None or speaker.record_fingerprint!=d.fingerprint:raise ValueError("output discourse speaker dependency is stale")
            addressee_deps=[d for d in op.dependencies if d.record_kind==RecordKind.REFERENT and d.dependency_kind=="output_addressee"]
            if {d.record_ref for d in addressee_deps}!=set(record.addressee_refs) or len(addressee_deps)!=len(record.addressee_refs):raise ValueError("output discourse requires one exact durable dependency per addressee")
            for ad in addressee_deps:
                stored_addressee=self.r.resolve(RecordKind.REFERENT,ad.record_ref,ad.revision)
                if stored_addressee is None or stored_addressee.record_fingerprint!=ad.fingerprint:raise ValueError("output discourse addressee dependency is stale")
            response=self._exact(record.response_uol_pin).payload
            if tuple(record.goal_candidate_pins)!=tuple(response.selected_goal_pins):raise ValueError("output discourse goals differ from exact Response-UOL selected goals")
            response_ops={p for p in response.source_pins if p.record_kind==RecordKind.OPERATION_RESULT}
            if set(record.operation_result_pins)!=response_ops:raise ValueError("output discourse operation results differ from exact Response-UOL sources")
            targets={target for p in record.goal_candidate_pins for target in getattr(self._exact(p).payload,"target_refs",())}
            if not set(record.acknowledgement_target_refs).issubset(targets):raise ValueError("output acknowledgement target not authorized by selected goals")
        elif k==RecordKind.OUTPUT_COMMITMENT:
            if not isinstance(record,OutputCommitmentRecord):raise ValueError("output commitment type mismatch")
            self._require(op,record.discourse_pin)
            for p in record.correction_pins:self._require(op,p)
            self._supersession(record,RecordKind.OUTPUT_COMMITMENT,record.commitment_ref)
        elif k==RecordKind.COMMON_GROUND:
            if not isinstance(record,CommonGroundRecord):raise ValueError("common-ground type mismatch")
            for p in (*record.supporting_discourse_pins,*record.supporting_emission_pins,*record.opposing_pins):self._require(op,p)
            self._supersession(record,RecordKind.COMMON_GROUND,record.ground_ref)
            if record.status in {CommonGroundStatus.RECEIVED_EVIDENCE,CommonGroundStatus.ACKNOWLEDGED,CommonGroundStatus.SHARED,CommonGroundStatus.OPPOSED,CommonGroundStatus.DISPUTED} and not record.evidence_refs:raise ValueError("evidence-bearing common-ground status requires evidence")
        elif k==RecordKind.OUTPUT_REFERENCE_ANCHOR:
            if not isinstance(record,OutputReferenceAnchorRecord):raise ValueError("output reference anchor type mismatch")
            for p in (record.response_uol_pin,record.discourse_pin):self._require(op,p)
            if record.target_pin is not None:self._require(op,record.target_pin)
        elif k==RecordKind.OUTPUT_CORRECTION:
            if not isinstance(record,OutputCorrectionRecord):raise ValueError("output correction type mismatch")
            for p in (record.correcting_discourse_pin,*record.prior_commitment_pins,*record.prior_common_ground_pins):self._require(op,p)
            correcting=self._exact(record.correcting_discourse_pin).payload
            if not isinstance(correcting,OutputDiscourseActRecord) or not set(record.replacement_target_refs).issubset(set(correcting.response_root_refs)):raise ValueError("correction replacement targets are not grounded in correcting discourse roots")
            prior_targets={target for p in record.prior_commitment_pins for target in getattr(self._exact(p).payload,"target_refs",())}
            if not set(record.opposition_target_refs).issubset(prior_targets):raise ValueError("correction opposition targets are not prior committed targets")

    def _exact(self,p):
        s=self.r.resolve(p.record_kind,p.record_ref,p.revision)
        if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f"stale exact Phase18 dependency: {p.key}")
        return s
    def _require(self,op,p):
        if not any(d.record_kind==p.record_kind and d.record_ref==p.record_ref and d.revision==p.revision and d.fingerprint==p.record_fingerprint for d in op.dependencies):raise ValueError(f"Phase18 record missing exact dependency: {p.key}")
    def _supersession(self,record,kind,ref):
        prior=getattr(record,"supersedes_revision",None)
        if prior is not None and self.r.resolve(kind,ref,prior) is None:raise ValueError("supersedes missing exact prior revision")
    @staticmethod
    def _fail(msg):raise ValueError(msg)
