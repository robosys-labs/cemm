"""Partition Config ABI 1 for the R4 global four-class assignment.

The config is intentionally acyclic: it binds an authenticated feasibility
basis and minima witness, but never names the final feasibility receipt,
split manifest, Build Receipt, or admission run that descend from it.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

from .canonical import stable_ref
from .r3_codec import exact_fields, exact_int, exact_text
from .r4_partition_contracts import (
    MAX_COMPONENTS,
    MAX_EPISODE_INPUT_BYTES,
    MAX_HYPEREDGES,
    MAX_HYPEREDGES_PER_EPISODE,
    MAX_LABELS,
    MAX_LABELS_PER_EPISODE,
    MAX_MEMBERS_PER_RECORD,
    MAX_PARTITION_ARTIFACT_BYTES,
    MAX_SOURCE_EPISODES,
    MAX_TOTAL_HYPEREDGE_MEMBERSHIPS,
    MAX_TOTAL_LABEL_MEMBERSHIPS,
    SPLITS,
    canonical_json_bytes,
)

PARTITION_CONFIG_ABI_VERSION = 1
RATIO_DENOMINATOR = 100
RARITY_SCALE = 1_000_000
MAX_SOLVER_STATES = 250_000
MAX_SOLVER_KEY_INTS = 128
MAX_SOLVER_MEMORY_BYTES = 192 * 1024 * 1024
MAX_SOLVER_SECONDS = 120
TARGET_WEIGHTS = (
    ("train", 60),
    ("selection", 15),
    ("calibration", 15),
    ("frozen_test", 10),
)

COMPONENT_ORDER_TERMS = (
    "negative_member_count",
    "negative_rare_label_score",
    "component_ref",
)
LEXICOGRAPHIC_OBJECTIVE_TERMS = (
    "size_deviation",
    "label_deviation",
    "bound_violation",
    "tie_break_ref",
)
RARE_LABEL_FORMULA = (
    "sum(label_weight[label_ref] * "
    "(rarity_scale // global_label_member_count[label_ref]) "
    "for label_ref in component_label_refs)"
)
SIZE_DEVIATION_FORMULA = (
    "sum(abs(ratio_denominator * class_count[split] - "
    "source_count * target_weight[split]) for split in splits)"
)
LABEL_DEVIATION_FORMULA = (
    "sum(label_weight[label_ref] * abs(ratio_denominator * "
    "class_label_count[split,label_ref] - "
    "global_label_member_count[label_ref] * target_weight[split]) "
    "for split in splits for label_ref in configured_label_refs)"
)
BOUND_VIOLATION_FORMULA = (
    "sum(max(0, minimum[split,dimension] - observed[split,dimension]) + "
    "max(0, observed[split,dimension] - maximum[split,dimension]) "
    "for split in splits for dimension in configured_dimensions)"
)
TIE_BREAK_NAMESPACE = "r4_partition_tie"

_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*:[^\s:][^\s]*")

__all__ = [
    "BOUND_VIOLATION_FORMULA",
    "COMPONENT_ORDER_TERMS",
    "LABEL_DEVIATION_FORMULA",
    "LEXICOGRAPHIC_OBJECTIVE_TERMS",
    "MAX_SOLVER_KEY_INTS",
    "MAX_SOLVER_MEMORY_BYTES",
    "MAX_SOLVER_SECONDS",
    "MAX_SOLVER_STATES",
    "PARTITION_CONFIG_ABI_VERSION",
    "RARE_LABEL_FORMULA",
    "RARITY_SCALE",
    "RATIO_DENOMINATOR",
    "SIZE_DEVIATION_FORMULA",
    "TARGET_WEIGHTS",
    "TIE_BREAK_NAMESPACE",
    "SplitWeight",
    "PartitionBounds",
    "PartitionObjective",
    "DimensionMinimum",
    "DimensionMaximum",
    "R4PartitionConfig",
]


def _new(cls: type[Any], **values: object) -> Any:
    obj = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(obj, name, value)
    return obj


def _exact_ref(value: object, name: str) -> str:
    text = exact_text(value, name)
    if _REF_RE.fullmatch(text) is None:
        raise ValueError(f"{name} is not an admitted content/reference identity")
    return text


def _exact_split(value: object) -> str:
    split = exact_text(value, "split", maximum=32)
    if split not in SPLITS:
        raise ValueError("unsupported R4 split")
    return split


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise TypeError("JSON object keys must be exact strings")
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise ValueError(f"non-finite JSON value: {value}")


def _strict_decode(raw: object) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise TypeError("serialized partition config must be exact bytes")
    if not raw or len(raw) > MAX_PARTITION_ARTIFACT_BYTES:
        raise ValueError("serialized partition config violates byte bounds")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("serialized partition config is not strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise TypeError("serialized partition config must contain one exact object")
    if raw != canonical_json_bytes(value):
        raise ValueError("serialized partition config bytes are not canonical")
    return value


def _exact_tuple(
    value: object,
    name: str,
    expected_type: type[Any],
    *,
    nonempty: bool,
    maximum: int,
    key: Any,
) -> tuple[Any, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    if any(type(item) is not expected_type for item in value):
        raise TypeError(f"{name} must contain exact {expected_type.__name__} values")
    rows = tuple(value)
    identities = tuple(key(item) for item in rows)
    if len(identities) != len(set(identities)):
        raise ValueError(f"{name} contains duplicate identities")
    if identities != tuple(sorted(identities)):
        raise ValueError(f"{name} must be in canonical order")
    return rows


def _wire_tuple(
    value: object,
    name: str,
    decoder: Any,
    *,
    nonempty: bool,
    maximum: int,
) -> tuple[Any, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} rows")
    return tuple(decoder(item) for item in value)


@dataclass(frozen=True, init=False)
class SplitWeight:
    split: str
    weight: int

    _FIELDS = frozenset({"split", "weight"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use SplitWeight.create")

    @classmethod
    def create(cls, *, split: str, weight: int) -> "SplitWeight":
        return _new(
            cls,
            split=_exact_split(split),
            weight=exact_int(weight, "weight", minimum=1, maximum=RATIO_DENOMINATOR),
        )

    def as_dict(self) -> dict[str, Any]:
        return {"split": self.split, "weight": self.weight}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SplitWeight":
        row = exact_fields(value, cls._FIELDS, "SplitWeight")
        rebuilt = cls.create(split=row["split"], weight=row["weight"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical SplitWeight")
        return rebuilt


@dataclass(frozen=True, init=False)
class PartitionBounds:
    max_source_episodes: int
    max_hyperedges: int
    max_labels: int
    max_members_per_record: int
    max_hyperedges_per_episode: int
    max_labels_per_episode: int
    max_total_hyperedge_memberships: int
    max_total_label_memberships: int
    max_components: int
    max_solver_states: int
    max_solver_key_ints: int
    max_solver_memory_bytes: int
    max_solver_seconds: int
    max_episode_input_bytes: int
    max_partition_artifact_bytes: int

    _FIELDS = frozenset(
        {
            "max_source_episodes",
            "max_hyperedges",
            "max_labels",
            "max_members_per_record",
            "max_hyperedges_per_episode",
            "max_labels_per_episode",
            "max_total_hyperedge_memberships",
            "max_total_label_memberships",
            "max_components",
            "max_solver_states",
            "max_solver_key_ints",
            "max_solver_memory_bytes",
            "max_solver_seconds",
            "max_episode_input_bytes",
            "max_partition_artifact_bytes",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use PartitionBounds.reviewed")

    @classmethod
    def reviewed(cls) -> "PartitionBounds":
        return _new(
            cls,
            max_source_episodes=MAX_SOURCE_EPISODES,
            max_hyperedges=MAX_HYPEREDGES,
            max_labels=MAX_LABELS,
            max_members_per_record=MAX_MEMBERS_PER_RECORD,
            max_hyperedges_per_episode=MAX_HYPEREDGES_PER_EPISODE,
            max_labels_per_episode=MAX_LABELS_PER_EPISODE,
            max_total_hyperedge_memberships=MAX_TOTAL_HYPEREDGE_MEMBERSHIPS,
            max_total_label_memberships=MAX_TOTAL_LABEL_MEMBERSHIPS,
            max_components=MAX_COMPONENTS,
            max_solver_states=MAX_SOLVER_STATES,
            max_solver_key_ints=MAX_SOLVER_KEY_INTS,
            max_solver_memory_bytes=MAX_SOLVER_MEMORY_BYTES,
            max_solver_seconds=MAX_SOLVER_SECONDS,
            max_episode_input_bytes=MAX_EPISODE_INPUT_BYTES,
            max_partition_artifact_bytes=MAX_PARTITION_ARTIFACT_BYTES,
        )

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in sorted(self._FIELDS)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PartitionBounds":
        row = exact_fields(value, cls._FIELDS, "PartitionBounds")
        expected = cls.reviewed()
        for name in cls._FIELDS:
            exact_int(row[name], name, minimum=1)
        if expected.as_dict() != dict(row):
            raise ValueError("PartitionBounds differs from the reviewed hard bounds")
        return expected


@dataclass(frozen=True, init=False)
class PartitionObjective:
    ratio_denominator: int
    rarity_scale: int
    component_order_terms: tuple[str, ...]
    lexicographic_terms: tuple[str, ...]
    rare_label_formula: str
    size_deviation_formula: str
    label_deviation_formula: str
    bound_violation_formula: str
    tie_break_namespace: str

    _FIELDS = frozenset(
        {
            "ratio_denominator",
            "rarity_scale",
            "component_order_terms",
            "lexicographic_terms",
            "rare_label_formula",
            "size_deviation_formula",
            "label_deviation_formula",
            "bound_violation_formula",
            "tie_break_namespace",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use PartitionObjective.reviewed")

    @classmethod
    def reviewed(cls) -> "PartitionObjective":
        return _new(
            cls,
            ratio_denominator=RATIO_DENOMINATOR,
            rarity_scale=RARITY_SCALE,
            component_order_terms=COMPONENT_ORDER_TERMS,
            lexicographic_terms=LEXICOGRAPHIC_OBJECTIVE_TERMS,
            rare_label_formula=RARE_LABEL_FORMULA,
            size_deviation_formula=SIZE_DEVIATION_FORMULA,
            label_deviation_formula=LABEL_DEVIATION_FORMULA,
            bound_violation_formula=BOUND_VIOLATION_FORMULA,
            tie_break_namespace=TIE_BREAK_NAMESPACE,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ratio_denominator": self.ratio_denominator,
            "rarity_scale": self.rarity_scale,
            "component_order_terms": list(self.component_order_terms),
            "lexicographic_terms": list(self.lexicographic_terms),
            "rare_label_formula": self.rare_label_formula,
            "size_deviation_formula": self.size_deviation_formula,
            "label_deviation_formula": self.label_deviation_formula,
            "bound_violation_formula": self.bound_violation_formula,
            "tie_break_namespace": self.tie_break_namespace,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PartitionObjective":
        row = exact_fields(value, cls._FIELDS, "PartitionObjective")
        if type(row["component_order_terms"]) is not list or type(row["lexicographic_terms"]) is not list:
            raise TypeError("partition objective terms must be exact lists")
        expected = cls.reviewed()
        if expected.as_dict() != dict(row):
            raise ValueError("PartitionObjective differs from the reviewed integer formulas")
        return expected


@dataclass(frozen=True, init=False)
class DimensionMinimum:
    dimension_ref: str
    split: str
    minimum: int

    _FIELDS = frozenset({"dimension_ref", "split", "minimum"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use DimensionMinimum.create")

    @classmethod
    def create(
        cls, *, dimension_ref: str, split: str, minimum: int
    ) -> "DimensionMinimum":
        return _new(
            cls,
            dimension_ref=_exact_ref(dimension_ref, "dimension_ref"),
            split=_exact_split(split),
            minimum=exact_int(
                minimum, "minimum", minimum=1, maximum=MAX_SOURCE_EPISODES
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension_ref": self.dimension_ref,
            "split": self.split,
            "minimum": self.minimum,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DimensionMinimum":
        row = exact_fields(value, cls._FIELDS, "DimensionMinimum")
        rebuilt = cls.create(**row)
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DimensionMinimum")
        return rebuilt


@dataclass(frozen=True, init=False)
class DimensionMaximum:
    dimension_ref: str
    split: str
    maximum: int

    _FIELDS = frozenset({"dimension_ref", "split", "maximum"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use DimensionMaximum.create")

    @classmethod
    def create(
        cls, *, dimension_ref: str, split: str, maximum: int
    ) -> "DimensionMaximum":
        return _new(
            cls,
            dimension_ref=_exact_ref(dimension_ref, "dimension_ref"),
            split=_exact_split(split),
            maximum=exact_int(
                maximum, "maximum", minimum=1, maximum=MAX_SOURCE_EPISODES
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension_ref": self.dimension_ref,
            "split": self.split,
            "maximum": self.maximum,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DimensionMaximum":
        row = exact_fields(value, cls._FIELDS, "DimensionMaximum")
        rebuilt = cls.create(**row)
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DimensionMaximum")
        return rebuilt


@dataclass(frozen=True, init=False)
class R4PartitionConfig:
    abi_version: int
    config_ref: str
    seed: int
    target_weights: tuple[SplitWeight, ...]
    bounds: PartitionBounds
    objective: PartitionObjective
    minima: tuple[DimensionMinimum, ...]
    maxima: tuple[DimensionMaximum, ...]
    feasibility_basis_ref: str
    minima_witness_ref: str

    _FIELDS = frozenset(
        {
            "abi_version",
            "config_ref",
            "seed",
            "target_weights",
            "bounds",
            "objective",
            "minima",
            "maxima",
            "feasibility_basis_ref",
            "minima_witness_ref",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use R4PartitionConfig.create")

    @classmethod
    def create(
        cls,
        *,
        seed: int,
        target_weights: tuple[SplitWeight, ...],
        bounds: PartitionBounds,
        objective: PartitionObjective,
        minima: tuple[DimensionMinimum, ...],
        maxima: tuple[DimensionMaximum, ...],
        feasibility_basis_ref: str,
        minima_witness_ref: str,
    ) -> "R4PartitionConfig":
        weights = _exact_tuple(
            target_weights,
            "target_weights",
            SplitWeight,
            nonempty=True,
            maximum=len(SPLITS),
            key=lambda row: SPLITS.index(row.split),
        )
        if tuple((row.split, row.weight) for row in weights) != TARGET_WEIGHTS:
            raise ValueError("target_weights must be exactly 60/15/15/10")
        if type(bounds) is not PartitionBounds or bounds.as_dict() != PartitionBounds.reviewed().as_dict():
            raise TypeError("bounds must be the exact reviewed PartitionBounds")
        if type(objective) is not PartitionObjective or objective.as_dict() != PartitionObjective.reviewed().as_dict():
            raise TypeError("objective must be the exact reviewed PartitionObjective")
        minimum_rows = _exact_tuple(
            minima,
            "minima",
            DimensionMinimum,
            nonempty=True,
            maximum=MAX_LABELS * len(SPLITS),
            key=lambda row: (row.dimension_ref, SPLITS.index(row.split)),
        )
        maximum_rows = _exact_tuple(
            maxima,
            "maxima",
            DimensionMaximum,
            nonempty=True,
            maximum=MAX_LABELS * len(SPLITS),
            key=lambda row: (row.dimension_ref, SPLITS.index(row.split)),
        )
        minima_by_key = {
            (row.dimension_ref, row.split): row.minimum for row in minimum_rows
        }
        maxima_by_key = {
            (row.dimension_ref, row.split): row.maximum for row in maximum_rows
        }
        if minima_by_key.keys() != maxima_by_key.keys():
            raise ValueError("minima and maxima must cover identical dimension/split keys")
        if any(minima_by_key[key] > maxima_by_key[key] for key in minima_by_key):
            raise ValueError("a configured minimum exceeds its maximum")
        splits_by_dimension: dict[str, list[str]] = {}
        for dimension_ref, split in minima_by_key:
            splits_by_dimension.setdefault(dimension_ref, []).append(split)
        if any(tuple(splits) != SPLITS for splits in splits_by_dimension.values()):
            raise ValueError(
                "every configured dimension must cover every canonical split"
            )
        basis = _exact_ref(feasibility_basis_ref, "feasibility_basis_ref")
        witness = _exact_ref(minima_witness_ref, "minima_witness_ref")
        if basis == witness:
            raise ValueError("feasibility basis and minima witness must be distinct identities")
        material = {
            "abi_version": PARTITION_CONFIG_ABI_VERSION,
            "seed": exact_int(seed, "seed"),
            "target_weights": [row.as_dict() for row in weights],
            "bounds": bounds.as_dict(),
            "objective": objective.as_dict(),
            "minima": [row.as_dict() for row in minimum_rows],
            "maxima": [row.as_dict() for row in maximum_rows],
            "feasibility_basis_ref": basis,
            "minima_witness_ref": witness,
        }
        return _new(
            cls,
            abi_version=PARTITION_CONFIG_ABI_VERSION,
            config_ref=stable_ref("r4_partition_config_v1", material),
            seed=material["seed"],
            target_weights=weights,
            bounds=bounds,
            objective=objective,
            minima=minimum_rows,
            maxima=maximum_rows,
            feasibility_basis_ref=basis,
            minima_witness_ref=witness,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "config_ref": self.config_ref,
            "seed": self.seed,
            "target_weights": [row.as_dict() for row in self.target_weights],
            "bounds": self.bounds.as_dict(),
            "objective": self.objective.as_dict(),
            "minima": [row.as_dict() for row in self.minima],
            "maxima": [row.as_dict() for row in self.maxima],
            "feasibility_basis_ref": self.feasibility_basis_ref,
            "minima_witness_ref": self.minima_witness_ref,
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4PartitionConfig":
        row = exact_fields(value, cls._FIELDS, "R4PartitionConfig")
        if row["abi_version"] != PARTITION_CONFIG_ABI_VERSION:
            raise ValueError("unsupported Partition Config ABI")
        rebuilt = cls.create(
            seed=row["seed"],
            target_weights=_wire_tuple(
                row["target_weights"],
                "target_weights",
                SplitWeight.from_dict,
                nonempty=True,
                maximum=len(SPLITS),
            ),
            bounds=PartitionBounds.from_dict(row["bounds"]),
            objective=PartitionObjective.from_dict(row["objective"]),
            minima=_wire_tuple(
                row["minima"],
                "minima",
                DimensionMinimum.from_dict,
                nonempty=True,
                maximum=MAX_LABELS * len(SPLITS),
            ),
            maxima=_wire_tuple(
                row["maxima"],
                "maxima",
                DimensionMaximum.from_dict,
                nonempty=True,
                maximum=MAX_LABELS * len(SPLITS),
            ),
            feasibility_basis_ref=row["feasibility_basis_ref"],
            minima_witness_ref=row["minima_witness_ref"],
        )
        if rebuilt.config_ref != row["config_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4PartitionConfig")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4PartitionConfig":
        return cls.from_dict(_strict_decode(raw))
