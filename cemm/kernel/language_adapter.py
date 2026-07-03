"""LanguageAdapter — interface for language-specific surface-to-atom mapping.

Each language pack provides:
- pronouns.json: surface → (entity_type, role, source)
- question_cues.json: question detection cues
- modals.json: modality markers (should, can, must, etc.)
- negations.json: negation markers
- contractions.json: contraction expansion map
- surface_bindings.seed.json: seed surface→frame_key mappings
- state_keywords.json: surface → (state_key, dimension, polarity)
- action_keywords.json: surface → action_key
- affect_markers.json: affect_type → marker set

The adapter loads these and provides structured methods that MeaningPerceptor
calls instead of using hardcoded English dicts.

Cross-lingual design: all adapters produce the SAME atom types (ReferentAtom,
ActionAtom, StateAtom, etc.) — only the surface-to-atom mapping differs.
Structural inference downstream is language-agnostic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PronounMapping:
    """Mapping from a pronoun surface to structural roles."""
    entity_type: str
    role: str
    source: str = "pronoun"


@dataclass
class StateMapping:
    """Mapping from a state keyword to structural state metadata."""
    state_key: str
    dimension: str
    polarity: str


@dataclass
class LanguagePackData:
    """Container for all loaded language pack data."""
    language: str = "en"
    pronouns: dict[str, PronounMapping] = field(default_factory=dict)
    deictic_words: set[str] = field(default_factory=set)
    entity_exclude: set[str] = field(default_factory=set)
    state_keywords: dict[str, StateMapping] = field(default_factory=dict)
    need_keywords: dict[str, tuple[str, float]] = field(default_factory=dict)
    action_keywords: dict[str, str] = field(default_factory=dict)
    affect_markers: dict[str, set[str]] = field(default_factory=dict)
    question_cues: set[str] = field(default_factory=set)
    modals: dict[str, str] = field(default_factory=dict)
    negations: set[str] = field(default_factory=set)
    contractions: dict[str, str] = field(default_factory=dict)


class LanguageAdapter:
    """Interface for language-specific surface-to-atom mapping.

    Subclasses must implement all methods. The base class provides
    shared utilities for tokenization and text processing.
    """

    language: str = "en"

    def __init__(self, pack_data: LanguagePackData | None = None) -> None:
        self._data = pack_data or LanguagePackData()

    @property
    def data(self) -> LanguagePackData:
        return self._data

    def normalize(self, text: str) -> str:
        """Normalize text for this language (default: lowercase + strip)."""
        return text.lower().strip()

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into word tokens (Unicode-aware)."""
        return re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE)

    def detect_question(self, tokens: list[str], punctuation: dict[str, Any]) -> bool:
        """Detect whether the token sequence is a question."""
        if punctuation.get("has_question_mark"):
            return True
        if tokens and tokens[0] in self._data.question_cues:
            return True
        return False

    def map_pronouns(self, tokens: list[str]) -> list[tuple[str, PronounMapping]]:
        """Map pronoun tokens to PronounMapping entries.

        Returns list of (surface, mapping) pairs.
        """
        results = []
        for token in tokens:
            if token in self._data.pronouns:
                results.append((token, self._data.pronouns[token]))
        return results

    def map_deictics(self, tokens: list[str]) -> list[str]:
        """Return deictic words found in tokens."""
        return [t for t in tokens if t in self._data.deictic_words]

    def map_actions(self, tokens: list[str]) -> list[tuple[str, str]]:
        """Map action keyword tokens to action keys.

        Returns list of (surface, action_key) pairs.
        """
        results = []
        for token in tokens:
            if token in self._data.action_keywords:
                results.append((token, self._data.action_keywords[token]))
        return results

    def map_states(self, tokens: list[str]) -> list[tuple[str, StateMapping]]:
        """Map state keyword tokens to StateMapping entries.

        Returns list of (surface, mapping) pairs.
        """
        results = []
        for token in tokens:
            if token in self._data.state_keywords:
                results.append((token, self._data.state_keywords[token]))
        return results

    def map_needs(self, tokens: list[str]) -> list[tuple[str, str, float]]:
        """Map need keyword tokens to (surface, need_key, intensity) tuples."""
        results = []
        for token in tokens:
            if token in self._data.need_keywords:
                need_key, intensity = self._data.need_keywords[token]
                results.append((token, need_key, intensity))
        return results

    def expand_contractions(self, text: str) -> str:
        """Expand contractions in text."""
        result = text
        for contraction, expansion in self._data.contractions.items():
            result = result.replace(contraction, expansion)
        return result

    def detect_affect(self, text_lower: str) -> list[tuple[str, str]]:
        """Detect affect markers in text.

        Returns list of (affect_type, marker) pairs.
        """
        results = []
        for affect_type, markers in self._data.affect_markers.items():
            for marker in markers:
                if marker in text_lower:
                    results.append((affect_type, marker))
        return results

    def detect_modality(self, tokens: list[str]) -> str:
        """Detect modality from tokens.

        Returns 'proposed', 'desired', or 'observed'.
        """
        token_set = set(tokens)
        for modal, modality in self._data.modals.items():
            if modal in token_set:
                return modality
        return "observed"

    def detect_negation(self, tokens: list[str]) -> bool:
        """Detect whether the tokens contain negation."""
        token_set = set(tokens)
        return bool(token_set & self._data.negations)

    def is_entity_exclude(self, token_lower: str) -> bool:
        """Check if a token should be excluded from entity candidates."""
        return token_lower in self._data.entity_exclude

    def detect_holder(self, tokens: list[str]) -> str:
        """Detect the holder for state/need atoms based on pronoun context.

        Returns 'user', 'self', or 'third_party'.
        """
        token_set = set(tokens)
        # Check for self pronouns (you, your, yourself)
        self_pronouns = {
            s for s, m in self._data.pronouns.items()
            if m.entity_type == "self"
        }
        if token_set & self_pronouns:
            return "self"
        # Check for third person pronouns (he, she, him, her, they, them)
        third_pronouns = {
            s for s, m in self._data.pronouns.items()
            if m.entity_type == "person"
        }
        if token_set & third_pronouns:
            return "third_party"
        return "user"


