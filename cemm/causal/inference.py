from __future__ import annotations
from ..store.store import Store
from ..types.model import Model, ModelKind, ModelStatus
from ..types.claim import Claim
from ..types.context_kernel import ContextKernel


class CausalInference:
    def __init__(self, store: Store) -> None:
        self._store = store

    def predict(
        self,
        action_or_event: str,
        active_claim_ids: list[str],
        kernel: ContextKernel,
    ) -> list[dict]:
        models = self._store.models.find_by_kind(
            ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value,
        )
        active_claims = []
        for cid in active_claim_ids:
            claim = self._store.claims.get(cid)
            if claim:
                active_claims.append(claim)

        predictions: list[dict] = []
        for model in models:
            if not self._preconditions_match(model, active_claims, action_or_event):
                continue
            for effect in model.effects:
                predictions.append({
                    "model_id": model.id,
                    "predicate": effect,
                    "confidence": model.confidence * model.trust,
                })

        predictions.sort(key=lambda p: p["confidence"], reverse=True)
        max_ranked = kernel.budget.max_ranked
        return predictions[:max_ranked]

    def transitive_closure(
        self,
        start_claim_ids: list[str],
        kernel: ContextKernel,
        max_depth: int = 3,
    ) -> list[dict]:
        all_predictions: list[dict] = []
        current_ids = list(start_claim_ids)
        visited: set[str] = set()
        depth = 0
        while depth < max_depth and current_ids:
            next_ids: list[str] = []
            for cid in current_ids:
                claim = self._store.claims.get(cid)
                if claim is None:
                    continue
                predictions = self.predict(claim.predicate, [cid], kernel)
                for p in predictions:
                    if p["confidence"] >= 0.3:
                        pred_id = p["predicate"]
                        if pred_id in visited:
                            continue
                        visited.add(pred_id)
                        all_predictions.append(p)
                        next_ids.append(pred_id)
                if len(all_predictions) >= kernel.budget.max_ranked:
                    break
            current_ids = next_ids
            depth += 1
            if len(all_predictions) >= kernel.budget.max_ranked:
                break
        return all_predictions[:kernel.budget.max_ranked]

    @staticmethod
    def _preconditions_match(model: Model, claims: list[Claim], action: str) -> bool:
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
        return False
