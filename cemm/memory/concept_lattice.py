"""In-memory concept lattice with optional SQLite persistent backing.

This is the first concrete implementation behind the architecture's dynamic
concept-resolution seam. It is deliberately small and deterministic, but it is
not a hardcoded ontology: concepts, aliases, parent links, and ports are data
that can be updated through GraphPatch consolidation.

When a persistent_store is provided, concept writes are dual-written to SQLite
and the lattice is loaded from the store on startup.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from ..types.concept_atom import (
    ConceptAtom,
    ConceptState,
    Counterexample,
    ExemplarRef,
    PredicateSignature,
    SemanticFingerprint,
    SourceSupport,
    TemporalPolicy,
    EvidencePolicy,
    PermissionPolicy,
)
from ..types.graph_patch import GraphPatch
from ..types.operational_port import OperationalPort, EdgePattern, ResolverPolicy
from ..types.uol_graph import ConceptResolution, UOLAtom


class ConceptLattice:
    """A small mutable concept lattice with alias and parent traversal.

    When persistent_store is provided, dual-writes all concept updates to
    SQLite and loads persisted concepts on startup.
    """

    def __init__(
        self,
        concepts: Iterable[ConceptAtom] | None = None,
        *,
        persistent_store: Any = None,
    ) -> None:
        self._concepts: dict[str, ConceptAtom] = {}
        self._aliases: dict[str, str] = {}
        self._persistent_store = persistent_store
        self._dirty_ids: set[str] = set()
        if persistent_store:
            self.load_from_store()
        self._seed_minimal_concepts()
        for concept in concepts or []:
            self.upsert(concept)

    def load_from_store(self) -> None:
        """Load concept atoms from PersistentLatticeStore into in-memory _concepts."""
        if self._persistent_store is None:
            return
        for concept_id, data in self._persistent_store.load_all().items():
            key = data.get("key", concept_id.split(":", 1)[-1] if ":" in concept_id else concept_id)
            if key in self._concepts:
                continue
            aliases_raw = data.get("aliases_json", [])
            if isinstance(aliases_raw, str):
                aliases_raw = json.loads(aliases_raw)
            parents_raw = data.get("parents_json", [])
            if isinstance(parents_raw, str):
                parents_raw = json.loads(parents_raw)
            state_str = str(data.get("state", "candidate_atom"))
            try:
                state = ConceptState(state_str)
            except ValueError:
                state = ConceptState.candidate_atom
            record = ConceptAtom(
                concept_id=concept_id,
                key=key,
                atom_kind=str(data.get("atom_kind", "entity")),
                state=state,
                aliases=list(aliases_raw) if isinstance(aliases_raw, list) else [str(aliases_raw)],
                parents=list(parents_raw) if isinstance(parents_raw, list) else [str(parents_raw)],
                confidence=float(data.get("confidence", 0.5)),
            )
            self.upsert(record)

    def upsert(self, concept: ConceptAtom) -> ConceptAtom:
        existing = self._concepts.get(concept.key)
        if existing is None:
            self._concepts[concept.key] = concept
            existing = concept
        else:
            existing.confidence = max(existing.confidence, concept.confidence)
            existing.state = self._stronger_state(existing.state, concept.state)
            existing_aliases = set(existing.aliases)
            existing_aliases.update(concept.aliases)
            existing.aliases = sorted(existing_aliases)
            existing_parents = set(existing.parents)
            existing_parents.update(concept.parents)
            existing.parents = sorted(existing_parents)
            existing.source_support.extend(concept.source_support)
            existing.counterexamples.extend(concept.counterexamples)
            existing.exemplars.extend(concept.exemplars)
            for port in concept.ports:
                self.upsert_port(existing.key, port)
            if concept.fingerprint is not None:
                existing.fingerprint = concept.fingerprint
        all_aliases = set(existing.aliases)
        all_aliases.add(existing.key)
        for alias in all_aliases:
            self._aliases[self._clean_key(alias)] = existing.key
        return existing

    def lookup(self, key_or_alias: str) -> ConceptAtom | None:
        key = self._aliases.get(self._clean_key(key_or_alias), self._clean_key(key_or_alias))
        return self._concepts.get(key)

    def resolve(self, atom: UOLAtom, _graph: Any = None) -> ConceptResolution:
        concept = self.lookup(atom.key) or self.lookup(atom.surface)
        if concept is not None:
            inherited = sorted(self.parents_of(concept.key))
            aliases_set = set(concept.aliases)
            aliases_set.add(concept.key)
            state_str = "exact_alias" if self._clean_key(atom.key) in aliases_set else concept.state.value
            return ConceptResolution(
                atom_id=atom.id,
                concept_id=f"concept:{concept.key}",
                state=state_str,
                inherited_from=[f"concept:{parent}" for parent in inherited],
                confidence=max(atom.confidence, concept.confidence),
                evidence_refs=[],
                reason="concept_lattice_lookup",
            )
        candidate = ConceptAtom(
            concept_id=f"concept:{atom.key}",
            key=atom.key,
            atom_kind=atom.kind,
            state=ConceptState.candidate_atom,
            aliases=[atom.surface] if atom.surface else [],
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
        rec = self.lookup(concept_key)
        if rec is None:
            return visited
        stack = list(rec.parents)
        while stack:
            parent = self._clean_key(stack.pop())
            if parent in visited:
                continue
            visited.add(parent)
            parent_record = self.lookup(parent)
            if parent_record is not None:
                stack.extend(parent_record.parents)
        return visited

    def ports_for(self, concept_key: str) -> list[OperationalPort]:
        concept = self.lookup(concept_key)
        if concept is None:
            return []
        port_map: dict[str, OperationalPort] = {}
        for parent in self.parents_of(concept.key):
            parent_record = self.lookup(parent)
            if parent_record is not None:
                for p in parent_record.ports:
                    if p.key not in port_map:
                        port_map[p.key] = p
        for p in concept.ports:
            port_map[p.key] = p
        return list(port_map.values())

    def upsert_port(self, concept_key: str, port: OperationalPort) -> None:
        concept = self.lookup(concept_key)
        if concept is None:
            concept = self.upsert(ConceptAtom(
                concept_id=f"concept:{concept_key}",
                key=concept_key,
                atom_kind="entity",
            ))
        existing_port = None
        existing_idx = -1
        for i, p in enumerate(concept.ports):
            if p.key == port.key:
                existing_port = p
                existing_idx = i
                break
        if existing_port is None:
            concept.ports.append(port)
            return
        accepted_kinds = list({*existing_port.accepted_atom_kinds, *port.accepted_atom_kinds})
        accepted_parents = list({*existing_port.accepted_parent_concepts, *port.accepted_parent_concepts})
        merged = OperationalPort(
            port_id=existing_port.port_id or port.port_id,
            owner_concept_id=existing_port.owner_concept_id or port.owner_concept_id,
            key=port.key,
            required=existing_port.required or port.required,
            accepted_atom_kinds=accepted_kinds,
            accepted_parent_concepts=accepted_parents,
            resolver_policy=port.resolver_policy,
            confidence=max(existing_port.confidence, port.confidence),
            support=existing_port.support + port.support,
        )
        concept.ports[existing_idx] = merged

    def apply_patch(self, patch: GraphPatch) -> list[str]:
        applied: list[str] = []
        if patch.target != "concept_lattice":
            return applied
        for operation in patch.operations:
            if operation.operation == "upsert_concept_candidate":
                fields = operation.fields
                key = str(fields.get("key") or operation.target_id.replace("concept:", ""))
                state_str = str(fields.get("state") or "candidate_atom")
                try:
                    state = ConceptState(state_str)
                except ValueError:
                    state = ConceptState.candidate_atom
                concept = ConceptAtom(
                    concept_id=operation.target_id,
                    key=key,
                    atom_kind=str(fields.get("atom_kind") or "entity"),
                    state=state,
                    aliases=[str(fields.get("surface"))] if fields.get("surface") else [],
                    confidence=operation.confidence,
                )
                self.upsert(concept)
                applied.append(operation.target_id)
                self._dirty_ids.add(operation.target_id)
            elif operation.operation == "upsert_relation_candidate":
                fields = operation.fields
                source_key = str(fields.get("source_concept_key") or "")
                target_key = str(fields.get("target_concept_key") or "")
                relation = str(fields.get("relation") or "")
                if source_key and target_key and relation == "is_a":
                    source_parents = set()
                    existing_source = self.lookup(source_key)
                    if existing_source is not None:
                        source_parents = set(existing_source.parents)
                    source_parents.add(self._clean_key(target_key))
                    source = self.upsert(ConceptAtom(
                        concept_id=f"concept:{source_key}",
                        key=source_key,
                        atom_kind="entity",
                        parents=sorted(source_parents),
                    ))
                    applied.append(operation.target_id)
                    self._dirty_ids.add(f"concept:{source_key}")
                elif source_key and relation:
                    source = self.upsert(ConceptAtom(
                        concept_id=f"concept:{source_key}",
                        key=source_key,
                        atom_kind="entity",
                    ))
                    if target_key:
                        self.upsert(ConceptAtom(
                            concept_id=f"concept:{target_key}",
                            key=target_key,
                            atom_kind="entity",
                        ))
                        self._dirty_ids.add(f"concept:{target_key}")
                    existing_preds = set(
                        (p.predicate_key, p.role) for p in source.acceptable_predicates
                    )
                    if (relation, "subject") not in existing_preds:
                        source.acceptable_predicates.append(PredicateSignature(
                            predicate_key=relation,
                            role="subject",
                        ))
                    applied.append(operation.target_id)
                    self._dirty_ids.add(f"concept:{source_key}")
            elif operation.operation == "observe_port_binding":
                fields = operation.fields
                owner = str(fields.get("owner_concept_id") or "").replace("concept:", "")
                port_key = str(fields.get("port_key") or "")
                if owner and port_key:
                    self.upsert_port(owner, OperationalPort(
                        port_id=f"port:{owner}:{port_key}",
                        owner_concept_id=f"concept:{owner}",
                        key=port_key,
                        confidence=operation.confidence,
                        support=[dict(fields)],
                    ))
                    applied.append(operation.target_id)
                    self._dirty_ids.add(f"concept:{owner}")
            elif operation.operation == "custom":
                applied.append(operation.target_id)
                self._dirty_ids.add(operation.target_id)
        return applied

    def flush_to_store(self) -> None:
        """Write all dirty concepts to persistent store. Called once per turn by PatchRouter."""
        if self._persistent_store is None:
            self._dirty_ids.clear()
            return
        for dirty_id in list(self._dirty_ids):
            concept = self.lookup(dirty_id.replace("concept:", ""))
            if concept is None:
                continue
            data = {
                "key": concept.key,
                "atom_kind": concept.atom_kind,
                "state": concept.state.value if hasattr(concept.state, "value") else str(concept.state),
                "aliases_json": json.dumps(sorted(concept.aliases)),
                "parents_json": json.dumps(sorted(concept.parents)),
                "ports_json": json.dumps({
                    p.key: {
                        "port_id": p.port_id,
                        "accepted_atom_kinds": sorted(p.accepted_atom_kinds),
                        "accepted_parent_concepts": sorted(p.accepted_parent_concepts),
                        "required": p.required,
                        "confidence": p.confidence,
                        "support": [dict(item) if hasattr(item, "items") else item for item in p.support],
                    }
                    for p in concept.ports
                }),
                "confidence": concept.confidence,
                "stability": getattr(concept, "stability", 0.0),
            }
            self._persistent_store.upsert_concept(dirty_id, data)
        self._dirty_ids.clear()

    def has_dirty(self) -> bool:
        return bool(self._dirty_ids)

    def snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, concept in sorted(self._concepts.items()):
            data: dict[str, Any] = {
                "key": concept.key,
                "atom_kind": concept.atom_kind,
                "state": concept.state.value,
                "aliases": sorted(concept.aliases),
                "parents": sorted(concept.parents),
                "ports": [{"key": p.key, "accepted_atom_kinds": sorted(p.accepted_atom_kinds),
                           "accepted_parent_concepts": sorted(p.accepted_parent_concepts),
                           "required": p.required, "confidence": p.confidence,
                           "support": [dict(item) if hasattr(item, 'items') else item for item in p.support]}
                          for p in concept.ports],
                "confidence": concept.confidence,
            }
            result[key] = data
        return result

    def _seed_minimal_concepts(self) -> None:
        self.upsert(ConceptAtom(
            concept_id="concept:leader",
            key="leader",
            atom_kind="entity",
            state=ConceptState.operational_atom,
            ports=[
                OperationalPort("port:leader:holder", "concept:leader", "holder",
                                accepted_atom_kinds=["entity", "self"]),
                OperationalPort("port:leader:domain", "concept:leader", "domain",
                                accepted_atom_kinds=["entity", "place"]),
            ],
            confidence=0.65,
        ))
        self.upsert(ConceptAtom(
            concept_id="concept:president",
            key="president",
            atom_kind="entity",
            state=ConceptState.operational_atom,
            parents=["leader"],
            ports=[
                OperationalPort("port:president:time_scope", "concept:president", "time_scope",
                                accepted_atom_kinds=["time"]),
            ],
            confidence=0.62,
        ))
        self.upsert(ConceptAtom(
            concept_id="concept:cold",
            key="cold",
            atom_kind="state",
            state=ConceptState.operational_atom,
            ports=[
                OperationalPort("port:cold:holder", "concept:cold", "holder",
                                accepted_atom_kinds=["entity", "self", "place"]),
                OperationalPort("port:cold:intensity", "concept:cold", "intensity",
                                accepted_atom_kinds=["quantity", "quality"]),
                OperationalPort("port:cold:place", "concept:cold", "place",
                                accepted_atom_kinds=["place"]),
                OperationalPort("port:cold:time", "concept:cold", "time",
                                accepted_atom_kinds=["time"]),
            ],
            confidence=0.6,
        ))

    @staticmethod
    def _clean_key(value: str) -> str:
        return "_".join(str(value or "unknown").strip().lower().split()) or "unknown"

    @staticmethod
    def _stronger_state(current: ConceptState, new: ConceptState) -> ConceptState:
        order = {
            ConceptState.unknown_surface: 0,
            ConceptState.candidate_atom: 1,
            ConceptState.typed_candidate: 2,
            ConceptState.operational_atom: 3,
            ConceptState.consolidated_atom: 4,
            ConceptState.contested_atom: 5,
            ConceptState.stale_atom: 6,
        }
        return new if order.get(new, 0) > order.get(current, 0) else current
