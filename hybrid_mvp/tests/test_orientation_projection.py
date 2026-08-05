"""Tests for bounded ORIENT projection (OrientationProjector).

These tests verify that the ORIENT phase projects self, other, and reachable
context from participants, active turn/session events, verified focus, open
obligations, and relevant goals — without scanning all atoms.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import (
    Orientation,
    OrientationProjector,
    SemanticMode,
)


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


def test_orientation_projector_includes_source_on_first_construction(runtime):
    source = "what did you say?"
    orientation = runtime.orient("session:source", source)
    assert orientation.source_text == source
    assert Orientation.from_dict(orientation.as_dict()).source_text == source
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


def test_orientation_records_disabled_relation_adjacency_seam(runtime):
    """Projection exposes one bounded seam while adjacency is unavailable."""
    orientation = runtime.orient("session:one", "hello")
    assert orientation.index_probes.count("relation_adjacency:unavailable") == 1
    assert not any(
        probe.startswith("by_kind:relation_type") for probe in orientation.index_probes
    )


def test_orientation_entity_concept_relation_independent(runtime):
    """Entity, concept, relation, state, and event identities remain
    independently addressable; events do not become a universal wrapper."""
    orientation = runtime.orient("session:one", "hello")
    # event:greeting is an event_type, not an entity or concept.
    assert "event:greeting" in orientation.focus_refs
    # Participants are participants, not events.
    for p in orientation.participants:
        assert p.startswith("participant:")


class _ExplodingDependency:
    def __getattribute__(self, name: str):
        raise AssertionError(
            f"dependency used before projector input validation: {name}"
        )


@pytest.mark.parametrize(
    ("session_ref", "source_text", "mode", "message"),
    (
        ("s" * 257, "hello", SemanticMode.OBSERVE, "session_ref exceeds"),
        ("session:one", "x" * 16_385, SemanticMode.OBSERVE, "source_text exceeds"),
        ("session:one", "hello", "OBSERVE", "mode must be SemanticMode"),
    ),
    ids=("session-bound", "source-bound", "mode-type"),
)
def test_projector_rejects_hostile_inputs_before_tokenize_or_dependencies(
    session_ref, source_text, mode, message, monkeypatch
):
    projector = OrientationProjector(
        _ExplodingDependency(),
        _ExplodingDependency(),
        RuntimeConfig.release(),
    )

    def forbidden_tokenize(_text: str):
        raise AssertionError("invalid projector input reached tokenization")

    monkeypatch.setattr(projector, "_tokenize", forbidden_tokenize)
    with pytest.raises((TypeError, ValueError), match=message):
        projector.project(session_ref, source_text, mode=mode)


def test_projector_rejects_token_fanout_before_store_or_index_lookup() -> None:
    projector = OrientationProjector(
        _ExplodingDependency(),
        _ExplodingDependency(),
        RuntimeConfig.release(),
    )

    with pytest.raises(ValueError, match="token bound"):
        projector.project("session:one", " ".join("x" for _ in range(65)))


class _NoRelationEnumerationAuthority:
    def __init__(self, authority):
        self._authority = authority

    def __getattr__(self, name: str):
        return getattr(self._authority, name)

    def by_kind(self, kind: str):
        if kind == "relation_type":
            raise AssertionError("projection enumerated unrelated relation types")
        return self._authority.by_kind(kind)


def test_projector_does_not_enumerate_unrelated_relation_types(runtime) -> None:
    projector = OrientationProjector(
        _NoRelationEnumerationAuthority(runtime._authority),
        runtime._stores,
        runtime._config,
    )

    orientation = projector.project("session:no-relation-scan", "hello")

    assert orientation.focus_refs == ("event:greeting",)
    assert orientation.index_probes.count("relation_adjacency:unavailable") == 1
    assert all(
        not probe.startswith("by_kind:relation_type")
        for probe in orientation.index_probes
    )


class _PinnedStores:
    def __init__(self, pin):
        self._pin = pin

    def revision_pin(self):
        return self._pin


class _ObligationManager:
    def pending(self):
        return (SimpleNamespace(obligation_ref="obligation:one"),)


def test_projector_cache_key_is_exact_orientation_content_ref(runtime) -> None:
    base_projector = OrientationProjector(
        runtime._authority, runtime._stores, runtime._config
    )
    base = base_projector.project("session:cache", "hello")
    mode = base_projector.project("session:cache", "hello", mode=SemanticMode.QUERY)
    source = base_projector.project("session:cache", "say hello")
    pin = OrientationProjector(
        runtime._authority,
        _PinnedStores(replace(base.revision_pin, world_revision=9)),
        runtime._config,
    ).project("session:cache", "hello")
    obligation = OrientationProjector(
        runtime._authority,
        runtime._stores,
        runtime._config,
        obligation_manager=_ObligationManager(),
    ).project("session:cache", "hello")
    projection = OrientationProjector(
        runtime._authority,
        runtime._stores,
        runtime._config,
        focus_store=SimpleNamespace(refs=("event:other",)),
    ).project("session:cache", "hello")
    orientations = (base, mode, source, pin, obligation, projection)

    assert all(item.cache_key == item.orientation_ref for item in orientations)
    assert len({item.cache_key for item in orientations}) == len(orientations)
    assert all("cache_key" not in item.as_dict() for item in orientations)


__cemm_test_inventory__ = {
    "tests/test_orientation_projection.py::test_orientation_projector_includes_source_on_first_construction": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-projector-first-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "23fc1c6c28d84140cab8fa6af948714f5961b2864c54e2bb5189fc26707e24f3"
    },
    "tests/test_orientation_projection.py::test_orientation_records_disabled_relation_adjacency_seam": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-orientation-disabled-adjacency-seam",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "e376cd9732a3b8e65db1797d839e693f226c5debe383e35eb692b09f339f9265"
    },
    "tests/test_orientation_projection.py::test_projector_cache_key_is_exact_orientation_content_ref": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-orientation-cache-key-exact-content",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "d404bf67aea5c9b0adcbf21e93c9a5e2267cd0e121456cbf0a6686d85bd765ec"
    },
    "tests/test_orientation_projection.py::test_projector_does_not_enumerate_unrelated_relation_types": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-projector-forbids-relation-enumeration",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "9c852c4ba92524fb225a83326237e9f49bbaa8bd50d4057284b7cea5e101bcb9"
    },
    "tests/test_orientation_projection.py::test_projector_rejects_hostile_inputs_before_tokenize_or_dependencies[mode-type]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-projector-rejects-hostile-mode",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "3bb6f03f63592fb9bfd3b2fc43cb75d15f3fb323ec690620a07294c2a0389563"
    },
    "tests/test_orientation_projection.py::test_projector_rejects_hostile_inputs_before_tokenize_or_dependencies[session-bound]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-projector-rejects-hostile-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "3bb6f03f63592fb9bfd3b2fc43cb75d15f3fb323ec690620a07294c2a0389563"
    },
    "tests/test_orientation_projection.py::test_projector_rejects_hostile_inputs_before_tokenize_or_dependencies[source-bound]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-projector-rejects-hostile-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "3bb6f03f63592fb9bfd3b2fc43cb75d15f3fb323ec690620a07294c2a0389563"
    },
    "tests/test_orientation_projection.py::test_projector_rejects_token_fanout_before_store_or_index_lookup": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-projector-prebounds-token-fanout",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "28d3816149b494829e959b88fe0777677103f91c8c91cc9e1cd51fbd6a4eecd6"
    },
}
