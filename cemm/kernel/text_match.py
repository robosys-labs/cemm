"""Boundary-safe text matching primitives shared across the kernel.

These helpers replace raw substring checks (``alias in content``) with
token-boundary-aware matching to prevent false positives like ``"hi"``
matching inside ``"this"`` or ``"i"`` matching inside ``"time"``.

All helpers are language-agnostic: they operate on tokenised surfaces
produced by ``_tokenize_surface`` which splits on non-alphanumeric
characters (apostrophes preserved for contractions).
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def tokenize_surface(text: str) -> list[str]:
    """Tokenise *text* into lowercase alphanumeric tokens (apostrophes kept)."""
    return _TOKEN_RE.findall(text.lower())


def token_in_text(word: str, text: str) -> bool:
    """Return True if *word* appears as a complete token in *text*."""
    word_t = word.lower().strip()
    if not word_t:
        return False
    return word_t in tokenize_surface(text)


def any_token_in_text(words: list[str], text: str) -> bool:
    """Return True if any word in *words* appears as a complete token in *text*."""
    text_tokens = set(tokenize_surface(text))
    return any(w.lower().strip() in text_tokens for w in words)


def phrase_in_text(phrase: str, text: str) -> bool:
    """Return True if *phrase* appears as a contiguous token sequence in *text*.

    Single-word phrases require exact token match.
    Multi-word phrases require the exact token subsequence.
    """
    phrase_tokens = tokenize_surface(phrase)
    text_tokens = tokenize_surface(text)
    if not phrase_tokens or not text_tokens:
        return False
    if len(phrase_tokens) == 1:
        return phrase_tokens[0] in text_tokens
    window = len(phrase_tokens)
    for i in range(len(text_tokens) - window + 1):
        if text_tokens[i:i + window] == phrase_tokens:
            return True
    return False


def any_phrase_in_text(phrases: list[str], text: str) -> bool:
    """Return True if any phrase in *phrases* appears as a token sequence in *text*."""
    return any(phrase_in_text(p, text) for p in phrases)
