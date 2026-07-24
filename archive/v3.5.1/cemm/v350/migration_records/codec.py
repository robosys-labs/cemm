"""Deterministic codecs for Phase-19 migration audit records."""
from __future__ import annotations
from ..learning.codec import _pin
from ..schema.model import SchemaLifecycleStatus,canonical_data
from ..storage.model import RecordKind
from .model import *

def migration_record_to_document(record):return dict(canonical_data(record))
def _pins(v):return tuple(_pin(dict(x)) for x in v or ())

def migration_source_from_document(v):
 d=dict(v);return MigrationSourceRecord(str(d['source_ref']),str(d['source_system_ref']),str(d['source_version_ref']),str(d['source_locator_ref']),str(d['source_primary_key']),d.get('source_revision_ref'),str(d['content_fingerprint']),str(d['extraction_tool_ref']),str(d['extraction_tool_revision']),str(d['permission_ref']),tuple(map(str,d.get('scope_evidence_refs',()))),d.get('extracted_at'),int(d.get('revision',1)),dict(d.get('metadata',{})))
def migration_rule_from_document(v):
 d=dict(v);return MigrationRuleRecord(str(d['rule_ref']),tuple(map(str,d.get('source_system_refs',()))),tuple(map(str,d.get('source_version_refs',()))),str(d['source_shape_ref']),tuple(RecordKind(str(x)) for x in d.get('target_record_kinds',())),str(d['transformer_ref']),str(d['transformer_revision']),tuple(map(str,d.get('field_mapping_refs',()))),tuple(map(str,d.get('validation_requirements',()))),int(d.get('minimum_source_records',1)),None if d.get('maximum_source_records') is None else int(d.get('maximum_source_records',1)),tuple(map(str,d.get('known_loss_refs',()))),str(d.get('permission_policy_ref','migration:default_narrow')),tuple(map(str,d.get('competence_case_refs',()))),SchemaLifecycleStatus(str(d.get('lifecycle_status',SchemaLifecycleStatus.CANDIDATE.value))),str(d.get('permission_ref','internal')),int(d.get('revision',1)),None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),dict(d.get('metadata',{})))
def migration_target_map_from_document(v):
 d=dict(v);return MigrationTargetMapRecord(str(d['map_ref']),_pins(d.get('source_pins',())),_pin(dict(d['rule_pin'])),_pins(d.get('target_pins',())),MigrationDisposition(str(d['mapping_kind'])),tuple((str(x[0]),str(x[1])) for x in d.get('field_lineage',())),tuple(map(str,d.get('loss_refs',()))),tuple(map(str,d.get('warning_refs',()))),int(d.get('revision',1)))
def migration_quarantine_from_document(v):
 d=dict(v);return MigrationQuarantineRecord(str(d['quarantine_ref']),_pin(dict(d['source_pin'])),None if d.get('rule_pin') is None else _pin(dict(d['rule_pin'])),tuple(map(str,d.get('reason_refs',()))),tuple(RecordKind(str(x)) for x in d.get('candidate_target_kinds',())),tuple(map(str,d.get('missing_dependency_refs',()))),tuple(map(str,d.get('remediation_frontier_refs',()))),str(d['permission_ref']),bool(d.get('non_authority',True)),int(d.get('revision',1)),dict(d.get('metadata',{})))
def migration_decision_from_document(v):
 d=dict(v);return MigrationDecisionRecord(str(d['decision_ref']),_pin(dict(d['source_pin'])),None if d.get('rule_pin') is None else _pin(dict(d['rule_pin'])),MigrationDisposition(str(d['disposition'])),None if d.get('target_map_pin') is None else _pin(dict(d['target_map_pin'])),None if d.get('quarantine_pin') is None else _pin(dict(d['quarantine_pin'])),tuple(map(str,d.get('warning_refs',()))),tuple(map(str,d.get('loss_refs',()))),tuple(map(str,d.get('review_refs',()))),tuple(map(str,d.get('proof_refs',()))),str(d['permission_ref']),int(d.get('revision',1)))
def migration_rollback_from_document(v):
 d=dict(v);return MigrationRollbackRecord(str(d['rollback_ref']),str(d['batch_ref']),_pins(d.get('owned_target_pins',())),tuple(map(str,d.get('inverse_operation_refs',()))),_pins(d.get('blocked_by_dependent_pins',())),int(d['pre_batch_store_revision']),str(d['pre_batch_snapshot_fingerprint']),str(d['permission_ref']),int(d.get('revision',1)),dict(d.get('metadata',{})))
def migration_batch_from_document(v):
 d=dict(v);return MigrationBatchRecord(str(d['batch_ref']),_pins(d.get('source_pins',())),_pins(d.get('rule_pins',())),_pins(d.get('decision_pins',())),str(d['source_set_fingerprint']),str(d['rule_set_fingerprint']),int(d['expected_target_store_revision']),str(d['expected_target_snapshot_fingerprint']),MigrationBatchStatus(str(d['status'])),None if d.get('rollback_pin') is None else _pin(dict(d['rollback_pin'])),tuple((str(x[0]),float(x[1])) for x in d.get('metrics',())),tuple(map(str,d.get('error_refs',()))),str(d.get('permission_ref','internal')),int(d.get('revision',1)),None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),dict(d.get('metadata',{})))
def migration_intentional_change_from_document(v):
 d=dict(v);return MigrationIntentionalChangeRecord(str(d['change_ref']),str(d['legacy_behavior_ref']),str(d['v350_behavior_ref']),str(d['reason_ref']),tuple(map(str,d.get('approved_by_refs',()))),_pins(d.get('fixture_pins',())),str(d.get('permission_ref','internal')),int(d.get('revision',1)))
def semantic_equivalence_from_document(v):
 d=dict(v);return SemanticEquivalenceRecord(str(d['equivalence_ref']),_pins(d.get('source_fixture_pins',())),_pins(d.get('target_trace_pins',())),tuple((str(x[0]),EquivalenceOutcome(str(x[1]))) for x in d.get('dimensions',())),EquivalenceOutcome(str(d['overall'])),_pins(d.get('intentional_change_pins',())),tuple(map(str,d.get('difference_refs',()))),tuple(map(str,d.get('proof_refs',()))),str(d['runner_ref']),str(d['runner_revision']),str(d.get('permission_ref','internal')),int(d.get('revision',1)),dict(d.get('metadata',{})))
