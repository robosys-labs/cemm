"""ObligationGraphBuilder — builds an obligation graph from selected
interpretation branches and detected gaps.
"""

from __future__ import annotations

from typing import Any
import uuid

from ..types.obligation_graph import ObligationGraph, ObligationNode, ObligationNodeKind, ObligationEdge
from ..types.operational_meaning import OperationalMeaningFrame


class ObligationGraphBuilder:
    """Builds obligation graph from meaning frames and gaps.
    
    One utterance may contain multiple compatible meanings.
    The obligation graph preserves them all with dependency edges.
    """
    
    def build(
        self,
        frames: list[OperationalMeaningFrame],
        gaps: list[Any],
        blocking_gap_ids: set[str],
    ) -> ObligationGraph:
        graph = ObligationGraph()
        
        # Add nodes for each operational meaning frame
        for frame in frames:
            kind = self._frame_to_obligation_kind(frame.frame_type)
            node = ObligationNode(
                node_id=f"obl_{frame.frame_id}",
                kind=kind,
                frame_id=frame.frame_id,
                branch_id="",
                group_id="",
                is_required=True,
            )
            graph.add_node(node)
        
        # Add learning question nodes for blocking gaps
        for gap in gaps:
            if gap.gap_id in blocking_gap_ids:
                node = ObligationNode(
                    node_id=f"lq_{gap.gap_id}",
                    kind=ObligationNodeKind.LEARNING_QUESTION,
                    gap_ids=(gap.gap_id,),
                    is_required=False,
                    budget_cost=0.5,
                )
                graph.add_node(node)
                
                # Learning question blocks obligations that depend on it
                for artifact_id in getattr(gap, "blocking_artifact_ids", []):
                    edge = ObligationEdge(
                        source_id=f"lq_{gap.gap_id}",
                        target_id=f"obl_{artifact_id}",
                        edge_type="blocks",
                    )
                    graph.add_edge(edge)
        
        return graph
    
    @staticmethod
    def _frame_to_obligation_kind(frame_type: str) -> ObligationNodeKind:
        mapping = {
            "profile_assertion": ObligationNodeKind.WRITE,
            "concept_definition_teaching": ObligationNodeKind.WRITE,
            "world_fact_claim": ObligationNodeKind.WRITE,
            "correction": ObligationNodeKind.WRITE,
            "memory_command": ObligationNodeKind.WRITE,
            "command": ObligationNodeKind.WRITE,
            "concept_definition_query": ObligationNodeKind.QUERY,
            "self_identity_query": ObligationNodeKind.QUERY,
            "self_capability_query": ObligationNodeKind.QUERY,
            "self_knowledge_query": ObligationNodeKind.QUERY,
            "user_profile_query": ObligationNodeKind.QUERY,
            "user_state_report": ObligationNodeKind.ACKNOWLEDGMENT,
            "social_act": ObligationNodeKind.ACKNOWLEDGMENT,
            "phatic_act": ObligationNodeKind.ACKNOWLEDGMENT,
            "style_feedback": ObligationNodeKind.REACTION,
            "response_feedback": ObligationNodeKind.REACTION,
            "session_exit": ObligationNodeKind.ACTION,
            "safety_candidate": ObligationNodeKind.SAFETY,
            "clarification_request": ObligationNodeKind.CLARIFICATION,
        }
        return mapping.get(frame_type, ObligationNodeKind.RESPONSE)
