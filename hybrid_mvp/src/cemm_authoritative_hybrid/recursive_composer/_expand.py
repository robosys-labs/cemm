"""Context-local bounded action expansion for recursive composition."""

from __future__ import annotations

from itertools import combinations, islice, permutations
from typing import Any, Iterable, Iterator

from ..programs import ProgramAction
from ..proposal_context import UnresolvedDesignationFrame
from ._core import (
    _Choice,
    _CRITICAL_KINDS,
    _LINK_KINDS,
    _ROLE_KINDS,
    _State,
    _SourceUse,
    _TRANSITION_KINDS,
    _VARIABLE_KINDS,
    _bound_role_set,
    _next_node_ref,
    _predicate_bundles,
    _predicate_source_refs,
    _roots,
    _support_bundles,
    _subtree_nodes,
    _used_sources,
    _variable_owner,
)


def _typed_report_regions(context: Any) -> tuple[tuple[str, int, int, int], ...]:
    """Return exact typed report geometry once per composer search."""
    report_sources = tuple(
        row.source_unit_refs
        for row in context.contribution_slots
        if row.kind == "discourse"
        and ("discourse", "report") in row.constraints
        and row.source_unit_refs
    )
    sentence_boundaries = tuple(
        context.source_span(row.source_unit_refs)
        for row in context.contribution_slots
        if row.kind == "discourse"
        and row.constraints == (("orthography", "sentence_boundary"),)
    )
    regions: list[tuple[str, int, int, int]] = []
    for source_refs in report_sources:
        report_span = context.source_span(source_refs)
        if report_span is None:
            continue
        content_end = min(
            (
                span[0]
                for span in sentence_boundaries
                if span is not None and span[0] >= report_span[1]
            ),
            default=max(end for _, _, end in context.source_unit_spans),
        )
        for frame in context.application_frames:
            frame_span = context.source_span(frame.source_unit_refs)
            if (
                "role:content" in frame.proposition_roles
                and "role:actor" in frame.required_roles
                and frame_span is not None
                and report_span[0] <= frame_span[0]
                and frame_span[1] <= report_span[1]
            ):
                regions.append(
                    (frame.slot_ref, report_span[0], report_span[1], content_end)
                )
    return tuple(regions)


def _reported_child_is_local(
    owner: Any,
    state: _State,
    parent_frame_ref: str,
    child_ref: str,
) -> bool:
    matching = tuple(
        row for row in owner._reported_regions
        if row[0] == parent_frame_ref
    )
    if not matching:
        return True
    child_nodes = frozenset(_subtree_nodes(state, child_ref))
    child_frames = tuple(
        owner._context.frame(frame_ref)
        for app_ref, frame_ref in state.application_frames
        if app_ref in child_nodes
    )
    if not child_frames:
        return False
    for _parent, _report_start, content_start, content_end in matching:
        if all(
            (span := owner._context.source_span(frame.source_unit_refs)) is not None
            and content_start <= span[0]
            and span[1] <= content_end
            for frame in child_frames
        ):
            return True
    return False


def _reported_scope_is_local(
    owner: Any,
    state: _State,
    scope: Any,
    operand_ref: str,
) -> bool:
    scope_span = owner._context.source_span(scope.source_unit_refs)
    if scope_span is None:
        return True
    applicable = tuple(
        row for row in owner._reported_regions
        if row[2] <= scope_span[0] and scope_span[1] <= row[3]
    )
    if not applicable:
        return True
    operand_nodes = frozenset(_subtree_nodes(state, operand_ref))
    operand_frames = tuple(
        owner._context.frame(frame_ref)
        for app_ref, frame_ref in state.application_frames
        if app_ref in operand_nodes
    )
    return bool(operand_frames) and any(
        all(
            (span := owner._context.source_span(frame.source_unit_refs)) is not None
            and content_start <= span[0]
            and span[1] <= content_end
            for frame in operand_frames
        )
        for _parent, _report_start, content_start, content_end in applicable
    )

