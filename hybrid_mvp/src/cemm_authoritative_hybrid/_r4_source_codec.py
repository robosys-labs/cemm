"""Private strict codec seam for reviewed R4.1 source contracts."""
from __future__ import annotations

from dataclasses import is_dataclass
import json
import re
from typing import Any, Callable, Mapping, TypeVar

from .r3_codec import exact_bool, exact_fields, exact_int, exact_text

MAX_R4_SOURCE_BYTES = 16 * 1024 * 1024
MAX_R4_SOURCE_RECORDS = 4_096
MAX_R4_REFS_PER_RECORD = 128
MAX_R4_TEXT_CHARS = 16_384

REVIEW_PROVENANCE_PREFIXES = ("source_review:",)
REVIEWER_PREFIXES = ("reviewer:",)

_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*:[^\s:][^\s]*\Z")
_CONTENT_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*:[0-9a-f]{24}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_REVISION_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")

_T = TypeVar("_T")


def construct(cls: type[_T], **values: object) -> _T:
    obj = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(obj, name, value)
    return obj


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    if type(value) is not dict:
        raise TypeError("canonical JSON payload must be an exact dict")
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise TypeError("JSON object keys must be exact strings")
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise ValueError(f"non-finite JSON value: {value}")


def strict_decode(
    raw: object,
    decoder: Callable[[Mapping[str, Any]], _T],
    *,
    owner: str,
    maximum: int = MAX_R4_SOURCE_BYTES,
) -> _T:
    if type(raw) is not bytes:
        raise TypeError(f"serialized {owner} must be exact bytes")
    if not raw or len(raw) > maximum:
        raise ValueError(f"serialized {owner} violates byte bounds")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"serialized {owner} is not strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise TypeError(f"serialized {owner} must contain one exact object")
    if raw != canonical_json_bytes(value):
        raise ValueError(f"serialized {owner} bytes are not canonical")
    return decoder(value)


def exact_ref(value: object, name: str, *, prefix: str | None = None) -> str:
    text = exact_text(value, name)
    if _REF_RE.fullmatch(text) is None:
        raise ValueError(f"{name} is not an admitted reference")
    if prefix is not None and not text.startswith(prefix):
        raise ValueError(f"{name} must use the {prefix} namespace")
    return text


def exact_abi(value: object, expected: int, owner: str) -> int:
    if type(value) is not int or value != expected:
        raise ValueError(f"unsupported {owner} ABI")
    return value


def exact_content_ref(value: object, name: str, *, prefix: str | None = None) -> str:
    text = exact_text(value, name)
    if _CONTENT_REF_RE.fullmatch(text) is None:
        raise ValueError(f"{name} is not an admitted content ref")
    if prefix is not None and not text.startswith(prefix):
        raise ValueError(f"{name} must use the {prefix} namespace")
    return text


def exact_case_ref(value: object, name: str = "source_case_ref") -> str:
    return exact_content_ref(value, name, prefix="expanded_case_v2:")


def exact_review_refs(
    value: object,
    name: str = "review_refs",
    *,
    maximum: int = MAX_R4_REFS_PER_RECORD,
) -> tuple[str, ...]:
    refs = exact_content_ref_tuple(value, name, nonempty=True, maximum=maximum)
    if any(not ref.startswith(REVIEW_PROVENANCE_PREFIXES) for ref in refs):
        raise ValueError(f"{name} must contain typed review provenance refs")
    return refs


def exact_reviewer_refs(
    value: object,
    name: str = "reviewer_refs",
    *,
    maximum: int = MAX_R4_REFS_PER_RECORD,
) -> tuple[str, ...]:
    refs = exact_ref_tuple(value, name, nonempty=True, maximum=maximum)
    if any(not ref.startswith(REVIEWER_PREFIXES) for ref in refs):
        raise ValueError(f"{name} must contain typed reviewer refs")
    return refs


