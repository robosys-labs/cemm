"""ScopeGraphBuilder — builds scope graph for interpretation branches.
Resolves quotation, negation, condition, desire, command, question, and completion.
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict

from ..types.uol_graph import UOLGraph


class ScopeGraphBuilder:
    """Builds and resolves scope relationships for interpretation branches."""
    
    def build(self, graph: UOLGraph) -> dict[str, dict[str, Any]]:
        scopes: dict[str, dict[str, Any]] = {}
        
        for atom_id, atom in (graph.atoms or {}).items():
            group_id = getattr(atom, "group_id", "") or ""
            modality = getattr(atom, "modality", "observed")
            polarity = getattr(atom, "polarity", "affirmed")
            
            scopes[atom_id] = {
                "group_id": group_id,
                "modality": modality,
                "polarity": polarity,
                "is_negated": polarity == "negated",
                "is_quoted": modality in ("reported", "quoted"),
                "is_desired": modality in ("desired", "proposed"),
                "is_commanded": modality == "commanded",
                "is_questioned": modality == "questioned",
                "is_hypothetical": modality == "hypothetical",
                "is_completed": modality == "completed",
            }
        
        for edge in (graph.edges or []):
            if edge.edge_type == "scope":
                source_scope = scopes.get(edge.source_id, {})
                target_scope = scopes.get(edge.target_id, {})
                if source_scope and target_scope:
                    target_scope["parent_scope"] = edge.source_id
        
        return scopes
