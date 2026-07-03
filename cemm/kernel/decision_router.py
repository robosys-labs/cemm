from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..types.context_kernel import ContextKernel
from ..types.packets import (
    ActionPlan,
    DecisionPacket,
    GroundedGraph,
    InferencePacket,
    MemoryPacket,
)
from ..types.context_inference import ContextInference
from ..types.conversation_act import ConversationAct, ConversationActPacket
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..types.semantic_event_graph import SemanticEventGraph
from ..types.signal import ObservationSemantics
from .answer_graph_ranker import best_candidate
from ..registry.uol_mapper import UOLMapper
from ..registry.act_type_policy import (
    is_simple_answer as _is_simple_answer,
    is_identity_query as _is_identity_query,
    is_assertion as _is_assertion,
    get_response_mode as _get_response_mode,
    get_default_template as _get_default_template,
    QUESTION_FRAMES as _QUESTION_FRAMES,
)


_PURE_ACKNOWLEDGMENT_PHRASES_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_pure_acknowledgment_phrases() -> set[str]:
    if not _PURE_ACKNOWLEDGMENT_PHRASES_PATH.exists():
        return set()
    data = json.loads(_PURE_ACKNOWLEDGMENT_PHRASES_PATH.read_text(encoding="utf-8"))
    return set(data.get("pure_acknowledgment_phrases", []))


def _load_cue_sets() -> dict[str, set[str]]:
    """Load cue sets from UOL semantic entries with cue_type metadata."""
    if not _PURE_ACKNOWLEDGMENT_PHRASES_PATH.exists():
        return {}
    data = json.loads(_PURE_ACKNOWLEDGMENT_PHRASES_PATH.read_text(encoding="utf-8"))
    cue_sets: dict[str, set[str]] = {}
    for entry in data.get("uol_semantics", []):
        cue_type = entry.get("cue_type")
        if not cue_type:
            continue
        cue_sets.setdefault(cue_type, set()).update(entry.get("aliases", []))
    return cue_sets


_CUE_SETS = _load_cue_sets()


