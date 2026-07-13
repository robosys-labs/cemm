"""Surface span and lexical form references.

Import boundary: standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .refs import FrozenMap


@dataclass(frozen=True, slots=True)
class SurfaceSpan:
    """Character/token span in the original surface signal."""
    signal_ref: str
    start: int
    end: int
    raw_text: str
    token_start: int = 0
    token_end: int = 0
    features: FrozenMap = field(default_factory=FrozenMap)


@dataclass(frozen=True, slots=True)
class LexicalFormRef:
    """Reference to a lexical form with language tag."""
    surface: str
    language_tag: str = "und"
    normalised: str | None = None
    features: FrozenMap = field(default_factory=FrozenMap)


@dataclass(frozen=True, slots=True)
class KindHypothesis:
    """Hypothesis about a referent's kind."""
    kind: str
    confidence: float
    evidence_refs: tuple[str, ...] = ()
