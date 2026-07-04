from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphPattern:
    atom_patterns: list[dict[str, Any]] = field(default_factory=list)
    edge_patterns: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GraphPatchTemplate:
    operations: list[dict[str, Any]] = field(default_factory=list)
    target: str = "concept_lattice"


@dataclass
class PredicateSchema:
    predicate_id: str
    key: str
    owner_concept_ids: list[str] = field(default_factory=list)
    required_ports: list[str] = field(default_factory=list)
    optional_ports: list[str] = field(default_factory=list)
    accepted_subject_concepts: list[str] = field(default_factory=list)
    accepted_object_concepts: list[str] = field(default_factory=list)
    default_edges: list[str] = field(default_factory=list)
    preconditions: list[GraphPattern] = field(default_factory=list)
    effects: list[GraphPatchTemplate] = field(default_factory=list)
    evidence_policy: Any | None = None
    source_support: list[Any] = field(default_factory=list)
    counterexamples: list[Any] = field(default_factory=list)
    confidence: float = 0.5
