"""Commit-boundary invariants for Phase-17 realization authority."""
from __future__ import annotations
from ..storage.model import DependencyEdge,RecordKind
from ..learning.authority import record_supports_use
from ..learning.model import PromotionDecisionKind,PromotionDecisionRecord
from ..schema.model import SchemaLifecycleStatus,UseDecision,UseOperation
from .model import DeepClausePlanRecord,RealizationRequestRecord,ReferencePlanRecord,SurfaceCandidateRecord,SemanticAnalyzerContractRecord,SemanticRoundTripRecord,RoundTripDecision

class Phase17CommitValidator:
 def __init__(self,resolver):self.r=resolver
 def validate_operation(self,op,record):
  if op.record_kind==RecordKind.REALIZATION_REQUEST:
   if not isinstance(record,RealizationRequestRecord):raise ValueError('realization request type mismatch')
   self._require(op,record.response_uol_pin)
   response_current=self.r.resolve(record.response_uol_pin.record_kind,record.response_uol_pin.record_ref)
   if response_current is None or response_current.revision!=record.response_uol_pin.revision or response_current.record_fingerprint!=record.response_uol_pin.record_fingerprint:raise ValueError('realization request pins stale Response UOL')
   response=response_current.payload
   if getattr(response,'permission_ref',None) not in {'public',record.permission_ref}:raise ValueError('realization request broadens Response UOL permission scope')
   if not set(record.audience_refs).issubset(set(getattr(response,'audience_refs',()))):raise ValueError('realization request broadens authorized audience')
   if getattr(response,'sensitivity',record.sensitivity)!=record.sensitivity:raise ValueError('realization request changes sensitivity scope without an explicit lattice')
   for p in record.language_pack_pins:
    self._require(op,p)
    stored=self.r.resolve(p.record_kind,p.record_ref,p.revision)
    if stored is None or stored.permission_ref not in {None,'public',record.permission_ref}:raise ValueError('realization language pack permission is incompatible')
    if not self._language_use_authorized(p,UseOperation.REALIZE):raise ValueError(f'language pack is not REALIZE-authorized: {p.key}')
  elif op.record_kind==RecordKind.DEEP_CLAUSE_PLAN:
   if not isinstance(record,DeepClausePlanRecord):raise ValueError('deep clause plan type mismatch')
   self._require(op,record.request_pin);self._require(op,record.frame_pin)
   if not self._language_use_authorized(record.frame_pin,UseOperation.REALIZE):raise ValueError('deep clause plan uses non-REALIZE frame')
   self._require_in_request_pack(record.request_pin,record.frame_pin)
  elif op.record_kind==RecordKind.REFERENCE_PLAN:
   if not isinstance(record,ReferencePlanRecord):raise ValueError('reference plan type mismatch')
   self._require(op,record.request_pin);self._require(op,record.referent_pin);self._require(op,record.language_rule_pin)
   for p in (*record.competitor_pins,*record.allowed_identity_facet_pins):self._require(op,p)
   if not self._language_use_authorized(record.language_rule_pin,UseOperation.REALIZE):raise ValueError('reference plan uses non-REALIZE language rule')
   self._require_in_request_pack(record.request_pin,record.language_rule_pin)
  elif op.record_kind==RecordKind.SURFACE_CANDIDATE:
   if not isinstance(record,SurfaceCandidateRecord):raise ValueError('surface candidate type mismatch')
   self._require(op,record.request_pin)
   request_stored=self.r.resolve(record.request_pin.record_kind,record.request_pin.record_ref,record.request_pin.revision)
   if request_stored is None or not isinstance(request_stored.payload,RealizationRequestRecord):raise ValueError('surface candidate request is missing')
   for p in (*record.clause_pins,*record.frame_pins,*record.lexical_pins,*record.morphology_pins,*record.reference_pins,*record.linearization_pins):self._require(op,p)
   for p in (*record.frame_pins,*record.lexical_pins,*record.morphology_pins,*record.linearization_pins):
    if not self._language_use_authorized(p,UseOperation.REALIZE):raise ValueError(f'surface candidate uses non-REALIZE language authority: {p.key}')
    self._require_in_request_pack(record.request_pin,p)
  elif op.record_kind==RecordKind.SEMANTIC_ANALYZER_CONTRACT:
   if not isinstance(record,SemanticAnalyzerContractRecord):raise ValueError('semantic analyzer contract type mismatch')
   if record.active and not record.competence_case_refs:raise ValueError('active semantic analyzer contract requires competence')
   if record.supersedes_revision is not None and self.r.resolve(RecordKind.SEMANTIC_ANALYZER_CONTRACT,record.contract_ref,record.supersedes_revision) is None:raise ValueError('analyzer contract supersedes missing prior revision')
  elif op.record_kind==RecordKind.SEMANTIC_ROUNDTRIP:
   if not isinstance(record,SemanticRoundTripRecord):raise ValueError('roundtrip type mismatch')
   self._require(op,record.request_pin);self._require(op,record.surface_candidate_pin);self._require(op,record.analyzer_contract_pin)
   analyzer_contract=self.r.resolve(record.analyzer_contract_pin.record_kind,record.analyzer_contract_pin.record_ref,record.analyzer_contract_pin.revision)
   if analyzer_contract is None or analyzer_contract.record_fingerprint!=record.analyzer_contract_pin.record_fingerprint or not isinstance(analyzer_contract.payload,SemanticAnalyzerContractRecord) or not analyzer_contract.payload.active:raise ValueError('roundtrip requires active exact semantic analyzer contract')
   same=[x for x in self.r.records(RecordKind.SEMANTIC_ANALYZER_CONTRACT) if x.record_ref==analyzer_contract.record_ref and getattr(x.payload,'active',False)]
   superseded={getattr(x.payload,'supersedes_revision',None) for x in same if getattr(x.payload,'supersedes_revision',None) is not None}
   effective=[x for x in same if x.revision not in superseded]
   if len(effective)!=1 or effective[0].revision!=analyzer_contract.revision or effective[0].record_fingerprint!=analyzer_contract.record_fingerprint:raise ValueError('roundtrip analyzer contract is not singular effective authority')
   if analyzer_contract.payload.analyzer_ref!=record.analyzer_ref or analyzer_contract.payload.analyzer_revision!=record.analyzer_revision:raise ValueError('roundtrip analyzer identity differs from reviewed contract')
   request=self.r.resolve(record.request_pin.record_kind,record.request_pin.record_ref,record.request_pin.revision)
   if request is None or not isinstance(request.payload,RealizationRequestRecord):raise ValueError('roundtrip request is missing')
   response=self.r.resolve(request.payload.response_uol_pin.record_kind,request.payload.response_uol_pin.record_ref,request.payload.response_uol_pin.revision)
   if response is None:raise ValueError('roundtrip Response UOL is missing')
   expected=getattr(getattr(response.payload,'graph',None),'record_fingerprint',None)
   if record.expected_graph_fingerprint!=expected:raise ValueError('roundtrip expected fingerprint is not the exact Response UOL graph fingerprint')
   # Round-trip PASS is necessary for future emission, but does not itself authorize emission.
   if record.decision==RoundTripDecision.PASS and record.recovered_graph_fingerprint!=record.expected_graph_fingerprint:raise ValueError('roundtrip PASS fingerprint mismatch')
 def _require_in_request_pack(self,request_pin,language_pin):
  request=self.r.resolve(request_pin.record_kind,request_pin.record_ref,request_pin.revision)
  if request is None or not isinstance(request.payload,RealizationRequestRecord):raise ValueError('realization request missing for pack-closure validation')
  allowed={(p.record_ref,p.revision) for p in request.payload.language_pack_pins}
  stored=self.r.resolve(language_pin.record_kind,language_pin.record_ref,language_pin.revision)
  if stored is None:raise ValueError('language authority pin is missing')
  if language_pin.record_kind==RecordKind.LANGUAGE_PACK:
   packs={(stored.record_ref,stored.revision)}
  elif language_pin.record_kind==RecordKind.FORM_SENSE_LINK:
   form=self.r.resolve(RecordKind.LANGUAGE_FORM,stored.payload.form_ref,stored.payload.form_revision)
   sense=self.r.resolve(RecordKind.LEXICAL_SENSE,stored.payload.sense_ref,stored.payload.sense_revision)
   if form is None or sense is None:raise ValueError('form-sense link pack closure cannot resolve exact form/sense')
   packs={(form.payload.pack_ref,form.payload.pack_revision),(sense.payload.pack_ref,sense.payload.pack_revision)}
  else:
   packs={(getattr(stored.payload,'pack_ref',None),getattr(stored.payload,'pack_revision',None))}
  if not packs or any(pack not in allowed for pack in packs):raise ValueError(f'language authority escapes exact request pack closure: {language_pin.key}')
 def _language_use_authorized(self,pin,operation):
  stored=self.r.resolve(pin.record_kind,pin.record_ref,pin.revision)
  if stored is None or stored.record_fingerprint!=pin.record_fingerprint:return False
  if getattr(stored.payload,'lifecycle_status',None)!=SchemaLifecycleStatus.ACTIVE or not record_supports_use(pin.record_kind,stored.payload,operation):return False
  same=[x for x in self.r.records(pin.record_kind) if x.record_ref==pin.record_ref and getattr(x.payload,'lifecycle_status',None)==SchemaLifecycleStatus.ACTIVE]
  superseded={getattr(x.payload,'supersedes_revision',None) for x in same if getattr(x.payload,'supersedes_revision',None) is not None}
  effective=[x for x in same if x.revision not in superseded]
  if len(effective)!=1 or effective[0].revision!=pin.revision or effective[0].record_fingerprint!=pin.record_fingerprint:return False
  edges=[e.payload for e in self.r.records(RecordKind.DEPENDENCY) if isinstance(e.payload,DependencyEdge) and e.payload.active and e.payload.dependent_kind==pin.record_kind and e.payload.dependent_ref==pin.record_ref and e.payload.dependent_revision==pin.revision]
  promotion=[e for e in edges if e.prerequisite_kind==RecordKind.PROMOTION_DECISION]
  if not promotion:return getattr(stored,'layer',None)=='boot'
  for edge in promotion:
   decision=self.r.resolve(RecordKind.PROMOTION_DECISION,edge.prerequisite_ref,edge.prerequisite_revision)
   if decision is None or decision.record_fingerprint!=edge.prerequisite_fingerprint or not isinstance(decision.payload,PromotionDecisionRecord) or decision.payload.decision!=PromotionDecisionKind.PROMOTE:continue
   for grant in decision.payload.use_grants:
    if grant.operation==operation and grant.decision==UseDecision.ALLOW and grant.candidate_pin.record_kind==pin.record_kind and grant.candidate_pin.record_ref==pin.record_ref:
     if any(e.prerequisite_kind==grant.candidate_pin.record_kind and e.prerequisite_ref==grant.candidate_pin.record_ref and e.prerequisite_revision==grant.candidate_pin.revision and e.prerequisite_fingerprint==grant.candidate_pin.record_fingerprint for e in edges):return True
  return False
 def _require(self,op,pin):
  if not any(d.record_kind==pin.record_kind and d.record_ref==pin.record_ref and d.revision==pin.revision and d.fingerprint==pin.record_fingerprint for d in op.dependencies):raise ValueError(f'Phase17 record missing exact dependency: {pin.key}')
