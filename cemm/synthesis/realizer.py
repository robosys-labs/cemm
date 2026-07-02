from __future__ import annotations

from ..kernel.realization_verifier import verify, VerificationResult
from ..registry import Registry
from ..store.store import Store
from ..types.context_kernel import ContextKernel
from ..types.semantic_answer_graph import SemanticAnswerGraph
from .router import SynthesisRouter
from .result import SynthesisResult


def _name_variables(answer_graph: SemanticAnswerGraph, store: Store) -> dict:
    for cid in answer_graph.selected_claim_ids:
        claim = store.claims.get(cid)
        if claim and claim.object_value:
            return {"name": str(claim.object_value)}
    return {"name": "you"}


def _self_identity_variables(answer_graph: SemanticAnswerGraph, store: Store) -> dict:
    for cid in answer_graph.selected_claim_ids:
        claim = store.claims.get(cid)
        if claim and claim.object_value:
            return {"name": str(claim.object_value), "role": claim.predicate}
    return {"name": "CEMM", "role": "assistant"}


def _self_capability_variables(answer_graph: SemanticAnswerGraph, store: Store) -> dict:
    capabilities = []
    for cid in answer_graph.selected_claim_ids:
        claim = store.claims.get(cid)
        if claim and claim.object_value:
            capabilities.append(str(claim.object_value))
    if not capabilities:
        capabilities = ["answer questions, remember facts, and reason about claims"]
    return {"capabilities": ", ".join(capabilities)}


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
        elif intent == "ask" or intent == "ask_meaning":
            clarification = next(
                (e.get("question") for e in answer_graph.entity_refs if e.get("kind") == "clarification"),
                None,
            )
            term = next(
                (e.get("term") for e in answer_graph.entity_refs if e.get("kind") == "clarification"),
                "that",
            )
            if clarification:
                params["template"] = clarification
            else:
                params["template_key"] = "ask_meaning"
                params.setdefault("variables", {"term": term})
        elif intent == "abstain" and not answer_graph.selected_claim_ids:
            reason = answer_graph.uncertainty_reasons[0] if answer_graph.uncertainty_reasons else ""
            params["template"] = reason or "I don't have enough information to answer."
        elif intent == "remember":
            params["template_key"] = "remember_confirm"
        elif intent == "retrieve" and not answer_graph.selected_claim_ids:
            params["template_key"] = "retrieve_empty"
        elif intent == "permission_denied":
            params["template_key"] = "permission_denied"
        elif intent == "self_identity" and answer_graph.selected_claim_ids:
            params["template_key"] = "self_identity"
            params.setdefault("variables", _self_identity_variables(answer_graph, store))
        elif intent == "self_capability" and answer_graph.selected_claim_ids:
            params["template_key"] = "self_capability"
            params.setdefault("variables", _self_capability_variables(answer_graph, store))
        elif intent == "self_knowledge":
            params["template_key"] = "self_knowledge"
        elif intent == "user_identity":
            params["template_key"] = "user_identity"
            params.setdefault("variables", _self_identity_variables(answer_graph, store))
        elif intent == "user_name":
            params["template_key"] = "user_name"
            params.setdefault("variables", _name_variables(answer_graph, store))
        elif intent in ("user_identity_unknown", "user_name_unknown"):
            params["template_key"] = intent
        elif intent == "self_query_unknown":
            params["template_key"] = "self_query_unknown"

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
