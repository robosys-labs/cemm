from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationAct:
    """Pragmatic classification of a single conversational intent within a turn.

    A turn may contain multiple acts (e.g. "I'm good, what can you do?"
    is both a social_status_report and a self_capability_query).
    See ConversationActPacket for multi-act packaging.
    """
    act_type: str = "unknown"
    target: str = ""
    topic: str = ""
    polarity: str = "neutral"  # neutral, positive, negative, skeptical
    intensity: float = 0.5
    confidence: float = 0.5
    evidence_spans: list[str] = field(default_factory=list)
    entity_mentions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def requires_evidence(self) -> bool:
        return self.act_type in (
            "evidence_query",
            "memory_query",
            "self_capability_query",
            "self_capability_skeptical_query",
            "self_identity_query",
            "self_knowledge_query",
            "user_identity_query",
            "user_name_query",
            "open_domain_entity_query",
        )

    @property
    def allows_memory_write(self) -> bool:
        return self.act_type in (
            "claim_assertion",
            "preference_assertion",
            "explicit_remember",
            "definition_teaching",
            "command_alias_teaching",
            "user_state_report",
        )

    @property
    def is_social(self) -> bool:
        return self.act_type in (
            "greeting",
            "phatic_checkin",
            "acknowledgment",
            "playful_acknowledgment",
            "user_state_report",
            "chat_mode_statement",
        )

    @property
    def is_creative(self) -> bool:
        return self.act_type in (
            "story_request",
            "creative_request",
        )

    @property
    def is_repair(self) -> bool:
        return self.act_type in (
            "confusion_repair",
            "playful_repair",
            "self_correction",
            "simplification_request",
            "teachability_complaint",
        )

    @property
    def is_evaluative(self) -> bool:
        return self.act_type in (
            "assistant_evaluation",
            "meta_critique",
            "self_capability_skeptical_query",
        )

    @property
    def response_mode(self) -> str:
        """Map act_type to a response mode for the realizer."""
        mode_map = {
            "greeting": "social_response",
            "phatic_checkin": "social_response",
            "acknowledgment": "social_response",
            "playful_acknowledgment": "social_response",
            "user_state_report": "social_response",
            "chat_mode_statement": "social_response",
            "story_request": "creative_response",
            "creative_request": "creative_response",
            "confusion_repair": "repair_response",
            "playful_repair": "repair_response",
            "self_correction": "repair_response",
            "simplification_request": "repair_response",
            "frustration_signal": "repair_response",
            "teachability_complaint": "repair_response",
            "capability_query": "capability_summary",
            "self_capability_query": "capability_summary",
            "self_capability_skeptical_query": "capability_summary",
            "self_identity_query": "evidence_answer",
            "self_knowledge_query": "evidence_answer",
            "user_identity_query": "evidence_answer",
            "user_name_query": "evidence_answer",
            "memory_query": "evidence_answer",
            "evidence_query": "evidence_answer",
            "open_domain_entity_query": "unknown_entity_response",
            "teaching_offer": "teaching_prompt",
            "claim_assertion": "memory_write",
            "preference_assertion": "memory_write",
            "explicit_remember": "memory_write",
            "definition_teaching": "teaching_prompt",
            "command_alias_teaching": "teaching_prompt",
            "assistant_evaluation": "evaluation_response",
            "meta_question_intent": "social_response",
            "meta_critique": "meta_response",
            "command": "tool_action",
            "tool_request": "tool_action",
            "exit": "abstain",
            "unknown": "general_conversation",
        }
        return mode_map.get(self.act_type, "general_conversation")


@dataclass
class ConversationActPacket:
    """Multi-act container for a single conversational turn.

    A turn like "I'm good, just trying to see what you can do" contains
    both a social status report and a capability query. The packet
    preserves the primary act (highest confidence) plus secondary acts,
    a discourse relation between them, and optional linkage to the
    pending assistant question for contextual resolution.

    The packet is the control spine of the runtime: retrieval, decision,
    and realization all consult the packet rather than a single act.
    """
    primary: ConversationAct = field(default_factory=ConversationAct)
    secondary: list[ConversationAct] = field(default_factory=list)
    discourse_relation: str = "none"  # none, elaboration, contrast, sequence, answer_to_pending
    expected_response_to_previous: str = ""  # set when answering a pending assistant question
    raw_text: str = ""
    diagnostics: dict = field(default_factory=dict)

    @property
    def requires_evidence(self) -> bool:
        if self.primary.requires_evidence:
            return True
        return any(act.requires_evidence for act in self.secondary)

    @property
    def allows_memory_write(self) -> bool:
        if self.primary.allows_memory_write:
            return True
        return any(act.allows_memory_write for act in self.secondary)

    @property
    def is_social(self) -> bool:
        if self.primary.is_social:
            return True
        return any(act.is_social for act in self.secondary)

    @property
    def is_creative(self) -> bool:
        if self.primary.is_creative:
            return True
        return any(act.is_creative for act in self.secondary)

    @property
    def is_repair(self) -> bool:
        if self.primary.is_repair:
            return True
        return any(act.is_repair for act in self.secondary)

    @property
    def is_evaluative(self) -> bool:
        if self.primary.is_evaluative:
            return True
        return any(act.is_evaluative for act in self.secondary)

    @property
    def response_mode(self) -> str:
        return self.primary.response_mode

    @property
    def act_type(self) -> str:
        """Duck-type compatibility: delegates to primary act."""
        return self.primary.act_type

    @property
    def confidence(self) -> float:
        """Duck-type compatibility: delegates to primary act."""
        return self.primary.confidence

    @property
    def all_acts(self) -> list[ConversationAct]:
        return [self.primary] + self.secondary

    @property
    def act_types(self) -> list[str]:
        return [a.act_type for a in self.all_acts]

    def has_act(self, act_type: str) -> bool:
        return any(a.act_type == act_type for a in self.all_acts)

    def get_act(self, act_type: str) -> ConversationAct | None:
        for a in self.all_acts:
            if a.act_type == act_type:
                return a
        return None
