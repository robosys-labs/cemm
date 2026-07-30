"""Tests for lineage-aware partition leakage control.

A partitioner must build one graph joining episodes that share any protected
lineage value, assign whole connected components to train/validation/test, and
emit immutable manifest hashes and counts.  The sealed test manifest is readable
by evaluation only, never imported by training or calibration modules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.canonical import canonical_json
from cemm_authoritative_hybrid.partitions import (
    PartitionManifest,
    connected_lineage_components,
    load_partition_episodes,
    load_partition_manifest,
)

ROOT = Path(__file__).parents[1]
PARTITIONS_DIR = ROOT / "data" / "partitions"
TRAIN_CONFIG_PATH = ROOT / "configs" / "proposal_dev.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _Partitioned:
    """All partitioned episodes with a partition lookup."""

    def __init__(self) -> None:
        self.all: list[dict] = []
        self._ref_to_partition: dict[str, str] = {}
        for name in ("train", "validation", "test"):
            eps = load_partition_episodes(PARTITIONS_DIR / f"{name}.jsonl")
            for ep in eps:
                ref = ep["episode_ref"]
                self.all.append(ep)
                self._ref_to_partition[ref] = name

    def partition_of(self, ref: str) -> str:
        return self._ref_to_partition[ref]


@pytest.fixture
def partitioned() -> _Partitioned:
    return _Partitioned()


@pytest.fixture
def partition_manifest() -> PartitionManifest:
    return load_partition_manifest(PARTITIONS_DIR / "manifest.json")


@pytest.fixture
def train_config() -> dict:
    assert TRAIN_CONFIG_PATH.exists(), f"Missing {TRAIN_CONFIG_PATH}"
    return json.loads(TRAIN_CONFIG_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Transitive leakage tests
# ---------------------------------------------------------------------------


LINEAGE_KEYS = [
    "normalized_text",
    "template",
    "lexical_value",
    "entity",
    "authority_target",
    "graph_topology",
    "dialogue",
    "adversarial_mutation",
]


@pytest.mark.parametrize("lineage", LINEAGE_KEYS)
def test_no_lineage_component_crosses_partitions(
    partitioned: _Partitioned, lineage: str
) -> None:
    """No group of episodes sharing a protected lineage value spans partitions."""
    groups = connected_lineage_components(partitioned.all, lineage)
    assert all(
        len({partitioned.partition_of(ref) for ref in group}) == 1
        for group in groups
    )


def test_sealed_test_hash_is_not_available_to_training(
    partition_manifest: PartitionManifest, train_config: dict
) -> None:
    """The test partition hash and path must not appear in training config."""
    text = canonical_json(train_config)
    assert partition_manifest.test_sha256 not in text
    assert partition_manifest.test_path not in text


def test_partition_manifest_has_correct_counts(
    partitioned: _Partitioned, partition_manifest: PartitionManifest
) -> None:
    """Manifest counts must sum to the total number of episodes."""
    total = len(partitioned.all)
    assert (
        partition_manifest.train_count
        + partition_manifest.validation_count
        + partition_manifest.test_count
        == total
    )


def test_partition_counts_match_files(partition_manifest: PartitionManifest) -> None:
    """Each partition file must contain exactly the manifest-declared count."""
    for name, count in [
        ("train", partition_manifest.train_count),
        ("validation", partition_manifest.validation_count),
        ("test", partition_manifest.test_count),
    ]:
        path = PARTITIONS_DIR / f"{name}.jsonl"
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == count


def test_partition_manifest_hashes_match_files(
    partition_manifest: PartitionManifest,
) -> None:
    """Manifest SHA-256 hashes must match the actual partition files."""
    from cemm_authoritative_hybrid.canonical import sha256_file

    assert sha256_file(PARTITIONS_DIR / "train.jsonl") == partition_manifest.train_sha256
    assert (
        sha256_file(PARTITIONS_DIR / "validation.jsonl")
        == partition_manifest.validation_sha256
    )
    assert sha256_file(PARTITIONS_DIR / "test.jsonl") == partition_manifest.test_sha256


def test_every_episode_apars_in_exactly_one_partition(
    partitioned: _Partitioned,
) -> None:
    """Every episode ref must appear in exactly one partition."""
    refs = [ep["episode_ref"] for ep in partitioned.all]
    assert len(refs) == len(set(refs)), "duplicate episode refs across partitions"


def test_partition_ratios_are_approximately_balanced(
    partitioned: _Partitioned,
) -> None:
    """Partition sizes should be approximately 60/20/20."""
    total = len(partitioned.all)
    train = sum(1 for ep in partitioned.all if partitioned.partition_of(ep["episode_ref"]) == "train")
    val = sum(1 for ep in partitioned.all if partitioned.partition_of(ep["episode_ref"]) == "validation")
    test = sum(1 for ep in partitioned.all if partitioned.partition_of(ep["episode_ref"]) == "test")
    # Allow generous tolerance because connected components are atomic.
    assert train / total >= 0.45, f"train ratio {train / total:.2f} too low"
    assert val / total >= 0.10, f"validation ratio {val / total:.2f} too low"
    assert test / total >= 0.10, f"test ratio {test / total:.2f} too low"
