"""ContextFrame — context for propositions (actual, reported, hypothetical, etc.).

Import boundary: standard library only → refs, identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import TimeExtent, Provenance


@dataclass(frozen=True, slots=True)
class ContextFrame:
    """Context frame for a proposition.

    context_kind: actual, reported, belief, hypothetical, counterfactual,
                  simulated, quoted, desired, etc.

    Contexts are independent from polarity and modality.
    """
    id: str
    context_kind: str = "actual"
    owner_ref: str | None = None  # Ref[Referent] as opaque string
    parent_ref: str | None = None  # Ref[ContextFrame] for nested contexts
    assumptions: tuple[str, ...] = ()  # Ref[Proposition] refs
    accessibility_policy_ref: str | None = None  # Ref[ContextSchema]
    valid_time: TimeExtent | None = None
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source_id="unknown")
    )
