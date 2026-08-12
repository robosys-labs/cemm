"""Tests for the linked semantic authority (AuthorityLinker).

These tests verify that linking rejects missing targets, duplicate owners,
and internal-ref lexicalization, and that the linked authority produces
stable content and model-compatibility hashes with bounded indexes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.authority import (
    AuthorityLinker,
    AuthorityLinkError,
    LinkedAuthority,
)

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    "tests/test_authority_linker.py::test_transition_index_selects_exact_event_dimension_and_value": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-transition-index-selects-exact-value",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R4-Final-Admission-Closeout",
        "source_ast_sha256": "0503f7c4eb687c5201ee94bc431bf5b5c08757c52684c408ed48e8a1b7c5341e",
    },
    "tests/test_authority_linker.py::test_transition_index_does_not_collapse_distinct_target_values": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-transition-index-preserves-distinct-values",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R4-Final-Admission-Closeout",
        "source_ast_sha256": "d9cfbd87f956f4153cb70a3482599a0efc96ebfc53a82dc21de18176c55055a0",
    },
}


# ---------------------------------------------------------------------------
# Step 1: atomic-link tests (must fail before implementation)
# ---------------------------------------------------------------------------


def test_missing_target_rejects_entire_generation(authority_factory):
    bundle = authority_factory(designation_target="concept:missing")
    with pytest.raises(AuthorityLinkError, match="missing target"):
        AuthorityLinker().link(bundle.manifest)
    assert bundle.store.active_generation is None


def test_internal_ref_is_not_automatically_a_surface(linked_authority):
    assert linked_authority.designations.for_surface("semantic store", "en") == ()


def test_exactly_one_owner_per_atom(authority_factory):
    with pytest.raises(AuthorityLinkError, match="duplicate owner"):
        AuthorityLinker().link(authority_factory(duplicate_atom="event:greeting").manifest)


# ---------------------------------------------------------------------------
# Link-path and hash stability
# ---------------------------------------------------------------------------


def test_link_path_returns_linked_authority():
    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert isinstance(linked, LinkedAuthority)
    assert linked.content_hash.startswith("authority-content:")
    assert linked.model_compatibility_hash.startswith("authority-compat:")
    assert linked.generation == "authority-v1-2026-07-29"


def test_repeated_link_produces_same_hashes():
    a = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    b = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert a.content_hash == b.content_hash
    assert a.model_compatibility_hash == b.model_compatibility_hash


def test_content_and_compat_hashes_differ():
    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert linked.content_hash != linked.model_compatibility_hash


# ---------------------------------------------------------------------------
# Designation index
# ---------------------------------------------------------------------------


def test_designation_index_resolves_surfaces(linked_authority):
    targets = linked_authority.designations.for_surface("hello", "en")
    assert "event:greeting" in targets


def test_designation_index_resolves_targets(linked_authority):
    surfaces = linked_authority.designations.for_target("event:greeting", "en")
    assert "hello" in surfaces
    assert "hi" in surfaces


def test_designation_index_empty_for_unknown_surface(linked_authority):
    assert linked_authority.designations.for_surface("nonexistent", "en") == ()


def test_designation_index_empty_for_unknown_target(linked_authority):
    assert linked_authority.designations.for_target("entity:nonexistent", "en") == ()


# ---------------------------------------------------------------------------
# Atoms and kinds
# ---------------------------------------------------------------------------


def test_atoms_are_reviewed(linked_authority):
    for ref, atom in linked_authority.atoms.items():
        assert atom.reviewed is True


def test_kind_index_is_bounded(linked_authority):
    participants = linked_authority.by_kind("participant")
    assert "participant:user" in participants
    assert "participant:system" in participants
    # No telescope entity
    assert "entity:telescope" not in linked_authority.atoms


def test_all_atoms_have_valid_kinds(linked_authority):
    valid_kinds = {
        "participant", "entity", "concept", "label_type", "relation_type",
        "state_dimension", "state_value", "event_type", "capability",
        "permission", "adapter",
    }
    for atom in linked_authority.atoms.values():
        assert atom.kind in valid_kinds


# ---------------------------------------------------------------------------
# Event signatures, rules, operator roles
# ---------------------------------------------------------------------------


def test_event_signatures_built(linked_authority):
    assert "event:greeting" in linked_authority.event_signatures
    sig = linked_authority.event_signatures["event:greeting"]
    assert sig.event_type == "event:greeting"
    assert len(sig.roles) == 2


def test_event_signature_index_bounded(linked_authority):
    sig = linked_authority.by_event_signature("event:set_state")
    assert sig is not None
    assert "cap:set_state" in sig.required_capabilities


def test_rules_built(linked_authority):
    assert "rule:mother-in-law-implies-partner-exists" in linked_authority.rules
    rule = linked_authority.rules["rule:mother-in-law-implies-partner-exists"]
    assert rule.reviewed is True
    assert len(rule.antecedent) == 1
    assert len(rule.consequent) == 1


def test_operator_roles_present(linked_authority):
    for op in ("op:designation", "op:type", "op:relation", "op:state", "op:event"):
        assert op in linked_authority.operator_roles
        roles = linked_authority.operator_roles[op]
        assert isinstance(roles, list)
        assert len(roles) >= 2


# ---------------------------------------------------------------------------
# State dimensions and value dimensions
# ---------------------------------------------------------------------------


def test_value_dimensions_mapped(linked_authority):
    assert linked_authority.value_dimensions["value:online"] == "dim:availability"
    assert linked_authority.value_dimensions["value:married"] == "dim:marital_status"


def test_state_dimension_index_bounded(linked_authority):
    availability_values = linked_authority.by_state_dimension("dim:availability")
    assert "value:online" in availability_values
    assert "value:offline" in availability_values


def test_transition_index_selects_exact_event_dimension_and_value(linked_authority):
    transition = linked_authority.transition_for(
        "event:set_state", "dim:availability", "value:online"
    )
    assert transition is not None
    assert transition["transition_ref"] == "transition:set_availability_online"


def test_transition_index_does_not_collapse_distinct_target_values(linked_authority):
    online = linked_authority.transition_for(
        "event:set_state", "dim:availability", "value:online"
    )
    offline = linked_authority.transition_for(
        "event:set_state", "dim:availability", "value:offline"
    )
    assert online is not None and offline is not None
    assert online["transition_ref"] != offline["transition_ref"]


# ---------------------------------------------------------------------------
# Capabilities, permissions, adapters
# ---------------------------------------------------------------------------


def test_capabilities_built(linked_authority):
    caps = linked_authority.capabilities.get("participant:system", [])
    assert "cap:query" in caps
    assert "cap:respond" in caps
    assert "cap:learn_alias" in caps
    assert "cap:set_state" in caps


def test_permissions_built(linked_authority):
    perm_refs = [p[1] for p in linked_authority.permissions]
    assert "permission:write_alias" in perm_refs
    assert "permission:set_state" in perm_refs


def test_adapters_built(linked_authority):
    assert "adapter:memory" in linked_authority.adapters
    assert "adapter:state" in linked_authority.adapters


# ---------------------------------------------------------------------------
# Hash mismatch rejection
# ---------------------------------------------------------------------------


def test_owner_hash_mismatch_rejects(authority_factory):
    with pytest.raises(AuthorityLinkError, match="hash mismatch"):
        AuthorityLinker().link(authority_factory(corrupt_hash=True).manifest)
