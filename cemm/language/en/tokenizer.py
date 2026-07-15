"""English tokenizer producing reversible, semantics-neutral evidence."""
from __future__ import annotations

import re

from ..stream import (
    ClauseBoundary,
    ContractionDecomposition,
    DependencyEdge,
    MorphologicalFeature,
    QuotationSpan,
    Token,
    TokenKind,
    TokenStream,
)


_CONTRACTIONS: dict[str, tuple[str, ...]] = {
    "i'm": ("I", "am"), "i've": ("I", "have"), "i'll": ("I", "will"),
    "i'd": ("I", "would"), "you're": ("you", "are"),
    "you've": ("you", "have"), "you'll": ("you", "will"),
    "you'd": ("you", "would"), "he's": ("he", "is"),
    "she's": ("she", "is"), "it's": ("it", "is"),
    "we're": ("we", "are"), "they're": ("they", "are"),
    "don't": ("do", "not"), "doesn't": ("does", "not"),
    "didn't": ("did", "not"), "won't": ("will", "not"),
    "can't": ("can", "not"), "couldn't": ("could", "not"),
    "shouldn't": ("should", "not"), "wouldn't": ("would", "not"),
    "isn't": ("is", "not"), "aren't": ("are", "not"),
    "wasn't": ("was", "not"), "weren't": ("were", "not"),
    "haven't": ("have", "not"), "hasn't": ("has", "not"),
    "that's": ("that", "is"), "what's": ("what", "is"),
    "who's": ("who", "is"), "where's": ("where", "is"),
    "how's": ("how", "is"), "there's": ("there", "is"),
}
_NEGATION = frozenset({"not", "no", "never", "neither", "nor", "none", "nothing"})
_PRONOUNS = frozenset({
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "this",
    "that", "these", "those",
})
_COPULAR = frozenset({"is", "are", "am", "was", "were", "be", "been", "being"})
_AUX = frozenset({
    "do", "does", "did", "have", "has", "had", "will", "would", "can",
    "could", "should", "might", "must", "may", "shall",
})
_TOKEN_PATTERN = re.compile(
    r"\s*([A-Za-z]+(?:['’][A-Za-z]+)?)|\s*([\"“”])|\s*(['‘’])|\s*([.!?;,:])|\s*(\S)"
)


def tokenize(raw_text: str) -> TokenStream:
    tokens: list[Token] = []
    clauses: list[ClauseBoundary] = []
    quotes: list[QuotationSpan] = []
    clause_start = 0
    quote_open: int | None = None
    quote_content_start = 0

    for match in _TOKEN_PATTERN.finditer(raw_text):
        raw = match.group(0).strip()
        if not raw:
            continue
        start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip()))
        end = start + len(raw)
        lower = raw.lower().replace("’", "'")
        kind = TokenKind.WORD
        contraction = None
        is_negation = False
        lemma: tuple[str, ...] = ()
        morphology: tuple[MorphologicalFeature, ...] = ()

        if match.group(1):
            if lower in _CONTRACTIONS:
                components = _CONTRACTIONS[lower]
                contraction = ContractionDecomposition(raw, components)
                kind = TokenKind.NEGATION if "not" in components else TokenKind.CONTRACTION
                is_negation = "not" in components
                lemma = (components[0].lower(),)
            elif lower in _NEGATION:
                kind = TokenKind.NEGATION
                is_negation = True
                lemma = (lower,)
            else:
                lemma = (_lemma(lower),)
                morphology = tuple(_morphology(lower, raw))
        elif match.group(2) or match.group(3):
            if quote_open is None:
                kind = TokenKind.QUOTE_OPEN
                quote_open = start
                quote_content_start = end
            else:
                kind = TokenKind.QUOTE_CLOSE
                quotes.append(
                    QuotationSpan(
                        open_offset=quote_open,
                        close_offset=end,
                        content_offsets=(quote_content_start, start),
                    )
                )
                quote_open = None
        elif match.group(4):
            kind = TokenKind.PUNCTUATION
            if raw in ".!?;:":
                clauses.append(ClauseBoundary(clause_start, end, "main"))
                clause_start = end
        else:
            kind = TokenKind.UNKNOWN

        tokens.append(
            Token(
                raw_form=raw,
                normalized_form=lower,
                start_offset=start,
                end_offset=end,
                kind=kind,
                lemma_candidates=lemma,
                morphological_features=morphology,
                contraction=contraction,
                language_tag="en",
                is_negation=is_negation,
                # Semantic opacity is decided by schema resolution, not tokenization.
                is_unknown=False,
            )
        )

    if quote_open is not None:
        quotes.append(
            QuotationSpan(
                open_offset=quote_open,
                close_offset=len(raw_text),
                content_offsets=(quote_content_start, len(raw_text)),
            )
        )
    if clause_start < len(raw_text) or not clauses:
        clauses.append(ClauseBoundary(clause_start, len(raw_text), "main"))

    return TokenStream(
        tokens=tuple(tokens),
        dependency_edges=tuple(_dependencies(tokens)),
        clause_boundaries=tuple(clauses),
        quotation_spans=tuple(quotes),
        language_tag="en",
        overall_confidence=0.85,
        raw_text=raw_text,
    )


def _lemma(lower: str) -> str:
    irregular = {"means": "mean", "knew": "know", "knows": "know", "does": "do"}
    if lower in irregular:
        return irregular[lower]
    if lower.endswith("ing") and len(lower) > 5:
        base = lower[:-3]
        return base + "e" if base.endswith("at") else base
    if lower.endswith("ed") and len(lower) > 4:
        return lower[:-2]
    if lower.endswith("s") and len(lower) > 3 and not lower.endswith("ss"):
        return lower[:-1]
    return lower


def _morphology(lower: str, raw: str) -> list[MorphologicalFeature]:
    result: list[MorphologicalFeature] = []
    if lower in _PRONOUNS:
        person = "first" if lower in {"i", "me", "my", "we", "us", "our"} else (
            "second" if lower in {"you", "your"} else "third"
        )
        result.append(MorphologicalFeature("person", person, 1.0))
    if lower.endswith("ed"):
        result.append(MorphologicalFeature("tense", "past", 0.8))
    elif lower.endswith("ing"):
        result.append(MorphologicalFeature("tense", "present_participle", 0.8))
    if raw[:1].isupper() and lower not in _PRONOUNS:
        result.append(MorphologicalFeature("case", "proper", 0.9))
    return result


def _dependencies(tokens: list[Token]) -> list[DependencyEdge]:
    edges: list[DependencyEdge] = []
    word_indices = [
        i for i, token in enumerate(tokens)
        if token.kind in {TokenKind.WORD, TokenKind.CONTRACTION, TokenKind.NEGATION}
    ]
    for position, index in enumerate(word_indices):
        token = tokens[index]
        lemma = token.lemma_candidates[0] if token.lemma_candidates else token.normalized_form
        if lemma in _PRONOUNS:
            for next_index in word_indices[position + 1:]:
                next_token = tokens[next_index]
                next_lemma = (
                    next_token.lemma_candidates[0]
                    if next_token.lemma_candidates else next_token.normalized_form
                )
                components = next_token.contraction.components if next_token.contraction else ()
                if next_lemma in _COPULAR | _AUX | {"know", "mean"} or any(
                    component.lower() in _COPULAR | _AUX for component in components
                ):
                    edges.append(DependencyEdge(next_index, index, "nsubj", 0.75))
                    break
        if lemma in {"a", "an", "the"} and position + 1 < len(word_indices):
            edges.append(DependencyEdge(word_indices[position + 1], index, "det", 0.9))
    return edges
