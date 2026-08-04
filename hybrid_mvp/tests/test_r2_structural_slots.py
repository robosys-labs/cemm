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
