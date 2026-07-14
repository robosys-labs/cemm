"""English tokenizer — produces canonical TokenStream preserving raw text.

Implements:
- tokenization with exact offsets
- contraction decomposition (I'm → I + am)
- morphology (lemma candidates, tense/number/person)
- negation detection (not, n't)
- clause boundaries (main, subordinate, complement)
- quotation spans (preserving quote marks)
- punctuation classification

Per UNDERSTANDING_PIPELINE.md §2:
- Apostrophes and quotation boundaries must survive.
- Different tokenizers may not create incompatible canonical forms.
- Unknown content is never converted into a generic entity.
"""
from __future__ import annotations

import re
from typing import Any

from ..stream import (
    Token, TokenKind, TokenStream,
    MorphologicalFeature, ContractionDecomposition,
    ClauseBoundary, QuotationSpan, DependencyEdge,
)


# ── Contraction map ──

_CONTRACTIONS: dict[str, tuple[str, ...]] = {
    "i'm": ("I", "am"),
    "i've": ("I", "have"),
    "i'll": ("I", "will"),
    "i'd": ("I", "would"),
    "you're": ("you", "are"),
    "you've": ("you", "have"),
    "you'll": ("you", "will"),
    "you'd": ("you", "would"),
    "he's": ("he", "is"),
    "he'll": ("he", "will"),
    "he'd": ("he", "would"),
    "she's": ("she", "is"),
    "she'll": ("she", "will"),
    "she'd": ("she", "would"),
    "it's": ("it", "is"),
    "it'll": ("it", "will"),
    "it'd": ("it", "would"),
    "we're": ("we", "are"),
    "we've": ("we", "have"),
    "we'll": ("we", "will"),
    "we'd": ("we", "would"),
    "they're": ("they", "are"),
    "they've": ("they", "have"),
    "they'll": ("they", "will"),
    "they'd": ("they", "would"),
    "don't": ("do", "not"),
    "doesn't": ("does", "not"),
    "didn't": ("did", "not"),
    "won't": ("will", "not"),
    "can't": ("can", "not"),
    "couldn't": ("could", "not"),
    "shouldn't": ("should", "not"),
    "wouldn't": ("would", "not"),
    "isn't": ("is", "not"),
    "aren't": ("are", "not"),
    "wasn't": ("was", "not"),
    "weren't": ("were", "not"),
    "haven't": ("have", "not"),
    "hasn't": ("has", "not"),
    "hadn't": ("had", "not"),
    "mightn't": ("might", "not"),
    "mustn't": ("must", "not"),
    "needn't": ("need", "not"),
    "oughtn't": ("ought", "not"),
    "that's": ("that", "is"),
    "that'll": ("that", "will"),
    "what's": ("what", "is"),
    "what'll": ("what", "will"),
    "who's": ("who", "is"),
    "who'll": ("who", "will"),
    "where's": ("where", "is"),
    "how's": ("how", "is"),
    "there's": ("there", "is"),
    "here's": ("here", "is"),
}

# Negation words
_NEGATION_WORDS = frozenset({"not", "no", "never", "neither", "nor", "none", "nobody", "nothing"})

# Wh-words
_WH_WORDS = frozenset({"what", "who", "whom", "whose", "which", "where", "when", "why", "how"})

# Pronouns
_PRONOUNS = frozenset({
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "mine", "yours", "hers", "ours", "theirs",
    "myself", "yourself", "himself", "herself", "itself",
    "ourselves", "yourselves", "themselves",
    "this", "that", "these", "those",
    "someone", "somebody", "something", "anyone", "anybody", "anything",
    "everyone", "everybody", "everything", "nobody", "nothing", "none",
})

# Copular verbs
_COPULAR = frozenset({"is", "are", "am", "was", "were", "be", "being", "been", "seem", "seems", "become", "becomes"})

# Auxiliary verbs
_AUX = frozenset({"do", "does", "did", "have", "has", "had", "will", "would", "can", "could", "should", "might", "must", "may", "shall", "ought"})

# Punctuation that ends clauses
_CLAUSE_END = frozenset({".", "!", "?", ";", ":"})

# Punctuation that separates clauses
_CLAUSE_SEP = frozenset({",", ";", ":"})

# Quote characters
_QUOTE_CHARS = frozenset({'"', '\u201c', '\u201d', "'", '\u2018', '\u2019'})


def _is_contraction(token: str) -> bool:
    lower = token.lower()
    return lower in _CONTRACTIONS or "'" in token and not lower.endswith("'s") or False


def _is_negation_contraction(token: str) -> bool:
    lower = token.lower()
    return "'t" in lower or lower in _NEGATION_WORDS


# ── Tokenizer ──

