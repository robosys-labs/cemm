"""Reversible form evidence: source-preserving tokenisation and closed-class features.

This module owns :class:`EvidenceItem`, :class:`EvidencePacket`,
:class:`FormUnit`, :class:`FormHypothesis`, :class:`FormLattice`, and
:class:`FormResolver`.

The :class:`FormResolver` owns *only* text tokenisation, morphology,
punctuation, closed-class evidence, and bounded construction annotations.
It preserves the exact source text so that joining every unit's
``source_text`` reproduces the input.  It does **not** choose operators and
does **not** inspect internal ref spelling.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .canonical import canonical_bytes, stable_ref

__all__ = [
    "EvidenceItem",
    "EvidencePacket",
    "FormUnit",
    "FormHypothesis",
    "FormLattice",
    "FormResolver",
]

# ABI-level bounds are language-agnostic Unicode-code-point and item counts.
# They cap all work before canonical hashing or tokenization in a normal cycle.
EVIDENCE_MAX_SOURCE_CHARS = 16_384
EVIDENCE_MAX_SCALAR_CHARS = 16_384
EVIDENCE_MAX_REF_CHARS = 512
EVIDENCE_MAX_KEY_CHARS = 256
EVIDENCE_MAX_INTEGER = (1 << 63) - 1
EVIDENCE_MAX_ITEMS = 64
EVIDENCE_MAX_PROVENANCE_REFS = 64
EVIDENCE_MAX_CONTAINER_ITEMS = 64
EVIDENCE_MAX_CONTENT_DEPTH = 6
EVIDENCE_MAX_AGGREGATE_NODES = 1_024
EVIDENCE_MAX_AGGREGATE_CHARS = 65_536

_MAX_HYPOTHESES = 16
_MAX_FORM_UNITS = 64
_MAX_NORMALIZED_FORMS = 8
_MAX_FEATURES_PER_UNIT = 16
_MAX_UNIT_REFS_PER_HYPOTHESIS = 64
_MAX_FEATURES_PER_HYPOTHESIS = 64
EVIDENCE_ABI_VERSION = 1
FORM_LATTICE_ABI_VERSION = 1


# ---------------------------------------------------------------------------
# Evidence items and packets
# ---------------------------------------------------------------------------


@dataclass
class _EvidenceBudget:
    nodes: int = 0
    chars: int = 0

    def add_node(self) -> None:
        self.nodes += 1
        if self.nodes > EVIDENCE_MAX_AGGREGATE_NODES:
            raise ValueError("evidence content aggregate nodes exceed bound")

    def add_chars(self, count: int) -> None:
        self.chars += count
        if self.chars > EVIDENCE_MAX_AGGREGATE_CHARS:
            raise ValueError("evidence content aggregate chars exceed bound")


def _bounded_evidence_string(value: object, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return value


def _bounded_evidence_ref(value: object, name: str) -> str:
    return _bounded_evidence_string(value, name, maximum=EVIDENCE_MAX_REF_CHARS)


def _freeze_evidence_content(
    value: object,
    *,
    depth: int = 0,
    budget: _EvidenceBudget | None = None,
) -> object:
    if budget is None:
        budget = _EvidenceBudget()
    if depth > EVIDENCE_MAX_CONTENT_DEPTH:
        raise ValueError("evidence content exceeds maximum depth")
    budget.add_node()
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) > EVIDENCE_MAX_SCALAR_CHARS:
            raise ValueError(
                f"evidence content string exceeds {EVIDENCE_MAX_SCALAR_CHARS} characters"
            )
        budget.add_chars(len(value))
        return value
    if isinstance(value, int):
        if abs(value) > EVIDENCE_MAX_INTEGER:
            raise ValueError("evidence content integer exceeds signed 64-bit bound")
        return value
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("evidence content floats must be finite")
        return value
    if isinstance(value, Mapping):
        if len(value) > EVIDENCE_MAX_CONTAINER_ITEMS:
            raise ValueError("evidence content mapping exceeds bound")
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeError(
                    "evidence content mapping keys must be non-empty strings"
                )
            if len(key) > EVIDENCE_MAX_KEY_CHARS:
                raise ValueError(
                    f"evidence content mapping key exceeds {EVIDENCE_MAX_KEY_CHARS} characters"
                )
            budget.add_chars(len(key))
            frozen[key] = _freeze_evidence_content(
                item,
                depth=depth + 1,
                budget=budget,
            )
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        if len(value) > EVIDENCE_MAX_CONTAINER_ITEMS:
            raise ValueError("evidence content sequence exceeds bound")
        return tuple(
            _freeze_evidence_content(item, depth=depth + 1, budget=budget)
            for item in value
        )
    raise TypeError("evidence content must contain only bounded JSON values")


def _wire_evidence_content(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _wire_evidence_content(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_wire_evidence_content(item) for item in value]
    return value


@dataclass(frozen=True)
class EvidenceItem:
    """One content-addressed item in Evidence ABI 1."""

    abi_version: int
    item_ref: str
    source: str
    content: str | Mapping[str, Any]
    source_ref: str
    provenance_refs: tuple[str, ...]
    adapter_receipt_ref: str | None

    _FIELDS = frozenset(
        {
            "abi_version",
            "item_ref",
            "source",
            "content",
            "source_ref",
            "provenance_refs",
            "adapter_receipt_ref",
        }
    )

    def __post_init__(self) -> None:
        _require_abi_version(self.abi_version, EVIDENCE_ABI_VERSION, "EvidenceItem")
        _bounded_evidence_ref(self.item_ref, "item_ref")
        if self.source not in {"text", "sensor", "operation"}:
            raise ValueError(f"unsupported evidence source: {self.source!r}")
        if self.source == "text":
            if not isinstance(self.content, str):
                raise TypeError("text evidence content must be a string")
            if self.adapter_receipt_ref is not None:
                raise ValueError("text evidence cannot carry an adapter receipt")
        elif not isinstance(self.content, Mapping):
            raise TypeError("sensor and operation evidence content must be a mapping")
        _bounded_evidence_ref(self.source_ref, "source_ref")
        _require_string_tuple(
            self.provenance_refs,
            "provenance_refs",
            max_items=EVIDENCE_MAX_PROVENANCE_REFS,
        )
        for provenance_ref in self.provenance_refs:
            _bounded_evidence_ref(provenance_ref, "provenance_ref")
        if self.adapter_receipt_ref is not None:
            _bounded_evidence_ref(self.adapter_receipt_ref, "adapter_receipt_ref")
        frozen_content = _freeze_evidence_content(self.content)
        object.__setattr__(self, "content", frozen_content)
        if self.item_ref != stable_ref("evidence_item", self._identity_material()):
            raise ValueError("EvidenceItem ref mismatch")

    @classmethod
    def create(
        cls,
        *,
        source: str,
        content: str | Mapping[str, Any],
        source_ref: str,
        provenance_refs: tuple[str, ...],
        adapter_receipt_ref: str | None,
    ) -> "EvidenceItem":
        if source not in {"text", "sensor", "operation"}:
            raise ValueError(f"unsupported evidence source: {source!r}")
        _bounded_evidence_ref(source_ref, "source_ref")
        _require_string_tuple(
            provenance_refs,
            "provenance_refs",
            max_items=EVIDENCE_MAX_PROVENANCE_REFS,
        )
        for provenance_ref in provenance_refs:
            _bounded_evidence_ref(provenance_ref, "provenance_ref")
        if adapter_receipt_ref is not None:
            _bounded_evidence_ref(adapter_receipt_ref, "adapter_receipt_ref")
        frozen_content = _freeze_evidence_content(content)
        if source == "text":
            if not isinstance(frozen_content, str):
                raise TypeError("text evidence content must be a string")
            if len(frozen_content) > EVIDENCE_MAX_SOURCE_CHARS:
                raise ValueError(
                    f"text evidence content exceeds {EVIDENCE_MAX_SOURCE_CHARS} characters"
                )
            if adapter_receipt_ref is not None:
                raise ValueError("text evidence cannot carry an adapter receipt")
        elif not isinstance(frozen_content, Mapping):
            raise TypeError("sensor and operation evidence content must be a mapping")
        material = {
            "abi_version": EVIDENCE_ABI_VERSION,
            "source": source,
            "content": _wire_evidence_content(frozen_content),
            "source_ref": source_ref,
            "provenance_refs": list(provenance_refs),
            "adapter_receipt_ref": adapter_receipt_ref,
        }
        return cls(
            abi_version=EVIDENCE_ABI_VERSION,
            item_ref=stable_ref("evidence_item", material),
            source=source,
            content=frozen_content,
            source_ref=source_ref,
            provenance_refs=provenance_refs,
            adapter_receipt_ref=adapter_receipt_ref,
        )

    def _identity_material(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "source": self.source,
            "content": _wire_evidence_content(self.content),
            "source_ref": self.source_ref,
            "provenance_refs": list(self.provenance_refs),
            "adapter_receipt_ref": self.adapter_receipt_ref,
        }

    def as_dict(self) -> dict[str, Any]:
        return {"item_ref": self.item_ref, **self._identity_material()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceItem":
        _require_exact_fields(data, cls._FIELDS, "EvidenceItem")
        _require_abi_version(data["abi_version"], EVIDENCE_ABI_VERSION, "EvidenceItem")
        provenance_refs = _wire_string_tuple(
            data["provenance_refs"],
            "provenance_refs",
            max_items=EVIDENCE_MAX_PROVENANCE_REFS,
        )
        if not isinstance(data["content"], (str, Mapping)):
            raise TypeError("evidence content wire value must be a string or mapping")
        rebuilt = cls.create(
            source=data["source"],
            content=data["content"],
            source_ref=data["source_ref"],
            provenance_refs=provenance_refs,
            adapter_receipt_ref=data["adapter_receipt_ref"],
        )
        if data["item_ref"] != rebuilt.item_ref:
            raise ValueError("EvidenceItem ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical EvidenceItem encoding")
        return rebuilt


@dataclass(frozen=True)
class EvidencePacket:
    """One immutable content-addressed Evidence ABI 1 packet."""

    abi_version: int
    packet_ref: str
    items: tuple[EvidenceItem, ...]
    source_text: str
    form_pack_hash: str

    _FIELDS = frozenset(
        {"abi_version", "packet_ref", "items", "source_text", "form_pack_hash"}
    )

    def __post_init__(self) -> None:
        _require_abi_version(self.abi_version, EVIDENCE_ABI_VERSION, "EvidencePacket")
        _bounded_evidence_ref(self.packet_ref, "packet_ref")
        if not isinstance(self.items, tuple):
            raise TypeError("items must be a tuple")
        if not self.items:
            raise ValueError("evidence packet items must be non-empty")
        if len(self.items) > EVIDENCE_MAX_ITEMS:
            raise ValueError(f"evidence packet exceeds {EVIDENCE_MAX_ITEMS} items")
        if any(not isinstance(item, EvidenceItem) for item in self.items):
            raise TypeError("items must contain EvidenceItem values")
        item_refs = tuple(item.item_ref for item in self.items)
        if len(item_refs) != len(set(item_refs)):
            raise ValueError("evidence packet item refs must be unique")
        source_refs = tuple(item.source_ref for item in self.items)
        if len(source_refs) != len(set(source_refs)):
            raise ValueError("evidence packet source refs must be unique")
        _bounded_source_text(self.source_text)
        _bounded_evidence_ref(self.form_pack_hash, "form_pack_hash")
        text_items = tuple(item for item in self.items if item.source == "text")
        if text_items:
            if len(text_items) != 1:
                raise ValueError("R1 evidence packet supports exactly one text item")
            if text_items[0].content != self.source_text:
                raise ValueError("text evidence content must equal packet source_text")
        elif self.source_text:
            raise ValueError("source_text requires one matching text evidence item")
        if self.packet_ref != stable_ref("evidence_packet", self._identity_material()):
            raise ValueError("EvidencePacket ref mismatch")

    @classmethod
    def create(
        cls,
        *,
        items: tuple[EvidenceItem, ...],
        source_text: str,
        form_pack_hash: str,
    ) -> "EvidencePacket":
        _prebound_tuple(
            items,
            "items",
            max_items=EVIDENCE_MAX_ITEMS,
            item_type=EvidenceItem,
            nonempty=True,
        )
        _bounded_source_text(source_text)
        _bounded_evidence_ref(form_pack_hash, "form_pack_hash")
        item_refs = tuple(item.item_ref for item in items)
        if len(item_refs) != len(set(item_refs)):
            raise ValueError("evidence packet item refs must be unique")
        source_refs = tuple(item.source_ref for item in items)
        if len(source_refs) != len(set(source_refs)):
            raise ValueError("evidence packet source refs must be unique")
        text_items = tuple(item for item in items if item.source == "text")
        if text_items:
            if len(text_items) != 1:
                raise ValueError("R1 evidence packet supports exactly one text item")
            if text_items[0].content != source_text:
                raise ValueError("text evidence content must equal packet source_text")
        elif source_text:
            raise ValueError("source_text requires one matching text evidence item")
        material = {
            "abi_version": EVIDENCE_ABI_VERSION,
            "items": [item.as_dict() for item in items],
            "source_text": source_text,
            "form_pack_hash": form_pack_hash,
        }
        return cls(
            abi_version=EVIDENCE_ABI_VERSION,
            packet_ref=stable_ref("evidence_packet", material),
            items=items,
            source_text=source_text,
            form_pack_hash=form_pack_hash,
        )

    def _identity_material(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "items": [item.as_dict() for item in self.items],
            "source_text": self.source_text,
            "form_pack_hash": self.form_pack_hash,
        }

    def as_dict(self) -> dict[str, Any]:
        return {"packet_ref": self.packet_ref, **self._identity_material()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidencePacket":
        _require_exact_fields(data, cls._FIELDS, "EvidencePacket")
        _require_abi_version(
            data["abi_version"], EVIDENCE_ABI_VERSION, "EvidencePacket"
        )
        if not isinstance(data["items"], list):
            raise TypeError("items must be a list")
        if not data["items"]:
            raise ValueError("evidence packet items must be non-empty")
        if len(data["items"]) > EVIDENCE_MAX_ITEMS:
            raise ValueError(f"items exceeds {EVIDENCE_MAX_ITEMS} items")
        rebuilt = cls.create(
            items=tuple(EvidenceItem.from_dict(item) for item in data["items"]),
            source_text=data["source_text"],
            form_pack_hash=data["form_pack_hash"],
        )
        if data["packet_ref"] != rebuilt.packet_ref:
            raise ValueError("EvidencePacket ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical EvidencePacket encoding")
        return rebuilt


# ---------------------------------------------------------------------------
# Form units, hypotheses, and lattice
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormUnit:
    """One exact, source-preserving form unit."""

    unit_ref: str
    source_text: str
    normalized_forms: tuple[str, ...]
    source_start: int
    source_end: int
    features: tuple[tuple[str, str], ...]

    _FIELDS = frozenset(
        {
            "unit_ref",
            "source_text",
            "normalized_forms",
            "source_start",
            "source_end",
            "features",
        }
    )

    def __post_init__(self) -> None:
        _bounded_evidence_ref(self.unit_ref, "unit_ref")
        _bounded_source_text(self.source_text)
        _require_string_tuple(
            self.normalized_forms,
            "normalized_forms",
            max_items=_MAX_NORMALIZED_FORMS,
            item_maximum=EVIDENCE_MAX_SCALAR_CHARS,
            item_name="normalized_forms value",
        )
        _require_offset(self.source_start, "source_start")
        _require_offset(self.source_end, "source_end")
        if self.source_end <= self.source_start:
            raise ValueError("form unit geometry must have positive width")
        _require_feature_pairs(
            self.features, "features", max_items=_MAX_FEATURES_PER_UNIT
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_ref": self.unit_ref,
            "source_text": self.source_text,
            "normalized_forms": list(self.normalized_forms),
            "source_start": self.source_start,
            "source_end": self.source_end,
            "features": [list(row) for row in self.features],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FormUnit":
        _require_exact_fields(data, cls._FIELDS, "FormUnit")
        unit_ref = _bounded_evidence_ref(data["unit_ref"], "unit_ref")
        source_text = _bounded_source_text(data["source_text"])
        source_start = _require_offset(data["source_start"], "source_start")
        source_end = _require_offset(data["source_end"], "source_end")
        normalized_forms = _wire_string_tuple(
            data["normalized_forms"],
            "normalized_forms",
            max_items=_MAX_NORMALIZED_FORMS,
            item_maximum=EVIDENCE_MAX_SCALAR_CHARS,
            item_name="normalized_forms value",
        )
        features = _wire_feature_pairs(
            data["features"], "features", max_items=_MAX_FEATURES_PER_UNIT
        )
        unit = cls(
            unit_ref=unit_ref,
            source_text=source_text,
            normalized_forms=normalized_forms,
            source_start=source_start,
            source_end=source_end,
            features=features,
        )
        if unit.as_dict() != dict(data):
            raise ValueError("non-canonical FormUnit encoding")
        return unit


@dataclass(frozen=True)
class FormHypothesis:
    """One bounded construction hypothesis over existing form units."""

    hypothesis_ref: str
    unit_refs: tuple[str, ...]
    construction: str | None
    features: tuple[tuple[str, str], ...]

    _FIELDS = frozenset({"hypothesis_ref", "unit_refs", "construction", "features"})

    def __post_init__(self) -> None:
        _bounded_evidence_ref(self.hypothesis_ref, "hypothesis_ref")
        _require_string_tuple(
            self.unit_refs,
            "unit_refs",
            nonempty=True,
            max_items=_MAX_UNIT_REFS_PER_HYPOTHESIS,
            item_maximum=EVIDENCE_MAX_REF_CHARS,
            item_name="unit_ref",
        )
        if self.construction is not None:
            _bounded_evidence_string(
                self.construction,
                "construction",
                maximum=EVIDENCE_MAX_SCALAR_CHARS,
            )
        _require_feature_pairs(
            self.features, "features", max_items=_MAX_FEATURES_PER_HYPOTHESIS
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_ref": self.hypothesis_ref,
            "unit_refs": list(self.unit_refs),
            "construction": self.construction,
            "features": [list(row) for row in self.features],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FormHypothesis":
        _require_exact_fields(data, cls._FIELDS, "FormHypothesis")
        hypothesis_ref = _bounded_evidence_ref(data["hypothesis_ref"], "hypothesis_ref")
        construction = data["construction"]
        if construction is not None:
            construction = _bounded_evidence_string(
                construction,
                "construction",
                maximum=EVIDENCE_MAX_SCALAR_CHARS,
            )
        unit_refs = _wire_string_tuple(
            data["unit_refs"],
            "unit_refs",
            max_items=_MAX_UNIT_REFS_PER_HYPOTHESIS,
            item_maximum=EVIDENCE_MAX_REF_CHARS,
            item_name="unit_ref",
        )
        features = _wire_feature_pairs(
            data["features"], "features", max_items=_MAX_FEATURES_PER_HYPOTHESIS
        )
        hypothesis = cls(
            hypothesis_ref=hypothesis_ref,
            unit_refs=unit_refs,
            construction=construction,
            features=features,
        )
        if hypothesis.as_dict() != dict(data):
            raise ValueError("non-canonical FormHypothesis encoding")
        return hypothesis


@dataclass(frozen=True)
class FormLattice:
    """Content-addressed Form Lattice ABI 1 with exact source geometry."""

    abi_version: int
    lattice_ref: str
    evidence_packet_ref: str
    form_pack_hash: str
    source_text: str
    source_length: int
    units: tuple[FormUnit, ...]
    hypotheses: tuple[FormHypothesis, ...]
    _unit_index: Mapping[str, FormUnit] = field(
        init=False, repr=False, compare=False, hash=False
    )

    _FIELDS = frozenset(
        {
            "abi_version",
            "lattice_ref",
            "evidence_packet_ref",
            "form_pack_hash",
            "source_text",
            "source_length",
            "units",
            "hypotheses",
        }
    )

    def __post_init__(self) -> None:
        if isinstance(self.abi_version, bool) or not isinstance(self.abi_version, int):
            raise TypeError("abi_version must be an integer")
        if self.abi_version != FORM_LATTICE_ABI_VERSION:
            raise ValueError(
                f"unsupported FormLattice ABI version: {self.abi_version!r}"
            )
        _bounded_evidence_ref(self.lattice_ref, "lattice_ref")
        _bounded_evidence_ref(self.evidence_packet_ref, "evidence_packet_ref")
        _bounded_evidence_ref(self.form_pack_hash, "form_pack_hash")
        _bounded_source_text(self.source_text)
        _require_offset(self.source_length, "source_length")
        if self.source_length != len(self.source_text):
            raise ValueError(
                "form lattice source_length does not match source geometry"
            )
        _prebound_tuple(
            self.units,
            "units",
            max_items=_MAX_FORM_UNITS,
            item_type=FormUnit,
        )
        _prebound_tuple(
            self.hypotheses,
            "hypotheses",
            max_items=_MAX_HYPOTHESES,
            item_type=FormHypothesis,
        )
        unit_index: dict[str, FormUnit] = {}
        cursor = 0
        for unit in self.units:
            if unit.unit_ref in unit_index:
                raise ValueError("form lattice unit refs must be unique")
            if unit.source_start != cursor or unit.source_end > self.source_length:
                raise ValueError(
                    "form lattice unit geometry must exactly partition source"
                )
            if (
                self.source_text[unit.source_start : unit.source_end]
                != unit.source_text
            ):
                raise ValueError(
                    "form lattice unit text does not match source geometry"
                )
            unit_index[unit.unit_ref] = unit
            cursor = unit.source_end
        if cursor != self.source_length:
            raise ValueError(
                "form lattice unit geometry does not cover complete source"
            )
        hypothesis_refs: set[str] = set()
        for hypothesis in self.hypotheses:
            if hypothesis.hypothesis_ref in hypothesis_refs:
                raise ValueError("form lattice hypothesis refs must be unique")
            hypothesis_refs.add(hypothesis.hypothesis_ref)
            unknown = set(hypothesis.unit_refs) - unit_index.keys()
            if unknown:
                raise ValueError(
                    f"form lattice hypothesis references unknown units: {sorted(unknown)}"
                )
        object.__setattr__(self, "_unit_index", MappingProxyType(unit_index))
        if self.lattice_ref != stable_ref("form_lattice", self._identity_material()):
            raise ValueError("FormLattice ref mismatch")

    @classmethod
    def create(
        cls,
        *,
        evidence_packet_ref: str,
        form_pack_hash: str,
        source_text: str,
        units: tuple[FormUnit, ...],
        hypotheses: tuple[FormHypothesis, ...],
    ) -> "FormLattice":
        _bounded_evidence_ref(evidence_packet_ref, "evidence_packet_ref")
        _bounded_evidence_ref(form_pack_hash, "form_pack_hash")
        _bounded_source_text(source_text)
        _prebound_tuple(
            units,
            "units",
            max_items=_MAX_FORM_UNITS,
            item_type=FormUnit,
        )
        _prebound_tuple(
            hypotheses,
            "hypotheses",
            max_items=_MAX_HYPOTHESES,
            item_type=FormHypothesis,
        )
        material = {
            "abi_version": FORM_LATTICE_ABI_VERSION,
            "evidence_packet_ref": evidence_packet_ref,
            "form_pack_hash": form_pack_hash,
            "source_text": source_text,
            "source_length": len(source_text),
            "units": [unit.as_dict() for unit in units],
            "hypotheses": [hypothesis.as_dict() for hypothesis in hypotheses],
        }
        return cls(
            abi_version=FORM_LATTICE_ABI_VERSION,
            lattice_ref=stable_ref("form_lattice", material),
            evidence_packet_ref=evidence_packet_ref,
            form_pack_hash=form_pack_hash,
            source_text=source_text,
            source_length=len(source_text),
            units=units,
            hypotheses=hypotheses,
        )

    def _identity_material(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "evidence_packet_ref": self.evidence_packet_ref,
            "form_pack_hash": self.form_pack_hash,
            "source_text": self.source_text,
            "source_length": self.source_length,
            "units": [unit.as_dict() for unit in self.units],
            "hypotheses": [hypothesis.as_dict() for hypothesis in self.hypotheses],
        }

    @property
    def unit_index(self) -> Mapping[str, FormUnit]:
        return self._unit_index

    def unit(self, unit_ref: str) -> FormUnit | None:
        return self._unit_index.get(unit_ref)

    def as_dict(self) -> dict[str, Any]:
        return {"lattice_ref": self.lattice_ref, **self._identity_material()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FormLattice":
        _require_exact_fields(data, cls._FIELDS, "FormLattice")
        _require_abi_version(
            data["abi_version"], FORM_LATTICE_ABI_VERSION, "FormLattice"
        )
        lattice_ref = _bounded_evidence_ref(data["lattice_ref"], "lattice_ref")
        evidence_packet_ref = _bounded_evidence_ref(
            data["evidence_packet_ref"], "evidence_packet_ref"
        )
        form_pack_hash = _bounded_evidence_ref(data["form_pack_hash"], "form_pack_hash")
        source_text = _bounded_source_text(data["source_text"])
        source_length = _require_offset(data["source_length"], "source_length")
        if source_length != len(source_text):
            raise ValueError(
                "form lattice source_length does not match source geometry"
            )
        if not isinstance(data["units"], list):
            raise TypeError("units must be a list")
        if not isinstance(data["hypotheses"], list):
            raise TypeError("hypotheses must be a list")
        if len(data["units"]) > _MAX_FORM_UNITS:
            raise ValueError(f"units exceeds {_MAX_FORM_UNITS} items")
        if len(data["hypotheses"]) > _MAX_HYPOTHESES:
            raise ValueError(f"hypotheses exceeds {_MAX_HYPOTHESES} items")
        rebuilt = cls.create(
            evidence_packet_ref=evidence_packet_ref,
            form_pack_hash=form_pack_hash,
            source_text=source_text,
            units=tuple(FormUnit.from_dict(row) for row in data["units"]),
            hypotheses=tuple(
                FormHypothesis.from_dict(row) for row in data["hypotheses"]
            ),
        )
        if source_length != rebuilt.source_length:
            raise ValueError(
                "form lattice source_length does not match source geometry"
            )
        if lattice_ref != rebuilt.lattice_ref:
            raise ValueError("FormLattice ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical FormLattice encoding")
        return rebuilt


def _bounded_source_text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("source_text must be a string")
    if len(value) > EVIDENCE_MAX_SOURCE_CHARS:
        raise ValueError(f"source text exceeds {EVIDENCE_MAX_SOURCE_CHARS} characters")
    return value


def _prebound_tuple(
    value: object,
    name: str,
    *,
    max_items: int,
    item_type: type,
    nonempty: bool = False,
) -> tuple:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be non-empty")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if any(not isinstance(item, item_type) for item in value):
        raise TypeError(f"{name} contains an invalid item")
    return value


def _require_abi_version(value: object, expected: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} abi_version must be an integer")
    if value != expected:
        raise ValueError(f"unsupported {label} ABI version: {value!r}")
    return value


def _require_exact_fields(
    data: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} payload must be a mapping")
    actual = frozenset(data)
    if actual != expected:
        raise ValueError(
            f"{label} fields mismatch: missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _require_nonempty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string")
    return value


def _require_offset(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _require_string_tuple(
    value: object,
    name: str,
    *,
    nonempty: bool = False,
    max_items: int,
    item_maximum: int | None = None,
    item_name: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be non-empty")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if any(not isinstance(item, str) or not item for item in value):
        raise TypeError(f"{name} must contain non-empty strings")
    if item_maximum is not None:
        label = item_name or f"{name} item"
        for item in value:
            _bounded_evidence_string(item, label, maximum=item_maximum)
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    return value


def _require_feature_pairs(
    value: object, name: str, *, max_items: int
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if any(
        not isinstance(row, tuple)
        or len(row) != 2
        or any(not isinstance(item, str) or not item for item in row)
        for row in value
    ):
        raise TypeError(f"{name} must contain non-empty string pairs")
    for key, item in value:
        _bounded_evidence_string(key, "feature key", maximum=EVIDENCE_MAX_KEY_CHARS)
        _bounded_evidence_string(
            item, "feature value", maximum=EVIDENCE_MAX_SCALAR_CHARS
        )
    return value


def _wire_string_tuple(
    value: object,
    name: str,
    *,
    max_items: int,
    item_maximum: int | None = None,
    item_name: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if any(not isinstance(item, str) or not item for item in value):
        raise TypeError(f"{name} must contain non-empty strings")
    if item_maximum is not None:
        label = item_name or f"{name} item"
        for item in value:
            _bounded_evidence_string(item, label, maximum=item_maximum)
    return tuple(value)


def _wire_feature_pairs(
    value: object, name: str, *, max_items: int
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if any(
        not isinstance(row, list)
        or len(row) != 2
        or any(not isinstance(item, str) or not item for item in row)
        for row in value
    ):
        raise TypeError(f"{name} must contain non-empty string pairs")
    for key, item in value:
        _bounded_evidence_string(key, "feature key", maximum=EVIDENCE_MAX_KEY_CHARS)
        _bounded_evidence_string(
            item, "feature value", maximum=EVIDENCE_MAX_SCALAR_CHARS
        )
    return tuple((row[0], row[1]) for row in value)


# ---------------------------------------------------------------------------
# FormResolver
# ---------------------------------------------------------------------------

# Feature category -> pack key mapping.  Each closed-class category in the
# language pack contributes a feature ``(category, kind)`` to matching units.
_FEATURE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("participant", "participant_deixis"),
    ("binder", "binders"),
    ("query", "query_projection"),
    ("polarity", "polarity"),
    ("modality", "modality"),
    ("tense_aspect", "tense_aspect"),
    ("connector", "connectors"),
    ("discourse", "discourse"),
    ("determiner", "determiners"),
    ("linker", "linkers"),
    ("correction", "correction"),
)

# Constructions detected from feature presence.  Each entry is
# (construction_name, required_feature_category, required_feature_value_prefix).
# A construction fires when at least one unit has a feature in the category
# whose value starts with the given prefix (or any value if prefix is None).
_CONSTRUCTION_RULES: tuple[tuple[str, str, str | None], ...] = (
    ("query", "query", None),
    ("negation", "polarity", None),
    ("modality", "modality", None),
    ("conjunction", "connector", "conjunction"),
    ("disjunction", "connector", "disjunction"),
    ("coordination", "connector", "coordination"),
    ("contrast", "connector", "contrast"),
    ("causal", "connector", "causal"),
    ("conditional", "connector", "conditional"),
    ("hypothetical", "connector", "hypothetical"),
    ("purpose", "connector", "purpose"),
    ("sequence", "connector", "sequence"),
    ("discourse_report", "discourse", "report"),
    ("definition", "discourse", "definition_marker"),
    ("deixis", "participant", None),
    ("tense_aspect", "tense_aspect", None),
)


class FormResolver:
    """Tokenises text into a reversible :class:`FormLattice`.

    The resolver preserves the exact source text: joining every unit's
    ``source_text`` reproduces the input.  It assigns closed-class features
    from the language pack and generates bounded construction hypotheses.

    It does **not** choose operators and does **not** inspect internal ref
    spelling.
    """

    def __init__(self, form_pack: Mapping[str, Any], config: Any) -> None:
        self._pack = dict(form_pack)
        self._config = config
        self._max_units = min(config.max_input_tokens, _MAX_FORM_UNITS)
        self._form_pack_hash = (
            "sha256:" + hashlib.sha256(canonical_bytes(form_pack)).hexdigest()
        )
        self._lowercase = bool(form_pack.get("tokenization", {}).get("lowercase", True))
        self._punctuation = set(
            form_pack.get("tokenization", {}).get("punctuation", [])
        )
        # Build a lookup: normalized_surface -> list of (category, kind)
        self._feature_map: dict[str, list[tuple[str, str]]] = {}
        for category, pack_key in _FEATURE_CATEGORIES:
            entries = form_pack.get(pack_key, {})
            if isinstance(entries, dict):
                for surface, info in entries.items():
                    kind = (
                        info.get("kind", category)
                        if isinstance(info, dict)
                        else str(info)
                    )
                    norm = self._normalize_surface(surface)
                    self._feature_map.setdefault(norm, []).append((category, kind))
            elif isinstance(entries, list):
                for surface in entries:
                    norm = self._normalize_surface(surface)
                    self._feature_map.setdefault(norm, []).append((category, category))

    # -- public ---------------------------------------------------------------

    @property
    def form_pack_hash(self) -> str:
        """Return the exact canonical hash used in lattice lineage."""

        return self._form_pack_hash

    def resolve_evidence(self, packet: EvidencePacket) -> FormLattice:
        """Resolve one exact Evidence ABI 1 packet without changing its identity."""

        if not isinstance(packet, EvidencePacket):
            raise TypeError("packet must be an EvidencePacket")
        if packet.form_pack_hash != self._form_pack_hash:
            raise ValueError("evidence packet form pack hash does not match resolver")
        units = self._tokenize(packet.source_text)
        hypotheses = self._build_hypotheses(units)
        return FormLattice.create(
            evidence_packet_ref=packet.packet_ref,
            form_pack_hash=packet.form_pack_hash,
            units=tuple(units),
            hypotheses=tuple(hypotheses),
            source_text=packet.source_text,
        )

    def resolve(self, text: str) -> FormLattice:
        """Legacy/test helper that first creates one canonical EvidencePacket."""

        _bounded_source_text(text)
        item = EvidenceItem.create(
            source="text",
            content=text,
            source_ref=stable_ref("legacy_text_source", {"source_text": text}),
            provenance_refs=(),
            adapter_receipt_ref=None,
        )
        packet = EvidencePacket.create(
            items=(item,),
            source_text=text,
            form_pack_hash=self._form_pack_hash,
        )
        return self.resolve_evidence(packet)

    # -- tokenisation ---------------------------------------------------------

    def _tokenize(self, text: str) -> list[FormUnit]:
        """Split text into units preserving exact source spans.

        Whitespace and punctuation are kept as their own units so that joining
        all ``source_text`` values reproduces the input exactly.
        """
        if not text:
            return []
        units: list[FormUnit] = []
        i = 0
        n = len(text)
        index = 0
        while i < n:
            if len(units) >= self._max_units:
                raise ValueError("form resolver unit bound exceeded")
            ch = text[i]
            if ch.isspace():
                # Consume a run of whitespace as one unit.
                j = i + 1
                while j < n and text[j].isspace():
                    j += 1
                units.append(self._make_unit(text, i, j, index))
                index += 1
                i = j
            elif ch in self._punctuation:
                # Each punctuation character is its own unit.
                j = i + 1
                units.append(self._make_unit(text, i, j, index))
                index += 1
                i = j
            else:
                # Consume a run of non-whitespace, non-punctuation characters.
                j = i + 1
                while (
                    j < n and not text[j].isspace() and text[j] not in self._punctuation
                ):
                    j += 1
                units.append(self._make_unit(text, i, j, index))
                index += 1
                i = j
        return units

    def _make_unit(self, text: str, start: int, end: int, index: int) -> FormUnit:
        source = text[start:end]
        norm = self._normalize_surface(source)
        features = tuple(self._feature_map.get(norm, ()))
        normalized_forms: tuple[str, ...]
        if source.strip() and source != norm:
            normalized_forms = (norm,)
        elif source.strip():
            normalized_forms = (norm,)
        else:
            # Whitespace-only unit: no normalized form.
            normalized_forms = ()
        return FormUnit(
            unit_ref=f"unit:{index}",
            source_text=source,
            normalized_forms=normalized_forms,
            source_start=start,
            source_end=end,
            features=features,
        )

    def _normalize_surface(self, surface: str) -> str:
        """Normalise a surface for closed-class lookup (casefold + trim)."""
        s = surface.strip()
        if self._lowercase:
            s = s.casefold()
        return s

    # -- construction hypotheses ----------------------------------------------

    def _build_hypotheses(self, units: Sequence[FormUnit]) -> list[FormHypothesis]:
        """Generate bounded construction hypotheses from unit features."""
        hypotheses: list[FormHypothesis] = []
        # Collect units by feature category.
        category_units: dict[str, list[FormUnit]] = {}
        for unit in units:
            if not unit.features:
                continue
            # A unit participates once per construction category, while its
            # ordered feature rows remain available below for exact evidence.
            categories = tuple(dict.fromkeys(category for category, _ in unit.features))
            for category in categories:
                category_units.setdefault(category, []).append(unit)

        for construction, category, prefix in _CONSTRUCTION_RULES:
            if len(hypotheses) >= _MAX_HYPOTHESES:
                break
            matching = category_units.get(category, [])
            if not matching:
                continue
            if prefix is not None:
                matching = [
                    u
                    for u in matching
                    if any(
                        v.startswith(prefix) for _c, v in u.features if _c == category
                    )
                ]
            if not matching:
                continue
            unit_refs = tuple(u.unit_ref for u in matching)
            features = tuple(
                (category, v)
                for u in matching
                for _c, v in u.features
                if _c == category and (prefix is None or v.startswith(prefix))
            )
            hypotheses.append(
                FormHypothesis(
                    hypothesis_ref=f"hyp:{len(hypotheses)}:{construction}",
                    unit_refs=unit_refs,
                    construction=construction,
                    features=features,
                )
            )
        return hypotheses
