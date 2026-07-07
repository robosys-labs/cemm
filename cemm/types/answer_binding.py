"""AnswerBinding — result of executing a SemanticQuery.

Binds answer slots with evidence references, confidence scores,
and explanation paths through the relation algebra. This is the
semantic equivalent of a retrieval result — but instead of a
flat list of claims, it's a structured binding with provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlotFill:
    slot_name: str = ""
    concept_id: str = ""
    entity_id: str = ""
    surface: str = ""
    relation_key: str = ""
    source_frame_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    explanation_path: list[str] = field(default_factory=list)
    confidence: float = 0.5
    is_inherited: bool = False
    is_inverse: bool = False
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnswerBinding:
    binding_id: str = ""
    source_query_id: str = ""
    query_kind: str = "lookup"
    slot_fills: list[SlotFill] = field(default_factory=list)
    matched_frame_ids: list[str] = field(default_factory=list)
    explanation_paths: list[list[str]] = field(default_factory=list)
    has_answer: bool = False
    confidence: float = 0.0
    abstention_reason: str = ""
    evidence_policy: str = "speaker_asserted"
    freshness_policy: str = "any"

    def evidence_refs_present(self) -> bool:
        return any(f.evidence_refs for f in self.slot_fills)
