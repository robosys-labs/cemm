from __future__ import annotations

from typing import Any

from .ner_tagger import NERTagger


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
    """

    def __init__(self, ner_tagger: NERTagger | None = None) -> None:
        self._ner = ner_tagger

    # Common surface cues for semantic roles
    _PROCESS_WORDS = {
        "remember", "save", "store", "note", "recall", "retrieve", "find",
        "search", "look", "get", "make", "take", "go", "come", "say", "tell",
        "ask", "answer", "know", "learn", "teach", "explain", "show", "give",
        "send", "write", "read", "call", "name", "mean", "work", "do", "run",
    }
    _MODIFIER_WORDS = {
        "quietly", "secretly", "privately", "quickly", "slowly", "carefully",
        "loudly", "softly", "gently", "really", "very", "extremely", "quite",
        "pretty", "fairly", "slightly", "maybe", "probably", "definitely",
    }
    _RELATION_WORDS = {
        "means", "is", "are", "was", "were", "called", "named", "known",
        "like", "as", "for", "about", "with", "from", "to", "of", "in",
        "when", "while", "before", "after", "because", "so", "if", "then",
    }
    _KNOWN_LEXEMES = {
        "zibble", "zorp", "groovy", "moonlight", "nah", "lol", "haha",
        "ouch", "wow", "yay", "aww", "boo", "meh", "huh", "erm", "uhh",
    }

    def tag(self, words: list[str], unknown_tokens: list[str] | None = None) -> list[str]:
        """Return combined semantic BIO tags for the token sequence."""
        tags: list[str] = []
        unknowns = {t.lower() for t in (unknown_tokens or [])}
        for i, w in enumerate(words):
            wl = w.lower().strip(".,!?;:\"'()[]{}")
            if not wl:
                tags.append("O")
                continue
            # Unknown lexeme -> candidate learnable word
            if wl in unknowns or (wl in self._KNOWN_LEXEMES and len(wl) > 3):
                if i == 0 or not tags[-1].startswith("B-UNKNOWN_LEXEME"):
                    tags.append("B-UNKNOWN_LEXEME")
                else:
                    tags.append("I-UNKNOWN_LEXEME")
                continue
            # Process/action candidate
            if wl in self._PROCESS_WORDS:
                if i == 0 or not tags[-1].startswith("B-PROCESS"):
                    tags.append("B-PROCESS")
                else:
                    tags.append("I-PROCESS")
                continue
            # Modifier candidate
            if wl in self._MODIFIER_WORDS:
                if i == 0 or not tags[-1].startswith("B-MODIFIER"):
                    tags.append("B-MODIFIER")
                else:
                    tags.append("I-MODIFIER")
                continue
            # Relation candidate
            if wl in self._RELATION_WORDS:
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
