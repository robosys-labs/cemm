from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EdgePattern:
    edge_type: str
    direction: str = "outgoing"
    target_kind: str | None = None
    target_concept: str | None = None


@dataclass
class ResolverPolicy:
    strategy: str = "score"
    min_score: float = 0.3
    allow_inheritance: bool = True
    allow_placeholder: bool = True


@dataclass
class OperationalPort:
    port_id: str
    owner_concept_id: str
    key: str
    required: bool = False
    accepted_atom_kinds: list[str] = field(default_factory=list)
    accepted_parent_concepts: list[str] = field(default_factory=list)
    required_edges: list[EdgePattern] = field(default_factory=list)
    forbidden_edges: list[EdgePattern] = field(default_factory=list)
    temporal_policy: Any | None = None
    evidence_policy: Any | None = None
    resolver_policy: ResolverPolicy = field(default_factory=ResolverPolicy)
    support: list[Any] = field(default_factory=list)
    confidence: float = 0.5
