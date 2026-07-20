"""Deterministic codecs for Phase-16 Response UOL records."""
from __future__ import annotations
from typing import Any, Mapping
from ..learning.codec import _pin
from ..schema.model import SchemaLifecycleStatus, UseDecision, UseOperation, canonical_data
from ..storage.model import RecordKind
from ..uol.codec import uol_graph_from_document
from .model import (ResponseBindingSelector,ResponseOmissionRecord,ResponseSelectorMode,ResponseTransformationProof,ResponseTransformRuleRecord,ResponseUOLRecord)

def response_record_to_document(record:Any)->dict[str,Any]: return dict(canonical_data(record))
def _selector(v):
 d=dict(v); return ResponseBindingSelector(str(d['output_port_ref']),ResponseSelectorMode(str(d['mode'])),d.get('source_field'),d.get('source_port_ref'),d.get('fixed_ref'),None if d.get('target_index') is None else int(d['target_index']),d.get('target_port_ref'))
def response_transform_rule_from_document(v:Mapping[str,Any])->ResponseTransformRuleRecord:
 d=dict(v); return ResponseTransformRuleRecord(rule_ref=str(d['rule_ref']),goal_schema_pins=tuple((str(x[0]),int(x[1])) for x in d.get('goal_schema_pins',())),source_record_kinds=tuple(RecordKind(str(x)) for x in d.get('source_record_kinds',())),output_schema_ref=str(d['output_schema_ref']),output_schema_revision=int(d['output_schema_revision']),selectors=tuple(_selector(x) for x in d.get('selectors',())),required_source_statuses=tuple(map(str,d.get('required_source_statuses',()))),mandatory_qualification_refs=tuple(map(str,d.get('mandatory_qualification_refs',()))),priority=int(d.get('priority',0)),lifecycle_status=SchemaLifecycleStatus(str(d.get('lifecycle_status','candidate'))),use_operation=UseOperation(str(d.get('use_operation','plan'))),use_decision=UseDecision(str(d.get('use_decision','deny'))),permission_ref=str(d.get('permission_ref','public')),revision=int(d.get('revision',1)),supersedes_revision=None if d.get('supersedes_revision') is None else int(d['supersedes_revision']),metadata=dict(d.get('metadata',{})))
def response_transformation_proof_from_document(v):
 d=dict(v); return ResponseTransformationProof(str(d['proof_ref']),_pin(dict(d['goal_candidate_pin'])),_pin(dict(d['rule_pin'])),tuple(_pin(dict(x)) for x in d.get('input_pins',())),tuple(map(str,d.get('output_refs',()))),tuple(_pin(dict(x)) for x in d.get('authorization_pins',())),tuple(_pin(dict(x)) for x in d.get('omitted_input_pins',())),tuple(map(str,d.get('aggregation_input_refs',()))),tuple(map(str,d.get('reason_refs',()))),int(d.get('revision',1)))
def response_omission_from_document(v):
 d=dict(v); return ResponseOmissionRecord(str(d['omission_ref']),_pin(dict(d['goal_candidate_pin'])),tuple(_pin(dict(x)) for x in d.get('omitted_pins',())),str(d['reason_ref']),bool(d['authorized']),bool(d.get('mandatory',False)),int(d.get('revision',1)))
def response_uol_from_document(v):
 d=dict(v); return ResponseUOLRecord(response_ref=str(d['response_ref']),goal_decision_pin=_pin(dict(d['goal_decision_pin'])),selected_goal_pins=tuple(_pin(dict(x)) for x in d.get('selected_goal_pins',())),source_pins=tuple(_pin(dict(x)) for x in d.get('source_pins',())),transformation_proof_refs=tuple(map(str,d.get('transformation_proof_refs',()))),omission_refs=tuple(map(str,d.get('omission_refs',()))),graph=uol_graph_from_document(dict(d['graph'])),unresolved_frontier_refs=tuple(map(str,d.get('unresolved_frontier_refs',()))),audience_refs=tuple(map(str,d.get('audience_refs',()))),perspective_ref=str(d['perspective_ref']),context_ref=str(d['context_ref']),permission_ref=str(d['permission_ref']),sensitivity=str(d.get('sensitivity','normal')),snapshot_revision=int(d.get('snapshot_revision',0)),snapshot_fingerprint=str(d.get('snapshot_fingerprint','')),revision=int(d.get('revision',1)),metadata=dict(d.get('metadata',{})))
