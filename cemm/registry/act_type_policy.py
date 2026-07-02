"""Data-driven act type policy loaded from uol_semantics.json.

This module provides a single loading point for all act type metadata
that was previously hardcoded across operator-level code
(conversation_act.py, decision_router.py, conversation_act_classifier.py,
realizer.py, realization_verifier.py).

Per architecture §10.1.2: "Domain behavior belongs in registry entries,
style policies, permission policies — not in new foundational operators."

All consumers import from this module instead of maintaining their own
hardcoded lists. Adding a new act type now requires only appending to
the ``act_type_metadata`` key in ``uol_semantics.json``.
"""

from __future__ import annotations

import json
from pathlib import Path


_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load() -> dict:
    if not _UOL_SEMANTICS_PATH.exists():
        return {}
    return json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))


_DATA = _load()

ACT_TYPE_METADATA: dict[str, dict] = _DATA.get("act_type_metadata", {})
NO_EVIDENCE_INTENTS: frozenset[str] = frozenset(_DATA.get("no_evidence_intents", []))
DISCOURSE_FRAMES: frozenset[str] = frozenset(_DATA.get("discourse_frames", []))
QUESTION_FRAMES: frozenset[str] = frozenset(_DATA.get("question_frames", []))
INTENT_TEMPLATE_DEFAULT: dict[str, str] = _DATA.get("intent_template_default", {})


def get_metadata(act_type: str) -> dict:
    """Return the metadata dict for *act_type*, or an empty dict."""
    return ACT_TYPE_METADATA.get(act_type, {})


def get_flag(act_type: str, flag: str, default: bool = False) -> bool:
    """Return a boolean flag from act type metadata."""
    return get_metadata(act_type).get(flag, default)


def get_response_mode(act_type: str) -> str:
    """Return the response mode for *act_type*, defaulting to general_conversation."""
    return get_metadata(act_type).get("response_mode", "general_conversation")


def get_default_template(act_type: str) -> str:
    """Return the default template key for *act_type*."""
    return get_metadata(act_type).get("default_template", "general_conversation")


def requires_evidence(act_type: str) -> bool:
    return get_flag(act_type, "requires_evidence")


def allows_memory_write(act_type: str) -> bool:
    return get_flag(act_type, "allows_memory_write")


def is_social(act_type: str) -> bool:
    return get_flag(act_type, "is_social")


def is_creative(act_type: str) -> bool:
    return get_flag(act_type, "is_creative")


def is_repair(act_type: str) -> bool:
    return get_flag(act_type, "is_repair")


def is_evaluative(act_type: str) -> bool:
    return get_flag(act_type, "is_evaluative")


def is_simple_answer(act_type: str) -> bool:
    return get_flag(act_type, "simple_answer")


def is_identity_query(act_type: str) -> bool:
    return get_flag(act_type, "identity_query")


def is_assertion(act_type: str) -> bool:
    return get_flag(act_type, "assertion")


def is_no_evidence_intent(intent: str) -> bool:
    return intent in NO_EVIDENCE_INTENTS


def get_intent_template(intent: str) -> str | None:
    """Return the default template key for a SAG intent, or None if not mapped."""
    return INTENT_TEMPLATE_DEFAULT.get(intent)
