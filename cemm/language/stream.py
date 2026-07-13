"""Canonical token stream — preserves raw text, contractions, offsets, quotes, negation, morphology.

Import boundary: model submodules only. No engine imports.

Architectural guardrails (AGENTS.md §8):
- The canonical token stream preserves raw text, apostrophes, offsets,
  punctuation, quotation boundaries, negation, contractions, and morphology.
- Apostrophes and quotation boundaries must survive.
- Different tokenizers may not create incompatible canonical forms.
- Unknown content is never converted into a generic entity, role marker,
  or durable concept fact merely to keep the pipeline moving.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TokenKind(str, Enum):
    WORD = "word"
    CONTRACTION = "contraction"
    PUNCTUATION = "punctuation"
    QUOTE_OPEN = "quote_open"
    QUOTE_CLOSE = "quote_close"
    NEGATION = "negation"
    WHITESPACE = "whitespace"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MorphologicalFeature:
    """A morphological feature annotation on a token."""
    feature: str  # tense, number, person, mood, case, gender, etc.
    value: str
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class ContractionDecomposition:
    """Decomposition of a contraction into components.

    'I'm' → ('I', 'am')
    'don't' → ('do', 'not')
    The raw form is always preserved alongside the decomposition.
    """
    raw_form: str
    components: tuple[str, ...]
    component_offsets: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ClauseBoundary:
    """A clause boundary annotation."""
    start_offset: int
    end_offset: int
    clause_kind: str = "main"  # main, subordinate, relative, complement
    parent_clause_index: int | None = None


@dataclass(frozen=True, slots=True)
class QuotationSpan:
    """A quotation span with open/close boundaries."""
    open_offset: int
    close_offset: int
    content_offsets: tuple[int, int]
    quote_level: int = 0  # nesting level


@dataclass(frozen=True, slots=True)
class Token:
    """A canonical token preserving raw text and offsets.

    The canonical token stream preserves raw text — normalization
    produces a normalized surface but never destroys the raw form.
    """
    raw_form: str
    normalized_form: str
    start_offset: int
    end_offset: int
    kind: TokenKind = TokenKind.WORD
    lemma_candidates: tuple[str, ...] = ()
    morphological_features: tuple[MorphologicalFeature, ...] = ()
    contraction: ContractionDecomposition | None = None
    language_tag: str = "und"
    confidence: float = 1.0
    is_negation: bool = False
    is_unknown: bool = False

    @property
    def preserves_raw(self) -> bool:
        """Whether the raw form differs from the normalized form."""
        return self.raw_form != self.normalized_form


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """A syntax/dependency evidence edge."""
    head_index: int
    dependent_index: int
    relation: str  # nsubj, dobj, prep, etc.
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class TokenStream:
    """A canonical token stream — the reversible output of language perception.

    Preserves:
    - raw text and exact offsets
    - normalized form without destroying raw form
    - lemma and morphology candidates
    - contraction decomposition
    - quotation, negation, clause, and modality boundaries
    - syntax/dependency evidence
    - language and confidence

    Different tokenizers may not create incompatible canonical forms.
    """
    tokens: tuple[Token, ...] = ()
    dependency_edges: tuple[DependencyEdge, ...] = ()
    clause_boundaries: tuple[ClauseBoundary, ...] = ()
    quotation_spans: tuple[QuotationSpan, ...] = ()
    language_tag: str = "und"
    overall_confidence: float = 1.0
    raw_text: str = ""

    def __len__(self) -> int:
        return len(self.tokens)

    def __iter__(self):
        return iter(self.tokens)

    @property
    def has_contractions(self) -> bool:
        return any(t.contraction is not None for t in self.tokens)

    @property
    def has_quotations(self) -> bool:
        return len(self.quotation_spans) > 0

    @property
    def has_negation(self) -> bool:
        return any(t.is_negation for t in self.tokens)

    @property
    def has_unknown_tokens(self) -> bool:
        return any(t.is_unknown for t in self.tokens)

    def tokens_in_clause(self, clause_index: int) -> tuple[Token, ...]:
        """Get tokens within a specific clause."""
        if clause_index >= len(self.clause_boundaries):
            return ()
        clause = self.clause_boundaries[clause_index]
        return tuple(
            t for t in self.tokens
            if t.start_offset >= clause.start_offset
            and t.end_offset <= clause.end_offset
        )

    def tokens_in_quotation(self, quote_index: int) -> tuple[Token, ...]:
        """Get tokens within a specific quotation span."""
        if quote_index >= len(self.quotation_spans):
            return ()
        span = self.quotation_spans[quote_index]
        return tuple(
            t for t in self.tokens
            if t.start_offset >= span.content_offsets[0]
            and t.end_offset <= span.content_offsets[1]
        )
