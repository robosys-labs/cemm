"""Public semantic value validation for realization slots."""

from __future__ import annotations

from typing import Any

from ...kernel.proposition_semantics import is_internal_identifier

_INTERNAL_SOURCES = frozenset({"role_placeholder", "role_binding", "query_open_port"})
_INTERNAL_KINDS = frozenset({"role", "port", "placeholder", "internal"})


def public_value(value: Any, *, features: dict[str, Any] | None = None, slot_kind: str = "surface") -> str:
    text = str(value or "").strip()
    if not text or is_internal_identifier(text):
        return ""
    metadata = features or {}
    if str(metadata.get("source", "") or "") in _INTERNAL_SOURCES:
        return ""
    if str(metadata.get("semantic_kind", "") or "") in _INTERNAL_KINDS:
        return ""
    if metadata.get("placeholder") or metadata.get("internal"):
        return ""
    if str(metadata.get("proposition_mode", "") or "") == "queried":
        return ""
    if slot_kind in _INTERNAL_KINDS:
        return ""
    return text
