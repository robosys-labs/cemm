"""Independent transitive leakage sealing across R4 lineage axes."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    GroundedReference,
    LiteralValue,
    SemanticExpression,
    UnresolvedValue,
)
from .r3_codec import exact_fields, exact_int, exact_refs, exact_text, wire_refs
from .r4_contracts import ExpectedCycleContract
from .r4_mutations import SemanticMutation

PARTITION_AXIS_MANIFEST_ABI_VERSION = 2
TRAINING_ALLOWLIST_ABI_VERSION = 2
MAX_PROTECTED_VALUE_REFS = 4_096

AXES = (
    "general",
    "lexical",
    "semantic_target",
    "topology",
    "dialogue",
    "mutation",
    "realization",
)

__all__ = [
    "AXES",
    "PARTITION_AXIS_MANIFEST_ABI_VERSION",
    "TRAINING_ALLOWLIST_ABI_VERSION",
    "PartitionComponent",
    "PartitionAxisManifest",
    "TrainingAllowlist",
    "IndependentAxisPartitioner",
]


def _bucket(component_ref: str, seed: int, ratios: tuple[int, int, int]) -> str:
    digest = hashlib.sha256(f"{seed}:{component_ref}".encode("utf-8")).digest()
    position = int.from_bytes(digest[:8], "big") % sum(ratios)
    if position < ratios[0]:
        return "train"
    if position < ratios[0] + ratios[1]:
        return "validation"
    return "test"


class _UnionFind:
    def __init__(self, refs: Iterable[str]) -> None:
        self.parent = {ref: ref for ref in refs}

    def find(self, ref: str) -> str:
        parent = self.parent[ref]
        if parent != ref:
            self.parent[ref] = self.find(parent)
        return self.parent[ref]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if b < a:
            a, b = b, a
        self.parent[b] = a


@dataclass(frozen=True)
class PartitionComponent:
    component_ref: str
    protected_value_refs: tuple[str, ...]
    member_refs: tuple[str, ...]
    split: str

    _FIELDS = frozenset(
        {"component_ref", "protected_value_refs", "member_refs", "split"}
    )

    def __post_init__(self) -> None:
        exact_text(self.component_ref, "component_ref")
        object.__setattr__(
            self,
            "protected_value_refs",
            exact_refs(
                self.protected_value_refs,
                "protected_value_refs",
                nonempty=True,
                maximum=MAX_PROTECTED_VALUE_REFS,
            ),
        )
        object.__setattr__(
            self,
            "member_refs",
            exact_refs(self.member_refs, "member_refs", nonempty=True),
        )
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("invalid component split")
        expected = stable_ref(
            "partition_component_v2",
            {
                "protected_value_refs": list(self.protected_value_refs),
                "member_refs": list(self.member_refs),
                "split": self.split,
            },
        )
        if self.component_ref != expected:
            raise ValueError("partition component ref mismatch")

    @classmethod
    def create(
        cls,
        *,
        protected_value_refs: tuple[str, ...],
        member_refs: tuple[str, ...],
        split: str,
    ) -> "PartitionComponent":
        protected = exact_refs(
            tuple(sorted(protected_value_refs)),
            "protected_value_refs",
            nonempty=True,
            maximum=MAX_PROTECTED_VALUE_REFS,
        )
        members = exact_refs(tuple(sorted(member_refs)), "member_refs", nonempty=True)
        if split not in {"train", "validation", "test"}:
            raise ValueError("invalid component split")
        material = {
            "protected_value_refs": list(protected),
            "member_refs": list(members),
            "split": split,
        }
        return cls(stable_ref("partition_component_v2", material), protected, members, split)

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_ref": self.component_ref,
            "protected_value_refs": list(self.protected_value_refs),
            "member_refs": list(self.member_refs),
            "split": self.split,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PartitionComponent":
        row = exact_fields(value, cls._FIELDS, "PartitionComponent")
        rebuilt = cls.create(
            protected_value_refs=wire_refs(
                row["protected_value_refs"],
                "protected_value_refs",
                nonempty=True,
                maximum=MAX_PROTECTED_VALUE_REFS,
            ),
            member_refs=wire_refs(row["member_refs"], "member_refs", nonempty=True),
            split=row["split"],
        )
        if rebuilt.component_ref != row["component_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical PartitionComponent")
        return rebuilt


@dataclass(frozen=True, init=False)
class PartitionAxisManifest:
    abi_version: int
    manifest_ref: str
    axis: str
    source_set_ref: str
    seed: int
    protected_keys: tuple[str, ...]
    source_refs: tuple[str, ...]
    components: tuple[PartitionComponent, ...]
    train_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    test_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "manifest_ref",
            "axis",
            "source_set_ref",
            "seed",
            "protected_keys",
            "source_refs",
            "components",
            "train_refs",
            "validation_refs",
            "test_refs",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use PartitionAxisManifest.create")

    @classmethod
    def create(
        cls,
        *,
        axis: str,
        source_set_ref: str,
        seed: int,
        protected_keys: tuple[str, ...],
        source_refs: tuple[str, ...],
        components: tuple[PartitionComponent, ...],
    ) -> "PartitionAxisManifest":
        axis_name = exact_text(axis, "axis")
        if axis_name not in AXES:
            raise ValueError("unsupported partition axis")
        universe = exact_refs(tuple(sorted(source_refs)), "source_refs", nonempty=True)
        if type(components) is not tuple or not components:
            raise ValueError("partition manifest requires components")
        if any(type(row) is not PartitionComponent for row in components):
            raise TypeError("components must contain PartitionComponent values")
        ordered = tuple(sorted(components, key=lambda row: row.component_ref))
        all_members = [member for component in ordered for member in component.member_refs]
        if len(all_members) != len(set(all_members)):
            raise ValueError("partition components overlap")
        if tuple(sorted(all_members)) != universe:
            raise ValueError("partition components do not exactly cover source universe")
        train = tuple(
            sorted(member for row in ordered if row.split == "train" for member in row.member_refs)
        )
        validation = tuple(
            sorted(member for row in ordered if row.split == "validation" for member in row.member_refs)
        )
        test = tuple(
            sorted(member for row in ordered if row.split == "test" for member in row.member_refs)
        )
        expected_source_set = stable_ref("r4_partition_source_v2", list(universe))
        if source_set_ref != expected_source_set:
            raise ValueError("partition source_set_ref mismatch")
        values = {
            "axis": axis_name,
            "source_set_ref": source_set_ref,
            "seed": exact_int(seed, "seed"),
            "protected_keys": exact_refs(
                protected_keys, "protected_keys", nonempty=True
            ),
            "source_refs": universe,
            "components": ordered,
            "train_refs": train,
            "validation_refs": validation,
            "test_refs": test,
        }
        material = {
            "abi_version": PARTITION_AXIS_MANIFEST_ABI_VERSION,
            "axis": axis_name,
            "source_set_ref": source_set_ref,
            "seed": seed,
            "protected_keys": list(values["protected_keys"]),
            "source_refs": list(universe),
            "components": [row.as_dict() for row in ordered],
            "train_refs": list(train),
            "validation_refs": list(validation),
            "test_refs": list(test),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", PARTITION_AXIS_MANIFEST_ABI_VERSION)
        object.__setattr__(obj, "manifest_ref", stable_ref("partition_axis_manifest_v2", material))
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "manifest_ref": self.manifest_ref,
            "axis": self.axis,
            "source_set_ref": self.source_set_ref,
            "seed": self.seed,
            "protected_keys": list(self.protected_keys),
            "source_refs": list(self.source_refs),
            "components": [row.as_dict() for row in self.components],
            "train_refs": list(self.train_refs),
            "validation_refs": list(self.validation_refs),
            "test_refs": list(self.test_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PartitionAxisManifest":
        row = exact_fields(value, cls._FIELDS, "PartitionAxisManifest")
        if row["abi_version"] != PARTITION_AXIS_MANIFEST_ABI_VERSION:
            raise ValueError("unsupported Partition Axis Manifest ABI")
        if type(row["components"]) is not list:
            raise TypeError("components must be exact list")
        rebuilt = cls.create(
            axis=row["axis"],
            source_set_ref=row["source_set_ref"],
            seed=row["seed"],
            protected_keys=wire_refs(row["protected_keys"], "protected_keys", nonempty=True),
            source_refs=wire_refs(row["source_refs"], "source_refs", nonempty=True),
            components=tuple(PartitionComponent.from_dict(item) for item in row["components"]),
        )
        if (
            rebuilt.manifest_ref != row["manifest_ref"]
            or rebuilt.train_refs != wire_refs(row["train_refs"], "train_refs")
            or rebuilt.validation_refs
            != wire_refs(row["validation_refs"], "validation_refs")
            or rebuilt.test_refs != wire_refs(row["test_refs"], "test_refs")
            or rebuilt.as_dict() != dict(row)
        ):
            raise ValueError("non-canonical PartitionAxisManifest")
        return rebuilt


@dataclass(frozen=True, init=False)
class TrainingAllowlist:
    abi_version: int
    allowlist_ref: str
    source_set_ref: str
    axis_manifest_refs: tuple[str, ...]
    train_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "allowlist_ref",
            "source_set_ref",
            "axis_manifest_refs",
            "train_refs",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use TrainingAllowlist.from_manifests")

    @classmethod
    def from_manifests(
        cls, manifests: tuple[PartitionAxisManifest, ...]
    ) -> "TrainingAllowlist":
        if type(manifests) is not tuple or not manifests:
            raise ValueError("training allowlist requires axis manifests")
        if any(type(row) is not PartitionAxisManifest for row in manifests):
            raise TypeError("manifests must contain PartitionAxisManifest")
        axes = tuple(row.axis for row in manifests)
        if len(axes) != len(set(axes)) or set(axes) != set(AXES):
            raise ValueError("training allowlist requires exactly every protected axis")
        source_refs = manifests[0].source_refs
        source_set_ref = manifests[0].source_set_ref
        if any(
            row.source_refs != source_refs or row.source_set_ref != source_set_ref
            for row in manifests[1:]
        ):
            raise ValueError("axis manifests do not bind the same source universe")
        train = set(source_refs)
        for row in manifests:
            train.intersection_update(row.train_refs)
        values = {
            "source_set_ref": source_set_ref,
            "axis_manifest_refs": tuple(
                row.manifest_ref for row in sorted(manifests, key=lambda item: item.axis)
            ),
            "train_refs": tuple(sorted(train)),
        }
        material = {
            "abi_version": TRAINING_ALLOWLIST_ABI_VERSION,
            "source_set_ref": values["source_set_ref"],
            "axis_manifest_refs": list(values["axis_manifest_refs"]),
            "train_refs": list(values["train_refs"]),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", TRAINING_ALLOWLIST_ABI_VERSION)
        object.__setattr__(obj, "allowlist_ref", stable_ref("training_allowlist_v2", material))
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "allowlist_ref": self.allowlist_ref,
            "source_set_ref": self.source_set_ref,
            "axis_manifest_refs": list(self.axis_manifest_refs),
            "train_refs": list(self.train_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TrainingAllowlist":
        row = exact_fields(value, cls._FIELDS, "TrainingAllowlist")
        if row["abi_version"] != TRAINING_ALLOWLIST_ABI_VERSION:
            raise ValueError("unsupported Training Allowlist ABI")
        source_set_ref = exact_text(row["source_set_ref"], "source_set_ref")
        axis_manifest_refs = wire_refs(
            row["axis_manifest_refs"], "axis_manifest_refs", nonempty=True
        )
        train_refs = wire_refs(row["train_refs"], "train_refs")
        material = {
            "abi_version": TRAINING_ALLOWLIST_ABI_VERSION,
            "source_set_ref": source_set_ref,
            "axis_manifest_refs": list(axis_manifest_refs),
            "train_refs": list(train_refs),
        }
        allowlist_ref = stable_ref("training_allowlist_v2", material)
        if row["allowlist_ref"] != allowlist_ref:
            raise ValueError("non-canonical TrainingAllowlist")
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", TRAINING_ALLOWLIST_ABI_VERSION)
        object.__setattr__(obj, "allowlist_ref", allowlist_ref)
        object.__setattr__(obj, "source_set_ref", source_set_ref)
        object.__setattr__(obj, "axis_manifest_refs", axis_manifest_refs)
        object.__setattr__(obj, "train_refs", train_refs)
        if obj.as_dict() != dict(row):
            raise ValueError("non-canonical TrainingAllowlist")
        return obj


class IndependentAxisPartitioner:
    """Build one transitive connected-component partition per protected axis."""

    PROTECTED_KEYS: Mapping[str, tuple[str, ...]] = MappingProxyType(
        {
            "general": ("scenario_ref", "trajectory_ref"),
            "lexical": ("surface_family", "normalized_surface", "language"),
            "semantic_target": ("semantic_target", "predicate", "grounded_ref"),
            "topology": ("expression_topology",),
            "dialogue": ("trajectory_ref", "obligation_family"),
            "mutation": ("parent_case_ref", "mutation_family"),
            "realization": ("response_semantic_family",),
        }
    )

    def __init__(
        self,
        *,
        seed: int = 1701,
        ratios: tuple[int, int, int] = (60, 20, 20),
    ) -> None:
        self._seed = exact_int(seed, "seed")
        if (
            type(ratios) is not tuple
            or len(ratios) != 3
            or any(type(value) is not int or value <= 0 for value in ratios)
        ):
            raise TypeError("ratios must be three positive exact integers")
        self._ratios = ratios

    def partition(
        self,
        episodes: Iterable[Any],
        *,
        mutations: Iterable[SemanticMutation] = (),
    ) -> tuple[tuple[PartitionAxisManifest, ...], TrainingAllowlist]:
        rows = tuple(episodes)
        mutations_rows = tuple(mutations)
        if not rows:
            raise ValueError("partitioning requires authentic episodes")
        if any(type(getattr(row, "episode_ref", None)) is not str for row in rows):
            raise TypeError("episodes must expose exact episode_ref")
        if any(type(row) is not SemanticMutation for row in mutations_rows):
            raise TypeError("mutations must contain SemanticMutation")
        refs = tuple(sorted(row.episode_ref for row in rows))
        if len(refs) != len(set(refs)):
            raise ValueError("episode refs must be unique")
        source_set_ref = stable_ref("r4_partition_source_v2", list(refs))
        manifests = tuple(
            self._axis_manifest(axis, rows, mutations_rows, refs, source_set_ref)
            for axis in AXES
        )
        return manifests, TrainingAllowlist.from_manifests(manifests)

    def _axis_manifest(
        self,
        axis: str,
        episodes: tuple[Any, ...],
        mutations: tuple[SemanticMutation, ...],
        source_refs: tuple[str, ...],
        source_set_ref: str,
    ) -> PartitionAxisManifest:
        uf = _UnionFind(source_refs)
        protected_by_member: dict[str, tuple[str, ...]] = {}
        members_by_value: dict[str, list[str]] = {}
        for episode in episodes:
            values = self._protected_values(axis, episode, mutations)
            if not values:
                values = (stable_ref(f"partition_missing_{axis}", episode.episode_ref),)
            protected_by_member[episode.episode_ref] = tuple(sorted(set(values)))
            for value in protected_by_member[episode.episode_ref]:
                members_by_value.setdefault(value, []).append(episode.episode_ref)
        for members in members_by_value.values():
            first = members[0]
            for member in members[1:]:
                uf.union(first, member)
        members_by_root: dict[str, list[str]] = {}
        for ref in source_refs:
            members_by_root.setdefault(uf.find(ref), []).append(ref)
        components: list[PartitionComponent] = []
        for members in members_by_root.values():
            protected = tuple(
                sorted(
                    {
                        value
                        for member in members
                        for value in protected_by_member[member]
                    }
                )
            )
            provisional = stable_ref(
                f"partition_axis_{axis}",
                {"protected": list(protected), "members": sorted(members)},
            )
            components.append(
                PartitionComponent.create(
                    protected_value_refs=protected,
                    member_refs=tuple(sorted(members)),
                    split=_bucket(provisional, self._seed, self._ratios),
                )
            )
        return PartitionAxisManifest.create(
            axis=axis,
            source_set_ref=source_set_ref,
            seed=self._seed,
            protected_keys=self.PROTECTED_KEYS[axis],
            source_refs=source_refs,
            components=tuple(components),
        )

    @staticmethod
    def _filler_refs(expression: SemanticExpression) -> tuple[str, ...]:
        refs: list[str] = []
        for app in expression.applications:
            for binding in (*app.roles, *app.qualifiers):
                filler = binding.filler
                if isinstance(filler, GroundedReference):
                    refs.append(filler.target_ref)
                elif isinstance(filler, LiteralValue):
                    refs.append(stable_ref("literal_family", {"type": filler.value_type, "value": filler.value}))
                elif isinstance(filler, BoundVariable):
                    refs.append("filler:bound_variable")
                elif isinstance(filler, ApplicationFiller):
                    refs.append("filler:proposition")
                elif isinstance(filler, UnresolvedValue):
                    refs.append("filler:unresolved")
        return tuple(refs)

    @staticmethod
    def _topology(expression: SemanticExpression) -> str:
        return stable_ref(
            "expression_topology",
            {
                "applications": [
                    {
                        "operator": row.operator,
                        "roles": [binding.role_ref for binding in row.roles],
                        "qualifiers": [binding.role_ref for binding in row.qualifiers],
                    }
                    for row in expression.applications
                ],
                "roots": len(expression.root_refs),
                "scopes": [row.operator_type for row in expression.scope_operators],
                "links": [
                    [row.link_type, len(row.operand_refs)] for row in expression.expression_links
                ],
                "binders": len(expression.binders),
            },
        )

    def _protected_values(
        self,
        axis: str,
        episode: Any,
        mutations: tuple[SemanticMutation, ...],
    ) -> tuple[str, ...]:
        case = episode.expanded_case
        contract: ExpectedCycleContract = episode.expected_contract
        if axis == "general":
            return (
                stable_ref("scenario_family", case.scenario_ref),
                stable_ref("trajectory_family", case.trajectory_ref),
            )
        if axis == "lexical":
            return (
                next(
                    (ref for ref in case.lineage_refs if ref.startswith("surface_family:")),
                    stable_ref("surface_family", case.scenario_ref),
                ),
                stable_ref(
                    "normalized_surface",
                    {"language": case.language, "surface": " ".join(case.surface.casefold().split())},
                ),
                stable_ref("language_family", case.language),
            )
        if axis == "semantic_target":
            values: list[str] = []
            for expression in contract.expected_expressions:
                values.append(stable_ref("semantic_expression_family", expression.expression_ref))
                values.extend(
                    stable_ref("predicate_family", row.predicate_ref)
                    for row in expression.applications
                )
                values.extend(
                    stable_ref("grounded_family", ref)
                    for ref in self._filler_refs(expression)
                )
            return tuple(values) or (stable_ref("semantic_outcome", contract.outcome_kind.value),)
        if axis == "topology":
            return tuple(self._topology(row) for row in contract.expected_expressions) or (
                stable_ref("topology_no_expression", contract.outcome_kind.value),
            )
        if axis == "dialogue":
            obligation = getattr(
                getattr(episode.observed_cycle, "response_meaning", None),
                "obligation_ref",
                None,
            )
            return (
                stable_ref("trajectory_family", case.trajectory_ref),
                stable_ref("obligation_family", obligation or "none"),
            )
        if axis == "mutation":
            values = [stable_ref("parent_case_family", case.case_ref)]
            values.extend(
                stable_ref("mutation_family", row.dimension)
                for row in mutations
                if row.parent_case_ref == case.case_ref
            )
            return tuple(values)
        response = getattr(episode.observed_cycle, "response_meaning", None)
        return (
            stable_ref(
                "response_semantic_family",
                {
                    "expected": contract.expected_response.as_dict(),
                    "observed_expression": None
                    if response is None
                    else response.response_expression.expression_ref,
                    "discourse": None if response is None else response.discourse_action,
                },
            ),
        )
