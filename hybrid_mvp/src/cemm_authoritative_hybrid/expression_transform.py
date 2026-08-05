"""Pure canonical SemanticExpression transformations used by R3/R4."""
from __future__ import annotations

from .canonical import stable_ref
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionLink,
    GroundedReference,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    VariableBinder,
)


def instantiate_bindings(
    expression: SemanticExpression,
    bindings: tuple[tuple[str, str], ...],
) -> SemanticExpression:
    """Replace bound variables and eliminate resolved binder wrappers."""
    if type(expression) is not SemanticExpression:
        raise TypeError("expression must be exact SemanticExpression")
    mapping = dict(bindings)
    if len(mapping) != len(bindings):
        raise ValueError("bindings must have unique variables")
    redirect = {
        binder.binder_ref: binder.body_ref
        for binder in expression.binders
        if binder.variable_ref in mapping
    }

    def resolve(ref: str) -> str:
        seen: set[str] = set()
        while ref in redirect:
            if ref in seen:
                raise ValueError("binder redirect cycle")
            seen.add(ref)
            ref = redirect[ref]
        return ref

    def binding(row: RoleBinding) -> RoleBinding:
        filler = row.filler
        if isinstance(filler, BoundVariable) and filler.variable_ref in mapping:
            filler = GroundedReference(mapping[filler.variable_ref])
        elif isinstance(filler, ApplicationFiller):
            filler = ApplicationFiller(resolve(filler.node_ref))
        return RoleBinding(row.role_ref, filler)

    applications = tuple(
        SemanticApplication(
            app.application_ref,
            app.operator,
            app.predicate_ref,
            tuple(binding(row) for row in app.roles),
            tuple(binding(row) for row in app.qualifiers),
        )
        for app in expression.applications
    )
    scopes = tuple(
        ScopeOperator(row.scope_ref, row.operator_type, row.value_ref, resolve(row.operand_ref))
        for row in expression.scope_operators
    )
    links = tuple(
        ExpressionLink(row.link_ref, row.link_type, tuple(resolve(ref) for ref in row.operand_refs))
        for row in expression.expression_links
    )
    binders = tuple(
        VariableBinder(row.binder_ref, row.variable_ref, resolve(row.body_ref))
        for row in expression.binders
        if row.variable_ref not in mapping
    )
    roots = tuple(dict.fromkeys(resolve(ref) for ref in expression.root_refs))
    return SemanticExpression.create(
        applications=applications,
        root_refs=roots,
        scope_operators=scopes,
        expression_links=links,
        binders=binders,
        unresolved_fillers=expression.unresolved_fillers,
    )


def negate_expression(expression: SemanticExpression) -> SemanticExpression:
    """Return a canonical negative-polarity answer over every root."""
    scopes = list(expression.scope_operators)
    roots: list[str] = []
    for index, root in enumerate(expression.root_refs):
        local = stable_ref("answer_polarity", {"expression_ref": expression.expression_ref, "index": index})
        scopes.append(
            ScopeOperator(
                local,
                "scope:polarity",
                "scope_value:polarity:negative",
                root,
            )
        )
        roots.append(local)
    return SemanticExpression.create(
        applications=expression.applications,
        root_refs=tuple(roots),
        scope_operators=tuple(scopes),
        expression_links=expression.expression_links,
        binders=expression.binders,
        unresolved_fillers=expression.unresolved_fillers,
    )
