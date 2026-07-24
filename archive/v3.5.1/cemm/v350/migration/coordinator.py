"""Atomic bounded-batch persistence and safe rollback for Phase-19 migration."""
from __future__ import annotations
from dataclasses import replace
from typing import Iterable

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record,record_fingerprints,record_ref,record_revision
from ..storage.model import DependencyEdge,GraphPatch,PatchOperation,PatchOperationKind,RecordDependency,RecordKind
from .engine import MigrationTargetCandidate
from .model import *


def pin(kind,record):return PinnedRecord(kind,record_ref(kind,record),record_revision(kind,record),record_fingerprints(kind,record)[1])
def dep(p,k):return RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,k)
def upsert(kind,record,deps,reason,**cas):return PatchOperation(operation_ref="patch-operation:phase19:"+semantic_fingerprint("phase19-op",(kind.value,record_ref(kind,record),record_revision(kind,record),reason),20),operation_kind=PatchOperationKind.UPSERT,record_kind=kind,target_ref=record_ref(kind,record),record_revision=record_revision(kind,record),payload=encode_record(kind,record),dependencies=tuple(deps),reason=reason,expected_record_revision=cas.get('expected_revision'),expected_record_fingerprint=cas.get('expected_fingerprint'))

class MigrationCommitCoordinator:
 def __init__(self,store):self.store=store

 def persist_source(self,source:MigrationSourceRecord):
  return self._single(RecordKind.MIGRATION_SOURCE,source,(),"persist immutable legacy source snapshot")
 def persist_intentional_change(self,record:MigrationIntentionalChangeRecord):
  deps=tuple(dep(p,"intentional_change_fixture") for p in record.fixture_pins)
  return self._single(RecordKind.MIGRATION_INTENTIONAL_CHANGE,record,deps,"persist reviewed intentional semantic behavior change")
 def persist_equivalence(self,record:SemanticEquivalenceRecord):
  deps=[*tuple(dep(p,"equivalence_source_fixture") for p in record.source_fixture_pins),*tuple(dep(p,"equivalence_target_trace") for p in record.target_trace_pins),*tuple(dep(p,"equivalence_intentional_change") for p in record.intentional_change_pins)]
  return self._single(RecordKind.SEMANTIC_EQUIVALENCE,record,tuple(deps),"persist dimensioned semantic equivalence result")
 def persist_rule(self,rule:MigrationRuleRecord):
  deps=()
  if rule.supersedes_revision is not None:
   prior=self.store.get_record(RecordKind.MIGRATION_RULE,rule.rule_ref,rule.supersedes_revision)
   if prior is None:raise ValueError("migration rule supersedes missing prior")
   deps=(RecordDependency(RecordKind.MIGRATION_RULE,prior.record_ref,prior.revision,prior.record_fingerprint,"migration_rule_prior"),)
  return self._single(RecordKind.MIGRATION_RULE,rule,deps,"persist reviewed offline migration rule")

 def commit_batch(self,*,entries:tuple[tuple[tuple[MigrationTargetCandidate,...],MigrationTargetMapRecord|None,MigrationQuarantineRecord|None,MigrationDecisionRecord],...],source_pins:tuple[PinnedRecord,...],rule_pins:tuple[PinnedRecord,...],permission_ref:str="internal"):
  if not entries:raise ValueError("migration batch requires entries")
  for p in (*source_pins,*rule_pins):self._exact(p)
  if len({(p.key,p.record_fingerprint) for p in source_pins})!=len(source_pins):raise ValueError("migration batch source pins must be exact-unique")
  if len({(p.key,p.record_fingerprint) for p in rule_pins})!=len(rule_pins):raise ValueError("migration batch rule pins must be exact-unique")
  decision_records=tuple(entry[3] for entry in entries)
  decision_pins=tuple(pin(RecordKind.MIGRATION_DECISION,d) for d in decision_records)
  if len({(p.key,p.record_fingerprint) for p in decision_pins})!=len(decision_pins):raise ValueError("migration batch decisions must be exact-unique")
  source_fp=semantic_fingerprint("migration-source-set",tuple(sorted((p.key,p.record_fingerprint) for p in source_pins)),64)
  rule_fp=semantic_fingerprint("migration-rule-set",tuple(sorted((p.key,p.record_fingerprint) for p in rule_pins)),64)
  batch_ref="migration-batch:"+semantic_fingerprint("migration-batch-ref",(source_fp,rule_fp,tuple(sorted((p.key,p.record_fingerprint) for p in decision_pins))),24)
  # Re-running an identical logical batch is idempotent even after store revision advances.
  existing_batch=self.store.get_record(RecordKind.MIGRATION_BATCH,batch_ref)
  if existing_batch is not None:
   batch=existing_batch.payload
   if ({(p.key,p.record_fingerprint) for p in batch.source_pins}!={(p.key,p.record_fingerprint) for p in source_pins} or
       {(p.key,p.record_fingerprint) for p in batch.rule_pins}!={(p.key,p.record_fingerprint) for p in rule_pins} or
       {(p.key,p.record_fingerprint) for p in batch.decision_pins}!={(p.key,p.record_fingerprint) for p in decision_pins}):
    raise ValueError("deterministic migration batch identity collides with different exact substrate")
   if batch.status not in {MigrationBatchStatus.COMMITTED,MigrationBatchStatus.PARTIAL}:raise ValueError("identical migration batch exists but is not reusable in committed/partial state")
   if batch.rollback_pin is None:raise ValueError("committed migration batch lacks rollback plan")
   rollback=self._exact(batch.rollback_pin).payload
   return batch,rollback

  with self.store.snapshot() as snapshot:
   ops=[];owned=[];planned={}
   def add(op):
    key=(op.record_kind,op.target_ref,op.record_revision)
    prior=planned.get(key)
    if prior is not None:
     if prior.payload!=op.payload:raise ValueError(f"migration batch plans conflicting writes for {key}")
     return
    planned[key]=op;ops.append(op)
   source_set={(p.key,p.record_fingerprint) for p in source_pins};rule_set={(p.key,p.record_fingerprint) for p in rule_pins}
   for targets,map_record,quarantine,decision in entries:
    if (decision.source_pin.key,decision.source_pin.record_fingerprint) not in source_set:raise ValueError("decision source outside batch source set")
    if decision.rule_pin is not None and (decision.rule_pin.key,decision.rule_pin.record_fingerprint) not in rule_set:raise ValueError("decision rule outside batch rule set")
    target_pins=[]
    for target in targets:
     tp=pin(target.record_kind,target.record);existing=self.store.get_record(tp.record_kind,tp.record_ref,tp.revision)
     if existing is None:
      lineage_sources=map_record.source_pins if map_record is not None else (decision.source_pin,)
      deps=[dep(p,"migration_source") for p in lineage_sources]
      lineage_rule=map_record.rule_pin if map_record is not None else decision.rule_pin
      if lineage_rule is not None:deps.append(dep(lineage_rule,"migration_rule"))
      add(upsert(target.record_kind,target.record,tuple(deps),"persist v3.5 target produced by explicit migration rule"))
      if tp not in owned:owned.append(tp)
     elif existing.record_fingerprint!=tp.record_fingerprint:raise ValueError("migration target collision changed after planning")
     target_pins.append(tp)
    if map_record is not None:
     if not set((p.key,p.record_fingerprint) for p in map_record.source_pins).issubset(source_set):raise ValueError("migration target map contains source outside exact batch set")
     if decision.source_pin not in map_record.source_pins:raise ValueError("per-source decision must be covered by its migration target map")
     if tuple(map_record.target_pins)!=tuple(target_pins):raise ValueError("migration target map differs from exact batch targets")
     mp=pin(RecordKind.MIGRATION_TARGET_MAP,map_record)
     add(upsert(RecordKind.MIGRATION_TARGET_MAP,map_record,(*tuple(dep(p,"migration_source") for p in map_record.source_pins),dep(map_record.rule_pin,"migration_rule"),*tuple(dep(p,"migration_target") for p in map_record.target_pins)),"persist exact source-set-to-target migration map"))
     if decision.target_map_pin!=mp:raise ValueError("migration decision target map pin mismatch")
    if quarantine is not None:
     qp=pin(RecordKind.MIGRATION_QUARANTINE,quarantine)
     qdeps=[dep(quarantine.source_pin,"migration_source")]
     if quarantine.rule_pin is not None:qdeps.append(dep(quarantine.rule_pin,"migration_rule"))
     add(upsert(RecordKind.MIGRATION_QUARANTINE,quarantine,tuple(qdeps),"preserve unrepresentable legacy material as non-authority"))
     if decision.quarantine_pin!=qp:raise ValueError("migration decision quarantine pin mismatch")
    dp=pin(RecordKind.MIGRATION_DECISION,decision)
    ddeps=[dep(decision.source_pin,"migration_source")]
    if decision.rule_pin is not None:ddeps.append(dep(decision.rule_pin,"migration_rule"))
    if decision.target_map_pin is not None:ddeps.append(dep(decision.target_map_pin,"migration_target_map"))
    if decision.quarantine_pin is not None:ddeps.append(dep(decision.quarantine_pin,"migration_quarantine"))
    add(upsert(RecordKind.MIGRATION_DECISION,decision,tuple(ddeps),"persist explicit per-source migration disposition"))
   rollback=MigrationRollbackRecord(rollback_ref="migration-rollback:"+semantic_fingerprint("migration-rollback-plan",(batch_ref,tuple(sorted((p.key,p.record_fingerprint) for p in owned))),24),batch_ref=batch_ref,owned_target_pins=tuple(owned),inverse_operation_refs=tuple("tombstone:"+p.record_kind.value+":"+p.record_ref+"@"+str(p.revision) for p in owned),blocked_by_dependent_pins=(),pre_batch_store_revision=snapshot.store_revision,pre_batch_snapshot_fingerprint=snapshot.fingerprint,permission_ref=permission_ref)
   rbp=pin(RecordKind.MIGRATION_ROLLBACK,rollback)
   batch=MigrationBatchRecord(batch_ref=batch_ref,source_pins=source_pins,rule_pins=rule_pins,decision_pins=decision_pins,source_set_fingerprint=source_fp,rule_set_fingerprint=rule_fp,expected_target_store_revision=snapshot.store_revision,expected_target_snapshot_fingerprint=snapshot.fingerprint,status=MigrationBatchStatus.COMMITTED,rollback_pin=rbp,metrics=(("source_count",float(len(source_pins))),("decision_count",float(len(decision_pins))),("owned_target_count",float(len(owned)))),permission_ref=permission_ref)
   add(upsert(RecordKind.MIGRATION_ROLLBACK,rollback,tuple(dep(p,"migration_owned_target") for p in owned),"persist exact data-level rollback plan"))
   add(upsert(RecordKind.MIGRATION_BATCH,batch,(*tuple(dep(p,"migration_batch_source") for p in source_pins),*tuple(dep(p,"migration_batch_rule") for p in rule_pins),*tuple(dep(p,"migration_batch_decision") for p in decision_pins),dep(rbp,"migration_batch_rollback")),"persist bounded migration batch audit"))
   patch=GraphPatch(patch_ref="graph-patch:migration-batch:"+semantic_fingerprint("migration-batch-patch",batch_ref,24),context_ref="migration:offline",scope_ref="phase19:migration",source_ref="source:phase19:migration-coordinator",permission_ref=permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,validation_requirements=("phase19_exact_source_target_lineage","phase19_no_legacy_runtime_authority","phase19_rollback_owned_only","phase19_logical_batch_idempotent"),metadata={"phase":19,"offline_only":True,"batch_ref":batch_ref})
  result=self.store.apply_patch(patch)
  if not result.committed:raise RuntimeError("migration batch commit failed: "+"; ".join(result.errors))
  return batch,rollback

 def rollback(self,batch:MigrationBatchRecord,rollback:MigrationRollbackRecord):
  bp=pin(RecordKind.MIGRATION_BATCH,batch);rp=pin(RecordKind.MIGRATION_ROLLBACK,rollback);self._exact(bp);self._exact(rp)
  if batch.status not in {MigrationBatchStatus.COMMITTED,MigrationBatchStatus.PARTIAL}:raise ValueError("only committed/partial migration batch can roll back")
  blockers=[]
  for target in rollback.owned_target_pins:
   for stored in self.store.records(RecordKind.DEPENDENCY):
    edge=stored.payload
    if not isinstance(edge,DependencyEdge) or not edge.active:continue
    if edge.prerequisite_kind==target.record_kind and edge.prerequisite_ref==target.record_ref and edge.prerequisite_revision==target.revision and edge.prerequisite_fingerprint==target.record_fingerprint:
     if edge.dependent_kind not in {RecordKind.MIGRATION_TARGET_MAP,RecordKind.MIGRATION_DECISION,RecordKind.MIGRATION_BATCH,RecordKind.MIGRATION_ROLLBACK}:
      depstored=self.store.get_record(edge.dependent_kind,edge.dependent_ref,edge.dependent_revision)
      if depstored is not None:blockers.append(PinnedRecord(depstored.record_kind,depstored.record_ref,depstored.revision,depstored.record_fingerprint))
  if blockers:raise ValueError("rollback blocked by later/non-migration dependents: "+",".join(sorted(p.record_ref for p in blockers)))
  latest=self.store.get_record(RecordKind.MIGRATION_BATCH,batch.batch_ref)
  if latest is None or latest.revision!=batch.revision or latest.record_fingerprint!=bp.record_fingerprint:raise ValueError("stale migration batch rollback")
  rolled=replace(batch,revision=batch.revision+1,supersedes_revision=batch.revision,status=MigrationBatchStatus.ROLLED_BACK)
  with self.store.snapshot() as snapshot:
   ops=[]
   for p in rollback.owned_target_pins:
    current=self.store.get_record(p.record_kind,p.record_ref,p.revision)
    if current is None:continue
    if current.record_fingerprint!=p.record_fingerprint:raise ValueError("rollback target fingerprint changed")
    ops.append(PatchOperation(operation_ref="patch-operation:migration-rollback:"+semantic_fingerprint("migration-rollback-op",p.key,20),operation_kind=PatchOperationKind.TOMBSTONE,record_kind=p.record_kind,target_ref=p.record_ref,record_revision=p.revision,expected_record_revision=p.revision,expected_record_fingerprint=p.record_fingerprint,reason="phase19 exact batch-owned rollback"))
   ops.append(upsert(RecordKind.MIGRATION_BATCH,rolled,(dep(bp,"migration_batch_prior"),dep(rp,"migration_rollback_plan")),"mark migration batch rolled back",expected_revision=batch.revision,expected_fingerprint=bp.record_fingerprint))
   patch=GraphPatch(patch_ref="graph-patch:migration-rollback:"+semantic_fingerprint("migration-rollback-patch",(bp.key,rp.key,snapshot.fingerprint),24),context_ref="migration:offline",scope_ref="phase19:rollback",source_ref="source:phase19:rollback",permission_ref=batch.permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,metadata={"phase":19,"offline_only":True})
  result=self.store.apply_patch(patch)
  if not result.committed:raise RuntimeError("migration rollback failed: "+"; ".join(result.errors))
  return rolled

 def _single(self,kind,record,deps,reason):
  with self.store.snapshot() as snapshot:
   patch=GraphPatch(patch_ref="graph-patch:phase19-single:"+semantic_fingerprint("phase19-single",(kind.value,record_ref(kind,record),snapshot.fingerprint),24),context_ref="migration:offline",scope_ref="phase19:migration",source_ref="source:phase19:migration-audit",permission_ref=getattr(record,"permission_ref","internal"),operations=(upsert(kind,record,deps,reason),),expected_store_revision=snapshot.store_revision,metadata={"phase":19,"offline_only":True})
  result=self.store.apply_patch(patch)
  if not result.committed:raise RuntimeError("migration audit commit failed: "+"; ".join(result.errors))
  return result
 def _exact(self,p):
  s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
  if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f"stale migration dependency: {p.key}")
  return s
