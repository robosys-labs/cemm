"""R3 Learning Plan ABI 2 and Response Meaning ABI 2 tests."""
from __future__ import annotations

from cemm_authoritative_hybrid.cycle import CycleStatus, SemanticMode
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r3_learning import LearningPlan
from cemm_authoritative_hybrid.r3_response import ResponseMeaning

__cemm_test_inventory__ = {
    "tests/test_r3_learning_response.py::test_learning_plan_abi2_round_trip_binds_semantic_lineage": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-learning-plan-abi2-round-trip-binds-semantic-lineage",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "learning-response",
        "source_ast_sha256": "610ed4b1fa96bf1905473e689607a768e41ffdf6baaad89af3c05b2ed3ed8212"
    },
    "tests/test_r3_learning_response.py::test_response_meaning_round_trip_has_no_surface_text": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-response-meaning-round-trip-has-no-surface-text",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "learning-response",
        "source_ast_sha256": "96dc1d0bf10e208b208e5471b38ceac4d8cb84155b8c616866a90e91c8f525c0"
    }
}



def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def _expression() -> SemanticExpression:
    app = SemanticApplication(
        "application:test",
        "op:designation",
        "event:greeting",
        (RoleBinding("role:target", GroundedReference("event:greeting")),),
    )
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


def test_learning_plan_abi2_round_trip_binds_semantic_lineage() -> None:
    value = LearningPlan.create(
        contract_ref="contract:designation-learning",
        verified_meaning_ref="meaning:test",
        expression_ref="expression:test",
        situation_ref="situation:test",
        decision_ref="decision:test",
        source_query_ref="query:test",
        goal_ref="goal:learn",
        capability_ref="cap:learn",
        permission_ref="permission:learn",
        commit_operator_ref="op:designation",
        surface_literal="cheerful",
        target_ref="value:happy",
        expected_target_kinds=("state_value",),
        answer_contract_ref="contract:learning-answer",
        provenance_refs=("proof:test",),
        revision_pin=_pin(),
        expires_at_turn=2,
        obligation_ref="obligation:test",
    )
    assert LearningPlan.from_dict(value.as_dict()) == value


def test_response_meaning_round_trip_has_no_surface_text() -> None:
    expression = _expression()
    value = ResponseMeaning.create(
        decision_ref="decision:test",
        verified_meaning_ref="meaning:test",
        source_expression_ref=expression.expression_ref,
        response_expression=expression,
        situation_ref="situation:test",
        effect_outcome_ref="no_effect:test",
        learning_plan_ref=None,
        obligation_ref=None,
        mode=SemanticMode.QUERY,
        cycle_status=CycleStatus.PARTIAL,
        discourse_action="answer",
        bindings=(("?answer", "value:happy"),),
        polarity_ref="polarity:positive",
        modality_ref="modality:actual",
        epistemic_status_ref="epistemic_status:supported",
        source_refs=("fact:test",),
        proof_refs=("proof:test",),
        blocker_refs=(),
        policy_refs=("policy:query",),
        permitted_omissions=(),
        revision_pin=_pin(),
    )
    assert ResponseMeaning.from_dict(value.as_dict()) == value
    assert "surface" not in value.as_dict()
