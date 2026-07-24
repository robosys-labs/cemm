"""Commit-boundary invariants for offline-only Phase-19 migration records."""
from __future__ import annotations
from ..storage.model import RecordKind
from .model import *

class Phase19CommitValidator:
 def __init__(self,resolver):self.r=resolver
 def validate_operation(self,op,record):
  k=op.record_kind
  if k==RecordKind.MIGRATION_SOURCE:
   if not isinstance(record,MigrationSourceRecord):raise ValueError('migration source type mismatch')
  elif k==RecordKind.MIGRATION_RULE:
   if not isinstance(record,MigrationRuleRecord):raise ValueError('migration rule type mismatch')
   if bool(record.metadata.get('runtime_reachable',False)):raise ValueError('migration transformer/rule may not be runtime semantic authority')
   self._sup(record,RecordKind.MIGRATION_RULE,record.rule_ref)
  elif k==RecordKind.MIGRATION_TARGET_MAP:
   if not isinstance(record,MigrationTargetMapRecord):raise ValueError('migration target map type mismatch')
   for p in (*record.source_pins,record.rule_pin,*record.target_pins):self._require(op,p)
  elif k==RecordKind.MIGRATION_QUARANTINE:
   if not isinstance(record,MigrationQuarantineRecord):raise ValueError('migration quarantine type mismatch')
   if not record.non_authority:raise ValueError('quarantine cannot become semantic authority')
   self._require(op,record.source_pin)
   if record.rule_pin is not None:self._require(op,record.rule_pin)
  elif k==RecordKind.MIGRATION_DECISION:
   if not isinstance(record,MigrationDecisionRecord):raise ValueError('migration decision type mismatch')
   self._require(op,record.source_pin)
   if record.rule_pin is not None:self._require(op,record.rule_pin)
   if record.target_map_pin is not None:self._require(op,record.target_map_pin)
   if record.quarantine_pin is not None:self._require(op,record.quarantine_pin)
  elif k==RecordKind.MIGRATION_ROLLBACK:
   if not isinstance(record,MigrationRollbackRecord):raise ValueError('migration rollback type mismatch')
   for p in (*record.owned_target_pins,*record.blocked_by_dependent_pins):self._require(op,p)
  elif k==RecordKind.MIGRATION_BATCH:
   if not isinstance(record,MigrationBatchRecord):raise ValueError('migration batch type mismatch')
   for p in (*record.source_pins,*record.rule_pins,*record.decision_pins):self._require(op,p)
   if record.rollback_pin is not None:self._require(op,record.rollback_pin)
   self._sup(record,RecordKind.MIGRATION_BATCH,record.batch_ref)
   if bool(record.metadata.get('runtime_authority_enabled',False)):raise ValueError('migration batch cannot enable runtime semantic authority')
  elif k==RecordKind.MIGRATION_INTENTIONAL_CHANGE:
   if not isinstance(record,MigrationIntentionalChangeRecord):raise ValueError('intentional change type mismatch')
   for p in record.fixture_pins:self._require(op,p)
  elif k==RecordKind.SEMANTIC_EQUIVALENCE:
   if not isinstance(record,SemanticEquivalenceRecord):raise ValueError('semantic equivalence type mismatch')
   for p in (*record.source_fixture_pins,*record.target_trace_pins,*record.intentional_change_pins):self._require(op,p)
   if record.overall==EquivalenceOutcome.EQUIVALENT and any(o!=EquivalenceOutcome.EQUIVALENT for _,o in record.dimensions):raise ValueError('overall equivalent cannot hide non-equivalent dimensions')
 def _require(self,op,p):
  if not any(d.record_kind==p.record_kind and d.record_ref==p.record_ref and d.revision==p.revision and d.fingerprint==p.record_fingerprint for d in op.dependencies):raise ValueError(f'Phase19 record missing exact dependency: {p.key}')
  s=self.r.resolve(p.record_kind,p.record_ref,p.revision)
  if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f'stale Phase19 dependency: {p.key}')
 def _sup(self,record,kind,ref):
  prior=getattr(record,'supersedes_revision',None)
  if prior is not None and self.r.resolve(kind,ref,prior) is None:raise ValueError('supersedes missing exact prior revision')
