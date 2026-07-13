"""CapabilityAssessment — live capability evaluation for a referent.

Import boundary: standard library only → refs, identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import TimeExtent


@dataclass(frozen=True, slots=True)
class ConditionResult:
    """Result of evaluating one precondition or contextual condition."""
    condition_ref: str
    satisfied: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CapabilityAssessment:
    """Live capability assessment for a subject referent.

    Uses live component, resource, permission, and competence records.
    Static schema declarations cannot override live status.
    """
    subject_ref: str  # Ref[Referent]
    operation_schema_ref: str  # Ref[OperationSchema]
    status: str = "unknown"  # capable, incapable, degraded, unknown
    competence: float | None = None
    component_refs: tuple[str, ...] = ()
    health: str = "unknown"  # healthy, degraded, failed, unknown
    resource_status: str = "unknown"  # available, constrained, exhausted, unknown
    permission_status: str = "unknown"  # allowed, denied, unknown
    condition_results: tuple[ConditionResult, ...] = ()
    limitations: tuple[str, ...] = ()
    observed_reliability: float | None = None
    valid_time: TimeExtent = field(default_factory=TimeExtent)
    evidence_refs: tuple[str, ...] = ()
