"""Tests for gap episode coverage.

Every GapKind must have at least 5 positive and 5 near-miss episodes in the
partitioned data.  Positive episodes are episodes that genuinely produce the
gap; near-miss episodes are hard negative mutations labeled as near-miss for
that gap kind.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.gaps import GapKind
from cemm_authoritative_hybrid.partitions import load_partition_episodes

ROOT = Path(__file__).parents[1]
PARTITIONS_DIR = ROOT / "data" / "partitions"


# ---------------------------------------------------------------------------
# Gap episode counter
# ---------------------------------------------------------------------------


class GapEpisodeCounter:
    """Counts positive and near-miss episodes per gap kind."""

    def __init__(self, episodes: list[dict]) -> None:
        self._counts: Counter[str, tuple[str, str]] = Counter()
        for ep in episodes:
            kind: str | None = None
            label: str | None = None
            if ep.get("hard_negative"):
                kind = ep["hard_negative"].get("gap_kind")
                label = ep["hard_negative"].get("label")
            elif ep.get("gap_receipt"):
                kind = ep["gap_receipt"].get("kind")
                label = "positive"
            if kind and label:
                self._counts[(kind, label)] += 1

    def count(self, kind: GapKind | str, label: str) -> int:
        kind_value = kind.value if isinstance(kind, GapKind) else kind
        return self._counts.get((kind_value, label), 0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gap_episodes() -> GapEpisodeCounter:
    eps: list[dict] = []
    for name in ("train", "validation", "test"):
        eps.extend(load_partition_episodes(PARTITIONS_DIR / f"{name}.jsonl"))
    return GapEpisodeCounter(eps)


# ---------------------------------------------------------------------------
# Coverage tests
# ---------------------------------------------------------------------------


def test_every_gap_kind_has_positive_and_near_miss(
    gap_episodes: GapEpisodeCounter,
) -> None:
    """Every GapKind must have at least 5 positive and 5 near-miss episodes."""
    for kind in GapKind:
        assert gap_episodes.count(kind, "positive") >= 5, (
            f"GapKind.{kind.name} has only {gap_episodes.count(kind, 'positive')} "
            f"positive episodes (need >= 5)"
        )
        assert gap_episodes.count(kind, "near_miss") >= 5, (
            f"GapKind.{kind.name} has only {gap_episodes.count(kind, 'near_miss')} "
            f"near-miss episodes (need >= 5)"
        )


def test_all_18_gap_kinds_are_covered(gap_episodes: GapEpisodeCounter) -> None:
    """All 18 gap kinds must appear in the partitioned data."""
    for kind in GapKind:
        total = gap_episodes.count(kind, "positive") + gap_episodes.count(kind, "near_miss")
        assert total > 0, f"GapKind.{kind.name} has no episodes at all"
