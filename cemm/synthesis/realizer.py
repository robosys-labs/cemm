from __future__ import annotations

from ..kernel.realization_verifier import verify, VerificationResult
from ..registry import Registry
from ..store.store import Store
from ..types.context_kernel import ContextKernel
from ..types.semantic_answer_graph import SemanticAnswerGraph
from .router import SynthesisRouter
from .result import SynthesisResult


def _claim_atoms(answer_graph: SemanticAnswerGraph, store: Store) -> list[dict]:
    atoms: list[dict] = []
    for cid in answer_graph.selected_claim_ids:
        claim = store.claims.get(cid)
        if not claim:
            continue
        atoms.append({
            "claim_id": claim.id,
            "subject_entity_id": claim.subject_entity_id,
            "predicate": claim.predicate,
            "object_value": str(claim.object_value or claim.object_entity_id or ""),
            "confidence": claim.confidence,
            "trust": claim.trust,
        })
    return atoms


def _clean_object(text: str) -> str:
    text = text.strip()
    if text.startswith("it "):
        return text[3:]
    return text


def _join_objects(values: list[str]) -> str:
    values = [v for v in values if v]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


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


def _capability_variables(atoms: list[dict]) -> dict[str, str]:
    """Build capability template variables from curated categories.

    Instead of raw-joining all capability claim objects, group them into
    stable categories so the output is a concise summary.
    """
    if not atoms:
        return {"capabilities": "chat, remember what you teach me, answer from stored knowledge, and learn new words or commands"}

    # Map raw capability text to stable categories
    category_map = {
        "language-agnostic understanding via universal object language": "understand language",
        "knowledge compression from runtime traces": "learn from traces",
        "model-driven inference routing": "reason about causes",
        "turn signals into semantic graphs, select evidence, decide actions, realize verified answers, and export traces for training": "process meaning",
        "answer general open-domain questions conversationally when no specific stored claim applies": "answer open-domain questions",
        "tell stories, give light recommendations, and explain my own reasoning in plain language": "chat and explain reasoning",
    }

    categories: list[str] = []
    for atom in atoms:
        raw = _clean_object(str(atom.get("object_value", "")))
        if not raw:
            continue
        category = category_map.get(raw.lower(), raw)
        if category not in categories:
            categories.append(category)

    if not categories:
        return {"capabilities": "chat, remember what you teach me, answer from stored knowledge, and learn new words or commands"}

    return {"capabilities": _join_objects(categories)}


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
        semantic_claim_atoms = _claim_atoms(answer_graph, store)

        # Map SAG intent to template_key for conversational responses
        # when no explicit template or claims are provided
        intent = answer_graph.intent
        if intent == "greeting":
            params["template_key"] = "greeting"
        elif intent == "phatic_checkin":
            params["template_key"] = "phatic_checkin"
        elif intent == "acknowledgment":
            params["template_key"] = "acknowledgment"
        elif intent == "playful_acknowledgment":
            params["template_key"] = "playful_acknowledgment"
        elif intent == "low_competence_repair":
            params["template_key"] = "low_competence_repair"
        elif intent == "frustration_response":
            params["template_key"] = "frustration_response"
        elif intent == "confusion_repair":
            params["template_key"] = "confusion_repair"
        elif intent == "playful_repair":
            params["template_key"] = "playful_repair"
        elif intent == "teaching_offer":
            params["template_key"] = "teaching_offer"
        elif intent == "capability_summary":
            params["template_key"] = "capability_summary"
        elif intent == "unknown_entity_response":
            params["template_key"] = "unknown_entity_response"
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
            params["template_key"] = "abstain"
        elif intent == "remember":
            params["template_key"] = "remember_confirm"
        elif intent in ("learn_command_alias", "learn_lexeme", "learn_correction"):
            params["template_key"] = intent
            teaching_event = next(
                (e for e in answer_graph.entity_refs if e.get("kind") == "teaching_event"),
                {},
            )
            params.setdefault("variables", {
                "surface": teaching_event.get("surface", "that"),
                "meaning": teaching_event.get("meaning", "that"),
            })
        elif intent == "retrieve" and not answer_graph.selected_claim_ids:
            params["template_key"] = "retrieve_empty"
        elif intent == "permission_denied":
            params["template_key"] = "permission_denied"
        elif intent == "self_identity" and answer_graph.selected_claim_ids:
            params["template_key"] = "self_identity"
            params.setdefault("variables", _self_identity_variables(answer_graph, store))
        elif intent == "self_capability" and answer_graph.selected_claim_ids:
            params["template_key"] = "self_capability"
            params.setdefault("variables", _capability_variables(semantic_claim_atoms))
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
        elif intent in ("general_conversation", "story_request", "recommendation_request", "food_recommendation", "open_question"):
            params["template_key"] = intent

        strategy = self._router.select_strategy(kernel, store, registry, params)
        result = self._router.route(strategy, kernel, store, registry, params)
        result.metadata["source_answer_graph_id"] = answer_graph.id
        if semantic_claim_atoms:
            result.metadata["semantic_claim_atoms"] = semantic_claim_atoms

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
