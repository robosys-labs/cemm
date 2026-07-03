from __future__ import annotations

import re

from ..kernel.realization_verifier import verify, VerificationResult
from ..registry import Registry
from ..registry.act_type_policy import get_intent_template
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


def _source_text(answer_graph: SemanticAnswerGraph, store: Store) -> str:
    for signal_id in answer_graph.source_signal_ids:
        signal = store.signals.get(signal_id)
        if signal and signal.content:
            return str(signal.content)
    return ""


def _topic_from_scoped_help(text: str) -> str:
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    joined = " ".join(tokens)
    match = re.search(r"\b(help|assist)\s+me\b(?P<tail>.*)", joined)
    if not match:
        return ""
    tail_tokens = [
        t for t in re.findall(r"[a-z0-9']+", match.group("tail"))
        if t not in {"a", "an", "the", "to", "with", "for", "please", "though", "then", "really", "just"}
    ]
    topic = " ".join(tail_tokens).strip()
    if topic.startswith("grow my "):
        return "growing your " + topic[len("grow my "):]
    if topic.startswith("grow "):
        return "growing " + topic[len("grow "):]
    return topic


def _likely_cause_text(kernel: ContextKernel, store: Store) -> str:
    for cause_id in kernel.conversation.dynamics.likely_cause_claim_ids:
        claim = store.claims.get(cause_id)
        if not claim:
            continue
        if claim.object_value and str(claim.object_value).strip().lower() != "failure":
            return _clean_object(str(claim.object_value))
        subject = str(claim.subject_entity_id or "").replace("_", " ").strip()
        if subject:
            return subject
    return ""


def _is_situational_checkin(text: str) -> bool:
    normalized = " ".join(re.findall(r"[a-z0-9']+", text.lower()))
    return normalized in {
        "what's going on",
        "whats going on",
        "what is going on",
        "what's up",
        "whats up",
    }


