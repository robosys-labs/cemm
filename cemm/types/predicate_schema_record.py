"""PredicateSchemaRecord — first-class predicate schema for the semantic CPU.

Predicate schemas are the instruction definitions of the semantic CPU.
They define argument structure, inverse relations, freshness policy,
and answer projection. Learned predicates start as candidates and are
promoted through validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PredicateSchemaRecord:
    schema_id: str
    predicate_key: str
    relation_family: str = "definition"
    argument_roles: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    inverse_predicates: list[str] = field(default_factory=list)
    inheritance_behavior: str = "none"
    answer_projection: str = "subject"
    freshness_policy: str = "any"
    evidence_policy: str = "speaker_asserted"
    confidence: float = 0.5
    support_count: int = 0
