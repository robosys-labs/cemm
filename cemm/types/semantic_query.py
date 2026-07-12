"""SemanticQuery — structured query over relation frames.

Built from an ObligationFrame + RelationFrames, a SemanticQuery
specifies what to look up and how: relation key, subject/object
constraints, inheritance/inverse expansion flags, and evidence
policy. This replaces keyword-based claim retrieval with
algebraic graph queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QueryConstraint:
    constraint_id: str = ""
    role: str = ""
    concept_id: str = ""
    entity_id: str = ""
    surface: str = ""
    projection_policy: str = ""
    confidence: float = 0.5


@dataclass
class SemanticQuery:
    query_id: str = ""
    source_obligation_id: str = ""
    query_kind: str = "lookup"
    relation_key: str = ""
    subject_constraint: QueryConstraint = field(default_factory=QueryConstraint)
    object_constraint: QueryConstraint = field(default_factory=QueryConstraint)
    allow_inheritance: bool = True
    allow_inverse: bool = True
    allow_composition: bool = False
    evidence_policy: str = "speaker_asserted"
    freshness_policy: str = "any"
    required_slots: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    confidence: float = 0.5
