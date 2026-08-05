"""R2 recursive Semantic Expression compiler.

Lowers every admitted R2 Program ABI 2 action into a canonical
SemanticExpression forest.  Supports multiple applications, proposition
role nesting, expression links, scope operators, variable binders and
transition hints.
"""

from __future__ import annotations

from typing import Any

from .expressions import (
    ApplicationFiller,
    BoundVariable,
    CompilationFailure,
    CompilationProof,
    CompilationSuccess,
    ExpressionLink,
    ExpressionBounds,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    TranslationRow,
    UnresolvedFiller,
    VariableBinder,
)
from .programs import PERSISTENT_OPERATORS


class _State:
    """Mutable accumulator for the recursive compilation pass."""
    __slots__ = (
        "role_bindings", "node_map", "action_targets", "grounding",
        "scopes", "links", "binders", "unresolved", "var_counter",
    )

    def __init__(self) -> None:
        self.role_bindings: dict[str, dict[str, RoleBinding]] = {}
        self.node_map: dict[str, str] = {}
        self.action_targets: dict[str, tuple[str, ...]] = {}
        self.grounding: set[str] = set()
        self.scopes: list[ScopeOperator] = []
        self.links: list[ExpressionLink] = []
        self.binders: list[VariableBinder] = []
        self.unresolved: list[UnresolvedFiller] = []
        self.var_counter: int = 0


def _fail(code: str, detail: str, ref: str | None = None) -> CompilationFailure:
    return CompilationFailure(code, detail, ref)


def _find_frame(program: Any, app_ref: str, context: Any) -> Any | None:
    for a in program.actions:
        if a.action_type == "instantiate_operator" and a.arguments[0] == app_ref:
            return context.frame(a.arguments[1])
    return None


def _node_kind(ref: str) -> str:
    if ref.startswith("scope:"):
        return "scope"
    if ref.startswith("link:"):
        return "link"
    if ref.startswith("variable:"):
        return "binder"
    return "application"


def _build_ref_map(
    expression: SemanticExpression,
    applications: list[SemanticApplication],
    scopes: list[ScopeOperator],
    links: list[ExpressionLink],
    binders: list[VariableBinder],
) -> dict[str, str]:
    """Build a mapping from local refs to canonical expression refs.

    The canonicalization renames all refs.  We match nodes by their
    semantic content (operator+predicate for applications, operator_type
    for scopes, link_type for links, variable for binders).
    """
    ref_map: dict[str, str] = {}

    # Match applications by (operator, predicate_ref) in order of appearance.
    used_canonical: set[str] = set()
    for local_app in applications:
        for canon_app in expression.applications:
            if canon_app.application_ref in used_canonical:
                continue
            if (
                local_app.operator == canon_app.operator
                and local_app.predicate_ref == canon_app.predicate_ref
            ):
                ref_map[local_app.application_ref] = canon_app.application_ref
                used_canonical.add(canon_app.application_ref)
                break

    # Match scopes by operator_type
    used_scopes: set[str] = set()
    for local_scope in scopes:
        for canon_scope in expression.scope_operators:
            if canon_scope.scope_ref in used_scopes:
                continue
            if local_scope.operator_type == canon_scope.operator_type:
                ref_map[local_scope.scope_ref] = canon_scope.scope_ref
                used_scopes.add(canon_scope.scope_ref)
                break

    # Match links by link_type
    used_links: set[str] = set()
    for local_link in links:
        for canon_link in expression.expression_links:
            if canon_link.link_ref in used_links:
                continue
            if local_link.link_type == canon_link.link_type:
                ref_map[local_link.link_ref] = canon_link.link_ref
                used_links.add(canon_link.link_ref)
                break

    # Match binders by variable_ref
    used_binders: set[str] = set()
    for local_binder in binders:
        for canon_binder in expression.binders:
            if canon_binder.binder_ref in used_binders:
                continue
            ref_map[local_binder.binder_ref] = canon_binder.binder_ref
            used_binders.add(canon_binder.binder_ref)
            break

    return ref_map


def _canonical_ref(ref_map: dict[str, str], local_ref: str) -> str:
    """Map a local ref to its canonical expression ref."""
    return ref_map.get(local_ref, local_ref)


