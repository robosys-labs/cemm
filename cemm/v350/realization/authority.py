"""Operation-aware language authority for Phase 17.

ACTIVE lifecycle is necessary but learned language records additionally require
an exact per-use PromotionDecision lineage. Reviewed boot authority without a
promotion edge remains usable according to structural compatibility.
"""
from __future__ import annotations
from ..learning.authority import record_supports_use
from ..learning.model import PromotionDecisionKind,PromotionDecisionRecord
from ..schema.model import SchemaLifecycleStatus,UseDecision,UseOperation
from ..storage.model import DependencyEdge,RecordKind

class LanguageUseAuthority:
 LANGUAGE_KINDS={RecordKind.LANGUAGE_PACK,RecordKind.LANGUAGE_FORM,RecordKind.LEXICAL_SENSE,RecordKind.FORM_SENSE_LINK,RecordKind.CONSTRUCTION,RecordKind.ARGUMENT_FRAME,RecordKind.MORPHOLOGY_RULE,RecordKind.LINEARIZATION_RULE}
 def __init__(self,store): self.store=store
 def authorized(self,stored,operation:UseOperation)->bool:
  if stored.record_kind not in self.LANGUAGE_KINDS:return False
  record=stored.payload
  if getattr(record,'lifecycle_status',None)!=SchemaLifecycleStatus.ACTIVE:return False
  same=[item for item in self.store.records(stored.record_kind,all_revisions=True) if item.record_ref==stored.record_ref and getattr(item.payload,'lifecycle_status',None)==SchemaLifecycleStatus.ACTIVE]
  superseded={getattr(item.payload,'supersedes_revision',None) for item in same if getattr(item.payload,'supersedes_revision',None) is not None}
  if stored.revision in superseded:return False
  if not record_supports_use(stored.record_kind,record,operation):return False
  edges=[]
  for edge_stored in self.store.records(RecordKind.DEPENDENCY,all_revisions=True):
   e=edge_stored.payload
   if not isinstance(e,DependencyEdge) or not e.active:continue
   if e.dependent_kind==stored.record_kind and e.dependent_ref==stored.record_ref and e.dependent_revision==stored.revision:
    edges.append(e)
  promotion_edges=[e for e in edges if e.prerequisite_kind==RecordKind.PROMOTION_DECISION]
  if not promotion_edges:
   return True  # reviewed boot/manual authority
  for edge in promotion_edges:
   ds=self.store.get_record(RecordKind.PROMOTION_DECISION,edge.prerequisite_ref,edge.prerequisite_revision)
   if ds is None or not isinstance(ds.payload,PromotionDecisionRecord) or ds.payload.decision!=PromotionDecisionKind.PROMOTE:continue
   for grant in ds.payload.use_grants:
    if grant.operation!=operation or grant.decision!=UseDecision.ALLOW:continue
    if grant.candidate_pin.record_kind!=stored.record_kind or grant.candidate_pin.record_ref!=stored.record_ref:continue
    source_ok=any(
     e.prerequisite_kind==grant.candidate_pin.record_kind
     and e.prerequisite_ref==grant.candidate_pin.record_ref
     and e.prerequisite_revision==grant.candidate_pin.revision
     and e.prerequisite_fingerprint==grant.candidate_pin.record_fingerprint
     for e in edges
    )
    if source_ok:return True
  return False

 def records_for_use(self,kind:RecordKind,operation:UseOperation):
  by_ref={}
  for stored in self.store.records(kind,all_revisions=True):
   by_ref.setdefault(stored.record_ref,[]).append(stored)
  result=[]
  for ref in sorted(by_ref):
   values=by_ref[ref]
   superseded={
    getattr(item.payload,'supersedes_revision',None) for item in values
    if getattr(item.payload,'lifecycle_status',None)==SchemaLifecycleStatus.ACTIVE
    and getattr(item.payload,'supersedes_revision',None) is not None
   }
   effective=[item for item in values if getattr(item.payload,'lifecycle_status',None)==SchemaLifecycleStatus.ACTIVE and item.revision not in superseded]
   for item in sorted(effective,key=lambda x:x.revision):
    if self.authorized(item,operation):result.append(item)
  return tuple(result)
