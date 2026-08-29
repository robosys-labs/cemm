"""Independent transitive leakage sealing across R4 lineage axes."""
from __future__ import annotations

import hashlib
import json
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

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

from .r4_partition_contracts import (
    MAX_COMPONENTS as GLOBAL_MAX_COMPONENTS,
    MAX_HYPEREDGES,
    MAX_HYPEREDGES_PER_EPISODE,
    MAX_LABELS,
    MAX_LABELS_PER_EPISODE,
    MAX_SOURCE_EPISODES,
    MAX_TOTAL_HYPEREDGE_MEMBERSHIPS,
    MAX_TOTAL_LABEL_MEMBERSHIPS,
    PARTITION_EVIDENCE_ABI_VERSION,
    SPLITS,
    GlobalPartitionComponent,
    LeakageHyperedge,
    PartitionEvidence,
    StratificationLabel,
)
from .r4_partition_config import (
    MAX_SOLVER_KEY_INTS,
    MAX_SOLVER_SECONDS,
    MAX_SOLVER_STATES,
    RARITY_SCALE,
    RATIO_DENOMINATOR,
    DimensionMaximum,
    DimensionMinimum,
    R4PartitionConfig,
)

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

# ---------------------------------------------------------------------------
# Partition Evidence ABI 3 / four-class global partition implementation.
#
# The legacy ABI-2 classes above remain readable until the governed Task 7
# consumer hard-cut.  New source work must use GlobalLeakagePartitioner.
# ---------------------------------------------------------------------------

CURRENT_SPLITS = SPLITS
MAX_REVIEWED_DIMENSIONS = (MAX_SOLVER_KEY_INTS - 5) // len(SPLITS)


