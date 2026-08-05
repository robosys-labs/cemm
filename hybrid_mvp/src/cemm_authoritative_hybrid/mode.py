"""Structural semantic-mode projection from closed-class FormLattice evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import stable_ref
from .cycle import SemanticMode
from .r3_codec import exact_fields, exact_refs, exact_text, wire_refs

MODE_PROJECTION_ABI_VERSION = 1

__all__ = [
    "MODE_PROJECTION_ABI_VERSION",
    "ModeProjectionError",
    "ModeProjection",
    "StructuralModeProjector",
]


class ModeProjectionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = exact_text(code, "mode error code")
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True, init=False)
class ModeProjection:
    abi_version: int
    projection_ref: str
    form_lattice_ref: str
    mode: SemanticMode
    evidence_unit_refs: tuple[str, ...]
    construction_refs: tuple[str, ...]
    feature_refs: tuple[str, ...]

    _FIELDS = frozenset({
        "abi_version", "projection_ref", "form_lattice_ref", "mode",
        "evidence_unit_refs", "construction_refs", "feature_refs",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ModeProjection.create")

    @classmethod
    def create(
        cls,
        *,
        form_lattice_ref: str,
        mode: SemanticMode,
        evidence_unit_refs: tuple[str, ...],
        construction_refs: tuple[str, ...],
        feature_refs: tuple[str, ...],
    ) -> "ModeProjection":
        if cls is not ModeProjection:
            raise TypeError("ModeProjection factories require exact class")
        if type(mode) is not SemanticMode:
            raise TypeError("mode must be exact SemanticMode")
        values = {
            "form_lattice_ref": exact_text(form_lattice_ref, "form_lattice_ref"),
            "mode": mode,
            "evidence_unit_refs": exact_refs(evidence_unit_refs, "evidence_unit_refs"),
            "construction_refs": exact_refs(construction_refs, "construction_refs"),
            "feature_refs": exact_refs(feature_refs, "feature_refs"),
        }
        material = {
            "abi_version": MODE_PROJECTION_ABI_VERSION,
            "form_lattice_ref": values["form_lattice_ref"],
            "mode": mode.value,
            "evidence_unit_refs": list(values["evidence_unit_refs"]),
            "construction_refs": list(values["construction_refs"]),
            "feature_refs": list(values["feature_refs"]),
        }
        result = object.__new__(cls)
        object.__setattr__(result, "abi_version", MODE_PROJECTION_ABI_VERSION)
        object.__setattr__(result, "projection_ref", stable_ref("mode_projection", material))
        for name, value in values.items():
            object.__setattr__(result, name, value)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": MODE_PROJECTION_ABI_VERSION,
            "projection_ref": self.projection_ref,
            "form_lattice_ref": self.form_lattice_ref,
            "mode": self.mode.value,
            "evidence_unit_refs": list(self.evidence_unit_refs),
            "construction_refs": list(self.construction_refs),
            "feature_refs": list(self.feature_refs),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModeProjection":
        data = exact_fields(value, cls._FIELDS, "ModeProjection")
        if type(data["abi_version"]) is not int or data["abi_version"] != MODE_PROJECTION_ABI_VERSION:
            raise ValueError("unsupported Mode Projection ABI")
        if type(data["mode"]) is not str:
            raise TypeError("mode wire value must be exact str")
        rebuilt = cls.create(
            form_lattice_ref=data["form_lattice_ref"],
            mode=SemanticMode(data["mode"]),
            evidence_unit_refs=wire_refs(data["evidence_unit_refs"], "evidence_unit_refs"),
            construction_refs=wire_refs(data["construction_refs"], "construction_refs"),
            feature_refs=wire_refs(data["feature_refs"], "feature_refs"),
        )
        if rebuilt.projection_ref != data["projection_ref"] or rebuilt.as_dict() != data:
            raise ValueError("non-canonical ModeProjection encoding")
        return rebuilt


_CONSTRUCTION_MODES = {
    "query": SemanticMode.QUERY,
    "interrogative": SemanticMode.QUERY,
    "wh_query": SemanticMode.QUERY,
    "polar_query": SemanticMode.QUERY,
    "request": SemanticMode.REQUEST,
    "directive": SemanticMode.REQUEST,
    "imperative": SemanticMode.REQUEST,
    "operation_request": SemanticMode.REQUEST,
    "simulation": SemanticMode.SIMULATE,
    "hypothetical": SemanticMode.SIMULATE,
    "counterfactual": SemanticMode.SIMULATE,
    "conditional_simulation": SemanticMode.SIMULATE,
    "declarative": SemanticMode.OBSERVE,
    "assertion": SemanticMode.OBSERVE,
    "observation": SemanticMode.OBSERVE,
}
_FEATURE_MODES = {
    ("query", "query"): SemanticMode.QUERY,
    ("discourse", "question"): SemanticMode.QUERY,
    ("force", "query"): SemanticMode.QUERY,
    ("force", "request"): SemanticMode.REQUEST,
    ("discourse", "directive"): SemanticMode.REQUEST,
    ("modality", "conditional"): SemanticMode.SIMULATE,
    ("force", "simulate"): SemanticMode.SIMULATE,
}


def _feature_pairs(row: object) -> Iterable[tuple[str, str]]:
    for field in ("features", "feature_pairs", "annotations"):
        value = getattr(row, field, ())
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str) and isinstance(item, str):
                    yield key, item
        elif isinstance(value, (tuple, list)):
            for item in value:
                if isinstance(item, (tuple, list)) and len(item) == 2 and all(isinstance(v, str) for v in item):
                    yield item[0], item[1]


class StructuralModeProjector:
    """Project one closed mode without inspecting raw surface text."""

    def project(self, lattice: object) -> ModeProjection:
        lattice_ref = exact_text(getattr(lattice, "lattice_ref", None), "form_lattice_ref")
        hypotheses = getattr(lattice, "hypotheses", ())
        units = getattr(lattice, "units", ())
        if type(hypotheses) is not tuple:
            raise TypeError("FormLattice hypotheses must be an exact tuple")
        if type(units) is not tuple:
            raise TypeError("FormLattice units must be an exact tuple")

        evidence: dict[SemanticMode, dict[str, list[str]]] = {}
        def add(mode: SemanticMode, *, unit_refs: Iterable[str] = (), construction_ref: str | None = None, feature_ref: str | None = None) -> None:
            row = evidence.setdefault(mode, {"units": [], "constructions": [], "features": []})
            row["units"].extend(ref for ref in unit_refs if isinstance(ref, str) and ref)
            if construction_ref:
                row["constructions"].append(construction_ref)
            if feature_ref:
                row["features"].append(feature_ref)

        for hypothesis in hypotheses:
            construction = getattr(hypothesis, "construction", None)
            mode = _CONSTRUCTION_MODES.get(construction)
            unit_refs = tuple(getattr(hypothesis, "unit_refs", ()))
            hypothesis_ref = getattr(hypothesis, "hypothesis_ref", None)
            if mode is not None:
                add(mode, unit_refs=unit_refs, construction_ref=hypothesis_ref)
            for category, value in _feature_pairs(hypothesis):
                feature_mode = _FEATURE_MODES.get((category, value))
                if feature_mode is not None:
                    add(feature_mode, unit_refs=unit_refs, feature_ref=f"{category}:{value}")

        for unit in units:
            unit_ref = getattr(unit, "unit_ref", None)
            for category, value in _feature_pairs(unit):
                feature_mode = _FEATURE_MODES.get((category, value))
                if feature_mode is not None:
                    add(feature_mode, unit_refs=(unit_ref,), feature_ref=f"{category}:{value}")

        non_observe = tuple(mode for mode in evidence if mode is not SemanticMode.OBSERVE)
        if len(non_observe) > 1:
            raise ModeProjectionError(
                "mode_ambiguous",
                ",".join(sorted(mode.value for mode in non_observe)),
            )
        selected = non_observe[0] if non_observe else SemanticMode.OBSERVE
        row = evidence.get(selected, {"units": [], "constructions": [], "features": []})
        return ModeProjection.create(
            form_lattice_ref=lattice_ref,
            mode=selected,
            evidence_unit_refs=tuple(dict.fromkeys(row["units"])),
            construction_refs=tuple(dict.fromkeys(row["constructions"])),
            feature_refs=tuple(dict.fromkeys(row["features"])),
        )
