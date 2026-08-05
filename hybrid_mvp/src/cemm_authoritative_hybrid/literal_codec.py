"""Exact typed-literal decoding for Semantic Expression ABI 1."""

from __future__ import annotations

from typing import Any

_LITERAL_KINDS = frozenset({"string", "integer", "boolean"})


def decode_literal_value(literal_kind: str, source_value: str) -> str | int | bool:
    """Decode one canonical literal source into the scalar required by ABI 1."""
    if type(literal_kind) is not str or literal_kind not in _LITERAL_KINDS:
        raise ValueError("literal kind is not admitted")
    if type(source_value) is not str:
        raise TypeError("literal source value must be an exact string")
    if literal_kind == "string":
        return source_value
    if literal_kind == "boolean":
        if source_value == "true":
            return True
        if source_value == "false":
            return False
        raise ValueError("boolean literal must be canonical true or false")
    if not source_value:
        raise ValueError("integer literal must be non-empty")
    digits = source_value[1:] if source_value[0] in {"+", "-"} else source_value
    if not digits or not digits.isascii() or not digits.isdigit():
        raise ValueError("integer literal must contain canonical ASCII digits")
    value = int(source_value, 10)
    if not -(2**63) <= value < 2**63:
        raise ValueError("integer literal exceeds signed 64-bit range")
    return value


def decode_literal_slot(slot: Any) -> tuple[str, str | int | bool]:
    """Decode a ContributionSlot-like value without inventing missing type data."""
    source_value = getattr(slot, "literal_value", None)
    constraints = getattr(slot, "constraints", None)
    if type(source_value) is not str:
        raise ValueError("literal contribution has no exact source value")
    if not isinstance(constraints, tuple):
        raise TypeError("literal contribution constraints must be a tuple")
    kinds = tuple(value for key, value in constraints if key == "literal_kind")
    if len(kinds) != 1:
        raise ValueError("literal contribution requires exactly one literal_kind")
    literal_kind = kinds[0]
    return literal_kind, decode_literal_value(literal_kind, source_value)
