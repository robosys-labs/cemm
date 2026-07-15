"""CapabilityAssessment — live capability evaluation for a referent."""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import TimeExtent


@dataclass(frozen=True, slots=True)
class ConditionResult:
    condition_ref: str
    satisfied: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CapabilityAssessment:
    """Current, evidence-carrying assessment of one operation capability."""

    subject_ref: str
    operation_schema_ref: str
    assessment_id: str = ""
    context_ref: str = "actual"
    environment_fingerprint: str = ""
    status: str = "unknown"
    competence: float | None = None
    component_refs: tuple[str, ...] = ()
    health: str = "unknown"
    resource_status: str = "unknown"
    permission_status: str = "unknown"
    condition_results: tuple[ConditionResult, ...] = ()
    limitations: tuple[str, ...] = ()
    observed_reliability: float | None = None
    valid_time: TimeExtent = field(default_factory=TimeExtent)
    evidence_refs: tuple[str, ...] = ()

    @property
    def is_capable(self) -> bool:
        return self.status in {"capable", "degraded"}

    @property
    def operation_ref(self) -> str:
        return self.operation_schema_ref
