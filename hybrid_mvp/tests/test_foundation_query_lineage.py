"""Exact current-ABI successors for the audited historical QUERY assertions."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import Fact, RevisionPin, memory_stores
from cemm_authoritative_hybrid.r3_artifacts import QueryResult, QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from tests.test_foundation_semantics import _matrix_situation


__cemm_test_inventory__ = {
    "tests/test_foundation_query_lineage.py::test_repeated_exact_query_returns_same_identity_and_status": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:query-engine-query-memoization-returns-same-result",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "2c2d6c484dbeff37f6b078337c850cea817864a8f74dd85917921f9c332d9ddd",
        "supersedes_node_id": "tests/test_query_engine.py::test_query_memoization_returns_same_result",
    },
    "tests/test_foundation_query_lineage.py::test_query_result_embeds_current_retrieval_lineage": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:query-engine-query-result-has-retrieval-receipt",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "bd739183602eca0ffd292e38c85ff83de2a7096fb8f3fcc65d8bd47681f01311",
        "supersedes_node_id": "tests/test_query_engine.py::test_query_result_has_retrieval_receipt",
    },
    "tests/test_foundation_query_lineage.py::test_no_evidence_is_unknown_not_false": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:query-engine-unknown-is-not-false",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "b0f3b849d57422b2c43428025081af8af9a3785873df341470765a2edf617495",
        "supersedes_node_id": "tests/test_query_engine.py::test_unknown_is_not_false",
    },
    "tests/test_foundation_query_lineage.py::test_two_hop_query_is_supported_with_multirule_proof": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:recursive-inference-recursive-inference-chains-multiple-hops",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "d008a5c28dd962fa7e7ff7a611e61d5ff39db94256129ca24a8194d1d8ea822c",
        "supersedes_node_id": "tests/test_recursive_inference.py::test_recursive_inference_chains_multiple_hops",
    },
    "tests/test_foundation_query_lineage.py::test_two_hop_proof_preserves_family_semantic_refs": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:recursive-inference-recursive-inference-proof-has-semantic-refs",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "688e2c677dd37ed43dc1b7d403c90461ace545f929615d30410285d9803edd68",
        "supersedes_node_id": "tests/test_recursive_inference.py::test_recursive_inference_proof_has_semantic_refs",
    },
    "tests/test_foundation_query_lineage.py::test_two_hop_proof_tracks_rule_refs": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:recursive-inference-recursive-inference-proof-tracks-rule-applications",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "c734a55468e974179a83a56e9fd0af29e0f02e9b2710eaf5fb6dd3076af2c6ee",
        "supersedes_node_id": "tests/test_recursive_inference.py::test_recursive_inference_proof_tracks_rule_applications",
    },
    "tests/test_foundation_query_lineage.py::test_two_hop_proof_has_source_refs": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:recursive-inference-recursive-inference-source-refs-include-programs",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "46a5fba258e987bb7c92c6cec708340d727aabf07e6439e658c969d89e312180",
        "supersedes_node_id": "tests/test_recursive_inference.py::test_recursive_inference_source_refs_include_programs",
    },
    "tests/test_foundation_query_lineage.py::test_unknown_entity_remains_unknown_with_rules_present": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:recursive-inference-recursive-inference-unknown-entity-is-unknown",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "b73668296d27dcfb3b150062ba0004582d47b84467490cf49dd1ba3757789bd1",
        "supersedes_node_id": "tests/test_recursive_inference.py::test_recursive_inference_unknown_entity_is_unknown",
    },
    "tests/test_foundation_query_lineage.py::test_seven_hop_exhaustion_is_explicit_at_configured_round_limit": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:inference-bounds-inference-exhaustion-is-explicit",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "4a37eb87b22e0439f3e56a5a3213d6c89a847e7e6498419ee5c763d745a0e2b8",
        "supersedes_node_id": "tests/test_inference_bounds.py::test_inference_exhaustion_is_explicit",
    },
    "tests/test_foundation_query_lineage.py::test_exhaustion_rounds_equal_configured_maximum": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:inference-bounds-inference-exhaustion-receipt-records-rounds",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "c43a18a246adbfdbe17c6961e4599c02961cc9dda05074696f3ceee562288c0a",
        "supersedes_node_id": "tests/test_inference_bounds.py::test_inference_exhaustion_receipt_records_rounds",
    },
    "tests/test_foundation_query_lineage.py::test_exhaustion_has_no_proof": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:inference-bounds-inference-exhaustion-has-no-proof",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "5cdfb36f8803b65cc1800b87a0d13dc1d2ce94914ab669fe5cfc65bbdc621d97",
        "supersedes_node_id": "tests/test_inference_bounds.py::test_inference_exhaustion_has_no_proof",
    },
    "tests/test_foundation_query_lineage.py::test_one_hop_inference_succeeds_within_bounds": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:inference-bounds-inference-within-bounds-succeeds",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "9ee68888d53e2cf09eda8b0eb49838decb2f3471a8f4802e6318d69d1a09190e",
        "supersedes_node_id": "tests/test_inference_bounds.py::test_inference_within_bounds_succeeds",
    },
}


@pytest.fixture
def stores():
    value = memory_stores(
        authority_generation="authority:query-lineage",
        model_identity="model:query-lineage",
    )
    try:
        yield value
    finally:
        value.close()


def _relation_clause(predicate: str, subject: str, object_ref: str) -> dict[str, object]:
    return {
        "operator": "op:relation",
        "args": {
            "predicate_ref": predicate,
            "role:subject": subject,
            "role:object": object_ref,
        },
    }


def _state_clause(subject: str) -> dict[str, object]:
    return {
        "operator": "op:state",
        "args": {
            "predicate_ref": "state:married",
            "role:subject": subject,
            "role:dimension": "dim:marital_status",
            "role:value": "state:married",
        },
    }


def _rule(ref: str, antecedent: tuple[dict[str, object], ...], consequent: tuple[dict[str, object], ...]):
    return SimpleNamespace(
        rule_ref=ref,
        reviewed=True,
        source_ref=f"review:{ref}",
        antecedent=antecedent,
        consequent=consequent,
    )


def _expression(operator: str, predicate: str, roles: dict[str, str]) -> SemanticExpression:
    application_ref = stable_ref(
        "application",
        {"operator": operator, "predicate_ref": predicate, "roles": roles},
    )
    application = SemanticApplication(
        application_ref=application_ref,
        operator=operator,
        predicate_ref=predicate,
        roles=tuple(
            RoleBinding(role_ref, GroundedReference(target_ref))
            for role_ref, target_ref in sorted(roles.items())
        ),
    )
    return SemanticExpression.create(
        applications=(application,),
        root_refs=(application.application_ref,),
    )


def _relation_expression(predicate: str, subject: str, object_ref: str) -> SemanticExpression:
    return _expression(
        "op:relation",
        predicate,
        {"role:subject": subject, "role:object": object_ref},
    )


def _married_expression(subject: str) -> SemanticExpression:
    return _expression(
        "op:state",
        "state:married",
        {
            "role:subject": subject,
            "role:dimension": "dim:marital_status",
            "role:value": "state:married",
        },
    )


def _ask(stores, expression: SemanticExpression, rules=()) -> QueryResult:
    authority = SimpleNamespace(
        generation=stores.revision_pin().authority_generation,
        content_hash="authority_content:query-lineage",
        atoms={},
        capabilities={},
        rules={row.rule_ref: row for row in rules},
    )
    situation = _matrix_situation(stores)
    assert isinstance(situation.revision_pin, RevisionPin)
    evaluation = QueryDecisionOwner(
        stores,
        RuntimeConfig.release(),
        authority,
    ).evaluate_full(expression, project_expression(expression), situation)
    result = evaluation.query_results[0]
    assert result.revision_pin == situation.revision_pin == stores.revision_pin()
    return result


def _world_snapshot(stores):
    return stores.revisions(), stores.r3_world_facts()


def _seed_family_chain(stores):
    stores.world.commit(
        (
            Fact(
                "fact:mother",
                "op:relation",
                {
                    "predicate_ref": "concept:mother",
                    "role:subject": "entity:mary",
                    "role:object": "entity:carol",
                },
                proof={"source": "source:arrival-mother"},
            ),
            Fact(
                "fact:in-law",
                "op:relation",
                {
                    "predicate_ref": "relation:in-law",
                    "role:subject": "entity:mary",
                    "role:object": "entity:carol",
                },
                proof={"source": "source:arrival-in-law"},
            ),
        ),
        expected_revision=0,
    )
    rules = (
        _rule(
            "rule:family-partner",
            (
                _relation_clause("concept:mother", "?mother", "?person"),
                _relation_clause("relation:in-law", "?mother", "?person"),
            ),
            (_relation_clause("relation:wedded", "?person", "entity:partner"),),
        ),
        _rule(
            "rule:family-married",
            (_relation_clause("relation:wedded", "?person", "?partner"),),
            (_state_clause("?person"),),
        ),
    )
    return rules


def _seed_seven_hop_chain(stores):
    stores.world.commit(
        (
            Fact(
                "fact:chain-0",
                "op:relation",
                {
                    "predicate_ref": "relation:chain-0",
                    "role:subject": "entity:alice",
                    "role:object": "entity:bob",
                },
                proof={"source": "source:chain-0"},
            ),
        ),
        expected_revision=0,
    )
    return tuple(
        _rule(
            f"rule:chain-{index}-{index + 1}",
            (_relation_clause(f"relation:chain-{index}", "?x", "?y"),),
            (_relation_clause(f"relation:chain-{index + 1}", "?x", "?y"),),
        )
        for index in range(7)
    )


def test_repeated_exact_query_returns_same_identity_and_status(stores) -> None:
    expression = _relation_expression("relation:likes", "entity:alice", "entity:bob")
    before = _world_snapshot(stores)

    first = _ask(stores, expression)
    second = _ask(stores, expression)

    assert first.query_result_ref == second.query_result_ref
    assert first.status is second.status
    assert _world_snapshot(stores) == before


def test_query_result_embeds_current_retrieval_lineage(stores) -> None:
    stores.world.commit(
        (
            Fact(
                "fact:query-lineage-retrieval",
                "op:relation",
                {
                    "predicate_ref": "relation:likes",
                    "role:subject": "entity:alice",
                    "role:object": "entity:bob",
                },
                proof={"source": "source:query-lineage-retrieval"},
            ),
        ),
        expected_revision=0,
    )
    expression = _relation_expression("relation:likes", "entity:alice", "entity:bob")
    pin = stores.revision_pin()
    before = _world_snapshot(stores)

    result = _ask(stores, expression)
    restored = QueryResult.from_dict(result.as_dict())

    assert isinstance(result, QueryResult)
    assert not hasattr(result, "retrieval_receipt")
    assert result.retrieval_refs == ("fact:query-lineage-retrieval",)
    assert result.rounds == 1
    assert result.revision_pin == pin
    assert restored.query_result_ref == result.query_result_ref
    assert restored.as_dict() == result.as_dict()
    assert _world_snapshot(stores) == before


def test_no_evidence_is_unknown_not_false(stores) -> None:
    expression = _married_expression("entity:unobserved")
    before = _world_snapshot(stores)

    result = _ask(stores, expression)

    assert result.status is QueryStatus.UNKNOWN
    assert result.proof is None
    assert _world_snapshot(stores) == before


def test_two_hop_query_is_supported_with_multirule_proof(stores) -> None:
    rules = _seed_family_chain(stores)
    before = _world_snapshot(stores)

    result = _ask(stores, _married_expression("entity:carol"), rules)

    assert result.status is QueryStatus.SUPPORTED
    assert result.proof is not None
    assert len(result.proof.rule_refs) >= 2
    assert _world_snapshot(stores) == before


def test_two_hop_proof_preserves_family_semantic_refs(stores) -> None:
    rules = _seed_family_chain(stores)
    before = _world_snapshot(stores)

    result = _ask(stores, _married_expression("entity:carol"), rules)

    assert result.status is QueryStatus.SUPPORTED
    assert result.proof is not None
    assert {
        "concept:mother",
        "relation:in-law",
        "state:married",
    } <= set(result.proof.semantic_refs)
    assert _world_snapshot(stores) == before


def test_two_hop_proof_tracks_rule_refs(stores) -> None:
    rules = _seed_family_chain(stores)
    before = _world_snapshot(stores)

    result = _ask(stores, _married_expression("entity:carol"), rules)

    assert result.status is QueryStatus.SUPPORTED
    assert result.proof is not None
    assert result.proof.rule_refs
    assert all(ref.startswith("rule:") for ref in result.proof.rule_refs)
    assert _world_snapshot(stores) == before


def test_two_hop_proof_has_source_refs(stores) -> None:
    rules = _seed_family_chain(stores)
    before = _world_snapshot(stores)

    result = _ask(stores, _married_expression("entity:carol"), rules)

    assert result.status is QueryStatus.SUPPORTED
    assert result.proof is not None
    assert result.proof.source_refs
    assert _world_snapshot(stores) == before


def test_unknown_entity_remains_unknown_with_rules_present(stores) -> None:
    rules = _seed_family_chain(stores)
    before = _world_snapshot(stores)

    result = _ask(stores, _married_expression("entity:bob"), rules)

    assert result.status is QueryStatus.UNKNOWN
    assert result.proof is None
    assert _world_snapshot(stores) == before


def test_seven_hop_exhaustion_is_explicit_at_configured_round_limit(stores) -> None:
    rules = _seed_seven_hop_chain(stores)
    config = RuntimeConfig.release()
    before = _world_snapshot(stores)

    result = _ask(
        stores,
        _relation_expression("relation:chain-7", "entity:alice", "entity:bob"),
        rules,
    )

    assert result.status is QueryStatus.BUDGET_EXHAUSTED
    assert result.rounds == config.max_inference_rounds
    assert _world_snapshot(stores) == before


def test_exhaustion_rounds_equal_configured_maximum(stores) -> None:
    rules = _seed_seven_hop_chain(stores)
    config = RuntimeConfig.release()
    before = _world_snapshot(stores)

    result = _ask(
        stores,
        _relation_expression("relation:chain-7", "entity:alice", "entity:bob"),
        rules,
    )

    assert result.status is QueryStatus.BUDGET_EXHAUSTED
    assert result.rounds == config.max_inference_rounds
    assert _world_snapshot(stores) == before


def test_exhaustion_has_no_proof(stores) -> None:
    rules = _seed_seven_hop_chain(stores)
    before = _world_snapshot(stores)

    result = _ask(
        stores,
        _relation_expression("relation:chain-7", "entity:alice", "entity:bob"),
        rules,
    )

    assert result.status is QueryStatus.BUDGET_EXHAUSTED
    assert result.proof is None
    assert _world_snapshot(stores) == before


def test_one_hop_inference_succeeds_within_bounds(stores) -> None:
    stores.world.commit(
        (
            Fact(
                "fact:one-hop-base",
                "op:relation",
                {
                    "predicate_ref": "relation:chain",
                    "role:subject": "entity:alice",
                    "role:object": "entity:bob",
                },
                proof={"source": "source:one-hop-base"},
            ),
        ),
        expected_revision=0,
    )
    one_hop = _rule(
        "rule:chain-implies-linked",
        (_relation_clause("relation:chain", "?x", "?y"),),
        (
            {
                "operator": "op:state",
                "args": {
                    "predicate_ref": "state:linked",
                    "role:subject": "?x",
                    "role:dimension": "dim:linkage",
                    "role:value": "state:linked",
                },
            },
        ),
    )
    expression = _expression(
        "op:state",
        "state:linked",
        {
            "role:subject": "entity:alice",
            "role:dimension": "dim:linkage",
            "role:value": "state:linked",
        },
    )
    before = _world_snapshot(stores)

    result = _ask(stores, expression, (one_hop,))

    assert result.status is QueryStatus.SUPPORTED
    assert result.proof is not None
    assert _world_snapshot(stores) == before
