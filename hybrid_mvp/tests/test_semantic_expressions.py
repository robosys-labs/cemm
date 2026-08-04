from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace

import pytest

from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionBounds,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    UnresolvedFiller,
    UnresolvedValue,
    VariableBinder,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.persistence import RevisionPin


def _application(
    ref: str,
    *,
    subject: str = "entity:alice",
    object_: str = "entity:bob",
) -> SemanticApplication:
    return SemanticApplication(
        application_ref=ref,
        operator="op:relation",
        predicate_ref="relation:love",
        roles=(
            RoleBinding("role:subject", GroundedReference(subject)),
            RoleBinding("role:object", GroundedReference(object_)),
        ),
    )


def _pin() -> RevisionPin:
    return RevisionPin("authority:g1", 2, 3, 4, 5, "model:m1")


def test_expression_is_immutable_and_excludes_evidence_geometry() -> None:
    expression = SemanticExpression.create(
        applications=(_application("raw-app"),),
        root_refs=("raw-app",),
    )

    with pytest.raises(FrozenInstanceError):
        expression.root_refs = ()  # type: ignore[misc]
    assert "source_unit_refs" not in {field.name for field in fields(expression)}
    assert "evidence" not in {field.name for field in fields(expression)}


def test_alpha_renaming_and_declaration_order_do_not_change_identity() -> None:
    left = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "outer-a",
                "op:event",
                "event:know",
                (
                    RoleBinding("role:experiencer", GroundedReference("entity:alice")),
                    RoleBinding("role:content", ApplicationFiller("inner-a")),
                ),
            ),
            SemanticApplication(
                "inner-a",
                "op:type",
                "concept:person",
                (RoleBinding("role:instance", BoundVariable("?person-a")),),
            ),
        ),
        root_refs=("binder-a",),
        binders=(VariableBinder("binder-a", "?person-a", "outer-a"),),
    )
    right = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "renamed-inner",
                "op:type",
                "concept:person",
                (RoleBinding("role:instance", BoundVariable("?renamed")),),
            ),
            SemanticApplication(
                "renamed-outer",
                "op:event",
                "event:know",
                (
                    RoleBinding("role:content", ApplicationFiller("renamed-inner")),
                    RoleBinding("role:experiencer", GroundedReference("entity:alice")),
                ),
            ),
        ),
        root_refs=("renamed-binder",),
        binders=(
            VariableBinder("renamed-binder", "?renamed", "renamed-outer"),
        ),
    )

    assert left == right
    assert left.expression_ref == right.expression_ref
    assert left.root_refs == ("binder:0",)
    assert {app.application_ref for app in left.applications} == {
        "application:0",
        "application:1",
    }


def test_grounded_role_direction_changes_expression_identity() -> None:
    alice_loves_bob = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    bob_loves_alice = SemanticExpression.create(
        applications=(
            _application("b", subject="entity:bob", object_="entity:alice"),
        ),
        root_refs=("b",),
    )

    assert alice_loves_bob.expression_ref != bob_loves_alice.expression_ref


def test_ordered_links_preserve_order_but_reviewed_commutative_links_do_not() -> None:
    applications = (
        _application("left", subject="entity:alice"),
        _application("right", subject="entity:carol"),
    )

    ordered_left = SemanticExpression.create(
        applications=applications,
        root_refs=("link",),
        expression_links=(
            ExpressionLink("link", "link:sequence", ("left", "right")),
        ),
    )
    ordered_right = SemanticExpression.create(
        applications=applications,
        root_refs=("link",),
        expression_links=(
            ExpressionLink("link", "link:sequence", ("right", "left")),
        ),
    )
    commutative_left = SemanticExpression.create(
        applications=applications,
        root_refs=("link",),
        expression_links=(
            ExpressionLink("link", "link:coordination", ("left", "right")),
        ),
    )
    commutative_right = SemanticExpression.create(
        applications=applications,
        root_refs=("link",),
        expression_links=(
            ExpressionLink("link", "link:coordination", ("right", "left")),
        ),
    )

    assert ordered_left.expression_ref != ordered_right.expression_ref
    assert commutative_left == commutative_right


