"""Reversible, candidate-only language evidence interfaces."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol
from .stream import TokenStream
from ..kernel.model.surface import SurfaceSpan, LexicalFormRef

@dataclass(frozen=True, slots=True)
class LexicalSenseCandidate:
    lexical_form_ref: LexicalFormRef
    semantic_key: str
    sense_rank: float = 0.0
    evidence_kind: str = "lexical"
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()

@dataclass(frozen=True, slots=True)
class ConstructionCandidate:
    construction_key: str
    pattern: str
    predicate_schema_ref: str
    role_mappings: dict[str, int] = field(default_factory=dict)
    open_role_refs: tuple[str, ...] = ()
    communicative_force: str = ""
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()
    capture_spans: dict[str, tuple[int, int]] = field(default_factory=dict)
    output_kind: str = "predication"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class RuleCandidate:
    construction_key: str
    rule_kind: str
    strength: str
    causal_warrant: str
    premise_capture: str
    conclusion_capture: str
    capture_spans: dict[str, tuple[int, int]] = field(default_factory=dict)
    premise_token_indices: tuple[int, ...] = ()
    conclusion_token_indices: tuple[int, ...] = ()
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()

@dataclass(frozen=True, slots=True)
class CommunicativeCandidate:
    force: str
    confidence: float = 0.0
    evidence_kind: str = "syntactic"
    source_token_indices: tuple[int, ...] = ()

@dataclass(frozen=True, slots=True)
class PragmaticCue:
    cue_kind: str
    value: str
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()
    adds_candidates: bool = True
    replaces_content: bool = False

@dataclass(frozen=True, slots=True)
class SurfaceEvidence:
    token_stream: TokenStream
    lexical_sense_candidates: tuple[LexicalSenseCandidate, ...] = ()
    construction_candidates: tuple[ConstructionCandidate, ...] = ()
    rule_candidates: tuple[RuleCandidate, ...] = ()
    communicative_candidates: tuple[CommunicativeCandidate, ...] = ()
    pragmatic_cues: tuple[PragmaticCue, ...] = ()
    surface_spans: tuple[SurfaceSpan, ...] = ()
    language_tag: str = "und"
    overall_confidence: float = 1.0
    adapter_id: str = ""
    adapter_version: str = ""
    source_evidence_refs: tuple[str, ...] = ()

class LanguageAdapter(Protocol):
    adapter_id: str
    adapter_version: str
    supported_language_tags: tuple[str, ...]
    def perceive(self, raw_text: str, language_tag: str) -> SurfaceEvidence: ...
