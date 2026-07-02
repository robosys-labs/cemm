from __future__ import annotations

from typing import Any


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

    _DEFINITION_TRIGGERS = {
        "means", "is", "are", "was", "refers to", "stands for", "short for",
    }
    _COMMAND_TRIGGERS = {
        "when i say", "say", "call", "use", "from now on", "let's say", "if i say",
    }
    _CORRECTION_TRIGGERS = {
        "no", "not", "wrong", "actually", "correction", "i mean", "i meant",
    }

    def __init__(self) -> None:
        pass

    def interpret(self, text: str) -> list[TeachingEvent]:
        """Return candidate teaching events from the input text."""
        events: list[TeachingEvent] = []
        lower = text.lower().strip()
        words = lower.split()
        if not words:
            return events

        # "X means Y" / "X is Y" / "X refers to Y"
        for i, w in enumerate(words):
            if w in self._DEFINITION_TRIGGERS:
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
        for trigger in self._COMMAND_TRIGGERS:
            if trigger in lower:
                events.extend(self._extract_command_alias(lower, trigger))

        # "no, X means Y" / correction
        if any(w in self._CORRECTION_TRIGGERS for w in words[:3]):
            # Find the corrected definition
            for i, w in enumerate(words):
                if w in self._DEFINITION_TRIGGERS:
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

        return events

    def _extract_surface(self, words: list[str], trigger_index: int) -> str:
        """Extract the surface token before a definition trigger."""
        if trigger_index == 0:
            return ""
        # Walk left from trigger to collect the first noun/unknown token
        for i in range(trigger_index - 1, -1, -1):
            w = words[i].strip(".,!?;:\"'()[]{}")
            if w and w not in {"this", "that", "these", "those", "the", "a", "an"}:
                return w
        return ""

    def _extract_meaning(self, words: list[str], trigger_index: int) -> str:
        """Extract the meaning phrase after a definition trigger."""
        rest = words[trigger_index + 1:]
        if not rest:
            return ""
        # Stop at sentence boundaries or trailing punctuation
        stop_words = {"but", "and", "or", "so", "then", "because", "when", "if"}
        meaning_words: list[str] = []
        for w in rest:
            bare = w.strip(".,!?;:\"'()[]{}")
            if bare in stop_words:
                break
            meaning_words.append(bare)
        return " ".join(meaning_words)

    def _extract_command_alias(self, text: str, trigger: str) -> list[TeachingEvent]:
        """Extract 'when I say X, do Y' style command aliases."""
        events: list[TeachingEvent] = []
        parts = text.split(trigger)
        if len(parts) < 2:
            return events
        after = parts[1].strip()
        # Split on comma or "do"
        chunks = after.split(",")
        if not chunks:
            return events
        first = chunks[0].strip()
        alias = first.split()[0] if first else ""
        command = ""
        if len(chunks) > 1:
            command = chunks[1].strip()
        elif " do " in after:
            command = after.split(" do ", 1)[1].strip()
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
        """Infer whether the learned surface is a process, state, modifier, etc."""
        meaning_lower = meaning.lower()
        process_cues = {"remember", "save", "store", "note", "recall", "retrieve", "do", "run", "go", "say", "tell", "ask", "answer", "make", "take", "get", "call"}
        state_cues = {"is", "are", "was", "were", "be", "feel", "seem", "look", "sound", "happy", "sad", "angry", "tired", "busy", "beautiful", "good", "bad", "groovy"}
        modifier_cues = {"quietly", "secretly", "privately", "quickly", "slowly", "carefully", "loudly", "softly", "gently", "really", "very", "extremely", "quite", "pretty", "fairly", "slightly", "maybe", "probably", "definitely"}
        if any(c in modifier_cues for c in meaning_lower.split()):
            return "modifier"
        if any(c in state_cues for c in meaning_lower.split()):
            return "state"
        if any(c in process_cues for c in meaning_lower.split()):
            return "process"
        return "unknown"
