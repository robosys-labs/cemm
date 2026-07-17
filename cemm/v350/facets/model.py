"""Derived facet, entitlement, and referent-knowledge projections for CEMM v3.5.

These records are cycle-pinned views.  They never become a competing truth
store and defaults represented here are expectations, not state assignments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..schema.model import (
    EntitlementApplicability,
    EntitlementInheritancePolicy,
    SchemaRevisionRef,
    semantic_fingerprint,
    canonical_data,
)
from ..storage.model import ConditionTruth
from ..uol.model import CapabilityStatus, SemanticApplication


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ProjectionStatus(StrEnum):
    ACTIVE = "active"
    LATENT = "latent"
    DEFAULT_EXPECTED = "default_expected"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    TERMINATED = "terminated"
    INAPPLICABLE = "inapplicable"
    CONTRADICTED = "contradicted"


@dataclass(frozen=True, slots=True)
class TypeClosureMember:
    type_ref: str
    revision: int
    depth: int
    direct: bool
    source_assertion_refs: tuple[str, ...] = ()
    path_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TypeClosure:
    referent_ref: str
    context_ref: str
    at_time: str | None
    members: tuple[TypeClosureMember, ...]
    opposed_type_refs: tuple[str, ...] = ()
    contradicted_type_refs: tuple[str, ...] = ()
    unresolved_type_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    dependency_fingerprint: str = ""

    @property
    def type_refs(self) -> frozenset[str]:
        return frozenset(item.type_ref for item in self.members)

    def member(self, type_ref: str) -> TypeClosureMember | None:
        return next((item for item in self.members if item.type_ref == type_ref), None)


@dataclass(frozen=True, slots=True)
class ConditionAssessment:
    condition_ref: str
    truth: ConditionTruth
    evidence_refs: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ProjectedEntitlement:
    facet_ref: str
    status: ProjectionStatus
    applicability: EntitlementApplicability | None
    activation_policy: str
    inheritance_policies: tuple[EntitlementInheritancePolicy, ...]
    value_domain_refs: tuple[str, ...]
    default_rule_refs: tuple[str, ...]
    owner_type_refs: tuple[str, ...]
    source_entitlement_refs: tuple[str, ...]
    source_entitlement_revisions: tuple[tuple[str, int], ...]
    condition_assessments: tuple[ConditionAssessment, ...] = ()
    blocking_refs: tuple[str, ...] = ()
    confidence: float = 1.0
    dependency_refs: tuple[str, ...] = ()
    dependency_fingerprint: str = ""
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DefaultExpectation:
    expectation_ref: str
    rule_ref: str
    rule_revision: int
    facet_ref: str
    holder_ref: str
    context_ref: str
    dimension_ref: str | None
    dimension_revision: int | None
    value_ref: str | None
    value_revision: int | None
    confidence: float
    condition_assessments: tuple[ConditionAssessment, ...]
    defeater_assessments: tuple[ConditionAssessment, ...]
    dependency_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StateApplicability:
    holder_ref: str
    dimension_ref: str
    dimension_revision: int
    facet_ref: str
    status: ProjectionStatus
    active_value_refs: tuple[str, ...] = ()
    opposed_value_refs: tuple[str, ...] = ()
    terminated_value_refs: tuple[str, ...] = ()
    default_expectations: tuple[DefaultExpectation, ...] = ()
    assignment_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    dependency_fingerprint: str = ""
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityProjection:
    action_schema_ref: str
    action_schema_revision: int
    status: ProjectionStatus
    capability_statuses: tuple[CapabilityStatus, ...]
    capability_refs: tuple[str, ...]
    dependency_refs: tuple[str, ...]
    confidence: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReferentKnowledgeView:
    referent_ref: str
    referent_revision: int
    context_ref: str
    at_time: str | None
    snapshot_revision: int
    type_closure: TypeClosure
    identity_facet_refs: tuple[str, ...]
    facet_entitlements: tuple[ProjectedEntitlement, ...]
    property_applications: tuple[SemanticApplication, ...]
    state_timelines: Mapping[str, tuple[str, ...]]
    state_applicability: tuple[StateApplicability, ...]
    relation_applications: tuple[SemanticApplication, ...]
    role_applications: tuple[SemanticApplication, ...]
    event_refs: tuple[str, ...]
    afforded_action_refs: tuple[str, ...]
    live_capabilities: tuple[CapabilityProjection, ...]
    function_applications: tuple[SemanticApplication, ...]
    resource_applications: tuple[SemanticApplication, ...]
    significance_assessment_refs: tuple[str, ...]
    epistemic_record_refs: tuple[str, ...]
    default_expectations: tuple[DefaultExpectation, ...]
    unresolved_conflicts: tuple[str, ...]
    dependency_refs: tuple[str, ...]
    dependency_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("referent-knowledge-view", canonical_data(self), 64)

    def entitlement(self, facet_ref: str) -> ProjectedEntitlement | None:
        return next((item for item in self.facet_entitlements if item.facet_ref == facet_ref), None)
