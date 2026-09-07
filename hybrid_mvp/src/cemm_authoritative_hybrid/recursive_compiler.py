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
from .literal_codec import decode_literal_slot
from .proposal_context import UnresolvedDesignationFrame


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


def _canonical_designation_frame(frame: Any) -> bool:
    if frame.operator_ref != "op:designation":
        return True
    derived = dict(frame.derived_role_targets)
    available_roles = {
        *frame.required_roles,
        *frame.optional_roles,
        *derived,
    }
    return (
        frame.predicate_kind == "label_type"
        and frame.structural_role_ref == "role:label_type"
        and frame.proposition_roles == ()
        and available_roles
        == {"role:label_type", "role:surface", "role:target"}
        and derived.get("role:label_type") == frame.predicate_target_ref
    )


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
        if not _canonical_designation_frame(frame):
            return _fail(
                "invalid_designation_frame",
                "designation frame lacks canonical label_type structure and exact roles",
                a.action_ref,
            )
        if type(frame) is UnresolvedDesignationFrame:
            literal = context.contribution(frame.literal_contribution_slot_ref)
            binder = context.contribution(frame.query_binder_slot_ref)
            if (a.source_unit_refs or frame.label_type_ref != "label:lexical"
                or frame.label_type_ref not in frame.provenance_refs
                or literal is None or literal.kind != "literal" or literal.target_ref is not None
                or literal.source_unit_refs != frame.source_unit_refs
                or binder is None or binder.kind != "binder"):
                return _fail("invalid_unresolved_designation_frame", "unbound designation source authority is not exact", a.action_ref)
            source_provenance = (frame.construction_ref, context.form_lattice_ref)
            if (literal.provenance_refs != source_provenance or binder.provenance_refs != source_provenance
                or binder.constraints != (("binder", "explicit_lexical_target_query"),)
                or len(binder.source_unit_refs) != 2):
                return _fail("unresolved_designation_source_provenance", "literal and binder require exact current construction provenance", a.action_ref)
            features = {ref: row.constraints for row in context.contribution_slots for ref in row.source_unit_refs if len(row.source_unit_refs) == 1 and row.kind in {"open_variable", "binder", "discourse"} and not any(key == "orthography" for key, _ in row.constraints)}
            queries = tuple(ref for ref, values in features.items() if ("interrogative", "content") in values and ("query", "query") in values)
            auxiliary, terminal = binder.source_unit_refs
            if (len(queries) != 1
                or ("construction_role", "lexical_query_auxiliary") not in features.get(auxiliary, ())
                or ("query", "query_auxiliary") not in features.get(auxiliary, ())
                or ("construction_role", "lexical_query_terminal") not in features.get(terminal, ())):
                return _fail("unresolved_designation_form_evidence", "query requires reviewed content, auxiliary and terminal features", a.action_ref)
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
            if type(frame) is UnresolvedDesignationFrame and (role_ref != "role:surface" or slot_ref != frame.literal_contribution_slot_ref):
                return _fail("unresolved_designation_literal_pointer", "literal must be the exact frame-owned contribution", a.action_ref)
            slot = context.contribution(slot_ref)
            if slot is None:
                return _fail("unknown_contribution_slot", "contribution pointer is not in context", a.action_ref)
            if type(frame) is UnresolvedDesignationFrame and a.source_unit_refs != slot.source_unit_refs:
                return _fail("unresolved_designation_literal_sources", "surface action must consume the exact literal", a.action_ref)
            if role_ref not in slot.output_ports:
                return _fail("contribution_role_mismatch", "contribution does not expose the selected role port", a.action_ref)
            if slot.target_ref is not None:
                filler: Any = GroundedReference(slot.target_ref)
                st.grounding.add(slot.target_ref)
            elif slot.literal_value is not None:
                literal_kind, literal_value = decode_literal_slot(slot)
                filler = LiteralValue(literal_kind, literal_value)
            else:
                return _fail("unresolved_contribution", "contribution has no resolved filler", a.action_ref)
            st.grounding.update(slot.provenance_refs)
        else:
            if type(frame) is UnresolvedDesignationFrame:
                return _fail("unresolved_designation_reference", "unbound target cannot bind a reference", a.action_ref)
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

