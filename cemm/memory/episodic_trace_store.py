"""Sparse high-value graph exemplar store for seed consolidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types.uol_graph import UOLGraph


@dataclass
class EpisodicTrace:
    trace_id: str
    source_graph_id: str
    raw_text: str = ""
    reason: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "source_graph_id": self.source_graph_id,
            "raw_text": self.raw_text,
            "reason": self.reason,
            "score": self.score,
            "metadata": dict(self.metadata),
        }


class EpisodicTraceStore:
    """In-memory sparse trace store.

    This is deliberately not a permanent graph database. It keeps only selected
    exemplars so consolidation can inspect high-value traces without violating
    the graph-hoarding rule.
    """

    def __init__(self) -> None:
        self._traces: dict[str, EpisodicTrace] = {}

    def retain_graph(self, graph: UOLGraph, *, reason: str, score: float) -> EpisodicTrace:
        trace_id = f"trace:{graph.id}"
        trace = EpisodicTrace(
            trace_id=trace_id,
            source_graph_id=graph.id,
            raw_text=graph.raw_text,
            reason=reason,
            score=score,
            metadata={
                "atom_count": len(graph.atoms),
                "edge_count": len(graph.edges),
                "candidate_set_count": len(graph.candidate_sets),
            },
        )
        self._traces[trace_id] = trace
        return trace

    def snapshot(self) -> dict[str, Any]:
        return {trace_id: trace.to_dict() for trace_id, trace in sorted(self._traces.items())}
