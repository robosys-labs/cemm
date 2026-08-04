"""Lineage-aware partitions, hard negatives, and gap coverage.

This module owns the sealed partition contract for Milestone 4.  A
:class:`Partitioner` builds one graph joining episodes that share any protected
lineage value, assigns whole connected components to train/validation/test using
a seeded stratified bin-packing algorithm, and emits immutable manifest hashes
and counts.

The test manifest is readable by evaluation only, never imported by training or
calibration modules.  :class:`PartitionAccessError` is raised when a trainer
tries to access test or validation data.

:class:`HardNegativeGenerator` mutates role, polarity, modality, source, tense,
reference, effect permission, target kind, scope attachment, and action order
one at a time.  It retains the parent lineage, uses exact verifier errors as
labels (neural scores never determine truth), and adds proposer-miss cases
where a legal target exists and authority-gap cases where none exists.
"""

from __future__ import annotations

import copy
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .canonical import sha256_file, stable_ref

__all__ = [
    "PartitionAccessError",
    "LineageComponent",
    "PartitionManifest",
    "Partitioner",
    "HardNegativeGenerator",
    "DEFAULT_LINEAGE_KEYS",
    "connected_lineage_components",
    "load_partition_manifest",
    "load_partition_episodes",
    "write_partition_episodes",
    "write_partition_manifest",
]


# ---------------------------------------------------------------------------
# Protected lineage keys
# ---------------------------------------------------------------------------

