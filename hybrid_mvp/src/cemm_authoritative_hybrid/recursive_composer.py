"""Bounded recursive Program ABI 2 composer for the bootstrap proposer.

This module implements deterministic bounded DFS over legal action prefixes
using the context-local :class:`LegalActionIndex`. It produces canonical
``SemanticSwitchProgram`` candidates with:

- multiple applications and roots;
- grounded role/reference bindings;
- proposition-valued role nesting;
- expression links;
- scopes;
- variable binders;
- transition hints;
- exact source assignments;
- deterministic root derivation from declared parent topology.

The composer never invokes VERIFY, never inspects ref-name spelling, and never
creates authority. Scoring uses exact fixed-point integers only.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Sequence

from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from .proposal_context import ProposalContext
from .verifier import LegalActionIndex, _prefix_budget, _prefix_state

__all__ = ["RecursiveComposer"]


# ---------------------------------------------------------------------------
# Immutable search state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SearchState:
    """Immutable state for one branch of the bounded DFS."""

    prefix: tuple[ProgramAction, ...]
    consumed_sources: frozenset[str]
    binding_map: frozenset[tuple[str, str, str, str, str]]
    """(source_ref, action_ref, application_ref, role_ref, contribution_slot_ref)."""
    predicate_map: frozenset[tuple[str, str, str]]
    """(source_ref, application_ref, frame_slot_ref)."""
    score_q: int
    provenance: tuple[str, ...]


@dataclass
class _CompletedProgram:
    program: SemanticSwitchProgram
    score_q: int
    provenance: tuple[str, ...]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _add_score(left: int, right: int) -> int:
    return max(-(2**63), min((2**63) - 1, left + right))


def _critical_contribution(kind: str) -> bool:
    return kind not in {"discourse", "qualifier"}


def _assignment_kind_for_contribution(kind: str) -> str:
    return "qualifier" if kind == "qualifier" else "role"


def _find_predicate_slot(context: ProposalContext, frame: Any) -> Any | None:
    for source_ref in frame.source_unit_refs:
        for contribution in context.contributions_for_source(source_ref):
            if (
                contribution.kind == "predicate"
                and contribution.target_ref == frame.predicate_target_ref
                and contribution.target_kind == frame.predicate_kind
            ):
                return contribution
    return None


def _find_supporting_contribution(
    context: ProposalContext, source_ref: str, reference: Any
) -> str | None:
    """Find the supporting 'reference' kind contribution for a source ref."""
    for contribution in context.contributions_for_source(source_ref):
        if (
            contribution.kind == "reference"
            and contribution.target_ref == reference.target_ref
            and contribution.target_kind == reference.target_kind
        ):
            return contribution.slot_ref
    return None


def _find_action_by_ref(
    prefix: tuple[ProgramAction, ...], action_ref: str
) -> ProgramAction | None:
    for action in prefix:
        if action.action_ref == action_ref:
            return action
    return None


def _find_instantiate_action(
    prefix: tuple[ProgramAction, ...], app_ref: str
) -> ProgramAction | None:
    for action in prefix:
        if (
            action.action_type == "instantiate_operator"
            and action.arguments
            and action.arguments[0] == app_ref
        ):
            return action
    return None


def _operand_combinations(
    nodes: list[str], arity: int
) -> tuple[tuple[str, ...], ...]:
    if arity == 0 or not nodes:
        return ()
    if arity == 1:
        return tuple((node,) for node in nodes)
    return tuple(permutations(nodes, arity))


def _derive_roots(prefix: tuple[ProgramAction, ...]) -> tuple[str, ...]:
    """Derive root nodes from declared parent topology."""
    all_nodes: set[str] = set()
    children: set[str] = set()
    node_order: list[str] = []

    for action in prefix:
        args = action.arguments
        if action.action_type == "instantiate_operator":
            app_ref = args[0]
            if app_ref not in all_nodes:
                all_nodes.add(app_ref)
                node_order.append(app_ref)
        elif action.action_type == "bind_nested_application":
            if args[0] == "role":
                children.add(args[3])
            else:
                link_ref = args[1]
                if link_ref not in all_nodes:
                    all_nodes.add(link_ref)
                    node_order.append(link_ref)
                for operand in args[3:]:
                    children.add(operand)
        elif action.action_type == "attach_scope":
            scope_ref = args[0]
            if scope_ref not in all_nodes:
                all_nodes.add(scope_ref)
                node_order.append(scope_ref)
            children.add(args[2])
        elif action.action_type == "project_variable":
            var_ref = args[0]
            if var_ref not in all_nodes:
                all_nodes.add(var_ref)
                node_order.append(var_ref)
            children.add(args[2])

    roots = [node for node in node_order if node not in children]
    return tuple(roots) if roots else tuple(all_nodes - children)


def _enumerate_legal_actions(
    context: ProposalContext,
    legal_index: LegalActionIndex,
    prefix: tuple[ProgramAction, ...],
) -> tuple[ProgramAction, ...]:
    """Enumerate all legal actions from this prefix in deterministic order."""
    idx = len(prefix)
    designations, applications, nodes, bound_roles, terminal = _prefix_state(
        context, prefix
    )
    if terminal:
        return ()

    actions: list[ProgramAction] = []

    # 1. complete_program (highest priority — greedy completion)
    complete = ProgramAction.create(
        action_index=idx, action_type="complete_program", arguments=()
    )
    if legal_index.is_legal(complete, prefix):
        actions.append(complete)

    # 2. bind_role (prioritize binding existing applications)
    # Only anchor/literal/qualifier contributions are eligible for bind_role.
    # Reference-kind contributions use bind_reference via ReferenceSlot.
    _BIND_ROLE_KINDS = frozenset({"anchor", "literal", "qualifier"})
    for app_ref in sorted(applications):
        frame = applications[app_ref]
        all_roles = sorted(set(frame.required_roles) | set(frame.optional_roles))
        for role_ref in all_roles:
            if role_ref in bound_roles.get(app_ref, set()):
                continue
            for contribution in sorted(
                context.contribution_slots, key=lambda r: r.slot_ref
            ):
                if contribution.kind not in _BIND_ROLE_KINDS:
                    continue
                if role_ref not in contribution.output_ports:
                    continue
                if not contribution.source_unit_refs:
                    continue
                action = ProgramAction.create(
                    action_index=idx,
                    action_type="bind_role",
                    arguments=(app_ref, role_ref, contribution.slot_ref),
                    source_unit_refs=contribution.source_unit_refs,
                )
                if legal_index.is_legal(action, prefix):
                    actions.append(action)

    # 3. bind_reference
    for app_ref in sorted(applications):
        frame = applications[app_ref]
        all_roles = sorted(set(frame.required_roles) | set(frame.optional_roles))
        for role_ref in all_roles:
            if role_ref in bound_roles.get(app_ref, set()):
                continue
            for reference in sorted(
                context.reference_slots, key=lambda r: (-r.score_q, r.slot_ref)
            ):
                if role_ref not in reference.compatible_roles:
                    continue
                action = ProgramAction.create(
                    action_index=idx,
                    action_type="bind_reference",
                    arguments=(app_ref, role_ref, reference.slot_ref),
                    source_unit_refs=reference.source_unit_refs,
                )
                if legal_index.is_legal(action, prefix):
                    actions.append(action)

    # 4. bind_nested_application (role)
    for app_ref in sorted(applications):
        frame = applications[app_ref]
        for role_ref in sorted(frame.proposition_roles):
            if role_ref in bound_roles.get(app_ref, set()):
                continue
            for nested_ref in sorted(nodes):
                if nested_ref == app_ref:
                    continue
                action = ProgramAction.create(
                    action_index=idx,
                    action_type="bind_nested_application",
                    arguments=("role", app_ref, role_ref, nested_ref),
                )
                if legal_index.is_legal(action, prefix):
                    actions.append(action)

    # 5. attach_scope
    for scope in sorted(context.scope_slots, key=lambda r: r.slot_ref):
        scope_ref = f"scope:{len(nodes)}"
        for target_ref in sorted(nodes):
            action = ProgramAction.create(
                action_index=idx,
                action_type="attach_scope",
                arguments=(scope_ref, scope.slot_ref, target_ref),
            )
            if legal_index.is_legal(action, prefix):
                actions.append(action)

    # 6. project_variable
    for variable in sorted(context.variable_slots, key=lambda r: r.slot_ref):
        var_ref = f"variable:{len(nodes)}"
        for target_ref in sorted(nodes):
            action = ProgramAction.create(
                action_index=idx,
                action_type="project_variable",
                arguments=(var_ref, variable.slot_ref, target_ref),
            )
            if legal_index.is_legal(action, prefix):
                actions.append(action)

    # 7. propose_transition
    for transition in sorted(context.transition_slots, key=lambda r: r.slot_ref):
        for app_ref in sorted(applications):
            action = ProgramAction.create(
                action_index=idx,
                action_type="propose_transition",
                arguments=(transition.slot_ref, app_ref),
            )
            if legal_index.is_legal(action, prefix):
                actions.append(action)

    # 8. bind_nested_application (link) — structural, lower priority
    for link in sorted(context.expression_link_slots, key=lambda r: r.slot_ref):
        link_ref = f"link:{len(nodes)}"
        for arity in range(link.min_arity, link.max_arity + 1):
            for operands in _operand_combinations(sorted(nodes), arity):
                action = ProgramAction.create(
                    action_index=idx,
                    action_type="bind_nested_application",
                    arguments=("link", link_ref, link.slot_ref, *operands),
                )
                if legal_index.is_legal(action, prefix):
                    actions.append(action)

    # 9. select_designation — only if no unbound required roles remain
    #    in existing applications (prevents role-binding starvation)
    has_unbound_required = any(
        set(frame.required_roles) - bound_roles.get(app_ref, set())
        for app_ref, frame in applications.items()
    )
    if not has_unbound_required:
        for designation in sorted(
            context.designation_slots, key=lambda r: (-r.score_q, r.slot_ref)
        ):
            if designation.slot_ref in designations:
                continue
            action = ProgramAction.create(
                action_index=idx,
                action_type="select_designation",
                arguments=(designation.slot_ref,),
            )
            if legal_index.is_legal(action, prefix):
                actions.append(action)

    # 10. instantiate_operator — only if no unbound required roles remain
    if not has_unbound_required:
        app_count, _, _ = _prefix_budget(prefix)
        for designation_ref in sorted(designations):
            for frame in sorted(
                context.frame_for_designation(designation_ref),
                key=lambda r: r.slot_ref,
            ):
                app_ref = f"application:{app_count}"
                action = ProgramAction.create(
                    action_index=idx,
                    action_type="instantiate_operator",
                    arguments=(app_ref, frame.slot_ref),
                    source_unit_refs=frame.source_unit_refs,
                )
                if legal_index.is_legal(action, prefix):
                    actions.append(action)

    return tuple(actions)


def _build_assignments(
    context: ProposalContext,
    state: _SearchState,
) -> tuple[SourceAssignment, ...] | None:
    """Build exact source assignments for all source unit refs."""
    assignments: list[SourceAssignment] = []
    binding_map = dict(
        (src, (action_ref, app_ref, role_ref, slot_ref))
        for src, action_ref, app_ref, role_ref, slot_ref in state.binding_map
    )
    predicate_map = dict(
        (src, (app_ref, frame_slot_ref))
        for src, app_ref, frame_slot_ref in state.predicate_map
    )

    for source_ref in context.source_unit_refs:
        if source_ref in predicate_map:
            app_ref, frame_slot_ref = predicate_map[source_ref]
            frame = context.frame(frame_slot_ref)
            if frame is None:
                return None
            predicate_slot = _find_predicate_slot(context, frame)
            if predicate_slot is None:
                return None
            instantiate_action = _find_instantiate_action(state.prefix, app_ref)
            if instantiate_action is None:
                return None
            assignments.append(
                SourceAssignment.create(
                    source_unit_ref=source_ref,
                    contribution_slot_ref=predicate_slot.slot_ref,
                    assignment_kind="predicate",
                    target_action_ref=instantiate_action.action_ref,
                    target_role_ref=None,
                    residual_kind=None,
                    critical=True,
                )
            )
            continue

        binding = binding_map.get(source_ref)
        if binding is not None:
            action_ref, app_ref, role_ref, slot_ref = binding
            action = _find_action_by_ref(state.prefix, action_ref)
            if action is None:
                return None
            if action.action_type == "bind_role":
                slot = context.contribution(slot_ref)
                if slot is None:
                    return None
                kind = _assignment_kind_for_contribution(slot.kind)
                critical = _critical_contribution(slot.kind)
                assignment_slot_ref = slot_ref
            else:
                reference = context.reference(slot_ref)
                if reference is None:
                    return None
                kind = "reference"
                critical = True
                # For bind_reference, the source assignment uses the
                # supporting "reference" kind contribution slot, not the
                # reference slot itself.
                assignment_slot_ref = _find_supporting_contribution(
                    context, source_ref, reference
                )
                if assignment_slot_ref is None:
                    return None
            assignments.append(
                SourceAssignment.create(
                    source_unit_ref=source_ref,
                    contribution_slot_ref=assignment_slot_ref,
                    assignment_kind=kind,
                    target_action_ref=action_ref,
                    target_role_ref=role_ref,
                    residual_kind=None,
                    critical=critical,
                )
            )
            continue

        residual = context.residual_for_source(source_ref)
        if residual is not None:
            assignments.append(
                SourceAssignment.create(
                    source_unit_ref=source_ref,
                    contribution_slot_ref=residual.residual_ref,
                    assignment_kind="residual",
                    target_action_ref=None,
                    target_role_ref=None,
                    residual_kind=residual.contribution_kind,
                    critical=residual.critical,
                )
            )
            continue

        return None

    return tuple(assignments)


# ---------------------------------------------------------------------------
# Recursive composer
# ---------------------------------------------------------------------------


class RecursiveComposer:
    """Deterministic bounded DFS over legal action prefixes."""

    __slots__ = (
        "_context", "_legal_index", "_max_candidates", "_max_explored",
        "_max_provenance", "_max_depth", "_results", "_explored", "_truncated",
    )

    def __init__(
        self,
        context: ProposalContext,
        *,
        max_candidates: int = 48,
        max_explored: int = 768,
        max_provenance: int = 64,
        max_applications: int = 24,
        max_nodes: int = 64,
        max_depth: int = 32,
    ) -> None:
        self._context = context
        self._legal_index = LegalActionIndex(
            context, max_applications=max_applications, max_nodes=max_nodes
        )
        self._max_candidates = max_candidates
        self._max_explored = max_explored
        self._max_provenance = max_provenance
        self._max_depth = max_depth
        self._results: list[_CompletedProgram] = []
        self._explored = 0
        self._truncated = False

    @property
    def explored(self) -> int:
        return self._explored

    @property
    def truncated(self) -> bool:
        return self._truncated

    def search(self) -> tuple[_CompletedProgram, ...]:
        """Run the bounded DFS and return completed programs."""
        context = self._context
        mode_ref = sorted(context.mode_slots, key=lambda r: r.slot_ref)[0].slot_ref
        initial = _SearchState(
            prefix=(
                ProgramAction.create(
                    action_index=0,
                    action_type="select_context",
                    arguments=(context.context_ref,),
                ),
                ProgramAction.create(
                    action_index=1,
                    action_type="select_mode",
                    arguments=(mode_ref,),
                ),
            ),
            consumed_sources=frozenset(),
            binding_map=frozenset(),
            predicate_map=frozenset(),
            score_q=0,
            provenance=(
                context.evidence_packet_ref,
                context.form_lattice_ref,
                context.grounding_ref,
            ),
        )
        self._dfs(initial)
        return tuple(self._results)

    def _dfs(self, state: _SearchState) -> None:
        if len(self._results) >= self._max_candidates:
            self._truncated = True
            return
        if self._explored >= self._max_explored:
            self._truncated = True
            return
        if len(state.prefix) >= self._max_depth:
            return
        self._explored += 1

        actions = _enumerate_legal_actions(
            self._context, self._legal_index, state.prefix
        )
        # Separate complete_program from extending actions
        complete_action = None
        extending: list[ProgramAction] = []
        for action in actions:
            if action.action_type == "complete_program":
                complete_action = action
            else:
                extending.append(action)

        # Try complete_program first (greedy completion)
        if complete_action is not None:
            new_state = self._extend(state, complete_action)
            if new_state is not None:
                completed = self._finalize(new_state)
                if completed is not None:
                    self._results.append(completed)
                    # If we have enough candidates, stop exploring
                    if len(self._results) >= self._max_candidates:
                        self._truncated = bool(extending)
                        return

        # Then explore extending actions
        for action in extending:
            if len(self._results) >= self._max_candidates:
                self._truncated = True
                return
            if self._explored >= self._max_explored:
                self._truncated = True
                return
            new_state = self._extend(state, action)
            if new_state is None:
                continue
            self._dfs(new_state)

    def _extend(
        self, state: _SearchState, action: ProgramAction
    ) -> _SearchState | None:
        context = self._context
        new_prefix = state.prefix + (action,)
        consumed = set(state.consumed_sources)
        bindings = set(state.binding_map)
        predicates = set(state.predicate_map)
        score = state.score_q
        provenance = list(state.provenance)
        args = action.arguments

        if action.action_type == "select_designation":
            designation = context.designation(args[0])
            if designation is None:
                return None
            score = _add_score(score, designation.score_q)
            provenance.extend(designation.provenance_refs)
            provenance.append(designation.designation_fact_ref)
        elif action.action_type == "instantiate_operator":
            app_ref, frame_slot_ref = args
            frame = context.frame(frame_slot_ref)
            if frame is None:
                return None
            for src in frame.source_unit_refs:
                consumed.add(src)
                predicates.add((src, app_ref, frame_slot_ref))
            provenance.extend(frame.provenance_refs)
            provenance.append(frame.predicate_target_ref)
            for _, target_ref in frame.derived_role_targets:
                provenance.append(target_ref)
        elif action.action_type in ("bind_role", "bind_reference"):
            app_ref, role_ref, slot_ref = args
            if action.action_type == "bind_role":
                slot = context.contribution(slot_ref)
                if slot is None:
                    return None
                src_refs = slot.source_unit_refs
                provenance.extend(slot.provenance_refs)
                if slot.target_ref is not None:
                    provenance.append(slot.target_ref)
                score = _add_score(score, getattr(slot, "score_q", 0))
            else:
                slot = context.reference(slot_ref)
                if slot is None:
                    return None
                src_refs = slot.source_unit_refs
                provenance.extend(slot.provenance_refs)
                provenance.append(slot.target_ref)
                score = _add_score(score, slot.score_q)
            for src in src_refs:
                consumed.add(src)
                bindings.add((src, action.action_ref, app_ref, role_ref, slot_ref))
        elif action.action_type == "bind_nested_application":
            if args[0] != "role":
                link = context.expression_link(args[2])
                if link is None:
                    return None
                for src in link.source_unit_refs:
                    consumed.add(src)
        elif action.action_type == "attach_scope":
            scope = context.scope(args[1])
            if scope is None:
                return None
            for src in scope.source_unit_refs:
                consumed.add(src)
        elif action.action_type == "project_variable":
            variable = context.variable(args[1])
            if variable is None:
                return None
            for src in variable.source_unit_refs:
                consumed.add(src)
        elif action.action_type == "propose_transition":
            transition = context.transition(args[0])
            if transition is None:
                return None
            for src in transition.source_unit_refs:
                consumed.add(src)
            provenance.extend(transition.source_unit_refs)
        elif action.action_type == "complete_program":
            pass
        else:
            return None

        return _SearchState(
            prefix=new_prefix,
            consumed_sources=frozenset(consumed),
            binding_map=frozenset(bindings),
            predicate_map=frozenset(predicates),
            score_q=score,
            provenance=self._unique_bounded(provenance),
        )

    def _finalize(self, state: _SearchState) -> _CompletedProgram | None:
        context = self._context
        prefix = state.prefix
        # The prefix already includes the complete_program action (added by _extend)
        actions = prefix
        root_refs = _derive_roots(prefix)
        if not root_refs:
            return None
        assignments = _build_assignments(context, state)
        if assignments is None:
            return None
        try:
            program = SemanticSwitchProgram.create(
                orientation_ref=context.orientation_ref,
                proposal_context_ref=context.context_ref,
                actions=actions,
                root_refs=root_refs,
                mode_slot_ref=prefix[1].arguments[0],
                goal_refs=(),
                source_unit_refs=context.source_unit_refs,
                source_assignments=assignments,
                revision_pin=context.revision_pin,
            )
        except (ValueError, TypeError):
            return None
        return _CompletedProgram(
            program=program,
            score_q=state.score_q,
            provenance=self._unique_bounded(state.provenance),
        )

    def _unique_bounded(self, refs: Sequence[str]) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            result.append(ref)
            if len(result) >= self._max_provenance:
                break
        return tuple(result)
