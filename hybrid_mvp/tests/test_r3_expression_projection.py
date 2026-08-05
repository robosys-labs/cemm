from __future__ import annotations

from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)

__cemm_test_inventory__ = {
    "tests/test_r3_expression_projection.py::test_projection_indexes_roles_without_ref_spelling_dispatch": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-projection-indexes-roles-without-ref-spelling-dispatch",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "644b23a8f8cf15182943494d78487e1282e15dd86064a6202c20ac1aae9e2e37"
    },
    "tests/test_r3_expression_projection.py::test_projection_validates_recursive_expression": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-projection-validates-recursive-expression",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e4e93a1d4760da5703140e9c7a6189ad0fe339f9e9dff55310f5d0b199c9b252"
    }
}



def _expression() -> SemanticExpression:
    leave = SemanticApplication(
        application_ref="application:leave",
        operator="op:event",
        predicate_ref="event:leave",
        roles=(
            RoleBinding(
                "role:actor",
                GroundedReference("entity:bob"),
            ),
        ),
    )
    say = SemanticApplication(
        application_ref="application:say",
        operator="op:event",
        predicate_ref="event:say",
        roles=(
            RoleBinding(
                "role:actor",
                GroundedReference("entity:alice"),
            ),
            RoleBinding(
                "role:content",
                ApplicationFiller("application:leave"),
            ),
        ),
    )
    return SemanticExpression.create(
        applications=(say, leave),
        root_refs=("application:say",),
    )


def test_projection_validates_recursive_expression() -> None:
    expression = _expression()
    projection = project_expression(expression)
    assert projection.expression_ref == expression.expression_ref
    assert len(projection.event_applications()) == 2
    assert set(projection.grounded_refs) == {"entity:alice", "entity:bob"}
    assert len(projection.root_applications()) == 1
    assert projection.root_applications()[0].predicate_ref == "event:say"


def test_projection_indexes_roles_without_ref_spelling_dispatch() -> None:
    expression = _expression()
    projection = project_expression(expression)
    say = next(
        app for app in projection.applications if app.predicate_ref == "event:say"
    )
    content = projection.role_bindings(say.application_ref, "role:content")
    assert len(content) == 1
    assert type(content[0].filler) is ApplicationFiller
