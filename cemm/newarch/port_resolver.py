"""Lattice-backed operational port resolver."""

from __future__ import annotations

from typing import Any

from ..memory.concept_lattice import ConceptLattice, OperationalPortSpec
from ..types.uol_graph import PortBinding, UOLAtom, UOLGraph


class LatticePortResolver:
    """Resolve ports from concept-lattice specs against a working graph."""

    def __init__(self, concept_lattice: ConceptLattice) -> None:
        self._concept_lattice = concept_lattice

    def resolve_graph(self, graph: UOLGraph) -> list[PortBinding]:
        bindings: list[PortBinding] = []
        for owner in graph.atoms.values():
            concept_key = self._concept_key(owner)
            ports = self._concept_lattice.ports_for(concept_key)
            if not ports:
                continue
            group_atoms = graph.group_atoms(owner.group_id) if owner.group_id else list(graph.atoms.values())
            role_edges = graph.outgoing(owner.id, "has_role")
            for port in ports.values():
                binding = self._resolve_port(graph, owner, port, group_atoms, role_edges)
                if binding is not None:
                    bindings.append(binding)
        return bindings

    def _resolve_port(
        self,
        graph: UOLGraph,
        owner: UOLAtom,
        port: OperationalPortSpec,
        candidates: list[UOLAtom],
        role_edges: list[Any],
    ) -> PortBinding | None:
        scored: list[tuple[float, UOLAtom, dict[str, float], str]] = []
        for candidate in candidates:
            if candidate.id == owner.id:
                continue
            role_score, edge_id = self._role_support(candidate.id, port.key, role_edges)
            kind_score = 0.25 if port.accepts_kind(candidate.kind) else -0.2
            parent_score = self._parent_support(candidate.key, port)
            salience_score = 0.1 if candidate.group_id == owner.group_id else 0.0
            confidence_score = min(owner.confidence, candidate.confidence) * 0.25
            score_parts = {
                "role_support": role_score,
                "kind_match": kind_score,
                "parent_match": parent_score,
                "group_salience": salience_score,
                "confidence": confidence_score,
            }
            scored.append((sum(score_parts.values()), candidate, score_parts, edge_id))
        if not scored:
            return PortBinding(
                owner_atom_id=owner.id,
                owner_concept_id=f"concept:{self._concept_key(owner)}",
                port_id=f"port:{self._concept_key(owner)}:{port.key}",
                port_key=port.key,
                required=port.required,
                status="placeholder",
                score=0.0,
            )
        score, filler, score_parts, edge_id = max(scored, key=lambda item: item[0])
        return PortBinding(
            owner_atom_id=owner.id,
            owner_concept_id=f"concept:{self._concept_key(owner)}",
            port_id=f"port:{self._concept_key(owner)}:{port.key}",
            port_key=port.key,
            filler_atom_id=filler.id if score >= 0.35 else "",
            required=port.required,
            status="bound" if score >= 0.35 else "ambiguous",
            score=max(0.0, min(1.0, score)),
            score_parts=score_parts,
            source_edge_id=edge_id,
        )

    def _role_support(self, candidate_id: str, port_key: str, role_edges: list[Any]) -> tuple[float, str]:
        for edge in role_edges:
            if edge.target_id != candidate_id:
                continue
            role = str(edge.features.get("role") or edge.features.get("role_value") or "")
            if role == port_key:
                return 0.35, edge.id
            if role:
                return 0.15, edge.id
        return 0.0, ""

    def _parent_support(self, candidate_key: str, port: OperationalPortSpec) -> float:
        if not port.accepted_parent_concepts:
            return 0.0
        parents = self._concept_lattice.parents_of(candidate_key)
        if parents & port.accepted_parent_concepts:
            return 0.2
        return 0.0

    @staticmethod
    def _concept_key(atom: UOLAtom) -> str:
        return atom.key.replace("concept:", "")
