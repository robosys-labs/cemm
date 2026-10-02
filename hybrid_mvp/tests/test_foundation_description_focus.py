"""Description focus at the canonical component seam, not public QUERY authority."""
from dataclasses import replace

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.descriptions import DescriptionCompleteness
from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller, GroundedReference, LiteralValue, RoleBinding,
    SemanticApplication, SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import StaleRevisionError
from cemm_authoritative_hybrid.proof_bundle import ProofBundle
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from tests.test_foundation_description_builder import (
    _physically_replace_fact, _seed_reviewed_generic_claim, _stores,
)
from tests.test_foundation_description_proof import _inputs
from tests.test_foundation_description_request_lineage import _query_expression


__cemm_test_inventory__ = {'tests/test_foundation_description_focus.py::test_description_metadata_and_predicate_postings_are_missing[memory]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-focus-metadata-and-predicate-postings-are-missing-memory',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'f19bd33b574308184c2a91dd26fc0f1b6a971f3dc8ac76abc84b75d200a4d4b1'},
 'tests/test_foundation_description_focus.py::test_description_metadata_and_predicate_postings_are_missing[sqlite]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-focus-metadata-and-predicate-postings-are-missing-sqlite',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'f19bd33b574308184c2a91dd26fc0f1b6a971f3dc8ac76abc84b75d200a4d4b1'},
 'tests/test_foundation_description_focus.py::test_description_nonmetadata_focus_survives_for_all_operators[memory]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-focus-nonmetadata-focus-survives-for-all-operators-memory',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': 'a4351a00a2fa07633f86c582a289783e727c6a0feff8f3c3e0396ee61dd0524d'},
 'tests/test_foundation_description_focus.py::test_description_nonmetadata_focus_survives_for_all_operators[sqlite]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-focus-nonmetadata-focus-survives-for-all-operators-sqlite',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': 'a4351a00a2fa07633f86c582a289783e727c6a0feff8f3c3e0396ee61dd0524d'},
 'tests/test_foundation_description_focus.py::test_description_mixed_postings_keep_only_focused_nested_signed_lineage[memory]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-focus-mixed-postings-keep-only-focused-nested-signed-lineage-memory',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '2a13db74afa6aade0fc6ff63393be4f73e01406307e9450d5805d90279028491'},
 'tests/test_foundation_description_focus.py::test_description_mixed_postings_keep_only_focused_nested_signed_lineage[sqlite]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-focus-mixed-postings-keep-only-focused-nested-signed-lineage-sqlite',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '2a13db74afa6aade0fc6ff63393be4f73e01406307e9450d5805d90279028491'},
 'tests/test_foundation_description_focus.py::test_description_authenticates_irrelevant_postings_before_filter[memory]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-focus-authenticates-irrelevant-postings-before-filter-memory',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'c01fe42d080294dfe685119d104a8d853fc49263319b81b1ad09f52970e7a4e9'},
 'tests/test_foundation_description_focus.py::test_description_authenticates_irrelevant_postings_before_filter[sqlite]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-focus-authenticates-irrelevant-postings-before-filter-sqlite',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'c01fe42d080294dfe685119d104a8d853fc49263319b81b1ad09f52970e7a4e9'},
 'tests/test_foundation_description_focus.py::test_description_raw_metadata_overflow_is_not_hidden_by_filter[memory]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-focus-raw-metadata-overflow-is-not-hidden-by-filter-memory',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '85d488a4a7c9972441d501af1903cb535aa5d1fbfa20cff6925529fd6edd434e'},
 'tests/test_foundation_description_focus.py::test_description_raw_metadata_overflow_is_not_hidden_by_filter[sqlite]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-focus-raw-metadata-overflow-is-not-hidden-by-filter-sqlite',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '85d488a4a7c9972441d501af1903cb535aa5d1fbfa20cff6925529fd6edd434e'}}