def load_language_pack(language: str, pack_dir: Path | None = None) -> LanguagePackData:
    """Load a language pack from data files.

    Args:
        language: Language code (e.g., "en", "ig", "yo", "es").
        pack_dir: Directory containing language pack files.
                  Defaults to cemm/data/languages/{language}/

    Returns:
        LanguagePackData with all loaded mappings.
    """
    if pack_dir is None:
        pack_dir = Path(__file__).parent.parent / "data" / "languages" / language

    data = LanguagePackData(language=language)

    # Load pronouns
    pronouns_path = pack_dir / "pronouns.json"
    if pronouns_path.exists():
        pron_data = json.loads(pronouns_path.read_text(encoding="utf-8"))
        for surface, mapping in pron_data.items():
            data.pronouns[surface] = PronounMapping(
                entity_type=mapping.get("entity_type", "unknown"),
                role=mapping.get("role", "topic"),
                source=mapping.get("source", "pronoun"),
            )

    # Load deictic words
    deictic_path = pack_dir / "deictic_words.json"
    if deictic_path.exists():
        data.deictic_words = set(json.loads(deictic_path.read_text(encoding="utf-8")))

    # Load entity exclude
    exclude_path = pack_dir / "entity_exclude.json"
    if exclude_path.exists():
        data.entity_exclude = set(json.loads(exclude_path.read_text(encoding="utf-8")))

    # Load state keywords
    state_path = pack_dir / "state_keywords.json"
    if state_path.exists():
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        for surface, mapping in state_data.items():
            data.state_keywords[surface] = StateMapping(
                state_key=mapping.get("state_key", surface),
                dimension=mapping.get("dimension", "general"),
                polarity=mapping.get("polarity", "neutral"),
            )

    # Load need keywords
    need_path = pack_dir / "need_keywords.json"
    if need_path.exists():
        need_data = json.loads(need_path.read_text(encoding="utf-8"))
        for surface, mapping in need_data.items():
            data.need_keywords[surface] = (
                mapping.get("need_key", surface),
                float(mapping.get("intensity", 0.5)),
            )

    # Load action keywords
    action_path = pack_dir / "action_keywords.json"
    if action_path.exists():
        data.action_keywords = json.loads(action_path.read_text(encoding="utf-8"))

    # Load affect markers
    affect_path = pack_dir / "affect_markers.json"
    if affect_path.exists():
        affect_data = json.loads(affect_path.read_text(encoding="utf-8"))
        for affect_type, markers in affect_data.items():
            data.affect_markers[affect_type] = set(markers)

    # Load question cues
    question_path = pack_dir / "question_cues.json"
    if question_path.exists():
        data.question_cues = set(json.loads(question_path.read_text(encoding="utf-8")))

    # Load modals
    modals_path = pack_dir / "modals.json"
    if modals_path.exists():
        modals_data = json.loads(modals_path.read_text(encoding="utf-8"))
        for surface, modality in modals_data.items():
            data.modals[surface] = modality

    # Load negations
    negations_path = pack_dir / "negations.json"
    if negations_path.exists():
        data.negations = set(json.loads(negations_path.read_text(encoding="utf-8")))

    # Load contractions
    contractions_path = pack_dir / "contractions.json"
    if contractions_path.exists():
        data.contractions = json.loads(contractions_path.read_text(encoding="utf-8"))

    return data


def get_adapter(language: str = "en") -> LanguageAdapter:
    """Get a LanguageAdapter for the given language.

    Falls back to English if the requested language pack is not available.
    """
    pack_dir = Path(__file__).parent.parent / "data" / "languages" / language
    if not pack_dir.exists():
        # Fall back to English
        language = "en"
    pack_data = load_language_pack(language)
    adapter = LanguageAdapter(pack_data)
    adapter.language = language
    return adapter
