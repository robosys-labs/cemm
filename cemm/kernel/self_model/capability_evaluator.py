"""CapabilityEvaluator — sole capability authority.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §11, AUTHORITY_MATRIX):
- CapabilityEvaluator is the only capability authority.
- A current capability assessment requires:
    semantic competence
    ∧ registered implementation
    ∧ component health
    ∧ required input channel
    ∧ required output/effect channel
    ∧ sufficient resources
    ∧ permission and policy authorization
    ∧ contextual preconditions
- Observed reliability and current degradation qualify the result.
- A static entity schema, phrase template, or capability list cannot
  override live evidence.
- Self-description must query current assessments and ordinary semantic
  records, then pass through the normal response planner and NLG pipeline.
- self_model cannot maintain independent truth facts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.capability import CapabilityAssessment, ConditionResult
from ..model.identity import TimeExtent


@dataclass(frozen=True, slots=True)
class ComponentHealthRecord:
    """Live health record for a component."""
    component_id: str
    health: str = "unknown"  # healthy, degraded, failed, unknown
    last_checked: str = ""


@dataclass(frozen=True, slots=True)
class ResourceRecord:
    """Live resource availability record."""
    resource_kind: str  # cpu, memory, tokens, api_quota, etc.
    status: str = "unknown"  # available, constrained, exhausted, unknown
    available_amount: float = 0.0
    required_amount: float = 0.0


@dataclass(frozen=True, slots=True)
class ChannelRecord:
    """Live input/output channel record."""
    channel_kind: str  # input, output, effect
    channel_id: str
    is_available: bool = False
    detail: str = ""


@dataclass(frozen=True, slots=True)
class PermissionRecord:
    """Live permission and policy record."""
    operation_ref: str
    is_allowed: bool = False
    policy_ref: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CompetenceRecord:
    """Live semantic competence record."""
    schema_ref: str
    is_competent: bool = False
    competence_score: float = 0.0
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ImplementationRecord:
    """Registered implementation record."""
    operation_ref: str
    implementation_id: str = ""
    is_registered: bool = False


@dataclass(frozen=True, slots=True)
class ContextualPrecondition:
    """A contextual precondition for an operation."""
    precondition_id: str
    description: str = ""
    is_satisfied: bool = False


class CapabilityEvaluator:
    """Sole capability authority.

    A current capability assessment requires ALL 8 conditions:
    1. semantic competence
    2. registered implementation
    3. component health
    4. required input channel
    5. required output/effect channel
    6. sufficient resources
    7. permission and policy authorization
    8. contextual preconditions

    Observed reliability and current degradation qualify the result.
    A static entity schema, phrase template, or capability list cannot
    override live evidence.
    """

    def evaluate(
        self,
        subject_ref: str,
        operation_schema_ref: str,
        competence: CompetenceRecord | None = None,
        implementation: ImplementationRecord | None = None,
        component_health: ComponentHealthRecord | None = None,
        input_channel: ChannelRecord | None = None,
        output_channel: ChannelRecord | None = None,
        resources: tuple[ResourceRecord, ...] = (),
        permission: PermissionRecord | None = None,
        preconditions: tuple[ContextualPrecondition, ...] = (),
        observed_reliability: float | None = None,
    ) -> CapabilityAssessment:
        """Evaluate current capability for a subject and operation.

        Uses live component, resource, permission, and competence records.
        Static schema declarations cannot override live evidence.
        """
        condition_results: list[ConditionResult] = []
        limitations: list[str] = []

        # 1. Semantic competence
        cond_competence = competence is not None and competence.is_competent
        condition_results.append(ConditionResult(
            condition_ref="semantic_competence",
            satisfied=cond_competence,
            detail=competence.detail if competence else "No competence record",
        ))
        if not cond_competence:
            limitations.append("semantic competence not met")

        # 2. Registered implementation
        cond_impl = implementation is not None and implementation.is_registered
        condition_results.append(ConditionResult(
            condition_ref="registered_implementation",
            satisfied=cond_impl,
            detail=implementation.implementation_id if implementation else "No implementation",
        ))
        if not cond_impl:
            limitations.append("no registered implementation")

        # 3. Component health (degraded is still functional, just qualified)
        cond_health = (
            component_health is not None
            and component_health.health in ("healthy", "degraded")
        )
        condition_results.append(ConditionResult(
            condition_ref="component_health",
            satisfied=cond_health,
            detail=component_health.health if component_health else "unknown",
        ))
        if component_health and component_health.health == "degraded":
            limitations.append("component degraded")
        elif component_health and component_health.health == "failed":
            limitations.append("component failed")

        # 4. Required input channel
        cond_input = input_channel is not None and input_channel.is_available
        condition_results.append(ConditionResult(
            condition_ref="input_channel",
            satisfied=cond_input,
            detail=input_channel.detail if input_channel else "No input channel",
        ))
        if not cond_input:
            limitations.append("input channel unavailable")

        # 5. Required output/effect channel
        cond_output = output_channel is not None and output_channel.is_available
        condition_results.append(ConditionResult(
            condition_ref="output_channel",
            satisfied=cond_output,
            detail=output_channel.detail if output_channel else "No output channel",
        ))
        if not cond_output:
            limitations.append("output channel unavailable")

        # 6. Sufficient resources
        cond_resources = all(
            r.status in ("available",) and r.available_amount >= r.required_amount
            for r in resources
        ) if resources else False
        condition_results.append(ConditionResult(
            condition_ref="sufficient_resources",
            satisfied=cond_resources,
            detail=f"{len(resources)} resource(s) checked",
        ))
        for r in resources:
            if r.status == "constrained":
                limitations.append(f"resource {r.resource_kind} constrained")
            elif r.status == "exhausted":
                limitations.append(f"resource {r.resource_kind} exhausted")

        # 7. Permission and policy authorization
        cond_permission = permission is not None and permission.is_allowed
        condition_results.append(ConditionResult(
            condition_ref="permission_policy",
            satisfied=cond_permission,
            detail=permission.detail if permission else "No permission record",
        ))
        if not cond_permission:
            limitations.append("permission denied")

        # 8. Contextual preconditions
        cond_preconditions = all(p.is_satisfied for p in preconditions) if preconditions else False
        condition_results.append(ConditionResult(
            condition_ref="contextual_preconditions",
            satisfied=cond_preconditions,
            detail=f"{len(preconditions)} precondition(s) checked",
        ))
        for p in preconditions:
            if not p.is_satisfied:
                limitations.append(f"precondition not met: {p.description}")

        # All 8 conditions must be met
        all_met = (
            cond_competence
            and cond_impl
            and cond_health
            and cond_input
            and cond_output
            and cond_resources
            and cond_permission
            and cond_preconditions
        )

        # Determine status with degradation
        if all_met:
            status = "capable"
            if component_health and component_health.health == "degraded":
                status = "degraded"
        elif component_health and component_health.health == "failed":
            status = "incapable"
        else:
            status = "incapable"

        # Determine health
        if component_health:
            health = component_health.health
        else:
            health = "unknown"

        # Determine resource status
        if resources:
            if any(r.status == "exhausted" for r in resources):
                resource_status = "exhausted"
            elif any(r.status == "constrained" for r in resources):
                resource_status = "constrained"
            else:
                resource_status = "available"
        else:
            resource_status = "unknown"

        # Determine permission status
        if permission:
            permission_status = "allowed" if permission.is_allowed else "denied"
        else:
            permission_status = "unknown"

        return CapabilityAssessment(
            subject_ref=subject_ref,
            operation_schema_ref=operation_schema_ref,
            status=status,
            competence=competence.competence_score if competence else None,
            component_refs=(component_health.component_id,) if component_health else (),
            health=health,
            resource_status=resource_status,
            permission_status=permission_status,
            condition_results=tuple(condition_results),
            limitations=tuple(limitations),
            observed_reliability=observed_reliability,
            evidence_refs=tuple(result.condition_ref for result in condition_results),
        )
