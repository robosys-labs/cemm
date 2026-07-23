"""Canonical response transformation/proof record contracts for v3.5.1."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..learning.model import PinnedRecord
from ..schema.model import SchemaLifecycleStatus, UseDecision, UseOperation, semantic_fingerprint
from ..storage.model import RecordKind


class StrEnum(str,Enum):
    def __str__(self): return self.value


class ResponseTransformKind(StrEnum):
    BUILD_APPLICATION = "build_application"
    BOUND_QUERY_GRAPH = "bound_query_graph"
    CLARIFY_QUERY_GAP = "clarify_query_gap"


class ResponseSelectorMode(StrEnum):
    SOURCE = "source"
    SOURCE_FIELD = "source_field"
    APPLICATION_PORT = "application_port"
    TARGET = "target"
    FIXED = "fixed"
    QUERY_VALUE = "query_value"


@dataclass(frozen=True,slots=True)
class ResponseBindingSelector:
    output_port_ref: str
    mode: ResponseSelectorMode
    source_field: str|None=None
    source_port_ref: str|None=None
    fixed_ref: str|None=None
    target_index: int|None=None
    target_port_ref: str|None=None
    def __post_init__(self):
        _ref(self.output_port_ref,"response output port")
        if self.mode==ResponseSelectorMode.SOURCE_FIELD and not self.source_field: raise ValueError("SOURCE_FIELD requires source_field")
        if self.mode==ResponseSelectorMode.APPLICATION_PORT and not self.source_port_ref: raise ValueError("APPLICATION_PORT requires source_port_ref")
        if self.mode==ResponseSelectorMode.FIXED and not self.fixed_ref: raise ValueError("FIXED requires fixed_ref")
        if self.mode==ResponseSelectorMode.TARGET:
            if self.target_port_ref is None and (self.target_index is None or self.target_index<0): raise ValueError("TARGET requires target_port_ref or legacy non-negative target_index")
            if self.target_port_ref is not None and not self.target_port_ref.strip(): raise ValueError("TARGET target_port_ref cannot be blank")


@dataclass(frozen=True,slots=True)
class ResponseTransformRuleRecord:
    rule_ref: str
    goal_schema_pins: tuple[tuple[str,int],...]
    source_record_kinds: tuple[RecordKind,...]
    output_schema_ref: str
    output_schema_revision: int
    selectors: tuple[ResponseBindingSelector,...]
    required_source_statuses: tuple[str,...]=()
    mandatory_qualification_refs: tuple[str,...]=()
    priority: int=0
    lifecycle_status: SchemaLifecycleStatus=SchemaLifecycleStatus.CANDIDATE
    use_operation: UseOperation=UseOperation.PLAN
    use_decision: UseDecision=UseDecision.DENY
    permission_ref: str="public"
    revision: int=1
    supersedes_revision: int|None=None
    metadata: Mapping[str,Any]=field(default_factory=dict)
    transform_kind: ResponseTransformKind=ResponseTransformKind.BUILD_APPLICATION
    def __post_init__(self):
        for v,l in ((self.rule_ref,"response transform rule"),(self.output_schema_ref,"output schema"),(self.permission_ref,"permission")): _ref(v,l)
        if min(self.output_schema_revision,self.revision)<1: raise ValueError("response transform revisions must be positive")
        if self.supersedes_revision is not None and not 1<=self.supersedes_revision<self.revision: raise ValueError("invalid transform supersession")
        if not self.goal_schema_pins or not self.source_record_kinds or not self.selectors: raise ValueError("response transform rule requires goal/source/selector contracts")
        _unique(self.goal_schema_pins,"goal pins"); _unique(self.source_record_kinds,"source kinds"); _unique(tuple(s.output_port_ref for s in self.selectors),"output selector ports")
    @property
    def executable(self): return self.lifecycle_status==SchemaLifecycleStatus.ACTIVE and self.use_decision==UseDecision.ALLOW


@dataclass(frozen=True,slots=True)
class ResponseTransformationProof:
    proof_ref: str
    goal_candidate_pin: PinnedRecord
    rule_pin: PinnedRecord
    input_pins: tuple[PinnedRecord,...]
    output_refs: tuple[str,...]
    authorization_pins: tuple[PinnedRecord,...]=()
    omitted_input_pins: tuple[PinnedRecord,...]=()
    aggregation_input_refs: tuple[str,...]=()
    reason_refs: tuple[str,...]=()
    revision: int=1
    def __post_init__(self):
        _ref(self.proof_ref,"response transformation proof")
        if self.revision!=1: raise ValueError("response transformation proofs are immutable")
        if not self.input_pins or not self.output_refs: raise ValueError("response proof requires input and output lineage")
        _unique(tuple(p.key for p in self.input_pins),"response proof inputs"); _unique(self.output_refs,"response proof outputs")


@dataclass(frozen=True,slots=True)
class ResponseOmissionRecord:
    omission_ref: str
    goal_candidate_pin: PinnedRecord
    omitted_pins: tuple[PinnedRecord,...]
    reason_ref: str
    authorized: bool
    mandatory: bool=False
    revision: int=1
    def __post_init__(self):
        _ref(self.omission_ref,"omission_ref"); _ref(self.reason_ref,"omission reason")
        if self.revision!=1 or not self.omitted_pins: raise ValueError("omission must be immutable and pin omitted content")
        if self.mandatory and self.authorized: raise ValueError("mandatory content cannot be authorized for omission")




def _ref(v,l):
    if not isinstance(v,str) or not v.strip(): raise ValueError(f"{l} must be a non-empty reference")
def _unique(v,l):
    if len(v)!=len(set(v)): raise ValueError(f"{l} must be unique")
