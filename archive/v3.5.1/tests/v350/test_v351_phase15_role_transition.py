from __future__ import annotations

from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.schema.model import UseOperation
from cemm.v350.state import (
    CausalEventV351, MechanismTriggerKind, OperandKind, ParticipantRoleBinding,
    RoleStateTransformV351, StateDomainContractV351, StateDomainKind, StateKeyV351,
    StateOperandV351, StateSnapshotV351, StateTransformExpression, StateTransformOperator,
    StateValueV351, TransitionMechanismV351, TransitionPreviewEngineV351,
)


def pin(kind, ref): return ExactAuthorityPin(kind, "test", ref, 1, f"sha:{kind}:{ref}", "global")


def mechanism():
    role = pin("semantic_port", "affected")
    dimension = pin("state_dimension", "level")
    event = pin("semantic_definition", "event")
    competence = pin("competence_case", "transition")
    return TransitionMechanismV351(
        mechanism_ref="mechanism:test", revision=1, trigger_kind=MechanismTriggerKind.EVENT,
        trigger_definition_pin=event, participant_role_pins=(role,),
        deterministic_transforms=(RoleStateTransformV351(
            "transform:raise", role, dimension,
            StateTransformExpression(StateTransformOperator.ADD, (StateOperandV351(OperandKind.CONSTANT, constant=2.0),)),
        ),),
        competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    ), role, dimension, event


def test_surface_voice_cannot_change_semantic_transition_result():
    m, role, dimension, event_pin = mechanism()
    domain = StateDomainContractV351("level", 1, StateDomainKind.CONTINUOUS)
    current = StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=3)
    snap = StateSnapshotV351(((StateKeyV351("entity:1", dimension, "actual"), current),), ((dimension.key, domain),))
    engine = TransitionPreviewEngineV351()
    # Two derivations/voices are represented only by different source_application_ref values.
    events = tuple(CausalEventV351(
        event_ref=f"event:{source}", predicate_pin=event_pin,
        role_bindings=(ParticipantRoleBinding(role, "entity:1", source),),
        context_ref="actual", effective_time_ref="t:1",
    ) for source in ("derivation:active", "derivation:passive"))
    previews = [engine.preview_event(e, (m,), snap) for e in events]
    assert previews[0].distributions[0].branches[0][2][0].new_value.value_ref == previews[1].distributions[0].branches[0][2][0].new_value.value_ref
    assert previews[0].distributions[0].branches[0][2][0].new_value.scalar_value == 5


def test_active_lifecycle_without_explicit_transition_use_is_not_executable():
    role = pin("semantic_port", "affected:no-use")
    dimension = pin("state_dimension", "level:no-use")
    event = pin("semantic_definition", "event:no-use")
    competence = pin("competence_case", "transition:no-use")
    m = TransitionMechanismV351(
        mechanism_ref="mechanism:no-use", revision=1,
        trigger_kind=MechanismTriggerKind.EVENT, trigger_definition_pin=event,
        participant_role_pins=(role,),
        deterministic_transforms=(RoleStateTransformV351(
            "transform:no-use", role, dimension,
            StateTransformExpression(
                StateTransformOperator.ADD,
                (StateOperandV351(OperandKind.CONSTANT, constant=1.0),),
            ),
        ),),
        competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
    )
    assert not m.executable


def test_capability_dependency_graph_is_exact_use_authorized_bounded_dag():
    from cemm.v350.state import (
        CapabilityDependencyEvaluatorV351, CapabilityDependencyGraph,
        CapabilityDependencyNodeV351, CapabilityNodeKind, CapabilityStateRequirementV351,
        ConditionOperatorV351,
    )

    dimension = pin("state_dimension", "capability-energy")
    action = pin("action", "operate")
    holder_type = pin("referent_type", "device")
    case = pin("competence_case", "capability-operate")
    requirement = CapabilityStateRequirementV351(
        "requirement:energy-known", dimension, ConditionOperatorV351.KNOWN,
    )
    node = CapabilityDependencyNodeV351(
        "node:energy-known", CapabilityNodeKind.STATE, state_requirement=requirement,
    )
    no_use = CapabilityDependencyGraph(
        "capability-graph:operate", action, (holder_type,), node.node_ref, (node,),
        lifecycle_status="active", evidence_refs=("e:reviewed",), competence_case_pins=(case,),
    )
    assert not no_use.executable
    graph = CapabilityDependencyGraph(
        "capability-graph:operate", action, (holder_type,), node.node_ref, (node,),
        lifecycle_status="active", evidence_refs=("e:reviewed",), competence_case_pins=(case,),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    assert graph.executable
    assessment = CapabilityDependencyEvaluatorV351().evaluate(
        graph, holder_ref="entity:1",
        resolve_leaf=lambda leaf: (True, 1.0, ("proof:state",)),
    )
    assert assessment.status.value == "available"
    assert assessment.proof_refs == ("proof:state",)


def test_capability_dependency_codec_roundtrip_preserves_typed_state_requirement():
    from cemm.v350.state import (
        CapabilityDependencyGraph, CapabilityDependencyNodeV351, CapabilityNodeKind,
        CapabilityStateRequirementV351, ConditionOperatorV351,
    )
    from cemm.v350.state.codec_v351 import (
        capability_dependency_graph_from_document, capability_dependency_graph_to_document,
    )

    dimension = pin("state_dimension", "capability-level")
    action = pin("action", "lift")
    holder_type = pin("referent_type", "machine")
    case = pin("competence_case", "capability-lift")
    expected = StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=5)
    requirement = CapabilityStateRequirementV351(
        "requirement:level", dimension, ConditionOperatorV351.GREATER_EQUAL,
        numeric_threshold=5,
    )
    node = CapabilityDependencyNodeV351(
        "node:level", CapabilityNodeKind.STATE, state_requirement=requirement,
    )
    graph = CapabilityDependencyGraph(
        "capability-graph:lift", action, (holder_type,), node.node_ref, (node,),
        lifecycle_status="candidate", competence_case_pins=(case,),
    )
    restored = capability_dependency_graph_from_document(
        capability_dependency_graph_to_document(graph)
    )
    assert restored == graph
    assert restored.nodes[0].state_requirement.dimension_pin.key == dimension.key


def test_one_mechanism_branch_cannot_implicitly_sequence_two_writes_to_same_state_target():
    import pytest
    from cemm.v350.state import MechanismBranchV351, StateModelError

    role = pin("semantic_port", "duplicate-target-role")
    dimension = pin("state_dimension", "duplicate-target-dimension")
    expression = StateTransformExpression(
        StateTransformOperator.ADD,
        (StateOperandV351(OperandKind.CONSTANT, constant=1.0),),
    )
    first = RoleStateTransformV351("transform:first", role, dimension, expression)
    second = RoleStateTransformV351("transform:second", role, dimension, expression)
    with pytest.raises(StateModelError, match="transform targets"):
        MechanismBranchV351("branch:duplicate-target", 1.0, (first, second))
