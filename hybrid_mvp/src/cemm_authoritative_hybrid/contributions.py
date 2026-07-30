"""Closed transient contribution ABI: typed semantic contribution ports.

This module owns :class:`ContributionKind`, :class:`SemanticContribution`,
and :class:`ContributionExpander`.

A :class:`SemanticContribution` is a typed port-bearing unit that connects
grounded designations to structural roles.  Each contribution has typed
input and output ports, a contribution kind from the closed
:class:`ContributionKind` enum, source unit refs, a target ref, and
constraints.  Defaults are indexed by semantic kind; reviewed frame atoms
may refine them only when generation-pinned and linked.

The :class:`ContributionExpander` expands grounded designations into typed
contributions using the :class:`SemanticAffordanceIndex`.  It is bounded by
``RuntimeConfig``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, get_args

from .canonical import stable_ref

__all__ = [
    "ContributionKind",
    "SemanticContribution",
    "ContributionExpander",
]


# ---------------------------------------------------------------------------
# ContributionKind — closed enum
# ---------------------------------------------------------------------------

ContributionKind = Literal[
    "anchor",
    "predicate",
    "binder",
    "reference",
    "scope",
    "discourse",
    "connector",
    "qualifier",
    "literal",
    "open_variable",
]

_VALID_KINDS: frozenset[str] = frozenset(get_args(ContributionKind))  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SemanticContribution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticContribution:
    """A typed semantic contribution with ports.

    Attributes:
        contribution_ref: a stable ref for this contribution.
        kind: the :class:`ContributionKind` of this contribution.
        source_unit_refs: tuple of form unit refs that produced this contribution.
        target_ref: the semantic target ref, or None for open contributions.
        input_ports: tuple of input port names.
        output_ports: tuple of output port names.
        constraints: tuple of ``(key, value)`` constraint pairs.
    """

    contribution_ref: str
    kind: ContributionKind
    source_unit_refs: tuple[str, ...]
    target_ref: str | None
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    constraints: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"invalid contribution kind: {self.kind}")


# ---------------------------------------------------------------------------
# ContributionExpander
# ---------------------------------------------------------------------------


class ContributionExpander:
    """Expands grounded designations into typed semantic contributions.

    Uses the :class:`SemanticAffordanceIndex` to derive contribution kinds
    and ports for each grounded target.  Bounded by ``RuntimeConfig``.

    Args:
        affordance_index: the :class:`SemanticAffordanceIndex`.
        config: the :class:`RuntimeConfig` with bounds.
    """

    def __init__(self, affordance_index: Any, config: Any) -> None:
        self._index = affordance_index
        self._config = config
        self._max_per_unit = getattr(config, "max_affordances_per_target", 4)

    def expand(
        self,
        grounding_result: Any,
        form_lattice: Any,
    ) -> tuple[SemanticContribution, ...]:
        """Expand grounded designations into typed contributions.

        For each designation candidate in ``grounding_result``, derive
        affordance profiles from the target's semantic kind and create
        :class:`SemanticContribution` instances with typed ports.

        Args:
            grounding_result: a :class:`GroundingResult` with designations.
            form_lattice: a :class:`FormLattice` with form units.

        Returns:
            tuple of :class:`SemanticContribution` instances, bounded by
            the configured limits.
        """
        contributions: list[SemanticContribution] = []

        # Build a unit_ref → source_text lookup from the form lattice.
        unit_texts: dict[str, str] = {}
        if form_lattice is not None:
            for unit in getattr(form_lattice, "units", ()):
                unit_texts[unit.unit_ref] = unit.source_text

        for desig in getattr(grounding_result, "designations", ()):
            target_ref = desig.target_ref
            unit_refs = desig.unit_refs
            profiles = self._index.for_target(target_ref)

            for profile in profiles[: self._max_per_unit]:
                for kind in profile.contribution_kinds:
                    contribution = self._make_contribution(
                        kind=kind,
                        source_unit_refs=unit_refs,
                        target_ref=target_ref,
                        input_ports=profile.input_ports,
                        output_ports=profile.output_ports,
                        frame_ref=profile.frame_ref,
                    )
                    contributions.append(contribution)

            if len(contributions) >= self._max_per_unit * len(
                getattr(grounding_result, "designations", ())
            ):
                break

        return tuple(contributions)

    @staticmethod
    def _make_contribution(
        *,
        kind: str,
        source_unit_refs: tuple[str, ...],
        target_ref: str,
        input_ports: tuple[str, ...],
        output_ports: tuple[str, ...],
        frame_ref: str | None,
    ) -> SemanticContribution:
        """Create a single SemanticContribution with a stable ref."""
        constraints: tuple[tuple[str, str], ...] = ()
        if frame_ref is not None:
            constraints = (("frame_ref", frame_ref),)
        return SemanticContribution(
            contribution_ref=stable_ref(
                "contribution",
                {
                    "kind": kind,
                    "target": target_ref,
                    "units": list(source_unit_refs),
                    "inputs": list(input_ports),
                    "outputs": list(output_ports),
                },
            ),
            kind=kind,  # type: ignore[arg-type]
            source_unit_refs=source_unit_refs,
            target_ref=target_ref,
            input_ports=input_ports,
            output_ports=output_ports,
            constraints=constraints,
        )
