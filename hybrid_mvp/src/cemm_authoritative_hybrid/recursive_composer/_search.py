"""Bounded best-first orchestration for the recursive composer."""

from __future__ import annotations

from heapq import heappop, heappush
from itertools import islice
from typing import Any

from ..programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from ..proposal_context import ProposalContext
from ._core import (
    _ACTION_OVERHEAD,
    _CRITICAL_KINDS,
    _DEFAULT_BRANCH_BOUND,
    _MAX_ACTIONS_PER_APPLICATION,
    _MODE_KINDS,
    _Choice,
    _CompletedProgram,
    _SourceUse,
    _State,
    _bounded_add,
    _bound_role_set,
    _can_add_edges,
    _roots,
    _support_bundles,
    _topology_is_valid,
    _unique,
    _used_sources,
)
from ._expand import iter_choices

class RecursiveComposer:
    """Deterministic bounded best-first search over Program ABI 2 prefixes."""

    __slots__ = (
        "_context",
        "_max_candidates",
        "_max_explored",
        "_max_provenance",
        "_max_applications",
        "_max_nodes",
        "_max_graph_depth",
        "_max_actions",
        "_branch_bound",
        "_explored",
        "_truncated",
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
        max_depth: int = 6,
    ) -> None:
        if type(context) is not ProposalContext:
            raise TypeError("RecursiveComposer requires exact ProposalContext")
        for name, value in (
            ("max_candidates", max_candidates),
            ("max_explored", max_explored),
            ("max_provenance", max_provenance),
            ("max_applications", max_applications),
            ("max_nodes", max_nodes),
            ("max_depth", max_depth),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive exact int")
        self._context = context
        self._max_candidates = min(max_candidates, 48)
        self._max_explored = max_explored
        self._max_provenance = max_provenance
        self._max_applications = max_applications
        self._max_nodes = max_nodes
        self._max_graph_depth = max_depth
        self._max_actions = max_applications * _MAX_ACTIONS_PER_APPLICATION + _ACTION_OVERHEAD
        self._branch_bound = _DEFAULT_BRANCH_BOUND
        self._explored = 0
        self._truncated = False

    @property
    def explored(self) -> int:
        return self._explored

    @property
    def truncated(self) -> bool:
        return self._truncated

    def search(self) -> tuple[_CompletedProgram, ...]:
        self._explored = 0
        self._truncated = False
        frontier: list[tuple[tuple[int, int, int, int], int, _State]] = []
        serial = 0
        for state in self._initial_states():
            heappush(frontier, (self._priority(state), serial, state))
            serial += 1
        if not frontier:
            return ()

        completed: dict[str, _CompletedProgram] = {}
        seen: set[tuple[str, ...]] = set()
        while frontier and self._explored < self._max_explored:
            _, _, state = heappop(frontier)
            signature = tuple(action.action_ref for action in state.prefix)
            if signature in seen:
                continue
            seen.add(signature)
            self._explored += 1

            candidate = self._complete(state)
            if candidate is not None:
                current = completed.get(candidate.program.program_ref)
                if current is None or candidate.score_q > current.score_q:
                    completed[candidate.program.program_ref] = candidate

            choices = tuple(islice(iter_choices(self, state), self._branch_bound + 1))
            if len(choices) > self._branch_bound:
                self._truncated = True
                choices = choices[: self._branch_bound]
            for choice in choices:
                next_state = self._apply(state, choice)
                if next_state is None:
                    continue
                heappush(frontier, (self._priority(next_state), serial, next_state))
                serial += 1

        if frontier:
            self._truncated = True
        ordered = sorted(
            completed.values(),
            key=lambda row: (
                -row.score_q,
                len(row.program.actions),
                row.program.program_ref,
            ),
        )
        if len(ordered) > self._max_candidates:
            self._truncated = True
            ordered = ordered[: self._max_candidates]
        return tuple(ordered)

    def _initial_states(self) -> tuple[_State, ...]:
        states: list[_State] = []
        context_action = ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(self._context.context_ref,),
        )
        for mode in sorted(self._context.mode_slots, key=lambda row: row.slot_ref):
            mode_evidence = tuple(
                row
                for row in self._context.contribution_slots
                if row.kind in _MODE_KINDS
                and set(row.source_unit_refs) <= set(mode.source_unit_refs)
                and (
                    ("semantic_mode_evidence", "capability_query")
                    in row.constraints
                    or ("discourse", "question") in row.constraints
                )
            )
            mode_sources = tuple(
                dict.fromkeys(
                    source_ref
                    for row in mode_evidence
                    for source_ref in row.source_unit_refs
                )
            )
            mode_action = ProgramAction.create(
                action_index=1,
                action_type="select_mode",
                arguments=(mode.slot_ref,),
                source_unit_refs=mode_sources,
            )
            mode_uses = tuple(
                    _SourceUse(
                        source_unit_ref=source_ref,
                        contribution_slot_ref=row.slot_ref,
                        assignment_kind="discourse",
                        target_action_ref=mode_action.action_ref,
                        target_role_ref=None,
                        critical=False,
                    )
                    for row in mode_evidence
                    for source_ref in row.source_unit_refs
            )
            provenance = _unique(
                (
                    self._context.evidence_packet_ref,
                    self._context.form_lattice_ref,
                    self._context.grounding_ref,
                    mode.slot_ref,
                    *((mode.construction_ref,) if mode.construction_ref else ()),
                    *mode.source_unit_refs,
                ),
                self._max_provenance,
            )
            if provenance is None:
                self._truncated = True
                continue
            states.append(
                _State(
                    prefix=(context_action, mode_action),
                    application_frames=(),
                    bound_roles=(),
                    node_order=(),
                    parents=(),
                    source_uses=mode_uses,
                    selected_designations=(),
                    used_frame_slots=(),
                    used_structure_slots=(),
                    used_transition_pairs=(),
                    score_q=0,
                    provenance=provenance,
                )
            )
        return tuple(states)

    def _priority(self, state: _State) -> tuple[int, int, int, int]:
        missing_roles = self._missing_required_role_count(state)
        remaining_sources = len(self._context.source_unit_refs) - len(
            _used_sources(state)
        )
        return (-state.score_q, missing_roles, remaining_sources, len(state.prefix))

    def _missing_required_role_count(
        self, state: _State, *, include_proposition_roles: bool = True
    ) -> int:
        bound = _bound_role_set(state)
        result = 0
        for app_ref, frame_ref in state.application_frames:
            frame = self._context.frame(frame_ref)
            if frame is None:
                return self._max_actions
            result += sum(
                (app_ref, role) not in bound
                for role in frame.required_roles
                if include_proposition_roles or role not in frame.proposition_roles
            )
        return result

    def _apply(self, state: _State, choice: _Choice) -> _State | None:
        use_sources = tuple(row.source_unit_ref for row in choice.source_uses)
        if len(use_sources) != len(set(use_sources)):
            return None
        if set(use_sources) & _used_sources(state):
            return None
        if choice.action.source_unit_refs != use_sources:
            return None
        if (
            choice.declared_node_ref is not None
            and len(state.node_order) >= self._max_nodes
        ):
            self._truncated = True
            return None
        if not _can_add_edges(
            state,
            choice.declared_node_ref,
            choice.parent_edges,
            self._max_graph_depth,
        ):
            return None
        provenance = _unique(
            (*state.provenance, *choice.provenance_refs), self._max_provenance
        )
        if provenance is None:
            self._truncated = True
            return None
        derived_roles: tuple[tuple[str, str], ...] = ()
        if choice.application_frame is not None:
            app_ref, frame_ref = choice.application_frame
            frame = self._context.frame(frame_ref)
            if frame is None:
                return None
            derived_roles = tuple(
                (app_ref, role_ref) for role_ref, _ in frame.derived_role_targets
            )
        new_bound_roles = (
            *state.bound_roles,
            *derived_roles,
            *((choice.bound_role,) if choice.bound_role else ()),
        )
        if len(new_bound_roles) != len(set(new_bound_roles)):
            return None
        return _State(
            prefix=(*state.prefix, choice.action),
            application_frames=(
                *state.application_frames,
                *((choice.application_frame,) if choice.application_frame else ()),
            ),
            bound_roles=new_bound_roles,
            node_order=(
                *state.node_order,
                *((choice.declared_node_ref,) if choice.declared_node_ref else ()),
            ),
            parents=(*state.parents, *choice.parent_edges),
            source_uses=(*state.source_uses, *choice.source_uses),
            selected_designations=(
                *state.selected_designations,
                *((choice.selected_designation,) if choice.selected_designation else ()),
            ),
            used_frame_slots=(
                *state.used_frame_slots,
                *((choice.used_frame_slot,) if choice.used_frame_slot else ()),
            ),
            used_structure_slots=(
                *state.used_structure_slots,
                *((choice.used_structure_slot,) if choice.used_structure_slot else ()),
            ),
            used_transition_pairs=(
                *state.used_transition_pairs,
                *((choice.transition_pair,) if choice.transition_pair else ()),
            ),
            score_q=_bounded_add(state.score_q, choice.score_delta_q),
            provenance=provenance,
        )

    def _complete(self, state: _State) -> _CompletedProgram | None:
        if not state.application_frames or self._missing_required_role_count(state):
            return None
        used_designations = {
            frame.designation_slot_ref
            for _, frame_ref in state.application_frames
            if (frame := self._context.frame(frame_ref)) is not None
        }
        if used_designations != set(state.selected_designations):
            return None
        if not _topology_is_valid(
            state.node_order, state.parents, self._max_graph_depth
        ):
            return None
        roots = _roots(state)
        if not roots:
            return None

        uses = {row.source_unit_ref: row for row in state.source_uses}
        if len(uses) != len(state.source_uses):
            return None
        assignments: list[SourceAssignment] = []
        for source_ref in self._context.source_unit_refs:
            use = uses.get(source_ref)
            if use is not None:
                assignments.append(
                    SourceAssignment.create(
                        source_unit_ref=source_ref,
                        contribution_slot_ref=use.contribution_slot_ref,
                        assignment_kind=use.assignment_kind,
                        target_action_ref=use.target_action_ref,
                        target_role_ref=use.target_role_ref,
                        residual_kind=None,
                        critical=use.critical,
                    )
                )
                continue
            residual = self._context.residual_for_source(source_ref)
            if residual is None or residual.critical:
                return None
            assignments.append(
                SourceAssignment.create(
                    source_unit_ref=source_ref,
                    contribution_slot_ref=residual.residual_ref,
                    assignment_kind="residual",
                    target_action_ref=None,
                    target_role_ref=None,
                    residual_kind=residual.contribution_kind,
                    critical=False,
                )
            )

        complete_action = ProgramAction.create(
            action_index=len(state.prefix),
            action_type="complete_program",
            arguments=(),
        )
        actions = (*state.prefix, complete_action)
        try:
            program = SemanticSwitchProgram.create(
                orientation_ref=self._context.orientation_ref,
                proposal_context_ref=self._context.context_ref,
                actions=actions,
                root_refs=roots,
                mode_slot_ref=state.prefix[1].arguments[0],
                goal_refs=(),
                source_unit_refs=self._context.source_unit_refs,
                source_assignments=tuple(assignments),
                revision_pin=self._context.revision_pin,
            )
        except (TypeError, ValueError):
            return None
        return _CompletedProgram(
            program=program,
            score_q=state.score_q,
            provenance=state.provenance,
        )
