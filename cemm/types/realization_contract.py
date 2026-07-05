from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnswerVerification:
    supported: bool = False
    verification_type: str = "none"
    confidence: float = 0.0
    unsupported_spans: list[str] = field(default_factory=list)
    uncertainty_reason: str = ""


@dataclass
class RealizationSlot:
    slot_key: str
    slot_kind: str
    value: str
    source_binding_id: str = ""
    source_atom_id: str = ""
    source_relation_id: str = ""
    source_record_id: str = ""
    confidence: float = 0.5


@dataclass
class RealizationContract:
    contract_id: str = ""
    source_obligation_id: str = ""
    source_binding_id: str = ""
    response_mode: str = "general_conversation"
    intent: str = ""
    template_key: str = ""
    evidence_policy: str = "none"
    write_policy: str = ""
    verification_level: str = ""
    required_slots: list[str] = field(default_factory=list)
    filled_slots: list[str] = field(default_factory=list)
    unfilled_slots: list[str] = field(default_factory=list)
    explanation_required: bool = False
    explanation_paths: list[str] = field(default_factory=list)
    abstention_reason: str = ""
    confidence: float = 0.0
    slots: dict[str, RealizationSlot] = field(default_factory=dict)
