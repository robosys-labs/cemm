"""CEMM v3.5 Phase-19 migration/equivalence durable contracts.

Legacy material is immutable evidence. Migration records never make a legacy
router, keyword map, template, enum or mutable blob into runtime semantic authority.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import Enum
from typing import Any,Mapping

from ..learning.model import PinnedRecord
from ..schema.model import SchemaLifecycleStatus,semantic_fingerprint
from ..storage.model import RecordKind

class StrEnum(str,Enum):
 def __str__(self):return self.value
class MigrationDisposition(StrEnum):
 MAPPED="mapped";TRANSFORMED="transformed";SPLIT="split";MERGED="merged";QUARANTINED="quarantined";REJECTED="rejected";INTENTIONALLY_NOT_MIGRATED="intentionally_not_migrated"
class MigrationBatchStatus(StrEnum):
 PLANNED="planned";COMMITTED="committed";PARTIAL="partial";BLOCKED="blocked";ROLLED_BACK="rolled_back"
class EquivalenceOutcome(StrEnum):
 EQUIVALENT="equivalent";INTENTIONALLY_CHANGED="intentionally_changed";PARTIALLY_EQUIVALENT="partially_equivalent";NOT_EQUIVALENT="not_equivalent";UNTESTABLE="untestable"

@dataclass(frozen=True,slots=True)
class MigrationSourceRecord:
 source_ref:str;source_system_ref:str;source_version_ref:str;source_locator_ref:str;source_primary_key:str;source_revision_ref:str|None;content_fingerprint:str;extraction_tool_ref:str;extraction_tool_revision:str;permission_ref:str;scope_evidence_refs:tuple[str,...]=();extracted_at:str|None=None;revision:int=1;metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.source_ref,"source_ref"),(self.source_system_ref,"source system"),(self.source_version_ref,"source version"),(self.source_locator_ref,"source locator"),(self.source_primary_key,"source primary key"),(self.content_fingerprint,"content fingerprint"),(self.extraction_tool_ref,"extraction tool"),(self.extraction_tool_revision,"extraction tool revision"),(self.permission_ref,"permission")):_ref(v,l)
  if self.revision!=1:raise ValueError("migration source snapshots are immutable")
  _unique(self.scope_evidence_refs,"scope evidence")

@dataclass(frozen=True,slots=True)
class MigrationRuleRecord:
 rule_ref:str;source_system_refs:tuple[str,...];source_version_refs:tuple[str,...];source_shape_ref:str;target_record_kinds:tuple[RecordKind,...];transformer_ref:str;transformer_revision:str;field_mapping_refs:tuple[str,...];validation_requirements:tuple[str,...];minimum_source_records:int=1;maximum_source_records:int|None=1;known_loss_refs:tuple[str,...]=();permission_policy_ref:str="migration:default_narrow";competence_case_refs:tuple[str,...]=();lifecycle_status:SchemaLifecycleStatus=SchemaLifecycleStatus.CANDIDATE;permission_ref:str="internal";revision:int=1;supersedes_revision:int|None=None;metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.rule_ref,"rule_ref"),(self.source_shape_ref,"source shape"),(self.transformer_ref,"transformer"),(self.transformer_revision,"transformer revision"),(self.permission_policy_ref,"permission policy"),(self.permission_ref,"permission")):_ref(v,l)
  if self.revision<1 or not self.source_system_refs or not self.source_version_refs or not self.target_record_kinds:raise ValueError("migration rule requires positive revision and explicit source/target families")
  if self.minimum_source_records<1 or (self.maximum_source_records is not None and self.maximum_source_records<self.minimum_source_records):raise ValueError("migration rule source cardinality is invalid")
  _sup(self.revision,self.supersedes_revision,"migration rule")
  if self.lifecycle_status==SchemaLifecycleStatus.ACTIVE and not self.competence_case_refs:raise ValueError("active migration rule requires competence cases")
  for x,l in ((self.source_system_refs,"source systems"),(self.source_version_refs,"source versions"),(self.target_record_kinds,"target kinds"),(self.field_mapping_refs,"field mappings"),(self.validation_requirements,"validation requirements"),(self.known_loss_refs,"known losses"),(self.competence_case_refs,"competence cases")):_unique(x,l)
 @property
 def executable(self):return self.lifecycle_status==SchemaLifecycleStatus.ACTIVE

@dataclass(frozen=True,slots=True)
class MigrationTargetMapRecord:
 map_ref:str;source_pins:tuple[PinnedRecord,...];rule_pin:PinnedRecord;target_pins:tuple[PinnedRecord,...];mapping_kind:MigrationDisposition;field_lineage:tuple[tuple[str,str],...];loss_refs:tuple[str,...]=();warning_refs:tuple[str,...]=();revision:int=1
 def __post_init__(self):
  _ref(self.map_ref,"map_ref")
  if self.revision!=1 or not self.source_pins or not self.target_pins:raise ValueError("target maps are immutable and require exact source/target sets")
  if self.mapping_kind not in {MigrationDisposition.MAPPED,MigrationDisposition.TRANSFORMED,MigrationDisposition.SPLIT,MigrationDisposition.MERGED}:raise ValueError("target map requires a positive mapping disposition")
  if self.mapping_kind==MigrationDisposition.SPLIT and (len(self.source_pins)!=1 or len(self.target_pins)<2):raise ValueError("SPLIT requires one source and multiple exact targets")
  if self.mapping_kind==MigrationDisposition.MERGED and (len(self.source_pins)<2 or len(self.target_pins)!=1):raise ValueError("MERGED requires multiple exact sources and one target")
  if self.mapping_kind==MigrationDisposition.MAPPED and (len(self.source_pins)!=1 or len(self.target_pins)!=1):raise ValueError("MAPPED requires one exact source and one exact target")
  _unique(tuple(p.key for p in self.source_pins),"source pins");_unique(tuple(p.key for p in self.target_pins),"target pins");_unique(tuple(self.field_lineage),"field lineage entries");_unique(self.loss_refs,"loss refs");_unique(self.warning_refs,"warnings")

@dataclass(frozen=True,slots=True)
class MigrationQuarantineRecord:
 quarantine_ref:str;source_pin:PinnedRecord;rule_pin:PinnedRecord|None;reason_refs:tuple[str,...];candidate_target_kinds:tuple[RecordKind,...];missing_dependency_refs:tuple[str,...];remediation_frontier_refs:tuple[str,...];permission_ref:str;non_authority:bool=True;revision:int=1;metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  _ref(self.quarantine_ref,"quarantine_ref");_ref(self.permission_ref,"permission")
  if self.revision!=1 or not self.reason_refs or not self.non_authority:raise ValueError("quarantine is immutable, reasoned and explicitly non-authoritative")
  _unique(self.reason_refs,"quarantine reasons");_unique(self.candidate_target_kinds,"candidate target kinds");_unique(self.missing_dependency_refs,"missing dependencies");_unique(self.remediation_frontier_refs,"remediation frontiers")

@dataclass(frozen=True,slots=True)
class MigrationDecisionRecord:
 decision_ref:str;source_pin:PinnedRecord;rule_pin:PinnedRecord|None;disposition:MigrationDisposition;target_map_pin:PinnedRecord|None;quarantine_pin:PinnedRecord|None;warning_refs:tuple[str,...];loss_refs:tuple[str,...];review_refs:tuple[str,...];proof_refs:tuple[str,...];permission_ref:str;revision:int=1
 def __post_init__(self):
  _ref(self.decision_ref,"decision_ref");_ref(self.permission_ref,"permission")
  if self.revision!=1:raise ValueError("migration decisions are immutable")
  positive=self.disposition in {MigrationDisposition.MAPPED,MigrationDisposition.TRANSFORMED,MigrationDisposition.SPLIT,MigrationDisposition.MERGED}
  if positive!=(self.target_map_pin is not None):raise ValueError("positive migration disposition requires exactly one target map")
  if positive and self.rule_pin is None:raise ValueError("positive migration disposition requires exact reviewed rule pin")
  if self.disposition==MigrationDisposition.QUARANTINED and self.quarantine_pin is None:raise ValueError("quarantined decision requires quarantine pin")
  if self.disposition!=MigrationDisposition.QUARANTINED and self.quarantine_pin is not None:raise ValueError("only quarantined decision may carry quarantine pin")
  for x,l in ((self.warning_refs,"warnings"),(self.loss_refs,"losses"),(self.review_refs,"reviews"),(self.proof_refs,"proofs")):_unique(x,l)

@dataclass(frozen=True,slots=True)
class MigrationRollbackRecord:
 rollback_ref:str;batch_ref:str;owned_target_pins:tuple[PinnedRecord,...];inverse_operation_refs:tuple[str,...];blocked_by_dependent_pins:tuple[PinnedRecord,...];pre_batch_store_revision:int;pre_batch_snapshot_fingerprint:str;permission_ref:str;revision:int=1;metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.rollback_ref,"rollback_ref"),(self.batch_ref,"batch_ref"),(self.pre_batch_snapshot_fingerprint,"pre-batch fingerprint"),(self.permission_ref,"permission")):_ref(v,l)
  if self.revision!=1 or self.pre_batch_store_revision<0:raise ValueError("rollback records are immutable with valid pre-batch revision")
  _unique(tuple(p.key for p in self.owned_target_pins),"owned target pins");_unique(self.inverse_operation_refs,"inverse operations");_unique(tuple(p.key for p in self.blocked_by_dependent_pins),"rollback blockers")

@dataclass(frozen=True,slots=True)
class MigrationBatchRecord:
 batch_ref:str;source_pins:tuple[PinnedRecord,...];rule_pins:tuple[PinnedRecord,...];decision_pins:tuple[PinnedRecord,...];source_set_fingerprint:str;rule_set_fingerprint:str;expected_target_store_revision:int;expected_target_snapshot_fingerprint:str;status:MigrationBatchStatus;rollback_pin:PinnedRecord|None;metrics:tuple[tuple[str,float],...]=();error_refs:tuple[str,...]=();permission_ref:str="internal";revision:int=1;supersedes_revision:int|None=None;metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.batch_ref,"batch_ref"),(self.source_set_fingerprint,"source set fingerprint"),(self.rule_set_fingerprint,"rule set fingerprint"),(self.expected_target_snapshot_fingerprint,"target snapshot fingerprint"),(self.permission_ref,"permission")):_ref(v,l)
  if self.revision<1 or self.expected_target_store_revision<0:raise ValueError("migration batch revision/store revision invalid")
  _sup(self.revision,self.supersedes_revision,"migration batch")
  if not self.source_pins or not self.decision_pins:raise ValueError("migration batch requires exact source and decision sets")
  _unique(tuple(p.key for p in self.source_pins),"batch sources");_unique(tuple(p.key for p in self.rule_pins),"batch rules");_unique(tuple(p.key for p in self.decision_pins),"batch decisions");_unique(tuple(k for k,_ in self.metrics),"batch metric keys");_unique(self.error_refs,"batch errors")

@dataclass(frozen=True,slots=True)
class MigrationIntentionalChangeRecord:
 change_ref:str;legacy_behavior_ref:str;v350_behavior_ref:str;reason_ref:str;approved_by_refs:tuple[str,...];fixture_pins:tuple[PinnedRecord,...];permission_ref:str="internal";revision:int=1
 def __post_init__(self):
  for v,l in ((self.change_ref,"change_ref"),(self.legacy_behavior_ref,"legacy behavior"),(self.v350_behavior_ref,"v350 behavior"),(self.reason_ref,"reason"),(self.permission_ref,"permission")):_ref(v,l)
  if self.revision!=1 or not self.approved_by_refs or not self.fixture_pins:raise ValueError("intentional changes require immutable review and exact fixtures")
  _unique(self.approved_by_refs,"approvers");_unique(tuple(p.key for p in self.fixture_pins),"fixture pins")

@dataclass(frozen=True,slots=True)
class SemanticEquivalenceRecord:
 equivalence_ref:str;source_fixture_pins:tuple[PinnedRecord,...];target_trace_pins:tuple[PinnedRecord,...];dimensions:tuple[tuple[str,EquivalenceOutcome],...];overall:EquivalenceOutcome;intentional_change_pins:tuple[PinnedRecord,...];difference_refs:tuple[str,...];proof_refs:tuple[str,...];runner_ref:str;runner_revision:str;permission_ref:str="internal";revision:int=1;metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.equivalence_ref,"equivalence_ref"),(self.runner_ref,"runner_ref"),(self.runner_revision,"runner_revision"),(self.permission_ref,"permission")):_ref(v,l)
  if self.revision!=1 or not self.dimensions:raise ValueError("equivalence records are immutable and dimensioned")
  _unique(tuple(p.key for p in self.source_fixture_pins),"source fixture pins");_unique(tuple(p.key for p in self.target_trace_pins),"target trace pins");_unique(tuple(k for k,_ in self.dimensions),"equivalence dimensions");_unique(tuple(p.key for p in self.intentional_change_pins),"intentional changes");_unique(self.difference_refs,"differences");_unique(self.proof_refs,"proofs")

def fingerprint(prefix,value):return semantic_fingerprint(prefix,value,64)
def _ref(v,l):
 if not isinstance(v,str) or not v.strip():raise ValueError(f"{l} must be non-empty")
def _unique(v,l):
 x=tuple(v)
 if len(x)!=len(set(x)):raise ValueError(f"{l} must be unique")
def _sup(r,s,l):
 if s is not None and not 1<=s<r:raise ValueError(f"{l} supersedes_revision must target older revision")
