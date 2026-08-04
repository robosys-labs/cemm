"""Tests for kind-derived semantic affordances (SemanticAffordanceIndex).

These tests verify that affordances are derived only from semantic kind,
never from surface text or ref-name spelling.  Synonyms inherit identical
affordances because they designate the same semantic target.  Unlinked refs
produce no affordances.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.affordances import (
    AffordanceProfile,
    SemanticAffordanceIndex,
)
from cemm_authoritative_hybrid.config import RuntimeConfig


# ---------------------------------------------------------------------------
# Kind-derived affordance defaults
# ---------------------------------------------------------------------------


def test_affordance_index_exposes_exact_authority_generation(
    affordance_index: SemanticAffordanceIndex, linked_authority
):
    indexed_generation = linked_authority.generation
    assert affordance_index.authority_generation == indexed_generation

    linked_authority.generation = "authority:mutated-after-indexing"
    assert affordance_index.authority_generation == indexed_generation


def test_event_type_derives_event_affordances(affordance_index):
    profiles = affordance_index.for_target("event:greeting")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "predicate" in kinds
    assert "anchor" in kinds


def test_relation_type_derives_relation_affordances(affordance_index):
    profiles = affordance_index.for_target("rel:mother_in_law")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "predicate" in kinds
    assert "anchor" in kinds


def test_concept_derives_nominal_affordances(affordance_index):
    profiles = affordance_index.for_target("concept:mother")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "anchor" in kinds


def test_entity_derives_referent_affordances(affordance_index):
    profiles = affordance_index.for_target("entity:alice")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "anchor" in kinds


def test_state_dimension_derives_state_affordances(affordance_index):
    profiles = affordance_index.for_target("dim:availability")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "predicate" in kinds


def test_state_value_derives_value_affordances(affordance_index):
    profiles = affordance_index.for_target("value:online")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "anchor" in kinds


def test_capability_derives_capability_affordances(affordance_index):
    profiles = affordance_index.for_target("cap:query")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "predicate" in kinds or "reference" in kinds


def test_participant_derives_referent_and_reference(affordance_index):
    profiles = affordance_index.for_target("participant:system")
    assert len(profiles) >= 1
    kinds = set()
    for p in profiles:
        kinds.update(p.contribution_kinds)
    assert "anchor" in kinds


# ---------------------------------------------------------------------------
# Synonym inheritance
# ---------------------------------------------------------------------------


def test_synonyms_inherit_identical_affordances(affordance_index):
    mother = affordance_index.for_target("concept:mother")
    assert mother == affordance_index.for_designation("progenitor")


def test_designation_returns_target_affordances(affordance_index):
    profiles = affordance_index.for_designation("hello")
    target_profiles = affordance_index.for_target("event:greeting")
    assert profiles == target_profiles


def test_unknown_designation_returns_empty(affordance_index):
    assert affordance_index.for_designation("zorbulate") == ()


# ---------------------------------------------------------------------------
# Ref-name spelling cannot create affordances
# ---------------------------------------------------------------------------


def test_ref_name_cannot_create_affordance(affordance_index):
    assert affordance_index.for_unlinked_ref("event:learn") == ()


def test_unlinked_ref_returns_empty(affordance_index):
    assert affordance_index.for_unlinked_ref("concept:nonexistent") == ()


def test_linked_ref_returns_affordances(affordance_index):
    profiles = affordance_index.for_unlinked_ref("event:greeting")
    assert len(profiles) >= 1


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------


def test_affordances_bounded_by_config(affordance_index):
    config = RuntimeConfig.release()
    # Every target's affordance count is within the configured bound.
    for ref in ("event:greeting", "rel:mother_in_law", "concept:mother"):
        profiles = affordance_index.for_target(ref)
        assert len(profiles) <= config.max_affordances_per_target


# ---------------------------------------------------------------------------
# Frozen dataclass
# ---------------------------------------------------------------------------


def test_affordance_profile_is_frozen():
    profile = AffordanceProfile(
        target_ref="concept:test",
        contribution_kinds=("anchor",),
        input_ports=("role:subject",),
        output_ports=("role:target",),
        role_candidates=("role:subject",),
        frame_ref=None,
    )
    with pytest.raises(Exception):
        profile.target_ref = "concept:other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Frame refinement
# ---------------------------------------------------------------------------


def test_frame_refines_event_type_affordances(affordance_index):
    """Reviewed frame atoms may refine default affordances for event types."""
    profiles = affordance_index.for_target("event:greeting")
    # The frame for greeting should contribute role candidates.
    all_roles = set()
    for p in profiles:
        all_roles.update(p.role_candidates)
    assert "role:actor" in all_roles or "role:addressee" in all_roles


def test_frame_ref_is_set_for_reviewed_frames(affordance_index):
    """Profiles derived from reviewed frames carry a frame_ref."""
    profiles = affordance_index.for_target("event:greeting")
    has_frame = any(p.frame_ref is not None for p in profiles)
    assert has_frame

__cemm_test_inventory__ = {'tests/test_affordances.py::test_affordance_index_exposes_exact_authority_generation': {'activation_phase': 'R1',
                                                                                         'assertion_ref': 'assertion:r1-affordances-test-affordance-index-exposes-exact-authority-generation',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R1-Task-9',
                                                                                         'owner_ref': 'runtime-path',
                                                                                         'source_ast_sha256': '7a2a20412dd3a76532ac4ac8f6eaabcfa2cf77e92f87e6a410cc5d1a25320ae6'}}
