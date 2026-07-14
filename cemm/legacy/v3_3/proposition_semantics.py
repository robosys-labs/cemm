"""Canonical proposition-mode helpers for relation candidates and UOL atoms.

This module intentionally contains no language-specific surface logic. It is the
single compatibility seam for reading proposition metadata from both the new
explicit RelationAtom fields and older feature dictionaries.
"""

from __future__ import annotations

from typing import Any, Iterable

ASSERTED = "asserted"
QUERIED = "queried"
COMMANDED = "commanded"
HYPOTHETICAL = "hypothetical"
REPORTED = "reported"
NEGATED = "negated"

VALID_PROPOSITION_MODES = frozenset({
    ASSERTED,
    QUERIED,
    COMMANDED,
    HYPOTHETICAL,
    REPORTED,
    NEGATED,
})

_INTERNAL_ID_PREFIXES = (
    "uol_", "uolcand_", "cand_", "hyp_", "gap_", "omf_", "oc_",
    "rf_", "ab_", "pred_", "br_", "aff_", "cx_", "trace:", "port:",
    "entity:",
)


def _features(value: Any) -> dict[str, Any]:
    features = getattr(value, "features", {}) or {}
    return features if isinstance(features, dict) else {}


def proposition_mode(value: Any, default: str = ASSERTED) -> str:
    explicit = getattr(value, "proposition_mode", "") or _features(value).get(
        "proposition_mode", ""
    )
    mode = str(explicit or default).strip().lower()
    return mode if mode in VALID_PROPOSITION_MODES else default


def open_roles(value: Any) -> tuple[str, ...]:
    explicit = getattr(value, "open_roles", None)
    if explicit is None:
        explicit = _features(value).get("open_roles", ())
    if isinstance(explicit, str):
        explicit = [explicit]
    return tuple(dict.fromkeys(str(role).strip() for role in (explicit or ()) if str(role).strip()))


def has_open_role(value: Any, role: str) -> bool:
    return role in open_roles(value)


def is_asserted(value: Any) -> bool:
    return proposition_mode(value) in {ASSERTED, REPORTED}


def is_queried(value: Any) -> bool:
    return proposition_mode(value) == QUERIED


def can_materialize_domain_edge(value: Any) -> bool:
    return is_asserted(value) and not open_roles(value)


def is_role_placeholder(value: Any) -> bool:
    source = str(getattr(value, "source", "") or "")
    key = str(getattr(value, "key", "") or "")
    features = _features(value)
    return (
        source in {"role_placeholder", "role_binding"}
        or key.startswith("role:")
        or bool(features.get("role_placeholder"))
    )


def is_internal_identifier(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered.startswith(_INTERNAL_ID_PREFIXES):
        return True
    if lowered.startswith("concept:role:"):
        return True
    # Canonical concept IDs are internal unless a caller deliberately resolves
    # them to a public surface before realization.
    if lowered.startswith("concept:") and " " not in lowered:
        return True
    return False


def contains_internal_identifier(values: Iterable[str]) -> bool:
    return any(is_internal_identifier(value) for value in values)