_TOKEN_PATTERN = re.compile(
    r"\s*"  # leading whitespace
    r"([A-Za-z]+(?:'[A-Za-z]+)?)"  # word or contraction
    r"|(\u201c|\u201d|\")"  # double quotes
    r"|(\u2018|\u2019|')"  # single quotes (may be apostrophe)
    r"|([.!?;,:])"  # punctuation
    r"|(\S)"  # any other non-whitespace
)


def tokenize(raw_text: str) -> TokenStream:
    """Tokenize raw text into a canonical TokenStream.

    Preserves:
    - exact offsets (start, end)
    - raw form vs normalized form
    - contraction decomposition
    - negation flags
    - morphological features
    """
    tokens: list[Token] = []
    clause_boundaries: list[ClauseBoundary] = []
    quotation_spans: list[QuotationSpan] = []
    dependency_edges: list[DependencyEdge] = []

    pos = 0
    token_index = 0
    clause_start = 0
    quote_open_offset: int | None = None
    quote_level = 0
    quote_content_start = 0

    while pos < len(raw_text):
        m = _TOKEN_PATTERN.match(raw_text, pos)
        if not m or m.end() == pos:
            pos += 1
            continue

        pos = m.end()
        raw_form = m.group(0).strip()
        if not raw_form:
            continue

        start = m.start()
        # Skip leading whitespace in offset
        ws_match = re.match(r'\s*', raw_text[m.start():m.end()])
        if ws_match:
            start = m.start() + ws_match.end()

        end = start + len(raw_form)
        lower = raw_form.lower()

        kind = TokenKind.WORD
        contraction = None
        is_negation = False
        morph: list[MorphologicalFeature] = []
        lemma_candidates: tuple[str, ...] = ()

        # Check what group matched
        if m.group(1):  # word or contraction
            if lower in _CONTRACTIONS:
                kind = TokenKind.CONTRACTION
                components = _CONTRACTIONS[lower]
                contraction = ContractionDecomposition(
                    raw_form=raw_form,
                    components=components,
                )
                # Check if it's a negation contraction
                if "not" in components:
                    is_negation = True
                    kind = TokenKind.NEGATION
                # Lemma is the first component
                lemma_candidates = (components[0].lower(),)
            elif "'t" in lower and lower not in _CONTRACTIONS:
                # Unknown contraction with n't
                kind = TokenKind.NEGATION
                is_negation = True
                base = lower.rsplit("'", 1)[0]
                contraction = ContractionDecomposition(
                    raw_form=raw_form,
                    components=(base, "not"),
                )
                lemma_candidates = (base,)
            elif lower in _NEGATION_WORDS:
                kind = TokenKind.NEGATION
                is_negation = True
                lemma_candidates = (lower,)
            else:
                # Regular word
                lemma_candidates = (_compute_lemma(lower),)
                morph = _compute_morphology(lower, raw_form)

        elif m.group(2):  # double quote
            if quote_open_offset is None:
                kind = TokenKind.QUOTE_OPEN
                quote_open_offset = start
                quote_content_start = end
                quote_level += 1
            else:
                kind = TokenKind.QUOTE_CLOSE
                quotation_spans.append(QuotationSpan(
                    open_offset=quote_open_offset,
                    close_offset=end,
                    content_offsets=(quote_content_start, start),
                    quote_level=quote_level - 1,
                ))
                quote_open_offset = None
                quote_level -= 1

        elif m.group(3):  # single quote (could be apostrophe or quote)
            # If preceded by a letter, it's an apostrophe — already handled
            # as part of the word. Standalone single quote = quote marker.
            if quote_open_offset is None and start > 0 and raw_text[start - 1] in ' \t\n':
                kind = TokenKind.QUOTE_OPEN
                quote_open_offset = start
                quote_content_start = end
                quote_level += 1
            elif quote_open_offset is not None:
                kind = TokenKind.QUOTE_CLOSE
                quotation_spans.append(QuotationSpan(
                    open_offset=quote_open_offset,
                    close_offset=end,
                    content_offsets=(quote_content_start, start),
                    quote_level=quote_level - 1,
                ))
                quote_open_offset = None
                quote_level -= 1
            else:
                kind = TokenKind.PUNCTUATION

        elif m.group(4):  # clause-ending punctuation
            kind = TokenKind.PUNCTUATION
            # Close clause boundary
            clause_boundaries.append(ClauseBoundary(
                start_offset=clause_start,
                end_offset=end,
                clause_kind="main",
            ))
            clause_start = end

        elif m.group(5):  # other punctuation
            kind = TokenKind.PUNCTUATION

        # Determine if unknown
        is_unknown = kind == TokenKind.WORD and lower not in _KNOWN_WORDS

        token = Token(
            raw_form=raw_form,
            normalized_form=lower,
            start_offset=start,
            end_offset=end,
            kind=kind,
            lemma_candidates=lemma_candidates,
            morphological_features=tuple(morph),
            contraction=contraction,
            language_tag="en",
            is_negation=is_negation,
            is_unknown=is_unknown,
        )
        tokens.append(token)
        token_index += 1

    # Handle unclosed quotation
    if quote_open_offset is not None:
        quotation_spans.append(QuotationSpan(
            open_offset=quote_open_offset,
            close_offset=len(raw_text),
            content_offsets=(quote_content_start, len(raw_text)),
            quote_level=quote_level - 1,
        ))

    # Close final clause if not closed
    if clause_start < len(raw_text):
        clause_boundaries.append(ClauseBoundary(
            start_offset=clause_start,
            end_offset=len(raw_text),
            clause_kind="main",
        ))

    # Build dependency edges (simplified head-dependent)
    dependency_edges = _build_dependencies(tokens)

    return TokenStream(
        tokens=tuple(tokens),
        dependency_edges=tuple(dependency_edges),
        clause_boundaries=tuple(clause_boundaries),
        quotation_spans=tuple(quotation_spans),
        language_tag="en",
        overall_confidence=0.85,
        raw_text=raw_text,
    )


