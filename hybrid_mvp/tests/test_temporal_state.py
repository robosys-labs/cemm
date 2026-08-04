"""Tests for temporal state indexing and conflict detection.

Tests cover:
- Conflicting observations preserve both sources → status "conflict".
- Supported observations return the value and source.
- Unknown queries return status "unknown".
- State index is keyed by entity, dimension, interval, and epistemic placement.
- Time-filtered queries only match observations within the interval.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cemm_authoritative_hybrid.epistemics import EpistemicPlacement
from cemm_authoritative_hybrid.state import (
    StateClaim,
    StateIndex,
    StateQueryResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _placement(
    *,
    mode: str = "observed",
    source_ref: str = "participant:user",
) -> EpistemicPlacement:
    return EpistemicPlacement(
        source_ref=source_ref,
        mode=mode,  # type: ignore[arg-type]
    )


def state_claim(
    entity: str,
    value: str,
    *,
    source: str,
    at: int,
    dimension: str | None = None,
) -> StateClaim:
    """Build a StateClaim for ``entity`` with ``value`` from ``source`` at ``at``."""
    dim = dimension or f"dim:{entity}_state"
    return StateClaim(
        entity_ref=f"entity:{entity}",
        dimension_ref=dim,
        value_ref=f"value:{value}",
        interval=(at, at),
        source_ref=source,
        placement=_placement(source_ref=source),
    )


def state(entity: str, value: str) -> _StateQuery:
    """Create a state query for ``entity`` and the dimension of ``value``."""
    dim_map = {
        "open": "dim:door_state",
        "closed": "dim:door_state",
    }
    return _StateQuery(
        entity_ref=f"entity:{entity}",
        dimension_ref=dim_map.get(value, f"dim:{entity}_state"),
    )


@dataclass(frozen=True)
class _StateQuery:
    entity_ref: str
    dimension_ref: str


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def state_index() -> StateIndex:
    return StateIndex()


@pytest.fixture
def runtime(state_index):
    """Lightweight test runtime wrapping the state index."""

    class _WorldFacade:
        def __init__(self, idx: StateIndex) -> None:
            self._idx = idx

        def query(self, q: _StateQuery) -> StateQueryResult:
            return self._idx.query(q.entity_ref, q.dimension_ref)

    class _TestRuntime:
        def __init__(self) -> None:
            self._idx = state_index
            self.world = _WorldFacade(state_index)

        def observe(self, claim: StateClaim) -> None:
            self._idx.observe(claim)

        def query(self, q: _StateQuery) -> StateQueryResult:
            return self._idx.query(q.entity_ref, q.dimension_ref)

    return _TestRuntime()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConflictingObservationsPreserveBothSources:
    def test_conflict_status_and_sources(self, runtime):
        runtime.observe(state_claim("door", "open", source="sensor:a", at=10))
        runtime.observe(state_claim("door", "closed", source="sensor:b", at=10))
        result = runtime.query(state("door", "open"))
        assert result.status == "conflict"
        assert set(result.source_refs) == {"sensor:a", "sensor:b"}

    def test_conflict_preserves_both_observations(self, state_index):
        state_index.observe(state_claim("door", "open", source="sensor:a", at=10))
        state_index.observe(state_claim("door", "closed", source="sensor:b", at=10))
        result = state_index.query("entity:door", "dim:door_state")
        assert len(result.observations) == 2
        values = {obs.value_ref for obs in result.observations}
        assert values == {"value:open", "value:closed"}


class TestSupportedObservations:
    def test_single_observation_is_supported(self, state_index):
        state_index.observe(state_claim("door", "open", source="sensor:a", at=10))
        result = state_index.query("entity:door", "dim:door_state")
        assert result.status == "supported"
        assert result.value_ref == "value:open"
        assert result.source_refs == ("sensor:a",)

    def test_same_value_same_source_is_supported(self, state_index):
        state_index.observe(state_claim("door", "open", source="sensor:a", at=10))
        state_index.observe(state_claim("door", "open", source="sensor:a", at=12))
        result = state_index.query("entity:door", "dim:door_state")
        assert result.status == "supported"
        assert result.value_ref == "value:open"


class TestUnknownQueries:
    def test_no_observations_is_unknown(self, state_index):
        result = state_index.query("entity:door", "dim:door_state")
        assert result.status == "unknown"
        assert result.value_ref is None
        assert result.source_refs == ()

    def test_different_entity_is_unknown(self, state_index):
        state_index.observe(state_claim("door", "open", source="sensor:a", at=10))
        result = state_index.query("entity:window", "dim:door_state")
        assert result.status == "unknown"

    def test_different_dimension_is_unknown(self, state_index):
        state_index.observe(state_claim("door", "open", source="sensor:a", at=10))
        result = state_index.query("entity:door", "dim:power")
        assert result.status == "unknown"


class TestTimeFilteredQueries:
    def test_time_filter_excludes_outside_interval(self, state_index):
        state_index.observe(state_claim("door", "open", source="sensor:a", at=10))
        result = state_index.query("entity:door", "dim:door_state", time=20)
        assert result.status == "unknown"

    def test_time_filter_includes_inside_interval(self, state_index):
        state_index.observe(
            StateClaim(
                entity_ref="entity:door",
                dimension_ref="dim:door_state",
                value_ref="value:open",
                interval=(5, 15),
                source_ref="sensor:a",
                placement=_placement(),
            )
        )
        result = state_index.query("entity:door", "dim:door_state", time=10)
        assert result.status == "supported"
        assert result.value_ref == "value:open"


class TestKeyedByEpistemicPlacement:
    def test_different_placements_preserve_both(self, state_index):
        """Observations with different epistemic placements are both kept."""
        observed = state_claim("door", "open", source="sensor:a", at=10)
        reported = StateClaim(
            entity_ref="entity:door",
            dimension_ref="dim:door_state",
            value_ref="value:closed",
            interval=(10, 10),
            source_ref="entity:ada",
            placement=_placement(mode="reported", source_ref="entity:ada"),
        )
        state_index.observe(observed)
        state_index.observe(reported)
        result = state_index.query("entity:door", "dim:door_state")
        assert result.status == "conflict"
        assert set(result.source_refs) == {"sensor:a", "entity:ada"}
