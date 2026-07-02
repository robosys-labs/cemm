from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationAct:
    """Pragmatic classification of a conversational turn.

    Produced before retrieval so downstream stages know what kind of
    response is needed before fetching evidence.
    """
    act_type: str = "unknown"
    target: str = ""
    topic: str = ""
    polarity: str = "neutral"
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
        )

    @property
    def is_social(self) -> bool:
        return self.act_type in (
            "greeting",
            "phatic_checkin",
            "acknowledgment",
            "playful_acknowledgment",
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
        )

    @property
    def response_mode(self) -> str:
        """Map act_type to a response mode for the realizer."""
        mode_map = {
            "greeting": "social_response",
            "phatic_checkin": "social_response",
            "acknowledgment": "social_response",
            "playful_acknowledgment": "social_response",
            "story_request": "creative_response",
            "creative_request": "creative_response",
            "confusion_repair": "repair_response",
            "playful_repair": "repair_response",
            "self_correction": "repair_response",
            "simplification_request": "repair_response",
            "frustration_signal": "repair_response",
            "capability_query": "capability_summary",
            "self_capability_query": "capability_summary",
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
            "command": "tool_action",
            "tool_request": "tool_action",
            "exit": "abstain",
            "unknown": "general_conversation",
        }
        return mode_map.get(self.act_type, "general_conversation")