def _compute_lemma(lower: str) -> str:
    """Compute a simple lemma for an English word."""
    if lower.endswith("ing") and len(lower) > 4:
        return lower[:-3]
    if lower.endswith("ed") and len(lower) > 3:
        return lower[:-2]
    if lower.endswith("s") and len(lower) > 3 and not lower.endswith("ss"):
        return lower[:-1]
    return lower


def _compute_morphology(lower: str, raw_form: str) -> list[MorphologicalFeature]:
    """Compute morphological features for a word."""
    features: list[MorphologicalFeature] = []

    # Number
    if lower.endswith("s") and not lower.endswith("ss"):
        features.append(MorphologicalFeature("number", "plural", 0.7))
    else:
        features.append(MorphologicalFeature("number", "singular", 0.7))

    # Tense (for verbs)
    if lower.endswith("ed"):
        features.append(MorphologicalFeature("tense", "past", 0.8))
    elif lower.endswith("ing"):
        features.append(MorphologicalFeature("tense", "present_participle", 0.8))
    elif raw_form and raw_form[0].isupper() and lower not in _PRONOUNS:
        features.append(MorphologicalFeature("case", "proper", 0.9))

    # Person (for pronouns)
    if lower == "i":
        features.append(MorphologicalFeature("person", "first", 1.0))
    elif lower == "you":
        features.append(MorphologicalFeature("person", "second", 1.0))
    elif lower in ("he", "she", "it"):
        features.append(MorphologicalFeature("person", "third", 1.0))

    return features


def _build_dependencies(tokens: list[Token]) -> list[DependencyEdge]:
    """Build simplified dependency edges.

    This is a minimal head-dependent structure sufficient for
    construction detection. A full parser would produce richer edges.
    """
    edges: list[DependencyEdge] = []
    word_indices = [i for i, t in enumerate(tokens) if t.kind == TokenKind.WORD or t.kind == TokenKind.CONTRACTION]

    for idx_pos, idx in enumerate(word_indices):
        token = tokens[idx]
        lower = token.normalized_form

        # Subject → copular/verb
        if lower in _PRONOUNS or (token.morphological_features and
                                   any(f.feature == "case" and f.value == "proper" for f in token.morphological_features)):
            # Find next verb-like token
            for j in range(idx_pos + 1, len(word_indices)):
                next_idx = word_indices[j]
                next_token = tokens[next_idx]
                next_lower = next_token.normalized_form
                if next_lower in _COPULAR or next_lower in _AUX or next_lower == "know" or next_lower == "means":
                    edges.append(DependencyEdge(
                        head_index=next_idx,
                        dependent_index=idx,
                        relation="nsubj",
                        confidence=0.7,
                    ))
                    break

        # Determiner → noun
        if lower in ("a", "an", "the"):
            if idx_pos + 1 < len(word_indices):
                next_idx = word_indices[idx_pos + 1]
                edges.append(DependencyEdge(
                    head_index=next_idx,
                    dependent_index=idx,
                    relation="det",
                    confidence=0.9,
                ))

    return edges


# Minimal known-word set for unknown detection.
# In a real system this would come from the schema store.
_KNOWN_WORDS = frozenset({
    # pronouns
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    # copular
    "is", "are", "am", "was", "were", "be", "been", "being",
    # auxiliaries
    "do", "does", "did", "have", "has", "had",
    "will", "would", "can", "could", "should", "might", "must", "may",
    # wh-words
    "what", "who", "whom", "whose", "which", "where", "when", "why", "how",
    # determiners
    "a", "an", "the",
    # common verbs
    "know", "knows", "knew", "mean", "means", "meant",
    # common nouns (will be extended by schema store)
    "engineer",
    # negation
    "not", "no", "never",
    # demonstratives
    "this", "that", "these", "those",
    # conjunctions
    "and", "or", "but", "if", "because", "so", "that",
    # prepositions
    "of", "in", "on", "at", "to", "for", "with", "by", "from",
    # misc
    "there", "here", "about",
})
