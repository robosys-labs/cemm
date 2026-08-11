"""Context-local bounded action expansion for recursive composition."""

from __future__ import annotations

from itertools import combinations, islice, permutations
from typing import Any, Iterable, Iterator

from ..programs import ProgramAction
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
    _used_sources,
    _variable_owner,
)

def iter_choices(owner: Any, state: _State) -> Iterator[_Choice]:
    if len(state.prefix) >= owner._max_actions:
        owner._truncated = True
        return
    used_sources = _used_sources(state)
    bound = _bound_role_set(state)
    roots = _roots(state)
    action_index = len(state.prefix)

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
                if role_ref not in reference.compatible_roles:
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

    has_missing_required = owner._missing_required_role_count(state) > 0
    if not has_missing_required:
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