def test_scope_value_literal_and_multiple_roots_are_semantic_content() -> None:
    base = SemanticExpression.create(
        applications=(
            _application("a"),
            SemanticApplication(
                "count",
                "op:state",
                "dimension:count",
                (
                    RoleBinding("role:subject", GroundedReference("entity:items")),
                    RoleBinding("role:value", LiteralValue("integer", 3)),
                ),
            ),
        ),
        root_refs=("scope", "count"),
        scope_operators=(
            ScopeOperator("scope", "scope:polarity", "value:negative", "a"),
        ),
    )
    changed = SemanticExpression.create(
        applications=(
            _application("a"),
            SemanticApplication(
                "count",
                "op:state",
                "dimension:count",
                (
                    RoleBinding("role:subject", GroundedReference("entity:items")),
                    RoleBinding("role:value", LiteralValue("integer", 4)),
                ),
            ),
        ),
        root_refs=("scope", "count"),
        scope_operators=(
            ScopeOperator("scope", "scope:polarity", "value:negative", "a"),
        ),
    )

    assert len(base.root_refs) == 2
    assert base.expression_ref != changed.expression_ref


def test_typed_unresolved_filler_is_bound_to_one_exact_role() -> None:
    expression = SemanticExpression.create(
        applications=(
            SemanticApplication(
                "a",
                "op:event",
                "event:open",
                (
                    RoleBinding("role:actor", GroundedReference("entity:alice")),
                    RoleBinding("role:affected", UnresolvedValue("missing")),
                ),
            ),
        ),
        root_refs=("a",),
        unresolved_fillers=(
            UnresolvedFiller(
                "missing",
                "a",
                "role:affected",
                "reference",
                ("entity",),
                True,
            ),
        ),
    )

    assert expression.unresolved_fillers[0].critical is True
    with pytest.raises(ValueError, match="unresolved owner/role mismatch"):
        SemanticExpression.create(
            applications=expression.applications,
            root_refs=expression.root_refs,
            unresolved_fillers=(
                replace(expression.unresolved_fillers[0], role_ref="role:actor"),
            ),
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"root_refs": ()}, "root"),
        ({"root_refs": ("missing",)}, "unknown root"),
        (
            {
                "applications": (_application("a"),),
                "root_refs": ("scope",),
                "scope_operators": (
                    ScopeOperator("scope", "scope:polarity", "value:negative", "scope"),
                ),
            },
            "root|cycle",
        ),
    ],
    ids=("no-roots", "unknown-root", "self-cycle"),
)
def test_invalid_expression_topology_is_rejected(
    kwargs: dict[str, object], message: str
) -> None:
    arguments: dict[str, object] = {
        "applications": (_application("a"),),
        "root_refs": ("a",),
    }
    arguments.update(kwargs)

    with pytest.raises(ValueError, match=message):
        SemanticExpression.create(**arguments)  # type: ignore[arg-type]


def test_shared_child_is_rejected_to_preserve_exact_forest_identity() -> None:
    with pytest.raises(ValueError, match="exactly one parent"):
        SemanticExpression.create(
            applications=(
                _application("child"),
                SemanticApplication(
                    "p1",
                    "op:event",
                    "event:know",
                    (RoleBinding("role:content", ApplicationFiller("child")),),
                ),
                SemanticApplication(
                    "p2",
                    "op:event",
                    "event:remember",
                    (RoleBinding("role:content", ApplicationFiller("child")),),
                ),
            ),
            root_refs=("p1", "p2"),
        )


def test_bounds_and_lexical_binding_fail_closed() -> None:
    with pytest.raises(ValueError, match="application|applications"):
        SemanticExpression.create(
            applications=(_application("a"),),
            root_refs=("a",),
            bounds=ExpressionBounds(max_applications=0),
        )
    with pytest.raises(ValueError, match="unbound variable"):
        SemanticExpression.create(
            applications=(
                SemanticApplication(
                    "a",
                    "op:type",
                    "concept:person",
                    (RoleBinding("role:instance", BoundVariable("?x")),),
                ),
            ),
            root_refs=("a",),
        )


def test_expression_deserialization_rejects_nested_or_container_ref_tampering() -> None:
    expression = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    payload = expression.as_dict()
    payload["expression_ref"] = "expression:tampered"
    with pytest.raises(ValueError, match="expression_ref mismatch"):
        SemanticExpression.from_dict(payload)

    payload = expression.as_dict()
    payload["applications"][0]["application_ref"] = "application:9"
    with pytest.raises(ValueError, match="unknown root|non-canonical expression encoding"):
        SemanticExpression.from_dict(payload)


