from __future__ import annotations
from ..store.store import Store
from ..types.model import Model, ModelKind, ModelStatus
from ..types.claim import Claim
from ..types.context_kernel import ContextKernel
from ..types.packets import InferencePacket
from ..types.semantic_event_graph import SemanticEventGraph


class CausalInference:
    def __init__(self, store: Store) -> None:
        self._store = store

    def predict(
        self,
        action_or_event: str,
        active_claim_ids: list[str],
        kernel: ContextKernel,
        graph: SemanticEventGraph | None = None,
    ) -> InferencePacket:
        models = self._store.models.find_by_kind(
            ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value,
        )
        active_claims = []
        for cid in active_claim_ids:
            claim = self._store.claims.get(cid)
            if claim:
                active_claims.append(claim)

        graph_predicates: list[str] = []
        if graph:
            for proc in graph.processes:
                fk = proc.get("frame_key", "")
                if fk:
                    graph_predicates.append(fk)
            for state in graph.states:
                sk = state.get("state_key", "")
                if sk:
                    graph_predicates.append(sk)
            for ref in graph.entity_refs:
                role = ref.get("role", "")
                if role:
                    graph_predicates.append(role)

        predictions: list[dict] = []
        for model in models:
            if not self._preconditions_match(model, active_claims, action_or_event, graph_predicates):
                continue
            for effect in model.effects:
                predictions.append({
                    "model_id": model.id,
                    "predicate": effect,
                    "confidence": model.confidence * model.trust,
                    "risk": model.risk,
                })

        predictions.sort(key=lambda p: p["confidence"], reverse=True)
        max_ranked = kernel.budget.max_ranked
        predictions = predictions[:max_ranked]

        confidence = sum(p["confidence"] for p in predictions) / max(len(predictions), 1) if predictions else 0.5

        used_model_ids = [m.id for m in models]
        return InferencePacket(
            implications=[],
            contradictions=[],
            predictions=predictions,
            missing_slots=list(kernel.goal.missing_slots) if kernel.goal else [],
            state_deltas={},
            inference_graph_output_model_ids=used_model_ids,
            confidence=confidence,
        )


    def transitive_closure(
        self,
        start_claim_ids: list[str],
        kernel: ContextKernel,
        max_depth: int = 3,
        confidence_floor: float = 0.3,
    ) -> InferencePacket:
        all_predictions: list[dict] = []
        current_ids = list(start_claim_ids)
        visited_claims: set[str] = set(start_claim_ids)
        visited_effects: set[str] = set()
        depth = 0
        while depth < max_depth and current_ids:
            next_ids: list[str] = []
            for cid in current_ids:
                if cid in visited_claims:
                    continue
                visited_claims.add(cid)
                claim = self._store.claims.get(cid)
                if claim is None:
                    continue
                packet = self.predict(claim.predicate, [cid], kernel)
                for p in packet.predictions:
                    if p["confidence"] < confidence_floor:
                        continue
                    pred_id = p["predicate"]
                    if pred_id in visited_effects:
                        continue
                    visited_effects.add(pred_id)
                    all_predictions.append(p)
                    next_ids.append(pred_id)
                if len(all_predictions) >= kernel.budget.max_ranked:
                    break
            current_ids = next_ids
            depth += 1
            if len(all_predictions) >= kernel.budget.max_ranked:
                break
        all_predictions = all_predictions[:kernel.budget.max_ranked]
        confidence = sum(p["confidence"] for p in all_predictions) / max(len(all_predictions), 1) if all_predictions else 0.5
        return InferencePacket(
            implications=[],
            contradictions=[],
            predictions=all_predictions,
            missing_slots=[],
            state_deltas={},
            confidence=confidence,
        )

    @staticmethod
    def _preconditions_match(model: Model, claims: list[Claim], action: str, graph_predicates: list[str] | None = None) -> bool:
        if not model.preconditions:
            return False
        if not claims:
            return False
        action_lower = action.lower()
        for prec in model.preconditions:
            prec_lower = prec.lower()
            for claim in claims:
                if prec_lower in claim.predicate.lower():
                    return True
            if prec_lower in action_lower:
                return True
            if graph_predicates:
                for gp in graph_predicates:
                    if prec_lower in gp.lower():
                        return True
        return False
