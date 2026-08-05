"""Strict bounded codec helpers shared by R3 and R4 artifacts."""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .persistence import RevisionPin

MAX_REF_CHARS = 512
MAX_TEXT_CHARS = 16_384
MAX_ROWS = 512
MAX_PAIRS = 512


def exact_text(value: object, name: str, *, allow_empty: bool = False, maximum: int = MAX_REF_CHARS) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value and not allow_empty:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return value


def optional_text(value: object, name: str, *, maximum: int = MAX_REF_CHARS) -> str | None:
    if value is None:
        return None
    return exact_text(value, name, maximum=maximum)


def exact_int(value: object, name: str, *, minimum: int = 0, maximum: int = 2**63 - 1) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be exact int")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the admitted bound")
    return value


def exact_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be exact bool")
    return value


def exact_refs(value: object, name: str, *, nonempty: bool = False, maximum: int = MAX_ROWS) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    result = tuple(exact_text(item, f"{name} item") for item in value)
    if nonempty and not result:
        raise ValueError(f"{name} must be nonempty")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must contain unique refs")
    return result


def exact_pairs(value: object, name: str, *, maximum: int = MAX_PAIRS, unique_first: bool = False) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not tuple or len(row) != 2:
            raise TypeError(f"{name} rows must be exact pairs")
        rows.append((exact_text(row[0], f"{name} key"), exact_text(row[1], f"{name} value", maximum=MAX_TEXT_CHARS)))
    if unique_first and len(rows) != len({row[0] for row in rows}):
        raise ValueError(f"{name} keys must be unique")
    return tuple(rows)


def exact_pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    rebuilt = RevisionPin.from_dict(value.as_dict())
    if rebuilt != value:
        raise ValueError("revision_pin is non-canonical")
    return value


def exact_fields(value: object, fields: frozenset[str], name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{name} payload must be an exact dict")
    if frozenset(value) != fields:
        missing = sorted(fields - frozenset(value))
        unknown = sorted(frozenset(value) - fields)
        raise ValueError(f"{name} fields mismatch: missing={missing}, unknown={unknown}")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{name} field names must be exact str")
    return value


def wire_refs(value: object, name: str, *, nonempty: bool = False, maximum: int = MAX_ROWS) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    return exact_refs(tuple(value), name, nonempty=nonempty, maximum=maximum)


def wire_pairs(value: object, name: str, *, maximum: int = MAX_PAIRS, unique_first: bool = False) -> tuple[tuple[str, str], ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not list or len(row) != 2:
            raise TypeError(f"{name} wire rows must be two-item lists")
        rows.append((row[0], row[1]))
    return exact_pairs(tuple(rows), name, maximum=maximum, unique_first=unique_first)


def freeze_json(value: object, *, depth: int = 0) -> object:
    if depth > 16:
        raise ValueError("JSON value exceeds maximum depth")
    if value is None or type(value) in {bool, int, float, str}:
        if type(value) is str and len(value) > MAX_TEXT_CHARS:
            raise ValueError("JSON string exceeds bound")
        if type(value) is float and (value != value or value in {float('inf'), float('-inf')}):
            raise ValueError("JSON floats must be finite")
        return value
    if type(value) is tuple or type(value) is list:
        if len(value) > MAX_ROWS:
            raise ValueError("JSON sequence exceeds bound")
        return tuple(freeze_json(item, depth=depth + 1) for item in value)
    if isinstance(value, Mapping):
        if len(value) > MAX_ROWS:
            raise ValueError("JSON mapping exceeds bound")
        return MappingProxyType({
            exact_text(key, "JSON key", maximum=256): freeze_json(item, depth=depth + 1)
            for key, item in value.items()
        })
    raise TypeError("value is not bounded canonical JSON")


def thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [thaw_json(item) for item in value]
    return value


def canonical_refs(values: Iterable[str], *, maximum: int = MAX_ROWS) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(values))
    return exact_refs(result, "canonical refs", maximum=maximum)
