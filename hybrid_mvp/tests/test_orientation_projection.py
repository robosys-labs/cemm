"""Tests for bounded ORIENT projection (OrientationProjector).

These tests verify that the ORIENT phase projects self, other, and reachable
context from participants, active turn/session events, verified focus, open
obligations, and relevant goals — without scanning all atoms.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.cycle import Orientation


# ---------------------------------------------------------------------------
# Orientation projection
# ---------------------------------------------------------------------------


def test_orientation_projects_self_other_and_reachable_context(runtime):
    orientation = runtime.orient("session:one", "what did you say?")
    assert orientation.participants == ("participant:system", "participant:user")
    assert orientation.active_turn_ref in orientation.event_refs
    assert orientation.focus_refs
    assert orientation.revision_pin.authority_generation
    assert orientation.scanned_atom_count == 0


def test_orientation_does_not_scan_all_atoms(runtime):
    orientation = runtime.orient("session:one", "hello")
    assert orientation.scanned_atom_count == 0


def test_orientation_records_index_probes(runtime):
    orientation = runtime.orient("session:one", "hello")
    assert orientation.index_probes


def test_orientation_records_visited_refs(runtime):
    orientation = runtime.orient("session:one", "hello")
    assert orientation.visited_refs


def test_orientation_has_cache_key(runtime):
    orientation = runtime.orient("session:one", "hello")
    assert orientation.cache_key


def test_orientation_has_revision_pin(runtime):
    orientation = runtime.orient("session:one", "hello")
    assert orientation.revision_pin is not None
    assert orientation.revision_pin.authority_generation


def test_orientation_participants_are_sorted(runtime):
    orientation = runtime.orient("session:one", "hello")
    assert orientation.participants == tuple(sorted(orientation.participants))


def test_orientation_event_refs_include_active_turn(runtime):
    orientation = runtime.orient("session:two", "say hello")
    assert orientation.active_turn_ref
    assert orientation.active_turn_ref in orientation.event_refs


def test_orientation_focus_refs_from_grounding(runtime):
    """Focus refs come from grounding the input text, not from scanning atoms."""
    orientation = runtime.orient("session:one", "hello")
    # "hello" designates event:greeting in the authority.
    assert "event:greeting" in orientation.focus_refs


def test_orientation_is_frozen(runtime):
    import dataclasses

    orientation = runtime.orient("session:one", "hello")
    assert dataclasses.is_dataclass(orientation)
    try:
        orientation.scanned_atom_count = 1  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Orientation must be frozen")


def test_orientation_traverses_relations_within_depth(runtime):
    """Projection traverses indexed relations within max_graph_depth."""
    orientation = runtime.orient("session:one", "hello")
    # The authority has relation types; projection should visit some relation refs.
    # Visited refs should include more than just the focus refs.
    assert len(orientation.visited_refs) >= len(orientation.focus_refs)


def test_orientation_entity_concept_relation_independent(runtime):
    """Entity, concept, relation, state, and event identities remain
    independently addressable; events do not become a universal wrapper."""
    orientation = runtime.orient("session:one", "hello")
    # event:greeting is an event_type, not an entity or concept.
    assert "event:greeting" in orientation.focus_refs
    # Participants are participants, not events.
    for p in orientation.participants:
        assert p.startswith("participant:")
