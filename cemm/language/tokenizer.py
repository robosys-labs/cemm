"""Language-neutral reversible tokenizer.

The tokenizer identifies Unicode word-like spans, punctuation, quotation
boundaries, and unknown symbols.  Lexical meaning, contractions, negation, and
morphology are supplied by the selected semantic language pack rather than by
English-specific code.
"""
from __future__ import annotations

from .stream import ClauseBoundary, QuotationSpan, Token, TokenKind, TokenStream

_APOSTROPHES = frozenset({"'", "’"})
_QUOTES = frozenset({'"', "“", "”", "‘", "’"})
_CLAUSE_PUNCTUATION = frozenset({".", "!", "?", ";", ":"})
_PUNCTUATION = _CLAUSE_PUNCTUATION | frozenset({",", "-", "—", "–"})


def tokenize(raw_text: str, *, language_tag: str = "und") -> TokenStream:
    tokens: list[Token] = []
    clauses: list[ClauseBoundary] = []
    quotations: list[QuotationSpan] = []
    clause_start = 0
    quote_open: int | None = None
    quote_content_start = 0
    index = 0

    while index < len(raw_text):
        char = raw_text[index]
        if char.isspace():
            index += 1
            continue

        start = index
        if char.isalnum() or char == "_":
            index += 1
            while index < len(raw_text):
                current = raw_text[index]
                if current.isalnum() or current == "_":
                    index += 1
                    continue
                if (
                    current in _APOSTROPHES
                    and index + 1 < len(raw_text)
                    and raw_text[index - 1].isalnum()
                    and raw_text[index + 1].isalnum()
                ):
                    index += 1
                    continue
                if (
                    current == "-"
                    and index + 1 < len(raw_text)
                    and raw_text[index - 1].isalnum()
                    and raw_text[index + 1].isalnum()
                ):
                    index += 1
                    continue
                break
            raw = raw_text[start:index]
            kind = TokenKind.WORD
        else:
            index += 1
            raw = raw_text[start:index]
            if char in _QUOTES:
                if quote_open is None:
                    kind = TokenKind.QUOTE_OPEN
                    quote_open = start
                    quote_content_start = index
                else:
                    kind = TokenKind.QUOTE_CLOSE
                    quotations.append(QuotationSpan(
                        open_offset=quote_open,
                        close_offset=index,
                        content_offsets=(quote_content_start, start),
                    ))
                    quote_open = None
            elif char in _PUNCTUATION:
                kind = TokenKind.PUNCTUATION
                if char in _CLAUSE_PUNCTUATION:
                    clauses.append(ClauseBoundary(clause_start, index, "main"))
                    clause_start = index
            else:
                kind = TokenKind.UNKNOWN

        tokens.append(Token(
            raw_form=raw,
            normalized_form=raw.casefold(),
            start_offset=start,
            end_offset=index,
            kind=kind,
            lemma_candidates=(raw.casefold(),) if kind is TokenKind.WORD else (),
            language_tag=language_tag,
            is_unknown=kind is TokenKind.UNKNOWN,
        ))

    if quote_open is not None:
        quotations.append(QuotationSpan(
            open_offset=quote_open,
            close_offset=len(raw_text),
            content_offsets=(quote_content_start, len(raw_text)),
        ))
    if clause_start < len(raw_text) or not clauses:
        clauses.append(ClauseBoundary(clause_start, len(raw_text), "main"))

    return TokenStream(
        tokens=tuple(tokens),
        clause_boundaries=tuple(clauses),
        quotation_spans=tuple(quotations),
        language_tag=language_tag,
        overall_confidence=0.95,
        raw_text=raw_text,
    )
