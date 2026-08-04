"""Independent R2 expression reconstruction for verification.

This module independently reconstructs the expected SemanticExpression
from a Program ABI 2, providing a separate code path from the compiler
to verify compilation correctness.  It mirrors the compiler's logic but
is implemented independently to catch compilation errors.
"""

from __future__ import annotations

from typing import Any

from .expressions import (
    ApplicationFiller,
    ExpressionBounds,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    VariableBinder,
)
from .programs import PERSISTENT_OPERATORS

_R2_EXPRESSION_ACTIONS = frozenset(
    {
        "select_context",
        "select_mode",
        "select_designation",
        "instantiate_operator",
        "bind_role",
        "bind_reference",
        "bind_nested_application",
        "attach_scope",
        "project_variable",
        "propose_transition",
        "complete_program",
    }
)


class _ReconstructState:
    __slots__ = (
        "role_bindings", "node_map", "scopes", "links", "binders",
        "grounding", "var_counter",
    )

    def __init__(self) -> None:
        self.role_bindings: dict[str, dict[str, RoleBinding]] = {}
        self.node_map: set[str] = set()
        self.scopes: list[ScopeOperator] = []
        self.links: list[ExpressionLink] = []
        self.binders: list[VariableBinder] = []
        self.grounding: set[str] = set()
        self.var_counter: int = 0


def _find_frame(program: Any, app_ref: str, context: Any) -> Any | None:
    for a in program.actions:
        if a.action_type == "instantiate_operator" and a.arguments[0] == app_ref:
            return context.frame(a.arguments[1])
    return None


def reconstruct_expected_expression(
    program: Any, context: Any
) -> SemanticExpression | None:
    """Independently reconstruct the expected expression from a program.

    Returns None if the program contains actions outside the admitted
    R2 subset or if reconstruction is not possible.
    """
    actions = tuple(program.actions)
    if not actions or actions[-1].action_type != "complete_program":
        return None
    if any(a.action_type not in _R2_EXPRESSION_ACTIONS for a in actions):
        return None

    instantiations = tuple(
        a for a in actions if a.action_type == "instantiate_operator"
    )
    if not instantiations:
        return None

    st = _ReconstructState()

    # Collect grounding from designations
    for a in actions:
        if a.action_type != "select_designation":
            continue
        slot = context.designation(a.arguments[0])
        if slot is None:
            return None
        st.grounding.update({slot.slot_ref, slot.target_ref, slot.designation_fact_ref, *slot.provenance_refs})

    # Collect applications and derived role targets
    for a in instantiations:
        app_ref, frame_slot_ref = a.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None or frame.operator_ref not in PERSISTENT_OPERATORS:
            return None
        st.grounding.add(frame.predicate_target_ref)
        st.grounding.update(t for _, t in frame.derived_role_targets)
        st.role_bindings[app_ref] = {
            role: RoleBinding(role, GroundedReference(target))
            for role, target in frame.derived_role_targets
        }
        st.node_map.add(app_ref)

    # Collect role/reference bindings
    for a in actions:
        if a.action_type not in {"bind_role", "bind_reference"}:
            continue
        app_ref, role_ref, slot_ref = a.arguments
        if app_ref not in st.role_bindings:
            return None
        frame = _find_frame(program, app_ref, context)
        if frame is None:
            return None
        legal = set(frame.required_roles) | set(frame.optional_roles)
        if role_ref not in legal or role_ref in st.role_bindings[app_ref]:
            return None
        if a.action_type == "bind_role":
            slot = context.contribution(slot_ref)
            if slot is None or role_ref not in slot.output_ports:
                return None
            if slot.target_ref is not None:
                filler: Any = GroundedReference(slot.target_ref)
                st.grounding.add(slot.target_ref)
            elif slot.literal_value is not None:
                filler = LiteralValue("string", slot.literal_value)
            else:
                return None
            st.grounding.update(slot.provenance_refs)
        else:
            slot = context.reference(slot_ref)
            if slot is None or role_ref not in slot.compatible_roles:
                return None
            filler = GroundedReference(slot.target_ref)
            st.grounding.update({slot.target_ref, *slot.provenance_refs})
        st.role_bindings[app_ref][role_ref] = RoleBinding(role_ref, filler)

    # Collect nested role bindings (proposition roles)
    for a in actions:
        if a.action_type != "bind_nested_application" or not a.arguments or a.arguments[0] != "role":
            continue
        _, app_ref, role_ref, nested_ref = a.arguments
        if app_ref not in st.role_bindings or nested_ref not in st.node_map:
            return None
        frame = _find_frame(program, app_ref, context)
        if frame is None or role_ref not in frame.proposition_roles:
            return None
        if role_ref in st.role_bindings[app_ref]:
            return None
        st.role_bindings[app_ref][role_ref] = RoleBinding(role_ref, ApplicationFiller(nested_ref))

    # Collect scope operators
    for a in actions:
        if a.action_type != "attach_scope":
            continue
        scope_ref, slot_ref, target_ref = a.arguments
        slot = context.scope(slot_ref)
        if slot is None or target_ref not in st.node_map:
            return None
        st.scopes.append(ScopeOperator(scope_ref, slot.operator_type, slot.value_ref, target_ref))
        st.node_map.add(scope_ref)
        st.grounding.add(slot.value_ref)

    # Collect expression links
    for a in actions:
        if a.action_type != "bind_nested_application" or not a.arguments or a.arguments[0] != "link":
            continue
        _, link_ref, slot_ref, *operands = a.arguments
        slot = context.expression_link(slot_ref)
        if slot is None:
            return None
        if any(op not in st.node_map for op in operands):
            return None
        st.links.append(ExpressionLink(link_ref, slot.link_type, tuple(operands)))
        st.node_map.add(link_ref)

    # Collect variable binders
    for a in actions:
        if a.action_type != "project_variable":
            continue
        binder_ref, slot_ref, target_ref = a.arguments
        slot = context.variable(slot_ref)
        if slot is None or target_ref not in st.node_map:
            return None
        var_ref = f"?v{st.var_counter}"
        st.var_counter += 1
        st.binders.append(VariableBinder(binder_ref, var_ref, target_ref))
        st.node_map.add(binder_ref)

    # Build applications
    applications: list[SemanticApplication] = []
    for a in instantiations:
        app_ref, frame_slot_ref = a.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None:
            return None
        bindings = st.role_bindings.get(app_ref, {})
        if any(r not in bindings for r in frame.required_roles):
            return None
        prop_roles = set(frame.proposition_roles)
        roles = tuple(bindings[r] for r in sorted(bindings) if r not in prop_roles)
        if not roles:
            return None
        applications.append(SemanticApplication(app_ref, frame.operator_ref, frame.predicate_target_ref, roles))

    # Validate roots
    for root_ref in program.root_refs:
        if root_ref not in st.node_map:
            return None

    try:
        return SemanticExpression.create(
            applications=applications,
            root_refs=program.root_refs,
            scope_operators=st.scopes,
            expression_links=st.links,
            binders=st.binders,
            bounds=ExpressionBounds(),
        )
    except (ValueError, TypeError):
        return None
