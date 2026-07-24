"""Deterministic codecs for Phase-15 rich transition mechanism authority."""
from __future__ import annotations

from typing import Any, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import UseOperation, canonical_data
from .model_v351 import (
    ConditionOperatorV351, MechanismBranchV351, MechanismDefeater, MechanismPrecondition,
    MechanismTriggerKind, OperandKind, RoleStateTransformV351, SecondaryEventTemplateV351,
    RelationStateRoleBindingV351, StateOperandV351, StateTransformExpression, StateTransformOperator, StateValueV351,
    TransitionMechanismV351, UnknownConditionPolicyV351,
)
from .entitlement_v351 import state_value_from_document
from .model_v351 import ProbabilityPointV351, ProcessStatus, StateDomainKind


def _pin(value):
    if value is None:
        return None
    if isinstance(value, ExactAuthorityPin):
        return value
    if isinstance(value, Mapping):
        return ExactAuthorityPin(
            str(value["kind"]), str(value["namespace"]), str(value["ref"]),
            int(value["revision"]), str(value["content_hash"]), str(value.get("scope_ref", "global")),
        )
    return ExactAuthorityPin(
        str(value[0]), str(value[1]), str(value[2]), int(value[3]), str(value[4]), str(value[5])
    )



def _state_value(value):
    if value is None:
        return None
    if isinstance(value, StateValueV351):
        return value
    d = dict(value)
    if d.get("model") == "state-value-v351":
        return state_value_from_document(d)
    # canonical_data(dataclass) representation used inside transition authority documents.
    mass = []
    for item in d.get("probability_mass", ()):
        if isinstance(item, ProbabilityPointV351):
            mass.append(item)
        elif isinstance(item, Mapping):
            support = item.get("support_value")
            if not isinstance(support, Mapping):
                raise ValueError("probability support must be a typed state-value document")
            mass.append(ProbabilityPointV351(_state_value(support), float(item["probability"])))
        else:
            support, probability = item
            if not isinstance(support, Mapping):
                raise ValueError("probability support must be a typed state-value document")
            mass.append(ProbabilityPointV351(_state_value(support), float(probability)))
    return StateValueV351(
        domain_kind=StateDomainKind(str(d["domain_kind"])),
        categorical_pin=_pin(d.get("categorical_pin")),
        scalar_value=None if d.get("scalar_value") is None else float(d["scalar_value"]),
        vector_value=tuple(float(item) for item in d.get("vector_value", ())),
        relation_pin=_pin(d.get("relation_pin")),
        relation_bindings=tuple(
            RelationStateRoleBindingV351(
                _pin(item.get("role_pin") if isinstance(item, Mapping) else item[0]),
                str(item.get("participant_ref") if isinstance(item, Mapping) else item[1]),
            )
            for item in d.get("relation_bindings", ())
        ),
        set_members=tuple(map(str, d.get("set_members", ()))),
        process_pin=_pin(d.get("process_pin")),
        process_status=None if d.get("process_status") is None else ProcessStatus(str(d["process_status"])),
        process_progress=None if d.get("process_progress") is None else float(d["process_progress"]),
        probability_mass=tuple(mass),
        unit_pin=_pin(d.get("unit_pin")),
        coordinate_frame_pin=_pin(d.get("coordinate_frame_pin")),
        evidence_refs=tuple(map(str, d.get("evidence_refs", ()))),
    )

def _operand(d):
    d=dict(d)
    constant=d.get('constant')
    if isinstance(constant, Mapping) and 'domain_kind' in constant:
        constant=_state_value(constant)
    elif isinstance(constant, list):
        constant=tuple(constant)
    return StateOperandV351(
        kind=OperandKind(d['kind']), constant=constant,
        role_pin=_pin(d.get('role_pin')), dimension_pin=_pin(d.get('dimension_pin')),
        event_port_pin=_pin(d.get('event_port_pin')), parameter_pin=_pin(d.get('parameter_pin')),
        parameter_name=str(d.get('parameter_name','')),
    )


def _expr(d):
    d=dict(d)
    return StateTransformExpression(
        operator=StateTransformOperator(d['operator']),
        operands=tuple(_operand(x) for x in d.get('operands',())),
        external_operator_pin=_pin(d.get('external_operator_pin')),
        clamp_lower=None if d.get('clamp_lower') is None else float(d['clamp_lower']),
        clamp_upper=None if d.get('clamp_upper') is None else float(d['clamp_upper']),
    )


def _condition(d):
    d=dict(d); expected=_state_value(d.get('expected_value'))
    return MechanismPrecondition(
        str(d['condition_ref']), _pin(d['holder_role_pin']), _pin(d['dimension_pin']),
        ConditionOperatorV351(d['operator']), expected,
        str(d.get('expected_member_key','')),
        None if d.get('numeric_threshold') is None else float(d['numeric_threshold']),
        UnknownConditionPolicyV351(d.get('unknown_policy','preserve_frontier')),
    )


def _transform(d):
    d=dict(d)
    return RoleStateTransformV351(
        str(d['transform_ref']), _pin(d['target_role_pin']), _pin(d['dimension_pin']),
        _expr(d['expression']), float(d.get('confidence',1.0)), tuple(map(str,d.get('condition_refs',()))),
    )


def _secondary(d):
    d=dict(d)
    return SecondaryEventTemplateV351(
        str(d['template_ref']), _pin(d['event_definition_pin']),
        tuple((_pin(a),_pin(b)) for a,b in d.get('role_map',())), int(d.get('delay_steps',0)),
    )


