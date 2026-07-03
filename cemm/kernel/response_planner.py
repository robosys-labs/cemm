"""ResponsePlanner — v3.3 capability-aware response planning.

Produces a ResponsePlan that specifies the response mode, intent, template key,
and capability constraints for the current turn. This replaces the implicit
response mode derivation scattered across DecisionRouter and __main__.py.

The ResponsePlanner consults:
- ActResolutionPlan (authoritative routing signal)
- ConversationActPacket (act types and metadata)
- Capability model (what the system can and cannot do)
- Safety frame (override to safety_response)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ResponsePlan:
    """Planned response specification for the current turn."""
    response_mode: str = "general_conversation"
    intent: str = ""
    template_key: str = "general_conversation"
    capability_scope: str = ""  # what capability domain this response draws from
    requires_evidence: bool = False
    allows_memory_write: bool = False
    is_simple_answer: bool = True
    capability_confidence: float = 0.5
    fallback_template: str = "general_conversation"
    variables: dict[str, Any] = field(default_factory=dict)
    selected_claim_ids: list[str] = field(default_factory=list)
    verification_policy: str = "normal"  # normal, strict, lenient
    metadata: dict[str, Any] = field(default_factory=dict)


_CAPABILITY_MODEL_PATH = Path(__file__).parents[1] / "data" / "capability_model.json"


def _load_capability_model() -> dict[str, Any]:
    if not _CAPABILITY_MODEL_PATH.exists():
        return {}
    return json.loads(_CAPABILITY_MODEL_PATH.read_text(encoding="utf-8"))


_CAPABILITY_MODEL = _load_capability_model()


class ResponsePlanner:
    """Plans the response specification from act resolution and capability model."""

    def __init__(self) -> None:
        self._capability_model = _CAPABILITY_MODEL
        self._act_type_metadata = self._capability_model.get("act_type_metadata", {})
        self._capability_domains = self._capability_model.get("capability_domains", {})
        self._response_modes = self._capability_model.get("response_modes", {})

    def plan(
        self,
        conversation_act: Any | None = None,
        act_resolution_plan: Any | None = None,
        safety_frame: Any | None = None,
        has_evidence: bool = False,
    ) -> ResponsePlan:
        """Produce a ResponsePlan for the current turn."""
        # Safety override
        if safety_frame and safety_frame.category != "none":
            return ResponsePlan(
                response_mode="safety_response",
                intent="safety_deescalation",
                template_key="safety_deescalation",
                capability_scope="safety",
                requires_evidence=False,
                allows_memory_write=False,
                is_simple_answer=True,
                capability_confidence=0.95,
                metadata={"safety_category": safety_frame.category},
            )

        # Try act resolution plan first (authoritative)
        if act_resolution_plan and act_resolution_plan.answer_tasks:
            task = act_resolution_plan.answer_tasks[0]
            mode = task.response_mode or "general_conversation"
            intent = task.intent or ""
            template = self._template_for_mode(mode, intent)
            cap_scope = self._capability_scope_for_mode(mode)
            cap_conf = self._capability_confidence_for_mode(mode, has_evidence)
            return ResponsePlan(
                response_mode=mode,
                intent=intent,
                template_key=template,
                capability_scope=cap_scope,
                requires_evidence=self._mode_requires_evidence(mode),
                allows_memory_write=self._mode_allows_memory_write(mode),
                is_simple_answer=self._mode_is_simple(mode),
                capability_confidence=cap_conf,
                metadata={"source": "act_resolution_plan"},
            )

        # Fall back to conversation act metadata
        if conversation_act:
            primary_act = conversation_act.primary if hasattr(conversation_act, "primary") else None
            if primary_act:
                act_type = primary_act.act_type
                meta = self._act_type_metadata.get(act_type, {})
                mode = meta.get("response_mode", "general_conversation")
                intent = meta.get("default_template", "general_conversation")
                template = meta.get("default_template", "general_conversation")
                cap_scope = self._capability_scope_for_mode(mode)
                cap_conf = self._capability_confidence_for_mode(mode, has_evidence)
                return ResponsePlan(
                    response_mode=mode,
                    intent=intent,
                    template_key=template,
                    capability_scope=cap_scope,
                    requires_evidence=meta.get("requires_evidence", False),
                    allows_memory_write=meta.get("allows_memory_write", False),
                    is_simple_answer=meta.get("simple_answer", True),
                    capability_confidence=cap_conf,
                    metadata={"source": "conversation_act", "act_type": act_type},
                )

        # Default fallback
        return ResponsePlan(
            response_mode="general_conversation",
            intent="general_conversation",
            template_key="general_conversation",
            capability_scope="conversation",
            capability_confidence=0.4,
            metadata={"source": "fallback"},
        )

    def _template_for_mode(self, mode: str, intent: str) -> str:
        """Resolve template key from response mode and intent."""
        mode_info = self._response_modes.get(mode, {})
        # Check for per-intent template mapping in response mode config
        templates = mode_info.get("templates", {})
        if intent and intent in templates:
            return templates[intent]
        # Fall back to intent itself as template key (covers self_category, concept_unknown, etc.)
        if intent and intent != "general_conversation":
            return intent
        return mode_info.get("default_template", "general_conversation")

    def _capability_scope_for_mode(self, mode: str) -> str:
        """Map response mode to capability domain."""
        mode_info = self._response_modes.get(mode, {})
        return mode_info.get("capability_scope", "conversation")

    def _capability_confidence_for_mode(self, mode: str, has_evidence: bool) -> float:
        """Estimate confidence for this response mode."""
        mode_info = self._response_modes.get(mode, {})
        base = mode_info.get("base_confidence", 0.5)
        if mode_info.get("requires_evidence") and not has_evidence:
            base *= 0.5
        return min(1.0, base)

    def _mode_requires_evidence(self, mode: str) -> bool:
        return self._response_modes.get(mode, {}).get("requires_evidence", False)

    def _mode_allows_memory_write(self, mode: str) -> bool:
        return self._response_modes.get(mode, {}).get("allows_memory_write", False)

    def _mode_is_simple(self, mode: str) -> bool:
        return self._response_modes.get(mode, {}).get("simple_answer", True)
