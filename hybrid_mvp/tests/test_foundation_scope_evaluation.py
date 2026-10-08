"""Execution-level semantic gold: time/causality must not be invented.

Canonical graph identity alone is insufficient: the actual QUERY owner may not
return SUPPORT unless it can evaluate the named scope or nonlogical link using
admitted facts/relations. These cases have facts but NO time/causal proof.
"""
from __future__ import annotations

from types import SimpleNamespace
import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, RoleBinding, SemanticApplication,
    SemanticExpression, ExpressionLink, ScopeOperator,
)
from cemm_authoritative_hybrid.persistence import Fact, memory_stores
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from cemm_authoritative_hybrid.situation import SituationContext


def situation(pin):
    return SituationContext.create(
        orientation_ref="orientation:unlicensed-scope",
        proposal_context_ref="proposal_context:unlicensed-scope",
        mode=SemanticMode.QUERY, session_ref="session:scope",
        turn_ref="turn:scope", turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user", addressee_ref="participant:system",
        actor_ref=None, temporal_frame_ref="time:now",
        active_event_refs=(), focus_snapshot_ref="snapshot:focus:scope",
        focus_refs=(), obligation_snapshot_ref="snapshot:obligation:scope",
        obligation_refs=(), capability_refs=(),
        permission_snapshot_ref="snapshot:permission:scope",
        permission_refs=(), resource_snapshot_ref="snapshot:resource:scope",
        resource_refs=(), adapter_snapshot_ref="snapshot:adapter:scope",
        adapter_refs=(), evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:scope",),
        adapter_receipt_refs=(), trusted_observation=False,
        source_refs=("source:query",),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active", revision_pin=pin,
    )


def app(local, owner):
    return SemanticApplication(
        local, "op:relation", "rel:owns",
        (
            RoleBinding("role:subject", GroundedReference(owner)),
            RoleBinding("role:object", GroundedReference("entity:book")),
        ),
    )


def evaluated(expression, facts):
    stores = memory_stores(
        authority_generation="authority:semantic-scope",
        model_identity="model:reference",
    )
    try:
        stores.world.commit(tuple(facts), expected_revision=0)
        pin = stores.revision_pin()
        authority = SimpleNamespace(rules={})
        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority,
        ).evaluate_full(expression, project_expression(expression), situation(pin))
        assert stores.revision_pin() == pin
        return result
    finally:
        stores.close()


def evidence(owner, ref):
    return Fact(
        fact_ref=ref, operator="op:relation",
        args={
            "predicate_ref": "rel:owns",
            "role:subject": owner,
            "role:object": "entity:book",
        },
        proof={"source": "source:unqualified-present", "placement": "observed"},
    )


@pytest.mark.parametrize("scope,value", [
    ("scope:tense", "scope_value:tense:past"),
    ("scope:aspect", "scope_value:aspect:completed"),
])
def test_unqualified_world_fact_does_not_prove_temporally_scoped_claim(scope, value):
    atom = app("app:a", "entity:alice")
    expression = SemanticExpression.create(
        applications=(atom,),
        scope_operators=(ScopeOperator("scope:restricted", scope, value, atom.application_ref),),
        root_refs=("scope:restricted",),
    )
    result = evaluated(expression, (evidence("entity:alice", "fact:alice"),))
    assert result.query_results[0].status is QueryStatus.PARTIAL
    assert "scope:temporal_evaluation_not_admitted" in result.contribution.blocker_refs


@pytest.mark.parametrize("link", [
    "link:cause", "link:sequence", "link:purpose",
    "link:contrast", "link:condition", "link:coordination",
])
def test_two_supported_facts_do_not_prove_nonlogical_link(link):
    a, b = app("app:a", "entity:alice"), app("app:b", "entity:bob")
    expression = SemanticExpression.create(
        applications=(a, b),
        expression_links=(ExpressionLink("link:root", link, (a.application_ref, b.application_ref)),),
        root_refs=("link:root",),
    )
    result = evaluated(expression, (
        evidence("entity:alice", "fact:alice"),
        evidence("entity:bob", "fact:bob"),
    ))
    assert result.query_results[0].status is QueryStatus.PARTIAL
    assert "link:semantics_not_admitted" in result.contribution.blocker_refs


def test_genuine_conjunction_of_supported_facts_remains_supported():
    a, b = app("app:a", "entity:alice"), app("app:b", "entity:bob")
    expression = SemanticExpression.create(
        applications=(a, b),
        expression_links=(ExpressionLink("link:root", "link:conjunction", (a.application_ref, b.application_ref)),),
        root_refs=("link:root",),
    )
    result = evaluated(expression, (
        evidence("entity:alice", "fact:alice"),
        evidence("entity:bob", "fact:bob"),
    ))
    assert result.query_results[0].status is QueryStatus.SUPPORTED
