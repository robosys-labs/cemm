"""CEMM v3.5 Phase-17 multilingual realization algebra contracts."""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import Enum
from typing import Any,Mapping
from ..learning.model import PinnedRecord
from ..schema.model import SchemaLifecycleStatus,UseDecision,UseOperation,semantic_fingerprint

class StrEnum(str,Enum):
 def __str__(self): return self.value
class MorphologyOperation(StrEnum):
 IDENTITY="identity"; PREFIX="prefix"; SUFFIX="suffix"; REPLACE_FORM="replace_form"; ZERO="zero"
class RoundTripDecision(StrEnum):
 PASS="pass"; FAIL="fail"; PARTIAL="partial"

@dataclass(frozen=True,slots=True)
class RealizationRequestRecord:
 request_ref:str; response_uol_pin:PinnedRecord; language_tag:str; script:str|None; locale_ref:str|None; audience_refs:tuple[str,...]; register_refs:tuple[str,...]; language_pack_pins:tuple[PinnedRecord,...]; budget_ref:str; permission_ref:str; sensitivity:str="normal"; revision:int=1; metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.request_ref,"request_ref"),(self.language_tag,"language_tag"),(self.budget_ref,"budget_ref"),(self.permission_ref,"permission_ref"),(self.sensitivity,"sensitivity")): _ref(v,l)
  if self.revision!=1 or not self.language_pack_pins: raise ValueError("realization request must be immutable and pin language packages")
  _unique(self.audience_refs,"audiences");_unique(self.register_refs,"registers");_unique(tuple(p.key for p in self.language_pack_pins),"language pack pins")

@dataclass(frozen=True,slots=True)
class ArgumentFrameRecord:
 frame_ref:str; pack_ref:str; pack_revision:int; predicate_schema_classes:tuple[str,...]; required_port_refs:tuple[str,...]; optional_port_refs:tuple[str,...]; slot_order:tuple[str,...]; port_to_slot:tuple[tuple[str,str],...]; feature_constraints:tuple[tuple[str,str],...]=(); discourse_act_refs:tuple[str,...]=(); lifecycle_status:SchemaLifecycleStatus=SchemaLifecycleStatus.CANDIDATE; use_operation:UseOperation=UseOperation.REALIZE; use_decision:UseDecision=UseDecision.DENY; permission_ref:str="public"; revision:int=1; supersedes_revision:int|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.frame_ref,"frame_ref"),(self.pack_ref,"pack_ref"),(self.permission_ref,"permission_ref")): _ref(v,l)
  if min(self.pack_revision,self.revision)<1: raise ValueError("frame revisions must be positive")
  if self.supersedes_revision is not None and not 1<=self.supersedes_revision<self.revision: raise ValueError("invalid frame supersession")
  if self.use_operation!=UseOperation.REALIZE: raise ValueError("argument frame must be REALIZE-axis")
  _unique(self.required_port_refs,"required frame ports");_unique(self.optional_port_refs,"optional frame ports");_unique(self.slot_order,"slot order");_unique(tuple(p for p,_ in self.port_to_slot),"frame port mappings");_unique(tuple(s for _,s in self.port_to_slot),"frame slot mappings")
 @property
 def executable(self): return self.lifecycle_status==SchemaLifecycleStatus.ACTIVE and self.use_decision==UseDecision.ALLOW

@dataclass(frozen=True,slots=True)
class MorphologyRuleRecord:
 rule_ref:str; pack_ref:str; pack_revision:int; lexical_category:str; required_features:tuple[tuple[str,str],...]; operation:MorphologyOperation; operand:str=""; priority:int=0; lifecycle_status:SchemaLifecycleStatus=SchemaLifecycleStatus.CANDIDATE; use_operation:UseOperation=UseOperation.REALIZE; use_decision:UseDecision=UseDecision.DENY; permission_ref:str="public"; revision:int=1; supersedes_revision:int|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.rule_ref,"morphology rule_ref"),(self.pack_ref,"pack_ref"),(self.lexical_category,"lexical_category"),(self.permission_ref,"permission_ref")): _ref(v,l)
  if min(self.pack_revision,self.revision)<1: raise ValueError("morphology revisions must be positive")
  if self.supersedes_revision is not None and not 1<=self.supersedes_revision<self.revision: raise ValueError("invalid morphology supersession")
  if self.use_operation!=UseOperation.REALIZE: raise ValueError("morphology rule must be REALIZE-axis")
  _unique(tuple(k for k,_ in self.required_features),"morphology feature keys")
 @property
 def executable(self): return self.lifecycle_status==SchemaLifecycleStatus.ACTIVE and self.use_decision==UseDecision.ALLOW

@dataclass(frozen=True,slots=True)
class LinearizationRuleRecord:
 rule_ref:str; pack_ref:str; pack_revision:int; construction_ref:str; precedence_pairs:tuple[tuple[str,str],...]; separator:str=" "; prefix_tokens:tuple[str,...]=(); suffix_tokens:tuple[str,...]=(); lifecycle_status:SchemaLifecycleStatus=SchemaLifecycleStatus.CANDIDATE; use_operation:UseOperation=UseOperation.REALIZE; use_decision:UseDecision=UseDecision.DENY; permission_ref:str="public"; revision:int=1; supersedes_revision:int|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.rule_ref,"linearization rule_ref"),(self.pack_ref,"pack_ref"),(self.construction_ref,"construction_ref"),(self.permission_ref,"permission_ref")): _ref(v,l)
  if min(self.pack_revision,self.revision)<1: raise ValueError("linearization revisions must be positive")
  if self.supersedes_revision is not None and not 1<=self.supersedes_revision<self.revision: raise ValueError("invalid linearization supersession")
  if self.use_operation!=UseOperation.REALIZE: raise ValueError("linearization rule must be REALIZE-axis")
  _unique(self.precedence_pairs,"precedence pairs")
 @property
 def executable(self): return self.lifecycle_status==SchemaLifecycleStatus.ACTIVE and self.use_decision==UseDecision.ALLOW

