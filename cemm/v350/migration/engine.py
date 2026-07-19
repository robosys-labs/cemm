"""Offline-only structural Phase-19 migration engine.

The kernel dispatches by reviewed MigrationRuleRecord/transformer identity and
record family, never by legacy concept names, keywords or surface strings.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Mapping,Protocol

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import record_fingerprints,record_ref,record_revision
from ..storage.model import RecordKind
from .model import *

@dataclass(frozen=True,slots=True)
class MigrationTargetCandidate:
 record_kind:RecordKind
 record:Any
 field_lineage:tuple[tuple[str,str],...]=()
 warning_refs:tuple[str,...]=()
 loss_refs:tuple[str,...]=()

@dataclass(frozen=True,slots=True)
class MigrationTransformResult:
 targets:tuple[MigrationTargetCandidate,...]
 warning_refs:tuple[str,...]=()
 loss_refs:tuple[str,...]=()
 proof_refs:tuple[str,...]=()
 quarantine_reason_refs:tuple[str,...]=()
 missing_dependency_refs:tuple[str,...]=()

class MigrationTransformer(Protocol):
 transformer_ref:str
 transformer_revision:str
 def transform(self,*,source:MigrationSourceRecord,raw_source:Any,rule:MigrationRuleRecord,context:Mapping[str,Any]) -> MigrationTransformResult:...

class PermissionMigrationPolicy(Protocol):
 def allows(self,*,source_permission_ref:str,target_permission_ref:str,policy_ref:str) -> bool:...

class MigrationRuleRegistry:
 def __init__(self,rules):
  by={}
  for r in rules:
   if r.executable:by.setdefault(r.rule_ref,[]).append(r)
  effective=[]
  for ref in sorted(by):
   superseded={r.supersedes_revision for r in by[ref] if r.supersedes_revision is not None}
   effective.extend(r for r in by[ref] if r.revision not in superseded)
  self.rules=tuple(sorted(effective,key=lambda r:(r.rule_ref,r.revision)))
 def candidates(self,source:MigrationSourceRecord,source_shape_ref:str):
  return tuple(r for r in self.rules if source.source_system_ref in r.source_system_refs and source.source_version_ref in r.source_version_refs and r.source_shape_ref==source_shape_ref)

class MigrationTransformerRegistry:
 def __init__(self,transformers=()):
  items=tuple(transformers)
  self._by={(t.transformer_ref,t.transformer_revision):t for t in items}
  if len(self._by)!=len(items):raise ValueError("duplicate migration transformer identity")
 def require(self,rule:MigrationRuleRecord):
  try:return self._by[(rule.transformer_ref,rule.transformer_revision)]
  except KeyError as exc:raise ValueError("reviewed migration transformer implementation unavailable") from exc
 def require_many(self,rule:MigrationRuleRecord):
  transformer=self.require(rule)
  if not callable(getattr(transformer,"transform_many",None)):raise ValueError("reviewed merge migration transformer does not implement transform_many")
  return transformer

class MigrationEngine:
 def __init__(self,store,transformers:MigrationTransformerRegistry,permission_policy:PermissionMigrationPolicy):
  self.store=store;self.transformers=transformers;self.permission_policy=permission_policy

 def transform(self,*,source:MigrationSourceRecord,source_pin:PinnedRecord,raw_source:Any,rule:MigrationRuleRecord,rule_pin:PinnedRecord,context:Mapping[str,Any]|None=None):
  if not rule.executable:raise ValueError("inactive migration rule cannot transform")
  if not (rule.minimum_source_records<=1 and (rule.maximum_source_records is None or 1<=rule.maximum_source_records)):raise ValueError("migration rule does not authorize single-source transformation")
  self._exact(source_pin);self._exact(rule_pin)
  if source.source_system_ref not in rule.source_system_refs or source.source_version_ref not in rule.source_version_refs:raise ValueError("migration rule/source version mismatch")
  transformer=self.transformers.require(rule)
  result=transformer.transform(source=source,raw_source=raw_source,rule=rule,context=dict(context or {}))
  if result.quarantine_reason_refs or result.missing_dependency_refs:
   quarantine=self._quarantine(source_pin,rule_pin,result)
   return (),None,quarantine,self._decision(source_pin,rule_pin,MigrationDisposition.QUARANTINED,None,quarantine,result)
  if not result.targets:
   quarantine=self._quarantine(source_pin,rule_pin,MigrationTransformResult((),quarantine_reason_refs=("migration_transformer_returned_no_target",)))
   return (),None,quarantine,self._decision(source_pin,rule_pin,MigrationDisposition.QUARANTINED,None,quarantine,result)
  if any(t.record_kind not in rule.target_record_kinds for t in result.targets):raise ValueError("transformer emitted target family outside reviewed rule")
  pins=[];field_lineage=[];warnings=list(result.warning_refs);losses=list(result.loss_refs)
  for target in result.targets:
   permission=getattr(target.record,"permission_ref",source.permission_ref)
   if not self.permission_policy.allows(source_permission_ref=source.permission_ref,target_permission_ref=permission,policy_ref=rule.permission_policy_ref):
    quarantine=self._quarantine(source_pin,rule_pin,MigrationTransformResult((),quarantine_reason_refs=("migration_permission_widening_blocked",)))
    return (),None,quarantine,self._decision(source_pin,rule_pin,MigrationDisposition.QUARANTINED,None,quarantine,result)
   ref=record_ref(target.record_kind,target.record);rev=record_revision(target.record_kind,target.record);fp=record_fingerprints(target.record_kind,target.record)[1]
   existing=self.store.get_record(target.record_kind,ref,rev)
   if existing is not None and existing.record_fingerprint!=fp:
    quarantine=self._quarantine(source_pin,rule_pin,MigrationTransformResult((),quarantine_reason_refs=(f"target_collision:{target.record_kind.value}:{ref}@{rev}",)))
    return (),None,quarantine,self._decision(source_pin,rule_pin,MigrationDisposition.QUARANTINED,None,quarantine,result)
   pins.append(PinnedRecord(target.record_kind,ref,rev,fp));field_lineage.extend(target.field_lineage);warnings.extend(target.warning_refs);losses.extend(target.loss_refs)
  disposition=MigrationDisposition.MAPPED if len(result.targets)==1 and not losses else (MigrationDisposition.SPLIT if len(result.targets)>1 else MigrationDisposition.TRANSFORMED)
  map_record=MigrationTargetMapRecord(map_ref="migration-map:"+semantic_fingerprint("migration-target-map",(source_pin.key,rule_pin.key,tuple(p.key+(p.record_fingerprint,) for p in pins)),24),source_pins=(source_pin,),rule_pin=rule_pin,target_pins=tuple(pins),mapping_kind=disposition,field_lineage=tuple(field_lineage),loss_refs=tuple(sorted(set(losses))),warning_refs=tuple(sorted(set(warnings))))
  decision=self._decision(source_pin,rule_pin,disposition,map_record,None,result)
  return result.targets,map_record,None,decision

 def transform_merge(self,*,sources:tuple[MigrationSourceRecord,...],source_pins:tuple[PinnedRecord,...],raw_sources:tuple[Any,...],rule:MigrationRuleRecord,rule_pin:PinnedRecord,context:Mapping[str,Any]|None=None):
  if not rule.executable:raise ValueError("inactive migration rule cannot transform")
  if len(sources)!=len(source_pins) or len(sources)!=len(raw_sources) or len(sources)<2:raise ValueError("merge migration requires aligned multiple source sets")
  if len(sources)<rule.minimum_source_records or (rule.maximum_source_records is not None and len(sources)>rule.maximum_source_records):raise ValueError("merge source cardinality is not authorized by migration rule")
  self._exact(rule_pin)
  for source,p in zip(sources,source_pins):
   self._exact(p)
   if source.source_system_ref not in rule.source_system_refs or source.source_version_ref not in rule.source_version_refs:raise ValueError("migration merge rule/source version mismatch")
  transformer=self.transformers.require_many(rule)
  result=transformer.transform_many(sources=sources,raw_sources=raw_sources,rule=rule,context=dict(context or {}))
  if result.quarantine_reason_refs or result.missing_dependency_refs or not result.targets:
   reason=result if (result.quarantine_reason_refs or result.missing_dependency_refs) else MigrationTransformResult((),quarantine_reason_refs=("migration_transformer_returned_no_target",))
   quarantines=tuple(self._quarantine(p,rule_pin,reason) for p in source_pins)
   decisions=tuple(self._decision(p,rule_pin,MigrationDisposition.QUARANTINED,None,q,reason) for p,q in zip(source_pins,quarantines))
   return (),None,quarantines,decisions
  if any(t.record_kind not in rule.target_record_kinds for t in result.targets):raise ValueError("merge transformer emitted target family outside reviewed rule")
  pins=[];field_lineage=[];warnings=list(result.warning_refs);losses=list(result.loss_refs)
  for target in result.targets:
   permission=getattr(target.record,"permission_ref",sources[0].permission_ref)
   if any(not self.permission_policy.allows(source_permission_ref=src.permission_ref,target_permission_ref=permission,policy_ref=rule.permission_policy_ref) for src in sources):
    reason=MigrationTransformResult((),quarantine_reason_refs=("migration_permission_widening_blocked",))
    quarantines=tuple(self._quarantine(p,rule_pin,reason) for p in source_pins);decisions=tuple(self._decision(p,rule_pin,MigrationDisposition.QUARANTINED,None,q,reason) for p,q in zip(source_pins,quarantines))
    return (),None,quarantines,decisions
   ref=record_ref(target.record_kind,target.record);rev=record_revision(target.record_kind,target.record);fp=record_fingerprints(target.record_kind,target.record)[1]
   existing=self.store.get_record(target.record_kind,ref,rev)
   if existing is not None and existing.record_fingerprint!=fp:
    reason=MigrationTransformResult((),quarantine_reason_refs=(f"target_collision:{target.record_kind.value}:{ref}@{rev}",))
    quarantines=tuple(self._quarantine(p,rule_pin,reason) for p in source_pins);decisions=tuple(self._decision(p,rule_pin,MigrationDisposition.QUARANTINED,None,q,reason) for p,q in zip(source_pins,quarantines))
    return (),None,quarantines,decisions
   pins.append(PinnedRecord(target.record_kind,ref,rev,fp));field_lineage.extend(target.field_lineage);warnings.extend(target.warning_refs);losses.extend(target.loss_refs)
  disposition=MigrationDisposition.MERGED if len(pins)==1 else MigrationDisposition.TRANSFORMED
  map_record=MigrationTargetMapRecord(map_ref="migration-map:"+semantic_fingerprint("migration-target-map-merge",(tuple((p.key,p.record_fingerprint) for p in source_pins),rule_pin.key,tuple(p.key+(p.record_fingerprint,) for p in pins)),24),source_pins=source_pins,rule_pin=rule_pin,target_pins=tuple(pins),mapping_kind=disposition,field_lineage=tuple(field_lineage),loss_refs=tuple(sorted(set(losses))),warning_refs=tuple(sorted(set(warnings))))
  decisions=tuple(self._decision(p,rule_pin,disposition,map_record,None,result) for p in source_pins)
  return result.targets,map_record,(),decisions

 def _quarantine(self,source_pin,rule_pin,result):
  source=self._exact(source_pin).payload
  return MigrationQuarantineRecord(quarantine_ref="migration-quarantine:"+semantic_fingerprint("migration-quarantine",(source_pin.key,rule_pin.key,result.quarantine_reason_refs,result.missing_dependency_refs),24),source_pin=source_pin,rule_pin=rule_pin,reason_refs=tuple(sorted(set(result.quarantine_reason_refs or ("migration_unrepresentable",)))),candidate_target_kinds=(),missing_dependency_refs=tuple(sorted(set(result.missing_dependency_refs))),remediation_frontier_refs=(),permission_ref=source.permission_ref,non_authority=True)
 def _decision(self,source_pin,rule_pin,disp,map_record,quarantine,result):
  mp=None if map_record is None else PinnedRecord(RecordKind.MIGRATION_TARGET_MAP,map_record.map_ref,1,record_fingerprints(RecordKind.MIGRATION_TARGET_MAP,map_record)[1])
  qp=None if quarantine is None else PinnedRecord(RecordKind.MIGRATION_QUARANTINE,quarantine.quarantine_ref,1,record_fingerprints(RecordKind.MIGRATION_QUARANTINE,quarantine)[1])
  source=self._exact(source_pin).payload
  return MigrationDecisionRecord(decision_ref="migration-decision:"+semantic_fingerprint("migration-decision",(source_pin.key,rule_pin.key,disp.value,None if mp is None else mp.key,None if qp is None else qp.key),24),source_pin=source_pin,rule_pin=rule_pin,disposition=disp,target_map_pin=mp,quarantine_pin=qp,warning_refs=tuple(sorted(set(result.warning_refs))),loss_refs=tuple(sorted(set(result.loss_refs))),review_refs=(),proof_refs=result.proof_refs,permission_ref=source.permission_ref)
 def _exact(self,p):
  s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
  if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f"stale migration dependency: {p.key}")
  return s
