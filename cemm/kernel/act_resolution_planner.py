"""ActResolutionPlanner - turn multi-act packets into runtime obligations.

ConversationActPacket preserves multiple pragmatic acts, but downstream code
often still asks for one primary act. This planner makes all acts operational by
turning them into typed tasks:

* reply obligations
* memory update plans
* answer tasks
* safety tasks
* ignored/deferred acts

It is intentionally small and deterministic first. The output is a good
supervised target for a later Pi-friendly decision model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..registry.act_type_policy import get_response_mode
from ..types.conversation_act import ConversationAct, ConversationActPacket
from ..types.meaning_percept import MeaningPerceptPacket, SafetyFrame, SituationFrame
from .entity_fact_extractor import EntityFactCandidate


@dataclass
class ReplyObligation:
    """A user-facing response obligation created by one act."""

    act_type: str
    response_mode: str
    priority: int
    intent: str
    reason: str = ""
    requires_evidence: bool = False
    allowed_creativity: bool = False
    confidence: float = 0.5


@dataclass
class MemoryUpdatePlan:
    """A proposed memory write, not an executed mutation."""

    write_kind: str
    candidates: list[EntityFactCandidate] = field(default_factory=list)
    act_type: str = ""
    permission_scope: str = "public"
    confidence: float = 0.5
    reason: str = ""


@dataclass
class AnswerTask:
    """Internal answer task produced by act resolution."""

    response_mode: str
    intent: str
    selected_act_type: str
    retrieval_mode: str = "none"
    params: dict[str, Any] = field(default_factory=dict)
    priority: int = 50
    confidence: float = 0.5


@dataclass
class SafetyTask:
    """Safety task that can override normal answer behavior."""

    category: str
    response_mode: str
    severity: str
    must_not_do: list[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class IgnoredAct:
    """An act intentionally ignored or deferred with a trace reason."""

    act_type: str
    reason: str


@dataclass
class ActResolutionPlan:
    """Operational plan for all acts in one turn."""

    obligations: list[ReplyObligation] = field(default_factory=list)
    memory_updates: list[MemoryUpdatePlan] = field(default_factory=list)
    answer_tasks: list[AnswerTask] = field(default_factory=list)
    safety_tasks: list[SafetyTask] = field(default_factory=list)
    ignored_acts: list[IgnoredAct] = field(default_factory=list)
    selected_response_mode: str = "general_conversation"
    selected_intent: str = "general_conversation"
    requires_retrieval: bool = False
    retrieval_mode: str = "none"
    confidence: float = 0.5


class ActResolutionPlanner:
    """Resolve ConversationActPacket into concrete runtime tasks."""

    _PRIORITY = {
        "self_harm": 100,
        "safety": 95,
        "frustration_signal": 90,
        "confusion_repair": 85,
        "playful_repair": 80,
        "self_capability_query": 75,
        "capability_query": 75,
        "self_identity_query": 72,
        "self_knowledge_query": 72,
        "user_identity_query": 72,
        "user_name_query": 72,
        "open_domain_entity_query": 70,
        "evidence_query": 68,
        "memory_query": 68,
        "teaching_offer": 66,
        "teaching_instruction_query": 71,
        "self_category_query": 73,
        "concept_query": 69,
        "story_request": 62,
        "creative_request": 62,
        "phatic_checkin": 55,
        "greeting": 50,
        "acknowledgment": 35,
        "claim_assertion": 30,
        "preference_assertion": 30,
        "definition_teaching": 30,
        "command_alias_teaching": 30,
    }

    _MEMORY_ACTS = {
        "claim_assertion",
        "preference_assertion",
        "definition_teaching",
        "command_alias_teaching",
        "explicit_remember",
    }

    def plan(
        self,
        conversation_act: ConversationActPacket | None,
        situation: SituationFrame | None = None,
        safety_frame: SafetyFrame | None = None,
        fact_candidates: list[EntityFactCandidate] | None = None,
        meaning_percept: MeaningPerceptPacket | None = None,
        retrieval_plan: Any = None,
    ) -> ActResolutionPlan:
        result = ActResolutionPlan()
        facts = list(fact_candidates or [])

        if safety_frame and safety_frame.category != "none":
            safety_task = SafetyTask(
                category=safety_frame.category,
                response_mode=safety_frame.allowed_response_mode or "safe_info",
                severity=safety_frame.severity,
                must_not_do=list(safety_frame.must_not_do),
                confidence=safety_frame.confidence,
            )
            result.safety_tasks.append(safety_task)
            result.obligations.append(ReplyObligation(
                act_type="safety",
                response_mode=safety_task.response_mode,
                priority=self._PRIORITY["safety"],
                intent=safety_frame.category,
                reason="safety_frame_override",
                confidence=safety_frame.confidence,
            ))

        acts = conversation_act.all_acts if conversation_act else [ConversationAct()]
        for act in acts:
            self._resolve_act(act, result, facts)

        if not result.obligations and not result.memory_updates and facts:
            result.memory_updates.append(MemoryUpdatePlan(
                write_kind="claim",
                candidates=facts,
                act_type="inferred_claim_assertion",
                confidence=sum(c.confidence for c in facts) / len(facts),
                reason="fact_candidates_without_explicit_act",
            ))
            result.obligations.append(ReplyObligation(
                act_type="memory_write",
                response_mode="social_response",
                priority=25,
                intent="remember",
                reason="acknowledge_fact_learning",
                confidence=0.6,
            ))

        self._select_answer_task(result)

        if retrieval_plan is not None:
            result.requires_retrieval = retrieval_plan.mode != "none"
            result.retrieval_mode = retrieval_plan.mode

        return result

    def _resolve_act(
        self,
        act: ConversationAct,
        result: ActResolutionPlan,
        fact_candidates: list[EntityFactCandidate],
    ) -> None:
        act_type = act.act_type
        if act_type == "unknown":
            result.ignored_acts.append(IgnoredAct(act_type=act_type, reason="unknown_act"))
            return

        if act_type in self._MEMORY_ACTS:
            if fact_candidates:
                result.memory_updates.append(MemoryUpdatePlan(
                    write_kind=self._write_kind_for_act(act_type),
                    candidates=fact_candidates,
                    act_type=act_type,
                    confidence=max(act.confidence, self._avg_fact_confidence(fact_candidates)),
                    reason=f"act_type={act_type}",
                ))
                result.obligations.append(ReplyObligation(
                    act_type=act_type,
                    response_mode="social_response",
                    priority=self._PRIORITY.get(act_type, 30),
                    intent="remember",
                    reason=f"memory_act={act_type}",
                    confidence=act.confidence,
                ))
            else:
                result.ignored_acts.append(IgnoredAct(
                    act_type=act_type,
                    reason="memory_act_without_fact_candidates",
                ))
            return

        response_mode = get_response_mode(act_type) or act.response_mode
        priority = self._PRIORITY.get(act_type, 40)
        requires_evidence = act.requires_evidence
        allowed_creativity = act.is_creative
        intent = self._intent_for_act(act_type, response_mode)

        result.obligations.append(ReplyObligation(
            act_type=act_type,
            response_mode=response_mode,
            priority=priority,
            intent=intent,
            reason=f"act_type={act_type}",
            requires_evidence=requires_evidence,
            allowed_creativity=allowed_creativity,
            confidence=act.confidence,
        ))

        result.answer_tasks.append(AnswerTask(
            response_mode=response_mode,
            intent=intent,
            selected_act_type=act_type,
            retrieval_mode="none",
            priority=priority,
            confidence=act.confidence,
        ))

    def _select_answer_task(
        self,
        result: ActResolutionPlan,
    ) -> None:
        if not result.obligations:
            result.selected_response_mode = "general_conversation"
            result.selected_intent = "general_conversation"
            result.confidence = 0.5
            return

        result.obligations.sort(key=lambda o: (o.priority, o.confidence), reverse=True)
        selected = result.obligations[0]
        result.selected_response_mode = selected.response_mode
        result.selected_intent = selected.intent
        result.confidence = selected.confidence

        result.answer_tasks.sort(key=lambda t: (t.priority, t.confidence), reverse=True)

    def _write_kind_for_act(self, act_type: str) -> str:
        if act_type == "preference_assertion":
            return "preference"
        if act_type in {"definition_teaching", "command_alias_teaching"}:
            return "lexeme_or_model"
        return "claim"

    def _intent_for_act(self, act_type: str, response_mode: str) -> str:
        if act_type == "teaching_instruction_query":
            return "teaching_instruction"
        if act_type == "self_category_query":
            return "self_category"
        if act_type == "concept_query":
            return "concept_unknown"
        if response_mode == "capability_summary":
            return "capability_summary"
        if response_mode == "unknown_entity_response":
            return "unknown_entity_response"
        if response_mode == "teaching_prompt":
            return "teaching_offer"
        if act_type == "frustration_signal":
            return "frustration_response"
        return act_type

    def _avg_fact_confidence(self, facts: list[EntityFactCandidate]) -> float:
        if not facts:
            return 0.5
        return sum(f.confidence for f in facts) / len(facts)
