from __future__ import annotations

from dataclasses import replace

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    LiteralValue,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
from cemm_authoritative_hybrid.r3_learning import LearningCoordinator
from cemm_authoritative_hybrid.situation import SituationContext

__cemm_test_inventory__ = {
    "tests/test_r3_learning_transaction.py::test_learning_decision_materializes_exact_evaluated_draft": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-learning-decision-materializes-exact-evaluated-draft",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Closeout",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "bd2bcbd5fe18c6fb446368ff69f40dfdb902282e3f24da3a5c8ba65cfec3781a",
    },
    "tests/test_r3_learning_transaction.py::test_learning_finalization_rejects_unbound_draft_ref": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-learning-finalization-rejects-unbound-draft-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Closeout",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "679abbb236ca8643b7376ded661a2a594912805068f36dbc5746edd515fb11d0",
    },
    "tests/test_r3_learning_transaction.py::test_incomplete_designation_requests_clarification_without_learning_draft": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-incomplete-designation-clarifies-without-learning-draft",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Closeout",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1c691c9d3206d47dcf11b1c3711bb873b745d34b27388f99a5f58f8c80f35331",
    },
}


def _meaning(pin, *, include_target: bool = True) -> VerifiedMeaning:
    roles = [
        RoleBinding("role:surface", LiteralValue("string", "cheerful")),
    ]
    if include_target:
        roles.append(RoleBinding("role:target", GroundedReference("event:greeting")))
    application = SemanticApplication(
        application_ref="application:learn-designation",
        operator="op:designation",
        predicate_ref="event:greeting",
        roles=tuple(roles),
    )
    expression = SemanticExpression.create(
        applications=(application,),
        root_refs=(application.application_ref,),
    )
    return VerifiedMeaning.create(
        program_ref="program:learning-derivation",
        expression=expression,
        grounding_refs=("grounding:learning",),
        coverage_receipt_ref="coverage:learning",
        compilation_proof_ref="compilation_proof:learning",
        verification_receipt_ref="verification_receipt:learning",
        revision_pin=pin,
    )


def _situation(pin) -> SituationContext:
    return SituationContext.create(
        orientation_ref="orientation:learning",
        proposal_context_ref="proposal_context:learning",
        mode=SemanticMode.REQUEST,
        session_ref="session:learning",
        turn_ref="turn:learning",
        turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref="participant:user",
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref="snapshot:focus:learning",
        focus_refs=(),
        obligation_snapshot_ref="snapshot:obligation:learning",
        obligation_refs=(),
        capability_refs=("cap:learn",),
        permission_snapshot_ref="snapshot:permission:learning",
        permission_refs=("permission:learn_designation",),
        resource_snapshot_ref="snapshot:resource:learning",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:learning",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:learning",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=("evidence:learning",),
        epistemic_scope_ref="epistemic_scope:request",
        session_phase_ref="session_phase:active_turn",
        revision_pin=pin,
    )


def test_learning_decision_materializes_exact_evaluated_draft(
    linked_authority, memory_stores_fixture
) -> None:
    pin = memory_stores_fixture.revision_pin()
    meaning = _meaning(pin)
    situation = _situation(pin)
    evaluator = R3EvaluationOwner(
        linked_authority, memory_stores_fixture, RuntimeConfig.release()
    )

    evaluation = evaluator.evaluate(meaning, situation)

    assert evaluation.decision.status is DecisionStatus.PENDING
    assert evaluation.decision.action is DecisionAction.CREATE_LEARNING_OBLIGATION
    assert len(evaluation.learning_drafts) == 1
    draft = evaluation.learning_drafts[0]
    assert evaluation.decision.learning_draft_refs == (draft.learning_draft_ref,)

    plan, obligation = LearningCoordinator(
        linked_authority, memory_stores_fixture
    ).materialize(evaluation, meaning, situation)

    assert plan is not None
    assert obligation is not None
    assert plan.decision_ref == evaluation.decision.decision_ref
    assert plan.surface_literal == draft.surface_literal
    assert plan.target_ref == draft.target_ref
    assert plan.expected_target_kinds == draft.expected_target_kinds
    assert plan.answer_contract_ref == draft.answer_contract_ref
    assert draft.learning_draft_ref in plan.provenance_refs
    assert obligation.plan_ref == plan.plan_ref


def test_learning_finalization_rejects_unbound_draft_ref(
    linked_authority, memory_stores_fixture
) -> None:
    pin = memory_stores_fixture.revision_pin()
    meaning = _meaning(pin)
    situation = _situation(pin)
    evaluator = R3EvaluationOwner(
        linked_authority, memory_stores_fixture, RuntimeConfig.release()
    )
    mode_result = evaluator.evaluate_mode(meaning, situation)
    tampered = replace(
        mode_result.contribution,
        learning_draft_refs=("learning_draft:tampered",),
    )

    with pytest.raises(
        ValueError, match="Decision learning_draft_refs does not match included artifacts"
    ):
        evaluator.finalize(meaning, situation, mode_result, tampered)


def test_incomplete_designation_requests_clarification_without_learning_draft(
    linked_authority, memory_stores_fixture
) -> None:
    pin = memory_stores_fixture.revision_pin()
    meaning = _meaning(pin, include_target=False)
    situation = _situation(pin)
    evaluator = R3EvaluationOwner(
        linked_authority, memory_stores_fixture, RuntimeConfig.release()
    )

    evaluation = evaluator.evaluate(meaning, situation)

    assert evaluation.decision.status is DecisionStatus.UNKNOWN
    assert evaluation.decision.action is DecisionAction.REQUEST_CLARIFICATION
    assert evaluation.decision.blocker_refs == ("learning:target_missing",)
    assert evaluation.learning_drafts == ()
