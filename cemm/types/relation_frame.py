"""RelationFrame — operational relation structure over UOL atoms/edges.

A RelationFrame turns a graph edge or relation atom into an executable
relation with typed arguments, family classification, inverse hints,
and inheritance lineage. This is the bridge between "I saw a relation"
and "I can reason with it."
"""

from __future__ import annotations

from dataclasses import dataclass, field


RELATION_FAMILIES = frozenset({
    "taxonomy",
    "role",
    "property",
    "causal",
    "temporal",
    "affordance",
    "identity",
    "definition",
    "membership",
})


@dataclass
class RelationArgument:
    role: str
    atom_id: str = ""
    concept_id: str = ""
    entity_id: str = ""
    surface: str = ""
    confidence: float = 0.5


@dataclass
class RelationFrame:
    relation_id: str
    relation_key: str
    relation_family: str
    subject: RelationArgument = field(default_factory=RelationArgument)
    object: RelationArgument = field(default_factory=RelationArgument)
    qualifiers: dict[str, RelationArgument] = field(default_factory=dict)
    source_edge_ids: list[str] = field(default_factory=list)
    source_atom_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    inverse_relation_keys: list[str] = field(default_factory=list)
    inherited_from: list[str] = field(default_factory=list)
    confidence: float = 0.5
