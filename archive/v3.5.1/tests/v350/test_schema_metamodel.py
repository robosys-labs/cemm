from __future__ import annotations

from dataclasses import replace

import pytest

from cemm.v350.schema.codec import record_from_document, record_to_document
from cemm.v350.schema.model import (
    Cardinality,
    CompetenceHook,
    EntitlementApplicability,
    EventSchema,
    FacetEntitlement,
    FacetSchema,
    LocalPortSchema,
    MeaningSchema,
    OpenBindingPurpose,
    ParentRevisionPolicy,
    PortFillerClass,
    ReferentTypeSchema,
    SchemaClass,
    SchemaDependency,
    SchemaLifecycleStatus,
    SchemaParentLink,
    SchemaProvenance,
    StateDimensionSchema,
    StateValueSchema,
    StorageKind,
    UseDecision,
    UseOperation,
    UseProfile,
    lifecycle_transition_allowed,
)
from cemm.v350.schema.registry import (
    DuplicateRevisionError,
    InheritanceCycleError,
    SchemaRegistry,
)


def profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def active_type(ref: str, *parents: str, revision: int = 1) -> ReferentTypeSchema:
    return ReferentTypeSchema(
        schema_ref=ref,
        semantic_key=ref.split(":")[-1],
        parent_links=tuple(SchemaParentLink(item) for item in parents),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        revision=revision,
        storage_kinds=frozenset({StorageKind.ORDINARY}),
        use_profile=profile(mention="allow", ground="allow", compose="allow", query="allow"),
    )


def test_new_type_is_data_not_python_enum() -> None:
    lumin = active_type("type:lumin", "type:digital", "type:agent")
    assert lumin.schema_class == SchemaClass.REFERENT_TYPE
    assert lumin.parent_schema_refs == ("type:digital", "type:agent")
    assert not hasattr(__import__("cemm.v350.schema.model", fromlist=["ReferentKind"]), "ReferentKind")


def test_open_port_supports_learning_and_partial_composition() -> None:
    port = LocalPortSchema(
        "value",
        filler_classes=frozenset({PortFillerClass.REFERENT, PortFillerClass.SEMANTIC_VARIABLE}),
        open_binding_purposes=frozenset({
            OpenBindingPurpose.LEARNING,
            OpenBindingPurpose.PARTIAL_COMPOSITION,
        }),
    )
    assert port.allows_open
    assert not port.queryable


def test_query_open_requires_queryable() -> None:
    with pytest.raises(ValueError, match="query-open"):
        LocalPortSchema(
            "value",
            filler_classes=frozenset({PortFillerClass.SEMANTIC_VARIABLE}),
            open_binding_purposes=frozenset({OpenBindingPurpose.QUERY}),
        )


def test_multiple_inheritance_closure_is_deterministic() -> None:
    registry = SchemaRegistry([
        active_type("type:referent"),
        active_type("type:digital", "type:referent"),
        active_type("type:agent", "type:referent"),
        active_type("type:lumin", "type:digital", "type:agent"),
    ])
    assert registry.type_closure("type:lumin") == frozenset({
        "type:lumin", "type:digital", "type:agent", "type:referent"
    })


def test_parent_revision_policy_exact_and_minimum() -> None:
    base1 = active_type("type:base", revision=1)
    base2 = replace(base1, revision=2, supersedes_revision=1, lifecycle_status=SchemaLifecycleStatus.ACTIVE)
    registry = SchemaRegistry([replace(base1, lifecycle_status=SchemaLifecycleStatus.SUPERSEDED), base2])
    assert registry.resolve_parent(SchemaParentLink("type:base", ParentRevisionPolicy.EXACT, 1)).revision == 1
    assert registry.resolve_parent(SchemaParentLink("type:base", ParentRevisionPolicy.MINIMUM, 2)).revision == 2


def test_inheritance_cycle_is_rejected() -> None:
    registry = SchemaRegistry([
        active_type("type:a", "type:b"),
        active_type("type:b", "type:a"),
    ])
    with pytest.raises(InheritanceCycleError):
        registry.type_closure("type:a")
    assert any(item.code == "type_inheritance_cycle" for item in registry.validate().errors)


def test_newer_candidate_does_not_hide_active_revision() -> None:
    active = active_type("type:lumin", revision=1)
    candidate = replace(active, revision=2, lifecycle_status=SchemaLifecycleStatus.CANDIDATE)
    registry = SchemaRegistry([active, candidate])
    assert registry.authoritative_schema("type:lumin").revision == 1


