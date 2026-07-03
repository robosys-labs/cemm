"""GraphPatch extraction boundary.

The graph builder may emit seed patch candidates, but learning code should use
this boundary so future extractors can replace builder-side heuristics without
changing planner or consolidator contracts.
"""

from __future__ import annotations

from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.uol_graph import UOLGraph


class GraphPatchExtractor:
    def extract(self, graph: UOLGraph) -> list[GraphPatch]:
        patches = list(graph.patch_candidates)
        if not patches and self._should_retain_exemplar(graph):
            patches.append(GraphPatch(
                source_graph_id=graph.id,
                target="episodic_trace",
                operations=[
                    PatchOperation(
                        operation="retain_exemplar",
                        target_id=f"trace:{graph.id}",
                        fields={"raw_text": graph.raw_text},
                        confidence=0.5,
                        reason="interesting_graph_without_patch",
                    )
                ],
                confidence=0.5,
                reason="retain_sparse_exemplar",
            ))
        return patches

    @staticmethod
    def _should_retain_exemplar(graph: UOLGraph) -> bool:
        return bool(graph.candidate_sets or graph.affordance_predictions or graph.construction_matches)