def _expression(operator, predicate, roles):
    bindings = tuple(
        RoleBinding(role, GroundedReference(ref)) for role, ref in roles
    )
    if operator == "op:designation":
        bindings = (
            next(binding for binding in bindings if binding.role_ref == "role:target"),
            RoleBinding("role:label_type", GroundedReference(predicate)),
            RoleBinding("role:surface", LiteralValue("string", predicate)),
        )
    app = SemanticApplication("application:focus", operator, predicate, bindings)
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


def _source(target):
    app = SemanticApplication("application:component-source", "op:designation", "label:lexical", (
        RoleBinding("role:target", GroundedReference(target)),
        RoleBinding("role:label_type", GroundedReference("label:lexical")),
        RoleBinding("role:surface", LiteralValue("string", "unknownlabel")),
    ))
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


def _seed(stores, expression, identity, stance="support"):
    return _seed_reviewed_generic_claim(stores, expression, stance=stance,
        fact_ref=f"fact:{identity}", source_ref=f"source:{identity}",
        decision_ref=f"decision:{identity}", occurrence_ref=f"occurrence:{identity}",
        proof_refs=(f"proof:{identity}",))


def _read(stores, target, *, max_depth=1, max_facts=64):
    expression = _source(target)
    source, request, authority = _inputs(stores, expression, target_ref=target,
        max_depth=max_depth, max_facts=max_facts)
    owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
    before = stores.revisions()
    result, bundle = owner.describe_with_proof(request, _query_expression(request.target_ref), source)
    assert result == owner.describe(request, _query_expression(request.target_ref), source)
    assert bundle.description == result
    assert ProofBundle.from_dict(bundle.as_dict()) == bundle
    assert stores.revisions() == before
    return result, bundle


