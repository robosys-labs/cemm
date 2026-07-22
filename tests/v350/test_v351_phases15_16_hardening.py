from __future__ import annotations

import dataclasses

import pytest

from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.schema.model import UseOperation
from cemm.v350.storage.model import AssignmentStatus, StateAssignment
from cemm.v350.causal.goals_v351 import goals_from_impact
from cemm.v350.causal.impact_v351 import ImpactComponentV351, ImpactVector
from cemm.v350.causal.model_v351 import (
    CausalExplanationV351, CausalModelError, CausalQueryResultV351, ContextSemantics,
)
from cemm.v350.state.entitlement_v351 import EntitledStateSpaceCompilerV351
from cemm.v350.state.model_v351 import (
    MechanismTriggerKind, OperandKind, ParticipantRoleBinding, RoleStateTransformV351,
    StateDomainKind, StateOperandV351, StateTransformExpression, StateTransformOperator,
    StateValueV351, TransitionMechanismV351,
)


def pin(kind: str, ref: str) -> ExactAuthorityPin:
    return ExactAuthorityPin(kind, "test", ref, 1, f"sha:{kind}:{ref}", "global")


def mechanism(*, context_scopes=(), metadata=None):
    role = pin("semantic_port", "affected")
    dimension = pin("state_dimension", "level")
    trigger = pin("semantic_definition", "event")
    case = pin("competence_case", "transition")
    return TransitionMechanismV351(
        "mechanism:identity", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        deterministic_transforms=(RoleStateTransformV351(
            "transform:identity", role, dimension,
            StateTransformExpression(
                StateTransformOperator.ADD,
                (StateOperandV351(OperandKind.CONSTANT, constant=1.0),),
            ),
        ),),
        competence_case_pins=(case,), evidence_refs=("e:review",), lifecycle_status="active",
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
        context_scopes=tuple(context_scopes), metadata=dict(metadata or {}),
    )


def test_causal_mechanism_identity_does_not_bundle_context_or_review_metadata():
    a = mechanism(context_scopes=("ctx:a",), metadata={"review": "A"})
    b = mechanism(context_scopes=("ctx:b",), metadata={"review": "B"})
    assert a.authority_pin.key == b.authority_pin.key
    assert a.executable and b.executable


def test_unanswered_causal_result_cannot_smuggle_definitive_explanation():
    explanation = CausalExplanationV351(
        explanation_ref="explanation:1", query_ref="query:1", target_variable_ref="var:y",
        cause_variable_refs=("var:x",), cause_event_refs=(), mechanism_pins=(pin("causal_mechanism", "m"),),
        proof_ref="proof:1", step_refs=("step:1",), minimal=True, confidence=1.0,
    )
    with pytest.raises(CausalModelError, match="unanswered causal query"):
        CausalQueryResultV351(
            result_ref="result:1", query_ref="query:1", answered=False,
            explanation=explanation, frontier_refs=("frontier:missing-warrant",),
        )


def test_unresolved_actual_impact_is_not_ordinary_goal_pressure():
    channel = pin("impact_channel", "physical")
    component = ImpactComponentV351(
        channel_pin=channel, stakeholder_ref="r:stakeholder", affected_ref="r:affected",
        signed_magnitude=100.0, confidence=1.0, source_delta_refs=("delta:1",),
        causal_proof_refs=("proof:1",),
    )
    unresolved = ImpactVector(
        impact_ref="impact:unresolved", source_ref="simulation:1", components=(component,),
        context_ref="actual", context_semantics=ContextSemantics.ACTUAL,
        branch_probability=1.0, resolved=False, physical_state_delta_refs=("delta:1",),
        proof_refs=("proof:1",), frontier_refs=("frontier:causal:unknown",),
    )
    assert goals_from_impact((unresolved,)) == ()
    resolved = dataclasses.replace(unresolved, impact_ref="impact:resolved", resolved=True, frontier_refs=())
    goals = goals_from_impact((resolved,))
    assert len(goals) == 1
    assert goals[0].utility_components[0].value == 100.0


def test_rich_state_assignment_revalidates_content_addressed_value_identity():
    value = StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=12.5)
    assignment = StateAssignment(
        assignment_ref="assignment:1", holder_ref="r:1", dimension_ref="dimension:x",
        dimension_revision=1, value_ref="tampered:value-ref", value_revision=1,
        status=AssignmentStatus.ACTIVE, context_ref="actual", confidence=1.0,
        evidence_refs=("e:1",), value_document=value.document(),
    )
    with pytest.raises(Exception, match="content identity differs"):
        EntitledStateSpaceCompilerV351.assignment_value(assignment, None, store=None)
