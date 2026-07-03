"""Lightweight language detection for multilingual support.

Uses simple heuristics:
1. Check for common function words / pronouns unique to each language
2. Score by token overlap with known language packs
3. Fall back to English

This is intentionally lightweight — no external dependencies.
The detection is used to select the appropriate LanguageAdapter.
"""

from __future__ import annotations

import re
from pathlib import Path

from .language_adapter import LanguageAdapter, get_adapter, load_language_pack, LanguagePackData


_AVAILABLE_LANGUAGES: list[str] | None = None


def _available_languages() -> list[str]:
    """Return list of available language codes from data/languages/."""
    global _AVAILABLE_LANGUAGES
    if _AVAILABLE_LANGUAGES is not None:
        return _AVAILABLE_LANGUAGES
    lang_dir = Path(__file__).parent.parent / "data" / "languages"
    if not lang_dir.exists():
        _AVAILABLE_LANGUAGES = ["en"]
        return _AVAILABLE_LANGUAGES
    _AVAILABLE_LANGUAGES = sorted(
        d.name for d in lang_dir.iterdir() if d.is_dir() and (d / "pronouns.json").exists()
    )
    if "en" not in _AVAILABLE_LANGUAGES:
        _AVAILABLE_LANGUAGES = ["en"] + _AVAILABLE_LANGUAGES
    return _AVAILABLE_LANGUAGES


def detect_language(text: str) -> str:
    """Detect the language of a text string.

    Uses token overlap scoring with available language packs.
    Returns the language code with highest overlap, or 'en' as fallback.

    Args:
        text: Input text to detect language for.

    Returns:
        Language code (e.g., "en", "ig", "yo", "es").
    """
    tokens = set(re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE))
    if not tokens:
        return "en"

    languages = _available_languages()
    if len(languages) == 1:
        return languages[0]

    best_lang = "en"
    best_score = 0

    for lang in languages:
        pack = load_language_pack(lang)
        # Score: overlap of tokens with pronouns + action keywords + state keywords
        # + entity_exclude + question_cues
        known_tokens = set()
        known_tokens.update(pack.pronouns.keys())
        known_tokens.update(pack.action_keywords.keys())
        known_tokens.update(pack.state_keywords.keys())
        known_tokens.update(pack.entity_exclude)
        known_tokens.update(pack.question_cues)
        known_tokens.update(pack.deictic_words)

        overlap = len(tokens & known_tokens)
        # Normalize by total known tokens to avoid bias toward larger packs
        score = overlap / max(len(known_tokens), 1)

        if score > best_score:
            best_score = score
            best_lang = lang

    return best_lang


def detect_and_get_adapter(text: str) -> tuple[str, LanguageAdapter]:
    """Detect language and return the appropriate adapter.

    Args:
        text: Input text to detect language for.

    Returns:
        Tuple of (language_code, LanguageAdapter).
    """
    lang = detect_language(text)
    adapter = get_adapter(lang)
    return lang, adapter
