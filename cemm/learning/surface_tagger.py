from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ner_tagger import NERTagger
from ..learning.lexeme_memory import LexemeMemory


_SURFACE_ROLE_WORDS_PATH = Path(__file__).parent.parent / "data" / "surface_role_words.json"


def _load_surface_role_words() -> dict[str, set[str]]:
    if not _SURFACE_ROLE_WORDS_PATH.exists():
        return {}
    data = json.loads(_SURFACE_ROLE_WORDS_PATH.read_text(encoding="utf-8"))
    return {key: set(words) for key, words in data.items() if key != "meta"}


# Lightweight semantic role tags beyond pure named entities
SEMANTIC_TAGS = [
    "O",
    "B-PROCESS", "I-PROCESS",
    "B-STATE", "I-STATE",
    "B-MODIFIER", "I-MODIFIER",
    "B-RELATION", "I-RELATION",
    "B-COMMAND_ALIAS", "I-COMMAND_ALIAS",
    "B-UNKNOWN_LEXEME", "I-UNKNOWN_LEXEME",
]

SEMANTIC_TAG_TO_ROLE = {
    "PROCESS": "process",
    "STATE": "state",
    "MODIFIER": "modifier",
    "RELATION": "relation",
    "COMMAND_ALIAS": "command_alias",
    "UNKNOWN_LEXEME": "unknown_lexeme",
}


class SurfaceTagger:
    """Surface-to-meaning tagger combining NER with lightweight semantic roles.

    Keeps the original Pi-friendly structured perceptron model for named entities
    and adds rule-based semantic role hints for unknown lexemes, processes, and
    modifiers. This is the bridge between raw text and the semantic event graph.

    Unknown lexemes are sourced from the upstream normalizer's ``unknown_tokens``
    list and then filtered against the shared vocabulary and lexeme memory, so
    there is a single source of truth for what counts as a known token.
    """

    def __init__(
        self,
        ner_tagger: NERTagger | None = None,
        known_words: set[str] | None = None,
        lexeme_memory: LexemeMemory | None = None,
    ) -> None:
        self._ner = ner_tagger
        self._known_words = set(known_words or set())
        self._lexeme_memory = lexeme_memory
        role_words = _load_surface_role_words()
        self._process_words = role_words.get("process", set())
        self._modifier_words = role_words.get("modifier", set())
        self._relation_words = role_words.get("relation", set())

    def _is_known(self, word: str) -> bool:
        """Return True if the word is already in the shared vocabulary or lexeme memory."""
        if word in self._known_words:
            return True
        if self._lexeme_memory is not None and self._lexeme_memory.lookup_active(word) is not None:
            return True
        return False

    def tag(self, words: list[str], unknown_tokens: list[str] | None = None) -> list[str]:
        """Return combined semantic BIO tags for the token sequence."""
        tags: list[str] = []
        unknowns = {t.lower() for t in (unknown_tokens or [])}
        for i, w in enumerate(words):
            wl = w.lower().strip(".,!?;:\"'()[]{}")
            if not wl:
                tags.append("O")
                continue
            # Unknown lexeme -> candidate learnable word.  The source of truth is the
            # normalizer's unknown_tokens list, filtered by the shared vocabulary and
            # lexeme memory so a word is never tagged as both known and unknown.
            if wl in unknowns and not self._is_known(wl):
                if i == 0 or not tags[-1].startswith("B-UNKNOWN_LEXEME"):
                    tags.append("B-UNKNOWN_LEXEME")
                else:
                    tags.append("I-UNKNOWN_LEXEME")
                continue
            # Process/action candidate
            if wl in self._process_words:
                if i == 0 or not tags[-1].startswith("B-PROCESS"):
                    tags.append("B-PROCESS")
                else:
                    tags.append("I-PROCESS")
                continue
            # Modifier candidate
            if wl in self._modifier_words:
                if i == 0 or not tags[-1].startswith("B-MODIFIER"):
                    tags.append("B-MODIFIER")
                else:
                    tags.append("I-MODIFIER")
                continue
            # Relation candidate
            if wl in self._relation_words:
                if i == 0 or not tags[-1].startswith("B-RELATION"):
                    tags.append("B-RELATION")
                else:
                    tags.append("I-RELATION")
                continue
            tags.append("O")
        return tags

    def extract_semantic_spans(
        self,
        words: list[str],
        unknown_tokens: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract semantic spans from surface tagging."""
        tags = self.tag(words, unknown_tokens)
        spans: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        scores: list[float] = []
        for i, (word, tag) in enumerate(zip(words, tags)):
            if tag.startswith("B-"):
                if current:
                    current["confidence"] = sum(scores) / len(scores) if scores else 0.6
                    spans.append(current)
                    scores = []
                label = tag[2:]
                current = {
                    "text": word,
                    "label": label,
                    "role": SEMANTIC_TAG_TO_ROLE.get(label, "unknown"),
                    "start": i,
                    "end": i + 1,
                }
                scores = [0.6]
            elif tag.startswith("I-") and current and current["label"] == tag[2:]:
                current["text"] += " " + word
                current["end"] = i + 1
                scores.append(0.6)
            else:
                if current:
                    current["confidence"] = sum(scores) / len(scores) if scores else 0.6
                    spans.append(current)
                    current = None
                    scores = []
        if current:
            current["confidence"] = sum(scores) / len(scores) if scores else 0.6
            spans.append(current)
        return spans

    def extract_entities(self, words: list[str]) -> list[dict[str, Any]]:
        """Forward to the learned NER tagger if available."""
        if self._ner is None:
            return []
        return self._ner.extract_entities(words)

    def extract_all(
        self,
        words: list[str],
        unknown_tokens: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return both NER entities and semantic role spans."""
        entities = self.extract_entities(words)
        spans = self.extract_semantic_spans(words, unknown_tokens)
        # Merge entities and semantic spans, preferring entities for known tokens
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for e in entities:
            key = (e.get("text", "").lower(), e.get("role", ""))
            if key not in seen:
                seen.add(key)
                merged.append(e)
        for s in spans:
            key = (s.get("text", "").lower(), s.get("role", ""))
            if key not in seen:
                seen.add(key)
                merged.append(s)
        return merged