def iter_choices(owner: Any, state: _State) -> Iterator[_Choice]:
    if len(state.prefix) >= owner._max_actions:
        owner._truncated = True
        return
    used_sources = _used_sources(state)
    bound = _bound_role_set(state)
    roots = _roots(state)
    action_index = len(state.prefix)

    # A request leaf is a separate graph sum type, never an empty application.
    # It cannot be wrapped or combined with proposition structure.
    if any(a.action_type == "project_variable" and len(a.arguments) == 2 for a in state.prefix):
        return
    mode = owner._context.mode_slot(state.prefix[1].arguments[0])
    if not state.node_order and mode is not None and mode.mode == "QUERY":
        for projection in owner._context.query_projection_slots:
            target = owner._context.designation(projection.target_designation_slot_ref)
            if target is None:
                continue
            if not state.selected_designations:
                action = ProgramAction.create(action_index=action_index,
                    action_type="select_designation", arguments=(target.slot_ref,))
                yield _Choice(action=action, selected_designation=target.slot_ref,
                    score_delta_q=target.score_q,
                    provenance_refs=(target.designation_fact_ref, *target.provenance_refs))
            elif state.selected_designations == (target.slot_ref,):
                orthography = set(projection.orthographic_source_unit_refs)
                ownership = tuple((ref, binding.contribution_slot_ref)
                    for binding in projection.bindings for ref in binding.source_unit_refs
                    if ref not in orthography)
                sources = tuple(ref for ref in projection.source_unit_refs
                    if ref in {ref for ref, _ in ownership})
                if set(sources) & used_sources:
                    continue
                local_ref = _next_node_ref("projection", state)
                action = ProgramAction.create(action_index=action_index,
                    action_type="project_variable", arguments=(local_ref, projection.slot_ref),
                    source_unit_refs=sources)
                pointers = dict(ownership)
                uses = tuple(_SourceUse(ref, pointers[ref], "projection", action.action_ref,
                    None, owner._context.contribution(pointers[ref]).kind in _CRITICAL_KINDS)
                    for ref in sources)
                yield _Choice(action=action, source_uses=uses, declared_node_ref=local_ref,
                    used_structure_slot=projection.slot_ref,
                    provenance_refs=projection.provenance_refs)

    # Required and optional ordinary role/reference bindings.
    for app_ref, frame_ref in state.application_frames:
        frame = owner._context.frame(frame_ref)
        if frame is None:
            continue
        roles = (*frame.required_roles, *frame.optional_roles)
        for role_ref in roles:
            if (app_ref, role_ref) in bound or role_ref in frame.proposition_roles:
                continue
            for contribution in sorted(
                owner._context.contribution_slots, key=lambda row: row.slot_ref
            ):
                if contribution.kind not in _ROLE_KINDS:
                    continue
                if role_ref not in contribution.output_ports:
                    continue
                naming_slots = owner._naming_binding_slots.get((frame_ref, role_ref))
                if naming_slots is not None and contribution.slot_ref not in naming_slots:
                    continue
                if type(frame) is UnresolvedDesignationFrame and (role_ref != "role:surface" or contribution.slot_ref != frame.literal_contribution_slot_ref):
                    continue
                nominal_slots = owner._nominal_binding_slots.get(frame_ref)
                if nominal_slots is not None and contribution.slot_ref not in nominal_slots:
                    continue
                sources = tuple(contribution.source_unit_refs)
                if not sources or any(ref in used_sources for ref in sources):
                    continue
                action = ProgramAction.create(
                    action_index=action_index,
                    action_type="bind_role",
                    arguments=(app_ref, role_ref, contribution.slot_ref),
                    source_unit_refs=sources,
                )
                uses = tuple(
                    _SourceUse(
                        source_unit_ref=source_ref,
                        contribution_slot_ref=contribution.slot_ref,
                        assignment_kind=(
                            "qualifier"
                            if contribution.kind == "qualifier"
                            else "role"
                        ),
                        target_action_ref=action.action_ref,
                        target_role_ref=role_ref,
                        critical=contribution.kind in _CRITICAL_KINDS,
                    )
                    for source_ref in sources
                )
                yield _Choice(
                    action=action,
                    source_uses=uses,
                    bound_role=(app_ref, role_ref),
                    provenance_refs=tuple(
                        (
                            *contribution.provenance_refs,
                            *(
                                (contribution.target_ref,)
                                if contribution.target_ref is not None
                                else ()
                            ),
                        )
                    ),
                )
            for reference in sorted(
                owner._context.reference_slots,
                key=lambda row: (-row.score_q, row.slot_ref),
            ):
                if type(frame) is UnresolvedDesignationFrame:
                    continue
                if role_ref not in reference.compatible_roles:
                    continue
                naming_slots = owner._naming_binding_slots.get((frame_ref, role_ref))
                if naming_slots is not None and reference.slot_ref not in naming_slots:
                    continue
                nominal_slots = owner._nominal_binding_slots.get(frame_ref)
                if nominal_slots is not None and reference.slot_ref not in nominal_slots:
                    continue
                scoped_frames = tuple(
                    ref
                    for ref in reference.provenance_refs
                    if ref.startswith("application_frame_slot:")
                )
                if scoped_frames and frame_ref not in scoped_frames:
                    continue
                action = ProgramAction.create(
                    action_index=action_index,
                    action_type="bind_reference",
                    arguments=(app_ref, role_ref, reference.slot_ref),
                    source_unit_refs=reference.source_unit_refs,
                )
                bundles = _support_bundles(
                    owner._context,
                    tuple(reference.source_unit_refs),
                    kinds=frozenset({"reference"}),
                    assignment_kind="reference",
                    action_ref=action.action_ref,
                    role_ref=role_ref,
                    used_sources=used_sources,
                    branch_bound=owner._branch_bound,
                    target_ref=reference.target_ref,
                    target_kind=reference.target_kind,
                )
                for uses in bundles:
                    yield _Choice(
                        action=action,
                        source_uses=uses,
                        bound_role=(app_ref, role_ref),
                        score_delta_q=reference.score_q,
                        provenance_refs=(
                            reference.target_ref,
                            *reference.provenance_refs,
                        ),
                    )

    # Proposition-valued role parenting uses an unparented existing root.
    for app_ref, frame_ref in state.application_frames:
        frame = owner._context.frame(frame_ref)
        if frame is None:
            continue
        for role_ref in frame.proposition_roles:
            if (app_ref, role_ref) in bound:
                continue
            support_rows = tuple(
                contribution
                for contribution in owner._context.contribution_slots
                if contribution.kind in _LINK_KINDS
                and role_ref in contribution.output_ports
                and contribution.source_unit_refs
                and not any(
                    ref in used_sources for ref in contribution.source_unit_refs
                )
            )
            support_options: tuple[Any | None, ...] = (
                tuple(sorted(support_rows, key=lambda row: row.slot_ref))
                if support_rows
                else (None,)
            )
            for child_ref in roots:
                if child_ref == app_ref:
                    continue
                if not _reported_child_is_local(
                    owner, state, frame_ref, child_ref
                ):
                    continue
                for support in support_options:
                    sources = (
                        tuple(support.source_unit_refs)
                        if support is not None
                        else ()
                    )
                    action = ProgramAction.create(
                        action_index=action_index,
                        action_type="bind_nested_application",
                        arguments=("role", app_ref, role_ref, child_ref),
                        source_unit_refs=sources,
                    )
                    uses = (
                        tuple(
                            _SourceUse(
                                source_unit_ref=source_ref,
                                contribution_slot_ref=support.slot_ref,
                                assignment_kind="discourse",
                                target_action_ref=action.action_ref,
                                target_role_ref=None,
                                critical=support.kind in _CRITICAL_KINDS,
                            )
                            for source_ref in sources
                        )
                        if support is not None
                        else ()
                    )
                    yield _Choice(
                        action=action,
                        source_uses=uses,
                        parent_edges=((child_ref, app_ref),),
                        bound_role=(app_ref, role_ref),
                        provenance_refs=(
                            tuple(support.provenance_refs)
                            if support is not None
                            else ()
                        ),
                    )

    # Variable binders bind exactly one frame/role in their body subtree.
    for variable in sorted(
        owner._context.variable_slots, key=lambda row: row.slot_ref
    ):
        if variable.slot_ref in state.used_structure_slots:
            continue
        for body_ref in roots:
            variable_binding = _variable_owner(state, body_ref, variable)
            if variable_binding is None:
                continue
            binder_ref = _next_node_ref("variable", state)
            action = ProgramAction.create(
                action_index=action_index,
                action_type="project_variable",
                arguments=(binder_ref, variable.slot_ref, body_ref),
                source_unit_refs=variable.source_unit_refs,
            )
            bundles = _support_bundles(
                owner._context,
                tuple(variable.source_unit_refs),
                kinds=_VARIABLE_KINDS,
                assignment_kind="role",
                action_ref=action.action_ref,
                role_ref=None,
                used_sources=used_sources,
                branch_bound=owner._branch_bound,
            )
            for raw_uses in bundles:
                frame = owner._context.frame(variable.application_frame_ref)
                if type(frame) is UnresolvedDesignationFrame:
                    binder = owner._context.contribution(frame.query_binder_slot_ref)
                    if binder is None or any(use.source_unit_ref in binder.source_unit_refs and use.contribution_slot_ref != binder.slot_ref for use in raw_uses):
                        continue
                uses = tuple(
                    _SourceUse(
                        source_unit_ref=use.source_unit_ref,
                        contribution_slot_ref=use.contribution_slot_ref,
                        assignment_kind=use.assignment_kind,
                        target_action_ref=use.target_action_ref,
                        target_role_ref=variable.role_ref,
                        critical=use.critical,
                    )
                    for use in raw_uses
                )
                yield _Choice(
                    action=action,
                    source_uses=uses,
                    declared_node_ref=binder_ref,
                    parent_edges=((body_ref, binder_ref),),
                    bound_role=variable_binding,
                    used_structure_slot=variable.slot_ref,
                    provenance_refs=tuple(
                        use.contribution_slot_ref for use in uses
                    ),
                )

    has_missing_required = (
        owner._missing_required_role_count(
            state, include_proposition_roles=False
        )
        > 0
    )
    if not has_missing_required:
        if len(state.application_frames) < owner._max_applications:
            for frame in owner._context.unresolved_designation_frames:
                if frame.slot_ref in state.used_frame_slots or any(ref in used_sources for ref in frame.source_unit_refs):
                    continue
                app_ref = _next_node_ref("application", state)
                action = ProgramAction.create(action_index=action_index, action_type="instantiate_operator", arguments=(app_ref, frame.slot_ref), source_unit_refs=())
                yield _Choice(action=action, declared_node_ref=app_ref,
                    application_frame=(app_ref, frame.slot_ref), used_frame_slot=frame.slot_ref,
                    provenance_refs=(frame.label_type_ref, *frame.provenance_refs))
        # Select designations whose frame has unused predicate geometry.
        for designation in sorted(
            owner._context.designation_slots,
            key=lambda row: (-row.score_q, row.slot_ref),
        ):
            if designation.slot_ref in state.selected_designations:
                continue
            frames = tuple(
                frame
                for frame in owner._context.frame_for_designation(
                    designation.slot_ref
                )
                if frame.slot_ref not in state.used_frame_slots
                and not any(ref in used_sources for ref in frame.source_unit_refs)
            )
            if not frames:
                continue
            action = ProgramAction.create(
                action_index=action_index,
                action_type="select_designation",
                arguments=(designation.slot_ref,),
            )
            yield _Choice(
                action=action,
                selected_designation=designation.slot_ref,
                score_delta_q=designation.score_q,
                provenance_refs=(
                    designation.designation_fact_ref,
                    *designation.provenance_refs,
                ),
            )

        # Instantiate one context-local reviewed frame at most once.
        if len(state.application_frames) < owner._max_applications:
            for designation_ref in state.selected_designations:
                for frame in sorted(
                    owner._context.frame_for_designation(designation_ref),
                    key=lambda row: row.slot_ref,
                ):
                    if frame.slot_ref in state.used_frame_slots:
                        continue
                    app_ref = _next_node_ref("application", state)
                    action = ProgramAction.create(
                        action_index=action_index,
                        action_type="instantiate_operator",
                        arguments=(app_ref, frame.slot_ref),
                        source_unit_refs=_predicate_source_refs(frame),
                    )
                    for uses in _predicate_bundles(
                        owner._context,
                        frame,
                        action,
                        used_sources,
                        owner._branch_bound,
                    ):
                        yield _Choice(
                            action=action,
                            source_uses=uses,
                            declared_node_ref=app_ref,
                            application_frame=(app_ref, frame.slot_ref),
                            used_frame_slot=frame.slot_ref,
                            provenance_refs=(
                                frame.predicate_target_ref,
                                *(
                                    target
                                    for _, target in frame.derived_role_targets
                                ),
                                *frame.provenance_refs,
                            ),
                        )

        # Scope wrapping applies only to current roots and each slot once.
        for scope in sorted(owner._context.scope_slots, key=lambda row: row.slot_ref):
            if scope.slot_ref in state.used_structure_slots:
                continue
            for operand_ref in roots:
                if not _reported_scope_is_local(owner, state, scope, operand_ref):
                    continue
                if scope.operator_type == "scope:polarity":
                    applications = dict(state.application_frames)
                    nominal_owners = owner._nominal_scope_frames.get(scope.slot_ref, frozenset())
                    nominal_operand = any(
                        applications.get(ref) in owner._nominal_binding_slots
                        for ref in _subtree_nodes(state, operand_ref)
                    )
                    # Unselected nominal alternatives cannot constrain another
                    # interpretation. Once active, a nominal source owns only
                    # its direct application, never another root or forest.
                    if nominal_operand or nominal_owners.intersection(applications.values()):
                        if applications.get(operand_ref) not in nominal_owners:
                            continue
                scope_ref = _next_node_ref("scope", state)
                action = ProgramAction.create(
                    action_index=action_index,
                    action_type="attach_scope",
                    arguments=(scope_ref, scope.slot_ref, operand_ref),
                    source_unit_refs=scope.source_unit_refs,
                )
                bundles = _support_bundles(
                    owner._context,
                    tuple(scope.source_unit_refs),
                    kinds=frozenset({"scope"}),
                    assignment_kind="scope",
                    action_ref=action.action_ref,
                    role_ref=None,
                    used_sources=used_sources,
                    branch_bound=owner._branch_bound,
                )
                for uses in bundles:
                    yield _Choice(
                        action=action,
                        source_uses=uses,
                        declared_node_ref=scope_ref,
                        parent_edges=((operand_ref, scope_ref),),
                        used_structure_slot=scope.slot_ref,
                        provenance_refs=(
                            scope.value_ref,
                            *(
                                (scope.construction_ref,)
                                if scope.construction_ref is not None
                                else ()
                            ),
                        ),
                    )

        # Link only current roots so every operand receives one parent.
        for link in sorted(
            owner._context.expression_link_slots, key=lambda row: row.slot_ref
        ):
            if link.slot_ref in state.used_structure_slots:
                continue
            maximum = min(link.max_arity, len(roots))
            for arity in range(link.min_arity, maximum + 1):
                iterator: Iterable[tuple[str, ...]]
                if link.commutative:
                    iterator = combinations(roots, arity)
                else:
                    iterator = permutations(roots, arity)
                for operands in islice(iterator, owner._branch_bound):
                    link_ref = _next_node_ref("link", state)
                    action = ProgramAction.create(
                        action_index=action_index,
                        action_type="bind_nested_application",
                        arguments=(
                            "link",
                            link_ref,
                            link.slot_ref,
                            *operands,
                        ),
                        source_unit_refs=link.source_unit_refs,
                    )
                    bundles = _support_bundles(
                        owner._context,
                        tuple(link.source_unit_refs),
                        kinds=_LINK_KINDS,
                        assignment_kind="connector",
                        action_ref=action.action_ref,
                        role_ref=None,
                        used_sources=used_sources,
                        branch_bound=owner._branch_bound,
                    )
                    for uses in bundles:
                        yield _Choice(
                            action=action,
                            source_uses=uses,
                            declared_node_ref=link_ref,
                            parent_edges=tuple(
                                (operand, link_ref) for operand in operands
                            ),
                            used_structure_slot=link.slot_ref,
                            provenance_refs=(
                                *(
                                    (link.construction_ref,)
                                    if link.construction_ref is not None
                                    else ()
                                ),
                            ),
                        )

        # Transition hints are proof-only and do not alter topology.
        mode = owner._context.mode_slot(state.prefix[1].arguments[0])
        if mode is not None:
            for transition in sorted(
                owner._context.transition_slots, key=lambda row: row.slot_ref
            ):
                for app_ref, frame_ref in state.application_frames:
                    pair = (transition.slot_ref, app_ref)
                    if pair in state.used_transition_pairs:
                        continue
                    if transition.application_frame_ref != frame_ref:
                        continue
                    if mode.mode not in transition.compatible_modes:
                        continue
                    if any(
                        (app_ref, role) not in bound
                        for role in transition.required_roles
                    ):
                        continue
                    # Transition is derived from the already-grounded
                    # application and must not consume predicate evidence twice.
                    action = ProgramAction.create(
                        action_index=action_index,
                        action_type="propose_transition",
                        arguments=(transition.slot_ref, app_ref),
                        source_unit_refs=(),
                    )
                    yield _Choice(
                        action=action,
                        source_uses=(),
                        transition_pair=pair,
                        provenance_refs=(
                            transition.slot_ref,
                            transition.event_type_ref,
                        ),
                    )
