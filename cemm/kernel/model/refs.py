"""Typed opaque references and frozen map for the canonical semantic model.

Import boundary: standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Mapping, Iterator, Any

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Ref(Generic[T]):
    """Typed opaque reference to a canonical record.

    Internal IDs never substitute for public lexical surfaces.
    """
    id: str

    def __str__(self) -> str:
        return self.id


class FrozenMap(Mapping[str, Any]):
    """Immutable hashable mapping for feature dictionaries.

    Wraps a frozenset of key-value pairs to provide Mapping interface
    while remaining hashable and frozen.
    """

    __slots__ = ("_data", "_hash")

    def __init__(self, items: Mapping[str, Any] | None = None) -> None:
        if items is None:
            object.__setattr__(self, "_data", frozenset())
        else:
            object.__setattr__(self, "_data", frozenset(items.items()))
        object.__setattr__(self, "_hash", hash(self._data))

    def __getitem__(self, key: str) -> Any:
        for k, v in self._data:
            if k == key:
                return v
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (k for k, _ in self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrozenMap):
            return self._data == other._data
        return NotImplemented

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)
