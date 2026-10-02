"""Exact authority-generation boundary for indexed R3 queries."""

from contextlib import contextmanager
import json

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinkError, RuleRecord
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.persistence import Fact, StaleRevisionError, memory_stores
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from tests.test_foundation_semantics import (
    _matrix_expression,
    _matrix_relation,
    _matrix_situation,
)


__cemm_test_inventory__ = {
    "tests/test_foundation_query_authority_snapshot.py::test_query_rejects_authority_generation_drift_before_refresh": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rejects-authority-generation-drift-before-refresh",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "6893844ca02104b65b7e37275d232aecca39005809994e6cc540220358d39e57",
    },
    "tests/test_foundation_query_authority_snapshot.py::test_linked_authority_rules_are_not_mutable_in_place": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-linked-authority-rules-are-not-mutable-in-place",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "38d8fc58334dd7fb607abd8ba774ab2c1beca576f1999cc0b31c7ee0f2230fde",
    },
    "tests/test_foundation_query_authority_snapshot.py::test_linked_authority_rule_clauses_are_deeply_immutable_and_serializable": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-linked-authority-rule-clauses-are-deeply-immutable-and-serializable",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c40c980ae933f96672a2e43c09876096f41852c9a49d025c873043954b19bfc5",
    },
    "tests/test_foundation_query_authority_snapshot.py::test_rule_record_rejects_malformed_clause_stance": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-rule-record-rejects-malformed-clause-stance",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "8b76f49c96c58a8dfb11c7399c0fe35bb54ec2bef75f2505ba9fae616be7b6e1",
    },
    "tests/test_foundation_query_authority_snapshot.py::test_query_rejects_rule_publication_interleaved_after_pin_check": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rejects-rule-publication-interleaved-after-pin-check",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e2d2abd91fd9f505ec46d010545b59dda67beb315ea9ce387381609fa6827f0b",
    },
    "tests/test_foundation_query_authority_snapshot.py::test_query_owner_activates_exact_rule_generation_snapshot": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-owner-activates-exact-rule-generation-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0fe46aec8b9ee48d946de300337ae80fbc81d518aff5cb93cc6e0cebdd7d8630",
    },
}


def _rule(rule_ref: str) -> RuleRecord:
    return RuleRecord(
        rule_ref=rule_ref,
        antecedent=(
            {
                "operator": "op:relation",
                "args": {
                    "predicate_ref": "rel:knows",
                    "role:subject": "?x",
                    "role:object": "?y",
                },
            },
        ),
        consequent=(
            {
                "operator": "op:relation",
                "args": {
                    "predicate_ref": "rel:likes",
                    "role:subject": "?x",
                    "role:object": "?y",
                },
            },
        ),
        reviewed=True,
        source_ref="review:query-authority-snapshot",
    )


def test_query_rejects_authority_generation_drift_before_refresh(linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        indexed_key = owner._rule_index_key
        linked_authority._publish_rule_generation(
            parent_generation=linked_authority.generation,
            new_generation="authority:published-after-query-owner",
            new_content_hash="authority-content:published-after-query-owner",
            rules={**linked_authority.rules, "rule:new": _rule("rule:new")},
        )
        expression = _matrix_expression(_matrix_relation())

        with pytest.raises(StaleRevisionError, match="authority generation"):
            owner.evaluate_full(
                expression,
                project_expression(expression),
                _matrix_situation(stores),
            )

        assert owner._rule_index_key == indexed_key
        assert "rule:new" not in owner._reviewed_rules
    finally:
        stores.close()


def test_query_rejects_rule_publication_interleaved_after_pin_check(linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        stores.world.commit((Fact(
            "fact:interleaved-base",
            "op:relation",
            {
                "predicate_ref": "rel:base",
                "role:subject": "entity:alice",
                "role:object": "entity:bob",
            },
        ),), expected_revision=0)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        indexed_key = owner._rule_index_key
        injected_payload = _rule("rule:interleaved").as_dict()
        injected_payload["antecedent"][0]["args"]["predicate_ref"] = "rel:base"
        injected = RuleRecord(**injected_payload)
        original_snapshot = stores.r3_read_snapshot

        @contextmanager
        def interleaved_snapshot(expected):
            linked_authority._publish_rule_generation(
                parent_generation=linked_authority.generation,
                new_generation="authority:interleaved",
                new_content_hash="authority-content:interleaved",
                rules={**linked_authority.rules, injected.rule_ref: injected},
            )
            with original_snapshot(expected):
                yield

        stores.r3_read_snapshot = interleaved_snapshot
        expression = _matrix_expression(_matrix_relation())

        with pytest.raises(StaleRevisionError, match="authority generation"):
            owner.evaluate_full(
                expression,
                project_expression(expression),
                _matrix_situation(stores),
            )

        assert owner._rule_index_key == indexed_key
        assert injected.rule_ref not in owner._reviewed_rules
    finally:
        stores.close()


def test_query_owner_activates_exact_rule_generation_snapshot(linked_authority):
    injected_payload = _rule("rule:new-generation").as_dict()
    injected_payload["antecedent"][0]["args"]["predicate_ref"] = "rel:base"
    injected = RuleRecord(**injected_payload)
    linked_authority._publish_rule_generation(
        parent_generation=linked_authority.generation,
        new_generation="authority:new-generation",
        new_content_hash="authority-content:new-generation",
        rules={**linked_authority.rules, injected.rule_ref: injected},
    )
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        stores.world.commit((Fact(
            "fact:new-generation-base",
            "op:relation",
            {
                "predicate_ref": "rel:base",
                "role:subject": "entity:alice",
                "role:object": "entity:bob",
            },
        ),), expected_revision=0)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        expression = _matrix_expression(_matrix_relation())

        result = owner.evaluate_full(
            expression,
            project_expression(expression),
            _matrix_situation(stores),
        ).query_results[0]

        assert result.status.value == "supported"
        assert result.proof is not None
        assert injected.rule_ref in result.proof.rule_refs
        assert owner._rule_index_key[:2] == (
            linked_authority.generation,
            linked_authority.content_hash,
        )
    finally:
        stores.close()


def test_linked_authority_rules_are_not_mutable_in_place(linked_authority):
    before = tuple(linked_authority.rules)

    assert not hasattr(linked_authority, "publish_rule_generation")
    with pytest.raises(TypeError):
        linked_authority.rules["rule:forged"] = _rule("rule:forged")
    with pytest.raises(AttributeError):
        linked_authority.rules = {**linked_authority.rules, "rule:forged": _rule("rule:forged")}

    assert tuple(linked_authority.rules) == before


def test_linked_authority_rule_clauses_are_deeply_immutable_and_serializable(
    linked_authority,
):
    rule = next(iter(linked_authority.rules.values()))
    before = stable_ref("rule-record", rule)

    with pytest.raises(TypeError):
        rule.antecedent[0]["args"]["predicate_ref"] = "rel:forged"
    with pytest.raises(TypeError):
        dict.__setitem__(rule.antecedent[0], "operator", "op:event")

    assert stable_ref("rule-record", rule) == before
    assert json.loads(json.dumps(rule.as_dict(), sort_keys=True))["rule_ref"] == rule.rule_ref


def test_rule_record_rejects_malformed_clause_stance():
    bad = _rule("rule:bad-stance").as_dict()
    bad["consequent"][0]["stance"] = "banana"

    with pytest.raises(AuthorityLinkError, match="stance"):
        RuleRecord(**bad)
