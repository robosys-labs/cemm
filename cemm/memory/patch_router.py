"""PatchRouter — dispatches validated GraphPatches to the correct lattice.

Part of the PatchPipeline: every durable write flows through
PatchValidator → PatchRouter → Lattice → Flush.

No component writes to durable storage directly. All writes go through
this pipeline so the PatchValidator is the single write gate.
"""

from __future__ import annotations

from typing import Any

from ..types.graph_patch import GraphPatch


class PatchRouter:
    """Routes validated GraphPatches to the correct lattice for consolidation.
    
    Each lattice's apply_patch() is pure in-memory. The flush_all() call
    at end-of-turn writes all dirty state to persistent store atomically.
    """

    def __init__(
        self,
        concept_lattice: Any,
        construction_lattice: Any = None,
        episodic_store: Any = None,
    ) -> None:
        self._concept_lattice = concept_lattice
        self._construction_lattice = construction_lattice
        self._episodic_store = episodic_store

    def route(self, patch: GraphPatch, source_graph: Any = None) -> list[str]:
        """Apply a validated patch to the correct lattice. Pure in-memory, no side effects."""
        if patch.target == "concept_lattice":
            return self._concept_lattice.apply_patch(patch)
        if patch.target == "construction_lattice" and self._construction_lattice is not None:
            return self._construction_lattice.apply_patch(patch)
        if patch.target == "episodic_trace" and self._episodic_store is not None and source_graph is not None:
            trace = self._episodic_store.retain_graph(source_graph, reason=patch.reason, score=patch.confidence)
            return [trace.trace_id]
        return []

    def route_batch(self, patches: list[GraphPatch], source_graph: Any = None) -> list[str]:
        """Apply multiple validated patches. Merges compatible patches first."""
        applied: list[str] = []
        from ..learning.concept_consolidator import ConceptConsolidator
        merged = ConceptConsolidator._merge_compatible_patches(patches)
        for patch in merged:
            applied.extend(self.route(patch, source_graph))
        return applied

    def flush_all(self) -> None:
        """Flush all dirty lattice state to persistent store. Call at end of turn."""
        if hasattr(self._concept_lattice, "flush_to_store"):
            self._concept_lattice.flush_to_store()
        if self._construction_lattice is not None and hasattr(self._construction_lattice, "flush_to_store"):
            self._construction_lattice.flush_to_store()