class DecisionRouter:
    def __init__(self, uol_mapper: UOLMapper | None = None) -> None:
        self._uol_mapper = uol_mapper
        self._pure_acknowledgment_phrases = _load_pure_acknowledgment_phrases()

    def run(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        grounded_graph: GroundedGraph | None = None,
        memory_packet: MemoryPacket | None = None,
        inference_packet: InferencePacket | None = None,
        answer_candidates: list[SemanticAnswerGraph] | None = None,
        input_text: str = "",
        observation_semantics: ObservationSemantics | None = None,
        context_inference: ContextInference | None = None,
        conversation_act: ConversationActPacket | ConversationAct | None = None,
        store: Any | None = None,
        act_resolution_plan: Any = None,
    ) -> DecisionPacket:
        selected_claim_ids = memory_packet.selected_claim_ids if memory_packet else []
        selected_model_ids = memory_packet.selected_model_ids if memory_packet else []
        predictions = inference_packet.predictions if inference_packet else []
        missing_slots = (grounded_graph.missing_slots if grounded_graph else
                         kernel.goal.missing_slots if kernel.goal else [])
        required_slots = list(kernel.goal.required_slots) if kernel.goal else []
        graph_frame_keys = {p.get("frame_key", "") for p in graph.processes}
        graph_state_keys = {s.get("state_key", "") for s in graph.states}
        input_lower = input_text.lower().strip() if input_text else ""
        # Language-agnostic question detection: terminal "?" is a surface signal,
        # and question frames in the SEG are the structural signal. No English
        # prefixes are used in routing. Question frames are sourced from the
        # registry data file (uol_semantics.json → question_frames).
        is_question = (
            input_lower.endswith("?")
            or bool(graph_frame_keys & _QUESTION_FRAMES)
            or bool(conversation_act and conversation_act.act_type == "evidence_query")
        )

        # ── Stage 0: ActResolutionPlan-based routing (highest authority) ──
        # When an ActResolutionPlan is provided, use it as the primary routing
        # signal. Priority: SafetyTask → highest-priority ReplyObligation →
        # MemoryUpdatePlan → AnswerTask → fall through to ConversationAct.
        if act_resolution_plan is not None:
            # Safety tasks always win
            if act_resolution_plan.safety_tasks:
                return self._make_answer_packet(
                    intent="safety_deescalation",
                    response_mode="safety_response",
                    confidence=act_resolution_plan.safety_tasks[0].confidence,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="act_resolution_plan: safety_task override",
                )

            # Abstain when planner requires it (tool_required/fresh_required policy
            # with no available fresh evidence). Checked after safety but before
            # obligation processing so external-facts queries are correctly gated.
            if act_resolution_plan.should_abstain:
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=act_resolution_plan.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=act_resolution_plan.confidence,
                    reason=f"act_resolution_plan.should_abstain: {act_resolution_plan.abstention_reason}",
                )

            # Memory updates with no answer tasks → remember
            if act_resolution_plan.memory_updates and not act_resolution_plan.answer_tasks:
                if graph.claim_candidates:
                    return DecisionPacket(
                        action_kind="remember",
                        action_plan=ActionPlan(
                            action_kind="remember",
                            execution_allowed=True,
                            confidence=act_resolution_plan.confidence,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=act_resolution_plan.confidence,
                        reason="act_resolution_plan: memory_updates only → remember",
                    )

            # Highest-priority obligation drives the answer
            if act_resolution_plan.obligations:
                top_obligation = act_resolution_plan.obligations[0]
                top_act = top_obligation.act_type

                # Memory acts → remember with claim candidates
                if top_act in ("claim_assertion", "preference_assertion",
                               "definition_teaching", "command_alias_teaching",
                               "explicit_remember", "memory_write"):
                    if graph.claim_candidates:
                        return DecisionPacket(
                            action_kind="remember",
                            action_plan=ActionPlan(
                                action_kind="remember",
                                execution_allowed=True,
                                confidence=top_obligation.confidence,
                                risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                            ),
                            confidence=top_obligation.confidence,
                            reason=f"act_resolution_plan: obligation={top_act} → remember",
                        )

                # Answer obligations with evidence
                if top_obligation.requires_evidence and selected_claim_ids:
                    return self._make_answer_packet(
                        intent=top_obligation.intent,
                        response_mode=top_obligation.response_mode,
                        confidence=top_obligation.confidence,
                        selected_claim_ids=selected_claim_ids,
                        selected_model_ids=selected_model_ids,
                        graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                        reason=f"act_resolution_plan: obligation={top_act} with evidence → answer",
                    )

                # Simple answer obligations (no evidence needed)
                if not top_obligation.requires_evidence:
                    return self._make_answer_packet(
                        intent=top_obligation.intent,
                        response_mode=top_obligation.response_mode,
                        confidence=top_obligation.confidence,
                        graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                        reason=f"act_resolution_plan: obligation={top_act} → answer",
                    )

            # Fall through to ConversationAct-based routing if plan didn't resolve

        # ── Stage 1: ConversationAct-based routing (fallback) ──
        # When a ConversationAct is provided, use it as the primary routing signal.
        # This prevents social, creative, repair, and teaching turns from falling
        # through into evidence answer, clarification, or remember.
        if conversation_act and conversation_act.act_type != "unknown":
            act = conversation_act.act_type
            response_mode = conversation_act.response_mode

            # Simple answer routing: act → intent, response_mode
            # All these acts produce an "answer" with no evidence retrieval needed.
            # The set is sourced from act_type_metadata in uol_semantics.json.
            if _is_simple_answer(act):
                intent = act
                mode = response_mode
                if act in {"frustration_signal", "assistant_evaluation", "user_complaint"}:
                    intent = "frustration_response"
                    mode = "repair_response"
                elif act == "user_state_report":
                    if "phatic_checkin" in getattr(conversation_act, "act_types", []):
                        intent = "reciprocal_phatic_checkin"
                    else:
                        intent = "chat_mode_statement"
                    mode = "social_response"
                return self._make_answer_packet(
                    intent=intent,
                    response_mode=mode,
                    confidence=conversation_act.confidence,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason=f"conversation_act={act} → {mode}",
                )

            # Capability query: use curated summary, not raw claim join
            # These acts share the capability_summary response_mode from metadata.
            if _get_response_mode(act) == "capability_summary":
                return self._make_answer_packet(
                    intent="capability_summary",
                    response_mode="capability_summary",
                    confidence=0.8,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason=f"conversation_act={act} → capability_summary",
                )

            # Self/user identity and knowledge queries: route to evidence answer
            # Only identity_query acts (self_identity, self_knowledge, user_identity,
            # user_name) route here — generic evidence_query falls through to old routing.
            if _is_identity_query(act):
                if selected_claim_ids:
                    return self._make_answer_packet(
                        intent=act,
                        response_mode="evidence_answer",
                        confidence=min(0.9, graph.confidence),
                        selected_claim_ids=selected_claim_ids,
                        selected_model_ids=selected_model_ids,
                        graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                        reason=f"conversation_act={act} with evidence → evidence_answer",
                    )
                # No evidence: fall through to old routing which handles unknown identity/name

            # Explicit remember command: route to remember with claim candidates
            if act == "explicit_remember" and graph.claim_candidates:
                return DecisionPacket(
                    action_kind="remember",
                    action_plan=ActionPlan(
                        action_kind="remember",
                        execution_allowed=True,
                        confidence=0.8,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.8,
                    reason="conversation_act=explicit_remember with claim candidates",
                )

            # Claim/preference assertions: route to remember when claim candidates exist
            if _is_assertion(act) and graph.claim_candidates:
                return DecisionPacket(
                    action_kind="remember",
                    action_plan=ActionPlan(
                        action_kind="remember",
                        execution_allowed=True,
                        confidence=0.75,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.75,
                    reason=f"conversation_act={act} with claim candidates → remember",
                )

            # Open-domain entity query: check for evidence, else unknown_entity_response
            if act == "open_domain_entity_query":
                if self._is_fresh_world_query(input_text):
                    return DecisionPacket(
                        action_kind="abstain",
                        action_plan=ActionPlan(
                            action_kind="abstain",
                            execution_allowed=False,
                            confidence=0.8,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=0.8,
                        reason="fresh-world query requires live retrieval",
                    )
                if selected_claim_ids:
                    return self._make_answer_packet(
                        intent="evidence_answer",
                        response_mode="evidence_answer",
                        confidence=min(0.9, graph.confidence),
                        selected_claim_ids=selected_claim_ids,
                        selected_model_ids=selected_model_ids,
                        graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                        reason="open_domain_entity_query with evidence → evidence_answer",
                    )
                return self._make_answer_packet(
                    intent="unknown_entity_response",
                    response_mode="unknown_entity_response",
                    confidence=0.7,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="open_domain_entity_query without evidence → unknown_entity_response",
                )

            # Exit — social closure, not abstention (P0-2)
            if act == "exit":
                return self._make_answer_packet(
                    intent="session_exit",
                    response_mode="social_response",
                    confidence=0.95,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="conversation_act=exit → social closure",
                )

            # Safety response — deescalate/refuse (P0-4)
            if act == "safety_response":
                return self._make_answer_packet(
                    intent="safety_deescalation",
                    response_mode="safety_response",
                    confidence=0.95,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="conversation_act=safety_response → deescalate",
                )

            # Social conflict clarification — ask for idiom clarification
            if act == "social_conflict_clarify":
                return self._make_answer_packet(
                    intent="social_conflict_clarify",
                    response_mode="social_response",
                    confidence=0.8,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="conversation_act=social_conflict_clarify → ask clarification",
                )

            # Reciprocal phatic check-in — answer with reciprocal checkin
            if act == "reciprocal_phatic_checkin":
                return self._make_answer_packet(
                    intent="reciprocal_phatic_checkin",
                    response_mode="social_response",
                    confidence=0.85,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="conversation_act=reciprocal_phatic_checkin → reciprocal social response",
                )

            # Retrospective repair — acknowledge and reset
            if act == "retrospective_repair":
                return self._make_answer_packet(
                    intent="retrospective_repair",
                    response_mode="repair_response",
                    confidence=0.8,
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                    reason="conversation_act=retrospective_repair → acknowledge and reset",
                )

        if "low_competence" in graph_state_keys:
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    execution_allowed=True,
                    confidence=0.75,
                    params={"intent": "low_competence_repair"},
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.75,
                reason="low competence/frustration signal handled conversationally",
            )

        # Teaching/learning intent detection: definitions, aliases, and corrections
        # take precedence so CEMM learns surface-to-meaning mappings before answering.
        teaching_intent = self._detect_teaching_intent(graph, input_text)
        if teaching_intent:
            return teaching_intent

        # If answer candidates are provided, rank them and use the best one
        if answer_candidates:
            best = best_candidate(answer_candidates, kernel, graph, memory_packet)
            if best is not None:
                selected_claim_ids = best.selected_claim_ids
                selected_model_ids = best.selected_model_ids
                if best.intent == "answer":
                    pass  # fall through to existing logic with improved claims
                elif best.intent == "ask":
                    return DecisionPacket(
                        action_kind="ask",
                        action_plan=ActionPlan(
                            action_kind="ask",
                            execution_allowed=True,
                            confidence=best.confidence,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=best.confidence,
                        reason=f"answer candidate intent=ask (score={best.confidence:.2f})",
                    )
                elif best.intent == "abstain":
                    return DecisionPacket(
                        action_kind="abstain",
                        action_plan=ActionPlan(
                            action_kind="abstain",
                            selected_model_ids=selected_model_ids,
                            execution_allowed=False,
                            confidence=best.confidence,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=best.confidence,
                        reason=f"best answer candidate intent=abstain (score={best.confidence:.2f})",
                    )

        # Command intent detection: explicit user commands take priority
        cmd_intent = self._detect_command_intent(
            input_text, graph, kernel, selected_claim_ids,
            predictions=predictions, missing_slots=missing_slots,
            is_question=is_question,
        )
        if cmd_intent:
            return cmd_intent

        if missing_slots:
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    required_slots=required_slots,
                    missing_slots=missing_slots,
                    execution_allowed=True,
                    confidence=0.9,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.9,
                reason="missing required slots",
            )

        # Claim candidates from SEG: route to remember to store new knowledge.
        # Gate: only store when the conversation act allows memory writes.
        if graph.claim_candidates and not selected_claim_ids and not is_question:
            if conversation_act and not conversation_act.allows_memory_write:
                pass  # fall through to conversational handling
            else:
                return DecisionPacket(
                    action_kind="remember",
                    action_plan=ActionPlan(
                        action_kind="remember",
                        execution_allowed=True,
                        confidence=0.7,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason="SEG contains claim candidates for storage",
                )

        if "assistance_request" in graph_frame_keys and self._has_scoped_assistance_content(input_text):
            return self._make_answer_packet(
                intent="general_conversation",
                response_mode="general_conversation",
                confidence=0.72,
                graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                reason="assistance request includes task scope",
            )

        # Predicate-aware query handlers: self identity/capability and user identity/name.
        # Evidence must exist AND match the requested predicate/frame; otherwise ask/abstain.
        self_query_frames = {"self_identity_query", "self_capability_query", "self_knowledge_query"}
        user_query_frames = {"user_identity_query", "user_name_query"}
        identity_predicates = {
            "name", "preferred_name", "called", "known_as", "identity_name",
            "answers_identity_as", "is_a",
        }
        capability_predicates = {
            "capability", "can", "does", "function", "role", "knows_about",
            "limitation", "architecture", "purpose",
        }

        def _claims_for_ids(claim_ids: list[str]) -> list:
            if not store or not claim_ids:
                return []
            return [c for c in (store.claims.get(cid) for cid in claim_ids) if c is not None]

        def _matching_evidence_ids(frame: str, claim_ids: list[str]) -> list[str]:
            claims = _claims_for_ids(claim_ids)
            if frame in {"user_identity_query", "user_name_query"} and store is not None:
                # Profile lane takes priority for user identity/name queries.
                for slot in ("name", "alias"):
                    value = store.profile.get(slot)
                    if value:
                        for claim in store.claims.find_by_subject("user"):
                            if claim.domain == "profile" and claim.predicate == f"user.{slot}":
                                return [claim.id]
            if not claims:
                return []
            if frame in {"self_identity_query", "user_identity_query", "user_name_query"}:
                return [c.id for c in claims if c.predicate in identity_predicates]
            if frame in {"self_capability_query", "self_knowledge_query"}:
                return [c.id for c in claims if c.predicate in capability_predicates]
            return [c.id for c in claims]

        self_id = getattr(kernel.self_view, "self_id", "")
        def _targets_self(proc: dict[str, Any]) -> bool:
            participants = proc.get("participants", []) or []
            return any(p.get("entity_id") == self_id and p.get("role") == "target" for p in participants)

        matched_self_frame = next(
            (
                p.get("frame_key", "")
                for p in graph.processes
                if p.get("frame_key", "") in self_query_frames and _targets_self(p)
            ),
            "",
        )
        if matched_self_frame:
            matching_claim_ids = _matching_evidence_ids(matched_self_frame, selected_claim_ids)
            if matched_self_frame == "self_identity_query" and matching_claim_ids:
                claims_by_id = {c.id: c for c in _claims_for_ids(matching_claim_ids)}
                for preferred_predicate in ("answers_identity_as", "name", "is_a"):
                    preferred = [
                        cid for cid in matching_claim_ids
                        if claims_by_id.get(cid) and claims_by_id[cid].predicate == preferred_predicate
                    ]
                    if preferred:
                        matching_claim_ids = preferred[:1]
                        break
            if matched_self_frame == "self_capability_query" and matching_claim_ids:
                claims_by_id = {c.id: c for c in _claims_for_ids(matching_claim_ids)}
                preferred = [
                    cid for cid in matching_claim_ids
                    if claims_by_id.get(cid) and claims_by_id[cid].predicate in {"does", "capability"}
                ]
                if preferred:
                    matching_claim_ids = preferred[:4]
            if matching_claim_ids:
                intent = matched_self_frame.replace("_query", "")
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        selected_claim_ids=matching_claim_ids,
                        selected_model_ids=selected_model_ids,
                        execution_allowed=True,
                        confidence=min(0.9, graph.confidence),
                        params={"intent": intent},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=min(0.9, graph.confidence),
                    reason=f"self query ({matched_self_frame}) answered from verified claims",
                )
            else:
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=0.7,
                        params={"intent": "self_query_unknown"},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason=f"self query ({matched_self_frame}) without matching evidence",
                )

        matched_user_frame = next(
            (p.get("frame_key", "") for p in graph.processes if p.get("frame_key", "") in user_query_frames),
            "",
        )
        if matched_user_frame:
            matching_claim_ids = _matching_evidence_ids(matched_user_frame, selected_claim_ids)
            if matching_claim_ids:
                matching_claim_ids = matching_claim_ids[:1]
            if matching_claim_ids:
                intent = "user_identity" if matched_user_frame == "user_identity_query" else "user_name"
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        selected_claim_ids=matching_claim_ids,
                        selected_model_ids=selected_model_ids,
                        execution_allowed=True,
                        confidence=min(0.9, graph.confidence),
                        params={"intent": intent},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=min(0.9, graph.confidence),
                    reason=f"user query ({matched_user_frame}) answered from verified claims",
                )
            else:
                intent = "user_identity_unknown" if matched_user_frame == "user_identity_query" else "user_name_unknown"
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        selected_model_ids=selected_model_ids,
                        execution_allowed=True,
                        confidence=0.7,
                        params={"intent": intent},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason=f"user query ({matched_user_frame}) without matching evidence",
                )

        if "assistance_request" in graph_frame_keys:
            if self._has_scoped_assistance_content(input_text):
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.72,
                        params={"intent": "general_conversation", "response_mode": "general_conversation"},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.72,
                    reason="assistance request includes task scope",
                )
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    execution_allowed=True,
                    confidence=0.72,
                    params={
                        "intent": "assistance_request",
                        "question": "What would you like help with?",
                    },
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.72,
                reason="assistance request needs task scope",
            )

        if "playful_acknowledgment" in graph_frame_keys:
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    execution_allowed=True,
                    confidence=0.7,
                    params={"intent": "playful_acknowledgment"},
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.7,
                reason="playful acknowledgment handled conversationally",
            )

        # General conversational question fallback: when the user asks a real question
        # but no stored claim or model covers it, answer conversationally rather than
        # immediately asking for clarification. This keeps the assistant useful for
        # open-domain chat and prevents the "Could you elaborate?" loop.
        if is_question and not selected_claim_ids and not graph.claim_candidates:
            if self._is_fresh_world_query(input_text):
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=0.8,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.8,
                    reason="fresh-world query requires live retrieval",
                )
            intent = self._classify_general_question(input_text, graph, kernel)
            if intent:
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.7,
                        params={"intent": intent, "response_mode": "general_conversation"},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason=f"general conversational question (intent={intent})",
                )

        # If user is asking for clarification and there are no claim candidates,
        # route to ask even if claims were retrieved (e.g. "how do you mean?"
        # retrieves self_main claims via "you" pronoun but is a question, not a query)
        if not graph.claim_candidates:
            for proc in graph.processes:
                if proc.get("frame_key") in _QUESTION_FRAMES:
                    return DecisionPacket(
                        action_kind="ask",
                        action_plan=ActionPlan(
                            action_kind="ask",
                            execution_allowed=True,
                            confidence=0.7,
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=0.7,
                        reason="graph indicates clarification needed",
                    )

        if selected_claim_ids:
            # Gate: only answer from claims when the conversation act requires evidence
            # or is unknown. Social/creative/repair turns must not trigger evidence answers.
            if conversation_act and not conversation_act.requires_evidence and conversation_act.act_type != "unknown":
                pass  # fall through to non-evidence handling below
            else:
                base_confidence = 0.8
                graph_confidence = getattr(graph, 'confidence', 0.5)
                confidence = min(0.95, base_confidence * (0.5 + 0.5 * graph_confidence))

                if predictions:
                    avg_pred = sum(p.get("confidence", 0) for p in predictions) / max(len(predictions), 1)
                    if avg_pred > 0.5:
                        confidence = min(0.95, confidence * 1.15)
                    else:
                        confidence = max(0.4, confidence * 0.85)

                if graph.temporal_edges:
                    confidence = min(0.95, confidence * 1.1)

                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        selected_claim_ids=selected_claim_ids,
                        selected_model_ids=selected_model_ids,
                        execution_allowed=True,
                        confidence=confidence,
                        params={"intent": "evidence_answer", "response_mode": "evidence_answer"},
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=confidence,
                    reason="selected evidence available with graph confidence {:.2f}".format(graph_confidence),
                )

        for proc in graph.processes:
            if proc.get("frame_key") in _QUESTION_FRAMES:
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=0.7,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason="graph indicates clarification needed",
                )

        if observation_semantics and observation_semantics.confidence >= 0.5:
            speech_act = observation_semantics.speech_act
            if speech_act == "greeting":
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.7,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.7,
                    reason=f"speech_act greeting fallback (conf={observation_semantics.confidence:.2f})",
                )
            if speech_act == "acknowledgment":
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.65,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.65,
                    reason=f"speech_act acknowledgment fallback (conf={observation_semantics.confidence:.2f})",
                )
            if speech_act == "clarification":
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=0.65,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.65,
                    reason=f"speech_act clarification fallback (conf={observation_semantics.confidence:.2f})",
                )
            if speech_act == "exit":
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=0.9,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=0.9,
                    reason=f"speech_act exit fallback (conf={observation_semantics.confidence:.2f})",
                )

        if context_inference and context_inference.confidence >= 0.5:
            if context_inference.frame_id in ("greeting", "session_opening", "acknowledgment"):
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=context_inference.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=context_inference.confidence,
                    reason=f"context frame {context_inference.frame_id} fallback",
                )
            if context_inference.frame_id == "clarification":
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=context_inference.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=context_inference.confidence,
                    reason="context frame clarification fallback",
                )
            if context_inference.frame_id == "session_exit":
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=context_inference.confidence,
                        risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                    ),
                    confidence=context_inference.confidence,
                    reason="context frame session_exit fallback",
                )

        # Short input fallback: only when the graph has no meaningful signal.
        if input_text and len(input_text.strip()) <= 3 and graph.confidence < 0.3:
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    execution_allowed=True,
                    confidence=0.7,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.7,
                reason="short input with low graph confidence — clarification needed",
            )

        return DecisionPacket(
            action_kind="abstain",
            action_plan=ActionPlan(
                action_kind="abstain",
                selected_model_ids=selected_model_ids,
                execution_allowed=False,
                confidence=max(0.4, min(0.6, graph.confidence)),
                risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
            ),
            confidence=max(0.4, min(0.6, graph.confidence)),
            reason="insufficient graph-grounded evidence (confidence={:.2f})".format(graph.confidence),
        )

    def _is_pure_acknowledgment(self, input_text: str) -> bool:
        """Return True if the input is only an acknowledgment word/punctuation.

        Phrases are loaded from cemm/data/uol_semantics.json so they can be
        language-specific without hardcoding English surface forms.
        """
        text = input_text.lower().strip("?.,!;:\"'()[]{} ")
        return text in self._pure_acknowledgment_phrases

    def _has_scoped_assistance_content(self, input_text: str) -> bool:
        import re

        tokens = re.findall(r"[a-z0-9']+", input_text.lower())
        joined = " ".join(tokens)
        assistance_cues = _CUE_SETS.get("assistance_marker", set())
        stopword_cues = _CUE_SETS.get("stopword", set())
        for marker in assistance_cues:
            marker_norm = " ".join(re.findall(r"[a-z0-9']+", marker.lower()))
            if marker_norm in joined:
                tail = joined[joined.index(marker_norm) + len(marker_norm):]
                tail_tokens = [
                    t for t in re.findall(r"[a-z0-9']+", tail)
                    if t not in stopword_cues
                ]
                if len(tail_tokens) >= 2:
                    return True
        return False

    def _is_fresh_world_query(self, input_text: str) -> bool:
        import re

        normalized = " ".join(re.findall(r"[a-z0-9']+", input_text.lower()))
        tokens = set(normalized.split())
        fresh_markers = _CUE_SETS.get("fresh_world_marker", set())
        question_starter_cues = _CUE_SETS.get("question_starter", set())
        if not (tokens & fresh_markers):
            return False
        text_tokens = normalized.split()
        first_token = text_tokens[0] if text_tokens else ""
        return (
            first_token in question_starter_cues
            or any(normalized.startswith(qs) for qs in question_starter_cues if len(qs) > 2)
            or input_text.strip().endswith("?")
        )

    def _classify_general_question(
        self, input_text: str, graph: SemanticEventGraph, kernel: ContextKernel,
    ) -> str:
        """Map an open-domain question to a conversational answer intent.

        Intent classification is data-driven: it prefers UOL semantic frames
        already present in the SEG, and falls back to a UOLMapper match against
        the language-specific aliases in cemm/data/uol_semantics.json.
        """
        frame_to_intent = {
            "story_request": "story_request",
            "food_recommendation_request": "food_recommendation",
            "recommendation_request": "recommendation_request",
            "self_capability_query": "self_capability",
        }
        graph_frame_keys = {p.get("frame_key", "") for p in graph.processes}
        for frame_key, intent in frame_to_intent.items():
            if frame_key in graph_frame_keys:
                return intent

        if self._uol_mapper is not None:
            uol_atoms = self._uol_mapper.map_signal(input_text, kernel)
            atom_frame_keys = {
                atom.frame_key for atom in uol_atoms
                if hasattr(atom, "frame_key")
            }
            for frame_key, intent in frame_to_intent.items():
                if frame_key in atom_frame_keys:
                    return intent

        return "general_conversation"

    def _detect_command_intent(
        self,
        input_text: str,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        selected_claim_ids: list[str] | None = None,
        predictions: list[dict[str, Any]] | None = None,
        missing_slots: list[str] | None = None,
        is_question: bool = False,
    ) -> DecisionPacket | None:
        frame_keys = {p.get("frame_key", "") for p in graph.processes}
        has_claims = bool(selected_claim_ids)

        if "session_exit" in frame_keys:
            return DecisionPacket(
                action_kind="abstain",
                action_plan=ActionPlan(
                    action_kind="abstain",
                    execution_allowed=False,
                    confidence=0.95,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.95,
                reason="session exit detected in SEG processes",
            )

        # Explicit commands take priority over conversational intents.
        # A remember command is only valid when the surface is not a question.
        # Question detection is language-agnostic: terminal "?" or question frames
        # in the SEG (ask_question, request_clarification, unknown_intent).
        if "command_remember" in frame_keys and not is_question:
            return DecisionPacket(
                action_kind="remember",
                action_plan=ActionPlan(
                    action_kind="remember",
                    execution_allowed=True,
                    confidence=0.85,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.85,
                reason="remember command detected in SEG processes",
            )

        if "command_reflect" in frame_keys:
            return DecisionPacket(
                action_kind="reflect",
                action_plan=ActionPlan(
                    action_kind="reflect",
                    execution_allowed=True,
                    confidence=0.8,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.8,
                reason="reflect command detected in SEG processes",
            )

        if "command_retrieve" in frame_keys:
            return DecisionPacket(
                action_kind="retrieve",
                action_plan=ActionPlan(
                    action_kind="retrieve",
                    execution_allowed=True,
                    confidence=0.8,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.8,
                reason="retrieve command detected in SEG processes",
            )

        if "assistance_request" in frame_keys:
            return None

        # Conversational intents after commands — only when no claims selected
        if not has_claims and "greeting" in frame_keys:
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    execution_allowed=True,
                    confidence=0.75,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.75,
                reason="greeting detected in SEG processes",
            )

        if not has_claims and "acknowledgment" in frame_keys:
            # Don't let a trailing "OK" or "sure" override a content request like
            # "OK can you tell me stories?" or "OK what should I eat?". If the rest
            # of the sentence is not just acknowledgment, classify the content.
            if not self._is_pure_acknowledgment(input_text):
                content_intent = self._classify_general_question(input_text, graph, kernel)
                if content_intent:
                    return DecisionPacket(
                        action_kind="answer",
                        action_plan=ActionPlan(
                            action_kind="answer",
                            execution_allowed=True,
                            confidence=0.7,
                            params={"intent": content_intent},
                            risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                        ),
                        confidence=0.7,
                        reason=f"acknowledgment + content request (intent={content_intent})",
                    )
            return DecisionPacket(
                action_kind="answer",
                action_plan=ActionPlan(
                    action_kind="answer",
                    execution_allowed=True,
                    confidence=0.7,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.7,
                reason="acknowledgment detected in SEG processes",
            )

        if not has_claims and "discourse_marker" in frame_keys:
            # Discourse markers like "oh", "well" often precede real content
            # If no other intent detected, treat as conversational
            return DecisionPacket(
                action_kind="ask",
                action_plan=ActionPlan(
                    action_kind="ask",
                    execution_allowed=True,
                    confidence=0.6,
                    risk=self._estimate_risk(graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions),
                ),
                confidence=0.6,
                reason="discourse marker — clarification needed",
            )

        return None

    def _detect_teaching_intent(
        self,
        graph: SemanticEventGraph,
        input_text: str,
    ) -> DecisionPacket | None:
        """Route surface teaching patterns (definition, alias, correction) to learning actions."""
        for proc in graph.processes:
            frame_key = proc.get("frame_key", "")
            params = proc.get("params", {})
            if frame_key == "command_alias_teaching":
                return DecisionPacket(
                    action_kind="learn_command_alias",
                    action_plan=ActionPlan(
                        action_kind="learn_command_alias",
                        execution_allowed=True,
                        confidence=proc.get("confidence", 0.6),
                        params={"teaching_event": params},
                    ),
                    confidence=proc.get("confidence", 0.6),
                    reason="user defined a command alias",
                )
            if frame_key == "definition_teaching":
                return DecisionPacket(
                    action_kind="learn_lexeme",
                    action_plan=ActionPlan(
                        action_kind="learn_lexeme",
                        execution_allowed=True,
                        confidence=proc.get("confidence", 0.6),
                        params={"teaching_event": params},
                    ),
                    confidence=proc.get("confidence", 0.6),
                    reason="user defined a word or alias",
                )
            if frame_key == "correction":
                return DecisionPacket(
                    action_kind="learn_correction",
                    action_plan=ActionPlan(
                        action_kind="learn_correction",
                        execution_allowed=True,
                        confidence=proc.get("confidence", 0.7),
                        params={"teaching_event": params},
                    ),
                    confidence=proc.get("confidence", 0.7),
                    reason="user corrected a previous meaning",
                )
        # Unknown lexeme gap: only ask for meaning when the unknown term is clearly the
        # focus of the question (e.g., "what does 'zibble' mean?"), not when a common
        # word is embedded in a general question. This prevents the "Could you elaborate?"
        # loop caused by treating everyday words as teachable unknowns.
        if input_text.endswith("?"):
            known_frames = {p.get("frame_key", "") for p in graph.processes}
            if known_frames & {
                "self_identity_query", "self_capability_query", "self_knowledge_query",
                "user_identity_query", "user_name_query",
            }:
                return None
            for entity in graph.entity_refs:
                if entity.get("role") == "unknown_lexeme":
                    _punct = '.,!?;:"' + "'()[]{}"
                    term = entity.get("entity_id", "").strip(_punct).lower()
                    if not term or len(term) <= 3:
                        continue
                    if self._is_unknown_term_focus(input_text, term):
                        return DecisionPacket(
                            action_kind="ask",
                            action_plan=ActionPlan(
                                action_kind="ask",
                                execution_allowed=True,
                                confidence=0.6,
                                params={"question": f"What do you mean by '{term}'?"},
                            ),
                            confidence=0.6,
                            reason=f"ask meaning of unknown term '{term}'",
                        )
        return None

    def _is_unknown_term_focus(self, input_text: str, term: str) -> bool:
        """Return True if the input is explicitly asking about the term itself."""
        text_lower = input_text.lower()
        q = chr(34)
        sq = chr(39)
        patterns = [
            f"what does {term} mean",
            f"what does {q}{term}{q} mean",
            f"what does {sq}{term}{sq} mean",
            f"what do you mean by {term}",
            f"what do you mean by {q}{term}{q}",
            f"what do you mean by {sq}{term}{sq}",
            f"what is {term}",
            f"what is {q}{term}{q}",
            f"what is {sq}{term}{sq}",
            f"what\'s {term}",
            f"what\'s {q}{term}{q}",
            f"what\'s {sq}{term}{sq}",
            f"who is {term}",
            f"who\'s {term}",
            f"define {term}",
            f"define {q}{term}{q}",
            f"define {sq}{term}{sq}",
            f"meaning of {term}",
            f"meaning of {q}{term}{q}",
            f"meaning of {sq}{term}{sq}",
            f"{term} means",
            f"{term} is a",
            f"{term} is the",
        ]
        for pattern in patterns:
            if pattern in text_lower:
                return True
        words = text_lower.strip("?").split()
        if len(words) <= 3 and term in words:
            return True
        return False

    def _estimate_risk(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        confidence: float | None = None,
        missing_slots: list[str] | None = None,
        predictions: list[dict[str, Any]] | None = None,
    ) -> float:
        if confidence is None:
            confidence = graph.confidence
        risk = (1.0 - confidence) * 0.5
        if missing_slots:
            risk += min(0.3, len(missing_slots) * 0.1)
        if predictions:
            risk += min(0.3, len(predictions) * 0.1)
        uncertainty = getattr(kernel.self_view, "uncertainty", 0.0)
        if uncertainty > 0.5:
            risk += (uncertainty - 0.5) * 0.2
        return min(1.0, max(0.0, risk))

    def _make_answer_packet(
        self,
        intent: str,
        response_mode: str,
        confidence: float,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        missing_slots: list[str] | None = None,
        predictions: list[dict[str, Any]] | None = None,
        selected_claim_ids: list[str] | None = None,
        selected_model_ids: list[str] | None = None,
        reason: str = "",
    ) -> DecisionPacket:
        """Build a standard answer DecisionPacket with intent and response_mode params."""
        params: dict[str, Any] = {"intent": intent, "response_mode": response_mode}
        return DecisionPacket(
            action_kind="answer",
            action_plan=ActionPlan(
                action_kind="answer",
                selected_claim_ids=selected_claim_ids or [],
                selected_model_ids=selected_model_ids or [],
                execution_allowed=True,
                confidence=confidence,
                params=params,
                risk=self._estimate_risk(
                    graph=graph, kernel=kernel, missing_slots=missing_slots, predictions=predictions,
                ),
            ),
            confidence=confidence,
            reason=reason,
        )
