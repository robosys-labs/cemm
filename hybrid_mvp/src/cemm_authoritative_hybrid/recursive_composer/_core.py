"""Bounded recursive Program ABI 2 composer.

The bootstrap proposer is a deterministic construction oracle over one immutable
``ProposalContext``.  This module owns search only: it never opens authority,
retokenizes evidence, invokes VERIFY, or treats a program as semantic meaning.

Search is bounded before expansion.  Every state retains exact source ownership
and parent topology so a completed candidate is emitted only when its source
assignments, roots, reachability, acyclicity and graph depth are already valid.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice, product
from typing import Any, Iterable

from ..programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from ..proposal_context import ProposalContext

_CRITICAL_KINDS = frozenset(
    {
        "anchor",
        "predicate",
        "binder",
        "reference",
        "scope",
        "connector",
        "literal",
        "open_variable",
    }
)
_ROLE_KINDS = frozenset({"anchor", "literal", "qualifier"})
_LINK_KINDS = frozenset({"connector", "discourse"})
_MODE_KINDS = frozenset({"discourse"})
_VARIABLE_KINDS = frozenset({"binder", "open_variable"})
_TRANSITION_KINDS = frozenset({"discourse"})
_MAX_ACTIONS_PER_APPLICATION = 8
_ACTION_OVERHEAD = 16
_DEFAULT_BRANCH_BOUND = 32


@dataclass(frozen=True)
class _SourceUse:
    source_unit_ref: str
    contribution_slot_ref: str
    assignment_kind: str
    target_action_ref: str
    target_role_ref: str | None
    critical: bool


@dataclass(frozen=True)
class _State:
    prefix: tuple[ProgramAction, ...]
    application_frames: tuple[tuple[str, str], ...]
    bound_roles: tuple[tuple[str, str], ...]
    node_order: tuple[str, ...]
    parents: tuple[tuple[str, str], ...]
    source_uses: tuple[_SourceUse, ...]
    selected_designations: tuple[str, ...]
    used_frame_slots: tuple[str, ...]
    used_structure_slots: tuple[str, ...]
    used_transition_pairs: tuple[tuple[str, str], ...]
    score_q: int
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class _Choice:
    action: ProgramAction
    source_uses: tuple[_SourceUse, ...] = ()
    declared_node_ref: str | None = None
    parent_edges: tuple[tuple[str, str], ...] = ()
    application_frame: tuple[str, str] | None = None
    bound_role: tuple[str, str] | None = None
    selected_designation: str | None = None
    used_frame_slot: str | None = None
    used_structure_slot: str | None = None
    transition_pair: tuple[str, str] | None = None
    score_delta_q: int = 0
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CompletedProgram:
    program: SemanticSwitchProgram
    score_q: int
    provenance: tuple[str, ...]


def _bounded_add(left: int, right: int) -> int:
    return max(-(2**63), min((2**63) - 1, left + right))


def _unique(values: Iterable[str], maximum: int) -> tuple[str, ...] | None:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        if len(result) >= maximum:
            return None
        seen.add(value)
        result.append(value)
    return tuple(result)


def _application_map(state: _State) -> dict[str, str]:
    return dict(state.application_frames)


def _bound_role_set(state: _State) -> set[tuple[str, str]]:
    return set(state.bound_roles)


def _used_sources(state: _State) -> set[str]:
    return {row.source_unit_ref for row in state.source_uses}


def _roots(state: _State) -> tuple[str, ...]:
    parented = {child for child, _ in state.parents}
    return tuple(ref for ref in state.node_order if ref not in parented)


def _children(state: _State) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for child, parent in state.parents:
        grouped.setdefault(parent, []).append(child)
    return {key: tuple(value) for key, value in grouped.items()}


def _subtree_nodes(state: _State, root_ref: str) -> tuple[str, ...]:
    children = _children(state)
    result: list[str] = []
    stack = [root_ref]
    while stack:
        ref = stack.pop()
        result.append(ref)
        stack.extend(reversed(children.get(ref, ())))
    return tuple(result)


def _topology_is_valid(
    node_order: tuple[str, ...],
    parents: tuple[tuple[str, str], ...],
    max_depth: int,
) -> bool:
    nodes = set(node_order)
    parent_map: dict[str, str] = {}
    for child, parent in parents:
        if child not in nodes or parent not in nodes or child == parent:
            return False
        if child in parent_map:
            return False
        parent_map[child] = parent
    if not nodes:
        return False
    roots = tuple(ref for ref in node_order if ref not in parent_map)
    if not roots:
        return False
    for node in node_order:
        seen: set[str] = set()
        cursor = node
        depth = 1
        while cursor in parent_map:
            if cursor in seen:
                return False
            seen.add(cursor)
            cursor = parent_map[cursor]
            depth += 1
            if depth > max_depth:
                return False
        if cursor not in roots:
            return False
    return True


def _can_add_edges(
    state: _State,
    declared_node_ref: str | None,
    edges: tuple[tuple[str, str], ...],
    max_depth: int,
) -> bool:
    if declared_node_ref is None and not edges:
        return True
    nodes = state.node_order
    if declared_node_ref is not None:
        if declared_node_ref in nodes:
            return False
        nodes = (*nodes, declared_node_ref)
    return _topology_is_valid(nodes, (*state.parents, *edges), max_depth)


def _contributions_for_source(
    context: ProposalContext,
    source_ref: str,
    *,
    kinds: frozenset[str],
    role_ref: str | None = None,
    target_ref: str | None = None,
    target_kind: str | None = None,
) -> tuple[Any, ...]:
    rows: list[Any] = []
    for contribution in context.contributions_for_source(source_ref):
        if contribution.kind not in kinds:
            continue
        if role_ref is not None and role_ref not in contribution.output_ports:
            continue
        if target_ref is not None and contribution.target_ref != target_ref:
            continue
        if target_kind is not None and contribution.target_kind != target_kind:
            continue
        rows.append(contribution)
    rows.sort(key=lambda row: row.slot_ref)
    return tuple(rows)


def _support_bundles(
    context: ProposalContext,
    source_refs: tuple[str, ...],
    *,
    kinds: frozenset[str],
    assignment_kind: str,
    action_ref: str,
    role_ref: str | None,
    used_sources: set[str],
    branch_bound: int,
    target_ref: str | None = None,
    target_kind: str | None = None,
) -> tuple[tuple[_SourceUse, ...], ...]:
    if not source_refs:
        return ((),)
    if len(source_refs) != len(set(source_refs)) or any(
        ref in used_sources for ref in source_refs
    ):
        return ()
    alternatives: list[tuple[Any, ...]] = []
    for source_ref in source_refs:
        rows = _contributions_for_source(
            context,
            source_ref,
            kinds=kinds,
            role_ref=role_ref,
            target_ref=target_ref,
            target_kind=target_kind,
        )
        if not rows:
            return ()
        alternatives.append(rows)
    bundles: list[tuple[_SourceUse, ...]] = []
    for selected in islice(product(*alternatives), branch_bound):
        bundles.append(
            tuple(
                _SourceUse(
                    source_unit_ref=source_ref,
                    contribution_slot_ref=contribution.slot_ref,
                    assignment_kind=assignment_kind,
                    target_action_ref=action_ref,
                    target_role_ref=role_ref,
                    critical=contribution.kind in _CRITICAL_KINDS,
                )
                for source_ref, contribution in zip(
                    source_refs, selected, strict=True
                )
            )
        )
    return tuple(bundles)


def _predicate_bundles(
    context: ProposalContext,
    frame: Any,
    action: ProgramAction,
    used_sources: set[str],
    branch_bound: int,
) -> tuple[tuple[_SourceUse, ...], ...]:
    return _support_bundles(
        context,
        tuple(frame.source_unit_refs),
        kinds=frozenset({"predicate"}),
        assignment_kind="predicate",
        action_ref=action.action_ref,
        role_ref=None,
        used_sources=used_sources,
        branch_bound=branch_bound,
        target_ref=frame.predicate_target_ref,
        target_kind=frame.predicate_kind,
    )


def _next_node_ref(kind: str, state: _State) -> str:
    count = sum(ref.startswith(f"{kind}:") for ref in state.node_order)
    return f"{kind}:{count}"


def _variable_owner(
    state: _State,
    body_ref: str,
    variable: Any,
) -> tuple[str, str] | None:
    applications = _application_map(state)
    bound = _bound_role_set(state)
    matches = tuple(
        app_ref
        for app_ref in _subtree_nodes(state, body_ref)
        if applications.get(app_ref) == variable.application_frame_ref
        and (app_ref, variable.role_ref) not in bound
    )
    if len(matches) != 1:
        return None
    return matches[0], variable.role_ref


