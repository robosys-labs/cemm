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

from .language_adapter import LanguageAdapter, get_adapter, EnglishLanguageAdapter, JSONLanguageAdapter


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


def _adapter_known_tokens(adapter: LanguageAdapter) -> set[str]:
    """Extract known tokens from an adapter for language detection scoring."""
    tokens: set[str] = set()

    if isinstance(adapter, EnglishLanguageAdapter):
        tokens.update(adapter.PRONOUNS.keys())
        tokens.update(adapter.ACTIONS.keys())
        tokens.update(adapter.STATES.keys())
        tokens.update(adapter.ENTITY_EXCLUDE)
        tokens.update(adapter.DEICTICS)
    elif isinstance(adapter, JSONLanguageAdapter):
        tokens.update(adapter._pronouns.keys())
        tokens.update(adapter._actions.keys())
        tokens.update(adapter._states.keys())
        tokens.update(adapter._entity_exclude)
        tokens.update(adapter._deictics)

    return tokens


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
        adapter = get_adapter(lang)
        known_tokens = _adapter_known_tokens(adapter)

        overlap = len(tokens & known_tokens)
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
