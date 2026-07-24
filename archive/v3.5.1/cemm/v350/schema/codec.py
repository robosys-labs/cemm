"""Deterministic document codec for the v3.5 schema metamodel."""
from __future__ import annotations

from dataclasses import fields
from typing import Any, Mapping

from .model import (
    ActionSchema,
    Cardinality,
    CompetenceHook,
    DiscourseActSchema,
    DiscourseRelationSchema,
    EntitlementApplicability,
    EntitlementInheritancePolicy,
    EventSchema,
    FacetEntitlement,
    FacetSchema,
    FunctionSchema,
    LocalPortSchema,
    MeaningSchema,
    MeasureDimensionSchema,
    OpenBindingPurpose,
    OperatorSchema,
    ParentRevisionPolicy,
    PortFillerClass,
    PropertySchema,
    ReferentTypeSchema,
    RelationSchema,
    ResponsePolicySchema,
    RoleSchema,
    SCHEMA_CLASS_TO_TYPE,
    SchemaClass,
    SchemaDependency,
    SchemaLifecycleStatus,
    SchemaParentLink,
    SchemaProvenance,
    StateDimensionSchema,
    StateValueSchema,
    StorageKind,
    UnitSchema,
    UseAuthorization,
    UseDecision,
    UseOperation,
    UseProfile,
    entitlement_to_document,
    schema_to_document,
)


class SchemaDecodeError(ValueError):
    pass


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _cardinality(value: Any) -> Cardinality:
    if isinstance(value, Cardinality):
        return value
    data = dict(value or {})
    maximum = data["maximum"] if "maximum" in data else 1
    return Cardinality(
        int(data.get("minimum", 0)),
        None if maximum is None else int(maximum),
    )


def _provenance(value: Any) -> SchemaProvenance:
    if isinstance(value, SchemaProvenance):
        return value
    data = dict(value or {})
    return SchemaProvenance(
        evidence_refs=_tuple_str(data.get("evidence_refs")),
        source_refs=_tuple_str(data.get("source_refs")),
        lineage_refs=_tuple_str(data.get("lineage_refs")),
        created_by=str(data.get("created_by", "")),
        created_at=str(data.get("created_at", "")),
        field_sources=tuple((str(a), str(b)) for a, b in data.get("field_sources", ())),
    )


def _parent_link(value: Any) -> SchemaParentLink:
    if isinstance(value, SchemaParentLink):
        return value
    data = dict(value)
    return SchemaParentLink(
        parent_ref=str(data["parent_ref"]),
        revision_policy=ParentRevisionPolicy(data.get("revision_policy", "authoritative")),
        revision=None if data.get("revision") is None else int(data["revision"]),
        inheritance_kind=str(data.get("inheritance_kind", "inherit")),
        priority=int(data.get("priority", 0)),
    )


def _dependency(value: Any) -> SchemaDependency:
    if isinstance(value, SchemaDependency):
        return value
    data = dict(value)
    return SchemaDependency(
        dependency_ref=str(data["dependency_ref"]),
        dependency_kind=str(data["dependency_kind"]),
        minimum_revision=None if data.get("minimum_revision") is None else int(data["minimum_revision"]),
        exact_revision=None if data.get("exact_revision") is None else int(data["exact_revision"]),
        required=bool(data.get("required", True)),
        required_for=frozenset(UseOperation(item) for item in data.get("required_for", ())),
        reason=str(data.get("reason", "")),
    )


def _competence(value: Any) -> CompetenceHook:
    if isinstance(value, CompetenceHook):
        return value
    data = dict(value)
    return CompetenceHook(
        case_ref=str(data["case_ref"]),
        operation=UseOperation(data["operation"]),
        required=bool(data.get("required", True)),
        independent_lineage_ref=str(data.get("independent_lineage_ref", "")),
        environment_ref=str(data.get("environment_ref", "")),
    )


def _use_profile(value: Any) -> UseProfile:
    if isinstance(value, UseProfile):
        return value
    if isinstance(value, Mapping) and "authorizations" not in value:
        return UseProfile.from_mapping(value)
    data = dict(value or {})
    return UseProfile(tuple(
        UseAuthorization(
            operation=UseOperation(item["operation"]),
            decision=UseDecision(item["decision"]),
            evidence_refs=_tuple_str(item.get("evidence_refs")),
            reason=str(item.get("reason", "")),
        )
        for item in data.get("authorizations", ())
    ))


def _port(value: Any) -> LocalPortSchema:
    if isinstance(value, LocalPortSchema):
        return value
    data = dict(value)
    return LocalPortSchema(
        port_ref=str(data["port_ref"]),
        filler_classes=frozenset(PortFillerClass(item) for item in data.get("filler_classes", ("referent",))),
        accepted_type_refs=_tuple_str(data.get("accepted_type_refs")),
        accepted_storage_kinds=frozenset(StorageKind(item) for item in data.get("accepted_storage_kinds", ())),
        accepted_schema_classes=frozenset(SchemaClass(item) for item in data.get("accepted_schema_classes", ())),
        cardinality=_cardinality(data.get("cardinality")),
        queryable=bool(data.get("queryable", False)),
        open_binding_purposes=frozenset(OpenBindingPurpose(item) for item in data.get("open_binding_purposes", ())),
        role_family=str(data.get("role_family", "")),
        context_policy=str(data.get("context_policy", "inherit")),
        time_policy=str(data.get("time_policy", "inherit")),
        identity_contribution=bool(data.get("identity_contribution", False)),
        ordered_fillers=bool(data.get("ordered_fillers", False)),
        constraint_refs=_tuple_str(data.get("constraint_refs")),
        metadata=dict(data.get("metadata", {})),
    )


