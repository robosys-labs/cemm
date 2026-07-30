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

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

__all__ = [
    "EvidenceItem",
    "EvidencePacket",
    "FormUnit",
    "FormHypothesis",
    "FormLattice",
    "FormResolver",
]

# Maximum number of construction hypotheses the resolver may emit.
_MAX_HYPOTHESES = 16


# ---------------------------------------------------------------------------
# Evidence items and packets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of typed evidence from text, sensor, or operation.

    Attributes:
        source: ``"text"``, ``"sensor"``, or ``"operation"``.
        content: the raw content (str for text, Mapping for sensor/operation).
        source_ref: a stable ref identifying this evidence item.
        provenance_refs: tuple of provenance refs for this item.
        adapter_receipt_ref: receipt ref for sensor/operation evidence, or None.
    """

    source: str
    content: str | Mapping[str, Any]
    source_ref: str
    provenance_refs: tuple[str, ...]
    adapter_receipt_ref: str | None = None


@dataclass(frozen=True)
class EvidencePacket:
    """A packet of evidence items with the source text and form pack hash.

    Attributes:
        items: tuple of :class:`EvidenceItem`.
        source_text: the original source text (for text evidence).
        form_pack_hash: the SHA-256 hash of the language pack used.
    """

    items: tuple[EvidenceItem, ...]
    source_text: str
    form_pack_hash: str


# ---------------------------------------------------------------------------
# Form units, hypotheses, and lattice
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormUnit:
    """A single source-preserving form unit with closed-class features.

    Attributes:
        unit_ref: a stable ref for this unit (e.g. ``"unit:0"``).
        source_text: the exact substring of the source this unit covers.
        normalized_forms: tuple of normalized surface forms.
        source_start: start offset in the source text (inclusive).
        source_end: end offset in the source text (exclusive).
        features: tuple of ``(key, value)`` pairs for closed-class features.
    """

    unit_ref: str
    source_text: str
    normalized_forms: tuple[str, ...]
    source_start: int
    source_end: int
    features: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class FormHypothesis:
    """A bounded construction hypothesis over a set of units.

    Attributes:
        hypothesis_ref: a stable ref for this hypothesis.
        unit_refs: tuple of unit refs participating in this construction.
        construction: the construction kind (e.g. ``"query"``) or None.
        features: tuple of ``(key, value)`` pairs for construction features.
    """

    hypothesis_ref: str
    unit_refs: tuple[str, ...]
    construction: str | None
    features: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class FormLattice:
    """The reversible form lattice produced by :class:`FormResolver`.

    Attributes:
        units: tuple of :class:`FormUnit` covering the entire source.
        hypotheses: tuple of :class:`FormHypothesis` (bounded by 16).
        source_text: the original source text.
    """

    units: tuple[FormUnit, ...]
    hypotheses: tuple[FormHypothesis, ...]
    source_text: str


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
    ("coordination", "connector", "coordination"),
    ("contrast", "connector", "contrast"),
    ("causal", "connector", "causal"),
    ("conditional", "connector", "conditional"),
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
                    kind = info.get("kind", category) if isinstance(info, dict) else str(info)
                    norm = self._normalize_surface(surface)
                    self._feature_map.setdefault(norm, []).append((category, kind))
            elif isinstance(entries, list):
                for surface in entries:
                    norm = self._normalize_surface(surface)
                    self._feature_map.setdefault(norm, []).append((category, category))

    # -- public ---------------------------------------------------------------

    def resolve(self, text: str) -> FormLattice:
        """Tokenise ``text`` into a :class:`FormLattice`."""
        units = self._tokenize(text)
        hypotheses = self._build_hypotheses(units)
        return FormLattice(
            units=tuple(units),
            hypotheses=tuple(hypotheses),
            source_text=text,
        )

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
                while j < n and not text[j].isspace() and text[j] not in self._punctuation:
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
            for category, _kind in unit.features:
                category_units.setdefault(category, []).append(unit)

        for construction, category, prefix in _CONSTRUCTION_RULES:
            if len(hypotheses) >= _MAX_HYPOTHESES:
                break
            matching = category_units.get(category, [])
            if not matching:
                continue
            if prefix is not None:
                matching = [
                    u for u in matching
                    if any(v.startswith(prefix) for _c, v in u.features if _c == category)
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
            hypotheses.append(FormHypothesis(
                hypothesis_ref=f"hyp:{len(hypotheses)}:{construction}",
                unit_refs=unit_refs,
                construction=construction,
                features=features,
            ))
        return hypotheses
