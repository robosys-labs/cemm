from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..registry.act_type_policy import (
    requires_evidence as _requires_evidence,
    allows_memory_write as _allows_memory_write,
    is_social as _is_social,
    is_creative as _is_creative,
    is_repair as _is_repair,
    is_evaluative as _is_evaluative,
    get_response_mode as _get_response_mode,
)


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
        return _requires_evidence(self.act_type)

    @property
    def allows_memory_write(self) -> bool:
        return _allows_memory_write(self.act_type)

    @property
    def is_social(self) -> bool:
        return _is_social(self.act_type)

    @property
    def is_creative(self) -> bool:
        return _is_creative(self.act_type)

    @property
    def is_repair(self) -> bool:
        return _is_repair(self.act_type)

    @property
    def is_evaluative(self) -> bool:
        return _is_evaluative(self.act_type)

    @property
    def response_mode(self) -> str:
        """Map act_type to a response mode for the realizer.

        Delegates to the registry-driven act_type_policy module so
        adding a new act type only requires editing uol_semantics.json.
        """
        return _get_response_mode(self.act_type)


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
