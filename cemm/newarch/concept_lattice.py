"""In-memory concept lattice seed.

This is the first concrete implementation behind the architecture's dynamic
concept-resolution seam. It is deliberately small and deterministic, but it is
not a hardcoded ontology: concepts, aliases, parent links, and ports are data
that can be updated through GraphPatch consolidation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..types.graph_patch import GraphPatch
from ..types.uol_graph import ConceptResolution, UOLAtom


@dataclass
class OperationalPortSpec:
    key: str
    accepted_atom_kinds: set[str] = field(default_factory=set)
    accepted_parent_concepts: set[str] = field(default_factory=set)
    required: bool = False
    confidence: float = 0.5
    support: list[dict[str, Any]] = field(default_factory=list)

    def accepts_kind(self, atom_kind: str) -> bool:
        return not self.accepted_atom_kinds or atom_kind in self.accepted_atom_kinds

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "accepted_atom_kinds": sorted(self.accepted_atom_kinds),
            "accepted_parent_concepts": sorted(self.accepted_parent_concepts),
            "required": self.required,
            "confidence": self.confidence,
            "support": [dict(item) for item in self.support],
        }


@dataclass
class ConceptRecord:
    key: str
    atom_kind: str = "entity"
    state: str = "candidate_atom"
    aliases: set[str] = field(default_factory=set)
    parents: set[str] = field(default_factory=set)
    ports: dict[str, OperationalPortSpec] = field(default_factory=dict)
    predicates: set[str] = field(default_factory=set)
    affordances: set[str] = field(default_factory=set)
    source_support: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5

    def __post_init__(self) -> None:
        self.key = self._clean_key(self.key)
        self.aliases.add(self.key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "atom_kind": self.atom_kind,
            "state": self.state,
            "aliases": sorted(self.aliases),
            "parents": sorted(self.parents),
            "ports": {key: port.to_dict() for key, port in self.ports.items()},
            "predicates": sorted(self.predicates),
            "affordances": sorted(self.affordances),
            "source_support": [dict(item) for item in self.source_support],
            "confidence": self.confidence,
        }

    @staticmethod
    def _clean_key(value: str) -> str:
        return "_".join(str(value or "unknown").strip().lower().split()) or "unknown"


class ConceptLattice:
    """A small mutable concept lattice with alias and parent traversal."""

    def __init__(self, concepts: Iterable[ConceptRecord] | None = None) -> None:
        self._concepts: dict[str, ConceptRecord] = {}
        self._aliases: dict[str, str] = {}
        self._seed_minimal_concepts()
        for concept in concepts or []:
            self.upsert(concept)

    def upsert(self, concept: ConceptRecord) -> ConceptRecord:
        existing = self._concepts.get(concept.key)
        if existing is None:
            self._concepts[concept.key] = concept
            existing = concept
        else:
            existing.confidence = max(existing.confidence, concept.confidence)
            existing.state = self._stronger_state(existing.state, concept.state)
            existing.aliases.update(concept.aliases)
            existing.parents.update(concept.parents)
            existing.predicates.update(concept.predicates)
            existing.affordances.update(concept.affordances)
            existing.source_support.extend(concept.source_support)
            for key, port in concept.ports.items():
                self.upsert_port(existing.key, port)
        for alias in existing.aliases:
            self._aliases[self._clean_key(alias)] = existing.key
        return existing

    def lookup(self, key_or_alias: str) -> ConceptRecord | None:
        key = self._aliases.get(self._clean_key(key_or_alias), self._clean_key(key_or_alias))
        return self._concepts.get(key)

    def resolve(self, atom: UOLAtom, _graph: Any = None) -> ConceptResolution:
        concept = self.lookup(atom.key) or self.lookup(atom.surface)
        if concept is not None:
            inherited = sorted(self.parents_of(concept.key))
            return ConceptResolution(
                atom_id=atom.id,
                concept_id=f"concept:{concept.key}",
                state="exact_alias" if self._clean_key(atom.key) in concept.aliases else concept.state,
                inherited_from=[f"concept:{parent}" for parent in inherited],
                confidence=max(atom.confidence, concept.confidence),
                evidence_refs=[],
                reason="concept_lattice_lookup",
            )
        candidate = ConceptRecord(
            key=atom.key,
            atom_kind=atom.kind,
            state="new_candidate",
            aliases={atom.surface} if atom.surface else set(),
            confidence=min(0.6, atom.confidence),
        )
        self.upsert(candidate)
        return ConceptResolution(
            atom_id=atom.id,
            concept_id=f"concept:{candidate.key}",
            state="new_candidate",
            confidence=candidate.confidence,
            reason="concept_lattice_candidate_created",
        )

    def parents_of(self, concept_key: str) -> set[str]:
        visited: set[str] = set()
        stack = list((self.lookup(concept_key) or ConceptRecord(concept_key)).parents)
        while stack:
            parent = self._clean_key(stack.pop())
            if parent in visited:
                continue
            visited.add(parent)
            parent_record = self.lookup(parent)
            if parent_record is not None:
                stack.extend(parent_record.parents)
        return visited

    def ports_for(self, concept_key: str) -> dict[str, OperationalPortSpec]:
        concept = self.lookup(concept_key)
        if concept is None:
            return {}
        ports: dict[str, OperationalPortSpec] = {}
        for parent in self.parents_of(concept.key):
            parent_record = self.lookup(parent)
            if parent_record is not None:
                ports.update(parent_record.ports)
        ports.update(concept.ports)
        return ports

    def upsert_port(self, concept_key: str, port: OperationalPortSpec) -> None:
        concept = self.lookup(concept_key)
        if concept is None:
            concept = self.upsert(ConceptRecord(key=concept_key))
        existing = concept.ports.get(port.key)
        if existing is None:
            concept.ports[port.key] = port
            return
        existing.accepted_atom_kinds.update(port.accepted_atom_kinds)
        existing.accepted_parent_concepts.update(port.accepted_parent_concepts)
        existing.required = existing.required or port.required
        existing.confidence = max(existing.confidence, port.confidence)
        existing.support.extend(port.support)

    def apply_patch(self, patch: GraphPatch) -> list[str]:
        applied: list[str] = []
        if patch.target != "concept_lattice":
            return applied
        for operation in patch.operations:
            if operation.operation == "upsert_concept_candidate":
                fields = operation.fields
                concept = ConceptRecord(
                    key=str(fields.get("key") or operation.target_id.replace("concept:", "")),
                    atom_kind=str(fields.get("atom_kind") or "entity"),
                    state=str(fields.get("state") or "candidate_atom"),
                    aliases={str(fields.get("surface"))} if fields.get("surface") else set(),
                    confidence=operation.confidence,
                )
                self.upsert(concept)
                applied.append(operation.target_id)
            elif operation.operation == "upsert_relation_candidate":
                fields = operation.fields
                source_key = str(fields.get("source_concept_key") or "")
                target_key = str(fields.get("target_concept_key") or "")
                relation = str(fields.get("relation") or "")
                if source_key and target_key and relation == "is_a":
                    source = self.upsert(ConceptRecord(key=source_key))
                    source.parents.add(self._clean_key(target_key))
                    applied.append(operation.target_id)
                elif source_key and relation:
                    source = self.upsert(ConceptRecord(key=source_key))
                    source.predicates.add(relation)
                    applied.append(operation.target_id)
            elif operation.operation == "observe_port_binding":
                fields = operation.fields
                owner = str(fields.get("owner_concept_id") or "").replace("concept:", "")
                port_key = str(fields.get("port_key") or "")
                if owner and port_key:
                    self.upsert_port(owner, OperationalPortSpec(
                        key=port_key,
                        confidence=operation.confidence,
                        support=[dict(fields)],
                    ))
                    applied.append(operation.target_id)
        return applied

    def snapshot(self) -> dict[str, Any]:
        return {key: concept.to_dict() for key, concept in sorted(self._concepts.items())}

    def _seed_minimal_concepts(self) -> None:
        self.upsert(ConceptRecord(
            key="leader",
            atom_kind="entity",
            state="operational_atom",
            ports={
                "holder": OperationalPortSpec("holder", accepted_atom_kinds={"entity", "self"}),
                "domain": OperationalPortSpec("domain", accepted_atom_kinds={"entity", "place"}),
            },
            predicates={"leads", "represents", "directs"},
            confidence=0.65,
        ))
        self.upsert(ConceptRecord(
            key="president",
            atom_kind="entity",
            state="operational_atom",
            parents={"leader"},
            ports={
                "time_scope": OperationalPortSpec("time_scope", accepted_atom_kinds={"time"}),
            },
            confidence=0.62,
        ))
        self.upsert(ConceptRecord(
            key="cold",
            atom_kind="state",
            state="operational_atom",
            ports={
                "holder": OperationalPortSpec("holder", accepted_atom_kinds={"entity", "self", "place"}),
                "intensity": OperationalPortSpec("intensity", accepted_atom_kinds={"quantity", "quality"}),
                "place": OperationalPortSpec("place", accepted_atom_kinds={"place"}),
                "time": OperationalPortSpec("time", accepted_atom_kinds={"time"}),
            },
            confidence=0.6,
        ))

    @staticmethod
    def _clean_key(value: str) -> str:
        return "_".join(str(value or "unknown").strip().lower().split()) or "unknown"

    @staticmethod
    def _stronger_state(current: str, new: str) -> str:
        order = {
            "unknown_surface": 0,
            "candidate_atom": 1,
            "new_candidate": 1,
            "typed_candidate": 2,
            "operational_atom": 3,
            "consolidated_atom": 4,
        }
        return new if order.get(new, 0) > order.get(current, 0) else current
