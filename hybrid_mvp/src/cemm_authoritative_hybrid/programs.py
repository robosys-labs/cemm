"""Recursive Semantic Switch Program ABI: bounded recursive program graphs.

This module owns the Semantic Switch Program ABI (version 1). It defines the
closed 12-action switch vocabulary, the five persistent application operators,
typed source assignments (including typed residuals), scope frames and
transition proposals.

The 12-action vocabulary is closed and copied exactly from the confirmed
contract; synonyms or replacement actions are an ABI change. Exact source
assignments — including typed residuals — are immutable serialized fields of
the completed program, not inferred or appended by the coverage verifier.
Role/reference/scope actions establish consumed assignments; the
``complete_program`` action carries an explicit bounded residual-assignment
table for every remaining source unit without creating a thirteenth action
type.

A designation added to an existing identity changes the designation/world
revision but neither expands the action vocabulary nor requires model
retraining. Programs are limited by action count, nesting depth, application
count, and beam/search bounds owned by :class:`RuntimeConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, get_args

from .canonical import stable_ref
from .contributions import ContributionKind
from .persistence import RevisionPin

__all__ = [
    "SWITCH_ACTION_TYPES",
    "PERSISTENT_OPERATORS",
    "ProgramAction",
    "SourceAssignment",
    "SemanticSwitchProgram",
    "ScopeFrame",
    "TransitionProposal",
]


# ---------------------------------------------------------------------------
# Closed action vocabulary (12 actions) and persistent operators (5)
# ---------------------------------------------------------------------------

SWITCH_ACTION_TYPES: tuple[str, ...] = (
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
    "abstain",
)

_SWITCH_ACTION_SET: frozenset[str] = frozenset(SWITCH_ACTION_TYPES)

PERSISTENT_OPERATORS: frozenset[str] = frozenset(
    {"op:designation", "op:type", "op:relation", "op:state", "op:event"}
)

AssignmentKind = Literal[
    "role", "reference", "scope", "qualifier", "discourse", "residual"
]

_ASSIGNMENT_KIND_SET: frozenset[str] = frozenset(get_args(AssignmentKind))  # type: ignore[attr-defined]

ScopeKind = Literal["modal", "polarity", "tense", "aspect", "negation"]
_SCOPE_KIND_SET: frozenset[str] = frozenset(get_args(ScopeKind))  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ProgramAction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProgramAction:
    """A single switch action from the closed 12-action vocabulary.

    Attributes:
        action_ref: a stable ref identifying this action within the program.
        action_type: one of the 12 closed switch action types.
        arguments: bounded pointer slots for dynamic designation, target,
            contribution and context selections.
        source_unit_refs: the source form unit refs this action consumes.
    """

    action_ref: str
    action_type: Literal[
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
        "abstain",
    ]
    arguments: tuple[str, ...]
    source_unit_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.action_type not in _SWITCH_ACTION_SET:
            raise ValueError(f"invalid switch action type: {self.action_type}")
        if not isinstance(self.arguments, tuple):
            object.__setattr__(self, "arguments", tuple(self.arguments))
        if not isinstance(self.source_unit_refs, tuple):
            object.__setattr__(
                self, "source_unit_refs", tuple(self.source_unit_refs)
            )

    def structural_id(self) -> str:
        """Return the structural action ID (ABI + role/kind schema, no dynamic
        pointer values)."""
        return f"{self.action_type}|{','.join(self.arguments)}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_ref": self.action_ref,
            "action_type": self.action_type,
            "arguments": list(self.arguments),
            "source_unit_refs": list(self.source_unit_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProgramAction":
        return cls(
            action_ref=data["action_ref"],
            action_type=data["action_type"],  # type: ignore[arg-type]
            arguments=tuple(data.get("arguments", ())),
            source_unit_refs=tuple(data.get("source_unit_refs", ())),
        )


# ---------------------------------------------------------------------------
# SourceAssignment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceAssignment:
    """An exact, typed assignment of one source unit to one semantic role.

    Every observed unit is consumed into exactly one semantic role or retained
    as exactly one typed residual. Consumed assignments use
    ``assignment_kind`` in ``{role, reference, scope, qualifier, discourse}``;
    residual assignments use ``assignment_kind == "residual"`` with a typed
    ``residual_kind`` from :class:`ContributionKind`.

    Attributes:
        assignment_ref: a stable ref identifying this assignment.
        source_unit_ref: the source form unit ref being assigned.
        contribution_ref: the typed semantic contribution this assignment binds.
        assignment_kind: the semantic role kind of this assignment.
        target_ref: the semantic target ref, or None for open/residual assignments.
        residual_kind: the :class:`ContributionKind` for residual assignments,
            or None for consumed assignments.
        critical: whether this assignment is critical (must be consumed for
            execution). Negation, modality, reference, unknown anchors and
            effect-related evidence are always critical until consumed.
    """

    assignment_ref: str
    source_unit_ref: str
    contribution_ref: str
    assignment_kind: AssignmentKind
    target_ref: str | None
    residual_kind: ContributionKind | None
    critical: bool

    def __post_init__(self) -> None:
        if self.assignment_kind not in _ASSIGNMENT_KIND_SET:
            raise ValueError(f"invalid assignment kind: {self.assignment_kind}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "assignment_ref": self.assignment_ref,
            "source_unit_ref": self.source_unit_ref,
            "contribution_ref": self.contribution_ref,
            "assignment_kind": self.assignment_kind,
            "target_ref": self.target_ref,
            "residual_kind": self.residual_kind,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceAssignment":
        return cls(
            assignment_ref=data["assignment_ref"],
            source_unit_ref=data["source_unit_ref"],
            contribution_ref=data["contribution_ref"],
            assignment_kind=data["assignment_kind"],  # type: ignore[arg-type]
            target_ref=data.get("target_ref"),
            residual_kind=data.get("residual_kind"),  # type: ignore[arg-type]
            critical=bool(data.get("critical", False)),
        )


# ---------------------------------------------------------------------------
# ScopeFrame and TransitionProposal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeFrame:
    """A bounded scope frame attached to an application.

    Attributes:
        scope_ref: a stable ref for this scope frame.
        kind: the scope kind from the closed set.
        target_application_ref: the application this scope frames, or None.
        source_unit_refs: the source unit refs that produced this scope.
    """

    scope_ref: str
    kind: ScopeKind
    target_application_ref: str | None
    source_unit_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind not in _SCOPE_KIND_SET:
            raise ValueError(f"invalid scope kind: {self.kind}")
        if not isinstance(self.source_unit_refs, tuple):
            object.__setattr__(
                self, "source_unit_refs", tuple(self.source_unit_refs)
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope_ref": self.scope_ref,
            "kind": self.kind,
            "target_application_ref": self.target_application_ref,
            "source_unit_refs": list(self.source_unit_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScopeFrame":
        return cls(
            scope_ref=data["scope_ref"],
            kind=data["kind"],  # type: ignore[arg-type]
            target_application_ref=data.get("target_application_ref"),
            source_unit_refs=tuple(data.get("source_unit_refs", ())),
        )


@dataclass(frozen=True)
class TransitionProposal:
    """A bounded transition proposal (event/state effect).

    Attributes:
        transition_ref: a stable ref for this transition.
        event_type_ref: the event type ref.
        subject_ref: the subject of the transition.
        target_state_ref: the target state ref.
        dimension_ref: the state dimension ref.
        preconditions: tuple of precondition refs.
        source_unit_refs: the source unit refs that produced this transition.
    """

    transition_ref: str
    event_type_ref: str
    subject_ref: str
    target_state_ref: str
    dimension_ref: str
    preconditions: tuple[str, ...]
    source_unit_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.preconditions, tuple):
            object.__setattr__(self, "preconditions", tuple(self.preconditions))
        if not isinstance(self.source_unit_refs, tuple):
            object.__setattr__(
                self, "source_unit_refs", tuple(self.source_unit_refs)
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "transition_ref": self.transition_ref,
            "event_type_ref": self.event_type_ref,
            "subject_ref": self.subject_ref,
            "target_state_ref": self.target_state_ref,
            "dimension_ref": self.dimension_ref,
            "preconditions": list(self.preconditions),
            "source_unit_refs": list(self.source_unit_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TransitionProposal":
        return cls(
            transition_ref=data["transition_ref"],
            event_type_ref=data["event_type_ref"],
            subject_ref=data["subject_ref"],
            target_state_ref=data["target_state_ref"],
            dimension_ref=data["dimension_ref"],
            preconditions=tuple(data.get("preconditions", ())),
            source_unit_refs=tuple(data.get("source_unit_refs", ())),
        )


# ---------------------------------------------------------------------------
# SemanticSwitchProgram
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticSwitchProgram:
    """A bounded recursive semantic switch program.

    The program carries its complete action sequence, root graph refs, mode,
    goals, the closed set of source unit refs, and the exact typed source
    assignments (including typed residuals). Source assignments are immutable
    serialized fields of the completed program — they are never inferred or
    appended by the coverage verifier.

    Attributes:
        program_ref: a stable ref for this program.
        orientation_ref: the orientation this program was proposed from.
        actions: tuple of :class:`ProgramAction` (bounded by config).
        root_graph_refs: root application/graph refs for recursive composition.
        mode_ref: the semantic mode ref.
        goal_refs: tuple of goal refs.
        source_unit_refs: the closed set of source unit refs the program covers.
        source_assignments: exact typed assignments, one per source unit.
        revision_pin: the :class:`RevisionPin` this program was proposed under.
    """

    program_ref: str
    orientation_ref: str
    actions: tuple[ProgramAction, ...]
    root_graph_refs: tuple[str, ...]
    mode_ref: str
    goal_refs: tuple[str, ...]
    source_unit_refs: tuple[str, ...]
    source_assignments: tuple[SourceAssignment, ...]
    revision_pin: RevisionPin

    def __post_init__(self) -> None:
        if not isinstance(self.actions, tuple):
            object.__setattr__(self, "actions", tuple(self.actions))
        if not isinstance(self.root_graph_refs, tuple):
            object.__setattr__(self, "root_graph_refs", tuple(self.root_graph_refs))
        if not isinstance(self.goal_refs, tuple):
            object.__setattr__(self, "goal_refs", tuple(self.goal_refs))
        if not isinstance(self.source_unit_refs, tuple):
            object.__setattr__(
                self, "source_unit_refs", tuple(self.source_unit_refs)
            )
        if not isinstance(self.source_assignments, tuple):
            object.__setattr__(
                self, "source_assignments", tuple(self.source_assignments)
            )

    # -- derived properties --------------------------------------------------

    @property
    def persistent_operators(self) -> frozenset[str]:
        """The set of persistent operators instantiated by this program.

        Only the five persistent application operators may appear; this is a
        subset of :data:`PERSISTENT_OPERATORS`.
        """
        operators: set[str] = set()
        for action in self.actions:
            if action.action_type == "instantiate_operator" and action.arguments:
                operators.add(action.arguments[0])
        return frozenset(operators)

    @property
    def action_encoding_hash(self) -> str:
        """A stable hash of the structural action IDs, sorted canonically.

        Structural action IDs are derived from the ABI plus reviewed role/kind
        schemas; dynamic designation, target, contribution and context
        selections use bounded pointer slots and do not change the structural
        identity.
        """
        structural_ids = sorted(action.structural_id() for action in self.actions)
        return stable_ref("program_actions", structural_ids)

    # -- canonical serialization --------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        return {
            "program_ref": self.program_ref,
            "orientation_ref": self.orientation_ref,
            "actions": [a.as_dict() for a in self.actions],
            "root_graph_refs": list(self.root_graph_refs),
            "mode_ref": self.mode_ref,
            "goal_refs": list(self.goal_refs),
            "source_unit_refs": list(self.source_unit_refs),
            "source_assignments": [a.as_dict() for a in self.source_assignments],
            "revision_pin": {
                "authority_generation": self.revision_pin.authority_generation,
                "world_revision": self.revision_pin.world_revision,
                "session_revision": self.revision_pin.session_revision,
                "episode_revision": self.revision_pin.episode_revision,
                "effect_revision": self.revision_pin.effect_revision,
                "model_identity": self.revision_pin.model_identity,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticSwitchProgram":
        pin_data = data["revision_pin"]
        return cls(
            program_ref=data["program_ref"],
            orientation_ref=data["orientation_ref"],
            actions=tuple(
                ProgramAction.from_dict(a) for a in data.get("actions", ())
            ),
            root_graph_refs=tuple(data.get("root_graph_refs", ())),
            mode_ref=data["mode_ref"],
            goal_refs=tuple(data.get("goal_refs", ())),
            source_unit_refs=tuple(data.get("source_unit_refs", ())),
            source_assignments=tuple(
                SourceAssignment.from_dict(a)
                for a in data.get("source_assignments", ())
            ),
            revision_pin=RevisionPin(
                authority_generation=pin_data["authority_generation"],
                world_revision=pin_data["world_revision"],
                session_revision=pin_data["session_revision"],
                episode_revision=pin_data["episode_revision"],
                effect_revision=pin_data["effect_revision"],
                model_identity=pin_data.get("model_identity"),
            ),
        )
