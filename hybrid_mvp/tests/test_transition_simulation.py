"""Tests for typed transition simulation and sequence composition.

Tests cover:
- Simulated transitions do not commit (world revision unchanged).
- Transition sequence is typed composition, not state overwrite.
- Composed result equals sequential result; proof_refs concatenate.
- No implicit inverse (inverse_of always returns None).
- Preview checks preconditions and raises on violation.
- Commit appends history with optimistic revision checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.epistemics import EpistemicPlacement
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.state import (
    StateIndex,
    StateClaim,
    TemporalState,
    TransitionEngine,
    TransitionPreview,
)


# ---------------------------------------------------------------------------
# Test-only authority with transitions
# ---------------------------------------------------------------------------


class _TransitionAuthority:
    """Minimal authority-like object with transitions for testing."""

    generation = "authority:transition-test-v1"
    content_hash = "test-content"
    model_compatibility_hash = "test-compat"
    value_dimensions = {
        "value:off": "dim:power",
        "value:on": "dim:power",
        "value:offline": "dim:availability",
        "value:online": "dim:availability",
        "value:open": "dim:door_state",
    }
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}

    _transitions = {
        "transition:power_on": {
            "transition_ref": "transition:power_on",
            "preconditions": [{"dimension": "dim:power", "value": "value:off"}],
            "effects": [{"dimension": "dim:power", "value": "value:on"}],
        },
        "transition:connect": {
            "transition_ref": "transition:connect",
            "preconditions": [{"dimension": "dim:power", "value": "value:on"}],
            "effects": [{"dimension": "dim:availability", "value": "value:online"}],
        },
        "transition:open_door": {
            "transition_ref": "transition:open_door",
            "preconditions": [{"dimension": "dim:door_state", "value": "value:closed"}],
            "effects": [{"dimension": "dim:door_state", "value": "value:open"}],
        },
    }

    def by_kind(self, kind: str) -> frozenset[str]:
        return frozenset()

    def by_transition(self, key: str) -> dict[str, Any] | None:
        return self._transitions.get(key)

    def by_event_signature(self, event_type: str) -> Any:
        return None

    def by_state_dimension(self, dim: str) -> frozenset[str]:
        return frozenset()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _placement(mode: str = "observed") -> EpistemicPlacement:
    return EpistemicPlacement(
        source_ref="participant:user",
        mode=mode,  # type: ignore[arg-type]
    )


def _temporal_state(
    entity: str = "entity:server",
    dimension: str = "dim:power",
    value: str = "value:off",
) -> TemporalState:
    return TemporalState(
        entity_ref=entity,
        dimension_ref=dimension,
        value_ref=value,
        interval=(0, 100),
        placement=_placement(),
        revision=0,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authority() -> _TransitionAuthority:
    return _TransitionAuthority()


@pytest.fixture
def config() -> RuntimeConfig:
    return RuntimeConfig.release()


@pytest.fixture
def transition_engine(authority, config) -> TransitionEngine:
    return TransitionEngine(authority, config)


@pytest.fixture
def offline_state() -> TemporalState:
    """A server in the offline/power-off state."""
    return _temporal_state("entity:server", "dim:power", "value:off")


@pytest.fixture
def stores(authority):
    return memory_stores(authority_generation=authority.generation)


# ---------------------------------------------------------------------------
# Tests: simulated transition does not commit
# ---------------------------------------------------------------------------


class TestSimulatedTransitionDoesNotCommit:
    def test_preview_does_not_mutate_revision(self, transition_engine, offline_state, stores):
        before = stores.world.revision
        preview = transition_engine.preview(offline_state, "transition:power_on")
        assert preview.resulting_state.value_ref == "value:on"
        assert stores.world.revision == before

    def test_preview_sequence_does_not_mutate_revision(
        self, transition_engine, offline_state, stores
    ):
        before = stores.world.revision
        preview = transition_engine.preview_sequence(
            offline_state, ("transition:power_on", "transition:connect")
        )
        assert preview.resulting_state.value_ref == "value:online"
        assert stores.world.revision == before


# ---------------------------------------------------------------------------
# Tests: transition sequence is typed composition, not state overwrite
# ---------------------------------------------------------------------------


class TestTransitionSequenceIsTypedComposition:
    def test_composed_equals_sequential(self, transition_engine, offline_state):
        first = transition_engine.preview(offline_state, "transition:power_on")
        second = transition_engine.preview(first.resulting_state, "transition:connect")
        composed = transition_engine.preview_sequence(
            offline_state, ("transition:power_on", "transition:connect")
        )
        assert composed.resulting_state == second.resulting_state

    def test_composed_proof_refs_concatenate(self, transition_engine, offline_state):
        first = transition_engine.preview(offline_state, "transition:power_on")
        second = transition_engine.preview(first.resulting_state, "transition:connect")
        composed = transition_engine.preview_sequence(
            offline_state, ("transition:power_on", "transition:connect")
        )
        assert composed.proof_refs == first.proof_refs + second.proof_refs

    def test_no_implicit_inverse(self, transition_engine):
        assert transition_engine.inverse_of("transition:power_on") is None
        assert transition_engine.inverse_of("transition:connect") is None

    def test_empty_sequence_returns_input_state(self, transition_engine, offline_state):
        composed = transition_engine.preview_sequence(offline_state, ())
        assert composed.resulting_state == offline_state
        assert composed.proof_refs == ()


# ---------------------------------------------------------------------------
# Tests: precondition checking
# ---------------------------------------------------------------------------


class TestPreconditionChecking:
    def test_precondition_violation_raises(self, transition_engine):
        """power_on requires power=off; power=on should raise."""
        on_state = _temporal_state("entity:server", "dim:power", "value:on")
        with pytest.raises(ValueError, match="precondition not met"):
            transition_engine.preview(on_state, "transition:power_on")

    def test_unknown_transition_raises(self, transition_engine, offline_state):
        with pytest.raises(ValueError, match="unknown transition"):
            transition_engine.preview(offline_state, "transition:nonexistent")

    def test_sequence_stops_on_precondition_violation(
        self, transition_engine, offline_state
    ):
        """connect requires power=on; starting from power=off should fail."""
        with pytest.raises(ValueError, match="precondition not met"):
            transition_engine.preview_sequence(
                offline_state, ("transition:connect",)
            )


# ---------------------------------------------------------------------------
# Tests: commit appends history with optimistic revision checks
# ---------------------------------------------------------------------------


class TestCommitAppendsHistory:
    def test_commit_increments_revision(self, transition_engine, offline_state, stores):
        preview = transition_engine.preview(offline_state, "transition:power_on")
        before = stores.world.revision
        receipt = transition_engine.commit(preview, stores)
        assert stores.world.revision == before + 1
        assert receipt.new_revision == before + 1
        assert receipt.parent_revision == before

    def test_commit_stale_revision_raises(self, transition_engine, offline_state, stores):
        from cemm_authoritative_hybrid.persistence import StaleRevisionError

        preview = transition_engine.preview(offline_state, "transition:power_on")
        # Commit once to advance the revision.
        transition_engine.commit(preview, stores)
        # Re-commit the same preview (which has the old expected revision).
        with pytest.raises(StaleRevisionError):
            transition_engine.commit(preview, stores)

    def test_commit_records_transition_proof(self, transition_engine, offline_state, stores):
        preview = transition_engine.preview(offline_state, "transition:power_on")
        receipt = transition_engine.commit(preview, stores)
        assert receipt.store == "world"
        assert receipt.transaction_ref
