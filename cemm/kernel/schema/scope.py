"""Scope resolution for schema access — not truth context.

Import boundary: standard library only → model.identity.
"""
from __future__ import annotations

from ..model.identity import Scope, ScopeLevel


def resolve_scope(
    requested: Scope,
    candidates: tuple[Scope, ...],
) -> tuple[Scope, ...]:
    """Filter candidate scopes by the requested access level.

    Narrower access scope does not blindly replace wider meaning.
    A user-scoped revision may represent a user theory or private
    convention without overriding an active global schema.
    """
    result: list[Scope] = []
    for cand in candidates:
        if cand.level == requested.level:
            result.append(cand)
        elif cand.is_wider_than(requested):
            result.append(cand)
    return tuple(result)
