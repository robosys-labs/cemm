"""ObligationGraph — typed obligation graph for one turn.
Preserves compatible query, write, acknowledgment, state, action, and learning nodes.
No single-primary arbitration discards compatible meanings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ObligationNodeKind(str, Enum):
    QUERY = "query"
    WRITE = "write"
    STATE = "state"
    REACTION = "reaction"
    SAFETY = "safety"
    ACTION = "action"
    LEARNING = "learning"
    LEARNING_QUESTION = "learning_question"
    RESPONSE = "response"
    ACKNOWLEDGMENT = "acknowledgment"
    CLARIFICATION = "clarification"
    ABSTRACTION = "abstention"


@dataclass(frozen=True, slots=True)
class ObligationNode:
    """A node in the obligation graph representing one obligation."""
    node_id: str
    kind: ObligationNodeKind
    frame_id: str = ""
    branch_id: str = ""
    group_id: str = ""
    gap_ids: tuple[str, ...] = ()
    
    # Dependencies
    depends_on: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    resumes: tuple[str, ...] = ()
    
    # Priority and budget
    priority: int = 0
    budget_cost: float = 1.0
    
    # Status
    is_required: bool = True
    is_executed: bool = False
    
    def can_execute(self, executed_ids: set[str]) -> bool:
        """Check if all dependencies are met."""
        for dep in self.depends_on:
            if dep not in executed_ids:
                return False
        return not self.blocked_by


@dataclass(frozen=True, slots=True)
class ObligationEdge:
    """An edge in the obligation graph."""
    source_id: str
    target_id: str
    edge_type: str = "depends_on"
    # depends_on, blocks, resumes, compatible_with, preempts


class ObligationGraph:
    """A directed graph of obligations for one turn.
    
    Supports multiple compatible obligations.
    Only safety, permission denial, hard contradiction, or required
    clarification globally preempt ordinary compatible obligations.
    """
    
    def __init__(self) -> None:
        self._nodes: dict[str, ObligationNode] = {}
        self._edges: list[ObligationEdge] = []
    
    def add_node(self, node: ObligationNode) -> None:
        self._nodes[node.node_id] = node
    
    def add_edge(self, edge: ObligationEdge) -> None:
        self._edges.append(edge)
    
    def get_node(self, node_id: str) -> ObligationNode | None:
        return self._nodes.get(node_id)
    
    def all_nodes(self) -> list[ObligationNode]:
        return list(self._nodes.values())
    
    def nodes_by_kind(self, kind: ObligationNodeKind) -> list[ObligationNode]:
        return [n for n in self._nodes.values() if n.kind == kind]
    
    def nodes_for_group(self, group_id: str) -> list[ObligationNode]:
        return [n for n in self._nodes.values() if n.group_id == group_id]
    
    def execution_order(self) -> list[str]:
        """Topological sort respecting dependencies."""
        executed: set[str] = set()
        ordered: list[str] = []
        remaining = set(self._nodes.keys())
        
        while remaining:
            ready = [
                nid for nid in remaining
                if self._nodes[nid].can_execute(executed)
            ]
            if not ready:
                break
            for nid in ready:
                ordered.append(nid)
                executed.add(nid)
                remaining.discard(nid)
        
        return ordered
    
    def has_learning_question(self) -> bool:
        return any(
            n.kind == ObligationNodeKind.LEARNING_QUESTION
            for n in self._nodes.values()
        )
    
    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
