"""Independent structural-semantic oracle for the foundation.

These tests compare independently constructed graph meanings, not generated
surface phrases or self-generated proposal labels.
"""
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, RoleBinding, SemanticApplication,
    SemanticExpression, ExpressionLink, ScopeOperator,
)


def app(local, subject, obj):
    return SemanticApplication(
        local, "op:relation", "rel:owns",
        (
            RoleBinding("role:subject", GroundedReference(subject)),
            RoleBinding("role:object", GroundedReference(obj)),
        ),
    )


def test_alpha_renaming_of_local_application_ids_preserves_semantics():
    a = app("application:one", "entity:ada", "entity:car")
    b = app("application:another", "entity:ada", "entity:car")
    x = SemanticExpression.create(applications=(a,), root_refs=(a.application_ref,))
    y = SemanticExpression.create(applications=(b,), root_refs=(b.application_ref,))
    assert x.expression_ref == y.expression_ref


def test_commutative_conjunction_but_not_directional_condition():
    a = app("application:a", "entity:ada", "entity:car")
    b = app("application:b", "entity:bob", "entity:bicycle")

    def joined(link_kind, operands):
        return SemanticExpression.create(
            applications=(a, b),
            expression_links=(ExpressionLink("link:root", link_kind, operands),),
            root_refs=("link:root",),
        )

    assert joined("link:conjunction", ("application:a", "application:b")).expression_ref == (
        joined("link:conjunction", ("application:b", "application:a")).expression_ref
    )
    assert joined("link:condition", ("application:a", "application:b")).expression_ref != (
        joined("link:condition", ("application:b", "application:a")).expression_ref
    )


def test_attribution_scope_is_distinct_from_world_assertion():
    a = app("application:one", "entity:ada", "entity:car")
    world = SemanticExpression.create(applications=(a,), root_refs=(a.application_ref,))
    attributed = SemanticExpression.create(
        applications=(a,),
        scope_operators=(ScopeOperator(
            "scope:report", "scope:attribution", "participant:mary", a.application_ref
        ),),
        root_refs=("scope:report",),
    )
    assert world.expression_ref != attributed.expression_ref


def test_negation_scope_does_not_reduce_to_independent_child_negations():
    a = app("application:a", "entity:ada", "entity:car")
    b = app("application:b", "entity:bob", "entity:bicycle")
    conjunction = ExpressionLink(
        "link:and", "link:conjunction", ("application:a", "application:b")
    )
    not_both = SemanticExpression.create(
        applications=(a, b),
        expression_links=(conjunction,),
        scope_operators=(ScopeOperator(
            "scope:negation", "scope:polarity", "scope_value:polarity:negative", "link:and"
        ),),
        root_refs=("scope:negation",),
    )
    a_negative = ScopeOperator(
        "scope:a", "scope:polarity", "scope_value:polarity:negative", "application:a"
    )
    b_negative = ScopeOperator(
        "scope:b", "scope:polarity", "scope_value:polarity:negative", "application:b"
    )
    both_negative = SemanticExpression.create(
        applications=(a, b),
        expression_links=(ExpressionLink(
            "link:and", "link:conjunction", ("scope:a", "scope:b")
        ),),
        scope_operators=(a_negative, b_negative),
        root_refs=("link:and",),
    )
    assert not_both.expression_ref != both_negative.expression_ref
