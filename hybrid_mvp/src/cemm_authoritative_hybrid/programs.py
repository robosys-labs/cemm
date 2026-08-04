"""Semantic Switch Program ABI 2: exact bounded derivation procedures.

A program records how a candidate meaning is constructed from one exact
Proposal Context. It is never the canonical meaning itself and therefore never
contains resolved applications or a semantic expression graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from types import MappingProxyType
from typing import Any, Iterable, Literal, Mapping, get_args

from .canonical import stable_ref
from .config import RuntimeConfig
from .contributions import ContributionKind
from .persistence import RevisionPin

PROGRAM_ABI_VERSION = 2

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
_SWITCH_ACTION_SET = frozenset(SWITCH_ACTION_TYPES)

PERSISTENT_OPERATORS: frozenset[str] = frozenset(
    {"op:designation", "op:type", "op:relation", "op:state", "op:event"}
)

# These values are ABI descriptions, not candidate values. The hash therefore
# stays stable when designation/context pointers or derivation order changes.
ACTION_ABI_SCHEMAS: Mapping[str, tuple[tuple[str, ...], ...]] = MappingProxyType(
    {
        "select_context": (("proposal_context_ref",),),
        "select_mode": (("mode_slot_ref",),),
        "select_designation": (("designation_slot_ref",),),
        "instantiate_operator": (
            ("application_local_ref", "application_frame_slot_ref"),
        ),
        "bind_role": (
            ("application_local_ref", "role_ref", "contribution_slot_ref"),
        ),
        "bind_reference": (
            ("application_local_ref", "role_ref", "reference_slot_ref"),
        ),
        "bind_nested_application": (
            ("literal:role", "parent_application_ref", "role_ref", "child_node_ref"),
            (
                "literal:link", "link_local_ref", "expression_link_slot_ref",
                "operand_node_refs[2:24]",
            ),
        ),
        "attach_scope": (("scope_local_ref", "scope_slot_ref", "operand_node_ref"),),
        "project_variable": (
            ("binder_local_ref", "variable_slot_ref", "body_node_ref"),
        ),
        "propose_transition": (("transition_slot_ref", "source_application_ref"),),
        "complete_program": ((),),
        "abstain": ((),),
    }
)
ACTION_ABI_HASH = stable_ref(
    "action_abi",
    {
        "program_abi_version": PROGRAM_ABI_VERSION,
        "schemas": [
            {"action_type": action_type, "variants": ACTION_ABI_SCHEMAS[action_type]}
            for action_type in SWITCH_ACTION_TYPES
        ],
    },
)

AssignmentKind = Literal[
    "role",
    "predicate",
    "reference",
    "scope",
    "qualifier",
    "discourse",
    "connector",
    "residual",
]
_ASSIGNMENT_KIND_SET = frozenset(get_args(AssignmentKind))
_VALID_CONTRIBUTION_KINDS = frozenset(get_args(ContributionKind))

_RELEASE_CONFIG = RuntimeConfig.release()
_MAX_ACTIONS = _RELEASE_CONFIG.max_applications * 8 + 16
_MAX_SOURCE_UNITS = _RELEASE_CONFIG.max_input_tokens
_MAX_ROOTS = 8
_MAX_GOALS = 16
_MAX_REF_CHARS = 256
_MAX_ARGUMENTS = _RELEASE_CONFIG.max_applications + 3

__all__ = [
    "PROGRAM_ABI_VERSION",
    "SWITCH_ACTION_TYPES",
    "PERSISTENT_OPERATORS",
    "ACTION_ABI_SCHEMAS",
    "ACTION_ABI_HASH",
    "ProgramAction",
    "SourceAssignment",
    "SemanticSwitchProgram",
]


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    if len(value) > _MAX_REF_CHARS:
        raise ValueError(f"{field} exceeds the release bound")
    return value


def _optional_ref(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _required(value, field)


def _bounded_tuple(values: Iterable[Any], maximum: int, field: str) -> tuple[Any, ...]:
    result = tuple(islice(iter(values), maximum + 1))
    if len(result) > maximum:
        raise ValueError(f"{field} exceeds the release bound")
    return result


def _exact_fields(data: Mapping[str, Any], expected: frozenset[str], owner: str) -> None:
    if not isinstance(data, Mapping) or set(data) != expected:
        raise ValueError(f"{owner} fields must match the canonical schema exactly")


def _wire_list(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    return value


def _validate_action_arguments(action_type: str, arguments: tuple[str, ...]) -> None:
    if action_type not in _SWITCH_ACTION_SET:
        raise ValueError(f"invalid switch action type: {action_type}")
    valid = False
    if action_type == "bind_nested_application":
        valid = (
            len(arguments) == 4 and arguments[0] == "role"
        ) or (
            5 <= len(arguments) <= _MAX_ARGUMENTS and arguments[0] == "link"
        )
    else:
        valid = any(len(arguments) == len(schema) for schema in ACTION_ABI_SCHEMAS[action_type])
    if not valid:
        raise ValueError(f"arguments violate the {action_type} action schema")


@dataclass(frozen=True, init=False)
class ProgramAction:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ProgramAction.create")

    action_ref: str
    action_index: int
    action_type: str
    arguments: tuple[str, ...]
    source_unit_refs: tuple[str, ...]

    @classmethod
    def _from_canonical(
        cls,
        action_ref: str,
        action_index: int,
        action_type: str,
        arguments: tuple[str, ...],
        source_unit_refs: tuple[str, ...],
    ) -> "ProgramAction":
        value = object.__new__(cls)
        for field, item in (
            ("action_ref", action_ref),
            ("action_index", action_index),
            ("action_type", action_type),
            ("arguments", arguments),
            ("source_unit_refs", source_unit_refs),
        ):
            object.__setattr__(value, field, item)
        return value

    @classmethod
    def create(
        cls,
        *,
        action_index: int,
        action_type: str,
        arguments: Iterable[str],
        source_unit_refs: Iterable[str] = (),
    ) -> "ProgramAction":
        if type(action_index) is not int or action_index < 0 or action_index >= _MAX_ACTIONS:
            raise ValueError("action_index must be a bounded non-negative integer")
        _required(action_type, "action_type")
        argument_tuple = _bounded_tuple(arguments, _MAX_ARGUMENTS, "action arguments")
        for argument in argument_tuple:
            _required(argument, "action argument")
        _validate_action_arguments(action_type, argument_tuple)
        sources = _bounded_tuple(source_unit_refs, _MAX_SOURCE_UNITS, "action source refs")
        for source_ref in sources:
            _required(source_ref, "source_unit_ref")
        if len(sources) != len(set(sources)):
            raise ValueError("duplicate action source ref")
        material = {
            "abi_version": PROGRAM_ABI_VERSION,
            "action_index": action_index,
            "action_type": action_type,
            "arguments": list(argument_tuple),
            "source_unit_refs": list(sources),
        }
        return cls._from_canonical(
            stable_ref("program_action", material),
            action_index,
            action_type,
            argument_tuple,
            sources,
        )

    def structural_id(self) -> str:
        """Return model-vocabulary identity without dynamic candidate pointers."""
        return f"{ACTION_ABI_HASH}:{self.action_type}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_ref": self.action_ref,
            "action_index": self.action_index,
            "action_type": self.action_type,
            "arguments": list(self.arguments),
            "source_unit_refs": list(self.source_unit_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProgramAction":
        _exact_fields(
            data,
            frozenset(
                {"action_ref", "action_index", "action_type", "arguments", "source_unit_refs"}
            ),
            "ProgramAction",
        )
        action = cls.create(
            action_index=data["action_index"],
            action_type=_required(data["action_type"], "action_type"),
            arguments=(
                _required(item, "action argument")
                for item in _wire_list(data["arguments"], "arguments")
            ),
            source_unit_refs=(
                _required(item, "source_unit_ref")
                for item in _wire_list(data["source_unit_refs"], "source_unit_refs")
            ),
        )
        if data["action_ref"] != action.action_ref:
            raise ValueError("ProgramAction ref mismatch")
        if action.as_dict() != dict(data):
            raise ValueError("non-canonical ProgramAction encoding")
        return action


@dataclass(frozen=True, init=False)
class SourceAssignment:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use SourceAssignment.create")

    assignment_ref: str
    source_unit_ref: str
    contribution_slot_ref: str
    assignment_kind: str
    target_action_ref: str | None
    target_role_ref: str | None
    residual_kind: str | None
    critical: bool

    @classmethod
    def _from_canonical(cls, assignment_ref: str, **values: Any) -> "SourceAssignment":
        value = object.__new__(cls)
        object.__setattr__(value, "assignment_ref", assignment_ref)
        for field, item in values.items():
            object.__setattr__(value, field, item)
        return value

    @classmethod
    def create(
        cls,
        *,
        source_unit_ref: str,
        contribution_slot_ref: str,
        assignment_kind: str,
        target_action_ref: str | None,
        target_role_ref: str | None,
        residual_kind: str | None,
        critical: bool,
    ) -> "SourceAssignment":
        source_unit_ref = _required(source_unit_ref, "source_unit_ref")
        contribution_slot_ref = _required(contribution_slot_ref, "contribution_slot_ref")
        if assignment_kind not in _ASSIGNMENT_KIND_SET:
            raise ValueError(f"invalid assignment kind: {assignment_kind}")
        target_action_ref = _optional_ref(target_action_ref, "target_action_ref")
        target_role_ref = _optional_ref(target_role_ref, "target_role_ref")
        if not isinstance(critical, bool):
            raise ValueError("critical must be boolean")
        if assignment_kind == "residual":
            if target_action_ref is not None or target_role_ref is not None:
                raise ValueError("residual assignment cannot target an action or role")
            if residual_kind not in _VALID_CONTRIBUTION_KINDS:
                raise ValueError("residual assignment requires a contribution kind")
        else:
            if target_action_ref is None:
                raise ValueError("consumed assignment requires a target action")
            if residual_kind is not None:
                raise ValueError("consumed assignment cannot carry a residual kind")
            if assignment_kind in {"role", "reference", "qualifier"} and target_role_ref is None:
                raise ValueError("role-bearing assignment requires target_role_ref")
        material = {
            "abi_version": PROGRAM_ABI_VERSION,
            "source_unit_ref": source_unit_ref,
            "contribution_slot_ref": contribution_slot_ref,
            "assignment_kind": assignment_kind,
            "target_action_ref": target_action_ref,
            "target_role_ref": target_role_ref,
            "residual_kind": residual_kind,
            "critical": critical,
        }
        return cls._from_canonical(
            stable_ref("source_assignment", material),
            source_unit_ref=source_unit_ref,
            contribution_slot_ref=contribution_slot_ref,
            assignment_kind=assignment_kind,
            target_action_ref=target_action_ref,
            target_role_ref=target_role_ref,
            residual_kind=residual_kind,
            critical=critical,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "assignment_ref": self.assignment_ref,
            "source_unit_ref": self.source_unit_ref,
            "contribution_slot_ref": self.contribution_slot_ref,
            "assignment_kind": self.assignment_kind,
            "target_action_ref": self.target_action_ref,
            "target_role_ref": self.target_role_ref,
            "residual_kind": self.residual_kind,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceAssignment":
        _exact_fields(
            data,
            frozenset(
                {
                    "assignment_ref", "source_unit_ref", "contribution_slot_ref",
                    "assignment_kind", "target_action_ref", "target_role_ref",
                    "residual_kind", "critical",
                }
            ),
            "SourceAssignment",
        )
        assignment = cls.create(
            source_unit_ref=_required(data["source_unit_ref"], "source_unit_ref"),
            contribution_slot_ref=_required(
                data["contribution_slot_ref"], "contribution_slot_ref"
            ),
            assignment_kind=_required(data["assignment_kind"], "assignment_kind"),
            target_action_ref=_optional_ref(data["target_action_ref"], "target_action_ref"),
            target_role_ref=_optional_ref(data["target_role_ref"], "target_role_ref"),
            residual_kind=_optional_ref(data["residual_kind"], "residual_kind"),
            critical=data["critical"],
        )
        if data["assignment_ref"] != assignment.assignment_ref:
            raise ValueError("SourceAssignment ref mismatch")
        if assignment.as_dict() != dict(data):
            raise ValueError("non-canonical SourceAssignment encoding")
        return assignment


def _declared_node_ref(action: ProgramAction) -> str | None:
    if action.action_type == "instantiate_operator":
        return action.arguments[0]
    if action.action_type == "bind_nested_application" and action.arguments[0] == "link":
        return action.arguments[1]
    if action.action_type == "attach_scope":
        return action.arguments[0]
    if action.action_type == "project_variable":
        return action.arguments[0]
    return None


def _validate_program_action_graph(
    actions: tuple[ProgramAction, ...],
    proposal_context_ref: str,
    mode_slot_ref: str,
) -> set[str]:
    if tuple(action.action_index for action in actions) != tuple(range(len(actions))):
        raise ValueError("program action indices must be contiguous")
    if len({action.action_ref for action in actions}) != len(actions):
        raise ValueError("duplicate program action ref")
    if actions[0].action_type != "select_context" or actions[0].arguments != (
        proposal_context_ref,
    ):
        raise ValueError("program must first select its exact proposal context")
    if len(actions) < 3 or actions[1].action_type != "select_mode" or actions[1].arguments != (
        mode_slot_ref,
    ):
        raise ValueError("program must second select its exact mode slot")
    terminal = actions[-1].action_type
    if terminal not in {"complete_program", "abstain"}:
        raise ValueError("program must end in one terminal action")
    if any(action.action_type in {"complete_program", "abstain"} for action in actions[:-1]):
        raise ValueError("program contains a non-final terminal action")
    if sum(action.action_type == "select_context" for action in actions) != 1:
        raise ValueError("program requires exactly one select_context action")
    if sum(action.action_type == "select_mode" for action in actions) != 1:
        raise ValueError("program requires exactly one select_mode action")

    declared: set[str] = set()
    for action in actions:
        args = action.arguments
        if action.action_type in {"bind_role", "bind_reference"}:
            if args[0] not in declared:
                raise ValueError("binding targets an undeclared application")
        elif action.action_type == "bind_nested_application":
            if args[0] == "role":
                if args[1] not in declared or args[3] not in declared:
                    raise ValueError("nested role targets an undeclared node")
            else:
                if any(operand not in declared for operand in args[3:]):
                    raise ValueError("expression link targets an undeclared operand")
        elif action.action_type == "attach_scope" and args[2] not in declared:
            raise ValueError("scope targets an undeclared operand")
        elif action.action_type == "project_variable" and args[2] not in declared:
            raise ValueError("binder targets an undeclared body")
        elif action.action_type == "propose_transition" and args[1] not in declared:
            raise ValueError("transition targets an undeclared application")
        node_ref = _declared_node_ref(action)
        if node_ref is not None:
            _required(node_ref, "local node ref")
            if node_ref in declared:
                raise ValueError("duplicate local node ref")
            declared.add(node_ref)
    return declared


@dataclass(frozen=True, init=False)
class SemanticSwitchProgram:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use SemanticSwitchProgram.create")

    program_ref: str
    orientation_ref: str
    proposal_context_ref: str
    actions: tuple[ProgramAction, ...]
    root_refs: tuple[str, ...]
    mode_slot_ref: str
    goal_refs: tuple[str, ...]
    source_unit_refs: tuple[str, ...]
    source_assignments: tuple[SourceAssignment, ...]
    revision_pin: RevisionPin

    @classmethod
    def _from_canonical(cls, program_ref: str, **values: Any) -> "SemanticSwitchProgram":
        value = object.__new__(cls)
        object.__setattr__(value, "program_ref", program_ref)
        for field, item in values.items():
            object.__setattr__(value, field, item)
        return value

    @classmethod
    def create(
        cls,
        *,
        orientation_ref: str,
        proposal_context_ref: str,
        actions: Iterable[ProgramAction],
        root_refs: Iterable[str],
        mode_slot_ref: str,
        goal_refs: Iterable[str],
        source_unit_refs: Iterable[str],
        source_assignments: Iterable[SourceAssignment],
        revision_pin: RevisionPin,
    ) -> "SemanticSwitchProgram":
        orientation_ref = _required(orientation_ref, "orientation_ref")
        proposal_context_ref = _required(proposal_context_ref, "proposal_context_ref")
        mode_slot_ref = _required(mode_slot_ref, "mode_slot_ref")
        if not isinstance(revision_pin, RevisionPin):
            raise ValueError("revision_pin must be RevisionPin")
        action_tuple = _bounded_tuple(actions, _MAX_ACTIONS, "program actions")
        if not action_tuple or any(not isinstance(item, ProgramAction) for item in action_tuple):
            raise ValueError("program actions must be non-empty ProgramAction values")
        for action in action_tuple:
            if ProgramAction.from_dict(action.as_dict()) != action:
                raise ValueError("non-canonical ProgramAction")
        roots = _bounded_tuple(root_refs, _MAX_ROOTS, "program roots")
        goals = _bounded_tuple(goal_refs, _MAX_GOALS, "goal refs")
        sources = _bounded_tuple(source_unit_refs, _MAX_SOURCE_UNITS, "source unit refs")
        assignments = _bounded_tuple(
            source_assignments, _MAX_SOURCE_UNITS, "source assignments"
        )
        for field, values in (("root_ref", roots), ("goal_ref", goals), ("source_unit_ref", sources)):
            for item in values:
                _required(item, field)
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {field}")
        if any(not isinstance(item, SourceAssignment) for item in assignments):
            raise ValueError("source assignments must be SourceAssignment values")
        for assignment in assignments:
            if SourceAssignment.from_dict(assignment.as_dict()) != assignment:
                raise ValueError("non-canonical SourceAssignment")
        declared = _validate_program_action_graph(
            action_tuple, proposal_context_ref, mode_slot_ref
        )
        terminal = action_tuple[-1].action_type
        if terminal == "abstain":
            if tuple(action.action_type for action in action_tuple) != (
                "select_context", "select_mode", "abstain"
            ):
                raise ValueError("abstain program may contain only context, mode and abstain")
            if roots:
                raise ValueError("abstain program cannot declare roots")
        else:
            if not roots or any(root not in declared for root in roots):
                raise ValueError("completed program has an unknown or empty root set")
        if any(source not in set(sources) for action in action_tuple for source in action.source_unit_refs):
            raise ValueError("action references a source outside the program")
        if tuple(item.source_unit_ref for item in assignments) != sources:
            raise ValueError("source assignments must cover source units exactly once in order")
        action_refs = {action.action_ref for action in action_tuple}
        if any(
            item.target_action_ref is not None and item.target_action_ref not in action_refs
            for item in assignments
        ):
            raise ValueError("source assignment target action is not in the program")
        material = {
            "abi_version": PROGRAM_ABI_VERSION,
            "orientation_ref": orientation_ref,
            "proposal_context_ref": proposal_context_ref,
            "action_abi_hash": ACTION_ABI_HASH,
            "actions": [action.as_dict() for action in action_tuple],
            "root_refs": list(roots),
            "mode_slot_ref": mode_slot_ref,
            "goal_refs": list(goals),
            "source_unit_refs": list(sources),
            "source_assignments": [item.as_dict() for item in assignments],
            "revision_pin": revision_pin.as_dict(),
        }
        return cls._from_canonical(
            stable_ref("program", material),
            orientation_ref=orientation_ref,
            proposal_context_ref=proposal_context_ref,
            actions=action_tuple,
            root_refs=roots,
            mode_slot_ref=mode_slot_ref,
            goal_refs=goals,
            source_unit_refs=sources,
            source_assignments=assignments,
            revision_pin=revision_pin,
        )

    @property
    def action_abi_hash(self) -> str:
        return ACTION_ABI_HASH

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": PROGRAM_ABI_VERSION,
            "program_ref": self.program_ref,
            "orientation_ref": self.orientation_ref,
            "proposal_context_ref": self.proposal_context_ref,
            "action_abi_hash": ACTION_ABI_HASH,
            "actions": [action.as_dict() for action in self.actions],
            "root_refs": list(self.root_refs),
            "mode_slot_ref": self.mode_slot_ref,
            "goal_refs": list(self.goal_refs),
            "source_unit_refs": list(self.source_unit_refs),
            "source_assignments": [item.as_dict() for item in self.source_assignments],
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticSwitchProgram":
        _exact_fields(
            data,
            frozenset(
                {
                    "abi_version", "program_ref", "orientation_ref", "proposal_context_ref",
                    "action_abi_hash", "actions", "root_refs", "mode_slot_ref",
                    "goal_refs", "source_unit_refs", "source_assignments", "revision_pin",
                }
            ),
            "SemanticSwitchProgram",
        )
        abi_version = data["abi_version"]
        if type(abi_version) is not int or abi_version != PROGRAM_ABI_VERSION:
            raise ValueError("unsupported Semantic Switch Program ABI")
        if data["action_abi_hash"] != ACTION_ABI_HASH:
            raise ValueError("action_abi_hash mismatch")
        pin_data = data["revision_pin"]
        if not isinstance(pin_data, Mapping):
            raise ValueError("revision_pin must be an object")
        program = cls.create(
            orientation_ref=_required(data["orientation_ref"], "orientation_ref"),
            proposal_context_ref=_required(
                data["proposal_context_ref"], "proposal_context_ref"
            ),
            actions=(
                ProgramAction.from_dict(item)
                for item in _wire_list(data["actions"], "actions")
            ),
            root_refs=(
                _required(item, "root_ref")
                for item in _wire_list(data["root_refs"], "root_refs")
            ),
            mode_slot_ref=_required(data["mode_slot_ref"], "mode_slot_ref"),
            goal_refs=(
                _required(item, "goal_ref")
                for item in _wire_list(data["goal_refs"], "goal_refs")
            ),
            source_unit_refs=(
                _required(item, "source_unit_ref")
                for item in _wire_list(data["source_unit_refs"], "source_unit_refs")
            ),
            source_assignments=(
                SourceAssignment.from_dict(item)
                for item in _wire_list(data["source_assignments"], "source_assignments")
            ),
            revision_pin=RevisionPin.from_dict(pin_data),
        )
        if data["program_ref"] != program.program_ref:
            raise ValueError("SemanticSwitchProgram ref mismatch")
        if program.as_dict() != dict(data):
            raise ValueError("non-canonical SemanticSwitchProgram encoding")
        return program