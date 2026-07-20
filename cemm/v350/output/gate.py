"""Phase-18 emission authorization gate.

This is the sole authority deciding whether an already verified surface may leave
CEMM. Round-trip PASS is necessary but never sufficient.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping, Protocol

from ..learning.model import PinnedRecord
from ..operations.model import OperationResultRecord, OperationResultStatus, OperationReconciliationRecord
from ..realization.model import RealizationRequestRecord, RoundTripDecision, SemanticRoundTripRecord, SurfaceCandidateRecord
from ..response.model import ResponseUOLRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import record_fingerprints, record_ref, record_revision
from ..storage.model import RecordKind
from .model import (
    ChannelAdapterContractRecord, EmissionAuthorizationDecision, EmissionAuthorizationRecord,
    EmissionGateAssessmentRecord, LiteralEmissionPolicyRecord,
)


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    passed: bool
    checked_pins: tuple[PinnedRecord, ...]
    authorization_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()
    evaluator_ref: str = "evaluator:phase18:external"
    evaluator_revision: str = "1"


class GateEvaluator(Protocol):
    def evaluate(self, *, gate_ref: str, store, substrate: Mapping[str, object]) -> GateEvaluation: ...


def pin(kind: RecordKind, record) -> PinnedRecord:
    return PinnedRecord(kind, record_ref(kind, record), record_revision(kind, record), record_fingerprints(kind, record)[1])


def surface_sha256(surface: str) -> str:
    return hashlib.sha256(surface.encode("utf-8")).hexdigest()


class EmissionGate:
    REQUIRED_GATES = (
        "response_current", "goal_current", "realization_current", "roundtrip_passed",
        "candidate_exact", "permission_audience", "channel_compatible", "policy_safety",
        "operation_freshness", "qualification_preserved",
    )

    def __init__(self, store, evaluators: Mapping[str, GateEvaluator] | None = None) -> None:
        self.store = store
        self.evaluators = dict(evaluators or {})

    def authorize(
        self, *, response: ResponseUOLRecord, request: RealizationRequestRecord,
        candidate: SurfaceCandidateRecord, roundtrip: SemanticRoundTripRecord,
        channel: ChannelAdapterContractRecord, audience_refs: tuple[str, ...],
        operation_results: tuple[OperationResultRecord, ...] = (),
        operation_reconciliations: tuple[OperationReconciliationRecord, ...] = (),
        literal_policy: LiteralEmissionPolicyRecord | None = None,
    ) -> tuple[EmissionAuthorizationRecord, tuple[EmissionGateAssessmentRecord, ...]]:
        rp=pin(RecordKind.RESPONSE_UOL,response); qp=pin(RecordKind.REALIZATION_REQUEST,request)
        cp=pin(RecordKind.SURFACE_CANDIDATE,candidate); tp=pin(RecordKind.SEMANTIC_ROUNDTRIP,roundtrip)
        gp=response.goal_decision_pin; chp=pin(RecordKind.CHANNEL_ADAPTER_CONTRACT,channel)
        result_pins=tuple(pin(RecordKind.OPERATION_RESULT,x) for x in operation_results)
        reconciliation_pins=tuple(pin(RecordKind.OPERATION_RECONCILIATION,x) for x in operation_reconciliations)
        literal_pin=None if literal_policy is None else pin(RecordKind.LITERAL_EMISSION_POLICY,literal_policy)
        with self.store.snapshot() as snapshot:
            substrate={"response":response,"request":request,"candidate":candidate,"roundtrip":roundtrip,"channel":channel,
                       "audience_refs":audience_refs,"operation_results":operation_results,"operation_reconciliations":operation_reconciliations,
                       "literal_policy":literal_policy,"snapshot":snapshot}
            builtins={
                "response_current": self._response_current(rp,response),
                "goal_current": self._goal_current(gp,response),
                "realization_current": self._realization_current(rp,qp,cp,tp,request,candidate,roundtrip),
                "roundtrip_passed": self._roundtrip_passed(rp,cp,roundtrip),
                "candidate_exact": self._candidate_exact(cp,candidate),
                "permission_audience": self._permission_audience(rp,qp,cp,chp,response,request,candidate,channel,audience_refs),
                "channel_compatible": self._channel_compatible(chp,channel,request,candidate),
                "operation_freshness": self._operation_freshness(response,result_pins,reconciliation_pins,operation_results,operation_reconciliations),
            }
            assessments=[]
            for gate_ref in self.REQUIRED_GATES:
                evaluation=builtins.get(gate_ref)
                if evaluation is None:
                    evaluator=self.evaluators.get(gate_ref)
                    if evaluator is None:
                        evaluation=GateEvaluation(False,(rp,cp),reason_refs=(f"missing_required_evaluator:{gate_ref}",),evaluator_ref="evaluator:phase18:missing")
                    else:
                        evaluation=evaluator.evaluate(gate_ref=gate_ref,store=self.store,substrate=substrate)
                assessment=EmissionGateAssessmentRecord(
                    assessment_ref="emission-gate:"+semantic_fingerprint("emission-gate-assessment",(gate_ref,snapshot.fingerprint,evaluation),24),
                    gate_ref=gate_ref,passed=evaluation.passed,evaluator_ref=evaluation.evaluator_ref,evaluator_revision=evaluation.evaluator_revision,
                    checked_pins=evaluation.checked_pins,authorization_refs=evaluation.authorization_refs,proof_refs=evaluation.proof_refs,reason_refs=evaluation.reason_refs,
                    context_ref=response.context_ref,permission_ref=response.permission_ref,snapshot_revision=snapshot.store_revision,snapshot_fingerprint=snapshot.fingerprint)
                assessments.append(assessment)
            # Literal policies are explicit exceptions and never inferred from surface text.
            literal_required=bool(candidate.metadata.get("literal_policy_required",False))
            if literal_required:
                ok,reason=self._literal_policy(response,candidate,literal_policy)
                assessments.append(EmissionGateAssessmentRecord(
                    assessment_ref="emission-gate:"+semantic_fingerprint("literal-emission-gate",(snapshot.fingerprint,candidate.candidate_ref,reason),24),
                    gate_ref="literal_policy_exact",passed=ok,evaluator_ref="evaluator:phase18:literal-policy",evaluator_revision="1",
                    checked_pins=(rp,cp) if literal_pin is None else (rp,cp,literal_pin),reason_refs=() if ok else (reason,),context_ref=response.context_ref,
                    permission_ref=response.permission_ref,snapshot_revision=snapshot.store_revision,snapshot_fingerprint=snapshot.fingerprint))
            passed=tuple(sorted(a.gate_ref for a in assessments if a.passed)); failed=tuple(sorted(a.gate_ref for a in assessments if not a.passed))
            decision=EmissionAuthorizationDecision.ALLOW if not failed else EmissionAuthorizationDecision.DENY
            auth=EmissionAuthorizationRecord(
                authorization_ref="emission-auth:"+semantic_fingerprint("emission-authorization",(snapshot.fingerprint,rp.key,cp.key,chp.key,audience_refs,passed,failed),24),
                response_uol_pin=rp,realization_request_pin=qp,surface_candidate_pin=cp,semantic_roundtrip_pin=tp,goal_decision_pin=gp,channel_contract_pin=chp,
                gate_assessment_pins=tuple(pin(RecordKind.EMISSION_GATE_ASSESSMENT,a) for a in assessments),decision=decision,audience_refs=audience_refs,
                surface_sha256=surface_sha256(candidate.surface),passed_gates=passed,failed_gates=failed,operation_result_pins=result_pins,
                operation_reconciliation_pins=reconciliation_pins,literal_policy_pin=literal_pin,
                authorization_refs=tuple(sorted({r for a in assessments for r in a.authorization_refs})),context_ref=response.context_ref,
                permission_ref=response.permission_ref,sensitivity=response.sensitivity,snapshot_revision=snapshot.store_revision,snapshot_fingerprint=snapshot.fingerprint)
        return auth,tuple(assessments)

    def _exact(self,p: PinnedRecord):
        s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        return s is not None and s.record_fingerprint==p.record_fingerprint

    def _effective_active(self,kind:RecordKind,ref:str,revision:int):
        rows=[x.payload for x in self.store.records(kind,all_revisions=True) if x.record_ref==ref and getattr(x.payload,"active",False)]
        superseded={x.supersedes_revision for x in rows if getattr(x,"supersedes_revision",None) is not None}
        effective=[x for x in rows if x.revision not in superseded]
        return len(effective)==1 and effective[0].revision==revision

    def _response_current(self,p,response):
        current=self.store.get_record(p.record_kind,p.record_ref)
        ok=current is not None and current.revision==p.revision and current.record_fingerprint==p.record_fingerprint
        return GateEvaluation(ok,(p,),reason_refs=() if ok else ("stale_response_uol",),evaluator_ref="evaluator:phase18:response-current")

    def _goal_current(self,p,response):
        current=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        ok=current is not None and current.record_fingerprint==p.record_fingerprint
        if ok:
            selected={x.record_ref for x in response.selected_goal_pins}
            ok=(selected==set(getattr(current.payload,"selected_goal_refs",()))
                and all(self._exact(x) for x in response.selected_goal_pins))
        return GateEvaluation(ok,(p,*response.selected_goal_pins),reason_refs=() if ok else ("stale_or_mismatched_goal_decision",),evaluator_ref="evaluator:phase18:goal-current")

    def _realization_current(self,rp,qp,cp,tp,request,candidate,roundtrip):
        ok=all(self._exact(p) for p in (rp,qp,cp,tp)) and request.response_uol_pin==rp and candidate.request_pin==qp and roundtrip.request_pin==qp and roundtrip.surface_candidate_pin==cp
        return GateEvaluation(ok,(rp,qp,cp,tp),reason_refs=() if ok else ("realization_chain_not_exact",),evaluator_ref="evaluator:phase18:realization-current")

    def _roundtrip_passed(self,rp,cp,roundtrip):
        response=self.store.get_record(rp.record_kind,rp.record_ref,rp.revision)
        expected=getattr(getattr(None if response is None else response.payload,"graph",None),"record_fingerprint",None)
        ok=(roundtrip.decision==RoundTripDecision.PASS and bool(roundtrip.proof_refs)
            and not roundtrip.additions and not roundtrip.losses and not roundtrip.drift_refs
            and roundtrip.expected_graph_fingerprint==expected and roundtrip.recovered_graph_fingerprint==expected)
        return GateEvaluation(ok,(rp,cp),proof_refs=roundtrip.proof_refs,reason_refs=() if ok else ("semantic_roundtrip_not_exact_pass",),evaluator_ref="evaluator:phase18:roundtrip")

    def _candidate_exact(self,cp,candidate):
        stored=self.store.get_record(cp.record_kind,cp.record_ref,cp.revision)
        ok=(stored is not None and stored.record_fingerprint==cp.record_fingerprint
            and isinstance(stored.payload,SurfaceCandidateRecord)
            and bool(candidate.surface)
            and surface_sha256(stored.payload.surface)==surface_sha256(candidate.surface))
        return GateEvaluation(ok,(cp,),reason_refs=() if ok else ("surface_candidate_not_exact",),evaluator_ref="evaluator:phase18:candidate-exact")

    def _permission_audience(self,rp,qp,cp,chp,response,request,candidate,channel,audience):
        ok=set(audience).issubset(set(response.audience_refs)) and set(audience).issubset(set(request.audience_refs))
        ok=ok and request.permission_ref in {"public",response.permission_ref} and candidate.permission_ref in {"public",response.permission_ref}
        # Channel-contract access scope is authority metadata, not content scope.
        # Content/audience scope is checked only against the exact response/request/candidate lineage.
        return GateEvaluation(ok,(rp,qp,cp,chp),reason_refs=() if ok else ("permission_or_audience_scope_widened",),evaluator_ref="evaluator:phase18:permission-audience")

    def _channel_compatible(self,chp,channel,request,candidate):
        ok=self._exact(chp) and self._effective_active(chp.record_kind,chp.record_ref,chp.revision)
        ok=ok and (not channel.allowed_language_tags or request.language_tag in channel.allowed_language_tags)
        ok=ok and len(candidate.surface.encode("utf-8"))<=channel.max_payload_bytes
        if channel.transformation_refs and (not channel.content_preserving_transform_only) and not channel.requires_post_transform_roundtrip:
            ok=False
        return GateEvaluation(ok,(chp,),reason_refs=() if ok else ("channel_contract_incompatible_or_inactive",),evaluator_ref="evaluator:phase18:channel-compatible")

    def _operation_freshness(self,response,result_pins,reconciliation_pins,results,reconciliations):
        # Operation reports are explicit Response-UOL source lineage, never optional metadata hints.
        reported=tuple(p for p in response.source_pins if p.record_kind==RecordKind.OPERATION_RESULT)
        reported_keys={(p.key,p.record_fingerprint) for p in reported}
        supplied_keys={(p.key,p.record_fingerprint) for p in result_pins}
        ok=reported_keys==supplied_keys
        for p in (*result_pins,*reconciliation_pins):
            ok=ok and self._exact(p)
        reconciliation_by_result={(r.result_pin.key,r.result_pin.record_fingerprint) for r in reconciliations}
        expected_reconciled={(p.key,p.record_fingerprint) for p,result in zip(result_pins,results) if result.status!=OperationResultStatus.UNKNOWN}
        ok=ok and reconciliation_by_result==expected_reconciled
        # Non-UNKNOWN operation results need semantic re-entry substrate, not only
        # adapter reports, before they can support surface emission.
        for reconciliation in reconciliations:
            matching=next(
                (
                    result
                    for pin_value,result in zip(result_pins,results)
                    if pin_value.record_ref==reconciliation.result_pin.record_ref
                ),
                None,
            )
            if matching is not None and matching.status!=OperationResultStatus.UNKNOWN:
                ok=ok and bool(reconciliation.observed_pins)
        # No unrelated reconciliation may be attached to this emission authorization.
        ok=ok and all(r.result_pin.record_ref in {p.record_ref for p in result_pins} for r in reconciliations)
        checked=tuple((*reported,*reconciliation_pins)) or (response.goal_decision_pin,)
        return GateEvaluation(ok,checked,reason_refs=() if ok else ("operation_result_not_fresh_exact_or_reconciled",),evaluator_ref="evaluator:phase18:operation-freshness")

    def _literal_policy(self,response,candidate,policy):
        if policy is None:return False,"literal_policy_missing"
        pp=pin(RecordKind.LITERAL_EMISSION_POLICY,policy)
        if not self._exact(pp) or not self._effective_active(pp.record_kind,pp.record_ref,pp.revision):return False,"literal_policy_not_effective"
        if policy.surface_sha256!=surface_sha256(candidate.surface):return False,"literal_surface_hash_mismatch"
        if policy.expected_graph_fingerprint!=response.graph.record_fingerprint:return False,"literal_graph_mismatch"
        allowed_trigger_keys={(p.key,p.record_fingerprint) for p in (*response.source_pins,*response.selected_goal_pins)}
        for trigger in policy.trigger_pins:
            if not self._exact(trigger):return False,"literal_trigger_stale"
            if (trigger.key,trigger.record_fingerprint) not in allowed_trigger_keys:return False,"literal_trigger_not_in_response_lineage"
        goals=[]
        for p in response.selected_goal_pins:
            s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
            if s is not None and s.record_fingerprint==p.record_fingerprint:
                goals.append((getattr(s.payload,"goal_schema_ref",None),getattr(s.payload,"goal_schema_revision",None)))
        if not set(goals).intersection(set(policy.response_goal_schema_pins)):return False,"literal_goal_policy_mismatch"
        return True,"ok"
