"""Referent — canonical semantic graph node for entities/concepts/etc.

Import boundary: standard library only → refs, identity, surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import Scope, Provenance
from .surface import LexicalFormRef, KindHypothesis


@dataclass(frozen=True, slots=True)
class Referent:
    """A canonical referent in the semantic graph.

    A provisional discourse referent may exist without a durable
    canonical identity.
    """
    id: str
    referent_kind: str  # entity, concept, place, source, schema, self, etc.
    canonical_key: str | None = None
    aliases: tuple[LexicalFormRef, ...] = ()
    kind_hypotheses: tuple[KindHypothesis, ...] = ()
    scope: Scope = field(default_factory=Scope)
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source_id="unknown")
    )
    confidence: float = 0.0
