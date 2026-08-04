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
        consumed_unit_refs: set[str] = set()
        if form_lattice is not None:
            for unit in getattr(form_lattice, "units", ()):
                unit_texts[unit.unit_ref] = unit.source_text

        for desig in getattr(grounding_result, "designations", ()):
            target_ref = desig.target_ref
            unit_refs = desig.unit_refs
            consumed_unit_refs.update(unit_refs)
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

        # Detect typed literal evidence from unconsumed form units.
        # Per R2 plan section 2.6: preserve exact source value for
        # string, integer, and boolean literals.
        if form_lattice is not None:
            for unit in getattr(form_lattice, "units", ()):
                if unit.unit_ref in consumed_unit_refs:
                    continue
                literal_info = _detect_literal(unit.source_text)
                if literal_info is not None:
                    literal_kind, literal_value = literal_info
                    contribution = self._make_literal_contribution(
                        source_unit_ref=unit.unit_ref,
                        literal_kind=literal_kind,
                        literal_value=literal_value,
                    )
                    contributions.append(contribution)
                    consumed_unit_refs.add(unit.unit_ref)

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

    @staticmethod
    def _make_literal_contribution(
        *,
        source_unit_ref: str,
        literal_kind: str,
        literal_value: str,
    ) -> SemanticContribution:
        """Create a typed literal contribution preserving exact source value.

        Per R2 plan section 2.6: typed literal preservation for string,
        integer, and boolean. The literal_value preserves the exact source
        text; the literal_kind records the reviewed type tag.
        """
        constraints = (
            ("literal", literal_value),
            ("literal_kind", literal_kind),
        )
        return SemanticContribution(
            contribution_ref=stable_ref(
                "contribution",
                {
                    "kind": "literal",
                    "literal_kind": literal_kind,
                    "literal_value": literal_value,
                    "units": [source_unit_ref],
                },
            ),
            kind="literal",
            source_unit_refs=(source_unit_ref,),
            target_ref=None,
            input_ports=(),
            output_ports=("role:literal",),
            constraints=constraints,
        )


def _detect_literal(source_text: str) -> tuple[str, str] | None:
    """Detect typed literal evidence from a form unit's source text.

    Returns (literal_kind, literal_value) or None.

    Per R2 plan section 2.6: preserve exact source value for string,
    integer, and boolean. Quoted strings preserve the inner content.
    """
    text = source_text.strip()
    if not text:
        return None
    # Boolean literals (reviewed English surface forms).
    if text.lower() in {"true", "false"}:
        return ("boolean", text.lower())
    # Integer literals (optionally signed digits).
    signed = text
    if signed.startswith(("+", "-")) and len(signed) > 1 and signed[1:].isdigit():
        return ("integer", text)
    if text.isdigit():
        return ("integer", text)
    # Quoted string literals — preserve inner content exactly.
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return ("string", text[1:-1])
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return ("string", text[1:-1])
    return None