def _is_fresh_world_limit(answer_graph: SemanticAnswerGraph, source_text: str) -> bool:
    reasons = " ".join(answer_graph.uncertainty_reasons).lower()
    text = source_text.lower()
    if "fresh-world query requires live retrieval" in reasons:
        return True
    markers = (
        "today", "tonight", "tomorrow", "latest", "current", "recent",
        "weather", "forecast", "temperature", "who won", "score", "match",
    )
    return any(marker in text for marker in markers)


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
        source_text = _source_text(answer_graph, store)
        source_text_lower = source_text.lower().strip()

        # Map SAG intent to template_key for conversational responses.
        # Conditional branches handle intents that need runtime state (turn index,
        # affect, repetition pressure, source text analysis).  All flat intent→
        # template mappings are sourced from intent_template_default in
        # uol_semantics.json via get_intent_template().
        intent = answer_graph.intent

        # ── Conditional branches (runtime state required) ───────────────
        if intent == "greeting":
            params["template_key"] = "greeting_returning" if kernel.conversation.turn_index > 1 else "greeting"
        elif intent == "phatic_checkin":
            params["template_key"] = "phatic_checkin_returning" if kernel.conversation.turn_index > 1 else "phatic_checkin"
        elif intent == "acknowledgment":
            params["template_key"] = "acknowledgment_followup" if kernel.conversation.turn_index > 1 else "acknowledgment"
        elif intent == "playful_acknowledgment":
            if (
                kernel.user.affect.playfulness > 0.7
                or (
                    kernel.user.affect.current_stance == "playful"
                    and kernel.user.affect.playfulness > 0.65
                )
            ):
                params["template_key"] = "playful_acknowledgment_followup"
            else:
                params["template_key"] = "playful_acknowledgment"
        elif intent == "frustration_response":
            likely_cause = _likely_cause_text(kernel, store)
            if kernel.conversation.dynamics.repetition_pressure >= 0.4 and likely_cause:
                params["template_key"] = "frustration_response_causal_loop"
                params.setdefault("variables", {"cause": likely_cause})
            elif kernel.conversation.dynamics.repetition_pressure >= 0.4:
                params["template_key"] = "frustration_response_repetition"
            elif (
                kernel.user.affect.current_stance in {"frustrated", "hostile"}
                or kernel.user.affect.frustration > 0.5
                or kernel.user.affect.hostility > 0.4
            ):
                params["template_key"] = "frustration_response_followup"
            else:
                params["template_key"] = "frustration_response"
        elif intent == "confusion_repair":
            if any(
                phrase in source_text_lower for phrase in (
                    "what does that mean",
                    "what does this mean",
                    "what did you mean by that",
                    "what do you mean by that",
                )
            ):
                params["template_key"] = "clarify_previous_meaning"
            else:
                params["template_key"] = "confusion_repair"
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
            if _is_fresh_world_limit(answer_graph, source_text):
                params["template_key"] = "live_world_limit"
            else:
                params["template_key"] = "abstain"
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
        elif intent == "self_identity" and answer_graph.selected_claim_ids:
            params["template_key"] = "self_identity"
            params.setdefault("variables", _self_identity_variables(answer_graph, store))
        elif intent == "self_capability" and answer_graph.selected_claim_ids:
            params["template_key"] = "self_capability"
            params.setdefault("variables", _capability_variables(semantic_claim_atoms))
        elif intent == "user_identity":
            params["template_key"] = "user_identity"
            params.setdefault("variables", _self_identity_variables(answer_graph, store))
        elif intent == "user_name":
            params["template_key"] = "user_name"
            params.setdefault("variables", _name_variables(answer_graph, store))
        elif intent == "general_conversation":
            topic = _topic_from_scoped_help(source_text_lower)
            if topic:
                params["template_key"] = "scoped_help_response"
                params.setdefault("variables", {"topic": topic})
            elif _is_situational_checkin(source_text_lower):
                params["template_key"] = "situational_checkin"
            else:
                params["template_key"] = intent
        elif intent == "evidence_query" and not answer_graph.selected_claim_ids:
            # No evidence found — check for scoped help before falling back
            topic = _topic_from_scoped_help(source_text_lower)
            if topic:
                params["template_key"] = "scoped_help_response"
                params.setdefault("variables", {"topic": topic})
            else:
                params["template_key"] = "abstain"
        elif intent == "safety_deescalation":
            # Extract the harmful action from source text
            harm_words = {"beat", "hit", "hurt", "attack", "fight", "punch", "kick", "stab", "kill", "shoot", "choke", "strangle"}
            source_tokens = set(re.findall(r"[a-z0-9']+", source_text_lower))
            matched_harm = source_tokens & harm_words
            params["template_key"] = "safety_deescalation"
            params.setdefault("variables", {"harmful_action": ", ".join(sorted(matched_harm)) if matched_harm else "do that"})
        elif intent == "social_conflict_clarify":
            # Extract entity name from source text (capitalized word that's not a common word)
            tokens_raw = re.findall(r"[A-Z][a-z]+", source_text)
            common_words = {"I", "The", "A", "An", "Is", "Are", "Do", "Does", "What", "How", "Why", "When", "Where", "Who"}
            entity_candidates = [t for t in tokens_raw if t not in common_words]
            params["template_key"] = "social_conflict_clarify"
            params.setdefault("variables", {"entity": entity_candidates[0] if entity_candidates else "that person"})
        elif intent == "reciprocal_phatic_checkin":
            # Detect user state from source text
            state_words = {"fine": "fine", "good": "good", "okay": "okay", "ok": "okay", "alright": "alright", "not bad": "doing well"}
            user_state = "doing well"
            for word, state in state_words.items():
                if word in source_text_lower:
                    user_state = state
                    break
            params["template_key"] = "reciprocal_phatic_checkin"
            params.setdefault("variables", {"user_state": user_state})
        elif intent == "session_exit":
            params["template_key"] = "session_exit"
        elif intent == "retrospective_repair":
            params["template_key"] = "retrospective_repair"
        else:
            # ── Data-driven fallback for flat intent→template mappings ────
            # All non-conditional intents are sourced from intent_template_default
            # in uol_semantics.json.  Adding a new flat-mapped intent only requires
            # adding an entry to that JSON key — no code change needed here.
            template_key = get_intent_template(intent)
            if template_key:
                params["template_key"] = template_key

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
