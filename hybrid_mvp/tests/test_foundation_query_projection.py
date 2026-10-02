"""Independent canonical query-request representation; no public activation."""
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from cemm_authoritative_hybrid import expressions as expr
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expression_transform import instantiate_bindings, negate_expression
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import PERSISTENT_OPERATORS


def _query(ref="local:query", requested="description", target="opaque:known-target"):
    node_type = getattr(expr, "QueryProjection", None)
    assert node_type is not None, "canonical QueryProjection leaf is missing"
    return node_type(ref, requested, target)


def _request(ref="local:query", requested="description", target="opaque:known-target", **kwargs):
    return expr.SemanticExpression.create(
        applications=(), root_refs=(ref,), query_projections=(_query(ref, requested, target),), **kwargs
    )


def _app(ref="local:claim", filler=None):
    return expr.SemanticApplication(ref, "op:type", "relation:instance_of", (
        expr.RoleBinding("role:subject", filler or expr.GroundedReference("entity:alice")),
        expr.RoleBinding("role:type", expr.GroundedReference("opaque:known-target")),
    ))


def test_pure_request_has_exact_nonpersistent_leaf_and_wire_schema():
    request = _request()
    assert expr.SEMANTIC_EXPRESSION_ABI_VERSION == 3
    assert request.applications == ()
    assert request.root_refs == ("projection:0",)
    assert request.query_projections == (_query("projection:0"),)
    assert not isinstance(request.query_projections[0], expr.SemanticApplication)
    wire = request.as_dict()
    assert set(wire) == {"abi_version", "expression_ref", "applications", "root_refs", "scope_operators",
                         "expression_links", "binders", "unresolved_fillers", "query_projections"}
    assert wire["query_projections"] == [{"projection_ref": "projection:0",
                                         "requested_content": "description", "target_ref": "opaque:known-target"}]
    assert expr.SemanticExpression.from_dict(wire) == request
    assert PERSISTENT_OPERATORS == frozenset({"op:designation", "op:type", "op:relation", "op:state", "op:event"})


def test_description_definition_membership_and_lexical_lookup_have_distinct_identities():
    description, definition = _request(), _request(requested="definition")
    membership = expr.SemanticExpression.create(
        applications=(_app(filler=expr.BoundVariable("?member")),), root_refs=("local:binder",),
        binders=(expr.VariableBinder("local:binder", "?member", "local:claim"),),
    )
    lexical = expr.SemanticExpression.create(applications=(expr.SemanticApplication(
        "local:lexical", "op:designation", "label:lexical", (
            expr.RoleBinding("role:label_type", expr.GroundedReference("label:lexical")),
            expr.RoleBinding("role:surface", expr.LiteralValue("string", "unknown form")),
            expr.RoleBinding("role:target", expr.BoundVariable("?target")),
        )),), root_refs=("local:binder",),
        binders=(expr.VariableBinder("local:binder", "?target", "local:lexical"),))
    assert len({item.expression_ref for item in (description, definition, membership, lexical)}) == 4
    assert membership.query_projections == lexical.query_projections == ()


def test_projection_alpha_renaming_preserves_target_and_requested_content():
    first = _request("local:first")
    second, mapping = expr.SemanticExpression._create_with_ref_map(
        applications=(), root_refs=("renamed:leaf",), query_projections=(_query("renamed:leaf"),))
    assert first == second
    assert mapping == {"renamed:leaf": "projection:0"}
    assert _request(target="opaque:different").expression_ref != first.expression_ref
    assert _request(requested="definition").expression_ref != first.expression_ref


def test_projection_fields_are_closed_bounded_and_immutable():
    class ForeignString(str):
        pass

    node = _query()
    with pytest.raises(FrozenInstanceError):
        node.target_ref = "other"
    for requested in ("membership", "lexical", "", None, 1, ["description"]):
        with pytest.raises(ValueError):
            _query(requested=requested)
    for target in ("", None, 1, "x" * 257, ForeignString("opaque:target")):
        with pytest.raises(ValueError):
            _query(target=target)
    for ref in ("", None, 1, "x" * 257, ForeignString("local:leaf")):
        with pytest.raises(ValueError):
            _query(ref=ref)
    assert _request(target="?opaque").query_projections[0].target_ref == "?opaque"
    assert _request(target="x" * 256).query_projections[0].target_ref == "x" * 256