def test_verified_meaning_binds_lineage_without_changing_expression_identity() -> None:
    expression = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    first = VerifiedMeaning.create(
        program_ref="program:first",
        expression=expression,
        grounding_refs=("grounding:1",),
        coverage_receipt_ref="coverage:1",
        compilation_proof_ref="proof:1",
        verification_receipt_ref="verification:1",
        revision_pin=_pin(),
    )
    second = VerifiedMeaning.create(
        program_ref="program:second",
        expression=expression,
        grounding_refs=("grounding:1",),
        coverage_receipt_ref="coverage:1",
        compilation_proof_ref="proof:2",
        verification_receipt_ref="verification:2",
        revision_pin=_pin(),
    )

    assert first.expression.expression_ref == second.expression.expression_ref
    assert first.verified_meaning_ref != second.verified_meaning_ref
    assert VerifiedMeaning.from_dict(first.as_dict()) == first



def test_canonical_containers_reject_direct_forged_construction() -> None:
    with pytest.raises(TypeError):
        SemanticExpression()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        VerifiedMeaning()  # type: ignore[call-arg]
    expression = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    with pytest.raises(TypeError):
        SemanticExpression(  # type: ignore[call-arg]
            "expression:forged", expression.applications, expression.root_refs
        )
    with pytest.raises(TypeError):
        VerifiedMeaning(  # type: ignore[call-arg]
            "verified_meaning:forged", "program:1", expression, ("grounding:1",),
            "coverage:1", "proof:1", "verification:1", _pin()
        )


@pytest.mark.parametrize("abi_version", [True, 1.0], ids=("bool", "float"))
def test_expression_deserializer_requires_exact_abi_integer(abi_version: object) -> None:
    expression = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    payload = expression.as_dict()
    payload["abi_version"] = abi_version
    with pytest.raises(ValueError, match="ABI"):
        SemanticExpression.from_dict(payload)


def test_expression_deserializer_rejects_unknown_and_missing_fields() -> None:
    expression = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    payload = expression.as_dict()
    payload["unexpected"] = "field"
    with pytest.raises(ValueError, match="fields"):
        SemanticExpression.from_dict(payload)

    payload = expression.as_dict()
    del payload["binders"]
    with pytest.raises(ValueError, match="fields"):
        SemanticExpression.from_dict(payload)


def test_unresolved_filler_requires_closed_exact_bounded_types() -> None:
    with pytest.raises(ValueError, match="contribution kind"):
        UnresolvedFiller("u", "a", "role:x", "banana", ("entity",), True)
    with pytest.raises(ValueError, match="expected kinds"):
        UnresolvedFiller("u", "a", "role:x", "reference", ("entity", "entity"), True)
    with pytest.raises(ValueError, match="expected kinds"):
        UnresolvedFiller("u", "a", "role:x", "reference", ("entity", 1), True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="critical"):
        UnresolvedFiller("u", "a", "role:x", "reference", ("entity",), 1)  # type: ignore[arg-type]


def test_expression_link_schema_enforces_reviewed_arity() -> None:
    with pytest.raises(ValueError, match="arity"):
        ExpressionLink("condition", "link:condition", ("a",))
    with pytest.raises(ValueError, match="arity"):
        ExpressionLink("coordination", "link:coordination", ("a",))


def test_expression_bounds_cannot_exceed_release_bounds() -> None:
    with pytest.raises(ValueError, match="release bound"):
        ExpressionBounds(max_applications=25)
    with pytest.raises(ValueError, match="release bound"):
        ExpressionBounds(max_depth=7)


def test_verified_meaning_rejects_nested_revision_pin_tampering() -> None:
    expression = SemanticExpression.create(
        applications=(_application("a"),), root_refs=("a",)
    )
    meaning = VerifiedMeaning.create(
        program_ref="program:1",
        expression=expression,
        grounding_refs=("grounding:1",),
        coverage_receipt_ref="coverage:1",
        compilation_proof_ref="proof:1",
        verification_receipt_ref="verification:1",
        revision_pin=_pin(),
    )
    payload = meaning.as_dict()
    payload["revision_pin"]["world_revision"] = True
    with pytest.raises((TypeError, ValueError), match="world_revision"):
        VerifiedMeaning.from_dict(payload)


