"""CapabilityClassifier — compositional 'can you X?' parser.

Implements Gap 10 from cemm_v3_1_operational_meaning_spine.md.

Parses capability questions like "can you browse the web?" or "can you play
music?" and returns a structured CapabilityAnswer with supported/unsupported
status, description, and limitations.

This is not a core architecture change — it's a self-affordance query layer
that prevents capability questions from being treated as entity questions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


_CAPABILITY_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "capabilities.json"

# Patterns for detecting capability questions
_CAN_YOU_PATTERNS = [
    re.compile(r"can\s+you\s+(\w[\w\s]*?)(?:\?|$)", re.IGNORECASE),
    re.compile(r"could\s+you\s+(\w[\w\s]*?)(?:\?|$)", re.IGNORECASE),
    re.compile(r"are\s+you\s+able\s+to\s+(\w[\w\s]*?)(?:\?|$)", re.IGNORECASE),
    re.compile(r"are\s+you\s+capable\s+of\s+(\w[\w\s]*?)(?:\?|$)", re.IGNORECASE),
]


@dataclass
class CapabilityRecord:
    """A single native capability."""
    capability_key: str = ""
    aliases: list[str] = field(default_factory=list)
    supported: bool = False
    requires_tool: str = ""
    description: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass
class CapabilityAnswer:
    """Result of a capability query."""
    matched: bool = False
    capability_key: str = ""
    supported: bool = False
    description: str = ""
    limitations: list[str] = field(default_factory=list)
    requires_tool: str = ""
    raw_query: str = ""
    confidence: float = 0.0


class CapabilityClassifier:
    """Parses capability questions and returns structured answers.

    Loads capability records from data/capabilities.json and matches
    compositional 'can you + ACTION?' patterns against them.
    """

    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or _CAPABILITY_DATA_PATH
        self._capabilities: list[CapabilityRecord] = []
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for entry in data:
                self._capabilities.append(CapabilityRecord(
                    capability_key=entry.get("capability_key", ""),
                    aliases=entry.get("aliases", []),
                    supported=entry.get("supported", False),
                    requires_tool=entry.get("requires_tool", ""),
                    description=entry.get("description", ""),
                    limitations=entry.get("limitations", []),
                ))

    def classify(self, text: str) -> CapabilityAnswer | None:
        """Check if text is a capability question and return an answer.

        Returns None if the text is not a capability question.
        """
        text_lower = text.lower().strip()

        # Extract the action phrase from the question
        action_phrase = ""
        for pattern in _CAN_YOU_PATTERNS:
            match = pattern.search(text_lower)
            if match:
                action_phrase = match.group(1).strip()
                break

        if not action_phrase:
            return None

        # Match against capability aliases
        action_words = set(action_phrase.split())
        for cap in self._capabilities:
            for alias in cap.aliases:
                alias_words = set(alias.split())
                # Check substring match or significant word overlap
                if alias in action_phrase or action_phrase in alias:
                    return CapabilityAnswer(
                        matched=True,
                        capability_key=cap.capability_key,
                        supported=cap.supported,
                        description=cap.description,
                        limitations=list(cap.limitations),
                        requires_tool=cap.requires_tool,
                        raw_query=action_phrase,
                        confidence=0.8,
                    )
                # Word overlap: if all alias words are in the action phrase
                if alias_words and alias_words.issubset(action_words):
                    return CapabilityAnswer(
                        matched=True,
                        capability_key=cap.capability_key,
                        supported=cap.supported,
                        description=cap.description,
                        limitations=list(cap.limitations),
                        requires_tool=cap.requires_tool,
                        raw_query=action_phrase,
                        confidence=0.7,
                    )

        # Unknown capability — still a capability question
        return CapabilityAnswer(
            matched=True,
            capability_key="unknown",
            supported=False,
            description="I'm not sure if I can do that yet. You can teach me what it means.",
            raw_query=action_phrase,
            confidence=0.4,
        )

    @property
    def capabilities(self) -> list[CapabilityRecord]:
        return list(self._capabilities)