def test_projection_wire_payload_cannot_mutate_canonical_leaf():
    request = _request()
    payload = request.as_dict()
    payload["query_projections"][0]["target_ref"] = "opaque:wire-only"
    assert request.query_projections[0].target_ref == "opaque:known-target"
    assert project_expression(request).grounded_refs == ("opaque:known-target",)


def test_scoped_query_wire_payload_cannot_mutate_canonical_scope():
    query = _query()
    scope = expr.ScopeOperator("local:scope", "scope:quotation", "scope_value:quoted", query.projection_ref)
    request = expr.SemanticExpression.create(applications=(), root_refs=(scope.scope_ref,),
        scope_operators=(scope,), query_projections=(query,))
    original_scope = request.scope_operators[0]
    payload = request.as_dict()
    assert payload["scope_operators"] == [{"scope_ref": "scope:0", "operator_type": "scope:quotation",
        "value_ref": "scope_value:quoted", "operand_ref": "projection:0"}]
    payload["scope_operators"][0]["operand_ref"] = "opaque:wire-only"
    payload["scope_operators"][0]["value_ref"] = "scope_value:changed"
    assert original_scope.operand_ref == "projection:0"
    assert original_scope.value_ref == "scope_value:quoted"
    assert expr.SemanticExpression.from_dict(request.as_dict()) == request
    assert project_expression(request).query_projections == request.query_projections


def test_bound_query_wire_payload_cannot_mutate_canonical_binder():
    query = _query()
    binder = expr.VariableBinder("local:binder", "?request", query.projection_ref)
    request = expr.SemanticExpression.create(applications=(), root_refs=(binder.binder_ref,),
        binders=(binder,), query_projections=(query,))
    original_binder = request.binders[0]
    payload = request.as_dict()
    assert payload["binders"] == [{"binder_ref": "binder:0", "variable_ref": "?v0", "body_ref": "projection:0"}]
    payload["binders"][0]["body_ref"] = "opaque:wire-only"
    payload["binders"][0]["variable_ref"] = "?changed"
    assert original_binder.body_ref == "projection:0"
    assert original_binder.variable_ref == "?v0"
    assert expr.SemanticExpression.from_dict(request.as_dict()) == request
    assert project_expression(request).query_projections == request.query_projections


def test_projection_codec_rejects_old_abi_tampering_and_unknown_wire_fields():
    wire = _request().as_dict()
    for abi in (2, 1, True, 3.0, "3"):
        bad = deepcopy(wire)
        bad["abi_version"] = abi
        with pytest.raises(ValueError):
            expr.SemanticExpression.from_dict(bad)
    for key, value in (("target_ref", "opaque:other"), ("requested_content", "definition"),
                       ("projection_ref", "forged:local"), ("kind", "concept")):
        bad = deepcopy(wire)
        bad["query_projections"][0][key] = value
        with pytest.raises(ValueError):
            expr.SemanticExpression.from_dict(bad)
    for field in ("query_projections", "target_ref"):
        bad = deepcopy(wire)
        if field == "query_projections":
            del bad[field]
        else:
            del bad["query_projections"][0][field]
        with pytest.raises(ValueError):
            expr.SemanticExpression.from_dict(bad)
    bad = deepcopy(wire)
    bad["query_projections"] = tuple(bad["query_projections"])
    with pytest.raises(ValueError):
        expr.SemanticExpression.from_dict(bad)


def test_rehashed_projection_payload_cannot_bypass_shape_or_canonical_ref_validation():
    request = _request()
    for alteration in ("requested", "ref", "duplicate", "unreachable"):
        node = request.query_projections[0]
        if alteration == "requested":
            object.__setattr__(node, "requested_content", "membership")
            nodes, roots = (node,), request.root_refs
        elif alteration == "ref":
            nodes, roots = (_query("local:forged"),), ("local:forged",)
        elif alteration == "duplicate":
            nodes, roots = (node, node), request.root_refs
        else:
            nodes, roots = (node,), ("missing:root",)
        material = dict(abi_version=3, applications=(), root_refs=roots, scope_operators=(),
                        expression_links=(), binders=(), unresolved_fillers=(), query_projections=nodes)
        forged = object.__new__(expr.SemanticExpression)
        for field, value in material.items():
            if field != "abi_version":
                object.__setattr__(forged, field, value)
        object.__setattr__(forged, "expression_ref", stable_ref("expression", material))
        with pytest.raises(ValueError):
            expr.SemanticExpression.from_dict(forged.as_dict())
        request = _request()