def _empty(result, bundle, completeness):
    assert result.completeness is completeness
    assert result.answer_expression is None
    assert result.fact_refs == result.claim_refs == result.definition_refs == ()
    assert result.source_refs == result.proof_refs == ()
    assert bundle.applications == bundle.claims == bundle.application_refs == ()
    assert bundle.answer_expression_ref is None


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_metadata_and_predicate_postings_are_missing(tmp_path, backend):
    cases = (
        ("op:designation", "label:lexical", "role:target", ("role:label_type",)),
        ("op:type", "concept:mother", "role:instance", ("role:class", "role:type")),
        ("op:relation", "rel:likes", "role:subject", ("role:relation",)),
        ("op:state", "dimension:mood", "role:subject", ("role:dimension", "role:value")),
        ("op:event", "event:learn", "role:actor", ("role:event", "role:type")),
    )
    for index, (operator, predicate, subject_role, metadata_roles) in enumerate(cases):
        stores = _stores(backend, tmp_path / str(index))
        try:
            roles = ((subject_role, "entity:alice"), *((role, predicate) for role in metadata_roles))
            _seed(stores, _expression(operator, predicate, roles), "metadata")
            _empty(*_read(stores, predicate), DescriptionCompleteness.MISSING)
            # Designation requires label_type equal to predicate; other shapes
            # also exercise a posting with no grounded target role occurrence.
            _seed(stores, _expression(operator, predicate, ((subject_role, "entity:bob"),)), "predicate")
            _empty(*_read(stores, predicate), DescriptionCompleteness.MISSING)
        finally:
            stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_nonmetadata_focus_survives_for_all_operators(tmp_path, backend):
    for index, (operator, role) in enumerate((
        ("op:designation", "role:target"), ("op:type", "role:instance"),
        ("op:relation", "role:object"), ("op:state", "role:subject"), ("op:event", "role:actor"),
    )):
        stores = _stores(backend, tmp_path / str(index))
        try:
            claim = _seed(stores, _expression(operator, "semantic:predicate", ((role, "semantic:target"),)), "focused")
            result, bundle = _read(stores, "semantic:target")
            assert result.completeness is DescriptionCompleteness.SUFFICIENT
            assert result.definition_refs == (claim.root_application_ref,)
            assert bundle.applications == claim.applications
            assert bundle.claims[0].claim_ref == claim.claim_ref
        finally:
            stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_mixed_postings_keep_only_focused_nested_signed_lineage(tmp_path, backend):
    for index, stances in enumerate((("support",), ("deny",), ("support", "deny"))):
        stores = _stores(backend, tmp_path / str(index))
        try:
            irrelevant = _expression("op:type", "concept:mother", (
                ("role:instance", "entity:alice"), ("role:class", "concept:mother")))
            for stance in ("support", "deny"):
                _seed(stores, irrelevant, f"irrelevant-{stance}", stance)
            child = _expression("op:relation", "rel:subtype_of", (
                ("role:subject", "concept:mother"), ("role:object", "concept:person"))).applications[0]
            parent = SemanticApplication("application:parent", "op:event", "event:assert", (
                RoleBinding("role:actor", GroundedReference("participant:reviewer")),
                RoleBinding("role:content", ApplicationFiller(child.application_ref)),
            ))
            focused = SemanticExpression.create(applications=(child, parent), root_refs=(parent.application_ref,))
            claims = tuple(_seed(stores, focused, f"focused-{stance}", stance) for stance in stances)
            result, bundle = _read(stores, "concept:mother", max_depth=2)
            assert result.completeness is (DescriptionCompleteness.CONFLICT if len(stances) == 2 else DescriptionCompleteness.SUFFICIENT)
            assert set(bundle.applications) == set(claims[0].applications)
            assert result.definition_refs == (claims[0].root_application_ref,)
            assert set(result.claim_refs) == {claim.claim_ref for claim in claims}
            assert set(result.fact_refs) == {claim.claim_payload["fact_ref"] for claim in claims}
            assert set(result.source_refs) == {claim.claim_payload["source_ref"] for claim in claims}
            assert set(result.proof_refs) == {proof for claim in claims for proof in claim.claim_payload["proof_refs"]}
            assert {claim.application_ref for claim in bundle.claims} == {claims[0].root_application_ref}
            assert {claim.stance for claim in bundle.claims} == set(stances)
            assert {claim.claim_ref: claim.as_dict() for claim in bundle.claims} == {
                claim.claim_ref: {"claim_ref": claim.claim_ref, **dict(claim.claim_payload)} for claim in claims
            }
        finally:
            stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_authenticates_irrelevant_postings_before_filter(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        claim = _seed(stores, _expression("op:type", "concept:mother", (
            ("role:instance", "entity:alice"), ("role:class", "concept:mother"))), "irrelevant")
        expression = _source("concept:mother")
        source, request, authority = _inputs(stores, expression, target_ref="concept:mother")
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        fact = stores.world.get(claim.claim_payload["fact_ref"])
        before = stores.revisions()
        for changed in (replace(fact, args={**fact.args, "role:instance": "entity:mallory"}),
                        replace(fact, proof={**fact.proof, "source": "source:forged"})):
            _physically_replace_fact(stores, backend, changed)
            for method in (owner.describe, owner.describe_with_proof):
                with pytest.raises(ValueError, match="description claim.*(projection|lineage)"):
                    method(request, _query_expression(request.target_ref), source)
            assert stores.revisions() == before
        _physically_replace_fact(stores, backend, fact)
        stores.world.commit((), expected_revision=stores.world.revision)
        for method in (owner.describe, owner.describe_with_proof):
            with pytest.raises(StaleRevisionError):
                method(request, _query_expression(request.target_ref), source)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_raw_metadata_overflow_is_not_hidden_by_filter(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        for index in range(2):
            _seed(stores, _expression("op:type", "concept:mother", (
                ("role:instance", f"entity:{index}"), ("role:class", "concept:mother"))), f"irrelevant-{index}")
        _empty(*_read(stores, "concept:mother", max_facts=1), DescriptionCompleteness.BUDGET_EXHAUSTED)
    finally:
        stores.close()
