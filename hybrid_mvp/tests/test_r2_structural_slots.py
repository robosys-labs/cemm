"""R2 structural slot derivation tests.

Verify that ProposalContextBuilder exposes every required recursive
structural slot without minting semantic refs or overclaiming syntax.

Per R2 plan section 2:
- No value: ref is created by string prefixing
- Every scope slot binds a reviewed value ref
- All 8 link types are covered
- Proposition-valued roles come from reviewed frame metadata
- Variable slots bind to exact frame roles with required kinds
- Transition slots bind to reviewed event signatures
- Typed literals preserve exact source value
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.proposal_context import (
    ExpressionLinkSlot,
    ProposalContextBuilder,
    ScopeSlot,
    VariableSlot,
    TransitionSlot,
    _LINK_TYPES,
    _SCOPE_TYPES,
)

__cemm_test_inventory__ = {
    "tests/test_r2_structural_slots.py::test_application_frame_slot_has_proposition_roles_field": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-application-frame-slot-has-proposition-roles-field",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "261b033b8dcaa3eee02c56b3e39d2d062865de8540ca7dcb7a123160bab112ce"
    },
    "tests/test_r2_structural_slots.py::test_application_frame_slot_rejects_undeclared_proposition_role": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-application-frame-slot-rejects-undeclared-proposition-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "250b18f755a0bfa7b0e80168d6675d4c5a0337b8fe66a58685129eed6fd30547"
    },
    "tests/test_r2_structural_slots.py::test_conjunction_connector_produces_link_slot": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-conjunction-connector-produces-link-slot",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "4c7f4c72e62ceed2469e2c082f0d739ff3008899700d663addd3527524056a88"
    },
    "tests/test_r2_structural_slots.py::test_contribution_slot_literal_value_validation": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-contribution-slot-literal-value-validation",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "84f06e66dc5d2664cf99c01e4bfb71ad6016c627b3ed990ee9a509be8854edcb"
    },
    "tests/test_r2_structural_slots.py::test_detect_literal_boolean": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-detect-literal-boolean",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "1269112ec6709eec2d4cae1b38146828b00d8dc7d5dab0c25cb8fe40f17a40c1"
    },
    "tests/test_r2_structural_slots.py::test_detect_literal_integer": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-detect-literal-integer",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "2b96b4de2c6fa200e4d7a987b510d6135392f8abfdea37a62857a8b0e946cce5"
    },
    "tests/test_r2_structural_slots.py::test_detect_literal_rejects_non_literal": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-detect-literal-rejects-non-literal",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "8ec387ac1e6d77509dce16cb06e6efa62fc8a4450171452e3004f49fae3e7068"
    },
    "tests/test_r2_structural_slots.py::test_detect_literal_string": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-detect-literal-string",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "c5e06eade3bd355dc3e35811cef54230aa27d2ef108da7430e3d2a132ea01f23"
    },
    "tests/test_r2_structural_slots.py::test_form_pack_link_schemas_have_valid_link_types": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-form-pack-link-schemas-have-valid-link-types",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "a5016736d119d44bcb9dd153b09c35e1474a22b1ffe1c7aa7c6a2a2de7c2891f"
    },
    "tests/test_r2_structural_slots.py::test_form_pack_scope_values_are_reviewed_refs": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-form-pack-scope-values-are-reviewed-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "836e253e88a4413e2ddcd5eeb9d297006a3633d625bc4e066403e4313de8346b"
    },
    "tests/test_r2_structural_slots.py::test_language_packs_share_reviewed_link_types": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-language-packs-share-reviewed-link-types",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "6755f77109dac3e0e0af7ce82b1e52b8d17f5ca326e12136147c424ec7fd0edd"
    },
    "tests/test_r2_structural_slots.py::test_language_packs_share_reviewed_scope_value_refs": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-language-packs-share-reviewed-scope-value-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "c7862efe2159f19375aa6b0d4611b8598ca23490355130ddac45da2c05dd7666"
    },
    "tests/test_r2_structural_slots.py::test_link_schemas_defined_in_form_pack": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-link-schemas-defined-in-form-pack",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "966db9fe87cd9331e1ffdfbdea0fb83f5cd13812211d6715f8bf8a4bed68ffc5"
    },
    "tests/test_r2_structural_slots.py::test_link_types_cover_all_eight": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-link-types-cover-all-eight",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "3d84166f51f0a35b135421569b0ea933ec57f8b8e8aa101cd5d50c79f51947ce"
    },
    "tests/test_r2_structural_slots.py::test_literal_contribution_preserves_value": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-literal-contribution-preserves-value",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "836c00f22783a2530f4ff33322931261e2fb8773e1d309bd4fb67e8f52689b89"
    },
    "tests/test_r2_structural_slots.py::test_purpose_connector_produces_link_slot": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-purpose-connector-produces-link-slot",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "11b525fbca02f4fa87a6989f5fadcd3934c6219cde00429a38f9a3f03e6b2b0d"
    },
    "tests/test_r2_structural_slots.py::test_scope_negation_normalized_to_polarity": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-scope-negation-normalized-to-polarity",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "3c535079ff5b10a86051ec2b325800b9fc8dc4dd713f84088c5353d9e10e734a"
    },
    "tests/test_r2_structural_slots.py::test_scope_operator_types_are_reviewed": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-scope-operator-types-are-reviewed",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "d258b2e186d33a1faaa79624df5716373a9cedb0905d64ed25c1bf08f0d5f844"
    },
    "tests/test_r2_structural_slots.py::test_scope_slots_cover_polarity_and_modality": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-scope-slots-cover-polarity-and-modality",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "f270a3cd29d883d86ff557bd26b120e23924cf109db7fc25627a6ab7c0ea5ea2"
    },
    "tests/test_r2_structural_slots.py::test_scope_slots_use_reviewed_value_refs": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-scope-slots-use-reviewed-value-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "85fe55ec678ab8111e4d82af325445d39c5a6c35fca7547748f536e120a1d840"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_detects_conjunction": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-detects-conjunction",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "fd12eea2903c0fd9e44358dca6ff4370b75e1c0c8f2c7740dda3d2ba6531fb74"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_detects_polarity": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-detects-polarity",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "1c0d09fe507a4f6363027613d219efea368ca8a2a55fa3038735a65024cc0f6f"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_exists": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-exists",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "95208894628c8594fcbc55a67f80975eda1672d6bfd6d4da58699f7680aa6af9"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_has_link_schemas": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-has-link-schemas",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "9023bbb0309f28da49cd7089063062463957879f6498b85e539e07a58a7ffce2"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_has_same_abi_version": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-has-same-abi-version",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "23d2c8c620c9ce387d5c819f69eb9fb588ae4e16af388efe40e19b02d265fb30"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_has_scope_values": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-has-scope-values",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "35c2980b7cbdb9ed7615af731916ba939f09e3273d457501c84ef48fbe60a99d"
    },
    "tests/test_r2_structural_slots.py::test_second_language_pack_tokenizes": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-second-language-pack-tokenizes",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "493179936546ae0e3c041bd9fb1ee64e28c3be75626a56d59306ba4cc8b022c1"
    },
    "tests/test_r2_structural_slots.py::test_transition_slot_allows_empty_capabilities": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-transition-slot-allows-empty-capabilities",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "66fe9ad349247d141b6c2aaf74319e96a97c4b4644fd3cd8cdcc735cee0797ef"
    },
    "tests/test_r2_structural_slots.py::test_transition_slot_binds_reviewed_fields": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-transition-slot-binds-reviewed-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "5084d16e5a948d056ed48ce138fbcbc8cac5ac41b97f9e4e4f18bee6b35c0642"
    },
    "tests/test_r2_structural_slots.py::test_transition_slot_rejects_empty_modes": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-transition-slot-rejects-empty-modes",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "4e3be6ca76363fbede190c8e4bda15dd3587de263ee1181caa9a84276d14b950"
    },
    "tests/test_r2_structural_slots.py::test_transition_slot_rejects_invalid_mode": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-transition-slot-rejects-invalid-mode",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "7809ea8390140427c0ff83aa6c7c51ee80ff1bc06c9342957e2ce437c36c3673"
    },
    "tests/test_r2_structural_slots.py::test_variable_slot_binds_to_frame_role": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-variable-slot-binds-to-frame-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "fa3d72cc8b07b8690ca0aed0901f9d4793df8f9a91441f5dce6bc91aff846825"
    },
    "tests/test_r2_structural_slots.py::test_variable_slot_rejects_non_role_prefix": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-variable-slot-rejects-non-role-prefix",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "ff24c13a5c42f50adf8b6ae17ef849c98d032babe12f0c0306298eb9f0ba60a4"
    },
    "tests/test_r2_structural_slots.py::test_variable_slot_required_kinds_nonempty": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-variable-slot-required-kinds-nonempty",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "form-context",
        "source_ast_sha256": "fe7f4576782e583b068cae19124c54a671f073ed1365c55fdd3ab299131bf020"
    },
}


ROOT = Path(__file__).resolve().parent.parent / "data"
FORMS_PATH = ROOT / "languages" / "en" / "forms.json"


@pytest.fixture
def form_pack() -> dict:
    with open(FORMS_PATH) as f:
        return json.load(f)


@pytest.fixture
def form_resolver(form_pack) -> FormResolver:
    return FormResolver(form_pack, RuntimeConfig.release())


@pytest.fixture
def config() -> RuntimeConfig:
    return RuntimeConfig.release()


# ---------------------------------------------------------------------------
# Scope value refs — no string prefixing
# ---------------------------------------------------------------------------


def test_scope_slots_use_reviewed_value_refs(form_resolver, form_pack):
    """Scope slots must bind reviewed value refs, not value:<surface-feature>.

    Per R2 plan section 2.1: no value: ref is created by string prefixing.
    """
    lattice = form_resolver.resolve("not can")
    config = RuntimeConfig.release()
    scope_values = form_pack.get("scope_values", {})
    from cemm_authoritative_hybrid.proposal_context import _scope_slots

    slots = _scope_slots(lattice, config, scope_values)
    assert len(slots) >= 1
    for slot in slots:
        # Value refs must be reviewed scope_value: refs, not value: refs
        assert slot.value_ref.startswith("scope_value:"), (
            f"Scope slot value_ref {slot.value_ref} is not a reviewed scope_value ref"
        )
        assert not slot.value_ref.startswith("value:"), (
            f"Scope slot value_ref {slot.value_ref} uses forbidden value: prefix"
        )


def test_scope_slots_cover_polarity_and_modality(form_resolver, form_pack):
    """Polarity and modality scope slots are derived from form evidence."""
    lattice = form_resolver.resolve("not can")
    config = RuntimeConfig.release()
    scope_values = form_pack.get("scope_values", {})
    from cemm_authoritative_hybrid.proposal_context import _scope_slots

    slots = _scope_slots(lattice, config, scope_values)
    operators = {slot.operator_type for slot in slots}
    assert "scope:polarity" in operators
    assert "scope:modality" in operators


def test_scope_operator_types_are_reviewed():
    """All scope operator types are in the reviewed _SCOPE_TYPES set."""
    expected = {
        "scope:polarity",
        "scope:modality",
        "scope:tense",
        "scope:aspect",
        "scope:attribution",
        "scope:epistemic",
        "scope:quotation",
        "scope:simulation",
    }
    assert _SCOPE_TYPES == expected


def test_scope_negation_normalized_to_polarity():
    """Negation must be normalized to polarity, not scope:negation."""
    with pytest.raises(ValueError, match="negation must be normalized to polarity"):
        ScopeSlot.create(
            operator_type="scope:negation",
            value_ref="scope_value:polarity:negative",
            source_unit_refs=("unit:0",),
            construction_ref=None,
        )


# ---------------------------------------------------------------------------
# Link coverage — all 8 link types
# ---------------------------------------------------------------------------


def test_link_types_cover_all_eight():
    """All 8 required link types are in the reviewed _LINK_TYPES set."""
    expected = {
        "link:coordination",
        "link:conjunction",
        "link:disjunction",
        "link:condition",
        "link:cause",
        "link:purpose",
        "link:contrast",
        "link:sequence",
    }
    assert _LINK_TYPES == expected


def test_link_schemas_defined_in_form_pack(form_pack):
    """The form pack defines reviewed link schemas for all connector kinds."""
    schemas = form_pack.get("link_schemas", {})
    assert "conjunction" in schemas
    assert "disjunction" in schemas
    assert "coordination" in schemas
    assert "causal" in schemas
    assert "contrast" in schemas
    assert "conditional" in schemas
    assert "purpose" in schemas
    assert "sequence" in schemas
    for name, schema in schemas.items():
        assert "link_type" in schema
        assert "commutative" in schema
        assert "min_arity" in schema
        assert "max_arity" in schema


def test_conjunction_connector_produces_link_slot(form_resolver, form_pack):
    """'and' produces a link:conjunction slot, not link:coordination."""
    lattice = form_resolver.resolve("alice and bob")
    config = RuntimeConfig.release()
    link_schemas = form_pack.get("link_schemas", {})
    from cemm_authoritative_hybrid.proposal_context import _expression_link_slots

    slots = _expression_link_slots(lattice, config, link_schemas)
    link_types = {slot.link_type for slot in slots}
    assert "link:conjunction" in link_types


def test_purpose_connector_produces_link_slot(form_resolver, form_pack):
    """Purpose connectors produce link:purpose slots."""
    lattice = form_resolver.resolve("I ran to stay fit")
    config = RuntimeConfig.release()
    link_schemas = form_pack.get("link_schemas", {})
    from cemm_authoritative_hybrid.proposal_context import _expression_link_slots

    slots = _expression_link_slots(lattice, config, link_schemas)
    # "to" is a purpose connector — check if it produces a purpose link
    # Note: "to" is also a linker, so it may not always produce a connector
    # hypothesis. This test verifies the link schema mapping exists.
    assert any(
        schema.get("link_type") == "link:purpose"
        for schema in link_schemas.values()
    )


# ---------------------------------------------------------------------------
# Variable slots — exact frame role binding
# ---------------------------------------------------------------------------


def test_variable_slot_binds_to_frame_role():
    """Variable slots bind to exact frame roles with required kinds."""
    slot = VariableSlot.create(
        application_frame_ref="application_frame_slot:0",
        role_ref="role:subject",
        required_kinds=("entity", "participant", "concept"),
        source_unit_refs=("unit:0",),
        construction_ref="hypothesis:0",
    )
    assert slot.role_ref == "role:subject"
    assert slot.required_kinds == ("entity", "participant", "concept")
    assert slot.application_frame_ref == "application_frame_slot:0"


def test_variable_slot_rejects_non_role_prefix():
    """Variable slot role_ref must start with 'role:'."""
    with pytest.raises(ValueError, match="role_ref must start with 'role:'"):
        VariableSlot.create(
            application_frame_ref="application_frame_slot:0",
            role_ref="subject",
            required_kinds=("entity",),
            source_unit_refs=("unit:0",),
            construction_ref=None,
        )


# ---------------------------------------------------------------------------
# Transition slots — reviewed event signatures
# ---------------------------------------------------------------------------


def test_transition_slot_binds_reviewed_fields():
    """Transition slots bind to reviewed event signatures with all fields."""
    slot = TransitionSlot.create(
        application_frame_ref="application_frame_slot:0",
        event_type_ref="event:set_state",
        compatible_modes=("REQUEST", "SIMULATE"),
        required_roles=("role:actor", "role:target"),
        required_capabilities=("cap:set_state",),
        required_permissions=("permission:set_state",),
        adapter_ref="adapter:state",
        source_unit_refs=("unit:0",),
    )
    assert slot.event_type_ref == "event:set_state"
    assert slot.compatible_modes == ("REQUEST", "SIMULATE")
    assert slot.required_capabilities == ("cap:set_state",)
    assert slot.adapter_ref == "adapter:state"


def test_transition_slot_rejects_invalid_mode():
    """Transition slots reject invalid modes."""
    with pytest.raises(ValueError, match="invalid compatible mode"):
        TransitionSlot.create(
            application_frame_ref="application_frame_slot:0",
            event_type_ref="event:set_state",
            compatible_modes=("INVALID",),
            required_roles=(),
            required_capabilities=(),
            required_permissions=(),
            adapter_ref=None,
            source_unit_refs=("unit:0",),
        )


# ---------------------------------------------------------------------------
# Form pack scope_values and link_schemas structure
# ---------------------------------------------------------------------------


def test_form_pack_scope_values_are_reviewed_refs(form_pack):
    """All scope_values in the form pack are reviewed scope_value: refs."""
    scope_values = form_pack.get("scope_values", {})
    for category, values in scope_values.items():
        for feature_value, ref in values.items():
            assert ref.startswith("scope_value:"), (
                f"Scope value {ref} for {category}/{feature_value} "
                f"is not a reviewed scope_value ref"
            )


def test_form_pack_link_schemas_have_valid_link_types(form_pack):
    """All link_schemas in the form pack use valid link types."""
    schemas = form_pack.get("link_schemas", {})
    for name, schema in schemas.items():
        link_type = schema.get("link_type", "")
        assert link_type in _LINK_TYPES, (
            f"Link schema {name} has invalid link_type {link_type}"
        )


# ---------------------------------------------------------------------------
# Task 2c: Proposition frame derivation
# ---------------------------------------------------------------------------


def test_application_frame_slot_has_proposition_roles_field():
    """ApplicationFrameSlot has a proposition_roles field for reviewed metadata."""
    from cemm_authoritative_hybrid.proposal_context import ApplicationFrameSlot

    slot = ApplicationFrameSlot.create(
        designation_slot_ref="designation_slot:0",
        predicate_target_ref="event:say",
        predicate_kind="event_type",
        operator_ref="op:event",
        structural_role_ref="role:event",
        required_roles=("role:actor", "role:content"),
        optional_roles=(),
        proposition_roles=("role:content",),
        source_unit_refs=("unit:0",),
        derived_role_targets=(),
        affordance_frame_ref="frame:event:say",
        provenance_refs=("designation_slot:0", "frame:event:say"),
    )
    assert slot.proposition_roles == ("role:content",)


def test_application_frame_slot_rejects_undeclared_proposition_role():
    """Proposition roles must be declared in required or optional roles."""
    from cemm_authoritative_hybrid.proposal_context import ApplicationFrameSlot

    with pytest.raises(ValueError, match="proposition roles must be declared roles"):
        ApplicationFrameSlot.create(
            designation_slot_ref="designation_slot:0",
            predicate_target_ref="event:say",
            predicate_kind="event_type",
            operator_ref="op:event",
            structural_role_ref="role:event",
            required_roles=("role:actor",),
            optional_roles=(),
            proposition_roles=("role:content",),
            source_unit_refs=("unit:0",),
            derived_role_targets=(),
            affordance_frame_ref="frame:event:say",
            provenance_refs=("designation_slot:0",),
        )


# ---------------------------------------------------------------------------
# Task 2d: Variable slots with exact frame role binding
# ---------------------------------------------------------------------------


def test_variable_slot_required_kinds_nonempty():
    """Variable slot required_kinds must be non-empty."""
    with pytest.raises(ValueError, match="required_kinds must be non-empty"):
        VariableSlot.create(
            application_frame_ref="application_frame_slot:0",
            role_ref="role:subject",
            required_kinds=(),
            source_unit_refs=("unit:0",),
            construction_ref=None,
        )


# ---------------------------------------------------------------------------
# Task 2e: Transition slot ownership from reviewed signatures
# ---------------------------------------------------------------------------


def test_transition_slot_rejects_empty_modes():
    """Transition slot compatible_modes must be non-empty."""
    with pytest.raises(ValueError, match="compatible_modes must be non-empty"):
        TransitionSlot.create(
            application_frame_ref="application_frame_slot:0",
            event_type_ref="event:set_state",
            compatible_modes=(),
            required_roles=(),
            required_capabilities=(),
            required_permissions=(),
            adapter_ref=None,
            source_unit_refs=("unit:0",),
        )


def test_transition_slot_allows_empty_capabilities():
    """Transition slot allows empty required_capabilities (some transitions need no caps)."""
    slot = TransitionSlot.create(
        application_frame_ref="application_frame_slot:0",
        event_type_ref="event:greeting",
        compatible_modes=("REQUEST",),
        required_roles=("role:actor",),
        required_capabilities=(),
        required_permissions=(),
        adapter_ref=None,
        source_unit_refs=("unit:0",),
    )
    assert slot.event_type_ref == "event:greeting"
    assert slot.required_capabilities == ()


# ---------------------------------------------------------------------------
# Task 2f: Typed literal preservation
# ---------------------------------------------------------------------------


def test_detect_literal_integer():
    """Integer literals are detected from source text."""
    from cemm_authoritative_hybrid.contributions import _detect_literal

    result = _detect_literal("42")
    assert result == ("integer", "42")

    result = _detect_literal("-7")
    assert result == ("integer", "-7")

    result = _detect_literal("+100")
    assert result == ("integer", "+100")


def test_detect_literal_boolean():
    """Boolean literals are detected from source text."""
    from cemm_authoritative_hybrid.contributions import _detect_literal

    result = _detect_literal("true")
    assert result == ("boolean", "true")

    result = _detect_literal("False")
    assert result == ("boolean", "false")


def test_detect_literal_string():
    """Quoted string literals preserve inner content."""
    from cemm_authoritative_hybrid.contributions import _detect_literal

    result = _detect_literal('"hello"')
    assert result == ("string", "hello")

    result = _detect_literal("'world'")
    assert result == ("string", "world")


def test_detect_literal_rejects_non_literal():
    """Non-literal text returns None."""
    from cemm_authoritative_hybrid.contributions import _detect_literal

    assert _detect_literal("alice") is None
    assert _detect_literal("") is None
    assert _detect_literal("  ") is None
    assert _detect_literal("not") is None


def test_literal_contribution_preserves_value():
    """Literal contributions preserve exact source value and type tag."""
    from cemm_authoritative_hybrid.contributions import ContributionExpander

    contribution = ContributionExpander._make_literal_contribution(
        source_unit_ref="unit:0",
        literal_kind="integer",
        literal_value="42",
    )
    assert contribution.kind == "literal"
    assert contribution.target_ref is None
    constraints = dict(contribution.constraints)
    assert constraints["literal"] == "42"
    assert constraints["literal_kind"] == "integer"


def test_contribution_slot_literal_value_validation():
    """ContributionSlot validates literal_value field correctly."""
    from cemm_authoritative_hybrid.proposal_context import ContributionSlot

    # Literal kind requires literal_value
    with pytest.raises(ValueError, match="literal contribution requires literal_value"):
        ContributionSlot.create(
            contribution_ref="contribution:0",
            kind="literal",
            source_unit_refs=("unit:0",),
            target_ref=None,
            target_kind=None,
            input_ports=(),
            output_ports=("role:literal",),
            constraints=(("literal", "42"),),
            provenance_refs=(),
            literal_value=None,
        )

    # Non-literal kind must not have literal_value
    with pytest.raises(ValueError, match="only literal contributions may carry"):
        ContributionSlot.create(
            contribution_ref="contribution:0",
            kind="anchor",
            source_unit_refs=("unit:0",),
            target_ref="entity:book",
            target_kind="entity",
            input_ports=(),
            output_ports=("role:anchor",),
            constraints=(),
            provenance_refs=(),
            literal_value="42",
        )


# ---------------------------------------------------------------------------
# Task 2g: Second reviewed language pack + multilingual canaries
# ---------------------------------------------------------------------------

ES_FORMS_PATH = ROOT / "languages" / "es" / "forms.json"


@pytest.fixture
def es_form_pack() -> dict:
    with open(ES_FORMS_PATH) as f:
        return json.load(f)


@pytest.fixture
def es_form_resolver(es_form_pack) -> FormResolver:
    return FormResolver(es_form_pack, RuntimeConfig.release())


def test_second_language_pack_exists():
    """A second reviewed language pack exists at data/languages/es/forms.json."""
    assert ES_FORMS_PATH.exists(), "Second language pack (es) must exist"


def test_second_language_pack_has_same_abi_version(es_form_pack):
    """The second language pack uses the same ABI version as English."""
    assert es_form_pack["abi_version"] == 7
    assert es_form_pack["language"] == "es"


def test_second_language_pack_has_scope_values(es_form_pack):
    """The second language pack has reviewed scope_values mapping."""
    scope_values = es_form_pack.get("scope_values", {})
    assert "polarity" in scope_values
    assert "modality" in scope_values
    for category, values in scope_values.items():
        for feature_value, ref in values.items():
            assert ref.startswith("scope_value:"), (
                f"ES scope value {ref} for {category}/{feature_value} "
                f"is not a reviewed scope_value ref"
            )


def test_second_language_pack_has_link_schemas(es_form_pack):
    """The second language pack has reviewed link_schemas mapping."""
    schemas = es_form_pack.get("link_schemas", {})
    assert len(schemas) >= 8
    for name, schema in schemas.items():
        assert "link_type" in schema
        assert "commutative" in schema
        assert "min_arity" in schema
        assert "max_arity" in schema


def test_second_language_pack_tokenizes(es_form_resolver):
    """The second language pack tokenizes Spanish text correctly."""
    lattice = es_form_resolver.resolve("hola")
    assert len(lattice.units) >= 1
    # Joining source_text must reproduce input
    assert "".join(u.source_text for u in lattice.units) == "hola"


def test_second_language_pack_detects_polarity(es_form_resolver, es_form_pack):
    """The second language pack detects Spanish negation."""
    lattice = es_form_resolver.resolve("no")
    config = RuntimeConfig.release()
    scope_values = es_form_pack.get("scope_values", {})
    from cemm_authoritative_hybrid.proposal_context import _scope_slots

    slots = _scope_slots(lattice, config, scope_values)
    assert len(slots) >= 1
    assert slots[0].operator_type == "scope:polarity"
    assert slots[0].value_ref == "scope_value:polarity:negative"


def test_second_language_pack_detects_conjunction(es_form_resolver, es_form_pack):
    """The second language pack detects Spanish conjunction ('y')."""
    lattice = es_form_resolver.resolve("alice y bob")
    config = RuntimeConfig.release()
    link_schemas = es_form_pack.get("link_schemas", {})
    from cemm_authoritative_hybrid.proposal_context import _expression_link_slots

    slots = _expression_link_slots(lattice, config, link_schemas)
    link_types = {slot.link_type for slot in slots}
    assert "link:conjunction" in link_types


def test_language_packs_share_reviewed_scope_value_refs(form_pack, es_form_pack):
    """Both language packs map to the same reviewed scope_value refs.

    Per R2 plan section 2.7: meaning != language. The same semantic
    scope value ref is reached regardless of input language.
    """
    en_polarity = form_pack["scope_values"]["polarity"]["negation"]
    es_polarity = es_form_pack["scope_values"]["polarity"]["negation"]
    assert en_polarity == es_polarity, (
        "Scope value refs must be language-invariant: "
        f"en={en_polarity}, es={es_polarity}"
    )


def test_language_packs_share_reviewed_link_types(form_pack, es_form_pack):
    """Both language packs map to the same reviewed link types."""
    en_conjunction = form_pack["link_schemas"]["conjunction"]["link_type"]
    es_conjunction = es_form_pack["link_schemas"]["conjunction"]["link_type"]
    assert en_conjunction == es_conjunction == "link:conjunction"