def test_empty_multiple_duplicate_dangling_and_unreachable_projection_forests_are_rejected():
    query = _query()
    cases = [dict(applications=(), root_refs=()),
             dict(applications=(), root_refs=("missing",), query_projections=(query,)),
             dict(applications=(), root_refs=(query.projection_ref, query.projection_ref), query_projections=(query,)),
             dict(applications=(), root_refs=(query.projection_ref,), query_projections=(query, query)),
             dict(applications=(), root_refs=(query.projection_ref, "other"), query_projections=(query, _query("other"))),
             dict(applications=(_app(),), root_refs=("local:claim",), query_projections=(query,)),
             dict(applications=(_app(ref=query.projection_ref),), root_refs=(query.projection_ref,), query_projections=(query,))]
    for case in cases:
        with pytest.raises(ValueError):
            expr.SemanticExpression.create(**case)


def test_nested_query_leaf_is_lossless_but_parent_sharing_is_rejected():
    query = _query()
    app = _app(filler=expr.ApplicationFiller(query.projection_ref))
    request = expr.SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,),
                                             query_projections=(query,))
    assert request.applications[0].roles[0].filler == expr.ApplicationFiller("projection:0")
    assert expr.SemanticExpression.from_dict(request.as_dict()) == request
    assert project_expression(request).descendant_applications("application:0") == request.applications
    for roots, scopes in (((app.application_ref, query.projection_ref), ()),
                          ((app.application_ref, "scope:other"),
                           (expr.ScopeOperator("scope:other", "scope:quotation", "quoted", query.projection_ref),))):
        with pytest.raises(ValueError):
            expr.SemanticExpression.create(applications=(app,), root_refs=roots,
                scope_operators=scopes, query_projections=(query,))


def test_query_leaf_counts_against_existing_root_depth_and_total_node_bounds():
    for bounds in (expr.ExpressionBounds(max_total_nodes=0), expr.ExpressionBounds(max_depth=0),
                   expr.ExpressionBounds(max_roots=0)):
        with pytest.raises(ValueError):
            _request(bounds=bounds)
    query = _query()
    scopes = (expr.ScopeOperator("scope:outer", "scope:quotation", "quoted", query.projection_ref),)
    for bounds in (expr.ExpressionBounds(max_total_nodes=1), expr.ExpressionBounds(max_depth=1)):
        with pytest.raises(ValueError):
            expr.SemanticExpression.create(applications=(), root_refs=("scope:outer",),
                scope_operators=scopes, query_projections=(query,), bounds=bounds)
    nested = expr.SemanticExpression.create(applications=(), root_refs=("scope:outer",),
        scope_operators=scopes, query_projections=(query,),
        bounds=expr.ExpressionBounds(max_total_nodes=2, max_depth=2, max_applications=0))
    assert len(project_expression(nested).node_by_ref) == 2
    release = expr.ExpressionBounds()
    scopes = tuple(expr.ScopeOperator(f"scope:{index}", "scope:quotation", "quoted",
        f"scope:{index + 1}" if index + 1 < release.max_depth else query.projection_ref)
        for index in range(release.max_depth))
    with pytest.raises(ValueError, match="depth bound"):
        expr.SemanticExpression.create(applications=(), root_refs=("scope:0",),
            scope_operators=scopes, query_projections=(query,))


def test_projection_index_is_immutable_grounded_and_contains_no_synthetic_applications():
    request = _request()
    index = project_expression(request)
    assert index.query_projections == request.query_projections
    assert index.node_by_ref["projection:0"] is request.query_projections[0]
    assert index.grounded_refs == ("opaque:known-target",)
    assert index.root_nodes() == request.query_projections
    assert index.applications == index.root_applications() == index.descendant_applications("projection:0") == ()
    assert index.applications_by_operator == {}
    assert index.literal_values == index.bound_variable_refs == index.unresolved_refs == ()
    with pytest.raises(TypeError):
        index.node_by_ref["projection:0"] = None
    forged = object.__new__(expr.SemanticExpression)
    for field, value in vars(request).items():
        object.__setattr__(forged, field, value)
    object.__setattr__(forged, "expression_ref", "expression:forged")
    with pytest.raises(ValueError):
        project_expression(forged)


