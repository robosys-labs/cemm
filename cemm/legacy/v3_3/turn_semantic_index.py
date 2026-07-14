"""TurnSemanticIndex — build-once indexes for one turn's UOL graph.
Eliminates repeated broad graph scans in core compilers.
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict

from ...types.uol_graph import UOLGraph
from ...types.uol_atom import UOLAtom, UOLEdge


class TurnSemanticIndex:
    """Indexes for one turn's UOL graph, built once and reused.
    
    All indexes are rebuilt fresh each turn — no cross-turn accumulation.
    """
    
    def __init__(self, graph: UOLGraph | None = None) -> None:
        self._graph = None
        self._atoms_by_kind: dict[str, list[UOLAtom]] = {}
        self._edges_by_type: dict[str, list[UOLEdge]] = {}
        self._edges_by_group: dict[str, list[UOLEdge]] = {}
        self._atoms_by_group: dict[str, list[UOLAtom]] = {}
        self._entities: dict[str, UOLAtom] = {}
        self._predicates: dict[str, UOLAtom] = {}
        
        if graph is not None:
            self.build(graph)
    
    def build(self, graph: UOLGraph) -> None:
        self._graph = graph
        self._atoms_by_kind = defaultdict(list)
        self._edges_by_type = defaultdict(list)
        self._edges_by_group = defaultdict(list)
        self._atoms_by_group = defaultdict(list)
        self._entities = {}
        self._predicates = {}
        
        for atom_id, atom in (graph.atoms or {}).items():
            self._atoms_by_kind[atom.kind].append(atom)
            group_id = getattr(atom, 'group_id', '') or ''
            if group_id:
                self._atoms_by_group[group_id].append(atom)
            if atom.kind == 'entity':
                self._entities[atom_id] = atom
            if atom.kind in ('action', 'process', 'predicate'):
                self._predicates[atom_id] = atom
        
        for edge in (graph.edges or []):
            self._edges_by_type[edge.edge_type].append(edge)
            group_id = getattr(edge, 'group_id', '') or ''
            if group_id:
                self._edges_by_group[group_id].append(edge)
    
    @property
    def graph(self) -> UOLGraph | None:
        return self._graph
    
    def atoms_by_kind(self, kind: str) -> list[UOLAtom]:
        return list(self._atoms_by_kind.get(kind, []))
    
    def edges_by_type(self, edge_type: str) -> list[UOLEdge]:
        return list(self._edges_by_type.get(edge_type, []))
    
    def edges_by_group(self, group_id: str) -> list[UOLEdge]:
        return list(self._edges_by_group.get(group_id, []))
    
    def atoms_by_group(self, group_id: str) -> list[UOLAtom]:
        return list(self._atoms_by_group.get(group_id, []))
    
    def entities(self) -> dict[str, UOLAtom]:
        return dict(self._entities)
    
    def predicates(self) -> dict[str, UOLAtom]:
        return dict(self._predicates)
    
    def has_kind(self, kind: str) -> bool:
        return kind in self._atoms_by_kind