def exact_ref_tuple(
    value: object,
    name: str,
    *,
    nonempty: bool,
    maximum: int = MAX_R4_REFS_PER_RECORD,
    prefix: str | None = None,
    canonical_order: bool = True,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    refs = tuple(exact_ref(item, f"{name} item", prefix=prefix) for item in value)
    if len(refs) != len(set(refs)):
        raise ValueError(f"{name} must contain unique refs")
    if canonical_order and any(left >= right for left, right in zip(refs, refs[1:])):
        raise ValueError(f"{name} must be in canonical order")
    return refs


def exact_content_ref_tuple(
    value: object,
    name: str,
    *,
    nonempty: bool,
    maximum: int = MAX_R4_REFS_PER_RECORD,
    prefix: str | None = None,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    refs = tuple(exact_content_ref(item, f"{name} item", prefix=prefix) for item in value)
    if len(refs) != len(set(refs)):
        raise ValueError(f"{name} must contain unique refs")
    if any(left >= right for left, right in zip(refs, refs[1:])):
        raise ValueError(f"{name} must be in canonical order")
    return refs


def wire_ref_tuple(
    value: object,
    name: str,
    *,
    nonempty: bool,
    maximum: int = MAX_R4_REFS_PER_RECORD,
    prefix: str | None = None,
    canonical_order: bool = True,
) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    return exact_ref_tuple(
        tuple(value),
        name,
        nonempty=nonempty,
        maximum=maximum,
        prefix=prefix,
        canonical_order=canonical_order,
    )


def wire_content_ref_tuple(
    value: object,
    name: str,
    *,
    nonempty: bool,
    maximum: int = MAX_R4_REFS_PER_RECORD,
    prefix: str | None = None,
) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    return exact_content_ref_tuple(
        tuple(value), name, nonempty=nonempty, maximum=maximum, prefix=prefix
    )


def exact_value_tuple(
    value: object,
    name: str,
    expected_type: type[_T],
    *,
    nonempty: bool,
    maximum: int,
    identity: Callable[[_T], object],
    canonical_order: bool = True,
) -> tuple[_T, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    if any(type(item) is not expected_type or not is_dataclass(item) for item in value):
        raise TypeError(f"{name} must contain exact {expected_type.__name__} values")
    rows = tuple(value)
    identities = tuple(identity(row) for row in rows)
    if len(identities) != len(set(identities)):
        raise ValueError(f"{name} contains duplicate identities")
    if canonical_order and any(
        left >= right for left, right in zip(identities, identities[1:])
    ):
        raise ValueError(f"{name} must be in canonical order")
    return rows


def wire_value_tuple(
    value: object,
    name: str,
    decoder: Callable[[Mapping[str, Any]], _T],
    *,
    nonempty: bool,
    maximum: int,
) -> tuple[_T, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    if any(type(item) is not dict for item in value):
        raise TypeError(f"{name} rows must be exact objects")
    return tuple(decoder(item) for item in value)


def exact_sha256(value: object, name: str) -> str:
    text = exact_text(value, name, maximum=64)
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be lowercase SHA-256 hex")
    return text


def exact_revision(value: object, name: str) -> str:
    text = exact_text(value, name, maximum=64)
    if _REVISION_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be a full lowercase Git object id")
    return text


__all__ = [
    "MAX_R4_REFS_PER_RECORD",
    "MAX_R4_SOURCE_BYTES",
    "MAX_R4_SOURCE_RECORDS",
    "MAX_R4_TEXT_CHARS",
    "canonical_json_bytes",
    "exact_abi",
    "exact_bool",
    "exact_case_ref",
    "exact_content_ref",
    "exact_content_ref_tuple",
    "exact_fields",
    "exact_int",
    "exact_ref",
    "exact_ref_tuple",
    "exact_review_refs",
    "exact_reviewer_refs",
    "exact_revision",
    "exact_sha256",
    "exact_text",
    "exact_value_tuple",
    "strict_decode",
    "wire_ref_tuple",
    "wire_content_ref_tuple",
    "wire_value_tuple",
]
