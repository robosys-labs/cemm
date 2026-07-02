"""Compositional intent parser for turn-level meaning extraction.

Extracts semantic roles (subject, modal, process, negation, polarity, target)
from a tokenised surface to support the ConversationActClassifier in
understanding mixed, contextual, or evaluative turns.

This parser is language-agnostic at the structural level: it relies on
token positions and configurable cue sets rather than hardcoded English
syntax. Cue sets are loaded from ``data/classifier_cues.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .text_match import tokenize_surface


_CUES_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_cues() -> dict[str, set[str]]:
    """Load cue sets from UOL semantic entries with cue_type metadata.

    This reads the same uol_semantics.json that backs the registry and
    classifier, ensuring a single source of truth for all language cues.
    """
    if not _CUES_PATH.exists():
        return {}
    data = json.loads(_CUES_PATH.read_text(encoding="utf-8"))
    entries = data.get("uol_semantics", [])
    cue_sets: dict[str, set[str]] = {}
    for entry in entries:
        cue_type = entry.get("cue_type")
        if not cue_type:
            continue
        aliases = entry.get("aliases", [])
        cue_sets.setdefault(cue_type, set()).update(aliases)
    return cue_sets


_CUES = _load_cues()


def _get_cue_set(key: str) -> frozenset[str]:
    """Return a frozen set of cues for *key*, empty if missing."""
    return frozenset(_CUES.get(key, set()))


@dataclass
class CompositionalIntent:
    """Structural decomposition of a single conversational turn."""
    subject: str = ""          # who the turn is about: "self", "user", "entity", "unknown"
    target: str = ""           # who is being addressed/targeted: "self", "user", "entity", "unknown"
    modal: str = ""            # modal verb if present: "can", "should", etc.
    process: str = ""          # main verb/action: "learn", "do", "remember", etc.
    negated: bool = False      # whether negation is present
    polarity: str = "neutral"  # neutral, positive, negative, skeptical
    is_question: bool = False
    question_starter: str = "" # "what", "who", etc. if is_question
    entity_mentions: list[str] = field(default_factory=list)
    raw_tokens: list[str] = field(default_factory=list)

    @property
    def is_self_directed(self) -> bool:
        """True if the turn targets the assistant (self)."""
        return self.target == "self"

    @property
    def is_user_directed(self) -> bool:
        """True if the turn is about the user."""
        return self.subject == "user"

    @property
    def is_skeptical(self) -> bool:
        return self.polarity == "skeptical"

    @property
    def is_capability_query(self) -> bool:
        """True if this looks like a capability question directed at self."""
        capability_modals = _get_cue_set("modal") & {"can", "could", "do", "does"}
        return (
            self.is_question
            and self.is_self_directed
            and self.modal in capability_modals
        )


def parse_intent(text: str) -> CompositionalIntent:
    """Parse *text* into a CompositionalIntent.

    This is a lightweight structural parser — not a full dependency parser.
    It identifies key roles via token positions and cue sets, sufficient
    to disambiguate mixed turns for the ConversationActClassifier.
    """
    tokens = tokenize_surface(text)
    if not tokens:
        return CompositionalIntent()

    token_set = set(tokens)
    first = tokens[0]
    last = tokens[-1]

    # Load cue sets from UOL metadata
    question_starter_cues = _get_cue_set("question_starter")
    negation_cues = _get_cue_set("negation")
    modal_cues = _get_cue_set("modal")
    skeptical_cues = _get_cue_set("skeptical")
    self_target_cues = _get_cue_set("self_target")
    user_subject_cues = _get_cue_set("user_subject")
    capability_modals = modal_cues & {"can", "could", "do", "does"}

    # ── Question detection ────────────────────────────────────────
    is_question = last == "?" or first in question_starter_cues
    question_starter = first if first in question_starter_cues else ""

    # ── Negation ──────────────────────────────────────────────────
    negated = bool(token_set & negation_cues) or "n't" in text.lower()

    # ── Modal ─────────────────────────────────────────────────────
    modal = ""
    for t in tokens:
        if t in modal_cues:
            modal = t
            break

    # ── Subject and target ────────────────────────────────────────
    subject = "unknown"
    target = "unknown"

    # Check for self-target cues (you/your)
    if token_set & self_target_cues:
        target = "self"

    # Check for user-subject cues (i/my/we)
    if token_set & user_subject_cues:
        subject = "user"

    # If question starts with "what can you" / "what do you" → self-targeted
    if is_question and target == "self" and modal in capability_modals:
        subject = "self"

    # ── Process (main verb) ───────────────────────────────────────
    # Heuristic: first non-modal, non-question-starter, non-pronoun token
    skip = modal_cues | question_starter_cues | self_target_cues | user_subject_cues | negation_cues
    process = ""
    for t in tokens:
        if t not in skip and len(t) >= 2:
            process = t
            break

    # ── Polarity ──────────────────────────────────────────────────
    if negated:
        polarity = "negative"
    elif token_set & skeptical_cues:
        polarity = "skeptical"
    elif is_question and target == "self" and modal in capability_modals:
        # "Can you even learn?" → skeptical
        if token_set & skeptical_cues:
            polarity = "skeptical"
        else:
            polarity = "neutral"
    else:
        polarity = "neutral"

    return CompositionalIntent(
        subject=subject,
        target=target,
        modal=modal,
        process=process,
        negated=negated,
        polarity=polarity,
        is_question=is_question,
        question_starter=question_starter,
        raw_tokens=tokens,
    )
