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
        max_claims = params.get("max_claims", min(len(claim_ids), 10) or 5)
        parts = []
        for cid in claim_ids[:max_claims]:
            claim = store.claims.get(cid)
            if claim:
                obj = claim.object_value or claim.object_entity_id or ""
                subj = self._humanize_subject(claim.subject_entity_id, kernel)
                predicate = claim.predicate.replace("_", " ")
                parts.append(self._format_claim(subj, predicate, obj))
        if not parts:
            output = "No relevant information found."
        elif len(parts) == 1:
            output = parts[0]
        else:
            output = " ".join(parts)
        return SynthesisResult(
            success=True,
            output=output,
            strategy="extractive",
            cost_ms=1.0,
        )

    @staticmethod
    def _humanize_subject(subject_id: str, kernel: ContextKernel) -> str:
        if subject_id == kernel.self_view.self_id:
            return "I"
        if subject_id == "user":
            return "You"
        return subject_id

    @staticmethod
    def _format_claim(subj: str, predicate: str, obj: str) -> str:
        if subj == "I":
            if predicate in ("knows about", "knows_about"):
                return f"I know about {obj}."
            if predicate in ("limitation", "limitations"):
                return f"My limitation: {obj}."
            if predicate in ("answers identity as", "answers_identity_as"):
                return f"I am {obj}."
            if predicate in ("architecture",):
                return f"My architecture: {obj}."
            if predicate in ("can do", "can_do"):
                return f"I can {obj}."
            return f"I {predicate} {obj}." if obj else f"I {predicate}."
        if subj == "You":
            return f"You {predicate} {obj}." if obj else f"You {predicate}."
        return f"{subj} {predicate} {obj}." if obj else f"{subj} {predicate}."