class FeasibilityIndeterminate(RuntimeError):
    """Raised when a bounded solver resource limit is reached."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LeakageComponent:
    component_ref: str
    member_refs: tuple[str, ...]
    hyperedge_refs: tuple[str, ...]


@dataclass(frozen=True)
class ComponentAssignment:
    component_ref: str
    split: str

    def as_dict(self) -> dict[str, str]:
        return {"component_ref": self.component_ref, "split": self.split}


@dataclass(frozen=True)
class DimensionSupport:
    dimension_ref: str
    source_support: int
    feasible_component_support: int

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension_ref": self.dimension_ref,
            "source_support": self.source_support,
            "feasible_component_support": self.feasible_component_support,
        }


@dataclass(frozen=True)
class SolverStats:
    state_count: int
    key_width_ints: int
    estimated_memory_bytes: int
    wall_seconds_millis: int

    def as_dict(self) -> dict[str, int]:
        return {
            "state_count": self.state_count,
            "key_width_ints": self.key_width_ints,
            "estimated_memory_bytes": self.estimated_memory_bytes,
            "wall_seconds_millis": self.wall_seconds_millis,
        }


@dataclass(frozen=True)
class PartitionFeasibility:
    source_count: int
    component_count: int
    largest_component_count: int
    component_size_histogram: tuple[tuple[int, int], ...]
    dimension_support: tuple[DimensionSupport, ...]
    four_nonempty_possible: bool
    infeasibility_reasons: tuple[str, ...]
    candidate_minima: tuple[DimensionMinimum, ...]
    candidate_maxima: tuple[DimensionMaximum, ...]
    assignment_witness: tuple[ComponentAssignment, ...]
    witness_objective_ref: str
    solver_stats: SolverStats


@dataclass(frozen=True)
class GlobalPartitionGraph:
    source_set_ref: str
    graph_ref: str
    hyperedges: tuple[LeakageHyperedge, ...]
    labels: tuple[StratificationLabel, ...]
    components: tuple[LeakageComponent, ...]


@dataclass(frozen=True)
class AssignmentResult:
    evidence: PartitionEvidence
    assignments: tuple[ComponentAssignment, ...]
    objective: tuple[int, int, int, str]
    solver_stats: SolverStats
    sparse_counter_updates: int


def normalized_surface_key(surface: object, language: object) -> str:
    if type(surface) is not str or type(language) is not str:
        raise TypeError("surface and language must be exact strings")
    normalized = " ".join(
        unicodedata.normalize("NFKC", surface).casefold().split()
    )
    if not normalized or not language:
        raise ValueError("surface and language must be nonempty")
    return stable_ref(
        "normalized_surface_v3",
        {"language": language, "surface": normalized},
    )


def _raw_episode(episode: object) -> dict[str, Any]:
    if type(episode) is dict:
        value = episode
    else:
        encoder = getattr(episode, "as_dict", None)
        if not callable(encoder):
            raise TypeError("episodes must be exact mappings or expose as_dict()")
        value = encoder()
    if type(value) is not dict:
        raise TypeError("episode serialization must be an exact object")
    episode_ref = value.get("episode_ref")
    if type(episode_ref) is not str or ":" not in episode_ref:
        raise ValueError("episode_ref must be an exact content reference")
    return value


def _raw_mutation(mutation: object) -> dict[str, Any]:
    if type(mutation) is dict:
        value = mutation
    else:
        encoder = getattr(mutation, "as_dict", None)
        if not callable(encoder):
            raise TypeError("mutations must be exact mappings or expose as_dict()")
        value = encoder()
    if type(value) is not dict:
        raise TypeError("mutation serialization must be an exact object")
    return value


def _lineage_ref(rows: object, prefix: str) -> str | None:
    if type(rows) is not list:
        return None
    matches = [row for row in rows if type(row) is str and row.startswith(prefix)]
    if len(matches) > 1:
        raise ValueError(f"duplicate {prefix} lineage")
    return matches[0] if matches else None


def _grounded_targets(expression: Mapping[str, Any]) -> tuple[str, ...]:
    refs: set[str] = set()
    applications = expression.get("applications", [])
    if type(applications) is not list:
        raise TypeError("expected expression applications must be a list")
    for app in applications:
        if type(app) is not dict:
            raise TypeError("application row must be an object")
        for field in ("roles", "qualifiers"):
            bindings = app.get(field, [])
            if type(bindings) is not list:
                raise TypeError(f"{field} must be a list")
            for binding in bindings:
                if type(binding) is not dict:
                    raise TypeError("binding row must be an object")
                filler = binding.get("filler")
                if type(filler) is not dict:
                    continue
                if filler.get("kind") == "grounded":
                    target = filler.get("target_ref")
                    if type(target) is str and ":" in target:
                        refs.add(target)
    return tuple(sorted(refs))


def _topology_key(expression: Mapping[str, Any]) -> str:
    applications = expression.get("applications", [])
    if type(applications) is not list:
        raise TypeError("expected expression applications must be a list")
    material: list[dict[str, object]] = []
    for app in applications:
        if type(app) is not dict:
            raise TypeError("application row must be an object")
        row: dict[str, object] = {
            "operator": app.get("operator"),
            "predicate_ref": app.get("predicate_ref"),
        }
        for field in ("roles", "qualifiers"):
            bindings = app.get(field, [])
            if type(bindings) is not list:
                raise TypeError(f"{field} must be a list")
            row[field] = [
                binding.get("role_ref")
                for binding in bindings
                if type(binding) is dict
            ]
        material.append(row)
    return stable_ref(
        "r4_expression_topology_v3",
        {
            "applications": material,
            "root_count": len(expression.get("root_refs", [])),
            "scope_operators": [
                row.get("operator_type")
                for row in expression.get("scope_operators", [])
                if type(row) is dict
            ],
            "expression_links": [
                [row.get("link_type"), len(row.get("operand_refs", []))]
                for row in expression.get("expression_links", [])
                if type(row) is dict
            ],
            "binder_count": len(expression.get("binders", [])),
        },
    )


def _topology_category(expression: Mapping[str, Any]) -> str:
    applications = expression.get("applications", [])
    operators = tuple(
        app.get("operator")
        for app in applications
        if type(app) is dict and type(app.get("operator")) is str
    )
    return stable_ref(
        "r4_topology_category_v1",
        {
            "application_count": len(applications),
            "operators": list(operators),
            "root_count": len(expression.get("root_refs", [])),
            "scope_count": len(expression.get("scope_operators", [])),
            "link_count": len(expression.get("expression_links", [])),
        },
    )


def _response_semantic_key(episode: Mapping[str, Any]) -> str | None:
    observed = episode.get("observed_cycle")
    if type(observed) is not dict:
        return None
    response = observed.get("response_meaning")
    if type(response) is not dict:
        return None
    material = {
        name: response.get(name)
        for name in (
            "cycle_status",
            "discourse_action",
            "epistemic_status_ref",
            "modality_ref",
            "polarity_ref",
        )
    }
    if not any(value is not None for value in material.values()):
        return None
    return stable_ref("r4_response_semantic_family_v1", material)


def _response_expression_ref(episode: Mapping[str, Any]) -> str | None:
    observed = episode.get("observed_cycle")
    if type(observed) is not dict:
        return None
    response = observed.get("response_meaning")
    if type(response) is not dict:
        return None
    expression = response.get("response_expression")
    if type(expression) is not dict:
        return None
    ref = expression.get("expression_ref")
    return ref if type(ref) is str and ":" in ref else None


def _obligation_refs(episode: Mapping[str, Any]) -> tuple[str, ...]:
    observed = episode.get("observed_cycle")
    if type(observed) is not dict:
        return ()
    response = observed.get("response_meaning")
    if type(response) is not dict:
        return ()
    refs: set[str] = set()
    for name in ("obligation_ref",):
        value = response.get(name)
        if type(value) is str and ":" in value:
            refs.add(value)
    obligation = response.get("obligation")
    if type(obligation) is dict:
        for name in (
            "obligation_ref",
            "plan_ref",
            "expected_answer_contract_ref",
            "completion_receipt_ref",
        ):
            value = obligation.get(name)
            if type(value) is str and ":" in value:
                refs.add(value)
    plan = response.get("learning_plan")
    if type(plan) is dict:
        for name in ("obligation_ref", "plan_ref"):
            value = plan.get(name)
            if type(value) is str and ":" in value:
                refs.add(value)
    return tuple(sorted(refs))


def _category(ref: str) -> str:
    return ref.split(":", 1)[0]


class GlobalLeakagePartitioner:
    """Build one deterministic global leakage graph and four-class assignment."""

    def build_graph(
        self,
        episodes: Iterable[object],
        *,
        mutations: Iterable[object] = (),
    ) -> GlobalPartitionGraph:
        rows = tuple(_raw_episode(row) for row in episodes)
        mutation_rows = tuple(_raw_mutation(row) for row in mutations)
        if not rows:
            raise ValueError("partition graph requires authentic episodes")
        if len(rows) > MAX_SOURCE_EPISODES:
            raise ValueError("partition source universe exceeds hard bound")
        refs = tuple(sorted(row["episode_ref"] for row in rows))
        if len(refs) != len(set(refs)):
            raise ValueError("episode refs must be unique")
        source_set_ref = stable_ref("r4_partition_source_v3", list(refs))
        by_ref = {row["episode_ref"]: row for row in rows}
        mutations_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for mutation in mutation_rows:
            parent = mutation.get("parent_case_ref")
            if type(parent) is str:
                mutations_by_parent[parent].append(mutation)

        key_members: dict[tuple[str, str, str], set[str]] = defaultdict(set)
        label_members: dict[str, set[str]] = defaultdict(set)

        def leakage(axis: str, namespace: str, key_ref: object, member: str) -> None:
            if key_ref is None:
                return
            if type(key_ref) is not str or ":" not in key_ref:
                raise ValueError(f"{axis}/{namespace} leakage key is not an exact ref")
            key_members[(axis, namespace, key_ref)].add(member)

        def label(namespace: str, member: str) -> None:
            if not namespace or len(namespace) > 128:
                raise ValueError("stratification namespace violates bounds")
            label_members[namespace].add(member)

        for episode_ref in refs:
            episode = by_ref[episode_ref]
            case = episode.get("expanded_case")
            contract = episode.get("expected_contract")
            if type(case) is not dict or type(contract) is not dict:
                raise TypeError("authentic episode lacks exact case/contract")

            # General exact reviewed-source identities.  Singleton keys are
            # intentionally retained in extraction material but serialize only
            # when they actually form a leakage hyperedge.
            for namespace, key in (
                ("scenario", case.get("scenario_ref")),
                ("case", case.get("case_ref")),
                ("trajectory", case.get("trajectory_ref")),
            ):
                leakage("general", namespace, key, episode_ref)
            for ref in episode.get("generator_lineage_refs", []):
                if type(ref) is str and ":" in ref:
                    leakage("general", "generator_lineage", ref, episode_ref)

            # Lexical exact identities. Language is only a qualifier on the
            # normalized surface; it never unions the corpus by itself.
            surface_family = _lineage_ref(case.get("lineage_refs"), "surface_family:")
            leakage("lexical", "surface_family", surface_family, episode_ref)
            surface = case.get("surface")
            language = case.get("language")
            if type(surface) is str and type(language) is str:
                leakage(
                    "lexical",
                    "normalized_surface",
                    normalized_surface_key(surface, language),
                    episode_ref,
                )
                label(f"coverage:language:{language}", episode_ref)
            if surface_family is not None:
                label(f"coverage:surface:{surface_family}", episode_ref)
            environment_family = _lineage_ref(
                case.get("lineage_refs"), "environment_family:"
            )
            if environment_family is not None:
                label(f"coverage:environment:{environment_family}", episode_ref)

            expressions = contract.get("expected_expressions", [])
            if type(expressions) is not list:
                raise TypeError("expected_expressions must be a list")
            if expressions:
                for expression in expressions:
                    if type(expression) is not dict:
                        raise TypeError("expected expression must be an object")
                    leakage(
                        "semantic_target",
                        "semantic_expression",
                        expression.get("expression_ref"),
                        episode_ref,
                    )
                    applications = expression.get("applications", [])
                    if type(applications) is not list:
                        raise TypeError("expression applications must be a list")
                    for app in applications:
                        if type(app) is not dict:
                            raise TypeError("expression application must be an object")
                        predicate = app.get("predicate_ref")
                        leakage(
                            "semantic_target", "predicate", predicate, episode_ref
                        )
                        operator = app.get("operator")
                        if type(operator) is str:
                            label(f"coverage:operator:{operator}", episode_ref)
                    for target in _grounded_targets(expression):
                        leakage(
                            "semantic_target", "grounded_target", target, episode_ref
                        )
                        label(f"coverage:target_category:{_category(target)}", episode_ref)
                    topology = _topology_key(expression)
                    leakage("topology", "expression_topology", topology, episode_ref)
                    label(
                        f"coverage:topology:{_topology_category(expression)}",
                        episode_ref,
                    )
            else:
                label("coverage:topology:none", episode_ref)

            # Dialogue exact identities: trajectory plus non-null obligation
            # descendants only.  No sentinel obligation is admitted.
            leakage("dialogue", "trajectory", case.get("trajectory_ref"), episode_ref)
            obligations = _obligation_refs(episode)
            for obligation_ref in obligations:
                leakage("dialogue", "obligation_lineage", obligation_ref, episode_ref)
            label(
                "coverage:dialogue_obligation:present"
                if obligations
                else "coverage:dialogue_obligation:none",
                episode_ref,
            )

            # Mutation identities are qualified by exact parent source so the
            # corpus-wide mutation dimension remains a label, not a union key.
            case_ref = case.get("case_ref")
            if type(case_ref) is str:
                leakage("mutation", "parent_case", case_ref, episode_ref)
                for mutation in mutations_by_parent.get(case_ref, ()):
                    mutation_ref = mutation.get("mutation_ref")
                    if type(mutation_ref) is str and ":" in mutation_ref:
                        leakage(
                            "mutation", "mutation_child", mutation_ref, episode_ref
                        )
                    family = _lineage_ref(
                        mutation.get("lineage_refs"), "mutation_family:"
                    )
                    if family is not None:
                        leakage(
                            "mutation",
                            "reviewed_mutation_family",
                            stable_ref(
                                "r4_reviewed_mutation_family_v1",
                                {"scenario_ref": case.get("scenario_ref"), "family_ref": family},
                            ),
                            episode_ref,
                        )
                    dimension = mutation.get("dimension")
                    if type(dimension) is str:
                        label(f"coverage:mutation:{dimension}", episode_ref)

            response_expression = _response_expression_ref(episode)
            leakage(
                "realization",
                "response_expression",
                response_expression,
                episode_ref,
            )
            response_semantics = _response_semantic_key(episode)
            leakage(
                "realization",
                "response_semantics",
                response_semantics,
                episode_ref,
            )
            expected_response = contract.get("expected_response")
            if type(expected_response) is dict:
                discourse = expected_response.get("discourse_action")
                if type(discourse) is str:
                    label(f"coverage:response:{discourse}", episode_ref)

            for field, prefix in (
                ("expected_mode", "mode"),
                ("expected_owner", "owner"),
                ("expression_relation", "expression_relation"),
            ):
                value = contract.get(field)
                if type(value) is str:
                    label(f"coverage:{prefix}:{value}", episode_ref)
            decision = contract.get("expected_decision")
            if type(decision) is dict:
                for field, prefix in (("action", "decision_action"), ("status", "decision_status")):
                    value = decision.get(field)
                    if type(value) is str:
                        label(f"coverage:{prefix}:{value}", episode_ref)
            effect = contract.get("expected_effect")
            if type(effect) is dict:
                for field, prefix in (("kind", "effect_kind"), ("status_or_reason", "effect_status")):
                    value = effect.get(field)
                    if type(value) is str:
                        label(f"coverage:{prefix}:{value}", episode_ref)
            assertions = contract.get("normalized_assertions", [])
            if type(assertions) is list:
                for assertion in assertions:
                    if type(assertion) is dict and type(assertion.get("kind")) is str:
                        label(f"coverage:assertion_kind:{assertion['kind']}", episode_ref)

            outcome = contract.get("outcome_kind")
            if type(outcome) is str:
                label(f"coverage:outcome:{outcome}", episode_ref)
            gap = contract.get("expected_gap")
            if type(gap) is dict:
                gap_kind = gap.get("kind") or gap.get("gap_kind")
                if type(gap_kind) is str:
                    label(f"coverage:gap:{gap_kind}", episode_ref)
            elif gap is None:
                label("coverage:gap:none", episode_ref)

        hyperedges: list[LeakageHyperedge] = []
        per_episode_edges: Counter[str] = Counter()
        total_edge_memberships = 0
        for (axis, namespace, key_ref), members in sorted(key_members.items()):
            ordered = tuple(sorted(members))
            if len(ordered) < 2:
                continue
            edge = LeakageHyperedge.create(
                axis=axis,
                key_namespace=namespace,
                key_ref=key_ref,
                member_refs=ordered,
            )
            hyperedges.append(edge)
            total_edge_memberships += len(ordered)
            per_episode_edges.update(ordered)
        hyperedges.sort(key=lambda row: row.hyperedge_ref)
        if len(hyperedges) > MAX_HYPEREDGES:
            raise ValueError("partition graph exceeds hyperedge bound")
        if total_edge_memberships > MAX_TOTAL_HYPEREDGE_MEMBERSHIPS:
            raise ValueError("partition graph exceeds hyperedge membership bound")
        if any(value > MAX_HYPEREDGES_PER_EPISODE for value in per_episode_edges.values()):
            raise ValueError("episode exceeds hyperedge fanout bound")

        labels: list[StratificationLabel] = []
        per_episode_labels: Counter[str] = Counter()
        total_label_memberships = 0
        for namespace, members in sorted(label_members.items()):
            ordered = tuple(sorted(members))
            row = StratificationLabel.create(namespace=namespace, member_refs=ordered)
            labels.append(row)
            total_label_memberships += len(ordered)
            per_episode_labels.update(ordered)
        labels.sort(key=lambda row: row.label_ref)
        if len(labels) > MAX_LABELS:
            raise ValueError("partition graph exceeds label bound")
        if total_label_memberships > MAX_TOTAL_LABEL_MEMBERSHIPS:
            raise ValueError("partition graph exceeds label membership bound")
        if any(value > MAX_LABELS_PER_EPISODE for value in per_episode_labels.values()):
            raise ValueError("episode exceeds label fanout bound")

        uf = _UnionFind(refs)
        for edge in hyperedges:
            first = edge.member_refs[0]
            for member in edge.member_refs[1:]:
                uf.union(first, member)
        members_by_root: dict[str, list[str]] = defaultdict(list)
        for ref in refs:
            members_by_root[uf.find(ref)].append(ref)
        edge_owner: dict[str, str] = {}
        root_by_member = {ref: uf.find(ref) for ref in refs}
        for edge in hyperedges:
            root = root_by_member[edge.member_refs[0]]
            edge_owner[edge.hyperedge_ref] = root
        components: list[LeakageComponent] = []
        for root, members in members_by_root.items():
            ordered_members = tuple(sorted(members))
            edge_refs = tuple(
                sorted(
                    ref for ref, owner in edge_owner.items() if owner == root
                )
            )
            material = {
                "source_set_ref": source_set_ref,
                "partition_abi_version": PARTITION_EVIDENCE_ABI_VERSION,
                "member_refs": list(ordered_members),
                "hyperedge_refs": list(edge_refs),
            }
            components.append(
                LeakageComponent(
                    component_ref=stable_ref(
                        "r4_global_partition_component_v3", material
                    ),
                    member_refs=ordered_members,
                    hyperedge_refs=edge_refs,
                )
            )
        components.sort(key=lambda row: row.component_ref)
        if len(components) > GLOBAL_MAX_COMPONENTS:
            raise ValueError("partition graph exceeds component bound")

        graph_ref = stable_ref(
            "r4_partition_graph_v3",
            {
                "source_set_ref": source_set_ref,
                "hyperedges": [row.as_dict() for row in hyperedges],
                "labels": [row.as_dict() for row in labels],
                "components": [
                    {
                        "component_ref": row.component_ref,
                        "member_refs": list(row.member_refs),
                        "hyperedge_refs": list(row.hyperedge_refs),
                    }
                    for row in components
                ],
            },
        )
        return GlobalPartitionGraph(
            source_set_ref=source_set_ref,
            graph_ref=graph_ref,
            hyperedges=tuple(hyperedges),
            labels=tuple(labels),
            components=tuple(components),
        )

    @staticmethod
    def dimension_support(graph: GlobalPartitionGraph) -> tuple[DimensionSupport, ...]:
        component_by_member = {
            member: component.component_ref
            for component in graph.components
            for member in component.member_refs
        }
        rows = []
        for label in graph.labels:
            component_refs = {
                component_by_member[member] for member in label.member_refs
            }
            rows.append(
                DimensionSupport(
                    dimension_ref=label.label_ref,
                    source_support=len(label.member_refs),
                    feasible_component_support=len(component_refs),
                )
            )
        return tuple(sorted(rows, key=lambda row: row.dimension_ref))

    def analyze_feasibility(
        self,
        episodes: Iterable[object],
        *,
        mutations: Iterable[object] = (),
        max_dimensions: int = 22,
    ) -> tuple[GlobalPartitionGraph, PartitionFeasibility]:
        graph = self.build_graph(episodes, mutations=mutations)
        support = self.dimension_support(graph)
        eligible = [
            row
            for row in support
            if row.source_support >= len(SPLITS)
            and row.feasible_component_support >= len(SPLITS)
        ]
        eligible.sort(
            key=lambda row: (
                -row.source_support,
                -row.feasible_component_support,
                row.dimension_ref,
            )
        )
        max_dimensions = min(
            exact_int(max_dimensions, "max_dimensions", minimum=1),
            MAX_REVIEWED_DIMENSIONS,
        )
        selected = eligible[:max_dimensions]
        labels_by_ref = {row.label_ref: row for row in graph.labels}

        reasons: list[str] = []
        witness: tuple[ComponentAssignment, ...] = ()
        stats = SolverStats(0, 5, 0, 0)
        # If the top candidate set is jointly infeasible, deterministically trim
        # the least-supported tail until one exact positive set remains.
        while selected:
            minima = tuple(
                DimensionMinimum.create(
                    dimension_ref=row.dimension_ref,
                    split=split,
                    minimum=1,
                )
                for row in sorted(selected, key=lambda item: item.dimension_ref)
                for split in SPLITS
            )
            maxima = tuple(
                DimensionMaximum.create(
                    dimension_ref=row.dimension_ref,
                    split=split,
                    maximum=row.source_support,
                )
                for row in sorted(selected, key=lambda item: item.dimension_ref)
                for split in SPLITS
            )
            try:
                oracle = _CompletionOracle(
                    components=graph.components,
                    labels_by_ref=labels_by_ref,
                    minima=minima,
                    maxima=maxima,
                    max_states=MAX_SOLVER_STATES,
                    max_seconds=MAX_SOLVER_SECONDS,
                )
                completion = oracle.find_completion(0, (0, 0, 0, 0), minima)
            except FeasibilityIndeterminate:
                raise
            stats = oracle.stats()
            if completion is not None:
                witness = tuple(
                    ComponentAssignment(component.component_ref, SPLITS[split_index])
                    for component, split_index in zip(
                        oracle.components, completion, strict=True
                    )
                )
                break
            selected = selected[:-1]
        if not witness:
            reasons.append("joint_four_class_dimension_coverage_infeasible")
            minima = ()
            maxima = ()
        else:
            selected_refs = {row.dimension_ref for row in selected}
            minima = tuple(
                row
                for row in minima
                if row.dimension_ref in selected_refs
            )
            maxima = tuple(
                row
                for row in maxima
                if row.dimension_ref in selected_refs
            )

        histogram = Counter(len(row.member_refs) for row in graph.components)
        objective_ref = stable_ref(
            "r4_partition_witness_objective_v1",
            [row.as_dict() for row in witness],
        )
        return graph, PartitionFeasibility(
            source_count=sum(len(row.member_refs) for row in graph.components),
            component_count=len(graph.components),
            largest_component_count=max(len(row.member_refs) for row in graph.components),
            component_size_histogram=tuple(sorted(histogram.items())),
            dimension_support=support,
            four_nonempty_possible=bool(witness),
            infeasibility_reasons=tuple(reasons),
            candidate_minima=minima,
            candidate_maxima=maxima,
            assignment_witness=witness,
            witness_objective_ref=objective_ref,
            solver_stats=stats,
        )

    def assign(
        self,
        episodes: Iterable[object],
        *,
        config: R4PartitionConfig,
        mutations: Iterable[object] = (),
    ) -> AssignmentResult:
        if type(config) is not R4PartitionConfig:
            raise TypeError("config must be an exact R4PartitionConfig")
        graph = self.build_graph(episodes, mutations=mutations)
        labels_by_ref = {row.label_ref: row for row in graph.labels}
        configured = tuple(sorted({row.dimension_ref for row in config.minima}))
        if any(ref not in labels_by_ref for ref in configured):
            raise ValueError("partition config names an unknown stratification label")

        label_members = {
            ref: frozenset(labels_by_ref[ref].member_refs) for ref in configured
        }
        global_label_counts = {ref: len(label_members[ref]) for ref in configured}
        component_label_counts: dict[str, dict[str, int]] = {}
        for component in graph.components:
            members = frozenset(component.member_refs)
            counts = {
                ref: len(members.intersection(label_members[ref]))
                for ref in configured
            }
            component_label_counts[component.component_ref] = {
                ref: count for ref, count in counts.items() if count
            }

        def rare_score(component: LeakageComponent) -> int:
            return sum(
                RARITY_SCALE // global_label_counts[ref]
                for ref in component_label_counts[component.component_ref]
            )

        ordered = tuple(
            sorted(
                graph.components,
                key=lambda row: (
                    -len(row.member_refs),
                    -rare_score(row),
                    row.component_ref,
                ),
            )
        )
        oracle = _CompletionOracle(
            components=ordered,
            labels_by_ref=labels_by_ref,
            minima=config.minima,
            maxima=config.maxima,
            max_states=config.bounds.max_solver_states,
            max_seconds=config.bounds.max_solver_seconds,
        )
        class_counts = [0, 0, 0, 0]
        observed = {
            (split, ref): 0 for split in SPLITS for ref in configured
        }
        assignment_by_component: dict[str, str] = {}
        sparse_updates = 0
        current_minima = tuple(config.minima)

        for index, component in enumerate(ordered):
            candidates: list[tuple[tuple[int, int, int, str], int]] = []
            counts = component_label_counts[component.component_ref]
            for split_index, split in enumerate(SPLITS):
                next_counts = list(class_counts)
                next_counts[split_index] += len(component.member_refs)
                next_minima = _remaining_minima_after(
                    current_minima,
                    split=split,
                    contribution=counts,
                )
                completion = oracle.find_completion(
                    index + 1, tuple(next_counts), next_minima
                )
                if completion is None:
                    continue
                next_observed = dict(observed)
                for ref, contribution in counts.items():
                    next_observed[(split, ref)] += contribution
                objective = _full_objective(
                    source_count=sum(len(row.member_refs) for row in ordered),
                    class_counts=tuple(next_counts),
                    observed=next_observed,
                    config=config,
                    global_label_counts=global_label_counts,
                    tie_break_ref=stable_ref(
                        "r4_partition_tie",
                        {
                            "component": component.component_ref,
                            "split": split,
                            "seed": config.seed,
                        },
                    ),
                )
                candidates.append((objective, split_index))
            if not candidates:
                raise ValueError(
                    f"no feasible placement remains for {component.component_ref}"
                )
            _, chosen_index = min(candidates, key=lambda row: row[0])
            chosen_split = SPLITS[chosen_index]
            class_counts[chosen_index] += len(component.member_refs)
            assignment_by_component[component.component_ref] = chosen_split
            counts = component_label_counts[component.component_ref]
            for ref, contribution in counts.items():
                observed[(chosen_split, ref)] += contribution
                sparse_updates += 1
            current_minima = _remaining_minima_after(
                current_minima, split=chosen_split, contribution=counts
            )

        if any(value <= 0 for value in class_counts):
            raise ValueError("allocator produced an empty split")
        if any(row.minimum > 0 for row in current_minima):
            raise ValueError("allocator did not satisfy configured minima")
        maxima = {(row.split, row.dimension_ref): row.maximum for row in config.maxima}
        if any(observed[key] > maxima[key] for key in maxima):
            raise ValueError("allocator exceeded a configured maximum")

        contract_components = tuple(
            sorted(
                (
                    GlobalPartitionComponent.create(
                        source_set_ref=graph.source_set_ref,
                        member_refs=component.member_refs,
                        hyperedge_refs=component.hyperedge_refs,
                        split=assignment_by_component[component.component_ref],
                    )
                    for component in graph.components
                ),
                key=lambda row: row.component_ref,
            )
        )
        evidence = PartitionEvidence.create(
            source_set_ref=graph.source_set_ref,
            config_ref=config.config_ref,
            hyperedges=graph.hyperedges,
            labels=graph.labels,
            components=contract_components,
        )
        final_tie = stable_ref(
            "r4_partition_assignment_tie_v1",
            sorted(assignment_by_component.items()),
        )
        final_objective = _full_objective(
            source_count=sum(class_counts),
            class_counts=tuple(class_counts),
            observed=observed,
            config=config,
            global_label_counts=global_label_counts,
            tie_break_ref=final_tie,
        )
        assignments = tuple(
            ComponentAssignment(component.component_ref, assignment_by_component[component.component_ref])
            for component in sorted(graph.components, key=lambda row: row.component_ref)
        )
        return AssignmentResult(
            evidence=evidence,
            assignments=assignments,
            objective=final_objective,
            solver_stats=oracle.stats(),
            sparse_counter_updates=sparse_updates,
        )


def _remaining_minima_after(
    minima: tuple[DimensionMinimum, ...],
    *,
    split: str,
    contribution: Mapping[str, int],
) -> tuple[DimensionMinimum, ...]:
    rows = []
    for row in minima:
        remaining = row.minimum
        if row.split == split:
            remaining = max(0, remaining - contribution.get(row.dimension_ref, 0))
        # Internal solver state admits zero; materialize an exact stand-in row.
        obj = object.__new__(DimensionMinimum)
        object.__setattr__(obj, "dimension_ref", row.dimension_ref)
        object.__setattr__(obj, "split", row.split)
        object.__setattr__(obj, "minimum", remaining)
        rows.append(obj)
    return tuple(rows)


def _full_objective(
    *,
    source_count: int,
    class_counts: tuple[int, int, int, int],
    observed: Mapping[tuple[str, str], int],
    config: R4PartitionConfig,
    global_label_counts: Mapping[str, int],
    tie_break_ref: str,
) -> tuple[int, int, int, str]:
    weights = {row.split: row.weight for row in config.target_weights}
    size_deviation = sum(
        abs(RATIO_DENOMINATOR * class_counts[index] - source_count * weights[split])
        for index, split in enumerate(SPLITS)
    )
    configured = tuple(sorted(global_label_counts))
    label_deviation = sum(
        abs(
            RATIO_DENOMINATOR * observed.get((split, ref), 0)
            - global_label_counts[ref] * weights[split]
        )
        for split in SPLITS
        for ref in configured
    )
    minima = {(row.split, row.dimension_ref): row.minimum for row in config.minima}
    maxima = {(row.split, row.dimension_ref): row.maximum for row in config.maxima}
    bound_violation = sum(
        max(0, minima[(split, ref)] - observed.get((split, ref), 0))
        + max(0, observed.get((split, ref), 0) - maxima[(split, ref)])
        for split in SPLITS
        for ref in configured
    )
    return size_deviation, label_deviation, bound_violation, tie_break_ref


class _CompletionOracle:
    """Bounded exact completion oracle shared by feasibility and allocation."""

    def __init__(
        self,
        *,
        components: Sequence[LeakageComponent],
        labels_by_ref: Mapping[str, StratificationLabel],
        minima: tuple[DimensionMinimum, ...],
        maxima: tuple[DimensionMaximum, ...],
        max_states: int,
        max_seconds: int,
    ) -> None:
        self.components = tuple(components)
        self.dimensions = tuple(sorted({row.dimension_ref for row in minima}))
        if len(self.dimensions) > MAX_REVIEWED_DIMENSIONS:
            raise ValueError("configured dimensions exceed solver key width")
        if {row.dimension_ref for row in maxima} != set(self.dimensions):
            raise ValueError("solver minima/maxima dimension mismatch")
        self._dim_index = {ref: index for index, ref in enumerate(self.dimensions)}
        label_members = {
            ref: frozenset(labels_by_ref[ref].member_refs) for ref in self.dimensions
        }
        self._contribution: tuple[tuple[int, ...], ...] = tuple(
            tuple(
                len(frozenset(component.member_refs).intersection(label_members[ref]))
                for ref in self.dimensions
            )
            for component in self.components
        )
        self._suffix_capacity: list[tuple[int, ...]] = [
            (0,) * len(self.dimensions) for _ in range(len(self.components) + 1)
        ]
        running = [0] * len(self.dimensions)
        for index in range(len(self.components) - 1, -1, -1):
            contribution = self._contribution[index]
            for dim, value in enumerate(contribution):
                running[dim] += value
            self._suffix_capacity[index] = tuple(running)
        self._memo: dict[tuple[int, ...], tuple[int, ...] | None] = {}
        self._max_states = exact_int(max_states, "max_states", minimum=1)
        self._max_seconds = exact_int(max_seconds, "max_seconds", minimum=1)
        self._start = time.monotonic()
        self._states = 0
        self._key_width = 1 + len(SPLITS) + len(SPLITS) * len(self.dimensions)
        if self._key_width > MAX_SOLVER_KEY_INTS:
            raise ValueError("solver memo key exceeds reviewed width")

    def _needs(self, minima: tuple[DimensionMinimum, ...]) -> tuple[int, ...]:
        by_key = {(row.split, row.dimension_ref): row.minimum for row in minima}
        return tuple(
            by_key.get((split, ref), 0)
            for split in SPLITS
            for ref in self.dimensions
        )

    def find_completion(
        self,
        index: int,
        class_counts: tuple[int, int, int, int],
        minima: tuple[DimensionMinimum, ...],
    ) -> tuple[int, ...] | None:
        needs = self._needs(minima)
        return self._search(index, class_counts, needs)

    def _search(
        self,
        index: int,
        class_counts: tuple[int, int, int, int],
        needs: tuple[int, ...],
    ) -> tuple[int, ...] | None:
        key = (index, *class_counts, *needs)
        cached = self._memo.get(key, ...)
        if cached is not ...:
            return cached
        self._states += 1
        if self._states > self._max_states:
            raise FeasibilityIndeterminate(reason="resource_bound:solver_states")
        elapsed = time.monotonic() - self._start
        if elapsed > self._max_seconds:
            raise FeasibilityIndeterminate(reason="resource_bound:solver_seconds")
        estimated = self._states * self._key_width * 32
        if estimated > 192 * 1024 * 1024:
            raise FeasibilityIndeterminate(reason="resource_bound:solver_memory")

        if index == len(self.components):
            result = () if all(class_counts) and not any(needs) else None
            self._memo[key] = result
            return result

        remaining_components = len(self.components) - index
        if sum(count == 0 for count in class_counts) > remaining_components:
            self._memo[key] = None
            return None
        cap = self._suffix_capacity[index]
        width = len(self.dimensions)
        for dim in range(width):
            aggregate_need = sum(needs[split * width + dim] for split in range(4))
            if aggregate_need > cap[dim]:
                self._memo[key] = None
                return None
            for split in range(4):
                if needs[split * width + dim] > cap[dim]:
                    self._memo[key] = None
                    return None

        component = self.components[index]
        contribution = self._contribution[index]
        # Symmetric split states are equivalent for feasibility.  Collapsing
        # them prevents the four-way class permutation from multiplying memo
        # states without changing the existence of a completion.
        split_rows: list[tuple[int, int, int]] = []
        seen_states: set[tuple[int, tuple[int, ...]]] = set()
        for split_index in range(4):
            base = split_index * width
            segment = needs[base : base + width]
            state_shape = (class_counts[split_index], segment)
            if state_shape in seen_states:
                continue
            seen_states.add(state_shape)
            coverage = sum(
                min(segment[dim], value)
                for dim, value in enumerate(contribution)
                if value
            )
            # Prefer empty classes and then placements that retire the most
            # remaining exact minima; split index is the final stable tie.
            split_rows.append((0 if class_counts[split_index] == 0 else 1, -coverage, split_index))
        for _, __, split_index in sorted(split_rows):
            next_counts = list(class_counts)
            next_counts[split_index] += len(component.member_refs)
            next_needs = list(needs)
            base = split_index * width
            for dim, value in enumerate(contribution):
                if value:
                    pos = base + dim
                    next_needs[pos] = max(0, next_needs[pos] - value)
            tail = self._search(index + 1, tuple(next_counts), tuple(next_needs))
            if tail is not None:
                result = (split_index, *tail)
                self._memo[key] = result
                return result
        self._memo[key] = None
        return None

    def stats(self) -> SolverStats:
        return SolverStats(
            state_count=self._states,
            key_width_ints=self._key_width,
            estimated_memory_bytes=self._states * self._key_width * 32,
            wall_seconds_millis=int((time.monotonic() - self._start) * 1000),
        )