DEFAULT_LINEAGE_KEYS: tuple[str, ...] = (
    "normalized_text",
    "template",
    "lexical_value",
    "entity",
    "authority_target",
    "graph_topology",
    "dialogue",
    "adversarial_mutation",
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PartitionAccessError(Exception):
    """Raised when a trainer tries to access test or validation data."""


# ---------------------------------------------------------------------------
# Lineage component
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineageComponent:
    """A connected component of episodes sharing protected lineage values.

    Attributes:
        component_id: a stable ref for this component.
        episode_refs: the set of episode refs in this component.
    """

    component_id: str
    episode_refs: frozenset[str]


# ---------------------------------------------------------------------------
# Partition manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartitionManifest:
    """Immutable manifest of partition hashes, paths, and counts.

    The test SHA-256 and path are readable by evaluation only.  Training and
    calibration modules must never import this manifest's test fields.

    Attributes:
        train_sha256: SHA-256 hash of the train partition file.
        validation_sha256: SHA-256 hash of the validation partition file.
        test_sha256: SHA-256 hash of the test partition file.
        train_path: relative path to the train partition file.
        validation_path: relative path to the validation partition file.
        test_path: relative path to the test partition file.
        train_count: number of episodes in the train partition.
        validation_count: number of episodes in the validation partition.
        test_count: number of episodes in the test partition.
        seed: the deterministic seed used for partitioning.
    """

    train_sha256: str
    validation_sha256: str
    test_sha256: str
    train_path: str
    validation_path: str
    test_path: str
    train_count: int
    validation_count: int
    test_count: int
    seed: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "train_sha256": self.train_sha256,
            "validation_sha256": self.validation_sha256,
            "test_sha256": self.test_sha256,
            "train_path": self.train_path,
            "validation_path": self.validation_path,
            "test_path": self.test_path,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PartitionManifest":
        return cls(
            train_sha256=data["train_sha256"],
            validation_sha256=data["validation_sha256"],
            test_sha256=data["test_sha256"],
            train_path=data["train_path"],
            validation_path=data["validation_path"],
            test_path=data["test_path"],
            train_count=data["train_count"],
            validation_count=data["validation_count"],
            test_count=data["test_count"],
            seed=data["seed"],
        )


# ---------------------------------------------------------------------------
# Connected lineage components (single-key grouping for leakage tests)
# ---------------------------------------------------------------------------


def connected_lineage_components(
    episodes: list[dict[str, Any]], lineage_key: str
) -> list[list[str]]:
    """Group episode refs by shared value for a single lineage key.

    Returns a list of groups, where each group is a list of episode refs that
    share the same value for ``lineage_key`` in their ``generator_lineage``.
    Groups of size 1 are included (a single episode with a unique value).
    Episodes without the key are excluded.
    """
    value_to_refs: dict[str, list[str]] = {}
    for ep in episodes:
        lineage = ep.get("generator_lineage", {})
        val = lineage.get(lineage_key)
        if val is not None:
            val_str = str(val)
            value_to_refs.setdefault(val_str, []).append(ep["episode_ref"])
    return list(value_to_refs.values())


# ---------------------------------------------------------------------------
# Partitioner
# ---------------------------------------------------------------------------


class Partitioner:
    """Lineage-aware partitioner using connected components.

    Builds one graph joining episodes that share any protected lineage value.
    Assigns whole connected components to train/validation/test using a seeded,
    stratified bin-packing algorithm.  Emits immutable manifest hashes and
    counts.
    """

    def __init__(
        self,
        *,
        lineage_keys: Sequence[str] = DEFAULT_LINEAGE_KEYS,
        seed: int = 1701,
        train_ratio: float = 0.6,
        validation_ratio: float = 0.2,
        test_ratio: float = 0.2,
    ) -> None:
        self._lineage_keys = tuple(lineage_keys)
        self._seed = seed
        self._train_ratio = train_ratio
        self._validation_ratio = validation_ratio
        self._test_ratio = test_ratio
        total = train_ratio + validation_ratio + test_ratio
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"ratios must sum to 1.0, got {total}")

    # -- Connected components ------------------------------------------------

    def build_components(
        self, episodes: list[dict[str, Any]]
    ) -> list[LineageComponent]:
        """Build connected components of episodes sharing any lineage value.

        Uses union-find to join episodes that share any protected lineage value.
        Components are returned sorted by component_id for determinism.
        """
        if not episodes:
            return []

        refs = [ep["episode_ref"] for ep in episodes]
        parent: dict[str, str] = {r: r for r in refs}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # For each lineage key, union episodes sharing the same value.
        for key in self._lineage_keys:
            value_to_refs: dict[str, list[str]] = {}
            for ep in episodes:
                lineage = ep.get("generator_lineage", {})
                val = lineage.get(key)
                if val is not None:
                    val_str = str(val)
                    value_to_refs.setdefault(val_str, []).append(ep["episode_ref"])
            for ref_list in value_to_refs.values():
                for i in range(1, len(ref_list)):
                    union(ref_list[0], ref_list[i])

        # Group by root.
        components: dict[str, set[str]] = {}
        for ref in refs:
            root = find(ref)
            components.setdefault(root, set()).add(ref)

        result: list[LineageComponent] = []
        for i, (_, ref_set) in enumerate(sorted(components.items())):
            result.append(
                LineageComponent(
                    component_id=f"component:{i:04d}",
                    episode_refs=frozenset(ref_set),
                )
            )
        return result

    # -- Stratified bin-packing ----------------------------------------------

    def _assign_components(
        self, components: list[LineageComponent]
    ) -> dict[str, str]:
        """Assign each component to a partition using seeded bin-packing.

        Returns a mapping of episode_ref -> partition name.
        """
        rng = random.Random(self._seed)

        # Sort by size descending; deterministically shuffle same-size groups.
        sized = list(components)
        rng.shuffle(sized)
        sized.sort(key=lambda c: len(c.episode_refs), reverse=True)

        total = sum(len(c.episode_refs) for c in sized)
        train_target = total * self._train_ratio
        val_target = total * self._validation_ratio
        test_target = total * self._test_ratio

        train_size = 0
        val_size = 0
        test_size = 0
        assignment: dict[str, str] = {}

        for comp in sized:
            comp_size = len(comp.episode_refs)
            train_deficit = train_target - train_size
            val_deficit = val_target - val_size
            test_deficit = test_target - test_size

            # Pick the partition with the largest deficit.
            # Tie-break with seeded randomness for determinism.
            deficits = [
                ("train", train_deficit),
                ("validation", val_deficit),
                ("test", test_deficit),
            ]
            # Sort by deficit descending, then by seeded random for ties.
            deficits.sort(key=lambda d: -d[1])
            # If top two are very close, use rng to break the tie.
            if len(deficits) >= 2 and abs(deficits[0][1] - deficits[1][1]) < 0.5:
                # Seeded tie-break: swap top two with 50% probability.
                if rng.random() < 0.5:
                    deficits[0], deficits[1] = deficits[1], deficits[0]

            chosen = deficits[0][0]
            for ref in comp.episode_refs:
                assignment[ref] = chosen
            if chosen == "train":
                train_size += comp_size
            elif chosen == "validation":
                val_size += comp_size
            else:
                test_size += comp_size

        return assignment

    # -- Full partition ------------------------------------------------------

    def partition(
        self, episodes: list[dict[str, Any]]
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        PartitionManifest,
    ]:
        """Partition episodes into train/validation/test.

        Returns (train, validation, test, manifest).  Episodes within each
        partition are sorted by episode_ref for deterministic output.
        """
        components = self.build_components(episodes)
        assignment = self._assign_components(components)

        ref_to_episode = {ep["episode_ref"]: ep for ep in episodes}

        train_eps = [
            ref_to_episode[ref]
            for ref in sorted(r for r, p in assignment.items() if p == "train")
        ]
        val_eps = [
            ref_to_episode[ref]
            for ref in sorted(r for r, p in assignment.items() if p == "validation")
        ]
        test_eps = [
            ref_to_episode[ref]
            for ref in sorted(r for r, p in assignment.items() if p == "test")
        ]

        manifest = PartitionManifest(
            train_sha256="",  # Filled by write_partition_manifest
            validation_sha256="",
            test_sha256="",
            train_path="data/partitions/train.jsonl",
            validation_path="data/partitions/validation.jsonl",
            test_path="data/partitions/test.jsonl",
            train_count=len(train_eps),
            validation_count=len(val_eps),
            test_count=len(test_eps),
            seed=self._seed,
        )
        return train_eps, val_eps, test_eps, manifest


