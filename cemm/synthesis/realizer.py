from __future__ import annotations

from ..kernel.realization_verifier import verify, VerificationResult
from ..registry import Registry
from ..store.store import Store
from ..types.context_kernel import ContextKernel
from ..types.semantic_answer_graph import SemanticAnswerGraph
from .router import SynthesisRouter
from .result import SynthesisResult


class RealizationPipeline:
    def __init__(self, router: SynthesisRouter | None = None) -> None:
        self._router = router or SynthesisRouter()

    def run(
        self,
        answer_graph: SemanticAnswerGraph,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
    ) -> SynthesisResult:
        params = {
            "selected_claim_ids": answer_graph.selected_claim_ids,
            "selected_model_ids": answer_graph.selected_model_ids,
            "answer_graph": answer_graph,
        }

        # Map SAG intent to template_key for conversational responses
        # when no explicit template or claims are provided
        intent = answer_graph.intent
        if intent == "greeting":
            params["template_key"] = "greeting"
        elif intent == "acknowledgment":
            params["template_key"] = "acknowledgment"
        elif intent == "ask":
            params["template_key"] = "clarification"
            params.setdefault("variables", {"term": "that"})
        elif intent == "abstain" and not answer_graph.selected_claim_ids:
            reason = answer_graph.uncertainty_reasons[0] if answer_graph.uncertainty_reasons else ""
            params["template"] = reason or "I don't have enough information to answer."

        strategy = self._router.select_strategy(kernel, store, registry, params)
        result = self._router.route(strategy, kernel, store, registry, params)
        result.metadata["source_answer_graph_id"] = answer_graph.id

        # Build claim_id -> claim_text map and claim objects for verification
        claim_text_map: dict[str, str] = {}
        claim_objs: list = []
        for cid in answer_graph.selected_claim_ids:
            claim = store.claims.get(cid)
            if claim:
                claim_objs.append(claim)
                if claim.object_value is not None:
                    claim_text_map[cid] = str(claim.object_value)
        private_names = [e.get("name", "") for e in answer_graph.entity_refs if e.get("scope") == "private"]
        verification = verify(
            answer_graph,
            result.output,
            claim_text_map=claim_text_map or None,
            private_entity_names=private_names or None,
            registry=registry,
            claims=claim_objs or None,
        )
        result.verified = verification.verified
        result.metadata["verification"] = {
            "claim_coverage": verification.claim_coverage,
            "uncertainty_preserved": verification.uncertainty_preserved,
            "private_evidence_protected": verification.private_evidence_protected,
            "evidence_integrity_ok": verification.evidence_integrity_ok,
            "unsupported_spans": verification.unsupported_spans,
            "details": verification.details,
        }
        return result
