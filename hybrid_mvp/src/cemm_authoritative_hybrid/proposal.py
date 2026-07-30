"""Deterministic proposal oracle and semantic episode seed.

This module owns :class:`ProposalModel`, :class:`ProposalResult`, and
:class:`BootstrapProposer`.

The :class:`BootstrapProposer` is a deterministic oracle for tests and episode
construction only. It searches legal action prefixes using the
:class:`LegalActionIndex` and indexed contributions/ports. It has no phrase
inventory and no word/regex branch. Canonical tie-breaking makes episode
generation deterministic.

The running product must load a safetensors-backed
:class:`NeuralSwitchProposer`; the :class:`BootstrapProposer` raises if
constructed by the release runtime factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .canonical import stable_ref
from .contributions import ContributionExpander
from .coverage import CoverageVerifier
from .cycle import Orientation
from .forms import FormResolver
from .grounding import Grounder
from .affordances import SemanticAffordanceIndex
from .authority import LinkedAuthority
from .config import RuntimeConfig
from .persistence import RevisionPin
from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from .verifier import ExactProgramVerifier, LegalActionIndex

__all__ = [
    "ProposalModel",
    "ProposalResult",
    "BootstrapProposer",
]


# ---------------------------------------------------------------------------
# ProposalModel protocol
# ---------------------------------------------------------------------------


class ProposalModel(Protocol):
    """Protocol for a proposal model (bootstrap or neural)."""

    model_identity: str

    def propose(self, orientation: Orientation) -> "ProposalResult":
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ProposalResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProposalResult:
    """The result of a proposal model's search.

    Attributes:
        candidates: tuple of verified :class:`SemanticSwitchProgram`.
        explored_states: number of search states explored.
        truncated: whether the search was truncated by bounds.
        model_identity: the identity of the proposal model.
    """

    candidates: tuple[SemanticSwitchProgram, ...]
    explored_states: int
    truncated: bool
    model_identity: str


# ---------------------------------------------------------------------------
# BootstrapProposer — deterministic oracle for tests and episode construction
# ---------------------------------------------------------------------------


class BootstrapProposer:
    """Deterministic proposal oracle for tests and episode construction.

    Searches legal action prefixes using the :class:`LegalActionIndex` and
    indexed contributions/ports. It has no phrase inventory and no word/regex
    branch. Canonical tie-breaking makes episode generation deterministic.

    Raises :class:`RuntimeError` if the ``release_only`` flag is set, preventing
    use in the release runtime.
    """

    model_identity: str = "bootstrap-proposer"

    def __init__(
        self,
        authority: LinkedAuthority,
        config: RuntimeConfig,
        form_resolver: FormResolver,
        grounder: Grounder,
        affordance_index: SemanticAffordanceIndex,
        contribution_expander: ContributionExpander,
        verifier: ExactProgramVerifier,
        coverage_verifier: CoverageVerifier,
        legal_action_index: LegalActionIndex,
    ) -> None:
        self._authority = authority
        self._config = config
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._affordance_index = affordance_index
        self._contribution_expander = contribution_expander
        self._verifier = verifier
        self._coverage_verifier = coverage_verifier
        self._legal_action_index = legal_action_index
        self._max_candidates = getattr(config, "max_complete_candidates", 48)
        self._max_actions = getattr(config, "max_applications", 24)
        self._max_explored = getattr(config, "max_beam_states", 32) * self._max_actions
        self._release_only: bool = False

    # -- public API ----------------------------------------------------------

    def propose(self, orientation: Orientation) -> ProposalResult:
        """Propose verified programs for ``orientation``.

        Searches legal action prefixes using BFS over the
        :class:`LegalActionIndex`. For each complete prefix (ending with
        ``complete_program`` or ``abstain``), builds a
        :class:`SemanticSwitchProgram` with source assignments and verifies it.

        Canonical tie-breaking: candidates are sorted by ``program_ref`` for
        determinism.
        """
        if self._release_only:
            raise RuntimeError(
                "BootstrapProposer cannot be used in release runtime"
            )

        text = orientation.source_text
        lattice = self._form_resolver.resolve(text)

        # Ground designations and expand contributions.
        grounding_result = self._grounder.ground_text(text)
        self._contribution_expander.expand(grounding_result, lattice)

        # Collect content units (non-whitespace, non-punctuation).
        content_unit_refs = [
            u.unit_ref for u in lattice.units if u.source_text.strip()
        ]

        # Build revision pin matching the authority generation.
        pin = self._build_revision_pin(orientation)

        # DFS over legal action prefixes.
        candidates, explored, truncated = self._search(
            lattice, content_unit_refs, orientation, pin
        )

        # Canonical tie-breaking: sort by program_ref, deduplicate.
        seen_refs: set[str] = set()
        unique: list[SemanticSwitchProgram] = []
        for p in sorted(candidates, key=lambda p: p.program_ref):
            if p.program_ref not in seen_refs:
                seen_refs.add(p.program_ref)
                unique.append(p)
        candidates = tuple(unique)

        return ProposalResult(
            candidates=candidates,
            explored_states=explored,
            truncated=truncated,
            model_identity=self.model_identity,
        )

    def propose_detailed(
        self, orientation: Orientation
    ) -> tuple[ProposalResult, list[dict[str, Any]]]:
        """Propose and return detailed results including rejected alternatives.

        Returns a tuple of (ProposalResult, rejected_alternatives) where
        ``rejected_alternatives`` is a list of dicts with ``action_ids``,
        ``program_ref``, and ``rejection_codes`` for each legal prefix that was
        built into a program but failed verification.
        """
        if self._release_only:
            raise RuntimeError(
                "BootstrapProposer cannot be used in release runtime"
            )

        text = orientation.source_text
        lattice = self._form_resolver.resolve(text)

        grounding_result = self._grounder.ground_text(text)
        self._contribution_expander.expand(grounding_result, lattice)

        content_unit_refs = [
            u.unit_ref for u in lattice.units if u.source_text.strip()
        ]
        pin = self._build_revision_pin(orientation)

        candidates, rejected, explored, truncated = self._search_detailed(
            lattice, content_unit_refs, orientation, pin
        )
        # Canonical tie-breaking: sort by program_ref, deduplicate.
        seen_refs: set[str] = set()
        unique: list[SemanticSwitchProgram] = []
        for p in sorted(candidates, key=lambda p: p.program_ref):
            if p.program_ref not in seen_refs:
                seen_refs.add(p.program_ref)
                unique.append(p)
        candidates = tuple(unique)

        result = ProposalResult(
            candidates=candidates,
            explored_states=explored,
            truncated=truncated,
            model_identity=self.model_identity,
        )
        return result, rejected

    # -- internal: revision pin ---------------------------------------------

    def _build_revision_pin(self, orientation: Orientation) -> RevisionPin:
        """Build a revision pin matching the authority's generation."""
        base = orientation.revision_pin
        if base is not None and base.authority_generation == self._authority.generation:
            return base
        return RevisionPin(
            authority_generation=self._authority.generation,
            world_revision=0,
            session_revision=0,
            episode_revision=0,
            effect_revision=0,
            model_identity=self.model_identity,
        )

    # -- internal: DFS search -----------------------------------------------

    def _search(
        self,
        lattice: Any,
        content_unit_refs: list[str],
        orientation: Orientation,
        pin: RevisionPin,
    ) -> tuple[list[SemanticSwitchProgram], int, bool]:
        """Bounded DFS over legal action prefixes.

        Searches for prefixes ending with ``complete_program``. If no
        complete_program candidates are found, an abstain fallback is added.

        Returns a tuple of (candidates, explored_states, truncated).
        """
        candidates: list[SemanticSwitchProgram] = []
        explored = 0
        truncated = False

        stack: list[tuple[ProgramAction, ...]] = [()]

        while stack:
            if len(candidates) >= self._max_candidates:
                truncated = True
                break
            if explored >= self._max_explored:
                truncated = True
                break

            prefix = stack.pop()
            explored += 1

            actions = self._generate_candidates(prefix, content_unit_refs)
            legal_actions = [
                a for a in actions if self._legal_action_index.is_legal(a, prefix)
            ]
            legal_actions.sort(key=lambda a: a.structural_id())

            # Push non-terminal actions in reverse order so the first
            # (by structural_id) is processed first (DFS).
            for action in reversed(legal_actions):
                if action.action_type == "complete_program":
                    new_prefix = prefix + (action,)
                    program = self._build_program(
                        new_prefix, lattice, orientation, pin
                    )
                    if program is not None:
                        result = self._verifier.verify(program)
                        if result.accepted:
                            candidates.append(program)
                            if len(candidates) >= self._max_candidates:
                                break
                elif action.action_type == "abstain":
                    # Skip abstain during DFS; only use as fallback.
                    continue
                else:
                    new_prefix = prefix + (action,)
                    if len(new_prefix) < self._max_actions:
                        stack.append(new_prefix)

            if len(candidates) >= self._max_candidates:
                truncated = True
                break

        # Fallback: if no complete_program candidates, add abstain.
        if not candidates:
            abstain_action = ProgramAction(
                action_ref="action:0",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
            program = self._build_program(
                (abstain_action,), lattice, orientation, pin
            )
            if program is not None:
                result = self._verifier.verify(program)
                if result.accepted:
                    candidates.append(program)

        return candidates, explored, truncated

    def _search_detailed(
        self,
        lattice: Any,
        content_unit_refs: list[str],
        orientation: Orientation,
        pin: RevisionPin,
    ) -> tuple[list[SemanticSwitchProgram], list[dict[str, Any]], int, bool]:
        """Bounded DFS over legal action prefixes with rejected tracking.

        Returns a tuple of (candidates, rejected, explored_states, truncated).
        """
        candidates: list[SemanticSwitchProgram] = []
        rejected: list[dict[str, Any]] = []
        explored = 0
        truncated = False

        stack: list[tuple[ProgramAction, ...]] = [()]

        while stack:
            if len(candidates) >= self._max_candidates:
                truncated = True
                break
            if explored >= self._max_explored:
                truncated = True
                break

            prefix = stack.pop()
            explored += 1

            actions = self._generate_candidates(prefix, content_unit_refs)
            legal_actions = [
                a for a in actions if self._legal_action_index.is_legal(a, prefix)
            ]
            legal_actions.sort(key=lambda a: a.structural_id())

            for action in reversed(legal_actions):
                if action.action_type == "complete_program":
                    new_prefix = prefix + (action,)
                    program = self._build_program(
                        new_prefix, lattice, orientation, pin
                    )
                    if program is not None:
                        result = self._verifier.verify(program)
                        if result.accepted:
                            candidates.append(program)
                            if len(candidates) >= self._max_candidates:
                                break
                        else:
                            rejected.append({
                                "action_ids": [
                                    a.structural_id() for a in new_prefix
                                ],
                                "program_ref": program.program_ref,
                                "rejection_codes": [
                                    e.code for e in result.errors
                                ],
                            })
                elif action.action_type == "abstain":
                    continue
                else:
                    new_prefix = prefix + (action,)
                    if len(new_prefix) < self._max_actions:
                        stack.append(new_prefix)

            if len(candidates) >= self._max_candidates:
                truncated = True
                break

        # Fallback: if no complete_program candidates, add abstain.
        if not candidates:
            abstain_action = ProgramAction(
                action_ref="action:0",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
            program = self._build_program(
                (abstain_action,), lattice, orientation, pin
            )
            if program is not None:
                result = self._verifier.verify(program)
                if result.accepted:
                    candidates.append(program)

        return candidates, rejected, explored, truncated

    # -- internal: candidate generation -------------------------------------

    def _generate_candidates(
        self, prefix: tuple[ProgramAction, ...], content_unit_refs: list[str]
    ) -> list[ProgramAction]:
        """Generate candidate actions for the given prefix.

        Generates only the essential actions for finding complete programs:
        ``select_context``, ``select_mode``, ``select_designation``,
        ``instantiate_operator``, ``bind_role``, and ``complete_program``.
        For ``bind_role``, uses actual lattice content units instead of the
        fallback ``unit:0``.

        The :class:`LegalActionIndex`'s ``is_legal`` predicate is used to
        filter these candidates, ensuring the same legality constraints as the
        verifier's exhaustive enumeration.
        """
        candidates: list[ProgramAction] = []
        idx = len(prefix)
        legal = self._legal_action_index

        # select_context
        for ctx in sorted(legal._context_refs):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                )
            )
        if not legal._context_refs:
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_context",
                    arguments=("context:turn",),
                    source_unit_refs=(),
                )
            )

        # select_mode
        for mode in sorted(legal._modes):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_mode",
                    arguments=(mode,),
                    source_unit_refs=(),
                )
            )

        # select_designation
        for target in sorted(legal._designation_targets):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_designation",
                    arguments=("designation:0", target),
                    source_unit_refs=(),
                )
            )

        # instantiate_operator
        for op in sorted(legal._operators):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="instantiate_operator",
                    arguments=(op, "designation:0"),
                    source_unit_refs=(),
                )
            )

        # bind_role — use actual lattice content units, skip already-bound roles/units
        operator: str | None = None
        for a in prefix:
            if a.action_type == "instantiate_operator" and a.arguments:
                operator = a.arguments[0]
                break
        if operator is not None:
            # Track already-bound roles and consumed units.
            bound_roles: set[str] = set()
            consumed_units: set[str] = set()
            for a in prefix:
                if a.action_type == "bind_role" and a.arguments:
                    bound_roles.add(a.arguments[0])
                    consumed_units.update(a.source_unit_refs)
            for role in legal._operator_roles.get(operator, ()):
                if role in bound_roles:
                    continue
                for unit in content_unit_refs:
                    if unit in consumed_units:
                        continue
                    candidates.append(
                        ProgramAction(
                            action_ref=f"action:{idx}",
                            action_type="bind_role",
                            arguments=(role, unit),
                            source_unit_refs=(unit,),
                        )
                    )

        # complete_program
        candidates.append(
            ProgramAction(
                action_ref=f"action:{idx}",
                action_type="complete_program",
                arguments=(),
                source_unit_refs=(),
            )
        )

        return candidates

    # -- internal: program building ------------------------------------------

    def _build_program(
        self,
        prefix: tuple[ProgramAction, ...],
        lattice: Any,
        orientation: Orientation,
        pin: RevisionPin,
    ) -> SemanticSwitchProgram | None:
        """Build a :class:`SemanticSwitchProgram` from a complete prefix.

        Returns None if the prefix is not a valid complete program.
        """
        if not prefix:
            return None

        last = prefix[-1]
        if last.action_type not in ("complete_program", "abstain"):
            return None

        # Extract mode from select_mode action.
        mode_name = "OBSERVE"
        for a in prefix:
            if a.action_type == "select_mode" and a.arguments:
                mode_name = a.arguments[0]
                break

        # Extract root graph ref from instantiate_operator action.
        root_refs: tuple[str, ...] = ()
        for a in prefix:
            if a.action_type == "instantiate_operator":
                root_refs = (a.action_ref,)
                break

        # Collect all source unit refs from the lattice.
        unit_refs = tuple(u.unit_ref for u in lattice.units)

        # Build source assignments.
        assignments = self._build_assignments(prefix, lattice)

        # Generate a deterministic program_ref.
        action_ids = [a.structural_id() for a in prefix]
        program_ref = stable_ref(
            "program",
            {
                "orientation": orientation.cache_key,
                "actions": sorted(action_ids),
                "mode": mode_name,
            },
        )

        return SemanticSwitchProgram(
            program_ref=program_ref,
            orientation_ref=orientation.cache_key or "orientation:0",
            actions=prefix,
            root_graph_refs=root_refs,
            mode_ref=f"mode:{mode_name}",
            goal_refs=(),
            source_unit_refs=unit_refs,
            source_assignments=assignments,
            revision_pin=pin,
        )

    def _build_assignments(
        self,
        prefix: tuple[ProgramAction, ...],
        lattice: Any,
    ) -> tuple[SourceAssignment, ...]:
        """Build source assignments from the prefix and lattice.

        For each bind_role action, the source_unit_refs are consumed into a
        role assignment. For remaining units, punctuation/whitespace become
        noncritical discourse residuals and content units become noncritical
        qualifier residuals.
        """
        # Track which units are consumed by bind_role actions.
        consumed: dict[str, str] = {}  # unit_ref -> role_name
        for action in prefix:
            if action.action_type == "bind_role" and action.source_unit_refs:
                role_name = action.arguments[0] if action.arguments else ""
                for unit_ref in action.source_unit_refs:
                    consumed[unit_ref] = role_name

        assignments: list[SourceAssignment] = []
        for unit in lattice.units:
            unit_ref = unit.unit_ref
            is_punct = not unit.source_text.strip() or not unit.normalized_forms

            if unit_ref in consumed:
                role_name = consumed[unit_ref]
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="role",
                        target_ref=f"target:{role_name}",
                        residual_kind=None,
                        critical=False,
                    )
                )
            elif is_punct:
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="residual",
                        target_ref=None,
                        residual_kind="discourse",
                        critical=False,
                    )
                )
            else:
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="residual",
                        target_ref=None,
                        residual_kind="qualifier",
                        critical=False,
                    )
                )

        return tuple(assignments)