def test_literal_wire_types_are_exact_and_r1_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="string literal"):
        LiteralValue("string", 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="not admitted"):
        LiteralValue("timestamp", "2026-08-03T00:00:00Z")

__cemm_test_inventory__ = {'tests/test_semantic_expressions.py::test_alpha_renaming_and_declaration_order_do_not_change_identity': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-semantic-expressions-test-alpha-renaming-and-declaration-order-do-not-change-identity',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': '6fb95b8a902c206754f6d84cdc6d53059ce9041897e19c41109991956fadc383'},
 'tests/test_semantic_expressions.py::test_bounds_and_lexical_binding_fail_closed': {'activation_phase': 'R1',
                                                                                     'assertion_ref': 'assertion:r1-semantic-expressions-test-bounds-and-lexical-binding-fail-closed',
                                                                                     'diagnostic_role': 'owner',
                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                     'owner_ref': 'program-verifier',
                                                                                     'source_ast_sha256': '3bed3c10af712041be0680889498422412baccd61414bd63de574b09aaa7b1e9'},
 'tests/test_semantic_expressions.py::test_canonical_containers_reject_direct_forged_construction': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-semantic-expressions-test-canonical-containers-reject-direct-forged-construction',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': 'c537e7d9f1184ac993205738aff36e315978c777c0f28cb624bfe1acbcc8dbb5'},
 'tests/test_semantic_expressions.py::test_expression_bounds_cannot_exceed_release_bounds': {'activation_phase': 'R1',
                                                                                             'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-bounds-cannot-exceed-release-bounds',
                                                                                             'diagnostic_role': 'owner',
                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                             'owner_ref': 'program-verifier',
                                                                                             'source_ast_sha256': '624a9f2b582ca4bfc2fa73388990116278b722409ec9cda2e036ba32ef50e0a9'},
 'tests/test_semantic_expressions.py::test_expression_deserialization_rejects_nested_or_container_ref_tampering': {'activation_phase': 'R1',
                                                                                                                   'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-deserialization-rejects-nested-or-container-ref-tampering',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                                   'owner_ref': 'program-verifier',
                                                                                                                   'source_ast_sha256': '4340abbd83e14cde6de3c35048947862709b5d95c75ddb12542ce06226a61a3e'},
 'tests/test_semantic_expressions.py::test_expression_deserializer_rejects_unknown_and_missing_fields': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-deserializer-rejects-unknown-and-missing-fields',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '5e4e5c9eeccbe0fae7d9a211eac3468fddb69c0ce4ca63e769a7f860657dd1a7'},
 'tests/test_semantic_expressions.py::test_expression_deserializer_requires_exact_abi_integer[bool]': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-deserializer-requires-exact-abi-integer-bool',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': '2cd46cc282c29bf9ed59a956cf82c7e2bdceb26082a7c3c95265b5574867369d'},
 'tests/test_semantic_expressions.py::test_expression_deserializer_requires_exact_abi_integer[float]': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-deserializer-requires-exact-abi-integer-float',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': '2cd46cc282c29bf9ed59a956cf82c7e2bdceb26082a7c3c95265b5574867369d'},
 'tests/test_semantic_expressions.py::test_expression_is_immutable_and_excludes_evidence_geometry': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-is-immutable-and-excludes-evidence-geometry',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '9799827379a8c7821b6ebf10468dad44222928fddc038a81ae1a5c60ca440270'},
 'tests/test_semantic_expressions.py::test_expression_link_schema_enforces_reviewed_arity': {'activation_phase': 'R1',
                                                                                             'assertion_ref': 'assertion:r1-semantic-expressions-test-expression-link-schema-enforces-reviewed-arity',
                                                                                             'diagnostic_role': 'owner',
                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                             'owner_ref': 'program-verifier',
                                                                                             'source_ast_sha256': 'cf1d5d647dbd6f5312e15d75b7d24f3b9a8c902d69e79e7b94ceff745cc656f8'},
 'tests/test_semantic_expressions.py::test_grounded_role_direction_changes_expression_identity': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-semantic-expressions-test-grounded-role-direction-changes-expression-identity',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '54617296c97c492da610154efe911b0fde2fd28639443841982ec11af21f4ee0'},
 'tests/test_semantic_expressions.py::test_invalid_expression_topology_is_rejected[no-roots]': {'activation_phase': 'R1',
                                                                                                'assertion_ref': 'assertion:r1-semantic-expressions-test-invalid-expression-topology-is-rejected-no-roots',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                'owner_ref': 'program-verifier',
                                                                                                'source_ast_sha256': '064b55e92008827d4375e60ebd05079f4bd35d7129beb5f45d9d2d42843b4fab'},
 'tests/test_semantic_expressions.py::test_invalid_expression_topology_is_rejected[self-cycle]': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-semantic-expressions-test-invalid-expression-topology-is-rejected-self-cycle',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                  'owner_ref': 'program-verifier',
                                                                                                  'source_ast_sha256': '064b55e92008827d4375e60ebd05079f4bd35d7129beb5f45d9d2d42843b4fab'},
 'tests/test_semantic_expressions.py::test_invalid_expression_topology_is_rejected[unknown-root]': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-semantic-expressions-test-invalid-expression-topology-is-rejected-unknown-root',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '064b55e92008827d4375e60ebd05079f4bd35d7129beb5f45d9d2d42843b4fab'},
 'tests/test_semantic_expressions.py::test_literal_wire_types_are_exact_and_r1_is_fail_closed': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-semantic-expressions-test-literal-wire-types-are-exact-and-r1-is-fail-closed',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': '94e4ffad4639ae4ce145a8753b9cc2e5f910b5a3d3b7005702d050c1b5b6380d'},
 'tests/test_semantic_expressions.py::test_ordered_links_preserve_order_but_reviewed_commutative_links_do_not': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-semantic-expressions-test-ordered-links-preserve-order-but-reviewed-commutative-links-do-not',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                 'source_ast_sha256': '1f6dcd6fd084f63ede150e8c9990a7fc60ebe9bbb2685a97a8cdc7c9ac6eac62'},
 'tests/test_semantic_expressions.py::test_scope_value_literal_and_multiple_roots_are_semantic_content': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-semantic-expressions-test-scope-value-literal-and-multiple-roots-are-semantic-content',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': '55a90942b8082c065a1a427bb59462e2da3fcaf5f46352adcc79b0519b77b211'},
 'tests/test_semantic_expressions.py::test_shared_child_is_rejected_to_preserve_exact_forest_identity': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-semantic-expressions-test-shared-child-is-rejected-to-preserve-exact-forest-identity',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '91de4e912e6e199ecb3cf64e2a8e45ab66452fe16a2e2f61fc7f44b585daab7b'},
 'tests/test_semantic_expressions.py::test_typed_unresolved_filler_is_bound_to_one_exact_role': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-semantic-expressions-test-typed-unresolved-filler-is-bound-to-one-exact-role',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': 'c2e0d56845086aaeb43107fe08eba7eadb3049478dc8ac66a857a661a63ae856'},
 'tests/test_semantic_expressions.py::test_unresolved_filler_requires_closed_exact_bounded_types': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-semantic-expressions-test-unresolved-filler-requires-closed-exact-bounded-types',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': 'c90e84f49ce6932783aab707fad30c34410f19650d7126cbc7c596eb7de63da9'},
 'tests/test_semantic_expressions.py::test_verified_meaning_binds_lineage_without_changing_expression_identity': {'activation_phase': 'R1',
                                                                                                                  'assertion_ref': 'assertion:r1-semantic-expressions-test-verified-meaning-binds-lineage-without-changing-expression-identity',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                                  'owner_ref': 'program-verifier',
                                                                                                                  'source_ast_sha256': '46a052960d041a4abc766c5aa476f8483c7845d760d054e0a4893d234908fa87'},
 'tests/test_semantic_expressions.py::test_verified_meaning_rejects_nested_revision_pin_tampering': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-semantic-expressions-test-verified-meaning-rejects-nested-revision-pin-tampering',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': 'dfa1abd855c55a6c2762615edd95d378a5106bff5f63ea17bb2b0e98e1398e92'}}