def test_use_profile_is_independent_per_operation() -> None:
    schema = replace(
        active_type("type:lumin"),
        use_profile=profile(mention="allow", ground="provisional", infer="deny"),
    )
    assert schema.use_profile.permits(UseOperation.MENTION)
    assert not schema.use_profile.permits(UseOperation.GROUND)
    assert schema.use_profile.permits(UseOperation.GROUND, provisional=True)
    assert not schema.use_profile.permits(UseOperation.INFER)


def test_content_fingerprint_ignores_provenance_and_revision_authority() -> None:
    original = active_type("type:lumin")
    revised = replace(
        original,
        revision=2,
        supersedes_revision=1,
        confidence=0.7,
        provenance=SchemaProvenance(source_refs=("source:new",)),
    )
    assert original.content_fingerprint == revised.content_fingerprint
    assert original.record_fingerprint != revised.record_fingerprint


def test_codec_preserves_exact_typed_record() -> None:
    event = EventSchema(
        schema_ref="event:dim",
        semantic_key="dim",
        parent_links=(SchemaParentLink("event:decrease", priority=10),),
        local_ports=(LocalPortSchema(
            "affected",
            accepted_type_refs=("type:lumin",),
            cardinality=Cardinality(1, 1),
        ),),
        lifecycle_status=SchemaLifecycleStatus.PROVISIONAL,
        revision=3,
        supersedes_revision=2,
        dependencies=(SchemaDependency("state:charge", "state_dimension", minimum_revision=2),),
        use_profile=profile(compose="provisional", query="allow"),
        competence_hooks=(CompetenceHook("case:dim:compose", UseOperation.COMPOSE),),
        transition_contract_refs=("transition:dim-charge",),
        provenance=SchemaProvenance(evidence_refs=("evidence:teach",)),
    )
    decoded = record_from_document(record_to_document(event))
    assert decoded == event
    assert decoded.record_fingerprint == event.record_fingerprint


def test_entitlement_has_same_revision_and_authority_infrastructure() -> None:
    entitlement = FacetEntitlement(
        entitlement_ref="entitlement:lumin:charge",
        owner_type_ref="type:lumin",
        facet_ref="facet:state",
        applicability=EntitlementApplicability.REQUIRED,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow"),
        dependencies=(SchemaDependency("state:charge", "value_domain"),),
        provenance=SchemaProvenance(source_refs=("foundation",)),
    )
    assert record_from_document(record_to_document(entitlement)) == entitlement


def test_registry_validates_state_value_back_reference() -> None:
    holder = active_type("type:referent")
    dimension = StateDimensionSchema(
        schema_ref="state:charge",
        semantic_key="charge",
        holder_type_refs=(holder.schema_ref,),
        value_schema_refs=("state-value:charged",),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow"),
    )
    value = StateValueSchema(
        schema_ref="state-value:charged",
        semantic_key="charged",
        dimension_ref="state:wrong",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow"),
    )
    report = SchemaRegistry([holder, dimension, value]).validate()
    assert any(item.code == "state_value_backref_mismatch" for item in report.errors)


def test_missing_dependency_is_frontier_for_candidate_but_error_for_active() -> None:
    candidate = ReferentTypeSchema(
        schema_ref="type:lumin",
        semantic_key="lumin",
        dependencies=(SchemaDependency("type:digital", "parent"),),
    )
    candidate_report = SchemaRegistry([candidate]).validate()
    assert any(item.code == "missing_required_dependency" for item in candidate_report.unresolved)
    active_report = SchemaRegistry([replace(candidate, lifecycle_status=SchemaLifecycleStatus.ACTIVE)]).validate()
    assert any(item.code == "missing_required_dependency" for item in active_report.errors)


def test_generic_meaning_schema_cannot_become_executable() -> None:
    generic = MeaningSchema(
        schema_ref="schema:generic",
        semantic_key="generic",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
    )
    assert any(item.code == "generic_schema_executable" for item in SchemaRegistry([generic]).validate().errors)


def test_active_high_risk_use_requires_competence_hook() -> None:
    schema = replace(active_type("type:lumin"), use_profile=profile(transition="allow"))
    report = SchemaRegistry([schema]).validate()
    assert any(item.code == "missing_competence_hook" for item in report.errors)


def test_duplicate_revision_is_rejected() -> None:
    schema = active_type("type:lumin")
    registry = SchemaRegistry([schema])
    with pytest.raises(DuplicateRevisionError):
        registry.add_schema(schema)


def test_lifecycle_is_forward_only_with_new_revisions_for_corrections() -> None:
    assert lifecycle_transition_allowed(SchemaLifecycleStatus.CANDIDATE, SchemaLifecycleStatus.STRUCTURALLY_CLOSED)
    assert not lifecycle_transition_allowed(SchemaLifecycleStatus.ACTIVE, SchemaLifecycleStatus.CANDIDATE)