def _base(data: Mapping[str, Any]) -> dict[str, Any]:
    parent_values = data.get("parent_links")
    if parent_values is None:
        # Compatibility for early v3.5 drafts; this does not affect runtime authority.
        parent_values = ({"parent_ref": ref} for ref in data.get("parent_schema_refs", ()))
    return {
        "schema_ref": str(data["schema_ref"]),
        "semantic_key": str(data["semantic_key"]),
        "parent_links": tuple(_parent_link(item) for item in parent_values),
        "local_ports": tuple(_port(item) for item in data.get("local_ports", ())),
        "lifecycle_status": SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
        "revision": int(data.get("revision", 1)),
        "supersedes_revision": None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        "scope_ref": str(data.get("scope_ref", "global")),
        "confidence": float(data.get("confidence", 1.0)),
        "permission_ref": str(data.get("permission_ref", "public")),
        "provenance": _provenance(data.get("provenance")),
        "dependencies": tuple(_dependency(item) for item in data.get("dependencies", ())),
        "use_profile": _use_profile(data.get("use_profile")),
        "competence_hooks": tuple(_competence(item) for item in data.get("competence_hooks", ())),
        "valid_from": data.get("valid_from"),
        "valid_to": data.get("valid_to"),
        "metadata": dict(data.get("metadata", {})),
    }


