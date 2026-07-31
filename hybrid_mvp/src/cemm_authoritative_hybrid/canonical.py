"""Canonical serialization and stable identity helpers.

This module owns canonical bytes, SHA-256 file hashing and stable refs. It
serializes Python primitives, dataclasses, mappings, sets, tuples and decimals
with sorted keys and explicit type tags so that two semantically equal payloads
always produce byte-identical canonical bytes regardless of insertion order.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping
import hashlib
import json

if TYPE_CHECKING:
    from torch import Tensor as TensorLike
else:
    TensorLike = Any


__all__ = [
    "canonical_bytes",
    "stable_ref",
    "tensor_identity",
    "sha256_file",
    "read_canonical_json",
    "write_canonical_json",
    "canonical_json",
    "stable",
    "is_variable",
    "is_existential",
    "app_link",
]


def _tag(tag: str, body: bytes) -> bytes:
    return tag.encode("ascii") + b":" + body


def canonical_json(value: Any) -> str:
    """Return a canonical JSON string for ``value`` with sorted keys.

    This is the JSON-serialization helper formerly known as ``canonical`` in
    :mod:`cemm_authoritative_hybrid.types`. It is kept separate from
    :func:`canonical_bytes` (which produces type-tagged byte encodings) and
    :func:`stable_ref` (which hashes namespace + canonical bytes).
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def stable(namespace: str, *parts: Any) -> str:
    """Return ``{namespace}:{sha256[:24]}`` over the canonical JSON of ``parts``.

    This is the legacy stable-ref helper from :mod:`cemm_authoritative_hybrid.types`.
    It differs from :func:`stable_ref` (which hashes namespace + canonical bytes
    of a single payload) and is kept for backward compatibility with the
    proposition graph and persistence modules.
    """
    return f"{namespace}:{hashlib.sha256(canonical_json(parts).encode('utf-8')).hexdigest()[:24]}"


def is_variable(value: Any) -> bool:
    """Return True if ``value`` is a variable ref (starts with ``?``)."""
    return isinstance(value, str) and value.startswith("?")


def is_existential(value: Any) -> bool:
    """Return True if ``value`` is an existential ref (starts with ``$``)."""
    return isinstance(value, str) and value.startswith("$")


def app_link(value: Any) -> str | None:
    """Return the application ref linked by ``value`` if it is an app link.

    An app link is a mapping with exactly the key ``"app"`` whose value is a
    non-empty string. Returns ``None`` otherwise.
    """
    if isinstance(value, Mapping) and set(value) == {"app"}:
        ref = value.get("app")
        return str(ref) if isinstance(ref, str) and ref else None
    return None


def canonical_bytes(obj: Any) -> bytes:
    """Return a deterministic byte encoding of ``obj`` with type tags.

    Mappings and sets are serialized with sorted keys so that insertion order
    does not change identity. Dataclasses are serialized by their fields in
    sorted field-name order.
    """
    if obj is None:
        return b"none:"
    if obj is True:
        return b"bool:1"
    if obj is False:
        return b"bool:0"
    if isinstance(obj, bool):  # defensive; covered above
        return b"bool:1" if obj else b"bool:0"
    if isinstance(obj, int):
        return _tag("int", str(obj).encode("utf-8"))
    if isinstance(obj, float):
        # repr(float) is the shortest round-trippable representation and is
        # stable across runs/platforms for finite values.
        return _tag("float", repr(obj).encode("utf-8"))
    if isinstance(obj, str):
        return _tag("str", obj.encode("utf-8"))
    if isinstance(obj, (bytes, bytearray)):
        return _tag("bytes", bytes(obj))
    if isinstance(obj, Decimal):
        return _tag("decimal", str(obj).encode("utf-8"))
    if isinstance(obj, Mapping):
        return _tag("dict", _canonical_mapping(obj))
    if is_dataclass(obj) and not isinstance(obj, type):
        return _tag("dataclass", _canonical_dataclass(obj))
    if isinstance(obj, tuple):
        return _tag("tuple", _canonical_sequence(obj))
    if isinstance(obj, list):
        return _tag("list", _canonical_sequence(obj))
    if isinstance(obj, (set, frozenset)):
        return _tag(
            "frozenset" if isinstance(obj, frozenset) else "set",
            _canonical_set(obj),
        )
    # Fallback: deterministic JSON for anything else (e.g. nested dicts from
    # JSON that are plain ``dict``). This keeps the function total for the
    # payloads used by the artifact contract.
    return _tag(
        "json",
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8"),
    )


def _canonical_sequence(seq: Any) -> bytes:
    parts = [canonical_bytes(item) for item in seq]
    body = b"\x1f".join(parts)
    return str(len(parts)).encode("ascii") + b"\x1f" + body


def _canonical_set(s: Any) -> bytes:
    # Sort by canonical bytes so set identity is order-independent.
    encoded = sorted(canonical_bytes(item) for item in s)
    body = b"\x1f".join(encoded)
    return str(len(encoded)).encode("ascii") + b"\x1f" + body


def _canonical_mapping(m: Mapping) -> bytes:
    pairs = sorted((canonical_bytes(k), canonical_bytes(v)) for k, v in m.items())
    body = b"\x1f".join(k + b"\x1e" + v for k, v in pairs)
    return str(len(pairs)).encode("ascii") + b"\x1f" + body


def _canonical_dataclass(obj: Any) -> bytes:
    flds = sorted(fields(obj), key=lambda f: f.name)
    pairs = []
    for f in flds:
        pairs.append(canonical_bytes(f.name) + b"\x1e" + canonical_bytes(getattr(obj, f.name)))
    body = b"\x1f".join(pairs)
    name = type(obj).__name__
    return (
        name.encode("utf-8")
        + b"\x1f"
        + str(len(pairs)).encode("ascii")
        + b"\x1f"
        + body
    )


def stable_ref(namespace: str, payload: Any) -> str:
    """Return ``{namespace}:{digest[:24]}`` over namespace + canonical bytes."""
    digest = hashlib.sha256(
        namespace.encode("utf-8") + b"\0" + canonical_bytes(payload)
    ).hexdigest()
    return f"{namespace}:{digest[:24]}"


def tensor_identity(tensors: Mapping[str, TensorLike]) -> str:
    """Hash sorted name, dtype, shape and every contiguous CPU byte.

    The hash is order-independent with respect to the mapping key order and is
    sensitive to any byte, shape or dtype change in any tensor.
    """
    h = hashlib.sha256()
    for name in sorted(tensors):
        tensor = tensors[name]
        t_cpu = tensor.detach().cpu().contiguous()
        meta = canonical_bytes(
            {"name": name, "dtype": str(t_cpu.dtype), "shape": list(int(d) for d in t_cpu.shape)}
        )
        h.update(meta)
        h.update(bytes(t_cpu.numpy().tobytes()))
    return f"tensor:{h.hexdigest()[:24]}"


def sha256_file(path: str | Path) -> str:
    """Return the hex SHA-256 digest of the file at ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_canonical_json(path: str | Path, obj: Any) -> None:
    """Write ``obj`` as canonical JSON (sorted keys, compact separators)."""
    Path(path).write_text(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def read_canonical_json(path: str | Path) -> Any:
    """Read canonical JSON written by :func:`write_canonical_json`."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