def _node_children(program: Any) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for action in program.actions:
        if action.action_type == "bind_nested_application":
            if action.arguments[0] == "role":
                _, parent_ref, _role_ref, child_ref = action.arguments
                grouped.setdefault(parent_ref, []).append(child_ref)
            else:
                _, link_ref, _slot_ref, *operands = action.arguments
                grouped.setdefault(link_ref, []).extend(operands)
        elif action.action_type == "attach_scope":
            scope_ref, _slot_ref, operand_ref = action.arguments
            grouped.setdefault(scope_ref, []).append(operand_ref)
        elif action.action_type == "project_variable":
            binder_ref, _slot_ref, body_ref = action.arguments
            grouped.setdefault(binder_ref, []).append(body_ref)
    return {key: tuple(value) for key, value in grouped.items()}


def _reachable_nodes(program: Any, body_ref: str) -> tuple[str, ...]:
    children = _node_children(program)
    result: list[str] = []
    stack = [body_ref]
    seen: set[str] = set()
    while stack:
        ref = stack.pop()
        if ref in seen:
            continue
        seen.add(ref)
        result.append(ref)
        stack.extend(reversed(children.get(ref, ())))
    return tuple(result)


def _resolve_variable_application(
    program: Any,
    context: Any,
    st: _State,
    body_ref: str,
    slot: Any,
) -> str | None:
    frame_by_application = {
        action.arguments[0]: action.arguments[1]
        for action in program.actions
        if action.action_type == "instantiate_operator"
    }
    matches = tuple(
        ref
        for ref in _reachable_nodes(program, body_ref)
        if frame_by_application.get(ref) == slot.application_frame_ref
        and slot.role_ref not in st.role_bindings.get(ref, {})
    )
    return matches[0] if len(matches) == 1 else None

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
        owner_ref = _resolve_variable_application(
            program, context, st, target_ref, slot
        )
        if owner_ref is None:
            return _fail(
                "variable_owner_ambiguous",
                "variable body does not contain exactly one unbound licensed role",
                a.action_ref,
            )
        role_ref = slot.role_ref
        frame = context.frame(slot.application_frame_ref)
        if type(frame) is UnresolvedDesignationFrame:
            binder = context.contribution(frame.query_binder_slot_ref)
            qualifying_queries = tuple(
                row
                for row in context.contribution_slots
                if row.kind == "open_variable"
                and len(row.source_unit_refs) == 1
                and ("query", "query") in row.constraints
                and ("interrogative", "content") in row.constraints
            )
            interrogative_sources = (
                set(slot.source_unit_refs) - set(binder.source_unit_refs)
                if binder is not None
                else set()
            )
            if (role_ref != "role:target" or slot.construction_ref != frame.construction_ref
                or binder is None or not set(binder.source_unit_refs) < set(slot.source_unit_refs)
                or len(qualifying_queries) != 1
                or set(qualifying_queries[0].source_unit_refs) != interrogative_sources
                or a.source_unit_refs != slot.source_unit_refs):
                return _fail("unresolved_designation_variable_sources", "query must consume its own binder and interrogative", a.action_ref)
            assignments = {row.source_unit_ref: row for row in program.source_assignments}
            if any(ref not in assignments or assignments[ref].contribution_slot_ref != binder.slot_ref for ref in binder.source_unit_refs):
                return _fail("unresolved_designation_binder_pointer", "query source assignment does not bind its own binder", a.action_ref)
            query = qualifying_queries[0]
            query_source = query.source_unit_refs[0]
            if (query_source not in assignments
                or assignments[query_source].contribution_slot_ref != query.slot_ref):
                return _fail("unresolved_designation_interrogative_pointer", "query source assignment does not bind its exact content-interrogative evidence", a.action_ref)
        st.role_bindings[owner_ref][role_ref] = RoleBinding(
            role_ref, BoundVariable(var_ref)
        )
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
    except ValueError as exc:
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