@dataclass(frozen=True,slots=True)
class DeepClausePlanRecord:
 clause_ref:str; request_pin:PinnedRecord; response_application_ref:str; predicate_schema_ref:str; predicate_schema_revision:int; argument_refs:tuple[tuple[str,tuple[tuple[str,str],...]],...]; discourse_act_ref:str|None; feature_values:tuple[tuple[str,str],...]; scope_refs:tuple[str,...]; coordination_refs:tuple[str,...]; information_structure:tuple[tuple[str,str],...]; frame_pin:PinnedRecord; revision:int=1
 def __post_init__(self):
  for v,l in ((self.clause_ref,"clause_ref"),(self.response_application_ref,"response application"),(self.predicate_schema_ref,"predicate schema")): _ref(v,l)
  if min(self.predicate_schema_revision,self.revision)<1: raise ValueError("clause revisions must be positive")
  _unique(tuple(k for k,_ in self.argument_refs),"clause argument ports");_unique(tuple(k for k,_ in self.feature_values),"clause features")
  for _port,fillers in self.argument_refs:
   _unique(tuple(fillers),"clause filler identities")

@dataclass(frozen=True,slots=True)
class ReferencePlanRecord:
 reference_ref:str; request_pin:PinnedRecord; referent_pin:PinnedRecord; competitor_pins:tuple[PinnedRecord,...]; allowed_identity_facet_pins:tuple[PinnedRecord,...]; strategy_ref:str; language_rule_pin:PinnedRecord; feature_values:tuple[tuple[str,str],...]; revision:int=1
 def __post_init__(self):
  for v,l in ((self.reference_ref,"reference_ref"),(self.strategy_ref,"reference strategy")): _ref(v,l)
  if self.revision!=1: raise ValueError("reference plans are immutable")

@dataclass(frozen=True,slots=True)
class SurfaceCandidateRecord:
 candidate_ref:str; request_pin:PinnedRecord; clause_pins:tuple[PinnedRecord,...]; frame_pins:tuple[PinnedRecord,...]; lexical_pins:tuple[PinnedRecord,...]; morphology_pins:tuple[PinnedRecord,...]; reference_pins:tuple[PinnedRecord,...]; linearization_pins:tuple[PinnedRecord,...]; tokens:tuple[str,...]; surface:str; generation_score:float; permission_ref:str; snapshot_revision:int; snapshot_fingerprint:str; revision:int=1; metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.candidate_ref,"surface candidate_ref"),(self.permission_ref,"permission_ref"),(self.snapshot_fingerprint,"surface snapshot fingerprint")): _ref(v,l)
  if self.revision!=1 or not self.tokens or self.snapshot_revision<0: raise ValueError("surface candidate must be immutable, non-empty, and snapshot-pinned")
  if not (0.0<=self.generation_score<=1.0): raise ValueError("generation score must be in [0,1]")

@dataclass(frozen=True,slots=True)
class SemanticAnalyzerContractRecord:
 contract_ref:str; analyzer_ref:str; analyzer_revision:str; supported_language_tags:tuple[str,...]; competence_case_refs:tuple[str,...]; resource_fingerprint:str; permission_ref:str="internal"; active:bool=False; revision:int=1; supersedes_revision:int|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
 def __post_init__(self):
  for v,l in ((self.contract_ref,"analyzer contract_ref"),(self.analyzer_ref,"analyzer_ref"),(self.analyzer_revision,"analyzer_revision"),(self.resource_fingerprint,"analyzer resource fingerprint"),(self.permission_ref,"permission_ref")):_ref(v,l)
  if self.revision<1:raise ValueError("analyzer contract revision must be positive")
  if self.supersedes_revision is not None and not 1<=self.supersedes_revision<self.revision:raise ValueError("invalid analyzer contract supersession")
  if self.active and not self.competence_case_refs:raise ValueError("active semantic analyzer contract requires competence cases")
  _unique(self.supported_language_tags,"analyzer languages");_unique(self.competence_case_refs,"analyzer competence cases")

@dataclass(frozen=True,slots=True)
class SemanticRoundTripRecord:
 roundtrip_ref:str; request_pin:PinnedRecord; surface_candidate_pin:PinnedRecord; analyzer_ref:str; analyzer_revision:str; recovered_graph_fingerprint:str; expected_graph_fingerprint:str; decision:RoundTripDecision; additions:tuple[str,...]; losses:tuple[str,...]; drift_refs:tuple[str,...]; proof_refs:tuple[str,...]; analyzer_contract_pin:PinnedRecord|None=None; revision:int=1
 def __post_init__(self):
  for v,l in ((self.roundtrip_ref,"roundtrip_ref"),(self.analyzer_ref,"analyzer_ref"),(self.analyzer_revision,"analyzer_revision"),(self.recovered_graph_fingerprint,"recovered fingerprint"),(self.expected_graph_fingerprint,"expected fingerprint")): _ref(v,l)
  if self.revision!=1: raise ValueError("round-trip records are immutable")
  if self.decision==RoundTripDecision.PASS and (self.additions or self.losses or self.drift_refs): raise ValueError("PASS cannot contain semantic drift")
  if self.analyzer_contract_pin is None: raise ValueError("roundtrip requires analyzer_contract_pin")

def _ref(v,l):
 if not isinstance(v,str) or not v.strip(): raise ValueError(f"{l} must be non-empty")
def _unique(v,l):
 if len(v)!=len(set(v)): raise ValueError(f"{l} must be unique")
