"""Source Coverage ABI 2: exact context-to-program assignment verification.

Coverage independently reconstructs source geometry, contribution type and
residual criticality from the exact Proposal Context.  It validates only; it
never compiles, repairs, or manufactures semantic-expression structure.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .config import RuntimeConfig
from .persistence import RevisionPin
from .proposal_context import ProposalContext
from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment


COVERAGE_ABI_VERSION = 2
_RELEASE = RuntimeConfig.release()
_MAX_UNITS = _RELEASE.max_input_tokens
_MAX_ACTIONS = _RELEASE.max_applications * 8 + 16
_MAX_ERRORS = _MAX_ACTIONS * _MAX_UNITS + _MAX_ACTIONS * 8 + _MAX_UNITS * 24 + 128
_MAX_REF = 256
_KINDS = frozenset(
    {
        "anchor",
        "predicate",
        "binder",
        "reference",
        "scope",
        "discourse",
        "connector",
        "qualifier",
        "literal",
        "open_variable",
    }
)
_ALWAYS_CRITICAL = frozenset(
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
_COMPATIBLE_ASSIGNMENTS = frozenset(
    {
        ("predicate", "predicate", "instantiate_operator"),
        ("anchor", "role", "bind_role"),
        ("literal", "role", "bind_role"),
        ("qualifier", "qualifier", "bind_role"),
        ("reference", "reference", "bind_reference"),
        ("scope", "scope", "attach_scope"),
        ("connector", "connector", "bind_nested_application"),
        ("discourse", "discourse", "select_mode"),
        ("discourse", "discourse", "bind_nested_application"),
        ("discourse", "discourse", "propose_transition"),
        ("open_variable", "role", "project_variable"),
        ("binder", "role", "project_variable"),
    }
)
_ROLE_ASSIGNMENT_KINDS = frozenset({"role", "reference", "qualifier"})

__all__ = [
    "COVERAGE_ABI_VERSION",
    "CoverageError",
    "CriticalResidual",
    "CoverageReceipt",
    "CoverageVerifier",
]


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_REF:
        raise ValueError(f"{field} must be a bounded non-empty string")
    return value


def _optional(value: object, field: str) -> str | None:
    return None if value is None else _required(value, field)


def _bounded(values: Iterable[Any], limit: int, field: str) -> tuple[Any, ...]:
    result = tuple(islice(iter(values), limit + 1))
    if len(result) > limit:
        raise ValueError(f"{field} exceeds the release bound")
    return result


def _exact(data: Mapping[str, Any], fields: frozenset[str], owner: str) -> None:
    if not isinstance(data, Mapping) or set(data) != fields:
        raise ValueError(f"{owner} fields must match the canonical schema exactly")


def _array(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    return value


@dataclass(frozen=True)
class CoverageError:
    code: str
    source_unit_ref: str | None = None
    contribution_slot_ref: str | None = None
    target_action_ref: str | None = None
    target_role_ref: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        _required(self.code, "coverage error code")
        _optional(self.source_unit_ref, "source_unit_ref")
        _optional(self.contribution_slot_ref, "contribution_slot_ref")
        _optional(self.target_action_ref, "target_action_ref")
        _optional(self.target_role_ref, "target_role_ref")
        if not isinstance(self.detail, str):
            raise ValueError("coverage error detail must be a string")

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "source_unit_ref": self.source_unit_ref,
            "contribution_slot_ref": self.contribution_slot_ref,
            "target_action_ref": self.target_action_ref,
            "target_role_ref": self.target_role_ref,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CoverageError":
        fields = frozenset(
            {
                "code",
                "source_unit_ref",
                "contribution_slot_ref",
                "target_action_ref",
                "target_role_ref",
                "detail",
            }
        )
        _exact(data, fields, "CoverageError")
        result = cls(
            code=_required(data["code"], "coverage error code"),
            source_unit_ref=_optional(data["source_unit_ref"], "source_unit_ref"),
            contribution_slot_ref=_optional(
                data["contribution_slot_ref"], "contribution_slot_ref"
            ),
            target_action_ref=_optional(data["target_action_ref"], "target_action_ref"),
            target_role_ref=_optional(data["target_role_ref"], "target_role_ref"),
            detail=data["detail"],
        )
        if result.as_dict() != dict(data):
            raise ValueError("non-canonical CoverageError encoding")
        return result


@dataclass(frozen=True)
class CriticalResidual:
    source_unit_ref: str
    contribution_slot_ref: str
    contribution_kind: str
    reason: str

    def __post_init__(self) -> None:
        _required(self.source_unit_ref, "source_unit_ref")
        _required(self.contribution_slot_ref, "contribution_slot_ref")
        if self.contribution_kind not in _KINDS:
            raise ValueError("invalid critical residual contribution kind")
        _required(self.reason, "critical residual reason")

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_unit_ref": self.source_unit_ref,
            "contribution_slot_ref": self.contribution_slot_ref,
            "contribution_kind": self.contribution_kind,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CriticalResidual":
        fields = frozenset(
            {"source_unit_ref", "contribution_slot_ref", "contribution_kind", "reason"}
        )
        _exact(data, fields, "CriticalResidual")
        result = cls(
            _required(data["source_unit_ref"], "source_unit_ref"),
            _required(data["contribution_slot_ref"], "contribution_slot_ref"),
            _required(data["contribution_kind"], "contribution_kind"),
            _required(data["reason"], "critical residual reason"),
        )
        if result.as_dict() != dict(data):
            raise ValueError("non-canonical CriticalResidual encoding")
        return result


@dataclass(frozen=True, init=False)
class CoverageReceipt:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use CoverageReceipt.create")

    coverage_receipt_ref: str
    program_ref: str
    proposal_context_ref: str
    source_unit_refs: tuple[str, ...]
    program_source_unit_refs: tuple[str, ...]
    assignments: tuple[SourceAssignment, ...]
    assigned_unit_refs: tuple[str, ...]
    residual_unit_refs: tuple[str, ...]
    duplicate_unit_refs: tuple[str, ...]
    missing_unit_refs: tuple[str, ...]
    extra_unit_refs: tuple[str, ...]
    critical_residuals: tuple[CriticalResidual, ...]
    errors: tuple[CoverageError, ...]
    executable: bool
    revision_pin: RevisionPin
    abi_version: int

    @classmethod
    def _canonical(cls, receipt_ref: str, **values: Any) -> "CoverageReceipt":
        result = object.__new__(cls)
        object.__setattr__(result, "coverage_receipt_ref", receipt_ref)
        for field, value in values.items():
            object.__setattr__(result, field, value)
        object.__setattr__(result, "abi_version", COVERAGE_ABI_VERSION)
        return result

    @classmethod
    def create(
        cls,
        *,
        program_ref: str,
        proposal_context_ref: str,
        source_unit_refs: Iterable[str],
        program_source_unit_refs: Iterable[str],
        assignments: Iterable[SourceAssignment],
        assigned_unit_refs: Iterable[str],
        residual_unit_refs: Iterable[str],
        duplicate_unit_refs: Iterable[str],
        missing_unit_refs: Iterable[str],
        extra_unit_refs: Iterable[str],
        critical_residuals: Iterable[CriticalResidual],
        errors: Iterable[CoverageError],
        executable: bool,
        revision_pin: RevisionPin,
    ) -> "CoverageReceipt":
        program_ref = _required(program_ref, "program_ref")
        proposal_context_ref = _required(proposal_context_ref, "proposal_context_ref")
        if not isinstance(revision_pin, RevisionPin):
            raise ValueError("revision_pin must be RevisionPin")
        if not isinstance(executable, bool):
            raise ValueError("executable must be boolean")
        sources = _bounded(source_unit_refs, _MAX_UNITS, "source units")
        program_sources = _bounded(
            program_source_unit_refs, _MAX_UNITS * 2, "program source units"
        )
        rows = _bounded(assignments, _MAX_UNITS * 2, "coverage assignments")
        for row in rows:
            if not isinstance(row, SourceAssignment):
                raise ValueError("assignments must contain SourceAssignment values")
            SourceAssignment.from_dict(row.as_dict())
        partitions = tuple(
            _bounded(values, _MAX_UNITS * 2, field)
            for values, field in (
                (assigned_unit_refs, "assigned units"),
                (residual_unit_refs, "residual units"),
                (duplicate_unit_refs, "duplicate units"),
                (missing_unit_refs, "missing units"),
                (extra_unit_refs, "extra units"),
            )
        )
        for values in (sources, program_sources, *partitions):
            for value in values:
                _required(value, "source_unit_ref")
        critical = _bounded(critical_residuals, _MAX_UNITS, "critical residuals")
        failures = _bounded(errors, _MAX_ERRORS, "coverage errors")
        if any(not isinstance(row, CriticalResidual) for row in critical):
            raise ValueError("invalid critical residual")
        if any(not isinstance(row, CoverageError) for row in failures):
            raise ValueError("invalid coverage error")
        if len(sources) != len(set(sources)):
            raise ValueError("duplicate source_unit_refs")
        for values, label in zip(
            partitions,
            ("assigned", "residual", "duplicate", "missing", "extra"),
            strict=True,
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} partition ref")
        if set(partitions[0]) & set(partitions[1]):
            raise ValueError("assigned and residual partitions overlap")

        counts = Counter(row.source_unit_ref for row in rows)
        source_set = set(sources)
        expected_assigned = tuple(
            row.source_unit_ref
            for row in rows
            if (
                row.source_unit_ref in source_set
                and counts[row.source_unit_ref] == 1
                and row.assignment_kind != "residual"
            )
        )
        expected_residual = tuple(
            row.source_unit_ref
            for row in rows
            if (
                row.source_unit_ref in source_set
                and counts[row.source_unit_ref] == 1
                and row.assignment_kind == "residual"
            )
        )
        expected_duplicate = tuple(
            dict.fromkeys(
                row.source_unit_ref for row in rows if counts[row.source_unit_ref] > 1
            )
        )
        expected_missing = tuple(ref for ref in sources if counts[ref] == 0)
        expected_extra = tuple(
            dict.fromkeys(
                ref
                for ref in (*program_sources, *(row.source_unit_ref for row in rows))
                if ref not in source_set
            )
        )
        expected_partitions = (
            expected_assigned,
            expected_residual,
            expected_duplicate,
            expected_missing,
            expected_extra,
        )
        for actual, expected, label in zip(
            partitions,
            expected_partitions,
            ("assigned", "residual", "duplicate", "missing", "extra"),
            strict=True,
        ):
            if actual != expected:
                raise ValueError(
                    f"{label} partition is inconsistent with retained content"
                )
        overflow_evidence = any(
            row.code == "coverage_error_overflow" for row in failures
        )

        def has_error(code: str, source_ref: str | None = None) -> bool:
            return overflow_evidence or any(
                row.code == code
                and (source_ref is None or row.source_unit_ref == source_ref)
                for row in failures
            )

        program_counts = Counter(program_sources)
        program_set = set(program_sources)
        for ref in sources:
            if ref not in program_set and not has_error("missing_source_unit", ref):
                raise ValueError(
                    "missing program source requires retained error evidence"
                )
        for ref in program_sources:
            if ref not in source_set and not has_error("extra_source_unit", ref):
                raise ValueError(
                    "extra program source requires retained error evidence"
                )
        for ref, count in program_counts.items():
            if count > 1 and not has_error("duplicate_program_source_unit", ref):
                raise ValueError(
                    "duplicate program source requires retained error evidence"
                )
        if (
            len(program_sources) == len(program_set)
            and program_set == source_set
            and program_sources != sources
            and not has_error("program_source_order_mismatch")
        ):
            raise ValueError("program source order requires retained error evidence")
        for ref in expected_duplicate:
            if not has_error("duplicate_source_assignment", ref):
                raise ValueError(
                    "duplicate assignment requires retained error evidence"
                )
        for ref in expected_missing:
            if not has_error("missing_source_assignment", ref):
                raise ValueError("missing assignment requires retained error evidence")
        assignment_sources = {row.source_unit_ref for row in rows}
        for ref in expected_extra:
            if ref in assignment_sources and not has_error(
                "extra_source_assignment", ref
            ):
                raise ValueError("extra assignment requires retained error evidence")
        should_execute = not failures and not critical
        if executable != should_execute:
            raise ValueError(
                "executable is inconsistent with retained failure evidence"
            )
        material = {
            "abi_version": COVERAGE_ABI_VERSION,
            "program_ref": program_ref,
            "proposal_context_ref": proposal_context_ref,
            "source_unit_refs": list(sources),
            "program_source_unit_refs": list(program_sources),
            "assignments": [row.as_dict() for row in rows],
            "assigned_unit_refs": list(partitions[0]),
            "residual_unit_refs": list(partitions[1]),
            "duplicate_unit_refs": list(partitions[2]),
            "missing_unit_refs": list(partitions[3]),
            "extra_unit_refs": list(partitions[4]),
            "critical_residuals": [row.as_dict() for row in critical],
            "errors": [row.as_dict() for row in failures],
            "executable": executable,
            "revision_pin": revision_pin.as_dict(),
        }
        return cls._canonical(
            stable_ref("coverage_receipt", material),
            program_ref=program_ref,
            proposal_context_ref=proposal_context_ref,
            source_unit_refs=sources,
            program_source_unit_refs=program_sources,
            assignments=rows,
            assigned_unit_refs=partitions[0],
            residual_unit_refs=partitions[1],
            duplicate_unit_refs=partitions[2],
            missing_unit_refs=partitions[3],
            extra_unit_refs=partitions[4],
            critical_residuals=critical,
            errors=failures,
            executable=executable,
            revision_pin=revision_pin,
        )

    @property
    def coverage_hash(self) -> str:
        return self.coverage_receipt_ref

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "coverage_receipt_ref": self.coverage_receipt_ref,
            "program_ref": self.program_ref,
            "proposal_context_ref": self.proposal_context_ref,
            "source_unit_refs": list(self.source_unit_refs),
            "program_source_unit_refs": list(self.program_source_unit_refs),
            "assignments": [row.as_dict() for row in self.assignments],
            "assigned_unit_refs": list(self.assigned_unit_refs),
            "residual_unit_refs": list(self.residual_unit_refs),
            "duplicate_unit_refs": list(self.duplicate_unit_refs),
            "missing_unit_refs": list(self.missing_unit_refs),
            "extra_unit_refs": list(self.extra_unit_refs),
            "critical_residuals": [row.as_dict() for row in self.critical_residuals],
            "errors": [row.as_dict() for row in self.errors],
            "executable": self.executable,
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CoverageReceipt":
        fields = frozenset(
            {
                "abi_version",
                "coverage_receipt_ref",
                "program_ref",
                "proposal_context_ref",
                "source_unit_refs",
                "program_source_unit_refs",
                "assignments",
                "assigned_unit_refs",
                "residual_unit_refs",
                "duplicate_unit_refs",
                "missing_unit_refs",
                "extra_unit_refs",
                "critical_residuals",
                "errors",
                "executable",
                "revision_pin",
            }
        )
        _exact(data, fields, "CoverageReceipt")
        if type(data["abi_version"]) is not int or data["abi_version"] != 2:
            raise ValueError("unsupported Source Coverage ABI")
        pin = data["revision_pin"]
        if not isinstance(pin, Mapping):
            raise ValueError("revision_pin must be an object")
        result = cls.create(
            program_ref=_required(data["program_ref"], "program_ref"),
            proposal_context_ref=_required(
                data["proposal_context_ref"], "proposal_context_ref"
            ),
            source_unit_refs=_array(data["source_unit_refs"], "source_unit_refs"),
            program_source_unit_refs=_array(
                data["program_source_unit_refs"], "program_source_unit_refs"
            ),
            assignments=(
                SourceAssignment.from_dict(row)
                for row in _array(data["assignments"], "assignments")
            ),
            assigned_unit_refs=_array(data["assigned_unit_refs"], "assigned_unit_refs"),
            residual_unit_refs=_array(data["residual_unit_refs"], "residual_unit_refs"),
            duplicate_unit_refs=_array(
                data["duplicate_unit_refs"], "duplicate_unit_refs"
            ),
            missing_unit_refs=_array(data["missing_unit_refs"], "missing_unit_refs"),
            extra_unit_refs=_array(data["extra_unit_refs"], "extra_unit_refs"),
            critical_residuals=(
                CriticalResidual.from_dict(row)
                for row in _array(data["critical_residuals"], "critical_residuals")
            ),
            errors=(
                CoverageError.from_dict(row) for row in _array(data["errors"], "errors")
            ),
            executable=data["executable"],
            revision_pin=RevisionPin.from_dict(pin),
        )
        if data["coverage_receipt_ref"] != result.coverage_receipt_ref:
            raise ValueError("CoverageReceipt ref mismatch")
        if result.as_dict() != dict(data):
            raise ValueError("non-canonical CoverageReceipt encoding")
        return result


class CoverageVerifier:
    """Validate a Program ABI 2 candidate against its exact ProposalContext."""

    def __init__(self, config: Any | None = None) -> None:
        self._limit = getattr(config or _RELEASE, "max_input_tokens", _MAX_UNITS)

    def verify(
        self, context: ProposalContext, program: SemanticSwitchProgram
    ) -> CoverageReceipt:
        if type(context) is not ProposalContext:
            raise TypeError("context must be an exact ProposalContext")
        if type(program) is not SemanticSwitchProgram:
            raise TypeError("program must be a SemanticSwitchProgram")
        errors: list[CoverageError] = []
        overflowed = False

        def report(code: str, *, detail: str = "", **refs: str | None) -> None:
            nonlocal overflowed
            error = CoverageError(code=code, detail=detail, **refs)
            if len(errors) < _MAX_ERRORS:
                errors.append(error)
                return
            if overflowed:
                return
            overflowed = True
            overflow = CoverageError(
                code="coverage_error_overflow",
                detail="complete diagnostics exceeded the defensive receipt bound",
            )
            if errors:
                errors[-1] = overflow
            else:
                errors.append(overflow)

        context_ref = context.context_ref
        expected = context.source_unit_refs
        actual = tuple(program.source_unit_refs)
        if len(expected) > self._limit:
            report("context_source_bound_exceeded")
        if program.proposal_context_ref != context_ref:
            report("proposal_context_mismatch")
        context_pin = context.revision_pin
        if context_pin != program.revision_pin:
            report("revision_pin_mismatch")
        expected_set, actual_set = set(expected), set(actual)
        for ref in expected:
            if ref not in actual_set:
                report("missing_source_unit", source_unit_ref=ref)
        for ref in actual:
            if ref not in expected_set:
                report("extra_source_unit", source_unit_ref=ref)
        for ref, count in Counter(actual).items():
            if count > 1:
                report("duplicate_program_source_unit", source_unit_ref=ref)
        if (
            len(actual) == len(actual_set)
            and actual_set == expected_set
            and actual != expected
        ):
            report("program_source_order_mismatch")

        find_designation = context.designation
        mode_slot = context.mode_slot
        find_contribution = context.contribution
        frame_slot = context.frame
        reference_slot = context.reference
        scope_slot = context.scope
        link_slot = context.expression_link
        variable_slot = context.variable
        transition_slot = context.transition
        residual_for_source = context.residual_for_source
        find_residual = context.residual

        contributions_for_source = context.contributions_for_source

        for residual_row in context.residual_evidence:
            conflicting = contributions_for_source(residual_row.source_unit_ref)
            if conflicting:
                report(
                    "context_residual_contribution_conflict",
                    source_unit_ref=residual_row.source_unit_ref,
                    contribution_slot_ref=conflicting[0].slot_ref,
                    detail=",".join(row.kind for row in conflicting),
                )
        actions = tuple(program.actions)
        action_by_ref: dict[str, ProgramAction] = {
            row.action_ref: row for row in actions
        }
        if len(action_by_ref) != len(actions):
            report("duplicate_program_action")
        action_sources: dict[str, list[str]] = {}
        application_frame_by_local: dict[str, Any] = {}
        node_frame_by_local: dict[str, Any] = {}
        for action in actions:
            args = action.arguments
            action_common = {"target_action_ref": action.action_ref}
            if action.action_type == "select_context":
                if args[0] != context.context_ref:
                    report("action_context_pointer_mismatch", **action_common)
            elif action.action_type == "select_mode":
                if mode_slot(args[0]) is None:
                    report("unknown_mode_slot", **action_common)
            elif action.action_type == "select_designation":
                if find_designation(args[0]) is None:
                    report("unknown_designation_slot", **action_common)
            elif action.action_type == "instantiate_operator":
                frame = frame_slot(args[1])
                if frame is None:
                    report("unknown_application_frame", **action_common)
                else:
                    application_frame_by_local[args[0]] = frame
                    node_frame_by_local[args[0]] = frame
            elif action.action_type == "bind_role":
                frame = application_frame_by_local.get(args[0])
                contribution = find_contribution(args[2])
                if frame is None:
                    report("unknown_application_frame_owner", **action_common)
                else:
                    roles = {
                        frame.structural_role_ref,
                        *frame.required_roles,
                        *frame.optional_roles,
                        *(role for role, _ in frame.derived_role_targets),
                    }
                    if args[1] not in roles:
                        report(
                            "incompatible_target_role",
                            target_action_ref=action.action_ref,
                            target_role_ref=args[1],
                        )
                if contribution is None:
                    report(
                        "unknown_contribution_slot",
                        contribution_slot_ref=args[2],
                        **action_common,
                    )
                elif args[1] not in contribution.output_ports:
                    report(
                        "contribution_role_incompatible",
                        contribution_slot_ref=args[2],
                        target_role_ref=args[1],
                        **action_common,
                    )
            elif action.action_type == "bind_reference":
                frame = application_frame_by_local.get(args[0])
                reference = reference_slot(args[2])
                if frame is None:
                    report("unknown_application_frame_owner", **action_common)
                elif args[1] not in {
                    *frame.required_roles,
                    *frame.optional_roles,
                    *(role for role, _ in frame.derived_role_targets),
                }:
                    report(
                        "incompatible_target_role",
                        target_action_ref=action.action_ref,
                        target_role_ref=args[1],
                    )
                if reference is None:
                    report("unknown_reference_slot", **action_common)
                elif args[1] not in reference.compatible_roles:
                    report("reference_role_incompatible", **action_common)
            elif action.action_type == "bind_nested_application":
                if args[0] == "role":
                    parent_frame = node_frame_by_local.get(args[1])
                    if parent_frame is None:
                        report("unknown_nested_parent_frame", **action_common)
                    elif args[2] not in parent_frame.proposition_roles:
                        report(
                            "nested_role_not_proposition_role",
                            target_action_ref=action.action_ref,
                            target_role_ref=args[2],
                        )
                else:
                    link = link_slot(args[2])
                    if link is None:
                        report("unknown_expression_link_slot", **action_common)
                    else:
                        arity = len(args) - 3
                        if not link.min_arity <= arity <= link.max_arity:
                            report("expression_link_arity_mismatch", **action_common)
            elif action.action_type == "attach_scope":
                if scope_slot(args[1]) is None:
                    report("unknown_scope_slot", **action_common)
                operand_frame = node_frame_by_local.get(args[2])
                if operand_frame is not None:
                    node_frame_by_local[args[0]] = operand_frame
            elif action.action_type == "project_variable":
                variable = variable_slot(args[1])
                body_frame = node_frame_by_local.get(args[2])
                if variable is None:
                    report("unknown_variable_slot", **action_common)
                elif body_frame is None:
                    report("unknown_variable_body_frame", **action_common)
                else:
                    if variable.application_frame_ref != body_frame.slot_ref:
                        report("variable_body_frame_mismatch", **action_common)
                    if variable.role_ref not in {
                        *body_frame.required_roles,
                        *body_frame.optional_roles,
                    }:
                        report(
                            "variable_role_incompatible",
                            target_action_ref=action.action_ref,
                            target_role_ref=variable.role_ref,
                        )
                    node_frame_by_local[args[0]] = body_frame
            elif action.action_type == "propose_transition":
                transition = transition_slot(args[0])
                source_frame = application_frame_by_local.get(args[1])
                if transition is None:
                    report("unknown_transition_slot", **action_common)
                elif source_frame is None:
                    report("unknown_transition_source_frame", **action_common)
                else:
                    if transition.application_frame_ref != source_frame.slot_ref:
                        report("transition_frame_mismatch", **action_common)
                    if source_frame.operator_ref != "op:state":
                        report("transition_source_not_state", **action_common)

            for ref in action.source_unit_refs:
                action_sources.setdefault(ref, []).append(action.action_ref)
                if ref not in expected_set:
                    report(
                        "unknown_action_source_unit",
                        source_unit_ref=ref,
                        target_action_ref=action.action_ref,
                    )
        for ref, targets in action_sources.items():
            if len(targets) > 1:
                report(
                    "duplicate_action_source_consumption",
                    source_unit_ref=ref,
                    detail=",".join(targets),
                )
        assignments = tuple(program.source_assignments)
        counts = Counter(row.source_unit_ref for row in assignments)
        duplicate = tuple(
            dict.fromkeys(
                row.source_unit_ref
                for row in assignments
                if counts[row.source_unit_ref] > 1
            )
        )
        missing = tuple(ref for ref in expected if counts[ref] == 0)
        extra = tuple(
            dict.fromkeys(
                ref
                for ref in (*actual, *(row.source_unit_ref for row in assignments))
                if ref not in expected_set
            )
        )
        for ref in duplicate:
            report("duplicate_source_assignment", source_unit_ref=ref)
        for ref in missing:
            report("missing_source_assignment", source_unit_ref=ref)
        for ref in dict.fromkeys(row.source_unit_ref for row in assignments):
            if ref not in expected_set:
                report("extra_source_assignment", source_unit_ref=ref)

        critical: list[CriticalResidual] = []
        for row in assignments:
            common = {
                "source_unit_ref": row.source_unit_ref,
                "contribution_slot_ref": row.contribution_slot_ref,
                "target_action_ref": row.target_action_ref,
                "target_role_ref": row.target_role_ref,
            }
            if (
                row.assignment_kind not in _ROLE_ASSIGNMENT_KINDS
                and row.target_role_ref is not None
            ):
                report("irrelevant_target_role", **common)
            contribution = find_contribution(row.contribution_slot_ref)
            if row.assignment_kind == "residual":
                decision = find_residual(row.contribution_slot_ref)
                source_decision = residual_for_source(row.source_unit_ref)
                if decision is None:
                    report("unknown_residual_ref", **common)
                    continue
                if decision.source_unit_ref != row.source_unit_ref:
                    report("residual_source_geometry_mismatch", **common)
                if (
                    source_decision is None
                    or source_decision.residual_ref != decision.residual_ref
                ):
                    report("residual_pointer_mismatch", **common)

                conflicting = contributions_for_source(row.source_unit_ref)
                conflict_kind = next(
                    (
                        item.kind
                        for item in conflicting
                        if item.kind in _ALWAYS_CRITICAL
                    ),
                    None,
                )
                kind = conflict_kind or decision.contribution_kind
                is_critical = conflict_kind is not None or self._critical(
                    decision.contribution_kind, decision, None
                )
                reason = (
                    "conflicting critical contribution metadata"
                    if conflict_kind is not None
                    else decision.reason
                )
                if row.residual_kind != kind:
                    report("residual_kind_mismatch", **common)
                if row.critical != is_critical:
                    report("false_residual_criticality", **common)
                if action_sources.get(row.source_unit_ref):
                    report("residual_action_conflict", **common)
                if is_critical and kind in _KINDS:
                    critical.append(
                        CriticalResidual(
                            row.source_unit_ref,
                            row.contribution_slot_ref,
                            kind,
                            reason,
                        )
                    )
                continue

            if contribution is None:
                report("unknown_contribution_slot", **common)
                continue
            if row.source_unit_ref not in contribution.source_unit_refs:
                report("contribution_source_geometry_mismatch", **common)
            if residual_for_source(row.source_unit_ref) is not None:
                report("context_residual_consumed", **common)
            action = action_by_ref.get(row.target_action_ref or "")
            if action is None:
                report("unknown_target_action", **common)
                continue
            if row.source_unit_ref not in action.source_unit_refs:
                report("action_source_assignment_mismatch", **common)
            compatibility = (
                contribution.kind,
                row.assignment_kind,
                action.action_type,
            )
            if compatibility not in _COMPATIBLE_ASSIGNMENTS:
                if not any(
                    candidate[1:] == compatibility[1:]
                    for candidate in _COMPATIBLE_ASSIGNMENTS
                ):
                    report("incompatible_target_action", **common)
                else:
                    report("contribution_assignment_kind_mismatch", **common)
                continue
            if (
                action.action_type == "bind_nested_application"
                and action.arguments[0] != "link"
            ):
                report("incompatible_target_action", **common)
                continue
            self._check_pointer(
                row,
                contribution,
                action,
                report,
                find_designation,
                mode_slot,
                frame_slot,
                reference_slot,
                scope_slot,
                link_slot,
                variable_slot,
                transition_slot,
                application_frame_by_local,
            )
        unique_assignments = {
            row.source_unit_ref: row
            for row in assignments
            if counts[row.source_unit_ref] == 1
        }
        for ref, targets in action_sources.items():
            assignment = unique_assignments.get(ref)
            if assignment is None or assignment.target_action_ref not in targets:
                report(
                    "action_source_assignment_mismatch",
                    source_unit_ref=ref,
                    target_action_ref=targets[0],
                )
        # Duplicate assignments remain retained evidence, but a duplicated unit
        # cannot also appear in either successful disposition partition.
        assigned = [
            row.source_unit_ref
            for row in assignments
            if (
                row.source_unit_ref in expected_set
                and counts[row.source_unit_ref] == 1
                and row.assignment_kind != "residual"
            )
        ]
        residual = [
            row.source_unit_ref
            for row in assignments
            if (
                row.source_unit_ref in expected_set
                and counts[row.source_unit_ref] == 1
                and row.assignment_kind == "residual"
            )
        ]
        return CoverageReceipt.create(
            program_ref=program.program_ref,
            proposal_context_ref=context_ref,
            source_unit_refs=expected,
            program_source_unit_refs=actual,
            assignments=assignments,
            assigned_unit_refs=assigned,
            residual_unit_refs=residual,
            duplicate_unit_refs=duplicate,
            missing_unit_refs=missing,
            extra_unit_refs=extra,
            critical_residuals=critical,
            errors=errors,
            executable=not errors and not critical,
            revision_pin=program.revision_pin,
        )

    @staticmethod
    def _critical(kind: Any, decision: Any, contribution: Any) -> bool:
        if kind in _ALWAYS_CRITICAL:
            return True
        if decision is not None:
            return getattr(decision, "critical", None) is True
        return any(
            key in {"critical", "residual_critical", "construction_critical"}
            and value == "true"
            for key, value in tuple(getattr(contribution, "constraints", ()))
        )

    @staticmethod
    def _check_pointer(
        row: SourceAssignment,
        contribution: Any,
        action: ProgramAction,
        report: Any,
        find_designation: Any,
        mode_slot: Any,
        frame_slot: Any,
        reference_slot: Any,
        scope_slot: Any,
        link_slot: Any,
        variable_slot: Any,
        transition_slot: Any,
        application_frame_by_local: Mapping[str, Any],
    ) -> None:
        common = {
            "source_unit_ref": row.source_unit_ref,
            "contribution_slot_ref": row.contribution_slot_ref,
            "target_action_ref": action.action_ref,
            "target_role_ref": row.target_role_ref,
        }
        args, kind = action.arguments, action.action_type

        def geometry(slot: Any, code: str) -> None:
            if slot is not None and row.source_unit_ref not in tuple(
                getattr(slot, "source_unit_refs", ())
            ):
                report(code, **common)

        if kind == "select_mode":
            mode = mode_slot(args[0])
            if mode is None:
                report("unknown_mode_slot", **common)
            else:
                geometry(mode, "mode_source_geometry_mismatch")
        elif kind == "select_designation":
            designation = find_designation(args[0])
            if designation is None:
                report("unknown_designation_slot", **common)
            else:
                geometry(designation, "designation_source_geometry_mismatch")
                if contribution.target_ref != designation.target_ref:
                    report("designation_target_mismatch", **common)
        elif kind == "bind_role":
            if row.target_role_ref != args[1]:
                report("incompatible_target_role", **common)
            if row.contribution_slot_ref != args[2]:
                report("action_contribution_pointer_mismatch", **common)
            if args[1] not in tuple(getattr(contribution, "output_ports", ())):
                report("contribution_role_incompatible", **common)
            frame = application_frame_by_local.get(args[0])
            if frame is None:
                report("unknown_application_frame_owner", **common)
            else:
                legal_roles = {
                    frame.structural_role_ref,
                    *frame.required_roles,
                    *frame.optional_roles,
                    *(role for role, _ in frame.derived_role_targets),
                }
                if args[1] not in legal_roles:
                    report("incompatible_target_role", **common)
        elif kind == "instantiate_operator":
            frame = frame_slot(args[1])
            if frame is None:
                report("unknown_application_frame", **common)
            else:
                geometry(frame, "application_frame_source_geometry_mismatch")
                if contribution.target_ref != frame.predicate_target_ref:
                    report("predicate_frame_mismatch", **common)
        elif kind == "bind_reference":
            reference = reference_slot(args[2])
            if row.target_role_ref != args[1]:
                report("incompatible_target_role", **common)
            frame = application_frame_by_local.get(args[0])
            if frame is None:
                report("unknown_application_frame_owner", **common)
            elif args[1] not in {
                *frame.required_roles,
                *frame.optional_roles,
                *(role for role, _ in frame.derived_role_targets),
            }:
                report("incompatible_target_role", **common)
            if reference is None:
                report("unknown_reference_slot", **common)
            else:
                geometry(reference, "reference_source_geometry_mismatch")
                if args[1] not in reference.compatible_roles:
                    report("reference_role_incompatible", **common)
                if contribution.target_ref is not None and (
                    contribution.target_ref != reference.target_ref
                ):
                    report("reference_target_mismatch", **common)
        elif kind == "attach_scope":
            scope = scope_slot(args[1])
            if scope is None:
                report("unknown_scope_slot", **common)
            else:
                geometry(scope, "scope_source_geometry_mismatch")
        elif kind == "bind_nested_application" and args[0] == "link":
            link = link_slot(args[2])
            if link is None:
                report("unknown_expression_link_slot", **common)
            else:
                geometry(link, "expression_link_source_geometry_mismatch")
        elif kind == "project_variable":
            variable = variable_slot(args[1])
            if variable is None:
                report("unknown_variable_slot", **common)
            else:
                geometry(variable, "variable_source_geometry_mismatch")
                if row.target_role_ref is not None and (
                    row.target_role_ref != variable.role_ref
                ):
                    report("incompatible_target_role", **common)
        elif kind == "propose_transition":
            transition = transition_slot(args[0])
            if transition is None:
                report("unknown_transition_slot", **common)
            else:
                geometry(transition, "transition_source_geometry_mismatch")
