"""Tests for hard negative generation.

Hard negatives mutate one dimension at a time (role, polarity, modality, source,
tense, reference, effect permission, target kind, scope attachment, action
order), retain the parent lineage, and use exact verifier errors as labels.
Neural scores never determine truth.

Proposer-miss cases are added where a legal target exists; authority-gap cases
are added where none exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.partitions import (
    HardNegativeGenerator,
    load_partition_episodes,
)

ROOT = Path(__file__).parents[1]
PARTITIONS_DIR = ROOT / "data" / "partitions"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def all_episodes() -> list[dict]:
    eps: list[dict] = []
    for name in ("train", "validation", "test"):
        eps.extend(load_partition_episodes(PARTITIONS_DIR / f"{name}.jsonl"))
    return eps


@pytest.fixture
def hard_negatives(all_episodes: list[dict]) -> list[dict]:
    return [ep for ep in all_episodes if ep.get("hard_negative")]


# ---------------------------------------------------------------------------
# Mutation dimension tests
# ---------------------------------------------------------------------------


def test_hard_negatives_exist(hard_negatives: list[dict]) -> None:
    """At least some hard negatives must be generated."""
    assert len(hard_negatives) > 0


def test_hard_negatives_mutate_one_dimension(hard_negatives: list[dict]) -> None:
    """Each hard negative must mutate exactly one valid dimension."""
    valid_dims = set(HardNegativeGenerator.MUTATION_DIMENSIONS)
    for hn in hard_negatives:
        meta = hn["hard_negative"]
        assert meta["mutation_dimension"] in valid_dims
        assert isinstance(meta["mutation_dimension"], str)


def test_hard_negatives_retain_parent_lineage(
    all_episodes: list[dict], hard_negatives: list[dict]
) -> None:
    """Hard negatives must retain the parent's generator_lineage exactly."""
    ref_to_ep = {ep["episode_ref"]: ep for ep in all_episodes}
    for hn in hard_negatives:
        parent_ref = hn["hard_negative"]["parent_episode_ref"]
        parent = ref_to_ep.get(parent_ref)
        assert parent is not None, f"parent {parent_ref} not found"
        assert hn["generator_lineage"] == parent["generator_lineage"]


def test_hard_negatives_have_verifier_error_labels(
    hard_negatives: list[dict],
) -> None:
    """Each hard negative must carry exact verifier errors as labels."""
    for hn in hard_negatives:
        meta = hn["hard_negative"]
        assert "verifier_errors" in meta
        assert isinstance(meta["verifier_errors"], list)
        assert len(meta["verifier_errors"]) > 0
        # Neural scores must not be the label source.
        assert "neural_score" not in meta


def test_hard_negatives_have_valid_labels(hard_negatives: list[dict]) -> None:
    """Each hard negative must be labeled 'positive' or 'near_miss'."""
    for hn in hard_negatives:
        label = hn["hard_negative"]["label"]
        assert label in ("positive", "near_miss"), f"invalid label: {label}"


def test_hard_negatives_have_gap_kind(hard_negatives: list[dict]) -> None:
    """Each hard negative must carry a gap_kind."""
    for hn in hard_negatives:
        assert "gap_kind" in hn["hard_negative"]
        assert hn["hard_negative"]["gap_kind"]


def test_proposer_miss_and_authority_gap_cases_exist(
    hard_negatives: list[dict],
) -> None:
    """Proposer-miss and authority-gap case types must be present."""
    case_types = {hn["hard_negative"].get("case_type") for hn in hard_negatives}
    assert "proposer_miss" in case_types
    assert "authority_gap" in case_types


def test_hard_negatives_have_unique_refs(hard_negatives: list[dict]) -> None:
    """Each hard negative must have a unique episode_ref."""
    refs = [hn["episode_ref"] for hn in hard_negatives]
    assert len(refs) == len(set(refs)), "duplicate hard negative refs"


def test_hard_negatives_have_valid_abi_version(hard_negatives: list[dict]) -> None:
    """Hard negatives must carry the active ABI version."""
    for hn in hard_negatives:
        assert hn["abi_version"] == 1
