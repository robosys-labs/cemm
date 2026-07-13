"""Failure types for the canonical semantic model.

Import boundary: standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TypedFailure:
    """A typed failure with recovery information."""
    failure_kind: str
    detail: str = ""
    recoverable: bool = False
    retry_after_seconds: float | None = None
