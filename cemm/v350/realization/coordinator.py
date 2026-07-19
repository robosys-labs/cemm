"""Atomic persistence for realization requests, plans, candidates and semantic round-trip proofs."""
from __future__ import annotations
from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record,record_fingerprints,record_ref,record_revision
from ..storage.model import GraphPatch,PatchOperation,PatchOperationKind,RecordDependency,RecordKind
from .model import RealizationRequestRecord,DeepClausePlanRecord,ReferencePlanRecord,SurfaceCandidateRecord,SemanticRoundTripRecord,RoundTripDecision

class RealizationCommitCoordinator:
 def __init__(self,store):self.store=store
 def commit_candidate(self,request:RealizationRequestRecord,clauses:tuple[DeepClausePlanRecord,...],reference_plans:tuple[ReferencePlanRecord,...],candidate:SurfaceCandidateRecord):
  response=self._exact(request.response_uol_pin)
  response_current=self.store.get_record(request.response_uol_pin.record_kind,request.response_uol_pin.record_ref)
  if response_current is None or response_current.revision!=request.response_uol_pin.revision or response_current.record_fingerprint!=request.response_uol_pin.record_fingerprint:raise ValueError('stale Response UOL before realization commit')
  request_pin=PinnedRecord(RecordKind.REALIZATION_REQUEST,request.request_ref,1,record_fingerprints(RecordKind.REALIZATION_REQUEST,request)[1])
  if candidate.request_pin!=request_pin:raise ValueError('surface candidate does not pin exact request')
  with self.store.snapshot() as snapshot:
   if snapshot.store_revision!=candidate.snapshot_revision or snapshot.fingerprint!=candidate.snapshot_fingerprint:
    raise ValueError('store changed after realization compile; rebuild candidate from the current exact snapshot')
   ops=[]
   reqdeps=(RecordDependency(request.response_uol_pin.record_kind,request.response_uol_pin.record_ref,request.response_uol_pin.revision,request.response_uol_pin.record_fingerprint,'realization_response_uol'),)+tuple(RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,'realization_language_pack') for p in request.language_pack_pins)
   ops.append(self._upsert(RecordKind.REALIZATION_REQUEST,request,reqdeps,'persist exact realization request'))
   clausefps={}
   for clause in clauses:
    deps=(RecordDependency(RecordKind.REALIZATION_REQUEST,request.request_ref,1,request_pin.record_fingerprint,'realization_request'),RecordDependency(clause.frame_pin.record_kind,clause.frame_pin.record_ref,clause.frame_pin.revision,clause.frame_pin.record_fingerprint,'argument_frame'))
    ops.append(self._upsert(RecordKind.DEEP_CLAUSE_PLAN,clause,deps,'persist deep clause plan without surface authority'));clausefps[clause.clause_ref]=record_fingerprints(RecordKind.DEEP_CLAUSE_PLAN,clause)[1]
   candidate_clause_map={(p.record_ref,p.revision,p.record_fingerprint) for p in candidate.clause_pins}
   committed_clause_map={(ref,1,fp) for ref,fp in clausefps.items()}
   if candidate_clause_map!=committed_clause_map:raise ValueError('surface candidate clause pins do not match committed deep clause plans')
   reference_fps={}
   for reference in reference_plans:
    deps=(RecordDependency(RecordKind.REALIZATION_REQUEST,request.request_ref,1,request_pin.record_fingerprint,'realization_request'),
          RecordDependency(reference.referent_pin.record_kind,reference.referent_pin.record_ref,reference.referent_pin.revision,reference.referent_pin.record_fingerprint,'reference_referent'),
          RecordDependency(reference.language_rule_pin.record_kind,reference.language_rule_pin.record_ref,reference.language_rule_pin.revision,reference.language_rule_pin.record_fingerprint,'reference_language_rule'))
    deps += tuple(RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,'reference_competitor') for p in reference.competitor_pins)
    deps += tuple(RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,'reference_identity_facet') for p in reference.allowed_identity_facet_pins)
    ops.append(self._upsert(RecordKind.REFERENCE_PLAN,reference,deps,'persist privacy-scoped reference plan'))
    reference_fps[reference.reference_ref]=record_fingerprints(RecordKind.REFERENCE_PLAN,reference)[1]
   if set(reference_fps) != {p.record_ref for p in candidate.reference_pins}:
    raise ValueError('surface candidate reference pins do not match committed reference plans')
   deps=[RecordDependency(RecordKind.REALIZATION_REQUEST,request.request_ref,1,request_pin.record_fingerprint,'realization_request')]
   deps += [RecordDependency(RecordKind.DEEP_CLAUSE_PLAN,p.record_ref,p.revision,p.record_fingerprint,'deep_clause_plan') for p in candidate.clause_pins]
   for kind,pins,label in ((None,candidate.frame_pins,'argument_frame'),(None,candidate.lexical_pins,'lexicalization'),(None,candidate.morphology_pins,'morphology'),(None,candidate.reference_pins,'reference'),(None,candidate.linearization_pins,'linearization')):
    deps += [RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,label) for p in pins]
   ops.append(self._upsert(RecordKind.SURFACE_CANDIDATE,candidate,tuple(deps),'persist unauthorized surface candidate pending round-trip'))
   patch=GraphPatch(patch_ref='graph-patch:realization-candidate:'+semantic_fingerprint('realization-candidate',(candidate.candidate_ref,snapshot.fingerprint),24),context_ref=response.context_ref or getattr(response.payload,'context_ref','actual'),scope_ref='phase17:realization',source_ref='source:phase17:realization',permission_ref=request.permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,validation_requirements=('phase17_no_domain_sentence_templates','phase17_exact_language_authority'),metadata={'phase':17,'emission_authorized':False})
  result=self.store.apply_patch(patch)
  if not result.committed:raise RuntimeError('realization candidate commit failed: '+'; '.join(result.errors))
  return result
 def commit_roundtrip(self,record:SemanticRoundTripRecord):
  self._exact(record.request_pin);self._exact(record.surface_candidate_pin)
  with self.store.snapshot() as snapshot:
   deps=(RecordDependency(record.request_pin.record_kind,record.request_pin.record_ref,record.request_pin.revision,record.request_pin.record_fingerprint,'realization_request'),RecordDependency(record.surface_candidate_pin.record_kind,record.surface_candidate_pin.record_ref,record.surface_candidate_pin.revision,record.surface_candidate_pin.record_fingerprint,'surface_candidate'))
   op=self._upsert(RecordKind.SEMANTIC_ROUNDTRIP,record,deps,'persist semantic round-trip verification; PASS required before emission')
   patch=GraphPatch(patch_ref='graph-patch:semantic-roundtrip:'+semantic_fingerprint('semantic-roundtrip-patch',(record.roundtrip_ref,snapshot.fingerprint),24),context_ref='realization:verification',scope_ref='phase17:realization',source_ref='source:phase17:roundtrip-verifier',permission_ref='internal',operations=(op,),expected_store_revision=snapshot.store_revision,metadata={'phase':17,'roundtrip_passed':record.decision==RoundTripDecision.PASS})
  result=self.store.apply_patch(patch)
  if not result.committed:raise RuntimeError('round-trip commit failed: '+'; '.join(result.errors))
  return result
 def _exact(self,p):
  s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
  if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f'stale realization dependency: {p.key}')
  return s
 @staticmethod
 def _upsert(kind,record,deps,reason):
  return PatchOperation(operation_ref='patch-operation:phase17:'+semantic_fingerprint('phase17-op',(kind.value,record_ref(kind,record),record_revision(kind,record),reason),20),operation_kind=PatchOperationKind.UPSERT,record_kind=kind,target_ref=record_ref(kind,record),record_revision=record_revision(kind,record),payload=encode_record(kind,record),dependencies=deps,reason=reason)
