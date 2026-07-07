"""CausalBridge — queries DurableSemanticStore for causal relations.

Examines the UOLGraph for "causes" edges and entity atoms, then queries
the DurableSemanticStore for matching causal relations. Converts matches
into AffordancePrediction objects for the semantic runtime pipeline.
"""

from __future__ import annotations

from typing import Any

from ..memory.durable_semantic_store import DurableSemanticStore
from ..types.uol_graph import AffordancePrediction


class CausalBridge:
    """Bridge between DurableSemanticStore and the semantic runtime.

    Queries durable causal relations and converts them into
    AffordancePrediction objects compatible with the UOLGraph pipeline.
    """

    def __init__(self, durable_store: DurableSemanticStore | None = None) -> None:
        self._store = durable_store

    def predict(
        self,
        graph: Any,
        kernel: Any,
        active_claim_ids: list[str] | None = None,
        action_or_event: str = "",
    ) -> list[AffordancePrediction]:
        """Query durable causal relations and convert to AffordancePredictions.

        Returns a list of AffordancePrediction objects that can be added
        to the graph's affordance_predictions list.
        """
        if self._store is None:
            return []

        try:
            return self._predict_from_durable(graph, kernel)
        except Exception:
            return []

    def _predict_from_durable(
        self, graph: Any, kernel: Any,
    ) -> list[AffordancePrediction]:
        """Query DurableSemanticStore for causal relations matching graph atoms."""
        entity_ids: list[str] = []
        graph_predicates: list[str] = []
        if graph:
            for atom in graph.atoms.values():
                if atom.kind == "entity":
                    entity_ids.append(atom.key)
                if atom.kind in ("process", "state", "intent", "need"):
                    graph_predicates.append(atom.key)
                if atom.surface:
                    graph_predicates.append(atom.surface)
            for edge in graph.edges:
                if edge.edge_type == "causes":
                    source = graph.atoms.get(edge.source_id)
                    target = graph.atoms.get(edge.target_id)
                    if source:
                        graph_predicates.append(source.key)
                    if target:
                        graph_predicates.append(target.key)

        all_causal = self._store.query_relations(relation_key="causes")
        if not all_causal:
            all_causal = [
                f for f in self._store.query_relations()
                if f.relation_family == "causal"
            ]

        predictions: list[AffordancePrediction] = []
        seen_keys: set[str] = set()

        for frame in all_causal:
            subj = frame.subject.entity_id or frame.subject.concept_id or frame.subject.surface
            obj = frame.object.entity_id or frame.object.concept_id or frame.object.surface
            match_key = f"{subj}:{frame.relation_key}:{obj}"
            if match_key in seen_keys:
                continue

            matched = False
            for eid in entity_ids:
                if subj and subj in eid:
                    matched = True
                    break
                if obj and obj in eid:
                    matched = True
                    break
            if not matched:
                for gp in graph_predicates:
                    if subj and subj.lower() in gp.lower():
                        matched = True
                        break
                    if obj and obj.lower() in gp.lower():
                        matched = True
                        break

            if not matched:
                continue

            seen_keys.add(match_key)
            trigger_ids = [
                atom_key for atom_key in entity_ids
                if (subj and subj in atom_key) or (obj and obj in atom_key)
            ]

            predictions.append(AffordancePrediction(
                id=f"causal_{frame.relation_id}",
                affordance_key=frame.relation_key,
                trigger_atom_ids=trigger_ids,
                predicted_patch_template={
                    "target": "episodic_trace",
                    "operation": "causal_prediction",
                    "predicate": frame.relation_key,
                    "subject": subj,
                    "object": obj,
                },
                effect_type="causal_effect",
                confidence=frame.confidence,
                evidence_refs=list(frame.evidence_refs) if hasattr(frame, "evidence_refs") else [],
                reason=f"durable_causal:{subj}->{obj}",
            ))

        predictions.sort(key=lambda p: p.confidence, reverse=True)

        max_ranked = 10
        if kernel is not None and hasattr(kernel, "budget"):
            max_ranked = getattr(kernel.budget, "max_ranked", 10)
        predictions = predictions[:max_ranked]

        return predictions
