from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..store.store import Store
from ..registry import Registry
from .result import SynthesisResult


class ExtractiveStrategy:
    def can_handle(self, params: dict) -> bool:
        return bool(params.get("claim_ids") or params.get("selected_claim_ids"))

    def render(
        self,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
        params: dict,
    ) -> SynthesisResult:
        claim_ids = params.get("claim_ids") or params.get("selected_claim_ids") or []
        max_claims = params.get("max_claims", 5)
        parts = []
        for cid in claim_ids[:max_claims]:
            claim = store.claims.get(cid)
            if claim:
                obj = claim.object_value or claim.object_entity_id or ""
                parts.append(f"{claim.subject_entity_id} {claim.predicate} {obj}")
        output = "; ".join(parts) if parts else "No relevant information found."
        return SynthesisResult(
            success=True,
            output=output,
            strategy="extractive",
            cost_ms=1.0,
        )
