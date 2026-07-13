"""OperationSchema, CapabilitySchema, and supporting types.

Import boundary: standard library only → model.refs, schema.grounding_spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .grounding_spec import SemanticPattern
from .predicate import MutationTemplate


@dataclass(frozen=True, slots=True)
class CostModel:
    """Cost model for an operation."""
    base_cost: float = 0.0
    resource_costs: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    """A resource requirement for a capability."""
    resource_kind: str
    minimum: float = 0.0
    maximum: float | None = None


@dataclass(frozen=True, slots=True)
class CompetencyTest:
    """A competency test for a capability."""
    test_kind: str = ""
    input_ref: str = ""
    expected_ref: str = ""
    oracle_kind: str = "invariant"


@dataclass(frozen=True, slots=True)
class OperationSchema:
    """Executable definition of an operation.

    operation_class: cognitive, communicative, external
    """
    semantic_key: str
    operation_class: str = "cognitive"
    input_roles: tuple[str, ...] = ()  # Ref[RoleSchema]
    output_roles: tuple[str, ...] = ()  # Ref[RoleSchema]
    semantic_preconditions: tuple[SemanticPattern, ...] = ()
    capability_schema_refs: tuple[str, ...] = ()  # Ref[CapabilitySchema]
    policy_refs: tuple[str, ...] = ()  # Ref[PolicySchema]
    cost_model: CostModel = field(default_factory=CostModel)
    predicted_effects: tuple[MutationTemplate, ...] = ()
    failure_modes: tuple[str, ...] = ()
    idempotency_policy: str = "strict"  # strict, idempotent, at_most_once
    adapter_binding: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilitySchema:
    """Executable definition of a capability.

    Capability schemas declare required components, channels, resources,
    and competency tests. Static schema declarations cannot advertise
    capabilities — live assessment is required.
    """
    semantic_key: str
    operation_schema_refs: tuple[str, ...] = ()  # Ref[OperationSchema]
    required_component_types: tuple[str, ...] = ()
    required_input_channels: tuple[str, ...] = ()
    required_output_channels: tuple[str, ...] = ()
    required_resources: tuple[ResourceRequirement, ...] = ()
    contextual_preconditions: tuple[SemanticPattern, ...] = ()
    competency_tests: tuple[CompetencyTest, ...] = ()