def test_generic_transformations_preserve_projection_structure():
    query = _query()
    app = _app(filler=expr.ApplicationFiller(query.projection_ref))
    request = expr.SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,),
        query_projections=(query,))
    assert instantiate_bindings(request, ()) == request
    negative = negate_expression(request)
    assert negative.query_projections == request.query_projections
    assert negative.applications == request.applications
    assert project_expression(negative).grounded_refs == ("opaque:known-target",)
    assert instantiate_bindings(_request(), ()) == _request()
    assert negate_expression(_request()).query_projections == _request().query_projections
    bound_query = expr.SemanticExpression.create(applications=(), root_refs=("local:binder",),
        binders=(expr.VariableBinder("local:binder", "?resolved", "local:query"),),
        query_projections=(_query(target="?opaque-target"),))
    resolved = instantiate_bindings(bound_query, (("?v0", "opaque:bound-value"),))
    assert resolved.binders == ()
    assert resolved == _request(target="?opaque-target")


def test_verified_meaning_authenticates_identity_covered_projection():
    request = _request()
    verified = expr.VerifiedMeaning.create(program_ref="program:request", expression=request,
        grounding_refs=("opaque:known-target",), coverage_receipt_ref="coverage:request",
        compilation_proof_ref="proof:request", verification_receipt_ref="verification:request",
        revision_pin=RevisionPin("authority:g1", 0, 0, 0, 0, "model:m1"))
    assert expr.VerifiedMeaning.from_dict(verified.as_dict()) == verified
    forged = object.__new__(expr.SemanticExpression)
    for field, value in vars(request).items():
        object.__setattr__(forged, field, value)
    object.__setattr__(forged, "query_projections", (_query("projection:0", target="opaque:other"),))
    with pytest.raises(ValueError, match="expression_ref mismatch"):
        expr.VerifiedMeaning.create(program_ref="program:request", expression=forged,
            grounding_refs=("opaque:other",), coverage_receipt_ref="coverage:request",
            compilation_proof_ref="proof:request", verification_receipt_ref="verification:request",
            revision_pin=verified.revision_pin)


def test_description_answer_boundary_rejects_query_content_before_reconstruction():
    from cemm_authoritative_hybrid.descriptions import DescriptionCompleteness, DescriptionRequest, DescriptionResult

    target = "opaque:known-target"
    claim = _app(filler=expr.GroundedReference(target))
    query = _query()
    answer = expr.SemanticExpression.create(applications=(claim,),
        root_refs=(claim.application_ref, query.projection_ref), query_projections=(query,))
    pin = RevisionPin("authority:g1", 0, 0, 0, 0, "model:m1")
    from tests.test_foundation_description_request_lineage import _situation
    request = DescriptionRequest.create(source_expression=_request(target=target), situation=_situation(pin),
        max_depth=6, max_facts=24)
    with pytest.raises(ValueError, match="query projection"):
        DescriptionResult.create(request=request, answer_expression=answer,
            completeness=DescriptionCompleteness.SUFFICIENT, fact_refs=("fact:claim",),
            definition_refs=("application:claim",), claim_refs=("claim:one",),
            source_refs=("source:one",), proof_refs=("proof:one",), revision_pin=pin)


def test_proof_application_cloning_explicitly_rejects_query_only_answer():
    from cemm_authoritative_hybrid.descriptions import DescriptionResult
    from cemm_authoritative_hybrid.proof_bundle import ProofBundle

    # Tampering must fail explicitly, not erase the pure request as zero claims.
    description = object.__new__(DescriptionResult)
    object.__setattr__(description, "answer_expression", _request())
    proof = object.__new__(ProofBundle)
    object.__setattr__(proof, "description", description)
    object.__setattr__(proof, "application_refs", ())
    with pytest.raises(ValueError, match="query projection"):
        _ = proof.applications

