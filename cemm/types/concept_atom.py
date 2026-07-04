from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ConceptState(str, Enum):
    unknown_surface = "unknown_surface"
    candidate_atom = "candidate_atom"
    typed_candidate = "typed_candidate"
    operational_atom = "operational_atom"
    consolidated_atom = "consolidated_atom"
    contested_atom = "contested_atom"
    stale_atom = "stale_atom"


@dataclass
class SemanticFingerprint:
    key_tokens: set[str] = field(default_factory=set)
    surface_tokens: set[str] = field(default_factory=set)
    role_tokens: set[str] = field(default_factory=set)

    def jaccard(self, other: SemanticFingerprint) -> float:
        union = self.key_tokens | other.key_tokens | self.surface_tokens | other.surface_tokens | self.role_tokens | other.role_tokens
        if not union:
            return 0.0
        intersection = self.key_tokens & other.key_tokens | self.surface_tokens & other.surface_tokens | self.role_tokens & other.role_tokens
        return len(intersection) / len(union)


@dataclass
class Counterexample:
    pattern: dict[str, Any]
    count: int = 1
    notes: str = ""


@dataclass
class SourceSupport:
    source_id: str
    source_type: str
    confidence: float
    observed_at: float = 0.0


@dataclass
class TemporalPolicy:
    valid_from: float | None = None
    valid_until: float | None = None
    max_age_hours: float = 0.0
    requires_fresh: bool = False


@dataclass
class EvidencePolicy:
    min_evidence: int = 1
    require_source: bool = True
    allow_self_report: bool = True


@dataclass
class PermissionPolicy:
    default_scope: str = "public"
    required_scope: str = "public"


@dataclass
class PredicateSignature:
    predicate_key: str
    role: str = "unknown"


@dataclass
class ExemplarRef:
    graph_id: str
    surface: str
    confidence: float


@dataclass
class ConceptAtom:
    concept_id: str
    key: str
    atom_kind: str
    state: ConceptState = ConceptState.unknown_surface
    aliases: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    ports: list[Any] = field(default_factory=list)
    acceptable_predicates: list[PredicateSignature] = field(default_factory=list)
    causal_affordances: list[str] = field(default_factory=list)
    temporal_policy: TemporalPolicy = field(default_factory=TemporalPolicy)
    evidence_policy: EvidencePolicy = field(default_factory=EvidencePolicy)
    permission_policy: PermissionPolicy = field(default_factory=PermissionPolicy)
    source_support: list[SourceSupport] = field(default_factory=list)
    counterexamples: list[Counterexample] = field(default_factory=list)
    exemplars: list[ExemplarRef] = field(default_factory=list)
    fingerprint: SemanticFingerprint | None = None
    confidence: float = 0.5
    stability: float = 0.0
