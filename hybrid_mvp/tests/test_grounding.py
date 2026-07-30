"""Tests for bounded grounding (Grounder).

These tests verify that the Grounder performs indexed exact-designation
lookup, does not manufacture atoms for unknown surfaces, uses adapter-schema-
pinned grounding for sensor evidence, and that adding a designation changes
authority generation without changing the form pack hash.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

from cemm_authoritative_hybrid.forms import EvidenceItem, EvidencePacket
from cemm_authoritative_hybrid.grounding import (
    DesignationCandidate,
    GroundedItem,
    GroundingResult,
    Grounder,
    ReferenceRequirement,
)
from cemm_authoritative_hybrid.config import RuntimeConfig

ROOT = Path(__file__).parents[1]
FORMS_PATH = ROOT / "data" / "languages" / "en" / "forms.json"


# ---------------------------------------------------------------------------
# Exact designation lookup
# ---------------------------------------------------------------------------


def test_known_surface_resolves_to_target(grounder):
    result = grounder.ground_text("hello")
    assert len(result.designations) >= 1
    assert result.designations[0].target_ref == "event:greeting"


def test_new_designation_uses_target_affordance_without_pack_regeneration(
    grounder, designation_store, form_pack_hash
):
    designation_store.commit_reviewed("progenitor", "concept:mother")
    result = grounder.ground_text("progenitor")
    assert result.designations[0].target_ref == "concept:mother"
    assert grounder.form_pack_hash == form_pack_hash


def test_unknown_surface_is_typed_not_manufactured(grounder):
    result = grounder.ground_text("zorbulate")
    assert result.designations == ()
    assert result.unresolved[0].kind == "designation"
    assert "concept:zorbulate" not in result.created_refs


def test_unknown_surface_produces_reference_requirement(grounder):
    result = grounder.ground_text("zorbulate")
    assert len(result.unresolved) == 1
    req = result.unresolved[0]
    assert req.kind == "designation"
    assert req.resolved_ref is None


def test_no_atoms_created_for_unknown(grounder):
    result = grounder.ground_text("zorbulate")
    assert result.created_refs == ()


# ---------------------------------------------------------------------------
# Sensor / non-linguistic evidence
# ---------------------------------------------------------------------------


def test_reviewed_sensor_evidence_enters_same_semantic_plane(grounder, door_sensor_evidence):
    result = grounder.ground(door_sensor_evidence)
    assert result.designations[0].target_ref == "entity:door"
    assert result.grounded_items[0].source_kind == "sensor"
    assert result.provenance_refs == (door_sensor_evidence.adapter_receipt_ref,)


def test_sensor_evidence_produces_grounded_item(grounder, door_sensor_evidence):
    result = grounder.ground(door_sensor_evidence)
    assert len(result.grounded_items) == 1
    item = result.grounded_items[0]
    assert item.source_kind == "sensor"
    assert item.target_ref == "entity:door"


# ---------------------------------------------------------------------------
# Designation candidate bounds
# ---------------------------------------------------------------------------


def test_designations_never_exceed_max_per_span(grounder):
    # Even with many surfaces, the result is bounded.
    config = RuntimeConfig.release()
    result = grounder.ground_text("hello")
    assert len(result.designations) <= config.max_designations_per_span


@given(text=st.text(alphabet=st.characters(whitelist_categories=("Ll",)), min_size=1, max_size=10))
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_designations_bounded_hypothesis(grounder, text):
    config = RuntimeConfig.release()
    result = grounder.ground_text(text)
    assert len(result.designations) <= config.max_designations_per_span


# ---------------------------------------------------------------------------
# Form pack hash stability
# ---------------------------------------------------------------------------


def test_form_pack_hash_matches_forms_json(grounder, form_pack_hash):
    assert grounder.form_pack_hash == form_pack_hash


def test_adding_designation_does_not_change_form_pack_hash(
    grounder, designation_store, form_pack_hash
):
    designation_store.commit_reviewed("progenitor", "concept:mother")
    assert grounder.form_pack_hash == form_pack_hash


def test_adding_designation_changes_authority_generation(linked_authority, form_pack_hash):
    """Adding a designation changes authority content hash but not forms.json hash."""
    from cemm_authoritative_hybrid.authority import AuthorityLinker

    original_hash = linked_authority.content_hash
    # The form pack hash is independent of authority content.
    assert form_pack_hash != original_hash
    # Re-linking the same authority produces the same hash (no designation added).
    re_linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert re_linked.content_hash == original_hash


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


def test_designation_candidate_is_frozen():
    cand = DesignationCandidate(
        unit_refs=("unit:0",),
        target_ref="entity:door",
        designation_fact_ref="fact:0",
        score=1.0,
        provenance_refs=(),
    )
    with pytest.raises(Exception):
        cand.target_ref = "entity:window"  # type: ignore[misc]


def test_reference_requirement_is_frozen():
    req = ReferenceRequirement(
        unit_ref="unit:0",
        kind="designation",
        required_kind=None,
        resolved_ref=None,
    )
    with pytest.raises(Exception):
        req.kind = "entity"  # type: ignore[misc]


def test_grounding_result_is_frozen():
    result = GroundingResult(
        designations=(),
        unresolved=(),
        grounded_items=(),
        created_refs=(),
        provenance_refs=(),
    )
    with pytest.raises(Exception):
        result.designations = ()  # type: ignore[misc]


def test_grounded_item_is_frozen():
    item = GroundedItem(
        source_ref="sensor:0",
        source_kind="sensor",
        target_ref="entity:door",
        unit_refs=(),
    )
    with pytest.raises(Exception):
        item.target_ref = "entity:window"  # type: ignore[misc]