__cemm_test_inventory__ = {'tests/test_foundation_query_projection.py::test_pure_request_has_exact_nonpersistent_leaf_and_wire_schema': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:foundation-pure-request-has-exact-nonpersistent-leaf-and-wire-schema',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                               'source_ast_sha256': 'b8c6d347cb82f249e8f6c5adeed611c3a348ff99f96bb5783321b27b0eb212f0'},
 'tests/test_foundation_query_projection.py::test_description_definition_membership_and_lexical_lookup_have_distinct_identities': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-description-definition-membership-and-lexical-lookup-have-distinct-identities',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '4db3b3bac62f08b6f075c1daaeb315b9bfb051b9a792223ee1231aea722140c7'},
 'tests/test_foundation_query_projection.py::test_projection_alpha_renaming_preserves_target_and_requested_content': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-alpha-renaming-preserves-target-and-requested-content',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': '15905d9551907f9fcba0799212b312eea5613d5352723df61339442f6a90a553'},
 'tests/test_foundation_query_projection.py::test_projection_fields_are_closed_bounded_and_immutable': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:foundation-projection-fields-are-closed-bounded-and-immutable',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                        'source_ast_sha256': '2752a550e0fd390a8b2151b2faaae8575000f371bf62d4567b0ac8f7497d9686'},
 'tests/test_foundation_query_projection.py::test_projection_wire_payload_cannot_mutate_canonical_leaf': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:foundation-projection-wire-payload-cannot-mutate-canonical-leaf',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                          'source_ast_sha256': '0ee338d5cc9453e7889d6d12e9309425ad76c102309055532b2258348488fdd5'},
 'tests/test_foundation_query_projection.py::test_scoped_query_wire_payload_cannot_mutate_canonical_scope': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-scoped-query-wire-payload-cannot-mutate-canonical-scope',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                             'source_ast_sha256': 'a535b2baabf115770c63627b171c089bc96bd99bb80e0baf82aade9467aa4313'},
 'tests/test_foundation_query_projection.py::test_bound_query_wire_payload_cannot_mutate_canonical_binder': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-bound-query-wire-payload-cannot-mutate-canonical-binder',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                             'source_ast_sha256': '2f98557b4d24bb9ebfe4ab6a937ad0951519349195ed2d43eb797b0ae7dcdaa8'},
 'tests/test_foundation_query_projection.py::test_projection_codec_rejects_old_abi_tampering_and_unknown_wire_fields': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-codec-rejects-old-abi-tampering-and-unknown-wire-fields',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '0990cca68c72c000c306392e1c30c288c857a54a81f5ebe438ff54dc54a8bfc4'},
 'tests/test_foundation_query_projection.py::test_rehashed_projection_payload_cannot_bypass_shape_or_canonical_ref_validation': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-rehashed-projection-payload-cannot-bypass-shape-or-canonical-ref-validation',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '344218f59cf075aa0e8b904d7263399c67e3d4154338ec0507bde1ec7a63c9ff'},
 'tests/test_foundation_query_projection.py::test_empty_multiple_duplicate_dangling_and_unreachable_projection_forests_are_rejected': {'activation_phase': 'R4',
                                                                                                                                       'assertion_ref': 'assertion:foundation-empty-multiple-duplicate-dangling-and-unreachable-projection-forests-are-rejected',
                                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                                       'source_ast_sha256': 'dda4fc12a6bdcc91c48aca6a5afbdd5b3296ad7b27f151a03ee07c0d92c9d999'},
 'tests/test_foundation_query_projection.py::test_nested_query_leaf_is_lossless_but_parent_sharing_is_rejected': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-nested-query-leaf-is-lossless-but-parent-sharing-is-rejected',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'd65092eb2ddb06f7fd9e4bea124dffb4259d9d50087f4fee87da13bee1396f9f'},
 'tests/test_foundation_query_projection.py::test_query_leaf_counts_against_existing_root_depth_and_total_node_bounds': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-query-leaf-counts-against-existing-root-depth-and-total-node-bounds',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'd1a3b224ac077303686a7b5380c88b8df588652602fcdc5dc96d42e082705a4c'},
 'tests/test_foundation_query_projection.py::test_projection_index_is_immutable_grounded_and_contains_no_synthetic_applications': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-projection-index-is-immutable-grounded-and-contains-no-synthetic-applications',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '61e0a3559426eecc43d171d8f0be15fb085580f567d457ab5378a6f0b6a09be2'},
 'tests/test_foundation_query_projection.py::test_generic_transformations_preserve_projection_structure': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-generic-transformations-preserve-projection-structure',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': '50b944fe11a6a214d4131f475bd9bbc4f1071f6650228baf2414177459519a3f'},
 'tests/test_foundation_query_projection.py::test_verified_meaning_authenticates_identity_covered_projection': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-verified-meaning-authenticates-identity-covered-projection',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': 'cf018f877050b9cbfc1b9776b6e4f3f16a0a1201f9d099c972318f12d65d4d53'},
 'tests/test_foundation_query_projection.py::test_description_answer_boundary_rejects_query_content_before_reconstruction': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-description-answer-boundary-rejects-query-content-before-reconstruction',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': 'a4ecc5b645159fae75c0c3bb25dd53fb115a0482d7a424d0335482a14a3aefe6'},
 'tests/test_foundation_query_projection.py::test_proof_application_cloning_explicitly_rejects_query_only_answer': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-proof-application-cloning-explicitly-rejects-query-only-answer',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': '3d6c30fec186e54b1fe2d9dfbe4ee84748ae07df7301fcfd43d9b6c1b6be6664'}}