def schema_from_document(value: Mapping[str, Any]) -> MeaningSchema:
    data = dict(value)
    try:
        schema_class = SchemaClass(data.get("schema_class", "meaning_schema"))
        cls = SCHEMA_CLASS_TO_TYPE[schema_class]
        kwargs = _base(data)
        extras: dict[type[MeaningSchema], dict[str, Any]] = {
            ReferentTypeSchema: {
                "storage_kinds": frozenset(StorageKind(item) for item in data.get("storage_kinds", ("ordinary",))),
                "facet_entitlement_refs": _tuple_str(data.get("facet_entitlement_refs")),
                "identity_criterion_refs": _tuple_str(data.get("identity_criterion_refs")),
            },
            FacetSchema: {
                "facet_family": str(data.get("facet_family", "")),
                "permitted_storage_kinds": frozenset(StorageKind(item) for item in data.get("permitted_storage_kinds", ())),
            },
            PropertySchema: {
                "holder_type_refs": _tuple_str(data.get("holder_type_refs")),
                "value_type_refs": _tuple_str(data.get("value_type_refs")),
                "value_schema_refs": _tuple_str(data.get("value_schema_refs")),
                "value_cardinality": _cardinality(data.get("value_cardinality")),
                "correction_policy": str(data.get("correction_policy", "supersede_same_holder")),
                "context_policy": str(data.get("context_policy", "qualified")),
                "time_policy": str(data.get("time_policy", "qualified")),
            },
            StateDimensionSchema: {
                "holder_type_refs": _tuple_str(data.get("holder_type_refs")),
                "value_schema_refs": _tuple_str(data.get("value_schema_refs")),
                "value_cardinality": _cardinality(data.get("value_cardinality")),
                "exclusive": bool(data.get("exclusive", True)),
                "ordered": bool(data.get("ordered", False)),
                "scalar": bool(data.get("scalar", False)),
                "persistence": str(data.get("persistence", "persistent_until_changed")),
                "observation_channel_refs": _tuple_str(data.get("observation_channel_refs")),
                "transition_contract_refs": _tuple_str(data.get("transition_contract_refs")),
                "default_rule_refs": _tuple_str(data.get("default_rule_refs")),
                "applicability_rule_refs": _tuple_str(data.get("applicability_rule_refs")),
            },
            StateValueSchema: {
                "dimension_ref": str(data.get("dimension_ref", "")),
                "ordering_key": data.get("ordering_key", data.get("order_rank")),
                "mutually_exclusive_with": _tuple_str(data.get("mutually_exclusive_with")),
            },
            RelationSchema: {
                "symmetric": bool(data.get("symmetric", False)),
                "transitive": bool(data.get("transitive", False)),
                "irreflexive": bool(data.get("irreflexive", False)),
                "inverse_relation_ref": data.get("inverse_relation_ref"),
                "persistence": str(data.get("persistence", "qualified")),
            },
            RoleSchema: {
                "holder_type_refs": _tuple_str(data.get("holder_type_refs")),
                "context_type_refs": _tuple_str(data.get("context_type_refs")),
                "occupancy_cardinality": _cardinality(data.get("occupancy_cardinality")),
                "occupancy_policy": str(data.get("occupancy_policy", "time_context_qualified")),
            },
            FunctionSchema: {
                "holder_type_refs": _tuple_str(data.get("holder_type_refs")),
                "contribution_schema_refs": _tuple_str(data.get("contribution_schema_refs")),
                "realization_action_refs": _tuple_str(data.get("realization_action_refs")),
            },
            ActionSchema: {
                "controlling_port_ref": data.get("controlling_port_ref"),
                "intentional_required": bool(data.get("intentional_required", True)),
                "affordance_rule_refs": _tuple_str(data.get("affordance_rule_refs")),
                "operation_contract_refs": _tuple_str(data.get("operation_contract_refs")),
            },
            EventSchema: {
                "temporal_profile": str(data.get("temporal_profile", "occurrence")),
                "occurrence_constraint_refs": _tuple_str(data.get("occurrence_constraint_refs")),
                "transition_contract_refs": _tuple_str(data.get("transition_contract_refs")),
                "result_contract_refs": _tuple_str(data.get("result_contract_refs")),
                "causal_contract_refs": _tuple_str(data.get("causal_contract_refs")),
                "impact_rule_refs": _tuple_str(data.get("impact_rule_refs")),
                "persistence": str(data.get("persistence", "instantaneous")),
                "reversibility": str(data.get("reversibility", "unknown")),
            },
            UnitSchema: {
                "measure_dimension_ref": str(data.get("measure_dimension_ref", "")),
                "symbol_refs": _tuple_str(data.get("symbol_refs")),
                "conversion_rule_refs": _tuple_str(data.get("conversion_rule_refs")),
            },
            MeasureDimensionSchema: {
                "quantity_type_refs": _tuple_str(data.get("quantity_type_refs")),
                "canonical_unit_ref": data.get("canonical_unit_ref"),
                "ordered": bool(data.get("ordered", True)),
            },
            OperatorSchema: {
                "operator_family": str(data.get("operator_family", "")),
                "minimum_arity": int(data.get("minimum_arity", 1)),
                "maximum_arity": (
                    None
                    if data.get("maximum_arity", 1) is None
                    else int(data.get("maximum_arity", 1))
                ),
                "scope_policy": str(data.get("scope_policy", "explicit")),
            },
            DiscourseActSchema: {
                "speaker_port_ref": data.get("speaker_port_ref"),
                "addressee_port_ref": data.get("addressee_port_ref"),
                "content_port_ref": data.get("content_port_ref"),
                "obligation_refs": _tuple_str(data.get("obligation_refs")),
            },
            DiscourseRelationSchema: {
                "source_class_refs": _tuple_str(data.get("source_class_refs")),
                "target_class_refs": _tuple_str(data.get("target_class_refs")),
                "structural": bool(data.get("structural", True)),
            },
            ResponsePolicySchema: {
                "trigger_schema_refs": _tuple_str(data.get("trigger_schema_refs")),
                "preferred_goal_refs": _tuple_str(data.get("preferred_goal_refs")),
                "literal_realization_refs": _tuple_str(data.get("literal_realization_refs")),
                "safety_override_refs": _tuple_str(data.get("safety_override_refs")),
            },
        }
        kwargs.update(extras.get(cls, {}))
        return cls(**kwargs)
    except (KeyError, TypeError, ValueError) as exc:
        raise SchemaDecodeError(str(exc)) from exc


def entitlement_from_document(value: Mapping[str, Any]) -> FacetEntitlement:
    data = dict(value)
    try:
        return FacetEntitlement(
            entitlement_ref=str(data["entitlement_ref"]),
            owner_type_ref=str(data["owner_type_ref"]),
            facet_ref=str(data["facet_ref"]),
            applicability=EntitlementApplicability(data["applicability"]),
            activation_policy=str(data.get("activation_policy", "on_evidence")),
            value_domain_refs=_tuple_str(data.get("value_domain_refs")),
            default_rule_refs=_tuple_str(data.get("default_rule_refs")),
            dependencies=tuple(_dependency(item) for item in data.get("dependencies", ())),
            inheritance_policy=EntitlementInheritancePolicy(data.get("inheritance_policy", "inherit")),
            context_constraints=_tuple_str(data.get("context_constraints")),
            temporal_constraints=_tuple_str(data.get("temporal_constraints")),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", "candidate")),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            scope_ref=str(data.get("scope_ref", "global")),
            confidence=float(data.get("confidence", 1.0)),
            permission_ref=str(data.get("permission_ref", "public")),
            provenance=_provenance(data.get("provenance")),
            use_profile=_use_profile(data.get("use_profile")),
            competence_hooks=tuple(_competence(item) for item in data.get("competence_hooks", ())),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SchemaDecodeError(str(exc)) from exc


def record_from_document(value: Mapping[str, Any]) -> MeaningSchema | FacetEntitlement:
    if value.get("record_class") == "facet_entitlement" or "entitlement_ref" in value:
        return entitlement_from_document(value)
    return schema_from_document(value)


def record_to_document(value: MeaningSchema | FacetEntitlement) -> dict[str, Any]:
    if isinstance(value, FacetEntitlement):
        return entitlement_to_document(value)
    return schema_to_document(value)
