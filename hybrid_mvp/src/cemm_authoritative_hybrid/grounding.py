"""Bounded grounding: indexed exact-designation lookup and adapter-pinned evidence.

This module owns :class:`DesignationCandidate`, :class:`ReferenceRequirement`,
:class:`GroundedItem`, :class:`GroundingResult`, and :class:`Grounder`.

The :class:`Grounder` performs indexed exact-designation lookup via the
authority's :class:`DesignationIndex`, participant/deictic binding, or
adapter-schema-pinned nonlinguistic grounding.  It does **not** manufacture
atoms for unknown surfaces — instead it emits a typed
:class:`ReferenceRequirement` with ``kind="designation"``.  It does **not**
choose operators and does **not** inspect internal ref spelling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import stable_ref
from .forms import EvidenceItem, FormResolver

__all__ = [
    "DesignationCandidate",
    "ReferenceRequirement",
    "GroundedItem",
    "GroundingResult",
    "Grounder",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignationCandidate:
    """A candidate designation linking units to a semantic target.

    Attributes:
        unit_refs: tuple of form unit refs that produced this candidate.
        target_ref: the semantic target ref (e.g. ``"entity:door"``).
        designation_fact_ref: a stable ref for the designation fact.
        score: the candidate score (0.0–1.0).
        provenance_refs: tuple of provenance refs.
    """

    unit_refs: tuple[str, ...]
    target_ref: str
    designation_fact_ref: str
    score: float
    provenance_refs: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceRequirement:
    """An unresolved reference requirement.

    Attributes:
        unit_ref: the form unit ref that needs resolution.
        kind: the requirement kind (``"designation"``, ``"participant"``,
            ``"deictic"``, ``"entity"``, or ``"unknown"``).
        required_kind: the required atom kind, or None.
        resolved_ref: the resolved target ref, or None if unresolved.
    """

    unit_ref: str
    kind: str
    required_kind: str | None
    resolved_ref: str | None = None


@dataclass(frozen=True)
class GroundedItem:
    """A grounded evidence item linked to a semantic target.

    Attributes:
        source_ref: the source evidence item ref.
        source_kind: ``"text"``, ``"sensor"``, or ``"operation"``.
        target_ref: the resolved semantic target ref.
        unit_refs: tuple of form unit refs involved.
    """

    source_ref: str
    source_kind: str
    target_ref: str
    unit_refs: tuple[str, ...]


@dataclass(frozen=True)
class GroundingResult:
    """The result of grounding evidence.

    Attributes:
        designations: tuple of resolved :class:`DesignationCandidate`.
        unresolved: tuple of unresolved :class:`ReferenceRequirement`.
        grounded_items: tuple of :class:`GroundedItem`.
        created_refs: tuple of refs created by grounding (always empty —
            the grounder never manufactures atoms).
        provenance_refs: tuple of provenance refs from all evidence.
    """

    designations: tuple[DesignationCandidate, ...]
    unresolved: tuple[ReferenceRequirement, ...]
    grounded_items: tuple[GroundedItem, ...]
    created_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]


# ---------------------------------------------------------------------------
# Grounder
# ---------------------------------------------------------------------------


class Grounder:
    """Grounds evidence via indexed exact-designation lookup.

    The grounder uses the authority's :class:`DesignationIndex` for surface
    lookup.  For unknown surfaces it emits a :class:`ReferenceRequirement`
    with ``kind="designation"`` — it never manufactures atoms.  For sensor
    evidence it uses adapter-schema-pinned grounding.

    It does **not** choose operators and does **not** inspect internal ref
    spelling.
    """

    def __init__(
        self,
        authority: Any,
        config: Any,
        form_pack: Mapping[str, Any] | None = None,
        form_pack_hash: str = "",
        designation_store: Any = None,
    ) -> None:
        self._authority = authority
        self._config = config
        self._form_pack = dict(form_pack) if form_pack else {}
        self._form_pack_hash = form_pack_hash
        self._designation_store = designation_store
        self._resolver = (
            FormResolver(self._form_pack, config) if self._form_pack else None
        )
        self._language = self._form_pack.get("language", "en")

    @property
    def form_pack_hash(self) -> str:
        """The SHA-256 hash of the language form pack."""
        return self._form_pack_hash

    # -- public API -----------------------------------------------------------

    def ground_text(self, text: str) -> GroundingResult:
        """Ground a text string via exact-designation lookup."""
        if self._resolver is None:
            # No form pack: treat entire text as one surface.
            return self._ground_surface(text, (), ())
        lattice = self._resolver.resolve(text)
        # Collect non-whitespace units for designation lookup.
        word_units = [u for u in lattice.units if u.source_text.strip()]
        return self._ground_units(word_units, text)

    def ground(self, evidence: EvidenceItem) -> GroundingResult:
        """Ground a single typed evidence item."""
        if evidence.source == "text":
            return self.ground_text(evidence.content if isinstance(evidence.content, str) else "")
        if evidence.source == "sensor":
            return self._ground_sensor(evidence)
        if evidence.source == "operation":
            return self._ground_operation(evidence)
        # Unknown source kind: treat as unresolved.
        return GroundingResult(
            designations=(),
            unresolved=(ReferenceRequirement(
                unit_ref=evidence.source_ref,
                kind="unknown",
                required_kind=None,
                resolved_ref=None,
            ),),
            grounded_items=(),
            created_refs=(),
            provenance_refs=evidence.provenance_refs,
        )

    # -- internal: text grounding --------------------------------------------

    def _ground_units(
        self, units: list, source_text: str
    ) -> GroundingResult:
        designations: list[DesignationCandidate] = []
        unresolved: list[ReferenceRequirement] = []
        provenance: list[str] = []
        max_desig = getattr(self._config, "max_designations_per_span", 8)

        for unit in units:
            surface = self._lookup_surface(unit)
            targets = self._lookup_designation(surface)
            if targets:
                for target in targets[:max_desig]:
                    fact_ref = stable_ref("designation", {
                        "surface": surface,
                        "target": target,
                        "language": self._language,
                    })
                    designations.append(DesignationCandidate(
                        unit_refs=(unit.unit_ref,),
                        target_ref=target,
                        designation_fact_ref=fact_ref,
                        score=1.0,
                        provenance_refs=(),
                    ))
            else:
                unresolved.append(ReferenceRequirement(
                    unit_ref=unit.unit_ref,
                    kind="designation",
                    required_kind=None,
                    resolved_ref=None,
                ))

        return GroundingResult(
            designations=tuple(designations),
            unresolved=tuple(unresolved),
            grounded_items=(),
            created_refs=(),
            provenance_refs=tuple(provenance),
        )

    def _ground_surface(
        self, surface: str, unit_refs: tuple[str, ...], provenance: tuple[str, ...]
    ) -> GroundingResult:
        targets = self._lookup_designation(surface)
        if targets:
            max_desig = getattr(self._config, "max_designations_per_span", 8)
            designations = tuple(
                DesignationCandidate(
                    unit_refs=unit_refs,
                    target_ref=t,
                    designation_fact_ref=stable_ref("designation", {
                        "surface": surface,
                        "target": t,
                        "language": self._language,
                    }),
                    score=1.0,
                    provenance_refs=provenance,
                )
                for t in targets[:max_desig]
            )
            return GroundingResult(
                designations=designations,
                unresolved=(),
                grounded_items=(),
                created_refs=(),
                provenance_refs=provenance,
            )
        return GroundingResult(
            designations=(),
            unresolved=(ReferenceRequirement(
                unit_ref="unit:0" if not unit_refs else unit_refs[0],
                kind="designation",
                required_kind=None,
                resolved_ref=None,
            ),),
            grounded_items=(),
            created_refs=(),
            provenance_refs=provenance,
        )

    def _lookup_surface(self, unit: Any) -> str:
        """Return the normalised surface for a form unit."""
        if unit.normalized_forms:
            return unit.normalized_forms[0]
        return unit.source_text.strip().casefold()

    def _lookup_designation(self, surface: str) -> tuple[str, ...]:
        """Look up designation targets for a surface.

        Checks the mutable designation store first (for reviewed learning),
        then the authority's DesignationIndex.
        """
        # Check the mutable designation store (reviewed learning).
        if self._designation_store is not None:
            index = self._designation_store.build_index()
            targets = index.for_surface(surface, self._language)
            if targets:
                return targets
        # Check the authority's static designation index.
        if self._authority is not None:
            return self._authority.designations.for_surface(surface, self._language)
        return ()

    # -- internal: sensor grounding -------------------------------------------

    def _ground_sensor(self, evidence: EvidenceItem) -> GroundingResult:
        """Ground sensor evidence via adapter-schema-pinned target ref."""
        content = evidence.content
        if not isinstance(content, Mapping):
            return GroundingResult(
                designations=(),
                unresolved=(ReferenceRequirement(
                    unit_ref=evidence.source_ref,
                    kind="entity",
                    required_kind=None,
                    resolved_ref=None,
                ),),
                grounded_items=(),
                created_refs=(),
                provenance_refs=evidence.provenance_refs,
            )
        target_ref = content.get("target_ref")
        if not target_ref:
            return GroundingResult(
                designations=(),
                unresolved=(ReferenceRequirement(
                    unit_ref=evidence.source_ref,
                    kind="entity",
                    required_kind=None,
                    resolved_ref=None,
                ),),
                grounded_items=(),
                created_refs=(),
                provenance_refs=evidence.provenance_refs,
            )
        fact_ref = stable_ref("designation", {
            "source": "sensor",
            "target": target_ref,
            "adapter_receipt": evidence.adapter_receipt_ref,
        })
        designation = DesignationCandidate(
            unit_refs=(),
            target_ref=target_ref,
            designation_fact_ref=fact_ref,
            score=1.0,
            provenance_refs=evidence.provenance_refs,
        )
        grounded = GroundedItem(
            source_ref=evidence.source_ref,
            source_kind="sensor",
            target_ref=target_ref,
            unit_refs=(),
        )
        provenance = evidence.provenance_refs
        if evidence.adapter_receipt_ref and evidence.adapter_receipt_ref not in provenance:
            provenance = (*provenance, evidence.adapter_receipt_ref)
        return GroundingResult(
            designations=(designation,),
            unresolved=(),
            grounded_items=(grounded,),
            created_refs=(),
            provenance_refs=provenance,
        )

    # -- internal: operation grounding ----------------------------------------

    def _ground_operation(self, evidence: EvidenceItem) -> GroundingResult:
        """Ground prior operation observation evidence."""
        content = evidence.content
        if isinstance(content, Mapping):
            target_ref = content.get("target_ref", "")
        else:
            target_ref = ""
        if not target_ref:
            return GroundingResult(
                designations=(),
                unresolved=(ReferenceRequirement(
                    unit_ref=evidence.source_ref,
                    kind="entity",
                    required_kind=None,
                    resolved_ref=None,
                ),),
                grounded_items=(),
                created_refs=(),
                provenance_refs=evidence.provenance_refs,
            )
        fact_ref = stable_ref("designation", {
            "source": "operation",
            "target": target_ref,
        })
        designation = DesignationCandidate(
            unit_refs=(),
            target_ref=target_ref,
            designation_fact_ref=fact_ref,
            score=1.0,
            provenance_refs=evidence.provenance_refs,
        )
        grounded = GroundedItem(
            source_ref=evidence.source_ref,
            source_kind="operation",
            target_ref=target_ref,
            unit_refs=(),
        )
        return GroundingResult(
            designations=(designation,),
            unresolved=(),
            grounded_items=(grounded,),
            created_refs=(),
            provenance_refs=evidence.provenance_refs,
        )
