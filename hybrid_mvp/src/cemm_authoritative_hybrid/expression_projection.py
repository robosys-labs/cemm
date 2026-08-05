"""Read-only structural projection over Semantic Expression ABI 1.

The projection validates and indexes canonical expression structure for R3
owners.  It never inspects source text, construction programs, or internal ref
spelling to infer semantic kind.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    UnresolvedValue,
    VariableBinder,
)

__all__ = ["ExpressionProjection", "project_expression"]


def _children(node: object) -> tuple[str, ...]:
    if type(node) is SemanticApplication:
        refs: list[str] = []
        for binding in (*node.roles, *node.qualifiers):
            if type(binding.filler) is ApplicationFiller:
                refs.append(binding.filler.node_ref)
        return tuple(refs)
    if type(node) is ScopeOperator:
        return (node.operand_ref,)
    if type(node) is ExpressionLink:
        return node.operand_refs
    if type(node) is VariableBinder:
        return (node.body_ref,)
    raise TypeError("unknown canonical expression node")


@dataclass(frozen=True)
class ExpressionProjection:
    """Validated immutable indexes for one canonical expression."""

    expression_ref: str
    root_refs: tuple[str, ...]
    node_by_ref: Mapping[str, object]
    applications: tuple[SemanticApplication, ...]
    applications_by_operator: Mapping[str, tuple[SemanticApplication, ...]]
    applications_by_predicate: Mapping[str, tuple[SemanticApplication, ...]]
    scopes_by_type: Mapping[str, tuple[ScopeOperator, ...]]
    links_by_type: Mapping[str, tuple[ExpressionLink, ...]]
    binders_by_variable: Mapping[str, VariableBinder]
    grounded_refs: tuple[str, ...]
    literal_values: tuple[LiteralValue, ...]
    unresolved_refs: tuple[str, ...]
    bound_variable_refs: tuple[str, ...]

    def root_nodes(self) -> tuple[object, ...]:
        return tuple(self.node_by_ref[ref] for ref in self.root_refs)

    def root_applications(self) -> tuple[SemanticApplication, ...]:
        return tuple(
            node for node in self.root_nodes() if type(node) is SemanticApplication
        )

    def state_applications(self) -> tuple[SemanticApplication, ...]:
        return self.applications_by_operator.get("op:state", ())

    def event_applications(self) -> tuple[SemanticApplication, ...]:
        return self.applications_by_operator.get("op:event", ())

    def relation_applications(self) -> tuple[SemanticApplication, ...]:
        return self.applications_by_operator.get("op:relation", ())

    def designation_applications(self) -> tuple[SemanticApplication, ...]:
        return self.applications_by_operator.get("op:designation", ())

    def application(self, application_ref: str) -> SemanticApplication | None:
        node = self.node_by_ref.get(application_ref)
        return node if type(node) is SemanticApplication else None

    def descendant_applications(self, node_ref: str) -> tuple[SemanticApplication, ...]:
        if node_ref not in self.node_by_ref:
            return ()
        selected: list[SemanticApplication] = []
        stack = [node_ref]
        seen: set[str] = set()
        while stack:
            ref = stack.pop()
            if ref in seen:
                continue
            seen.add(ref)
            node = self.node_by_ref[ref]
            if type(node) is SemanticApplication:
                selected.append(node)
            stack.extend(reversed(_children(node)))
        return tuple(selected)

    def role_bindings(
        self,
        application_ref: str,
        role_ref: str,
    ) -> tuple[RoleBinding, ...]:
        app = self.application(application_ref)
        if app is None:
            return ()
        return tuple(
            binding
            for binding in (*app.roles, *app.qualifiers)
            if binding.role_ref == role_ref
        )


def _group_applications(
    applications: tuple[SemanticApplication, ...],
    field: str,
) -> Mapping[str, tuple[SemanticApplication, ...]]:
    grouped: dict[str, list[SemanticApplication]] = {}
    for app in applications:
        grouped.setdefault(getattr(app, field), []).append(app)
    return MappingProxyType(
        {key: tuple(rows) for key, rows in sorted(grouped.items())}
    )


def _group_nodes(
    rows: tuple[Any, ...],
    field: str,
) -> Mapping[str, tuple[Any, ...]]:
    grouped: dict[str, list[Any]] = {}
    for row in rows:
        grouped.setdefault(getattr(row, field), []).append(row)
    return MappingProxyType(
        {key: tuple(values) for key, values in sorted(grouped.items())}
    )


def project_expression(expression: SemanticExpression) -> ExpressionProjection:
    """Authenticate, validate and index one exact SemanticExpression."""

    if type(expression) is not SemanticExpression:
        raise TypeError("expression must be exact SemanticExpression")
    canonical = SemanticExpression.from_dict(expression.as_dict())
    if canonical != expression:
        raise ValueError("expression is non-canonical")

    nodes: list[object] = [
        *expression.applications,
        *expression.scope_operators,
        *expression.expression_links,
        *expression.binders,
    ]
    refs: list[str] = []
    for node in nodes:
        if type(node) is SemanticApplication:
            refs.append(node.application_ref)
        elif type(node) is ScopeOperator:
            refs.append(node.scope_ref)
        elif type(node) is ExpressionLink:
            refs.append(node.link_ref)
        elif type(node) is VariableBinder:
            refs.append(node.binder_ref)
        else:
            raise TypeError("expression contains a non-canonical node")
    if len(refs) != len(set(refs)):
        raise ValueError("expression contains duplicate node refs")
    node_by_ref = dict(zip(refs, nodes, strict=True))

    if not expression.root_refs:
        raise ValueError("expression requires roots")
    unknown_roots = set(expression.root_refs) - set(node_by_ref)
    if unknown_roots:
        raise ValueError(f"expression has unknown roots: {sorted(unknown_roots)}")

    for node in nodes:
        unknown = set(_children(node)) - set(node_by_ref)
        if unknown:
            raise ValueError(
                f"expression node references unknown children: {sorted(unknown)}"
            )

    state: dict[str, int] = {}
    reachable: set[str] = set()

    def visit(ref: str) -> None:
        mark = state.get(ref, 0)
        if mark == 1:
            raise ValueError("expression graph contains a cycle")
        if mark == 2:
            reachable.add(ref)
            return
        state[ref] = 1
        for child in _children(node_by_ref[ref]):
            visit(child)
        state[ref] = 2
        reachable.add(ref)

    for root in expression.root_refs:
        visit(root)
    unreachable = set(node_by_ref) - reachable
    if unreachable:
        raise ValueError(
            f"expression contains unreachable nodes: {sorted(unreachable)}"
        )

    binder_by_variable: dict[str, VariableBinder] = {}
    for binder in expression.binders:
        if binder.variable_ref in binder_by_variable:
            raise ValueError("expression contains duplicate variable binders")
        binder_by_variable[binder.variable_ref] = binder

    grounded: list[str] = []
    literals: list[LiteralValue] = []
    unresolved: list[str] = []
    variables: list[str] = []
    for app in expression.applications:
        for binding in (*app.roles, *app.qualifiers):
            filler = binding.filler
            if type(filler) is GroundedReference:
                grounded.append(filler.target_ref)
            elif type(filler) is LiteralValue:
                literals.append(filler)
            elif type(filler) is UnresolvedValue:
                unresolved.append(filler.unresolved_ref)
            elif type(filler) is BoundVariable:
                variables.append(filler.variable_ref)
                if filler.variable_ref not in binder_by_variable:
                    raise ValueError("bound variable has no canonical binder")
            elif type(filler) is ApplicationFiller:
                continue
            else:
                raise TypeError("application contains a non-canonical filler")

    unresolved.extend(item.unresolved_ref for item in expression.unresolved_fillers)
    return ExpressionProjection(
        expression_ref=expression.expression_ref,
        root_refs=expression.root_refs,
        node_by_ref=MappingProxyType(node_by_ref),
        applications=expression.applications,
        applications_by_operator=_group_applications(
            expression.applications, "operator"
        ),
        applications_by_predicate=_group_applications(
            expression.applications, "predicate_ref"
        ),
        scopes_by_type=_group_nodes(
            expression.scope_operators, "operator_type"
        ),
        links_by_type=_group_nodes(expression.expression_links, "link_type"),
        binders_by_variable=MappingProxyType(binder_by_variable),
        grounded_refs=tuple(sorted(set(grounded))),
        literal_values=tuple(literals),
        unresolved_refs=tuple(sorted(set(unresolved))),
        bound_variable_refs=tuple(sorted(set(variables))),
    )
