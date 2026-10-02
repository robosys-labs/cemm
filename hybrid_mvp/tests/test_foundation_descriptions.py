"""Description ABI 2 remains exact, transient, and bounded."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import cemm_authoritative_hybrid.authority as authority_module
from cemm_authoritative_hybrid.authority import (
    AuthorityLinkError,
    AuthorityLinker,
    AuthorityStore,
    LinkedAuthority,
)
from cemm_authoritative_hybrid.canonical import sha256_governed_text
from cemm_authoritative_hybrid.descriptions import (
    DESCRIPTION_ABI_VERSION,
    DescriptionCompleteness,
    DescriptionRequest,
    DescriptionResult,
)
from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    ScopeOperator,
    UnresolvedFiller,
    UnresolvedValue,
    VariableBinder,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from tests.test_foundation_description_request_lineage import _query_expression, _situation


ROOT = Path(__file__).resolve().parents[1]


__cemm_test_inventory__ = {'tests/test_foundation_descriptions.py::test_description_request_roundtrip_binds_query_target_bounds_and_pin': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-description-request-roundtrip',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'dabb6da9b1a8919119724e8996b7d72dbfddf0713d077f4994e11444acd4c400'},
 'tests/test_foundation_descriptions.py::test_description_request_requires_current_r3_query_result_namespace': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-description-request-r3-query-result-namespace',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-6',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': '784bf3208ad2cdd31c564d15d59233879cbb3d3db12744b4df330a20595360cd'},
 'tests/test_foundation_descriptions.py::test_description_request_rejects_noncanonical_refs_scalars_and_containers[bad-query-ref]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-description-request-rejects-query-ref',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '99ea76772ded7b754de4f62cd960cb82c85978a6e59568fdbb3c81af77aa8c9b'},
 'tests/test_foundation_descriptions.py::test_description_request_rejects_noncanonical_refs_scalars_and_containers[bad-target-ref]': {'activation_phase': 'R4',
                                                                                                                                      'assertion_ref': 'assertion:foundation-description-request-rejects-target-ref',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                                      'source_ast_sha256': '99ea76772ded7b754de4f62cd960cb82c85978a6e59568fdbb3c81af77aa8c9b'},
 'tests/test_foundation_descriptions.py::test_description_request_rejects_noncanonical_refs_scalars_and_containers[bool-depth]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-description-request-rejects-bool-depth',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '99ea76772ded7b754de4f62cd960cb82c85978a6e59568fdbb3c81af77aa8c9b'},
 'tests/test_foundation_descriptions.py::test_description_request_rejects_noncanonical_refs_scalars_and_containers[fact-overflow]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-description-request-rejects-fact-overflow',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '99ea76772ded7b754de4f62cd960cb82c85978a6e59568fdbb3c81af77aa8c9b'},
 'tests/test_foundation_descriptions.py::test_description_request_rejects_noncanonical_refs_scalars_and_containers[wrong-pin-container]': {'activation_phase': 'R4',
                                                                                                                                           'assertion_ref': 'assertion:foundation-description-request-rejects-pin-container',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                                           'source_ast_sha256': '99ea76772ded7b754de4f62cd960cb82c85978a6e59568fdbb3c81af77aa8c9b'},
 'tests/test_foundation_descriptions.py::test_description_result_roundtrips_every_completeness_state[sufficient]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-description-result-roundtrip-sufficient',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': '88325aa096132fdd642e7b6afaa23f24367acb3aaa2d922d7289b2c5b70dc967'},
 'tests/test_foundation_descriptions.py::test_description_result_roundtrips_every_completeness_state[partial]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-description-result-roundtrip-partial',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '88325aa096132fdd642e7b6afaa23f24367acb3aaa2d922d7289b2c5b70dc967'},
 'tests/test_foundation_descriptions.py::test_description_result_roundtrips_every_completeness_state[missing]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-description-result-roundtrip-missing',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '88325aa096132fdd642e7b6afaa23f24367acb3aaa2d922d7289b2c5b70dc967'},
 'tests/test_foundation_descriptions.py::test_description_result_roundtrips_every_completeness_state[conflict]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-description-result-roundtrip-conflict',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-6',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': '88325aa096132fdd642e7b6afaa23f24367acb3aaa2d922d7289b2c5b70dc967'},
 'tests/test_foundation_descriptions.py::test_description_result_roundtrips_every_completeness_state[budget-exhausted]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-description-result-roundtrip-budget',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-6',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': '88325aa096132fdd642e7b6afaa23f24367acb3aaa2d922d7289b2c5b70dc967'},
 'tests/test_foundation_descriptions.py::test_description_result_rejects_forgery_wrong_containers_and_pin': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-description-result-rejects-forgery',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-6',
                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                             'source_ast_sha256': '23636a31ef763aa95bec51c5bc79bb575b1ab709fbe176900f7f5bcf41899910'},
 'tests/test_foundation_descriptions.py::test_content_result_requires_exact_evidence_and_targeted_settled_meaning': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-description-result-content-matrix',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'febbb7f9237b3990897be37ecf53dee9209fa28cc7484d93ee816ae5352d0fe2'},
 'tests/test_foundation_descriptions.py::test_description_target_must_be_a_descriptive_filler_not_metadata': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-description-target-descriptive-filler',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                              'source_ast_sha256': 'dc120dbfcbc43ed05a8f308c6479c25a66808314f5b51892b05711b03db1c4a4'},
 'tests/test_foundation_descriptions.py::test_description_fact_refs_use_persistent_fact_namespace': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:foundation-description-result-persistent-fact-identity',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                     'source_ast_sha256': 'f7bb8c7355db8d5f3fc3d20cdea8376c80de9e2408eec9abdc257c9b995dd9a0'},
 'tests/test_foundation_descriptions.py::test_description_max_depth_bounds_complete_answer_graph[application]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-description-max-depth-application',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'e4bafd7536b4519340b995b0fb26d341986a525435f03bd2cdd87b1914d031dc'},
 'tests/test_foundation_descriptions.py::test_description_max_depth_bounds_complete_answer_graph[scope]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-description-max-depth-scope',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': 'e4bafd7536b4519340b995b0fb26d341986a525435f03bd2cdd87b1914d031dc'},
 'tests/test_foundation_descriptions.py::test_description_max_depth_bounds_complete_answer_graph[link]': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:foundation-description-max-depth-link',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'Foundation-Task-6',
                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                          'source_ast_sha256': 'e4bafd7536b4519340b995b0fb26d341986a525435f03bd2cdd87b1914d031dc'},
 'tests/test_foundation_descriptions.py::test_description_max_depth_bounds_complete_answer_graph[binder]': {'activation_phase': 'R4',
                                                                                                            'assertion_ref': 'assertion:foundation-description-max-depth-binder',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                            'source_ast_sha256': 'e4bafd7536b4519340b995b0fb26d341986a525435f03bd2cdd87b1914d031dc'},
 'tests/test_foundation_descriptions.py::test_description_max_facts_bounds_persistent_fact_refs_only': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:foundation-description-max-persistent-facts',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                        'source_ast_sha256': '6fe41852fd3dae7bf3144b28156d4252d97d16b5782e05c771dd68267a4e363d'},
 'tests/test_foundation_descriptions.py::test_missing_result_rejects_positive_evidence_and_content': {'activation_phase': 'R4',
                                                                                                      'assertion_ref': 'assertion:foundation-description-result-missing-matrix',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                      'source_ast_sha256': '5667ce383db2cbb33d92cd0591ae2deae6f87777ccf707f54b4e95d979c94237'},
 'tests/test_foundation_descriptions.py::test_description_has_no_parallel_persistent_authority_plane': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:foundation-description-no-parallel-authority',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                        'owner_ref': 'runtime-path',
                                                                                                        'source_ast_sha256': 'd54923d8775ae587d711a6357c82f053215dff344d2fc505afd1dfec78a1fe13'}}


def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 2, 3, 4, 5, "model:test")


def _expression(
    *, instance_ref: str = "entity:alice", class_ref: str = "concept:mother"
) -> SemanticExpression:
    app = SemanticApplication(
        "application:description",
        "op:type",
        class_ref,
        (
            RoleBinding("role:instance", GroundedReference(instance_ref)),
            RoleBinding("role:class", GroundedReference(class_ref)),
        ),
    )
    return SemanticExpression.create(
        applications=(app,), root_refs=(app.application_ref,)
    )


def _unresolved_expression() -> SemanticExpression:
    app = SemanticApplication(
        "application:unresolved-description",
        "op:type",
        "concept:mother",
        (
            RoleBinding("role:instance", UnresolvedValue("unresolved:instance")),
            RoleBinding("role:class", GroundedReference("concept:mother")),
        ),
    )
    gap = UnresolvedFiller(
        "unresolved:instance",
        app.application_ref,
        "role:instance",
        "anchor",
        ("entity",),
        True,
    )
    return SemanticExpression.create(
        applications=(app,),
        root_refs=(app.application_ref,),
        unresolved_fillers=(gap,),
    )


def _request(**changes: object) -> DescriptionRequest:
    target = changes.pop("target_ref", "entity:alice")
    values = {
        "source_expression": _query_expression(target),
        "situation": _situation(_pin()),
        "max_depth": 3,
        "max_facts": 16,
    }
    values.update(changes)
    return DescriptionRequest.create(**values)


def _result(**changes: object) -> DescriptionResult:
    answer_expression = changes.get("answer_expression", _expression())
    assert answer_expression is None or isinstance(
        answer_expression, SemanticExpression
    )
    values = {
        "request": _request(),
        "answer_expression": answer_expression,
        "completeness": DescriptionCompleteness.SUFFICIENT,
        "fact_refs": (
            () if answer_expression is None else ("fact:description:test",)
        ),
        "definition_refs": ("definition:test",),
        "claim_refs": ("claim:test",),
        "source_refs": ("source:test",),
        "proof_refs": ("proof:test",),
        "revision_pin": _pin(),
    }
    values.update(changes)
    return DescriptionResult.create(**values)


def test_description_request_roundtrip_binds_query_target_bounds_and_pin() -> None:
    request = _request()
    assert request.abi_version == DESCRIPTION_ABI_VERSION == 2
    assert DescriptionRequest.from_dict(request.as_dict()) == request
    changed_query = _request(
        source_expression=_query_expression("entity:bob")
    )
    assert changed_query.description_request_ref != request.description_request_ref
    forged = request.as_dict()
    forged["description_request_ref"] = "description_request:forged"
    with pytest.raises(ValueError, match="description_request_ref mismatch"):
        DescriptionRequest.from_dict(forged)


def test_description_request_requires_current_r3_query_result_namespace() -> None:
    # Retain the historical node identity, not its retired ABI 1 namespace rule:
    # ABI 2 rejects the source-query argument entirely.
    with pytest.raises(TypeError, match="source_query_ref"):
        _request(source_query_ref="query:wellformed-but-not-an-r3-result")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_expression_ref", "query:wellformed-but-not-an-expression"),
        ("target_ref", "mother"),
        ("max_depth", True),
        ("max_facts", 257),
        ("revision_pin", []),
    ),
    ids=("bad-query-ref", "bad-target-ref", "bool-depth", "fact-overflow", "wrong-pin-container"),
)
def test_description_request_rejects_noncanonical_refs_scalars_and_containers(
    field: str, value: object
) -> None:
    payload = _request().as_dict()
    payload[field] = value
    with pytest.raises((TypeError, ValueError)):
        DescriptionRequest.from_dict(payload)


@pytest.mark.parametrize(
    "completeness",
    (
        DescriptionCompleteness.SUFFICIENT,
        DescriptionCompleteness.PARTIAL,
        DescriptionCompleteness.MISSING,
        DescriptionCompleteness.CONFLICT,
        DescriptionCompleteness.BUDGET_EXHAUSTED,
    ),
    ids=("sufficient", "partial", "missing", "conflict", "budget-exhausted"),
)
def test_description_result_roundtrips_every_completeness_state(
    completeness: DescriptionCompleteness,
) -> None:
    if completeness is DescriptionCompleteness.MISSING:
        result = _result(
            answer_expression=None,
            completeness=completeness,
            fact_refs=(),
            definition_refs=(),
            claim_refs=(),
            source_refs=(),
            proof_refs=(),
        )
    elif completeness is DescriptionCompleteness.BUDGET_EXHAUSTED:
        result = _result(answer_expression=None, completeness=completeness)
    else:
        result = _result(completeness=completeness)
    assert DescriptionResult.from_dict(result.as_dict()) == result


def test_description_result_rejects_forgery_wrong_containers_and_pin() -> None:
    result = _result()
    attacks = []
    forged = result.as_dict()
    forged["description_result_ref"] = "description_result:forged"
    attacks.append(forged)
    wrong_refs = result.as_dict()
    wrong_refs["proof_refs"] = ("proof:not-a-list",)
    attacks.append(wrong_refs)
    wrong_pin = result.as_dict()
    wrong_pin["revision_pin"]["world_revision"] += 1
    attacks.append(wrong_pin)
    forged_expression = result.as_dict()
    forged_expression["answer_expression"]["expression_ref"] = "expression:forged"
    attacks.append(forged_expression)
    for payload in attacks:
        with pytest.raises((TypeError, ValueError)):
            DescriptionResult.from_dict(payload)


def test_content_result_requires_exact_evidence_and_targeted_settled_meaning() -> None:
    for field in ("fact_refs", "claim_refs", "source_refs", "proof_refs"):
        with pytest.raises(ValueError, match=field):
            _result(**{field: ()})
    with pytest.raises(ValueError, match="requested target"):
        _result(
            answer_expression=_expression(
                instance_ref="entity:bob", class_ref="concept:job_role"
            )
        )
    with pytest.raises(ValueError, match="unresolved meaning"):
        _result(answer_expression=_unresolved_expression())


def test_description_target_must_be_a_descriptive_filler_not_metadata() -> None:
    class_only = _expression()
    predicate_only = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:predicate-only",
                "op:relation",
                "rel:parent",
                (
                    RoleBinding(
                        "role:subject", GroundedReference("entity:bob")
                    ),
                    RoleBinding(
                        "role:object", GroundedReference("entity:alice")
                    ),
                ),
            ),
        ),
        root_refs=("application:predicate-only",),
    )
    dimension_only = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:dimension-only",
                "op:state",
                "dimension:status",
                (
                    RoleBinding(
                        "role:subject", GroundedReference("entity:bob")
                    ),
                    RoleBinding(
                        "role:dimension", GroundedReference("dimension:status")
                    ),
                    RoleBinding(
                        "role:value", GroundedReference("value:offline")
                    ),
                ),
            ),
        ),
        root_refs=("application:dimension-only",),
    )
    type_only = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:type-only",
                "op:type",
                "concept:mother",
                (
                    RoleBinding(
                        "role:instance", GroundedReference("entity:bob")
                    ),
                    RoleBinding(
                        "role:type", GroundedReference("concept:mother")
                    ),
                ),
            ),
        ),
        root_refs=("application:type-only",),
    )
    relation_only = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:relation-only",
                "op:relation",
                "rel:parent",
                (
                    RoleBinding(
                        "role:subject", GroundedReference("entity:bob")
                    ),
                    RoleBinding(
                        "role:relation", GroundedReference("rel:parent")
                    ),
                    RoleBinding(
                        "role:object", GroundedReference("entity:alice")
                    ),
                ),
            ),
        ),
        root_refs=("application:relation-only",),
    )
    label_type_only = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:label-type-only",
                "op:designation",
                "label:name",
                (
                    RoleBinding(
                        "role:label_type", GroundedReference("label:name")
                    ),
                    RoleBinding(
                        "role:surface", LiteralValue("string", "Bob")
                    ),
                    RoleBinding(
                        "role:target", GroundedReference("entity:bob")
                    ),
                ),
            ),
        ),
        root_refs=("application:label-type-only",),
    )
    scope_child = SemanticApplication(
        "application:scope-only-child",
        "op:type",
        "concept:person",
        (
            RoleBinding("role:instance", GroundedReference("entity:bob")),
            RoleBinding("role:class", GroundedReference("concept:person")),
        ),
    )
    scope_only = SemanticExpression.create(
        applications=(scope_child,),
        root_refs=("scope:only",),
        scope_operators=(
            ScopeOperator(
                "scope:only",
                "scope:epistemic",
                "value:known",
                scope_child.application_ref,
            ),
        ),
    )
    event_only = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:event-only",
                "op:event",
                "event:learn",
                (
                    RoleBinding(
                        "role:actor", GroundedReference("entity:bob")
                    ),
                    RoleBinding(
                        "role:event", GroundedReference("event:learn")
                    ),
                ),
            ),
        ),
        root_refs=("application:event-only",),
    )
    cases = (
        ("concept:mother", class_only),
        ("rel:parent", predicate_only),
        ("dimension:status", dimension_only),
        ("value:offline", dimension_only),
        ("label:name", label_type_only),
        ("value:known", scope_only),
        ("concept:mother", type_only),
        ("rel:parent", relation_only),
        ("event:learn", event_only),
    )
    for target_ref, expression in cases:
        with pytest.raises(ValueError, match="centered on its requested target"):
            _result(
                request=_request(target_ref=target_ref),
                answer_expression=expression,
            )

    designation = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:designation-participant",
                "op:designation",
                "label:name",
                (
                    RoleBinding(
                        "role:label_type", GroundedReference("label:name")
                    ),
                    RoleBinding(
                        "role:surface", LiteralValue("string", "Alice")
                    ),
                    RoleBinding(
                        "role:target", GroundedReference("entity:alice")
                    ),
                ),
            ),
        ),
        root_refs=("application:designation-participant",),
    )
    relation = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:relation-participant",
                "op:relation",
                "rel:parent",
                (
                    RoleBinding(
                        "role:subject", GroundedReference("entity:alice")
                    ),
                    RoleBinding(
                        "role:object", GroundedReference("entity:bob")
                    ),
                ),
            ),
        ),
        root_refs=("application:relation-participant",),
    )
    state = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:state-participant",
                "op:state",
                "dimension:status",
                (
                    RoleBinding(
                        "role:subject", GroundedReference("entity:alice")
                    ),
                    RoleBinding(
                        "role:dimension", GroundedReference("dimension:status")
                    ),
                    RoleBinding(
                        "role:value", GroundedReference("value:offline")
                    ),
                ),
            ),
        ),
        root_refs=("application:state-participant",),
    )
    event = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "application:event-participant",
                "op:event",
                "event:learn",
                (
                    RoleBinding(
                        "role:actor", GroundedReference("entity:alice")
                    ),
                ),
            ),
        ),
        root_refs=("application:event-participant",),
    )
    for expression in (designation, class_only, relation, state, event):
        result = _result(answer_expression=expression)
        assert result.request.target_ref == "entity:alice"


def test_description_fact_refs_use_persistent_fact_namespace() -> None:
    expression = _expression()
    application_ref = expression.applications[0].application_ref
    result = _result(
        answer_expression=expression,
        fact_refs=("fact:description:test",),
    )
    assert result.fact_refs == ("fact:description:test",)
    with pytest.raises(ValueError, match="fact namespace"):
        _result(answer_expression=expression, fact_refs=(application_ref,))


def _wrapped_expression(wrapper: str) -> SemanticExpression:
    child = SemanticApplication(
        "application:child",
        "op:type",
        "concept:mother",
        (
            RoleBinding(
                "role:instance", GroundedReference("entity:alice")
            ),
            RoleBinding(
                "role:class", GroundedReference("concept:mother")
            ),
        ),
    )
    if wrapper == "application":
        parent = SemanticApplication(
            "application:parent",
            "op:event",
            "event:describe",
            (RoleBinding("role:content", ApplicationFiller(child.application_ref)),),
        )
        return SemanticExpression.create(
            applications=(child, parent), root_refs=(parent.application_ref,)
        )
    if wrapper == "scope":
        scope = ScopeOperator(
            "scope:test",
            "scope:epistemic",
            "value:known",
            child.application_ref,
        )
        return SemanticExpression.create(
            applications=(child,),
            root_refs=(scope.scope_ref,),
            scope_operators=(scope,),
        )
    if wrapper == "link":
        sibling = SemanticApplication(
            "application:sibling",
            "op:type",
            "concept:person",
            (
                RoleBinding(
                    "role:instance", GroundedReference("entity:bob")
                ),
                RoleBinding(
                    "role:class", GroundedReference("concept:person")
                ),
            ),
        )
        link = ExpressionLink(
            "link:test",
            "link:conjunction",
            (child.application_ref, sibling.application_ref),
        )
        return SemanticExpression.create(
            applications=(child, sibling),
            root_refs=(link.link_ref,),
            expression_links=(link,),
        )
    bound_child = SemanticApplication(
        "application:bound-child",
        "op:relation",
        "rel:describes",
        (
            RoleBinding(
                "role:subject", GroundedReference("entity:alice")
            ),
            RoleBinding("role:object", BoundVariable("?description")),
        ),
    )
    binder = VariableBinder(
        "binder:test", "?description", bound_child.application_ref
    )
    return SemanticExpression.create(
        applications=(bound_child,),
        root_refs=(binder.binder_ref,),
        binders=(binder,),
    )


@pytest.mark.parametrize(
    "wrapper",
    ("application", "scope", "link", "binder"),
    ids=("application", "scope", "link", "binder"),
)
def test_description_max_depth_bounds_complete_answer_graph(wrapper: str) -> None:
    expression = _wrapped_expression(wrapper)
    with pytest.raises(ValueError, match="max_depth"):
        _result(
            request=_request(max_depth=1),
            answer_expression=expression,
        )


def test_description_max_facts_bounds_persistent_fact_refs_only() -> None:
    expression = _wrapped_expression("application")
    result = _result(
        request=_request(max_facts=1),
        answer_expression=expression,
        fact_refs=("fact:description:one",),
    )
    assert len(result.answer_expression.applications) == 2
    with pytest.raises(ValueError, match="bound"):
        _result(
            request=_request(max_facts=1),
            answer_expression=expression,
            fact_refs=("fact:description:one", "fact:description:two"),
        )


def test_missing_result_rejects_positive_evidence_and_content() -> None:
    with pytest.raises(ValueError, match="cannot carry an answer"):
        _result(completeness=DescriptionCompleteness.MISSING)
    with pytest.raises(ValueError, match="positive evidence"):
        _result(
            answer_expression=None,
            completeness=DescriptionCompleteness.MISSING,
        )


def test_description_has_no_parallel_persistent_authority_plane(
    tmp_path: Path,
) -> None:
    assert not hasattr(authority_module, "ReviewedDescriptionGraph")
    assert not hasattr(LinkedAuthority, "reviewed_descriptions_for_target")
    manifest = json.loads((ROOT / "data/authority/manifest.json").read_text("utf-8"))
    for owner in manifest["owners"]:
        owner["path"] = str((ROOT / "data/authority" / owner["path"]).resolve())
    owner = next(row for row in manifest["owners"] if row["name"] == "conversation")
    payload = json.loads(Path(owner["path"]).read_text("utf-8"))
    payload["description_graphs"] = []
    stale = tmp_path / "stale-parallel-description-owner.json"
    stale.write_text(json.dumps(payload), encoding="utf-8")
    owner.update(path=str(stale), sha256=sha256_governed_text(stale))
    store = AuthorityStore()
    manifest["_store"] = store
    with pytest.raises(AuthorityLinkError, match="parallel description_graphs"):
        AuthorityLinker().link(manifest)
    assert store.active_generation is None
