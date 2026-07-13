"""Typed dependency graph for schema dependencies.

Import boundary: standard library only → model.refs, schema.envelope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CycleClass(str, Enum):
    """Classification of cyclic dependency components."""
    INVERSE_RELATION_CLUSTER = "inverse_relation_cluster"
    POSITIVE_MONOTONE_RECURSIVE = "positive_monotone_recursive"
    STRATIFIED_DEFEASIBLE = "stratified_defeasible"
    UNSUPPORTED_NON_MONOTONE = "unsupported_non_monotone"


@dataclass(frozen=True, slots=True)
class DependencyNode:
    """A node in the schema dependency graph."""
    schema_ref: str  # Ref[SchemaEnvelope]
    revision: int = 0


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """A typed edge in the schema dependency graph."""
    source: DependencyNode
    target: DependencyNode
    dependency_kind: str  # from SchemaDependency.dependency_kind
    polarity: str = "positive"
    monotonicity: str = "monotone"


@dataclass(frozen=True, slots=True)
class DependencyClosure:
    """Result of closing a schema's dependency graph.

    Cycles through negation, exception priority, permission, effect
    authorization, destructive mutation, identity collapse, or
    single-valued replacement are not directly jointly activated.
    """
    root_ref: str  # Ref[SchemaEnvelope]
    reachable: tuple[DependencyNode, ...] = ()
    edges: tuple[DependencyEdge, ...] = ()
    cycle_components: tuple[tuple[DependencyNode, ...], ...] = ()
    cycle_classes: tuple[CycleClass, ...] = ()
    has_unsupported_cycle: bool = False
    closure_fingerprint: str = ""
