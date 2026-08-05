from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import (
    DECISION_ABI_VERSION,
    Decision,
    DecisionAction,
    DecisionContribution,
    DecisionStatus,
    ExactDecisionEvaluator,
)
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.situation import SituationContext

__cemm_test_inventory__ = {
    "tests/test_r3_decision_abi.py::test_decision_identity_covers_proof_refs": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-decision-identity-covers-proof-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3cd0189066f70616b1f6729a6afa784e8ea3cb9f138a6b420d406319607493a5"
    },
    "tests/test_r3_decision_abi.py::test_evaluate_rejects_raw_program_like_object": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-evaluate-rejects-raw-program-like-object",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "80b07b3b8e9072cbe5b7530e2cacdfedd21c0a505ff0384b3390237186755eb2"
    },
    "tests/test_r3_decision_abi.py::test_evaluator_requires_all_four_closed_modes": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-evaluator-requires-all-four-closed-modes",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "f7c6dda0db744404f13f893fcf3c91e661ce5f86880f9761f2e1eb3bc97d3ec0"
    },
    "tests/test_r3_decision_abi.py::test_exact_evaluator_consumes_verified_meaning_and_situation": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-exact-evaluator-consumes-verified-meaning-and-situation",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0c55842942eef6cad2724c11fd2ace0cf8f292575dbaa8033a222031afb103c4"
    }
}



def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def _expression() -> SemanticExpression:
    app = SemanticApplication(
        application_ref="application:query",
        operator="op:relation",
        predicate_ref="relation:likes",
        roles=(
            RoleBinding("role:subject", GroundedReference("entity:alice")),
            RoleBinding("role:object", GroundedReference("entity:bob")),
        ),
    )
    return SemanticExpression.create(
        applications=(app,),
        root_refs=("application:query",),
    )


def _meaning() -> VerifiedMeaning:
    return VerifiedMeaning.create(
        program_ref="program:derivation-one",
        expression=_expression(),
        grounding_refs=("grounding:alice", "grounding:bob"),
        coverage_receipt_ref="coverage:test",
        compilation_proof_ref="compilation_proof:test",
        verification_receipt_ref="verification_receipt:test",
        revision_pin=_pin(),
    )


def _situation() -> SituationContext:
    return SituationContext.create(
        orientation_ref="orientation:test",
        proposal_context_ref="proposal_context:test",
        mode=SemanticMode.QUERY,
        session_ref="session:test",
        turn_ref="turn:test",
        turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref=None,
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref="snapshot:focus:test",
        focus_refs=(),
        obligation_snapshot_ref="snapshot:obligation:test",
        obligation_refs=(),
        capability_refs=("cap:answer",),
        permission_snapshot_ref="snapshot:permission:test",
        permission_refs=(),
        resource_snapshot_ref="snapshot:resource:test",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:test",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:test",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=("evidence:test",),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active_turn",
        revision_pin=_pin(),
    )


class _QueryOwner:
    def evaluate(self, expression, projection, situation):
        assert expression.expression_ref == projection.expression_ref
        assert situation.mode is SemanticMode.QUERY
        return DecisionContribution(
            status=DecisionStatus.SUPPORTED,
            action=DecisionAction.ANSWER,
            answer_expression_ref=expression.expression_ref,
            query_result_refs=("query_result:test",),
            proof_refs=("proof:test",),
            source_refs=("fact:test",),
            policy_refs=("policy:query",),
        )


class _UnusedOwner:
    def evaluate(self, expression, projection, situation):
        raise AssertionError("wrong semantic mode owner selected")


def _evaluator() -> ExactDecisionEvaluator:
    return ExactDecisionEvaluator(
        {
            SemanticMode.OBSERVE: _UnusedOwner(),
            SemanticMode.QUERY: _QueryOwner(),
            SemanticMode.REQUEST: _UnusedOwner(),
            SemanticMode.SIMULATE: _UnusedOwner(),
        }
    )


def test_exact_evaluator_consumes_verified_meaning_and_situation() -> None:
    decision = _evaluator().evaluate(_meaning(), _situation())
    assert decision.abi_version == DECISION_ABI_VERSION
    assert decision.status is DecisionStatus.SUPPORTED
    assert decision.action is DecisionAction.ANSWER
    assert decision.expression_ref == _meaning().expression.expression_ref
    assert Decision.from_dict(decision.as_dict()) == decision


def test_evaluate_rejects_raw_program_like_object() -> None:
    with pytest.raises(TypeError, match="VerifiedMeaning"):
        _evaluator().evaluate(object(), _situation())


def test_decision_identity_covers_proof_refs() -> None:
    meaning = _meaning()
    situation = _situation()
    left = Decision.create(
        meaning=meaning,
        situation=situation,
        contribution=DecisionContribution(
            status=DecisionStatus.SUPPORTED,
            action=DecisionAction.ANSWER,
            answer_expression_ref=meaning.expression.expression_ref,
            query_result_refs=("query_result:test",),
            proof_refs=("proof:left",),
        ),
    )
    right = Decision.create(
        meaning=meaning,
        situation=situation,
        contribution=DecisionContribution(
            status=DecisionStatus.SUPPORTED,
            action=DecisionAction.ANSWER,
            answer_expression_ref=meaning.expression.expression_ref,
            query_result_refs=("query_result:test",),
            proof_refs=("proof:right",),
        ),
    )
    assert left.decision_ref != right.decision_ref


def test_evaluator_requires_all_four_closed_modes() -> None:
    with pytest.raises(ValueError, match="exact SemanticMode set"):
        ExactDecisionEvaluator({SemanticMode.QUERY: _QueryOwner()})
