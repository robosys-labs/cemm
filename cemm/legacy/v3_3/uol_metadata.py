"""Shared loader for UOL semantic metadata from uol_semantics.json.

Both ``ConversationActClassifier`` and ``MeaningPerceptor`` (and any other
component that needs linguistic cue sets) import from here instead of
duplicating hardcoded Python sets.

This fulfils §3.6 of the consolidated architecture:
linguistic data lives in JSON, loaded dynamically — not hardcoded in code.

The JSON file ``uol_semantics.json`` contains entries with ``cue_type``
metadata.  This loader groups aliases by ``cue_type`` into ``cue_sets``
so any component can look up e.g. ``question_starter`` tokens without
hardcoding them.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

_logger = logging.getLogger("cemm.uol_metadata")
_UOL_SEMANTICS_PATH = Path(__file__).parent.parent.parent / "data" / "uol_semantics.json"


def _load() -> tuple[
    dict[str, list[str]],
    dict[str, str],
    dict[str, str],
    dict[str, float],
    dict[str, set[str]],
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, str],
    frozenset[str],
    frozenset[str],
    frozenset[str],
    frozenset[str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, dict[str, str]],
    dict[str, str],
]:
    """Load all UOL semantic metadata from the JSON data file.

    Returns:
        frame_aliases: canonical_key -> [aliases]
        frame_to_act: canonical_key -> act_type
        frame_polarity: canonical_key -> polarity
        frame_intensity: canonical_key -> intensity
        cue_sets: cue_type -> set of aliases belonging to that cue type
        frame_meta: canonical_key -> full metadata dict
        modal_types: modal_token -> modality classification
        conjunction_map: conjunction_token -> relation type
        connective_set: frozenset of all connective tokens
        strong_split_connectives: frozenset of strong split connectives
        subordinating_connectives: frozenset of subordinating connectives
        pure_acknowledgment_phrases: frozenset of acknowledgment tokens
        contractions: contraction -> expansion
        pronoun_to_entity: pronoun -> entity key
        possessive_to_entity: possessive pronoun -> entity key
        possessive_slot_to_predicate: slot word -> {edge_type, property_dimension}
        remember_extra_verbs: verb -> relation key
    """
    if not _UOL_SEMANTICS_PATH.exists():
        return (
            {}, {}, {}, {}, {}, {}, {}, {},
            frozenset(), frozenset(), frozenset(), frozenset(),
            {}, {}, {}, {}, {},
        )
    data = json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))
    entries = data.get("uol_semantics", [])
    frame_aliases: dict[str, list[str]] = {}
    frame_to_act: dict[str, str] = {}
    frame_polarity: dict[str, str] = {}
    frame_intensity: dict[str, float] = {}
    cue_sets: dict[str, set[str]] = {}
    frame_meta: dict[str, dict[str, object]] = {}
    modal_types: dict[str, str] = {}
    conjunction_map: dict[str, str] = {}
    for entry in entries:
        key = entry["canonical_key"]
        aliases = entry.get("aliases", [])
        frame_aliases[key] = aliases
        act_type = entry.get("act_type", "unknown")
        if act_type != "unknown":
            frame_to_act[key] = act_type
        if "polarity" in entry:
            frame_polarity[key] = entry["polarity"]
        if "intensity" in entry:
            frame_intensity[key] = float(entry["intensity"])
        cue_type = entry.get("cue_type")
        if cue_type:
            cue_sets.setdefault(cue_type, set())
            cue_sets[cue_type].update(aliases)
        frame_meta[key] = {
            "act_type": act_type,
            "polarity": entry.get("polarity", "neutral"),
            "intensity": float(entry.get("intensity", 0.5)),
            "cue_type": cue_type,
        }
    modal_types = dict(data.get("modal_types", {}))
    conjunction_map = dict(data.get("conjunction_map", {}))
    connective_set = frozenset(data.get("connective_set", []))
    strong_split_connectives = frozenset(data.get("strong_split_connectives", []))
    subordinating_connectives = frozenset(data.get("subordinating_connectives", []))
    pure_acknowledgment_phrases = frozenset(
        t.replace("'", "") for t in data.get("pure_acknowledgment_phrases", [])
    )
    contractions = dict(data.get("contractions", {}))
    pronoun_to_entity = dict(data.get("pronoun_to_entity", {}))
    possessive_to_entity = dict(data.get("possessive_to_entity", {}))
    possessive_slot_to_predicate = dict(data.get("possessive_slot_to_predicate", {}))
    remember_extra_verbs = dict(data.get("remember_extra_verbs", {}))
    _logger.debug(
        "UOL metadata loaded: %d frames, %d act_types, %d cue_sets, %d modals, %d conjunctions",
        len(frame_aliases),
        len(frame_to_act),
        len(cue_sets),
        len(modal_types),
        len(conjunction_map),
    )
    return (
        frame_aliases, frame_to_act, frame_polarity, frame_intensity,
        cue_sets, frame_meta, modal_types, conjunction_map,
        connective_set, strong_split_connectives, subordinating_connectives,
        pure_acknowledgment_phrases,
        contractions, pronoun_to_entity, possessive_to_entity,
        possessive_slot_to_predicate, remember_extra_verbs,
    )


# Load once at import time — same pattern ConversationActClassifier used.
(
    FRAME_ALIASES,
    FRAME_TO_ACT,
    FRAME_POLARITY,
    FRAME_INTENSITY,
    CUE_SETS,
    FRAME_META,
    MODAL_TYPES,
    CONJUNCTION_MAP,
    CONNECTIVE_SET,
    STRONG_SPLIT_CONNECTIVES,
    SUBORDINATING_CONNECTIVES,
    PURE_ACKNOWLEDGMENT_PHRASES,
    CONTRACTIONS,
    PRONOUN_TO_ENTITY,
    POSSESSIVE_TO_ENTITY,
    POSSESSIVE_SLOT_TO_PREDICATE,
    REMEMBER_EXTRA_VERBS,
) = _load()


def cue_set(name: str) -> frozenset[str]:
    """Return a frozen set of aliases for a cue_type, or empty set.

    Tokens are normalized (apostrophes stripped) to match the
    LanguageAdapter.tokenize normalization (§5.1).
    """
    return frozenset(t.replace("'", "") for t in CUE_SETS.get(name, set()))


def frame_alias_set(canonical_key: str) -> frozenset[str]:
    """Return a frozen set of aliases for a canonical frame key, or empty set.

    Tokens are normalized (apostrophes stripped) to match the
    LanguageAdapter.tokenize normalization (§5.1).
    """
    return frozenset(t.replace("'", "") for t in FRAME_ALIASES.get(canonical_key, []))


def modal_type(token: str) -> str | None:
    """Return the modality classification for a modal token, or None."""
    return MODAL_TYPES.get(token)


def conjunction_relation(token: str) -> str | None:
    """Return the relation type for a conjunction token, or None."""
    return CONJUNCTION_MAP.get(token)


def pure_acknowledgment_set() -> frozenset[str]:
    """Return the frozen set of pure acknowledgment phrases/single tokens.

    Loaded from ``pure_acknowledgment_phrases`` in uol_semantics.json.
    """
    return PURE_ACKNOWLEDGMENT_PHRASES


def contractions() -> dict[str, str]:
    """Return contraction -> expansion mapping from uol_semantics.json."""
    return CONTRACTIONS


def pronoun_to_entity() -> dict[str, str]:
    """Return pronoun -> entity key mapping from uol_semantics.json."""
    return PRONOUN_TO_ENTITY


def possessive_to_entity() -> dict[str, str]:
    """Return possessive pronoun -> entity key mapping from uol_semantics.json."""
    return POSSESSIVE_TO_ENTITY


def possessive_slot_to_predicate() -> dict[str, dict[str, str]]:
    """Return slot word -> {edge_type, property_dimension} from uol_semantics.json."""
    return POSSESSIVE_SLOT_TO_PREDICATE


def remember_extra_verbs() -> dict[str, str]:
    """Return verb -> relation key mapping for remember commands from uol_semantics.json."""
    return REMEMBER_EXTRA_VERBS