def transition_mechanism_from_document(value: Mapping[str,Any]) -> TransitionMechanismV351:
    d=dict(value)
    return TransitionMechanismV351(
        mechanism_ref=str(d.get('mechanism_ref',d.get('contract_ref'))), revision=int(d.get('revision',1)),
        trigger_kind=MechanismTriggerKind(d['trigger_kind']), trigger_definition_pin=_pin(d.get('trigger_definition_pin')),
        participant_role_pins=tuple(_pin(x) for x in d.get('participant_role_pins',())),
        participant_type_requirements=tuple((_pin(a),tuple(_pin(x) for x in b)) for a,b in d.get('participant_type_requirements',())),
        source_dimension_pins=tuple(_pin(x) for x in d.get('source_dimension_pins',())),
        preconditions=tuple(_condition(x) for x in d.get('preconditions',())),
        defeaters=tuple(MechanismDefeater(str(x['defeater_ref']),_condition(x['condition']),bool(x.get('hard',True)),float(x.get('attenuation',0.0))) for x in d.get('defeaters',())),
        deterministic_transforms=tuple(_transform(x) for x in d.get('deterministic_transforms',())),
        deterministic_secondary_events=tuple(_secondary(x) for x in d.get('deterministic_secondary_events',())),
        branches=tuple(MechanismBranchV351(str(x['branch_ref']),float(x['probability']),tuple(_transform(y) for y in x.get('transforms',())),tuple(_secondary(y) for y in x.get('secondary_events',()))) for x in d.get('branches',())),
        parameter_pins=tuple(_pin(x) for x in d.get('parameter_pins',())),
        competence_case_pins=tuple(_pin(x) for x in d.get('competence_case_pins',())),
        evidence_refs=tuple(map(str,d.get('evidence_refs',()))), lifecycle_status=str(d.get('lifecycle_status','candidate')),
        use_operation=UseOperation(str(d.get('use_operation', UseOperation.TRANSITION.value))),
        authorized_use_operations=tuple(UseOperation(str(x)) for x in d.get('authorized_use_operations',())),
        use_authority_explicit=bool(d.get('use_authority_explicit',False)),
        permission_ref=str(d.get('permission_ref','public')), context_scopes=tuple(map(str,d.get('context_scopes',()))),
        aggregation_contract_pin=_pin(d.get('aggregation_contract_pin')),
        stochastic_independence_pin=_pin(d.get('stochastic_independence_pin')),
        metadata=dict(d.get('metadata',{})),
    )


def transition_mechanism_to_document(value: TransitionMechanismV351):
    d=dict(canonical_data(value)); d['model_version']='v351'; d['contract_ref']=value.mechanism_ref
    return d


# ---- Phase-15 capability dependency graph codec ---------------------------------
from .capability_v351 import (
    CapabilityDependencyGraph, CapabilityDependencyNodeV351, CapabilityNodeKind,
    CapabilityStateRequirementV351,
)


def _capability_state_requirement(value):
    if value is None:
        return None
    d = dict(value)
    return CapabilityStateRequirementV351(
        requirement_ref=str(d["requirement_ref"]),
        dimension_pin=_pin(d["dimension_pin"]),
        operator=ConditionOperatorV351(str(d["operator"])),
        expected_value=_state_value(d.get("expected_value")),
        expected_member_ref=str(d.get("expected_member_ref", "")),
        numeric_threshold=(
            None if d.get("numeric_threshold") is None
            else float(d["numeric_threshold"])
        ),
    )


def _capability_node(value):
    d = dict(value)
    return CapabilityDependencyNodeV351(
        node_ref=str(d["node_ref"]),
        kind=CapabilityNodeKind(str(d["kind"])),
        child_refs=tuple(map(str, d.get("child_refs", ()))),
        requirement_ref=str(d.get("requirement_ref", "")),
        requirement_pin=_pin(d.get("requirement_pin")),
        state_requirement=_capability_state_requirement(d.get("state_requirement")),
        minimum_support=float(d.get("minimum_support", 1.0)),
        metadata=dict(d.get("metadata", {})),
    )


def capability_dependency_graph_from_document(value: Mapping[str, Any]) -> CapabilityDependencyGraph:
    d = dict(value)
    return CapabilityDependencyGraph(
        graph_ref=str(d.get("graph_ref", d.get("dependency_ref"))),
        action_schema_pin=_pin(d["action_schema_pin"]),
        holder_type_pins=tuple(_pin(x) for x in d.get("holder_type_pins", ())),
        root_ref=str(d["root_ref"]),
        nodes=tuple(_capability_node(x) for x in d.get("nodes", ())),
        lifecycle_status=str(d.get("lifecycle_status", "candidate")),
        competence_case_pins=tuple(_pin(x) for x in d.get("competence_case_pins", ())),
        permission_ref=str(d.get("permission_ref", "public")),
        revision=int(d.get("revision", 1)),
        use_operation=UseOperation(str(d.get("use_operation", UseOperation.TRANSITION.value))),
        authorized_use_operations=tuple(
            UseOperation(str(x)) for x in d.get("authorized_use_operations", ())
        ),
        use_authority_explicit=bool(d.get("use_authority_explicit", False)),
        context_scopes=tuple(map(str, d.get("context_scopes", ()))),
        evidence_refs=tuple(map(str, d.get("evidence_refs", ()))),
        metadata=dict(d.get("metadata", {})),
    )


def capability_dependency_graph_to_document(value: CapabilityDependencyGraph):
    d = dict(canonical_data(value))
    d["model_version"] = "capability-dependency-v351"
    d["dependency_ref"] = value.graph_ref
    return d


__all__ = [
    'transition_mechanism_from_document', 'transition_mechanism_to_document',
    'capability_dependency_graph_from_document', 'capability_dependency_graph_to_document',
]
