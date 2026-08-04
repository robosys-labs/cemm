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
from math import isfinite
from typing import Any, Mapping

from .canonical import stable_ref
from .forms import (
    EVIDENCE_MAX_PROVENANCE_REFS,
    EVIDENCE_MAX_REF_CHARS,
    EvidenceItem,
    FormLattice,
    FormResolver,
)
from .persistence import RevisionPin

__all__ = [
    "GROUNDING_RESULT_ABI_VERSION",
    "GROUNDING_MAX_DESIGNATIONS",
    "DesignationCandidate",
    "ReferenceRequirement",
    "GroundedItem",
    "GroundingResult",
    "Grounder",
]


# ---------------------------------------------------------------------------
# Data classes and strict codecs
# ---------------------------------------------------------------------------

GROUNDING_RESULT_ABI_VERSION = 1
GROUNDING_MAX_DESIGNATIONS = 512
GROUNDING_MAX_UNRESOLVED = 64
GROUNDING_MAX_GROUNDED_ITEMS = 64
GROUNDING_MAX_UNIT_REFS = 64
GROUNDING_MAX_PROVENANCE_REFS = EVIDENCE_MAX_PROVENANCE_REFS

_REFERENCE_KINDS = frozenset(
    {"designation", "participant", "deictic", "entity", "unknown"}
)
_SOURCE_KINDS = frozenset({"text", "sensor", "operation"})


def _require_exact_fields(
    data: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} payload must be a mapping")
    actual = frozenset(data)
    if actual != expected:
        raise ValueError(
            f"{label} fields mismatch: "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _bounded_string(
    value: object,
    name: str,
    *,
    maximum: int = EVIDENCE_MAX_REF_CHARS,
) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return value


def _optional_bounded_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, name)


def _prebound_tuple(
    value: object,
    name: str,
    *,
    maximum: int,
    item_type: type[Any] | None = None,
) -> tuple[Any, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} items")
    if item_type is not None and any(not isinstance(item, item_type) for item in value):
        raise TypeError(f"{name} must contain only {item_type.__name__}")
    return value


def _bounded_strings(
    value: object,
    name: str,
    *,
    maximum: int,
    unique: bool = True,
) -> tuple[str, ...]:
    rows = _prebound_tuple(value, name, maximum=maximum)
    if any(not isinstance(item, str) or not item for item in rows):
        raise TypeError(f"{name} must contain non-empty strings")
    if any(len(item) > EVIDENCE_MAX_REF_CHARS for item in rows):
        raise ValueError(f"{name} contains an overlong ref")
    if unique and len(rows) != len(set(rows)):
        raise ValueError(f"{name} must not contain duplicates")
    return rows


def _wire_strings(value: object, name: str, *, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} items")
    return _bounded_strings(tuple(value), name, maximum=maximum)


def _require_score(value: object) -> float:
    if type(value) is not float:
        raise TypeError("score must be a float")
    if not isfinite(value):
        raise ValueError("score must be finite")
    if value < 0.0 or value > 1.0:
        raise ValueError("score must be within [0, 1]")
    if value == 0.0 and value.hex().startswith("-"):
        raise ValueError("score must use canonical positive zero")
    return value


def _validate_revision_pin(value: object) -> RevisionPin:
    if not isinstance(value, RevisionPin):
        raise TypeError("revision_pin must be RevisionPin")
    rebuilt = RevisionPin.from_dict(value.as_dict())
    if rebuilt != value:
        raise ValueError("revision_pin is non-canonical")
    _bounded_string(value.authority_generation, "authority_generation")
    if value.model_identity is not None:
        _bounded_string(value.model_identity, "model_identity")
    return value


