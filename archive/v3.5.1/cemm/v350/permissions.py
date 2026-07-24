"""Permission-scope mechanics for CEMM v3.5 runtime authorization.

Permission refs remain data.  This module only evaluates an explicitly supplied
scope relation; it never infers privacy from concept names or string prefixes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class PermissionScope:
    permission_ref: str
    includes_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.permission_ref.strip():
            raise ValueError("permission_ref must be non-empty")
        if len(self.includes_refs) != len(set(self.includes_refs)):
            raise ValueError("permission includes refs must be unique")


class PermissionScopeEvaluator:
    """Evaluate monotone disclosure using an explicit finite scope graph."""

    def __init__(self, scopes: Iterable[PermissionScope] = ()) -> None:
        direct: dict[str, set[str]] = {}
        for item in scopes:
            direct.setdefault(item.permission_ref, set()).update(item.includes_refs)
        # Public is mechanically the least restrictive readable source scope.
        # It is not inserted as a semantic fact; it is a runtime access primitive.
        direct.setdefault("public", set())
        self._direct = {key: frozenset(values) for key, values in direct.items()}
        self._closure = self._compile_closure()

    def _compile_closure(self) -> Mapping[str, frozenset[str]]:
        result: dict[str, frozenset[str]] = {}
        for root in self._direct:
            seen: set[str] = set()
            stack = [root]
            while stack:
                current = stack.pop()
                for child in self._direct.get(current, ()):
                    if child == root:
                        raise ValueError(f"permission scope cycle reaches itself: {root}")
                    if child not in seen:
                        seen.add(child)
                        stack.append(child)
            result[root] = frozenset(seen)
        return result

    def can_read(self, source_permission_ref: str | None, audience_permission_ref: str) -> bool:
        source = source_permission_ref or ""
        if not source or not audience_permission_ref:
            return False
        if source == "public":
            return True
        if source == audience_permission_ref:
            return True
        return source in self._closure.get(audience_permission_ref, frozenset())

    def common_scope(self, refs: Iterable[str]) -> str | None:
        values = tuple(dict.fromkeys(ref for ref in refs if ref))
        if not values:
            return None
        # Pick the narrowest supplied scope that can read all sources.
        candidates = [
            candidate
            for candidate in values
            if all(self.can_read(source, candidate) for source in values)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda ref: (len(self._closure.get(ref, ())), ref))
