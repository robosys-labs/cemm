from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .text_match import (
    tokenize_surface,
    find_token_subsequence,
    find_all_token_subsequences,
)


_TEACHING_PATTERNS_PATH = Path(__file__).parent.parent / "data" / "teaching_patterns.json"
_VOCAB_PATH = Path(__file__).parent.parent / "data" / "vocab.json"


def _load_teaching_patterns() -> dict[str, set[str]]:
    if not _TEACHING_PATTERNS_PATH.exists():
        return {}
    data = json.loads(_TEACHING_PATTERNS_PATH.read_text(encoding="utf-8"))
    return {
        key: set(words) if isinstance(words, list) else words
        for key, words in data.items()
        if key != "meta"
    }


def _load_role_cues(vocab_path: Path | None = None) -> dict[str, set[str]]:
    """Load semantic role cues from the shared vocabulary file.

    Teaching role inference and surface tagging share the same process,
    modifier, and state cues so that a taught word is classified consistently
    with how it will be tagged at runtime.
    """
    path = vocab_path or _VOCAB_PATH
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    cues = data.get("semantic_role_cues", {})
    return {key: set(words) for key, words in cues.items()}


class TeachingEvent:
    """A candidate teaching event detected in surface text."""

    def __init__(
        self,
        kind: str,
        surface: str,
        meaning: str,
        role: str,
        confidence: float = 0.5,
        scope: str = "user",
        examples: list[str] | None = None,
    ) -> None:
        self.kind = kind
        self.surface = surface
        self.meaning = meaning
        self.role = role
        self.confidence = confidence
        self.scope = scope
        self.examples = list(examples or [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "surface": self.surface,
            "meaning": self.meaning,
            "role": self.role,
            "confidence": self.confidence,
            "scope": self.scope,
            "examples": list(self.examples),
        }


class TeachingInterpreter:
    """Detect surface patterns that teach meaning to CEMM.

    Patterns include definitions ("zibble means save this"), command aliases
    ("when I say zibble, remember this"), entity aliases ("call this a zorp"),
    and corrections ("no, zibble means ..."). The interpreter produces candidate
    teaching events, not committed memory. Downstream layers decide whether to
    store them based on permission, confidence, and context.

    Role cues are loaded from the shared vocabulary file so that teaching role
    inference and surface tagging use the same semantic categories.
    """

    def __init__(self, role_cues: dict[str, set[str]] | None = None) -> None:
        patterns = _load_teaching_patterns()
        self._definition_triggers = patterns.get("definition_triggers", set())
        self._command_triggers = patterns.get("command_triggers", set())
        self._correction_triggers = patterns.get("correction_triggers", set())
        self._surface_stop_words = patterns.get("surface_stop_words", set())
        self._meaning_stop_words = patterns.get("meaning_stop_words", set())
        self._command_alias_delimiters = patterns.get("command_alias_delimiters", set())
        cues = role_cues or _load_role_cues()
        self._process_cues = cues.get("process", set())
        self._state_cues = cues.get("state", set())
        self._modifier_cues = cues.get("modifier", set())

    def interpret(self, text: str) -> list[TeachingEvent]:
        """Return candidate teaching events from the input text."""
        events: list[TeachingEvent] = []
        words = tokenize_surface(text)
        if not words:
            return events

        is_correction = any(
            find_token_subsequence(tokenize_surface(trigger), words) == 0
            for trigger in self._correction_triggers
        )

        # "no, X means Y" / correction
        if is_correction:
            for trigger in self._definition_triggers:
                trigger_tokens = tokenize_surface(trigger)
                for start in find_all_token_subsequences(trigger_tokens, words):
                    surface = self._extract_surface(words, start)
                    meaning = self._extract_meaning(words, start + len(trigger_tokens))
                    if surface and meaning:
                        events.append(TeachingEvent(
                            kind="correction",
                            surface=surface,
                            meaning=meaning,
                            role=self._infer_role(surface, meaning),
                            confidence=0.7,
                        ))
            if events:
                return events

        # "X means Y" / "X is Y" / "X refers to Y"
        for trigger in self._definition_triggers:
            trigger_tokens = tokenize_surface(trigger)
            for start in find_all_token_subsequences(trigger_tokens, words):
                surface = self._extract_surface(words, start)
                meaning = self._extract_meaning(words, start + len(trigger_tokens))
                if surface and meaning:
                    role = self._infer_role(surface, meaning)
                    events.append(TeachingEvent(
                        kind="definition",
                        surface=surface,
                        meaning=meaning,
                        role=role,
                        confidence=0.6,
                    ))

        # "when I say X, do Y" / "call this X"
        for trigger in self._command_triggers:
            trigger_tokens = tokenize_surface(trigger)
            for start in find_all_token_subsequences(trigger_tokens, words):
                events.extend(self._extract_command_alias(words, start, len(trigger_tokens)))

        return events

    def _extract_surface(self, words: list[str], trigger_start: int) -> str:
        """Extract the surface token before a definition trigger."""
        if trigger_start == 0:
            return ""
        # Walk left from trigger to collect the first noun/unknown token
        for i in range(trigger_start - 1, -1, -1):
            w = words[i]
            if w and w not in self._surface_stop_words:
                return w
        return ""

    def _extract_meaning(self, words: list[str], trigger_end: int) -> str:
        """Extract the meaning phrase after a definition trigger."""
        rest = words[trigger_end:]
        if not rest:
            return ""
        # Stop at sentence boundaries or trailing punctuation; boundary words are
        # loaded from cemm/data/teaching_patterns.json.
        meaning_words: list[str] = []
        for w in rest:
            if w in self._meaning_stop_words:
                break
            meaning_words.append(w)
        return " ".join(meaning_words)

    def _extract_command_alias(
        self,
        words: list[str],
        trigger_start: int,
        trigger_length: int,
    ) -> list[TeachingEvent]:
        """Extract 'when I say X, do Y' style command aliases.

        The delimiter that separates the surface form from the command (e.g.,
        " do ") is loaded from cemm/data/teaching_patterns.json so it can be
        language-specific without hardcoding English surface forms.
        """
        events: list[TeachingEvent] = []
        after = words[trigger_start + trigger_length:]
        if not after:
            return events

        for delimiter in self._command_alias_delimiters:
            delimiter_tokens = tokenize_surface(delimiter)
            idx = find_token_subsequence(delimiter_tokens, after)
            if idx is not None:
                alias = self._extract_surface(after, idx)
                meaning = self._extract_meaning(after, idx + len(delimiter_tokens))
                if alias and meaning:
                    events.append(TeachingEvent(
                        kind="command_alias",
                        surface=alias,
                        meaning=meaning,
                        role="command_alias",
                        confidence=0.6,
                    ))
                break

        return events

    def _infer_role(self, surface: str, meaning: str) -> str:
        """Infer whether the learned surface is a process, state, modifier, etc.

        Cues are loaded from cemm/data/teaching_patterns.json so they can be
        language-specific without hardcoding English surface forms.
        """
        meaning_tokens = tokenize_surface(meaning)
        meaning_set = set(meaning_tokens)
        if self._modifier_cues and self._modifier_cues & meaning_set:
            return "modifier"
        if self._state_cues and self._state_cues & meaning_set:
            return "state"
        if self._process_cues and self._process_cues & meaning_set:
            return "process"
        return "unknown"