@dataclass(frozen=True)
class DesignationCandidate:
    """One immutable bounded designation alternative."""

    unit_refs: tuple[str, ...]
    target_ref: str
    designation_fact_ref: str
    score: float
    provenance_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "unit_refs",
            "target_ref",
            "designation_fact_ref",
            "score",
            "provenance_refs",
        }
    )

    def __post_init__(self) -> None:
        _bounded_strings(
            self.unit_refs,
            "unit_refs",
            maximum=GROUNDING_MAX_UNIT_REFS,
        )
        _bounded_string(self.target_ref, "target_ref")
        _bounded_string(self.designation_fact_ref, "designation_fact_ref")
        _require_score(self.score)
        _bounded_strings(
            self.provenance_refs,
            "provenance_refs",
            maximum=GROUNDING_MAX_PROVENANCE_REFS,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_refs": list(self.unit_refs),
            "target_ref": self.target_ref,
            "designation_fact_ref": self.designation_fact_ref,
            "score": self.score,
            "provenance_refs": list(self.provenance_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DesignationCandidate":
        _require_exact_fields(data, cls._FIELDS, "DesignationCandidate")
        target_ref = _bounded_string(data["target_ref"], "target_ref")
        fact_ref = _bounded_string(data["designation_fact_ref"], "designation_fact_ref")
        score = _require_score(data["score"])
        unit_refs = _wire_strings(
            data["unit_refs"], "unit_refs", maximum=GROUNDING_MAX_UNIT_REFS
        )
        provenance_refs = _wire_strings(
            data["provenance_refs"],
            "provenance_refs",
            maximum=GROUNDING_MAX_PROVENANCE_REFS,
        )
        rebuilt = cls(unit_refs, target_ref, fact_ref, score, provenance_refs)
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical DesignationCandidate encoding")
        return rebuilt


@dataclass(frozen=True)
class ReferenceRequirement:
    """One immutable unresolved reference requirement."""

    unit_ref: str
    kind: str
    required_kind: str | None
    resolved_ref: str | None = None

    _FIELDS = frozenset({"unit_ref", "kind", "required_kind", "resolved_ref"})

    def __post_init__(self) -> None:
        _bounded_string(self.unit_ref, "unit_ref")
        _bounded_string(self.kind, "kind")
        if self.kind not in _REFERENCE_KINDS:
            raise ValueError(f"unsupported reference requirement kind: {self.kind}")
        _optional_bounded_string(self.required_kind, "required_kind")
        _optional_bounded_string(self.resolved_ref, "resolved_ref")

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_ref": self.unit_ref,
            "kind": self.kind,
            "required_kind": self.required_kind,
            "resolved_ref": self.resolved_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReferenceRequirement":
        _require_exact_fields(data, cls._FIELDS, "ReferenceRequirement")
        rebuilt = cls(
            unit_ref=_bounded_string(data["unit_ref"], "unit_ref"),
            kind=_bounded_string(data["kind"], "kind"),
            required_kind=_optional_bounded_string(
                data["required_kind"], "required_kind"
            ),
            resolved_ref=_optional_bounded_string(data["resolved_ref"], "resolved_ref"),
        )
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical ReferenceRequirement encoding")
        return rebuilt


@dataclass(frozen=True)
class GroundedItem:
    """One immutable evidence item linked to an existing semantic target."""

    source_ref: str
    source_kind: str
    target_ref: str
    unit_refs: tuple[str, ...]

    _FIELDS = frozenset({"source_ref", "source_kind", "target_ref", "unit_refs"})

    def __post_init__(self) -> None:
        _bounded_string(self.source_ref, "source_ref")
        _bounded_string(self.source_kind, "source_kind")
        if self.source_kind not in _SOURCE_KINDS:
            raise ValueError(f"unsupported grounded source kind: {self.source_kind}")
        _bounded_string(self.target_ref, "target_ref")
        _bounded_strings(
            self.unit_refs,
            "unit_refs",
            maximum=GROUNDING_MAX_UNIT_REFS,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "source_kind": self.source_kind,
            "target_ref": self.target_ref,
            "unit_refs": list(self.unit_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GroundedItem":
        _require_exact_fields(data, cls._FIELDS, "GroundedItem")
        rebuilt = cls(
            source_ref=_bounded_string(data["source_ref"], "source_ref"),
            source_kind=_bounded_string(data["source_kind"], "source_kind"),
            target_ref=_bounded_string(data["target_ref"], "target_ref"),
            unit_refs=_wire_strings(
                data["unit_refs"], "unit_refs", maximum=GROUNDING_MAX_UNIT_REFS
            ),
        )
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical GroundedItem encoding")
        return rebuilt


@dataclass(frozen=True)
class GroundingResult:
    """Strict content-addressed Grounding Result ABI 1."""

    abi_version: int
    grounding_ref: str
    evidence_packet_ref: str
    form_lattice_ref: str
    revision_pin: RevisionPin
    designations: tuple[DesignationCandidate, ...]
    unresolved: tuple[ReferenceRequirement, ...]
    grounded_items: tuple[GroundedItem, ...]
    created_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "grounding_ref",
            "evidence_packet_ref",
            "form_lattice_ref",
            "revision_pin",
            "designations",
            "unresolved",
            "grounded_items",
            "created_refs",
            "provenance_refs",
        }
    )

    def __post_init__(self) -> None:
        if isinstance(self.abi_version, bool) or not isinstance(self.abi_version, int):
            raise TypeError("abi_version must be an integer")
        if self.abi_version != GROUNDING_RESULT_ABI_VERSION:
            raise ValueError(
                f"unsupported GroundingResult ABI version: {self.abi_version!r}"
            )
        _bounded_string(self.grounding_ref, "grounding_ref")
        _bounded_string(self.evidence_packet_ref, "evidence_packet_ref")
        _bounded_string(self.form_lattice_ref, "form_lattice_ref")
        _validate_revision_pin(self.revision_pin)
        _prebound_tuple(
            self.designations,
            "designations",
            maximum=GROUNDING_MAX_DESIGNATIONS,
            item_type=DesignationCandidate,
        )
        _prebound_tuple(
            self.unresolved,
            "unresolved",
            maximum=GROUNDING_MAX_UNRESOLVED,
            item_type=ReferenceRequirement,
        )
        _prebound_tuple(
            self.grounded_items,
            "grounded_items",
            maximum=GROUNDING_MAX_GROUNDED_ITEMS,
            item_type=GroundedItem,
        )
        if not isinstance(self.created_refs, tuple):
            raise TypeError("created_refs must be a tuple")
        if self.created_refs != ():
            raise ValueError("created_refs must be exactly empty")
        _bounded_strings(
            self.provenance_refs,
            "provenance_refs",
            maximum=GROUNDING_MAX_PROVENANCE_REFS,
        )
        if self.grounding_ref != stable_ref(
            "grounding_result", self._identity_material()
        ):
            raise ValueError("GroundingResult ref mismatch")

    @classmethod
    def create(
        cls,
        *,
        evidence_packet_ref: str,
        form_lattice_ref: str,
        revision_pin: RevisionPin,
        designations: tuple[DesignationCandidate, ...],
        unresolved: tuple[ReferenceRequirement, ...],
        grounded_items: tuple[GroundedItem, ...],
        provenance_refs: tuple[str, ...],
    ) -> "GroundingResult":
        _bounded_string(evidence_packet_ref, "evidence_packet_ref")
        _bounded_string(form_lattice_ref, "form_lattice_ref")
        _validate_revision_pin(revision_pin)
        _prebound_tuple(
            designations,
            "designations",
            maximum=GROUNDING_MAX_DESIGNATIONS,
            item_type=DesignationCandidate,
        )
        _prebound_tuple(
            unresolved,
            "unresolved",
            maximum=GROUNDING_MAX_UNRESOLVED,
            item_type=ReferenceRequirement,
        )
        _prebound_tuple(
            grounded_items,
            "grounded_items",
            maximum=GROUNDING_MAX_GROUNDED_ITEMS,
            item_type=GroundedItem,
        )
        _bounded_strings(
            provenance_refs,
            "provenance_refs",
            maximum=GROUNDING_MAX_PROVENANCE_REFS,
        )
        material = {
            "abi_version": GROUNDING_RESULT_ABI_VERSION,
            "evidence_packet_ref": evidence_packet_ref,
            "form_lattice_ref": form_lattice_ref,
            "revision_pin": revision_pin.as_dict(),
            "designations": [row.as_dict() for row in designations],
            "unresolved": [row.as_dict() for row in unresolved],
            "grounded_items": [row.as_dict() for row in grounded_items],
            "created_refs": [],
            "provenance_refs": list(provenance_refs),
        }
        return cls(
            abi_version=GROUNDING_RESULT_ABI_VERSION,
            grounding_ref=stable_ref("grounding_result", material),
            evidence_packet_ref=evidence_packet_ref,
            form_lattice_ref=form_lattice_ref,
            revision_pin=revision_pin,
            designations=designations,
            unresolved=unresolved,
            grounded_items=grounded_items,
            created_refs=(),
            provenance_refs=provenance_refs,
        )

    def _identity_material(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "evidence_packet_ref": self.evidence_packet_ref,
            "form_lattice_ref": self.form_lattice_ref,
            "revision_pin": self.revision_pin.as_dict(),
            "designations": [row.as_dict() for row in self.designations],
            "unresolved": [row.as_dict() for row in self.unresolved],
            "grounded_items": [row.as_dict() for row in self.grounded_items],
            "created_refs": list(self.created_refs),
            "provenance_refs": list(self.provenance_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {"grounding_ref": self.grounding_ref, **self._identity_material()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GroundingResult":
        _require_exact_fields(data, cls._FIELDS, "GroundingResult")
        abi_version = data["abi_version"]
        if isinstance(abi_version, bool) or not isinstance(abi_version, int):
            raise TypeError("abi_version must be an integer")
        if abi_version != GROUNDING_RESULT_ABI_VERSION:
            raise ValueError(
                f"unsupported GroundingResult ABI version: {abi_version!r}"
            )
        grounding_ref = _bounded_string(data["grounding_ref"], "grounding_ref")
        evidence_packet_ref = _bounded_string(
            data["evidence_packet_ref"], "evidence_packet_ref"
        )
        form_lattice_ref = _bounded_string(data["form_lattice_ref"], "form_lattice_ref")
        revision_pin = RevisionPin.from_dict(data["revision_pin"])
        _validate_revision_pin(revision_pin)

        collections = (
            ("designations", GROUNDING_MAX_DESIGNATIONS),
            ("unresolved", GROUNDING_MAX_UNRESOLVED),
            ("grounded_items", GROUNDING_MAX_GROUNDED_ITEMS),
            ("provenance_refs", GROUNDING_MAX_PROVENANCE_REFS),
        )
        for name, maximum in collections:
            value = data[name]
            if not isinstance(value, list):
                raise TypeError(f"{name} must be a list")
            if len(value) > maximum:
                raise ValueError(f"{name} exceeds {maximum} items")
        if not isinstance(data["created_refs"], list):
            raise TypeError("created_refs must be a list")
        if data["created_refs"] != []:
            raise ValueError("created_refs must be exactly empty")

        rebuilt = cls.create(
            evidence_packet_ref=evidence_packet_ref,
            form_lattice_ref=form_lattice_ref,
            revision_pin=revision_pin,
            designations=tuple(
                DesignationCandidate.from_dict(row) for row in data["designations"]
            ),
            unresolved=tuple(
                ReferenceRequirement.from_dict(row) for row in data["unresolved"]
            ),
            grounded_items=tuple(
                GroundedItem.from_dict(row) for row in data["grounded_items"]
            ),
            provenance_refs=_wire_strings(
                data["provenance_refs"],
                "provenance_refs",
                maximum=GROUNDING_MAX_PROVENANCE_REFS,
            ),
        )
        if grounding_ref != rebuilt.grounding_ref:
            raise ValueError("GroundingResult ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical GroundingResult encoding")
        return rebuilt


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

    def ground_lattice(
        self,
        lattice: FormLattice,
        revision_pin: RevisionPin,
    ) -> GroundingResult:
        """Ground one exact existing lattice without resolver re-entry."""
        if not isinstance(lattice, FormLattice):
            raise TypeError("lattice must be FormLattice")
        _validate_revision_pin(revision_pin)
        if len(lattice.units) > self._config.max_input_tokens:
            raise ValueError("form lattice source unit bound violated")
        word_units = tuple(unit for unit in lattice.units if unit.source_text.strip())
        return self._ground_units(word_units, lattice, revision_pin)

    def ground_text(self, text: str) -> GroundingResult:
        """Unadmitted transition point pending exact runtime lineage migration."""
        raise NotImplementedError(
            "ground_text is unadmitted: build one exact EvidencePacket/FormLattice "
            "and call ground_lattice(lattice, revision_pin)"
        )

    def ground(self, evidence: EvidenceItem) -> GroundingResult:
        """Unadmitted transition point pending modality-lattice lineage."""
        raise NotImplementedError(
            "ground(evidence) is unadmitted: grounding requires exact packet, "
            "lattice, and RevisionPin lineage through ground_lattice"
        )

    # -- internal: text grounding --------------------------------------------

    def _ground_units(
        self,
        units: tuple[Any, ...],
        lattice: FormLattice,
        revision_pin: RevisionPin,
    ) -> GroundingResult:
        designations: list[DesignationCandidate] = []
        unresolved: list[ReferenceRequirement] = []
        max_designations = self._config.max_designations_per_span

        for unit in units:
            surface = self._lookup_surface(unit)
            targets = self._lookup_designation(surface)
            if targets:
                for target in targets[:max_designations]:
                    fact_ref = stable_ref(
                        "designation",
                        {
                            "surface": surface,
                            "target": target,
                            "language": self._language,
                        },
                    )
                    designations.append(
                        DesignationCandidate(
                            unit_refs=(unit.unit_ref,),
                            target_ref=target,
                            designation_fact_ref=fact_ref,
                            score=1.0,
                            provenance_refs=(),
                        )
                    )
            else:
                unresolved.append(
                    ReferenceRequirement(
                        unit_ref=unit.unit_ref,
                        kind="designation",
                        required_kind=None,
                        resolved_ref=None,
                    )
                )

        return GroundingResult.create(
            evidence_packet_ref=lattice.evidence_packet_ref,
            form_lattice_ref=lattice.lattice_ref,
            revision_pin=revision_pin,
            designations=tuple(designations),
            unresolved=tuple(unresolved),
            grounded_items=(),
            provenance_refs=(),
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
