"""Novel data-and-rule composition gold, independent of language fixtures.

This probes the exact R3 query owner against reviewed multi-hop rule inference.
It proves the structured semantic half of the cognitive architecture only.
"""
from __future__ import annotations

from types import SimpleNamespace

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, RoleBinding, SemanticApplication, SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import Fact, memory_stores
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from cemm_authoritative_hybrid.situation import SituationContext


def situation(pin):
    return SituationContext.create(
        orientation_ref="orientation:foundation-inference",
        proposal_context_ref="proposal_context:foundation-inference",
        mode=SemanticMode.QUERY,
        session_ref="session:foundation-inference",
        turn_ref="turn:foundation-inference",
        turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref=None,
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref="snapshot:focus:foundation",
        focus_refs=(),
        obligation_snapshot_ref="snapshot:obligation:foundation",
        obligation_refs=(),
        capability_refs=(),
        permission_snapshot_ref="snapshot:permission:foundation",
        permission_refs=(),
        resource_snapshot_ref="snapshot:resource:foundation",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:foundation",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:foundation",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=("source:foundation-query",),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active",
        revision_pin=pin,
    )


def rule(name, antecedent_predicate, consequent_predicate):
    return SimpleNamespace(
        rule_ref=f"rule:{name}",
        reviewed=True,
        source_ref=f"review:{name}",
        antecedent=({
            "operator": "op:relation",
            "args": {
                "predicate_ref": antecedent_predicate,
                "role:subject": "?subject",
                "role:object": "?object",
            },
        },),
        consequent=({
            "operator": "op:relation",
            "args": {
                "predicate_ref": consequent_predicate,
                "role:subject": "?subject",
                "role:object": "?object",
            },
        },),
    )


def expression(subject="entity:ada", obj="entity:bob"):
    app = SemanticApplication(
        "application:foundation-query", "op:relation", "relation:trusts",
        (
            RoleBinding("role:subject", GroundedReference(subject)),
            RoleBinding("role:object", GroundedReference(obj)),
        ),
    )
    return SemanticExpression.create(
        applications=(app,), root_refs=(app.application_ref,)
    )


def test_two_reviewed_rules_compose_and_carry_grounded_proof():
    stores = memory_stores(
        authority_generation="authority:foundation", model_identity="model:reference"
    )
    try:
        stores.world.commit(
            (
                Fact(
                    fact_ref="fact:foundation-likes",
                    operator="op:relation",
                    args={
                        "predicate_ref": "relation:likes",
                        "role:subject": "entity:ada",
                        "role:object": "entity:bob",
                    },
                    proof={"source": "source:independent-observation"},
                ),
            ),
            expected_revision=0,
        )
        r1 = rule("likes-to-knows", "relation:likes", "relation:knows")
        r2 = rule("knows-to-trusts", "relation:knows", "relation:trusts")
        authority = SimpleNamespace(rules={r1.rule_ref: r1, r2.rule_ref: r2})
        x = expression()
        before = stores.revision_pin()
        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).evaluate_full(x, project_expression(x), situation(before))
        query = result.query_results[0]
        assert query.status is QueryStatus.SUPPORTED
        assert query.proof is not None
        assert {r1.rule_ref, r2.rule_ref} <= set(query.proof.rule_refs)
        assert "source:independent-observation" in query.proof.source_refs
        assert stores.revision_pin() == before, "read-only query mutated persistent state"
    finally:
        stores.close()


def test_unmatched_subject_cannot_inherit_another_subjects_inference():
    stores = memory_stores(
        authority_generation="authority:foundation", model_identity="model:reference"
    )
    try:
        stores.world.commit(
            (
                Fact(
                    fact_ref="fact:foundation-likes",
                    operator="op:relation",
                    args={
                        "predicate_ref": "relation:likes",
                        "role:subject": "entity:ada",
                        "role:object": "entity:bob",
                    },
                    proof={"source": "source:independent-observation"},
                ),
            ),
            expected_revision=0,
        )
        r1 = rule("likes-to-knows", "relation:likes", "relation:knows")
        r2 = rule("knows-to-trusts", "relation:knows", "relation:trusts")
        authority = SimpleNamespace(rules={r1.rule_ref: r1, r2.rule_ref: r2})
        x = expression(subject="entity:carol", obj="entity:bob")
        before = stores.revision_pin()
        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).evaluate_full(x, project_expression(x), situation(before))
        query = result.query_results[0]
        assert query.status is not QueryStatus.SUPPORTED
        assert stores.revision_pin() == before
    finally:
        stores.close()
