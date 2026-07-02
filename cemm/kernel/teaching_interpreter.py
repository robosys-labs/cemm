from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_TEACHING_PATTERNS_PATH = Path(__file__).parent.parent / "data" / "teaching_patterns.json"


def _load_teaching_patterns() -> dict[str, set[str]]:
    if not _TEACHING_PATTERNS_PATH.exists():
        return {}
    data = json.loads(_TEACHING_PATTERNS_PATH.read_text(encoding="utf-8"))
    return {
        key: set(words) if isinstance(words, list) else words
        for key, words in data.items()
        if key != "meta"
    }


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
    """

    def __init__(self) -> None:
        patterns = _load_teaching_patterns()
        self._definition_triggers = patterns.get("definition_triggers", set())
        self._command_triggers = patterns.get("command_triggers", set())
        self._correction_triggers = patterns.get("correction_triggers", set())
        self._surface_stop_words = patterns.get("surface_stop_words", set())
        self._meaning_stop_words = patterns.get("meaning_stop_words", set())
        self._command_alias_delimiters = patterns.get("command_alias_delimiters", set())
        role_cues = patterns.get("role_cues", {})
        self._process_cues = set(role_cues.get("process", []))
        self._state_cues = set(role_cues.get("state", []))
        self._modifier_cues = set(role_cues.get("modifier", []))

    def interpret(self, text: str) -> list[TeachingEvent]:
        """Return candidate teaching events from the input text."""
        events: list[TeachingEvent] = []
        lower = text.lower().strip()
        words = [w.strip(".,!?;:\"'()[]{}") for w in lower.split()]
        if not words:
            return events

        is_correction = any(w in self._correction_triggers for w in words[:3])

        # "no, X means Y" / correction
        if is_correction:
            for i, w in enumerate(words):
                if w in self._definition_triggers:
                    surface = self._extract_surface(words, i)
                    meaning = self._extract_meaning(words, i)
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
        for i, w in enumerate(words):
            if w in self._definition_triggers:
                surface = self._extract_surface(words, i)
                meaning = self._extract_meaning(words, i)
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
            if trigger in lower:
                events.extend(self._extract_command_alias(lower, trigger))

        return events

    def _extract_surface(self, words: list[str], trigger_index: int) -> str:
        """Extract the surface token before a definition trigger."""
        if trigger_index == 0:
            return ""
        # Walk left from trigger to collect the first noun/unknown token
        for i in range(trigger_index - 1, -1, -1):
            w = words[i].strip(".,!?;:\"'()[]{}")
            if w and w not in self._surface_stop_words:
                return w
        return ""

    def _extract_meaning(self, words: list[str], trigger_index: int) -> str:
        """Extract the meaning phrase after a definition trigger."""
        rest = words[trigger_index + 1:]
        if not rest:
            return ""
        # Stop at sentence boundaries or trailing punctuation; boundary words are
        # loaded from cemm/data/teaching_patterns.json.
        meaning_words: list[str] = []
        for w in rest:
            bare = w.strip(".,!?;:\"'()[]{}")
            if bare in self._meaning_stop_words:
                break
            meaning_words.append(bare)
        return " ".join(meaning_words)

    def _extract_command_alias(self, text: str, trigger: str) -> list[TeachingEvent]:
        """Extract 'when I say X, do Y' style command aliases.

        The delimiter that separates the surface form from the command (e.g.,
        " do ") is loaded from cemm/data/teaching_patterns.json so it can be
        language-specific without hardcoding English surface forms.
        """
        events: list[TeachingEvent] = []
        parts = text.split(trigger)
        if len(parts) < 2:
            return events
        after = parts[1].strip()
        chunks = after.split(",")
        if not chunks:
            return events
        first = chunks[0].strip()
        alias = first.split()[0] if first else ""
        command = ""
        if len(chunks) > 1:
            command = chunks[1].strip()
        else:
            for delimiter in self._command_alias_delimiters:
                if delimiter in after:
                    command = after.split(delimiter, 1)[1].strip()
                    break
        if alias and command:
            events.append(TeachingEvent(
                kind="command_alias",
                surface=alias,
                meaning=command,
                role="command_alias",
                confidence=0.6,
            ))
        return events

    def _infer_role(self, surface: str, meaning: str) -> str:
        """Infer whether the learned surface is a process, state, modifier, etc.

        Cues are loaded from cemm/data/teaching_patterns.json so they can be
        language-specific without hardcoding English surface forms.
        """
        meaning_lower = meaning.lower()
        if any(c in self._modifier_cues for c in meaning_lower.split()):
            return "modifier"
        if any(c in self._state_cues for c in meaning_lower.split()):
            return "state"
        if any(c in self._process_cues for c in meaning_lower.split()):
            return "process"
        return "unknown"
