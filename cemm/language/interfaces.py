"""Language adapter interfaces — reversible surface evidence types.

Import boundary: model + language.stream only. No engine imports.

Architectural guardrails (AGENTS.md §8, UNDERSTANDING_PIPELINE.md §2-3):
- Language adapters emit reversible surface evidence only.
- They may PROPOSE lexeme senses, constructions, predications, and
  communicative structures. They may NOT:
    select final meaning, authorize a write, declare truth,
    directly answer a query, directly mutate memory,
    claim a capability, choose final response content.
- Surface evidence is candidate-only — never authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .stream import TokenStream, Token
from ..kernel.model.surface import SurfaceSpan, LexicalFormRef, KindHypothesis
from ..kernel.model.refs import FrozenMap


@dataclass(frozen=True, slots=True)
class LexicalSenseCandidate:
    """A candidate lexical sense proposed by a language adapter.

    This is a PROPOSAL — the adapter may not select final meaning.
    Multiple candidates may exist for the same lexical form.
    """
    lexical_form_ref: LexicalFormRef
    semantic_key: str
    sense_rank: float = 0.0
    evidence_kind: str = "lexical"  # lexical, construction, pragmatic
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ConstructionCandidate:
    """A candidate grammatical construction proposed by a language adapter.

    Constructions map surface patterns to predications — but as
    candidate evidence, not authoritative interpretation.
    """
    construction_key: str
    pattern: str
    predicate_schema_ref: str  # proposed predicate
    role_mappings: dict[str, int] = field(default_factory=dict)  # role → token index
    open_role_refs: tuple[str, ...] = ()
    communicative_force: str = ""
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CommunicativeCandidate:
    """A candidate communicative force proposed by a language adapter.

    Communicative force: assert, ask, request, direct, acknowledge,
    correct, promise, refuse. This is independent from polarity,
    context, and modality (AGENTS.md §5).
    """
    force: str  # assert, ask, request, direct, acknowledge, correct, promise, refuse
    confidence: float = 0.0
    evidence_kind: str = "syntactic"  # syntactic, pragmatic, construction
    source_token_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class PragmaticCue:
    """A pragmatic cue from a language adapter.

    Pragmatic cues may ADD candidates or discourse relations.
    They may NOT replace compositional content (UNDERSTANDING_PIPELINE.md §3).
    """
    cue_kind: str  # politeness, formality, emphasis, topic_shift, etc.
    value: str
    confidence: float = 0.0
    source_token_indices: tuple[int, ...] = ()
    adds_candidates: bool = True
    replaces_content: bool = False  # Must always be False


@dataclass(frozen=True, slots=True)
class SurfaceEvidence:
    """Complete reversible surface evidence from a language adapter.

    This is the sole output of language perception. It contains:
    - raw token stream (preserving raw text, offsets, contractions, etc.)
    - candidate lexical senses (proposals, not selections)
    - candidate constructions (proposals)
    - candidate communicative forces (proposals)
    - pragmatic cues (additions, never replacements)
    - quotation and clause boundaries
    - language and confidence

    The adapter may not select final meaning, authorize a write,
    declare truth, directly answer a query, directly mutate memory,
    claim a capability, or choose final response content.
    """
    token_stream: TokenStream
    lexical_sense_candidates: tuple[LexicalSenseCandidate, ...] = ()
    construction_candidates: tuple[ConstructionCandidate, ...] = ()
    communicative_candidates: tuple[CommunicativeCandidate, ...] = ()
    pragmatic_cues: tuple[PragmaticCue, ...] = ()
    surface_spans: tuple[SurfaceSpan, ...] = ()
    language_tag: str = "und"
    overall_confidence: float = 1.0
    adapter_id: str = ""
    adapter_version: str = ""


class LanguageAdapter(Protocol):
    """Protocol for language adapters.

    Language adapters emit reversible surface evidence only.
    They do NOT select final meaning, authorize writes, declare truth,
    answer queries, mutate memory, claim capabilities, or choose
    response content.
    """
    adapter_id: str
    adapter_version: str
    supported_language_tags: tuple[str, ...]

    def perceive(self, raw_text: str, language_tag: str) -> SurfaceEvidence: ...
