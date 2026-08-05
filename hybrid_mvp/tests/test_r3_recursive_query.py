from __future__ import annotations

from types import SimpleNamespace

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import Fact, RevisionPin, memory_stores
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from cemm_authoritative_hybrid.situation import SituationContext

__cemm_test_inventory__ = {
    "tests/test_r3_recursive_query.py::test_query_owner_applies_reviewed_rules_with_proof_lineage": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-query-reviewed-rule-proof-lineage",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "eb6b63bc3d9a41baf5eed865773402c082385d4e8010223a7a08f58969c6df28"
    }
}


def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 1, 0, 0, 0, "model:test")


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
        capability_refs=(),
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
        source_refs=("source:test",),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active",
        revision_pin=_pin(),
    )


def test_query_owner_applies_reviewed_rules_with_proof_lineage():
    stores = memory_stores(
        authority_generation="authority:test", model_identity="model:test"
    )
    stores.world.commit(
        (
            Fact(
                fact_ref="fact:likes",
                operator="op:relation",
                args={
                    "predicate_ref": "relation:likes",
                    "role:subject": "entity:alice",
                    "role:object": "entity:bob",
                },
                proof={"source": "source:observation"},
            ),
        ),
        expected_revision=0,
    )
    rule = SimpleNamespace(
        rule_ref="rule:likes_implies_knows",
        reviewed=True,
        source_ref="review:rule",
        antecedent=(
            {
                "operator": "op:relation",
                "args": {
                    "predicate_ref": "relation:likes",
                    "role:subject": "?subject",
                    "role:object": "?object",
                },
            },
        ),
        consequent=(
            {
                "operator": "op:relation",
                "args": {
                    "predicate_ref": "relation:knows",
                    "role:subject": "?subject",
                    "role:object": "?object",
                },
            },
        ),
    )
    authority = SimpleNamespace(rules={rule.rule_ref: rule})
    app = SemanticApplication(
        application_ref="application:query",
        operator="op:relation",
        predicate_ref="relation:knows",
        roles=(
            RoleBinding("role:subject", GroundedReference("entity:alice")),
            RoleBinding("role:object", GroundedReference("entity:bob")),
        ),
    )
    expression = SemanticExpression.create(
        applications=(app,), root_refs=(app.application_ref,)
    )
    result = QueryDecisionOwner(
        stores, RuntimeConfig.release(), authority
    ).evaluate_full(expression, project_expression(expression), _situation())
    query = result.query_results[0]
    assert query.status is QueryStatus.SUPPORTED
    assert query.proof is not None
    assert query.proof.rule_refs == (rule.rule_ref,)
    assert "source:observation" in query.proof.source_refs