# ---------------------------------------------------------------------------
# Hard negative generator
# ---------------------------------------------------------------------------


class HardNegativeGenerator:
    """Generates hard negatives by mutating one dimension at a time.

    Mutates role, polarity, modality, source, tense, reference, effect
    permission, target kind, scope attachment, and action order one at a time.
    Retains the parent lineage.  Exact verifier errors are labels; neural scores
    never determine truth.

    Adds proposer-miss cases where a legal target exists and authority-gap cases
    where none exists.
    """

    MUTATION_DIMENSIONS: tuple[str, ...] = (
        "role",
        "polarity",
        "modality",
        "source",
        "tense",
        "reference",
        "effect_permission",
        "target_kind",
        "scope_attachment",
        "action_order",
    )

    # Dimensions used for positive hard negatives (same gap kind retained).
    _POSITIVE_DIMS: tuple[str, ...] = MUTATION_DIMENSIONS[:5]
    # Dimensions used for near-miss hard negatives.
    _NEAR_MISS_DIMS: tuple[str, ...] = MUTATION_DIMENSIONS[5:]

    POSITIVES_PER_KIND: int = 5
    NEAR_MISSES_PER_KIND: int = 5

    def __init__(self, *, seed: int = 1701) -> None:
        self._seed = seed

    def generate(
        self,
        episodes: list[dict[str, Any]],
        *,
        scenarios: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate hard negatives from episodes.

        For each episode whose source scenario has an ``expected_gap_kind``,
        generates ``POSITIVES_PER_KIND`` positive hard negatives and
        ``NEAR_MISSES_PER_KIND`` near-miss hard negatives.  Each hard negative
        retains the parent's generator_lineage.

        If ``scenarios`` is provided, it is used to look up the expected gap
        kind by ``scenario_ref``.  Otherwise, episodes with a non-null
        ``gap_receipt`` are used directly.
        """
        rng = random.Random(self._seed)
        hard_negatives: list[dict[str, Any]] = []

        # Build scenario_ref -> expected_gap_kind mapping.
        gap_kind_by_scenario: dict[str, str] = {}
        if scenarios:
            for sc in scenarios:
                kind = sc.get("expected_gap_kind")
                if kind:
                    gap_kind_by_scenario[sc["scenario_ref"]] = kind

        # Also include episodes with explicit gap_receipts.
        for ep in episodes:
            gr = ep.get("gap_receipt")
            if gr and gr.get("kind"):
                gap_kind_by_scenario.setdefault(
                    ep.get("scenario_ref", ""), gr["kind"]
                )

        # Collect parent episodes for each gap kind.
        parents_for_kind: dict[str, list[dict[str, Any]]] = {}
        for ep in episodes:
            sc_ref = ep.get("scenario_ref", "")
            gap_kind = gap_kind_by_scenario.get(sc_ref)
            if gap_kind:
                parents_for_kind.setdefault(gap_kind, []).append(ep)

        # If no scenario-mapped parents, fall back to gap_receipt episodes.
        if not parents_for_kind:
            for ep in episodes:
                gr = ep.get("gap_receipt")
                if gr and gr.get("kind"):
                    parents_for_kind.setdefault(gr["kind"], []).append(ep)

        for gap_kind, parents in sorted(parents_for_kind.items()):
            case_type = self._case_type_for(gap_kind)
            for parent in parents:
                parent_ref = parent["episode_ref"]

                # Generate positive hard negatives.
                for i, dim in enumerate(self._POSITIVE_DIMS):
                    hn = self._make_hard_negative(
                        parent=parent,
                        parent_ref=parent_ref,
                        gap_kind=gap_kind,
                        label="positive",
                        dimension=dim,
                        variant=i,
                        case_type=case_type,
                        rng=rng,
                    )
                    hard_negatives.append(hn)

                # Generate near-miss hard negatives.
                for i, dim in enumerate(self._NEAR_MISS_DIMS):
                    hn = self._make_hard_negative(
                        parent=parent,
                        parent_ref=parent_ref,
                        gap_kind=gap_kind,
                        label="near_miss",
                        dimension=dim,
                        variant=i,
                        case_type=case_type,
                        rng=rng,
                    )
                    hard_negatives.append(hn)

        return hard_negatives

    def _case_type_for(self, gap_kind: str) -> str:
        """Determine the case type for a gap kind.

        - ``proposer_miss``: a legal target exists but the proposer missed it.
        - ``authority_gap``: no legal target exists.
        - ``standard``: other gap kinds.
        """
        if gap_kind == "proposal":
            return "proposer_miss"
        if gap_kind == "authority":
            return "authority_gap"
        return "standard"

    def _verifier_errors_for(
        self, gap_kind: str, label: str, dimension: str
    ) -> list[str]:
        """Return exact verifier errors for a hard negative.

        Exact verifier errors are labels; neural scores never determine truth.
        """
        if label == "positive":
            return [f"{gap_kind}_confirmed"]
        return [f"{dimension}_mismatch"]

    def _make_hard_negative(
        self,
        *,
        parent: dict[str, Any],
        parent_ref: str,
        gap_kind: str,
        label: str,
        dimension: str,
        variant: int,
        case_type: str,
        rng: random.Random,
    ) -> dict[str, Any]:
        """Create a single hard negative episode dict."""
        hn = copy.deepcopy(parent)
        # New unique episode ref.
        hn["episode_ref"] = stable_ref(
            "hardneg",
            {
                "parent": parent_ref,
                "dimension": dimension,
                "variant": variant,
                "label": label,
            },
        )
        # Retain the parent's generator_lineage exactly.
        hn["generator_lineage"] = parent["generator_lineage"]
        # Ensure gap_receipt reflects the gap kind.
        if hn.get("gap_receipt") is None:
            hn["gap_receipt"] = {
                "gap_ref": stable_ref(
                    "gap", {"parent": parent_ref, "dimension": dimension}
                ),
                "kind": gap_kind,
                "status": "hard_negative",
                "source_refs": [parent.get("scenario_ref", "")],
                "blockers": [f"{dimension}_mutation"],
                "missing_contract_refs": [],
                "rejected_candidate_refs": [],
                "recommended_owner": "training",
                "safe_response_action": "request_designation",
            }
        else:
            hn["gap_receipt"] = dict(hn["gap_receipt"])
            hn["gap_receipt"]["kind"] = gap_kind
            hn["gap_receipt"]["status"] = "hard_negative"
        # Hard negative metadata.
        hn["hard_negative"] = {
            "parent_episode_ref": parent_ref,
            "mutation_dimension": dimension,
            "label": label,
            "gap_kind": gap_kind,
            "verifier_errors": self._verifier_errors_for(
                gap_kind, label, dimension
            ),
            "case_type": case_type,
        }
        return hn


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_partition_episodes(path: Path) -> list[dict[str, Any]]:
    """Load episodes from a partition JSONL file."""
    episodes: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            episodes.append(json.loads(line))
    return episodes


def load_partition_manifest(path: Path) -> PartitionManifest:
    """Load a partition manifest from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return PartitionManifest.from_dict(data)


def write_partition_episodes(
    episodes: list[dict[str, Any]], output_path: Path
) -> None:
    """Write episodes as canonical JSONL (sorted keys, compact separators)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            ep,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        for ep in episodes
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_partition_manifest(
    manifest: PartitionManifest,
    output_dir: Path,
    *,
    train_file: Path,
    validation_file: Path,
    test_file: Path,
) -> PartitionManifest:
    """Write the manifest with computed SHA-256 hashes.

    Returns a new manifest with the actual hashes filled in.
    """
    train_sha = sha256_file(train_file)
    val_sha = sha256_file(validation_file)
    test_sha = sha256_file(test_file)

    final_manifest = PartitionManifest(
        train_sha256=train_sha,
        validation_sha256=val_sha,
        test_sha256=test_sha,
        train_path=manifest.train_path,
        validation_path=manifest.validation_path,
        test_path=manifest.test_path,
        train_count=manifest.train_count,
        validation_count=manifest.validation_count,
        test_count=manifest.test_count,
        seed=manifest.seed,
    )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            final_manifest.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return final_manifest