def _collect_designations(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type != "select_designation":
            continue
        slot = context.designation(a.arguments[0])
        if slot is None:
            return _fail("unknown_designation_slot", "designation pointer is not in context", a.action_ref)
        st.grounding.update({slot.slot_ref, slot.target_ref, slot.designation_fact_ref, *slot.provenance_refs})
    return None


def _collect_applications(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type != "instantiate_operator":
            continue
        app_ref, frame_slot_ref = a.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None:
            return _fail("unknown_application_frame", "frame pointer is not in context", a.action_ref)
        if frame.operator_ref not in PERSISTENT_OPERATORS:
            return _fail("invalid_operator", "frame does not lower to a kernel operator", a.action_ref)
        st.grounding.add(frame.predicate_target_ref)
        st.grounding.update(t for _, t in frame.derived_role_targets)
        st.role_bindings[app_ref] = {
            role: RoleBinding(role, GroundedReference(target))
            for role, target in frame.derived_role_targets
        }
        st.node_map[app_ref] = app_ref
        st.action_targets[a.action_ref] = (app_ref,)
    return None


def _collect_role_bindings(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type not in {"bind_role", "bind_reference"}:
            continue
        app_ref, role_ref, slot_ref = a.arguments
        if app_ref not in st.role_bindings:
            return _fail("unknown_application_ref", "binding targets an unknown application", a.action_ref)
        frame = _find_frame(program, app_ref, context)
        if frame is None:
            return _fail("unknown_application_ref", "application has no frame", a.action_ref)
        if role_ref in st.role_bindings[app_ref]:
            return _fail("duplicate_role_binding", "application role was bound twice", a.action_ref)
        all_roles = set(frame.required_roles) | set(frame.optional_roles)
        if role_ref not in all_roles:
            return _fail("frame_role_mismatch", "role is not licensed by the application frame", a.action_ref)
        if a.action_type == "bind_role":
            slot = context.contribution(slot_ref)
            if slot is None:
                return _fail("unknown_contribution_slot", "contribution pointer is not in context", a.action_ref)
            if role_ref not in slot.output_ports:
                return _fail("contribution_role_mismatch", "contribution does not expose the selected role port", a.action_ref)
            if slot.target_ref is not None:
                filler: Any = GroundedReference(slot.target_ref)
                st.grounding.add(slot.target_ref)
            elif slot.literal_value is not None:
                literal_kind = next(
                    (value for key, value in slot.constraints if key == "literal_kind"),
                    "string",
                )
                filler = LiteralValue(literal_kind, slot.literal_value)
            else:
                return _fail("unresolved_contribution", "contribution has no resolved filler", a.action_ref)
            st.grounding.update(slot.provenance_refs)
        else:
            slot = context.reference(slot_ref)
            if slot is None:
                return _fail("unknown_reference_slot", "reference pointer is not in context", a.action_ref)
            if role_ref not in slot.compatible_roles:
                return _fail("reference_role_mismatch", "reference slot is incompatible with the selected role", a.action_ref)
            filler = GroundedReference(slot.target_ref)
            st.grounding.update({slot.target_ref, *slot.provenance_refs})
        st.role_bindings[app_ref][role_ref] = RoleBinding(role_ref, filler)
        st.action_targets[a.action_ref] = (app_ref, role_ref)
    return None


def _collect_nested_roles(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type != "bind_nested_application" or not a.arguments or a.arguments[0] != "role":
            continue
        _, app_ref, role_ref, nested_ref = a.arguments
        if app_ref not in st.role_bindings:
            return _fail("unknown_application_ref", "nested binding targets an unknown application", a.action_ref)
        frame = _find_frame(program, app_ref, context)
        if frame is None or role_ref not in frame.proposition_roles:
            return _fail("frame_role_mismatch", "role is not a proposition-valued frame role", a.action_ref)
        if role_ref in st.role_bindings[app_ref]:
            return _fail("duplicate_role_binding", "application role was bound twice", a.action_ref)
        if nested_ref not in st.node_map:
            return _fail("unknown_application_ref", "nested application is not instantiated", a.action_ref)
        st.role_bindings[app_ref][role_ref] = RoleBinding(role_ref, ApplicationFiller(nested_ref))
        st.action_targets[a.action_ref] = (app_ref, role_ref)
    return None


def _collect_scopes(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type != "attach_scope":
            continue
        scope_ref, slot_ref, target_ref = a.arguments
        slot = context.scope(slot_ref)
        if slot is None:
            return _fail("unknown_scope_slot", "scope pointer is not in context", a.action_ref)
        if target_ref not in st.node_map:
            return _fail("unknown_scope_target", "scope target is not a known node", a.action_ref)
        st.scopes.append(ScopeOperator(scope_ref, slot.operator_type, slot.value_ref, target_ref))
        st.node_map[scope_ref] = scope_ref
        st.grounding.add(slot.value_ref)
        st.action_targets[a.action_ref] = (scope_ref,)
    return None


def _collect_links(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type != "bind_nested_application" or not a.arguments or a.arguments[0] != "link":
            continue
        _, link_ref, slot_ref, *operands = a.arguments
        slot = context.expression_link(slot_ref)
        if slot is None:
            return _fail("unknown_link_slot", "expression link pointer is not in context", a.action_ref)
        for op in operands:
            if op not in st.node_map:
                return _fail("unknown_link_operand", "expression link operand is not a known node", a.action_ref)
        st.links.append(ExpressionLink(link_ref, slot.link_type, tuple(operands)))
        st.node_map[link_ref] = link_ref
        st.action_targets[a.action_ref] = (link_ref,)
    return None


def _collect_binders(program: Any, context: Any, st: _State) -> CompilationFailure | None:
    for a in program.actions:
        if a.action_type != "project_variable":
            continue
        binder_ref, slot_ref, target_ref = a.arguments
        slot = context.variable(slot_ref)
        if slot is None:
            return _fail("unknown_variable_slot", "variable pointer is not in context", a.action_ref)
        if target_ref not in st.node_map:
            return _fail("unknown_variable_target", "variable target is not a known node", a.action_ref)
        var_ref = f"?v{st.var_counter}"
        st.var_counter += 1
        st.binders.append(VariableBinder(binder_ref, var_ref, target_ref))
        st.node_map[binder_ref] = binder_ref
        st.action_targets[a.action_ref] = (binder_ref,)
        # Fill the target application's role with a BoundVariable so the
        # variable actually occurs in the semantic expression.
        role_ref = getattr(slot, "role_ref", None)
        if role_ref is not None:
            if target_ref in st.role_bindings and role_ref in st.role_bindings[target_ref]:
                return _fail("duplicate_role_binding", "variable target role is already bound", a.action_ref)
            if target_ref not in st.role_bindings:
                st.role_bindings[target_ref] = {}
            st.role_bindings[target_ref][role_ref] = RoleBinding(role_ref, BoundVariable(var_ref))
    return None


def _build_applications(
    program: Any, context: Any, st: _State
) -> list[SemanticApplication] | CompilationFailure:
    applications: list[SemanticApplication] = []
    for a in program.actions:
        if a.action_type != "instantiate_operator":
            continue
        app_ref, frame_slot_ref = a.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None:
            return _fail("unknown_application_frame", "frame pointer is not in context", a.action_ref)
        bindings = st.role_bindings.get(app_ref, {})
        missing = tuple(r for r in frame.required_roles if r not in bindings)
        if missing:
            return _fail("missing_required_role", f"missing required roles: {', '.join(missing)}", a.action_ref)
        prop_roles = set(frame.proposition_roles)
        # Include ALL role bindings (derived + bind_role + bind_reference +
        # nested proposition roles) in roles.  Proposition-valued roles
        # carry ApplicationFiller fillers and must be preserved.
        roles = tuple(bindings[r] for r in sorted(bindings))
        if not roles:
            return _fail("missing_required_role", "application has no bound roles", a.action_ref)
        applications.append(SemanticApplication(app_ref, frame.operator_ref, frame.predicate_target_ref, roles))
    return applications


def compile_recursive(
    program: Any, context: Any
) -> CompilationSuccess | CompilationFailure:
    """Compile an R2 Program ABI 2 into a canonical SemanticExpression."""
    if program.proposal_context_ref != context.context_ref:
        return _fail("proposal_context_mismatch", "program does not bind the supplied proposal context")
    if program.orientation_ref != context.orientation_ref:
        return _fail("orientation_mismatch", "program and context orientation differ")
    if program.revision_pin != context.revision_pin:
        return _fail("revision_mismatch", "program and context revision pins differ")
    if context.mode_slot(program.mode_slot_ref) is None:
        return _fail("unknown_mode_slot", "mode slot is not in context")
    if program.actions[-1].action_type == "abstain":
        return _fail("abstain_program", "abstention has no semantic expression")
    if sum(1 for a in program.actions if a.action_type == "instantiate_operator") < 1:
        return _fail("action_shape_not_admitted", "program requires at least one application")

    st = _State()
    for pass_fn in (
        _collect_designations, _collect_applications, _collect_role_bindings,
        _collect_nested_roles, _collect_scopes, _collect_links, _collect_binders,
    ):
        err = pass_fn(program, context, st)
        if err is not None:
            return err

    applications = _build_applications(program, context, st)
    if isinstance(applications, CompilationFailure):
        return applications

    for root_ref in program.root_refs:
        if root_ref not in st.node_map:
            return _fail("action_shape_not_admitted", f"root ref {root_ref} is not a known node")

    try:
        expression = SemanticExpression.create(
            applications=applications,
            root_refs=program.root_refs,
            scope_operators=st.scopes,
            expression_links=st.links,
            binders=st.binders,
            unresolved_fillers=st.unresolved,
            bounds=ExpressionBounds(),
        )
    except (ValueError, TypeError) as exc:
        return _fail("expression_construction_error", str(exc))

    # Build mapping from local refs to canonical expression refs
    ref_map = _build_ref_map(expression, applications, st.scopes, st.links, st.binders)

    action_rows: list[TranslationRow] = []
    for a in program.actions:
        if a.action_type == "select_context":
            disposition, targets = "validated", (context.context_ref,)
        elif a.action_type == "select_mode":
            disposition, targets = "validated", (program.mode_slot_ref,)
        elif a.action_type == "select_designation":
            disposition, targets = "validated", (a.arguments[0],)
        elif a.action_type == "instantiate_operator":
            app_ref = a.arguments[0]
            disposition, targets = "translated", (_canonical_ref(ref_map, app_ref),)
        elif a.action_type in {"bind_role", "bind_reference"}:
            raw = st.action_targets.get(a.action_ref, ())
            targets = tuple(_canonical_ref(ref_map, t) for t in raw)
            disposition = "translated"
        elif a.action_type == "bind_nested_application":
            raw = st.action_targets.get(a.action_ref, ())
            targets = tuple(_canonical_ref(ref_map, t) for t in raw)
            disposition = "translated"
        elif a.action_type == "attach_scope":
            raw = st.action_targets.get(a.action_ref, ())
            targets = tuple(_canonical_ref(ref_map, t) for t in raw)
            disposition = "translated"
        elif a.action_type == "project_variable":
            raw = st.action_targets.get(a.action_ref, ())
            targets = tuple(_canonical_ref(ref_map, t) for t in raw)
            disposition = "translated"
        elif a.action_type == "propose_transition":
            disposition, targets = "validated", a.arguments
        elif a.action_type == "complete_program":
            disposition, targets = "translated", (expression.expression_ref,)
        else:
            disposition, targets = "validated", ()
        action_rows.append(TranslationRow(a.action_ref, disposition, targets))

    assignment_rows = tuple(
        TranslationRow(
            asg.assignment_ref,
            "retained" if asg.assignment_kind == "residual" else "translated",
            tuple(t for t in (asg.target_action_ref or asg.contribution_slot_ref, asg.target_role_ref) if t is not None),
        )
        for asg in program.source_assignments
    )

    # Root translations: map program root refs to canonical expression root refs.
    # The canonicalization may reorder roots by semantic content, so we need
    # to use the ref_map to find the correct canonical ref for each program root.
    root_rows = tuple(
        TranslationRow(root_ref, "translated", (_canonical_ref(ref_map, root_ref),))
        for root_ref in program.root_refs
    )

    proof = CompilationProof.create(
        program_ref=program.program_ref,
        proposal_context_ref=context.context_ref,
        expression_ref=expression.expression_ref,
        action_translations=action_rows,
        assignment_translations=assignment_rows,
        root_translations=root_rows,
        grounding_refs=st.grounding,
        revision_pin=program.revision_pin,
    )
    return CompilationSuccess(expression, proof)
