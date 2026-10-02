"""Stage-10 description builder: first read-only normalized-claim boundary."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.descriptions import (
    DescriptionCompleteness,
    DescriptionRequest,
)
from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)
from cemm_authoritative_hybrid import persistence
from cemm_authoritative_hybrid.persistence import (
    Fact,
    _normalized_application_payload,
    _normalized_legacy_projection,
    _prepare_normalized_application_claim,
    memory_stores,
    open_stores,
)
from tests.test_foundation_description_request_lineage import _query_expression, _situation
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner


__cemm_test_inventory__ = {'tests/test_foundation_description_builder.py::test_description_reconstructs_reviewed_normalized_meaning[memory]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-description-builder-test-description-reconstructs-reviewed-normalized-meaning-memory',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': '81a38bfc4b9bfc6a28677a642eb81f204376513955be65185c3101e24ab10f77'},
 'tests/test_foundation_description_builder.py::test_description_reconstructs_reviewed_normalized_meaning[sqlite]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-description-builder-test-description-reconstructs-reviewed-normalized-meaning-sqlite',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': '81a38bfc4b9bfc6a28677a642eb81f204376513955be65185c3101e24ab10f77'},
 'tests/test_foundation_description_builder.py::test_description_rejects_target_not_selected_by_source_query[memory]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-description-builder-test-description-rejects-target-not-selected-by-source-query-memory',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': 'b02d8f1163baff8c9208e8728ca1272fb2a74ae96563b0f48902226fe05f4e05'},
 'tests/test_foundation_description_builder.py::test_description_rejects_target_not_selected_by_source_query[sqlite]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-description-builder-test-description-rejects-target-not-selected-by-source-query-sqlite',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': 'b02d8f1163baff8c9208e8728ca1272fb2a74ae96563b0f48902226fe05f4e05'},
 'tests/test_foundation_description_builder.py::test_description_returns_missing_for_no_reviewed_descriptive_claim[memory]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-missing-for-no-reviewed-descriptive-claim-memory',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': '1719479bda896a4a1581cf6f726e35ff7ce553804c65d61ae9402a47c5b8839a'},
 'tests/test_foundation_description_builder.py::test_description_returns_missing_for_no_reviewed_descriptive_claim[sqlite]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-missing-for-no-reviewed-descriptive-claim-sqlite',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': '1719479bda896a4a1581cf6f726e35ff7ce553804c65d61ae9402a47c5b8839a'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_when_target_posting_overflows[memory]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-when-target-posting-overflows-memory',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': 'cd0c30a609562268e3c4c187cc2814093fc7062be14b058ef5f4cd93494e78ea'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_when_target_posting_overflows[sqlite]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-when-target-posting-overflows-sqlite',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': 'cd0c30a609562268e3c4c187cc2814093fc7062be14b058ef5f4cd93494e78ea'},
 'tests/test_foundation_description_builder.py::test_description_preserves_same_application_support_and_deny_as_conflict[memory]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:foundation-description-builder-test-description-preserves-same-application-support-and-deny-as-conflict-memory',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': 'c12165a147bdf2c761cd0affe4337397e7c205eac57c46f4ce2582bbbb15a5c8'},
 'tests/test_foundation_description_builder.py::test_description_preserves_same_application_support_and_deny_as_conflict[sqlite]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:foundation-description-builder-test-description-preserves-same-application-support-and-deny-as-conflict-sqlite',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': 'c12165a147bdf2c761cd0affe4337397e7c205eac57c46f4ce2582bbbb15a5c8'},
 'tests/test_foundation_description_builder.py::test_description_rejects_physically_changed_generic_claim[projection-memory]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-description-builder-test-description-rejects-physically-changed-generic-claim-projection-memory',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': 'a193ef7cc1439e518d6a9c77051b81d45e9531d65b27297a95f4ebf7d561e442'},
 'tests/test_foundation_description_builder.py::test_description_rejects_physically_changed_generic_claim[projection-sqlite]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-description-builder-test-description-rejects-physically-changed-generic-claim-projection-sqlite',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': 'a193ef7cc1439e518d6a9c77051b81d45e9531d65b27297a95f4ebf7d561e442'},
 'tests/test_foundation_description_builder.py::test_description_rejects_physically_changed_generic_claim[lineage-memory]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-description-builder-test-description-rejects-physically-changed-generic-claim-lineage-memory',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-6',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': 'a193ef7cc1439e518d6a9c77051b81d45e9531d65b27297a95f4ebf7d561e442'},
 'tests/test_foundation_description_builder.py::test_description_rejects_physically_changed_generic_claim[lineage-sqlite]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-description-builder-test-description-rejects-physically-changed-generic-claim-lineage-sqlite',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-6',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': 'a193ef7cc1439e518d6a9c77051b81d45e9531d65b27297a95f4ebf7d561e442'},
 'tests/test_foundation_description_builder.py::test_description_sqlite_restart_is_canonical_and_read_only': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-description-builder-test-description-sqlite-restart-is-canonical-and-read-only',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                              'source_ast_sha256': '035955c2605e6c1f8d326b6d8272853a998469861e4aef7297e1f0a91bae0bde'},
 'tests/test_foundation_description_builder.py::test_description_deduplicates_shared_applications_and_provenance[memory]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-description-builder-test-description-deduplicates-shared-applications-and-provenance-memory',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'cc457ddf5d95a2de1839e38f74a160d52f2da0f6ce087a302527c3a3f92912b1'},
 'tests/test_foundation_description_builder.py::test_description_deduplicates_shared_applications_and_provenance[sqlite]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-description-builder-test-description-deduplicates-shared-applications-and-provenance-sqlite',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'cc457ddf5d95a2de1839e38f74a160d52f2da0f6ce087a302527c3a3f92912b1'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_for_shared_child_of_distinct_roots[memory]': {'activation_phase': 'R4',
                                                                                                                                        'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-for-shared-child-of-distinct-roots-memory',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                                        'source_ast_sha256': '274f573aafa157b885025b97cc18fda606773ff8e55ca62b127bb79226d50ada'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_for_shared_child_of_distinct_roots[sqlite]': {'activation_phase': 'R4',
                                                                                                                                        'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-for-shared-child-of-distinct-roots-sqlite',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                                        'source_ast_sha256': '274f573aafa157b885025b97cc18fda606773ff8e55ca62b127bb79226d50ada'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_when_answer_exceeds_max_depth[memory]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-when-answer-exceeds-max-depth-memory',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '73f1a91b0abddfedf21407127536cddf28daaa73d8ffc568ebeeaa640ecbf2a5'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_when_answer_exceeds_max_depth[sqlite]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-when-answer-exceeds-max-depth-sqlite',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '73f1a91b0abddfedf21407127536cddf28daaa73d8ffc568ebeeaa640ecbf2a5'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_when_proof_refs_exceed_abi_bound[memory]': {'activation_phase': 'R4',
                                                                                                                                      'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-when-proof-refs-exceed-abi-bound-memory',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                                      'source_ast_sha256': 'c59307ecfd774993d7aea7603f6bc175baa4fdc428a28682d7f15ce2e660b788'},
 'tests/test_foundation_description_builder.py::test_description_returns_budget_exhausted_when_proof_refs_exceed_abi_bound[sqlite]': {'activation_phase': 'R4',
                                                                                                                                      'assertion_ref': 'assertion:foundation-description-builder-test-description-returns-budget-exhausted-when-proof-refs-exceed-abi-bound-sqlite',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                                      'source_ast_sha256': 'c59307ecfd774993d7aea7603f6bc175baa4fdc428a28682d7f15ce2e660b788'},
 'tests/test_foundation_description_builder.py::test_description_propagates_unrelated_expression_abi_errors[memory]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-description-builder-test-description-propagates-unrelated-expression-abi-errors-memory',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-6',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': '293090062bb25db8614944dbba9fea6357fa92b25b90c7da49473f0801212d44'},
 'tests/test_foundation_description_builder.py::test_description_propagates_unrelated_expression_abi_errors[sqlite]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-description-builder-test-description-propagates-unrelated-expression-abi-errors-sqlite',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-6',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': '293090062bb25db8614944dbba9fea6357fa92b25b90c7da49473f0801212d44'}}


def _stores(backend: str, tmp_path):
    if backend == "memory":
        return memory_stores(authority_generation="authority:description-test")
    return open_stores(
        tmp_path / "description-store",
        authority_generation="authority:description-test",
    )


def _description_expression(instance_ref: str = "entity:alice") -> SemanticExpression:
    application = SemanticApplication(
        "application:description-source",
        "op:type",
        "concept:mother",
        (
            RoleBinding("role:instance", GroundedReference(instance_ref)),
            RoleBinding("role:class", GroundedReference("concept:mother")),
        ),
    )
    return SemanticExpression.create(
        applications=(application,), root_refs=(application.application_ref,)
    )


def _seed_reviewed_generic_claim(
    stores,
    expression: SemanticExpression,
    *,
    stance: str = "support",
    fact_ref: str = "fact:alice-mother",
    source_ref: str = "source:reviewed-definition",
    decision_ref: str = "decision:reviewed-definition",
    occurrence_ref: str = "occurrence:reviewed-definition",
    placement_ref: str = "policy:reviewed-definition",
    proof_refs: tuple[str, ...] = ("proof:reviewed-definition",),
):
    """Seed a generic reviewed claim below the public acquisition boundary."""
    provisional = _prepare_normalized_application_claim(
        expression,
        root_ref=expression.root_refs[0],
        stance=stance,
        fact_ref=fact_ref,
        source_ref=source_ref,
        decision_ref=decision_ref,
        occurrence_ref=occurrence_ref,
        placement="reviewed",
        placement_ref=placement_ref,
        proof_refs=proof_refs,
        authority_generation=stores.revision_pin().authority_generation,
        confidence_micros=1_000_000,
        commit_transaction_ref="transaction:pending",
        asserted_world_revision=0,
    )
    root = next(
        application
        for application in provisional.applications
        if application.application_ref == provisional.root_application_ref
    )
    operator, args, stance = _normalized_legacy_projection(
        _normalized_application_payload(root), stance
    )
    fact = Fact(
        fact_ref=fact_ref,
        operator=operator,
        args=args,
        stance=stance,
        proof={
            "source": source_ref,
            "decision_ref": decision_ref,
            "occurrence_ref": occurrence_ref,
            "placement": "reviewed",
            "placement_ref": placement_ref,
            "proof_refs": list(proof_refs),
        },
    )
    receipt = stores.world.commit((fact,), expected_revision=stores.world.revision)
    claim = _prepare_normalized_application_claim(
        expression,
        root_ref=expression.root_refs[0],
        stance=stance,
        fact_ref=fact.fact_ref,
        source_ref=source_ref,
        decision_ref=decision_ref,
        occurrence_ref=occurrence_ref,
        placement="reviewed",
        placement_ref=placement_ref,
        proof_refs=proof_refs,
        authority_generation=stores.revision_pin().authority_generation,
        confidence_micros=1_000_000,
        commit_transaction_ref=receipt.transaction_ref,
        asserted_world_revision=receipt.new_revision,
    )
    stores._r3_write_normalized_batch(claim)
    return claim


def _seeded_description_case(tmp_path, backend: str):
    stores = _stores(backend, tmp_path)
    expression = _description_expression()
    claim = _seed_reviewed_generic_claim(stores, expression)
    pin = stores.revision_pin()
    query_result = _situation(pin)
    request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=query_result,
        max_depth=1,
        max_facts=1,
    )
    authority = SimpleNamespace(
        generation=pin.authority_generation,
        content_hash="authority-content:description-test",
        atoms={},
        capabilities={},
        rules={},
    )
    return stores, expression, query_result, request, claim, authority


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_reconstructs_reviewed_normalized_meaning(tmp_path, backend):
    stores, expression, query_result, request, claim, authority = _seeded_description_case(
        tmp_path, backend
    )
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        before = stores.revisions()

        result = owner.describe(request, _query_expression(request.target_ref), query_result)

        assert result.completeness is DescriptionCompleteness.SUFFICIENT
        assert result.fact_refs == (claim.claim_payload["fact_ref"],)
        assert result.claim_refs == (claim.claim_ref,)
        assert result.definition_refs == (claim.root_application_ref,)
        assert result.answer_expression == SemanticExpression.create(
            applications=claim.applications,
            root_refs=(claim.root_application_ref,),
        )
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_rejects_target_not_selected_by_source_query(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        source_expression = _query_expression("entity:alice")
        _seed_reviewed_generic_claim(
            stores, _description_expression("entity:bob")
        )
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:bob"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)

        with pytest.raises(ValueError, match="source expression.*mismatch"):
            owner.describe(request, source_expression, source)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_returns_missing_for_no_reviewed_descriptive_claim(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={}, capabilities={}, rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.MISSING
        assert result.answer_expression is None
        assert result.fact_refs == ()
        assert result.claim_refs == ()
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_returns_budget_exhausted_when_target_posting_overflows(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path)
    try:
        _seed_reviewed_generic_claim(
            stores,
            _description_expression(),
            fact_ref="fact:overflow-first",
            source_ref="source:overflow-first",
            decision_ref="decision:overflow-first",
            occurrence_ref="occurrence:overflow-first",
            proof_refs=("proof:overflow-first",),
        )
        second_expression = SemanticExpression.create(
            applications=(
                SemanticApplication(
                    "application:overflow-second",
                    "op:type",
                    "concept:person",
                    (
                        RoleBinding("role:instance", GroundedReference("entity:alice")),
                        RoleBinding("role:class", GroundedReference("concept:person")),
                    ),
                ),
            ),
            root_refs=("application:overflow-second",),
        )
        _seed_reviewed_generic_claim(
            stores,
            second_expression,
            fact_ref="fact:overflow-second",
            source_ref="source:overflow-second",
            decision_ref="decision:overflow-second",
            occurrence_ref="occurrence:overflow-second",
            proof_refs=("proof:overflow-second",),
        )
        source_expression = _description_expression()
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={}, capabilities={}, rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.BUDGET_EXHAUSTED
        assert result.answer_expression is None
        assert result.fact_refs == ()
        assert result.definition_refs == ()
        assert result.claim_refs == ()
        assert result.source_refs == ()
        assert result.proof_refs == ()
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_preserves_same_application_support_and_deny_as_conflict(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        support = _seed_reviewed_generic_claim(
            stores,
            expression,
            stance="support",
            fact_ref="fact:conflict-support",
            source_ref="source:conflict-support",
            decision_ref="decision:conflict-support",
            occurrence_ref="occurrence:conflict-support",
            proof_refs=("proof:conflict-support",),
        )
        deny = _seed_reviewed_generic_claim(
            stores,
            expression,
            stance="deny",
            fact_ref="fact:conflict-deny",
            source_ref="source:conflict-deny",
            decision_ref="decision:conflict-deny",
            occurrence_ref="occurrence:conflict-deny",
            proof_refs=("proof:conflict-deny",),
        )
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=2,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={}, capabilities={}, rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.CONFLICT
        assert result.answer_expression == SemanticExpression.create(
            applications=support.applications,
            root_refs=(support.root_application_ref,),
        )
        assert result.fact_refs == tuple(sorted((
            support.claim_payload["fact_ref"], deny.claim_payload["fact_ref"],
        )))
        assert result.claim_refs == tuple(sorted((support.claim_ref, deny.claim_ref)))
        assert result.definition_refs == (support.root_application_ref,)
        assert result.source_refs == tuple(sorted((
            support.claim_payload["source_ref"], deny.claim_payload["source_ref"],
        )))
        assert result.proof_refs == tuple(sorted((
            support.claim_payload["proof_refs"][0], deny.claim_payload["proof_refs"][0],
        )))
    finally:
        stores.close()


def _physically_replace_fact(stores, backend: str, fact: Fact) -> None:
    if backend == "memory":
        stores._backend.world._store_fact(fact)
        return
    row = persistence._fact_to_row(fact)
    with stores._backend._conn:
        stores._backend._conn.execute(
            "UPDATE world_facts SET operator=:operator,args_json=:args_json,"
            "stance=:stance,confidence=:confidence,derived=:derived,"
            "proof_json=:proof_json,payload_hash=:payload_hash "
            "WHERE fact_ref=:fact_ref",
            {
                **row,
                "payload_hash": persistence._payload_hash(
                    persistence._fact_payload(fact)
                ),
            },
        )


@pytest.mark.parametrize(
    "backend,corruption",
    (
        ("memory", "projection"),
        ("sqlite", "projection"),
        ("memory", "lineage"),
        ("sqlite", "lineage"),
    ),
    ids=(
        "projection-memory",
        "projection-sqlite",
        "lineage-memory",
        "lineage-sqlite",
    ),
)
def test_description_rejects_physically_changed_generic_claim(
    tmp_path, backend, corruption
):
    stores, expression, query_result, request, claim, authority = _seeded_description_case(
        tmp_path, backend
    )
    try:
        fact = stores.world.get(claim.claim_payload["fact_ref"])
        assert fact is not None
        if corruption == "projection":
            changed = Fact(
                fact_ref=fact.fact_ref,
                operator=fact.operator,
                args={**fact.args, "role:instance": "entity:mallory"},
                stance=fact.stance,
                confidence=fact.confidence,
                derived=fact.derived,
                proof=fact.proof,
            )
        else:
            changed = Fact(
                fact_ref=fact.fact_ref,
                operator=fact.operator,
                args=fact.args,
                stance=fact.stance,
                confidence=fact.confidence,
                derived=fact.derived,
                proof={**fact.proof, "source": "source:forged"},
            )
        _physically_replace_fact(stores, backend, changed)

        with pytest.raises(ValueError, match="description claim.*(projection|lineage)"):
            QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe(request, _query_expression(request.target_ref), query_result)
    finally:
        stores.close()


def test_description_sqlite_restart_is_canonical_and_read_only(tmp_path):
    path = tmp_path / "description-store"
    stores = open_stores(path, authority_generation="authority:description-test")
    try:
        expression = _description_expression()
        claim = _seed_reviewed_generic_claim(stores, expression)
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )
        before = stores.revisions()
        initial = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)
        assert stores.revisions() == before
        assert initial.claim_refs == (claim.claim_ref,)
    finally:
        stores.close()

    reopened = open_stores(path, authority_generation="authority:description-test")
    try:
        pin = reopened.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )
        before = reopened.revisions()

        recovered = QueryDecisionOwner(
            reopened, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert recovered == initial
        assert reopened.revisions() == before
    finally:
        reopened.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_deduplicates_shared_applications_and_provenance(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        child = SemanticApplication(
            "application:shared-child",
            "op:type",
            "concept:mother",
            (
                RoleBinding("role:instance", GroundedReference("entity:alice")),
                RoleBinding("role:class", GroundedReference("concept:mother")),
            ),
        )

        def expression_for(root_ref: str) -> SemanticExpression:
            root = SemanticApplication(
                root_ref,
                "op:event",
                "event:assert",
                (
                    RoleBinding("role:actor", GroundedReference("participant:reviewer")),
                    RoleBinding("role:content", ApplicationFiller(child.application_ref)),
                ),
            )
            return SemanticExpression.create(
                applications=(child, root), root_refs=(root.application_ref,)
            )

        first = _seed_reviewed_generic_claim(
            stores,
            expression_for("application:first"),
            fact_ref="fact:shared-first",
            decision_ref="decision:shared-first",
            occurrence_ref="occurrence:shared-first",
            source_ref="source:shared",
            proof_refs=("proof:shared",),
        )
        second = _seed_reviewed_generic_claim(
            stores,
            expression_for("application:second"),
            fact_ref="fact:shared-second",
            decision_ref="decision:shared-second",
            occurrence_ref="occurrence:shared-second",
            source_ref="source:shared",
            proof_refs=("proof:shared",),
        )
        source_expression = SemanticExpression.create(
            applications=(child,), root_refs=(child.application_ref,)
        )
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=2,
            max_facts=2,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.SUFFICIENT
        assert len(result.answer_expression.applications) == 2
        assert len({app.application_ref for app in result.answer_expression.applications}) == 2
        assert result.fact_refs == tuple(sorted((first.claim_payload["fact_ref"], second.claim_payload["fact_ref"])))
        assert result.claim_refs == tuple(sorted((first.claim_ref, second.claim_ref)))
        assert result.definition_refs == (first.root_application_ref,)
        assert result.source_refs == ("source:shared",)
        assert result.proof_refs == ("proof:shared",)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_returns_budget_exhausted_for_shared_child_of_distinct_roots(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path)
    try:
        child = SemanticApplication(
            "application:shared-child",
            "op:type",
            "concept:mother",
            (
                RoleBinding("role:instance", GroundedReference("entity:alice")),
                RoleBinding("role:class", GroundedReference("concept:mother")),
            ),
        )

        def expression_for(channel_ref: str) -> SemanticExpression:
            root = SemanticApplication(
                "application:root-" + channel_ref,
                "op:event",
                "event:assert",
                (
                    RoleBinding("role:actor", GroundedReference("participant:reviewer")),
                    RoleBinding("role:content", ApplicationFiller(child.application_ref)),
                    RoleBinding("role:channel", GroundedReference(channel_ref)),
                ),
            )
            return SemanticExpression.create(
                applications=(child, root), root_refs=(root.application_ref,)
            )

        _seed_reviewed_generic_claim(
            stores,
            expression_for("channel:first"),
            fact_ref="fact:dag-first",
            decision_ref="decision:dag-first",
            occurrence_ref="occurrence:dag-first",
        )
        _seed_reviewed_generic_claim(
            stores,
            expression_for("channel:second"),
            fact_ref="fact:dag-second",
            decision_ref="decision:dag-second",
            occurrence_ref="occurrence:dag-second",
        )
        source_expression = SemanticExpression.create(
            applications=(child,), root_refs=(child.application_ref,)
        )
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=2,
            max_facts=2,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.BUDGET_EXHAUSTED
        assert result.answer_expression is None
        assert result.fact_refs == ()
        assert result.definition_refs == ()
        assert result.claim_refs == ()
        assert result.source_refs == ()
        assert result.proof_refs == ()
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_returns_budget_exhausted_when_answer_exceeds_max_depth(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path)
    try:
        child = SemanticApplication(
            "application:depth-child",
            "op:type",
            "concept:mother",
            (
                RoleBinding("role:instance", GroundedReference("entity:alice")),
                RoleBinding("role:class", GroundedReference("concept:mother")),
            ),
        )
        root = SemanticApplication(
            "application:depth-root",
            "op:event",
            "event:assert",
            (
                RoleBinding("role:actor", GroundedReference("participant:reviewer")),
                RoleBinding("role:content", ApplicationFiller(child.application_ref)),
            ),
        )
        expression = SemanticExpression.create(
            applications=(child, root), root_refs=(root.application_ref,)
        )
        _seed_reviewed_generic_claim(stores, expression)
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.BUDGET_EXHAUSTED
        assert result.answer_expression is None
        assert result.fact_refs == ()
        assert result.definition_refs == ()
        assert result.claim_refs == ()
        assert result.source_refs == ()
        assert result.proof_refs == ()
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_returns_budget_exhausted_when_proof_refs_exceed_abi_bound(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        _seed_reviewed_generic_claim(
            stores,
            expression,
            proof_refs=tuple(f"proof:description-overflow-{index}" for index in range(65)),
        )
        pin = stores.revision_pin()
        source = _situation(pin)
        request = DescriptionRequest.create(
        source_expression=_query_expression("entity:alice"), situation=source,
            max_depth=1,
            max_facts=1,
    )
        authority = SimpleNamespace(
            generation=pin.authority_generation,
            content_hash="authority-content:description-test",
            atoms={},
            capabilities={},
            rules={},
        )

        result = QueryDecisionOwner(
            stores, RuntimeConfig.release(), authority
        ).describe(request, _query_expression(request.target_ref), source)

        assert result.completeness is DescriptionCompleteness.BUDGET_EXHAUSTED
        assert result.answer_expression is None
        assert result.fact_refs == ()
        assert result.definition_refs == ()
        assert result.claim_refs == ()
        assert result.source_refs == ()
        assert result.proof_refs == ()
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_propagates_unrelated_expression_abi_errors(
    tmp_path, backend, monkeypatch
):
    stores, expression, query_result, request, claim, authority = _seeded_description_case(
        tmp_path, backend
    )
    try:
        original_create = SemanticExpression.create

        def fail_only_for_description_answer(cls, **kwargs):
            applications = tuple(kwargs["applications"])
            root_refs = tuple(kwargs["root_refs"])
            if (
                applications == claim.applications
                and root_refs == (claim.root_application_ref,)
            ):
                raise ValueError("unrelated expression ABI error")
            return original_create(
                **{**kwargs, "applications": applications, "root_refs": root_refs}
            )

        monkeypatch.setattr(
            SemanticExpression,
            "create",
            classmethod(fail_only_for_description_answer),
        )

        with pytest.raises(ValueError, match="unrelated expression ABI error"):
            QueryDecisionOwner(
                stores, RuntimeConfig.release(), authority
            ).describe(request, _query_expression(request.target_ref), query_result)
    finally:
        stores.close()
