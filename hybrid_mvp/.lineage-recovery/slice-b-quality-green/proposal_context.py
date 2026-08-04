"""Proposal Context ABI 1: bounded, current-cycle semantic proposal slots.

ORIENT constructs one immutable context and passes that exact value through
PROPOSE and VERIFY.  The context contains only grounded pointers and reviewed
structural slots.  It never contains a resolved application or semantic graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from math import isfinite
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, get_args

from .affordances import AffordanceProfile
from .authority import AtomRecord, EventSignature
from .canonical import stable_ref
from .config import RuntimeConfig
from .contributions import ContributionKind, SemanticContribution
from .cycle import Orientation, SemanticMode
from .forms import EvidencePacket, FormLattice
from .grounding import (
    DesignationCandidate,
    GroundedItem,
    GroundingResult,
    ReferenceRequirement,
)
from .persistence import RevisionPin

PROPOSAL_CONTEXT_ABI_VERSION = 1

_VALID_MODES = frozenset({"OBSERVE", "QUERY", "REQUEST", "SIMULATE"})
_VALID_CONTRIBUTION_KINDS = frozenset(get_args(ContributionKind))
_PERSISTENT_OPERATORS = frozenset(
    {"op:designation", "op:type", "op:relation", "op:state", "op:event"}
)
_SCOPE_TYPES = frozenset(
    {
        "scope:polarity",
        "scope:modality",
        "scope:tense",
        "scope:aspect",
        "scope:attribution",
        "scope:epistemic",
        "scope:quotation",
        "scope:simulation",
    }
)
_LINK_TYPES = frozenset(
    {
        "link:coordination",
        "link:conjunction",
        "link:disjunction",
        "link:condition",
        "link:cause",
        "link:purpose",
        "link:contrast",
        "link:sequence",
    }
)


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty string")
    return value


def _optional_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, name)


def _require_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")
    return value


def _require_strings(
    value: object,
    name: str,
    *,
    nonempty: bool = False,
    unique: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if nonempty and not value:
        raise ValueError(f"{name} must be non-empty")
    if any(not isinstance(item, str) or not item for item in value):
        raise TypeError(f"{name} must contain non-empty strings")
    if unique and len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    return value


def _require_pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, tuple) or any(
        not isinstance(row, tuple)
        or len(row) != 2
        or any(not isinstance(item, str) or not item for item in row)
        for row in value
    ):
        raise TypeError(f"{name} must contain string pairs")
    keys = tuple(row[0] for row in value)
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name} must not repeat keys")
    return value


def _strict_mapping(
    data: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} payload must be a mapping")
    if len(data) != len(expected):
        raise ValueError(f"{label} payload has wrong field count")
    actual = frozenset(data)
    if actual != expected:
        raise ValueError(
            f"{label} fields mismatch: "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _wire(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_wire(item) for item in value]
    return value


def _wire_string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise TypeError(f"{name} must be a list of non-empty strings")
    return tuple(value)


def _wire_pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or any(
        not isinstance(row, list)
        or len(row) != 2
        or any(not isinstance(item, str) or not item for item in row)
        for row in value
    ):
        raise TypeError(f"{name} must be a list of string pairs")
    return tuple((row[0], row[1]) for row in value)


class _ContentAddressedSlot:
    _REF_FIELD: ClassVar[str] = "slot_ref"
    _NAMESPACE: ClassVar[str]
    _TUPLE_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _PAIR_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def _material(self) -> dict[str, Any]:
        return {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{
                item.name: _wire(getattr(self, item.name))
                for item in fields(self)
                if item.init and item.name != self._REF_FIELD
            },
        }

    def _verify_ref(self) -> None:
        expected = stable_ref(self._NAMESPACE, self._material())
        if getattr(self, self._REF_FIELD) != expected:
            raise ValueError(f"{type(self).__name__} ref mismatch")

    def as_dict(self) -> dict[str, Any]:
        return {
            self._REF_FIELD: getattr(self, self._REF_FIELD),
            **{
                item.name: _wire(getattr(self, item.name))
                for item in fields(self)
                if item.init and item.name != self._REF_FIELD
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Any:
        names = frozenset(item.name for item in fields(cls) if item.init)
        _strict_mapping(data, names, cls.__name__)
        values: dict[str, Any] = {}
        for name in names - {cls._REF_FIELD}:
            if name in cls._PAIR_FIELDS:
                values[name] = _wire_pairs(data[name], name)
            elif name in cls._TUPLE_FIELDS:
                values[name] = _wire_string_tuple(data[name], name)
            else:
                values[name] = data[name]
        rebuilt = cls.create(**values)
        if data[cls._REF_FIELD] != getattr(rebuilt, cls._REF_FIELD):
            raise ValueError(f"{cls.__name__} ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError(f"non-canonical {cls.__name__} encoding")
        return rebuilt


@dataclass(frozen=True)
class DesignationSlot(_ContentAddressedSlot):
    slot_ref: str
    source_unit_refs: tuple[str, ...]
    target_ref: str
    target_kind: str
    score_q: int
    designation_fact_ref: str
    provenance_refs: tuple[str, ...]

    _NAMESPACE = "designation_slot"
    _TUPLE_FIELDS = frozenset({"source_unit_refs", "provenance_refs"})

    def __post_init__(self) -> None:
        _require_string(self.slot_ref, "slot_ref")
        _require_strings(self.source_unit_refs, "source_unit_refs", nonempty=True)
        _require_string(self.target_ref, "target_ref")
        _require_string(self.target_kind, "target_kind")
        _require_int(self.score_q, "score_q")
        _require_string(self.designation_fact_ref, "designation_fact_ref")
        _require_strings(self.provenance_refs, "provenance_refs", nonempty=True)
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        source_unit_refs: tuple[str, ...],
        target_ref: str,
        target_kind: str,
        score_q: int,
        designation_fact_ref: str,
        provenance_refs: tuple[str, ...],
    ) -> "DesignationSlot":
        values = locals()
        values.pop("cls")
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ContributionSlot(_ContentAddressedSlot):
    slot_ref: str
    contribution_ref: str
    kind: str
    source_unit_refs: tuple[str, ...]
    target_ref: str | None
    target_kind: str | None
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    constraints: tuple[tuple[str, str], ...]
    provenance_refs: tuple[str, ...]
    literal_value: str | None

    _NAMESPACE = "contribution_slot"
    _TUPLE_FIELDS = frozenset(
        {"source_unit_refs", "input_ports", "output_ports", "provenance_refs"}
    )
    _PAIR_FIELDS = frozenset({"constraints"})

    def __post_init__(self) -> None:
        _require_string(self.slot_ref, "slot_ref")
        _require_string(self.contribution_ref, "contribution_ref")
        if self.kind not in _VALID_CONTRIBUTION_KINDS:
            raise ValueError(f"invalid contribution kind: {self.kind}")
        _require_strings(self.source_unit_refs, "source_unit_refs")
        _optional_string(self.target_ref, "target_ref")
        _optional_string(self.target_kind, "target_kind")
        if (self.target_ref is None) != (self.target_kind is None):
            raise ValueError("target_ref and target_kind must be present together")
        _require_strings(self.input_ports, "input_ports")
        _require_strings(self.output_ports, "output_ports")
        _require_pairs(self.constraints, "constraints")
        _require_strings(self.provenance_refs, "provenance_refs")
        _optional_string(self.literal_value, "literal_value")
        if self.kind == "literal" and self.literal_value is None:
            raise ValueError("literal contribution requires literal_value")
        if self.kind != "literal" and self.literal_value is not None:
            raise ValueError("only literal contributions may carry literal_value")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        contribution_ref: str,
        kind: str,
        source_unit_refs: tuple[str, ...],
        target_ref: str | None,
        target_kind: str | None,
        input_ports: tuple[str, ...],
        output_ports: tuple[str, ...],
        constraints: tuple[tuple[str, str], ...],
        provenance_refs: tuple[str, ...] = (),
        literal_value: str | None = None,
    ) -> "ContributionSlot":
        values = {
            "contribution_ref": contribution_ref,
            "kind": kind,
            "source_unit_refs": source_unit_refs,
            "target_ref": target_ref,
            "target_kind": target_kind,
            "input_ports": input_ports,
            "output_ports": output_ports,
            "constraints": constraints,
            "provenance_refs": provenance_refs,
            "literal_value": literal_value,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ModeSlot(_ContentAddressedSlot):
    slot_ref: str
    mode: str
    source_unit_refs: tuple[str, ...]
    construction_ref: str | None
    requested_effect: str

    _NAMESPACE = "mode_slot"
    _TUPLE_FIELDS = frozenset({"source_unit_refs"})

    def __post_init__(self) -> None:
        _require_string(self.slot_ref, "slot_ref")
        if self.mode not in _VALID_MODES:
            raise ValueError(f"invalid mode: {self.mode}")
        _require_strings(self.source_unit_refs, "source_unit_refs")
        _optional_string(self.construction_ref, "construction_ref")
        _require_string(self.requested_effect, "requested_effect")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        mode: str,
        source_unit_refs: tuple[str, ...],
        construction_ref: str | None,
        requested_effect: str,
    ) -> "ModeSlot":
        values = {
            "mode": mode,
            "source_unit_refs": source_unit_refs,
            "construction_ref": construction_ref,
            "requested_effect": requested_effect,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ApplicationFrameSlot(_ContentAddressedSlot):
    slot_ref: str
    designation_slot_ref: str
    predicate_target_ref: str
    predicate_kind: str
    operator_ref: str
    structural_role_ref: str
    required_roles: tuple[str, ...]
    optional_roles: tuple[str, ...]
    proposition_roles: tuple[str, ...]
    source_unit_refs: tuple[str, ...]
    derived_role_targets: tuple[tuple[str, str], ...]
    affordance_frame_ref: str | None
    provenance_refs: tuple[str, ...]

    _NAMESPACE = "application_frame_slot"
    _TUPLE_FIELDS = frozenset(
        {
            "required_roles",
            "optional_roles",
            "proposition_roles",
            "source_unit_refs",
            "provenance_refs",
        }
    )
    _PAIR_FIELDS = frozenset({"derived_role_targets"})

    def __post_init__(self) -> None:
        for name in (
            "slot_ref",
            "designation_slot_ref",
            "predicate_target_ref",
            "predicate_kind",
            "structural_role_ref",
        ):
            _require_string(getattr(self, name), name)
        if self.operator_ref not in _PERSISTENT_OPERATORS:
            raise ValueError(f"invalid persistent operator: {self.operator_ref}")
        required = _require_strings(self.required_roles, "required_roles")
        optional = _require_strings(self.optional_roles, "optional_roles")
        proposition = _require_strings(self.proposition_roles, "proposition_roles")
        if set(required) & set(optional):
            raise ValueError("required and optional roles must be disjoint")
        if not set(proposition) <= set(required) | set(optional):
            raise ValueError("proposition roles must be declared roles")
        _require_strings(self.source_unit_refs, "source_unit_refs", nonempty=True)
        _require_pairs(self.derived_role_targets, "derived_role_targets")
        _optional_string(self.affordance_frame_ref, "affordance_frame_ref")
        provenance = _require_strings(
            self.provenance_refs, "provenance_refs", nonempty=True
        )
        if (
            self.affordance_frame_ref is not None
            and self.affordance_frame_ref not in provenance
        ):
            raise ValueError("reviewed affordance frame must occur in provenance")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        designation_slot_ref: str,
        predicate_target_ref: str,
        predicate_kind: str,
        operator_ref: str,
        structural_role_ref: str,
        required_roles: tuple[str, ...],
        optional_roles: tuple[str, ...],
        proposition_roles: tuple[str, ...],
        source_unit_refs: tuple[str, ...],
        derived_role_targets: tuple[tuple[str, str], ...],
        affordance_frame_ref: str | None,
        provenance_refs: tuple[str, ...],
    ) -> "ApplicationFrameSlot":
        values = {
            "designation_slot_ref": designation_slot_ref,
            "predicate_target_ref": predicate_target_ref,
            "predicate_kind": predicate_kind,
            "operator_ref": operator_ref,
            "structural_role_ref": structural_role_ref,
            "required_roles": required_roles,
            "optional_roles": optional_roles,
            "proposition_roles": proposition_roles,
            "source_unit_refs": source_unit_refs,
            "derived_role_targets": derived_role_targets,
            "affordance_frame_ref": affordance_frame_ref,
            "provenance_refs": provenance_refs,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{key: _wire(value) for key, value in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ReferenceSlot(_ContentAddressedSlot):
    slot_ref: str
    target_ref: str
    target_kind: str
    source_unit_refs: tuple[str, ...]
    resolution_kind: str
    compatible_roles: tuple[str, ...]
    score_q: int
    provenance_refs: tuple[str, ...]

    _NAMESPACE = "reference_slot"
    _TUPLE_FIELDS = frozenset(
        {"source_unit_refs", "compatible_roles", "provenance_refs"}
    )

    def __post_init__(self) -> None:
        for name in ("slot_ref", "target_ref", "target_kind", "resolution_kind"):
            _require_string(getattr(self, name), name)
        _require_strings(self.source_unit_refs, "source_unit_refs")
        _require_strings(self.compatible_roles, "compatible_roles", nonempty=True)
        _require_int(self.score_q, "score_q")
        _require_strings(self.provenance_refs, "provenance_refs", nonempty=True)
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        target_ref: str,
        target_kind: str,
        source_unit_refs: tuple[str, ...],
        resolution_kind: str,
        compatible_roles: tuple[str, ...],
        score_q: int,
        provenance_refs: tuple[str, ...],
    ) -> "ReferenceSlot":
        values = {
            "target_ref": target_ref,
            "target_kind": target_kind,
            "source_unit_refs": source_unit_refs,
            "resolution_kind": resolution_kind,
            "compatible_roles": compatible_roles,
            "score_q": score_q,
            "provenance_refs": provenance_refs,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ScopeSlot(_ContentAddressedSlot):
    slot_ref: str
    operator_type: str
    value_ref: str
    source_unit_refs: tuple[str, ...]
    construction_ref: str | None

    _NAMESPACE = "scope_slot"
    _TUPLE_FIELDS = frozenset({"source_unit_refs"})

    def __post_init__(self) -> None:
        _require_string(self.slot_ref, "slot_ref")
        if self.operator_type == "scope:negation":
            raise ValueError("negation must be normalized to polarity")
        if self.operator_type not in _SCOPE_TYPES:
            raise ValueError(f"invalid scope operator: {self.operator_type}")
        _require_string(self.value_ref, "value_ref")
        _require_strings(self.source_unit_refs, "source_unit_refs")
        _optional_string(self.construction_ref, "construction_ref")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        operator_type: str,
        value_ref: str,
        source_unit_refs: tuple[str, ...],
        construction_ref: str | None,
    ) -> "ScopeSlot":
        values = {
            "operator_type": operator_type,
            "value_ref": value_ref,
            "source_unit_refs": source_unit_refs,
            "construction_ref": construction_ref,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ExpressionLinkSlot(_ContentAddressedSlot):
    slot_ref: str
    link_type: str
    commutative: bool
    min_arity: int
    max_arity: int
    source_unit_refs: tuple[str, ...]
    construction_ref: str | None

    _NAMESPACE = "expression_link_slot"
    _TUPLE_FIELDS = frozenset({"source_unit_refs"})

    def __post_init__(self) -> None:
        _require_string(self.slot_ref, "slot_ref")
        if self.link_type not in _LINK_TYPES:
            raise ValueError(f"invalid expression link: {self.link_type}")
        _require_bool(self.commutative, "commutative")
        _require_int(self.min_arity, "min_arity", minimum=1)
        _require_int(self.max_arity, "max_arity", minimum=1)
        if self.max_arity < self.min_arity:
            raise ValueError("max_arity must not be less than min_arity")
        _require_strings(self.source_unit_refs, "source_unit_refs")
        _optional_string(self.construction_ref, "construction_ref")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        link_type: str,
        commutative: bool,
        min_arity: int,
        max_arity: int,
        source_unit_refs: tuple[str, ...],
        construction_ref: str | None,
    ) -> "ExpressionLinkSlot":
        values = {
            "link_type": link_type,
            "commutative": commutative,
            "min_arity": min_arity,
            "max_arity": max_arity,
            "source_unit_refs": source_unit_refs,
            "construction_ref": construction_ref,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class VariableSlot(_ContentAddressedSlot):
    slot_ref: str
    application_frame_ref: str
    role_ref: str
    required_kinds: tuple[str, ...]
    source_unit_refs: tuple[str, ...]
    construction_ref: str | None

    _NAMESPACE = "variable_slot"
    _TUPLE_FIELDS = frozenset({"required_kinds", "source_unit_refs"})

    def __post_init__(self) -> None:
        for name in ("slot_ref", "application_frame_ref", "role_ref"):
            _require_string(getattr(self, name), name)
        if not self.role_ref.startswith("role:"):
            raise ValueError("role_ref must start with 'role:'")
        _require_strings(self.required_kinds, "required_kinds", nonempty=True)
        _require_strings(self.source_unit_refs, "source_unit_refs")
        _optional_string(self.construction_ref, "construction_ref")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        application_frame_ref: str,
        role_ref: str,
        required_kinds: tuple[str, ...],
        source_unit_refs: tuple[str, ...],
        construction_ref: str | None,
    ) -> "VariableSlot":
        values = {
            "application_frame_ref": application_frame_ref,
            "role_ref": role_ref,
            "required_kinds": required_kinds,
            "source_unit_refs": source_unit_refs,
            "construction_ref": construction_ref,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class TransitionSlot(_ContentAddressedSlot):
    slot_ref: str
    application_frame_ref: str
    event_type_ref: str
    compatible_modes: tuple[str, ...]
    required_roles: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    required_permissions: tuple[str, ...]
    adapter_ref: str | None
    source_unit_refs: tuple[str, ...]

    _NAMESPACE = "transition_slot"
    _TUPLE_FIELDS = frozenset(
        {
            "compatible_modes",
            "required_roles",
            "required_capabilities",
            "required_permissions",
            "source_unit_refs",
        }
    )

    def __post_init__(self) -> None:
        for name in ("slot_ref", "application_frame_ref", "event_type_ref"):
            _require_string(getattr(self, name), name)
        modes = _require_strings(
            self.compatible_modes, "compatible_modes", nonempty=True
        )
        if any(mode not in _VALID_MODES for mode in modes):
            raise ValueError("transition contains invalid compatible mode")
        _require_strings(self.required_roles, "required_roles")
        _require_strings(self.required_capabilities, "required_capabilities")
        _require_strings(self.required_permissions, "required_permissions")
        _optional_string(self.adapter_ref, "adapter_ref")
        _require_strings(self.source_unit_refs, "source_unit_refs")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        application_frame_ref: str,
        event_type_ref: str,
        compatible_modes: tuple[str, ...],
        required_roles: tuple[str, ...],
        required_capabilities: tuple[str, ...],
        required_permissions: tuple[str, ...],
        adapter_ref: str | None,
        source_unit_refs: tuple[str, ...],
    ) -> "TransitionSlot":
        values = {
            "application_frame_ref": application_frame_ref,
            "event_type_ref": event_type_ref,
            "compatible_modes": compatible_modes,
            "required_roles": required_roles,
            "required_capabilities": required_capabilities,
            "required_permissions": required_permissions,
            "adapter_ref": adapter_ref,
            "source_unit_refs": source_unit_refs,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{k: _wire(v) for k, v in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)


@dataclass(frozen=True)
class ResidualEvidence(_ContentAddressedSlot):
    residual_ref: str
    source_unit_ref: str
    contribution_kind: str
    critical: bool
    reason: str

    _REF_FIELD = "residual_ref"
    _NAMESPACE = "residual_evidence"

    def __post_init__(self) -> None:
        _require_string(self.residual_ref, "residual_ref")
        _require_string(self.source_unit_ref, "source_unit_ref")
        if self.contribution_kind not in _VALID_CONTRIBUTION_KINDS:
            raise ValueError(f"invalid contribution kind: {self.contribution_kind}")
        _require_bool(self.critical, "critical")
        _require_string(self.reason, "reason")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        source_unit_ref: str,
        contribution_kind: str,
        critical: bool,
        reason: str,
    ) -> "ResidualEvidence":
        values = {
            "source_unit_ref": source_unit_ref,
            "contribution_kind": contribution_kind,
            "critical": critical,
            "reason": reason,
        }
        material = {"abi_version": PROPOSAL_CONTEXT_ABI_VERSION, **values}
        return cls(stable_ref(cls._NAMESPACE, material), **values)


Slot = (
    DesignationSlot
    | ContributionSlot
    | ModeSlot
    | ApplicationFrameSlot
    | ReferenceSlot
    | ScopeSlot
    | ExpressionLinkSlot
    | VariableSlot
    | TransitionSlot
)


@dataclass(frozen=True)
class ProposalContext:
    context_ref: str
    orientation_ref: str
    evidence_packet_ref: str
    form_lattice_ref: str
    grounding_ref: str
    designation_slots: tuple[DesignationSlot, ...]
    contribution_slots: tuple[ContributionSlot, ...]
    mode_slots: tuple[ModeSlot, ...]
    application_frames: tuple[ApplicationFrameSlot, ...]
    reference_slots: tuple[ReferenceSlot, ...]
    scope_slots: tuple[ScopeSlot, ...]
    expression_link_slots: tuple[ExpressionLinkSlot, ...]
    variable_slots: tuple[VariableSlot, ...]
    transition_slots: tuple[TransitionSlot, ...]
    residual_evidence: tuple[ResidualEvidence, ...]
    context_refs: tuple[str, ...]
    source_unit_refs: tuple[str, ...]
    source_unit_spans: tuple[tuple[str, int, int], ...]
    revision_pin: RevisionPin
    abi_version: int = PROPOSAL_CONTEXT_ABI_VERSION
    _designation_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _contribution_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _contributions_by_source: Mapping[str, tuple[int, ...]] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _mode_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _frame_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _frames_by_designation: Mapping[str, tuple[int, ...]] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _reference_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _scope_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _link_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _variable_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _transition_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _residual_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _residual_by_source: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _context_ref_set: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _source_span_by_ref: Mapping[str, int] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.abi_version) is not int
            or self.abi_version != PROPOSAL_CONTEXT_ABI_VERSION
        ):
            raise ValueError("unsupported Proposal Context ABI")
        for name in (
            "context_ref",
            "orientation_ref",
            "evidence_packet_ref",
            "form_lattice_ref",
            "grounding_ref",
        ):
            _require_string(getattr(self, name), name)
        if not isinstance(self.revision_pin, RevisionPin):
            raise TypeError("revision_pin must be RevisionPin")
        _validate_context(self, RuntimeConfig.release())
        expected = stable_ref("proposal_context", _context_material(self))
        if self.context_ref != expected:
            raise ValueError("ProposalContext ref mismatch")
        self._build_indexes()

    @classmethod
    def create(
        cls,
        *,
        orientation_ref: str,
        evidence_packet_ref: str,
        form_lattice_ref: str,
        grounding_ref: str,
        designation_slots: tuple[DesignationSlot, ...],
        contribution_slots: tuple[ContributionSlot, ...],
        mode_slots: tuple[ModeSlot, ...],
        application_frames: tuple[ApplicationFrameSlot, ...],
        reference_slots: tuple[ReferenceSlot, ...],
        scope_slots: tuple[ScopeSlot, ...],
        expression_link_slots: tuple[ExpressionLinkSlot, ...],
        variable_slots: tuple[VariableSlot, ...],
        transition_slots: tuple[TransitionSlot, ...],
        residual_evidence: tuple[ResidualEvidence, ...],
        context_refs: tuple[str, ...],
        source_unit_refs: tuple[str, ...],
        source_unit_spans: tuple[tuple[str, int, int], ...],
        revision_pin: RevisionPin,
        config: RuntimeConfig | None = None,
    ) -> "ProposalContext":
        if cls is not ProposalContext:
            raise TypeError("ProposalContext factories require exact ProposalContext")
        values = {
            "orientation_ref": orientation_ref,
            "evidence_packet_ref": evidence_packet_ref,
            "form_lattice_ref": form_lattice_ref,
            "grounding_ref": grounding_ref,
            "designation_slots": designation_slots,
            "contribution_slots": contribution_slots,
            "mode_slots": mode_slots,
            "application_frames": application_frames,
            "reference_slots": reference_slots,
            "scope_slots": scope_slots,
            "expression_link_slots": expression_link_slots,
            "variable_slots": variable_slots,
            "transition_slots": transition_slots,
            "residual_evidence": residual_evidence,
            "context_refs": context_refs,
            "source_unit_refs": source_unit_refs,
            "source_unit_spans": source_unit_spans,
            "revision_pin": revision_pin,
        }
        provisional = object.__new__(ProposalContext)
        for name, value in values.items():
            object.__setattr__(provisional, name, value)
        object.__setattr__(provisional, "abi_version", PROPOSAL_CONTEXT_ABI_VERSION)
        _validate_context(provisional, config or RuntimeConfig.release())
        context_ref = stable_ref("proposal_context", _context_material(provisional))
        return cls._from_checked(context_ref, values)

    @staticmethod
    def _from_checked(
        context_ref: str, values: Mapping[str, Any]
    ) -> "ProposalContext":
        value = object.__new__(ProposalContext)
        object.__setattr__(value, "context_ref", context_ref)
        for name, item in values.items():
            object.__setattr__(value, name, item)
        object.__setattr__(value, "abi_version", PROPOSAL_CONTEXT_ABI_VERSION)
        value._build_indexes()
        return value
    def _build_indexes(self) -> None:
        def index(
            rows: tuple[Any, ...], ref_field: str = "slot_ref"
        ) -> Mapping[str, int]:
            return MappingProxyType(
                {getattr(row, ref_field): position for position, row in enumerate(rows)}
            )

        object.__setattr__(self, "_designation_by_ref", index(self.designation_slots))
        object.__setattr__(self, "_contribution_by_ref", index(self.contribution_slots))
        contributions_by_source: dict[str, list[int]] = {}
        for position, contribution in enumerate(self.contribution_slots):
            for source_ref in contribution.source_unit_refs:
                contributions_by_source.setdefault(source_ref, []).append(position)
        object.__setattr__(
            self,
            "_contributions_by_source",
            MappingProxyType(
                {key: tuple(value) for key, value in contributions_by_source.items()}
            ),
        )
        object.__setattr__(self, "_mode_by_ref", index(self.mode_slots))
        object.__setattr__(self, "_frame_by_ref", index(self.application_frames))
        grouped: dict[str, list[int]] = {}
        for position, row in enumerate(self.application_frames):
            grouped.setdefault(row.designation_slot_ref, []).append(position)
        object.__setattr__(
            self,
            "_frames_by_designation",
            MappingProxyType({key: tuple(value) for key, value in grouped.items()}),
        )
        object.__setattr__(self, "_reference_by_ref", index(self.reference_slots))
        object.__setattr__(self, "_scope_by_ref", index(self.scope_slots))
        object.__setattr__(self, "_link_by_ref", index(self.expression_link_slots))
        object.__setattr__(self, "_variable_by_ref", index(self.variable_slots))
        object.__setattr__(self, "_transition_by_ref", index(self.transition_slots))
        object.__setattr__(
            self,
            "_residual_by_ref",
            index(self.residual_evidence, "residual_ref"),
        )
        object.__setattr__(
            self,
            "_residual_by_source",
            MappingProxyType(
                {
                    row.source_unit_ref: position
                    for position, row in enumerate(self.residual_evidence)
                }
            ),
        )
        object.__setattr__(
            self,
            "_context_ref_set",
            MappingProxyType(
                {ref: position for position, ref in enumerate(self.context_refs)}
            ),
        )
        object.__setattr__(
            self,
            "_source_span_by_ref",
            MappingProxyType(
                {
                    row[0]: position
                    for position, row in enumerate(self.source_unit_spans)
                }
            ),
        )

    @staticmethod
    def _indexed_row(
        rows: tuple[Any, ...],
        positions: Mapping[str, int],
        ref: str,
        *,
        ref_field: str = "slot_ref",
    ) -> Any | None:
        position = positions.get(ref)
        if position is None:
            return None
        if (
            isinstance(position, bool)
            or not isinstance(position, int)
            or position < 0
            or position >= len(rows)
        ):
            raise ValueError("ProposalContext derived index is incoherent")
        row = rows[position]
        if getattr(row, ref_field) != ref:
            raise ValueError("ProposalContext derived index is incoherent")
        return row

    def designation(self, slot_ref: str) -> DesignationSlot | None:
        return self._indexed_row(
            self.designation_slots, self._designation_by_ref, slot_ref
        )

    def contribution(self, slot_ref: str) -> ContributionSlot | None:
        return self._indexed_row(
            self.contribution_slots, self._contribution_by_ref, slot_ref
        )

    def contributions_for_source(
        self, source_unit_ref: str
    ) -> tuple[ContributionSlot, ...]:
        positions = self._contributions_by_source.get(source_unit_ref, ())
        rows: list[ContributionSlot] = []
        for position in positions:
            if (
                isinstance(position, bool)
                or not isinstance(position, int)
                or position < 0
                or position >= len(self.contribution_slots)
            ):
                raise ValueError("ProposalContext derived index is incoherent")
            row = self.contribution_slots[position]
            if source_unit_ref not in row.source_unit_refs:
                raise ValueError("ProposalContext derived index is incoherent")
            rows.append(row)
        return tuple(rows)

    def mode_slot(self, slot_ref: str) -> ModeSlot | None:
        return self._indexed_row(self.mode_slots, self._mode_by_ref, slot_ref)

    def frame(self, slot_ref: str) -> ApplicationFrameSlot | None:
        return self._indexed_row(self.application_frames, self._frame_by_ref, slot_ref)

    def frame_for_designation(self, slot_ref: str) -> tuple[ApplicationFrameSlot, ...]:
        positions = self._frames_by_designation.get(slot_ref, ())
        rows: list[ApplicationFrameSlot] = []
        for position in positions:
            if (
                isinstance(position, bool)
                or not isinstance(position, int)
                or position < 0
                or position >= len(self.application_frames)
            ):
                raise ValueError("ProposalContext derived index is incoherent")
            row = self.application_frames[position]
            if row.designation_slot_ref != slot_ref:
                raise ValueError("ProposalContext derived index is incoherent")
            rows.append(row)
        return tuple(rows)

    def reference(self, slot_ref: str) -> ReferenceSlot | None:
        return self._indexed_row(self.reference_slots, self._reference_by_ref, slot_ref)

    def scope(self, slot_ref: str) -> ScopeSlot | None:
        return self._indexed_row(self.scope_slots, self._scope_by_ref, slot_ref)

    def expression_link(self, slot_ref: str) -> ExpressionLinkSlot | None:
        return self._indexed_row(
            self.expression_link_slots, self._link_by_ref, slot_ref
        )

    def variable(self, slot_ref: str) -> VariableSlot | None:
        return self._indexed_row(self.variable_slots, self._variable_by_ref, slot_ref)

    def transition(self, slot_ref: str) -> TransitionSlot | None:
        return self._indexed_row(
            self.transition_slots, self._transition_by_ref, slot_ref
        )

    def residual(self, residual_ref: str) -> ResidualEvidence | None:
        return self._indexed_row(
            self.residual_evidence,
            self._residual_by_ref,
            residual_ref,
            ref_field="residual_ref",
        )

    def residual_for_source(self, source_unit_ref: str) -> ResidualEvidence | None:
        position = self._residual_by_source.get(source_unit_ref)
        if position is None:
            return None
        if (
            isinstance(position, bool)
            or not isinstance(position, int)
            or position < 0
            or position >= len(self.residual_evidence)
        ):
            raise ValueError("ProposalContext derived index is incoherent")
        row = self.residual_evidence[position]
        if row.source_unit_ref != source_unit_ref:
            raise ValueError("ProposalContext derived index is incoherent")
        return row

    def has_context_ref(self, context_ref: str) -> bool:
        position = self._context_ref_set.get(context_ref)
        if position is None:
            return False
        if (
            isinstance(position, bool)
            or not isinstance(position, int)
            or position < 0
            or position >= len(self.context_refs)
            or self.context_refs[position] != context_ref
        ):
            raise ValueError("ProposalContext derived index is incoherent")
        return True

    def source_span(self, unit_refs: tuple[str, ...]) -> tuple[int, int] | None:
        if not unit_refs:
            return None
        selected: list[tuple[int, int]] = []
        for ref in unit_refs:
            position = self._source_span_by_ref.get(ref)
            if position is None:
                return None
            if (
                isinstance(position, bool)
                or not isinstance(position, int)
                or position < 0
                or position >= len(self.source_unit_spans)
            ):
                raise ValueError("ProposalContext derived index is incoherent")
            row_ref, start, end = self.source_unit_spans[position]
            if row_ref != ref:
                raise ValueError("ProposalContext derived index is incoherent")
            selected.append((start, end))
        return min(row[0] for row in selected), max(row[1] for row in selected)

    @property
    def critical_residual_unit_refs(self) -> tuple[str, ...]:
        return tuple(
            row.source_unit_ref for row in self.residual_evidence if row.critical
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "context_ref": self.context_ref,
            "orientation_ref": self.orientation_ref,
            "evidence_packet_ref": self.evidence_packet_ref,
            "form_lattice_ref": self.form_lattice_ref,
            "grounding_ref": self.grounding_ref,
            "designation_slots": [row.as_dict() for row in self.designation_slots],
            "contribution_slots": [row.as_dict() for row in self.contribution_slots],
            "mode_slots": [row.as_dict() for row in self.mode_slots],
            "application_frames": [row.as_dict() for row in self.application_frames],
            "reference_slots": [row.as_dict() for row in self.reference_slots],
            "scope_slots": [row.as_dict() for row in self.scope_slots],
            "expression_link_slots": [
                row.as_dict() for row in self.expression_link_slots
            ],
            "variable_slots": [row.as_dict() for row in self.variable_slots],
            "transition_slots": [row.as_dict() for row in self.transition_slots],
            "residual_evidence": [row.as_dict() for row in self.residual_evidence],
            "context_refs": list(self.context_refs),
            "source_unit_refs": list(self.source_unit_refs),
            "source_unit_spans": [list(row) for row in self.source_unit_spans],
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProposalContext":
        if cls is not ProposalContext:
            raise TypeError("ProposalContext factories require exact ProposalContext")
        expected = frozenset(
            {
                "abi_version",
                "context_ref",
                "orientation_ref",
                "evidence_packet_ref",
                "form_lattice_ref",
                "grounding_ref",
                "designation_slots",
                "contribution_slots",
                "mode_slots",
                "application_frames",
                "reference_slots",
                "scope_slots",
                "expression_link_slots",
                "variable_slots",
                "transition_slots",
                "residual_evidence",
                "context_refs",
                "source_unit_refs",
                "source_unit_spans",
                "revision_pin",
            }
        )
        if type(data) is not dict:
            raise TypeError("ProposalContext payload must be an exact dict")
        if len(data) != len(expected):
            raise ValueError("ProposalContext payload has wrong field count")
        _strict_mapping(data, expected, "ProposalContext")
        if (
            type(data["abi_version"]) is not int
            or data["abi_version"] != PROPOSAL_CONTEXT_ABI_VERSION
        ):
            raise ValueError("unsupported Proposal Context ABI")

        config = RuntimeConfig.release()
        contribution_limit = config.max_input_tokens * (
            config.max_affordances_per_target * 2 + 1
        )
        row_specs = (
            ("designation_slots", DesignationSlot, config.max_orientation_alternatives),
            ("contribution_slots", ContributionSlot, contribution_limit),
            ("mode_slots", ModeSlot, config.max_orientation_alternatives),
            ("application_frames", ApplicationFrameSlot, config.max_orientation_alternatives),
            ("reference_slots", ReferenceSlot, config.max_orientation_alternatives),
            ("scope_slots", ScopeSlot, config.max_orientation_alternatives),
            ("expression_link_slots", ExpressionLinkSlot, config.max_orientation_alternatives),
            ("variable_slots", VariableSlot, config.max_orientation_alternatives),
            ("transition_slots", TransitionSlot, config.max_orientation_alternatives),
            ("residual_evidence", ResidualEvidence, config.max_input_tokens),
        )
        for name, _owner, limit in row_specs:
            value = data[name]
            if type(value) is not list:
                raise TypeError(f"{name} must be an exact list")
            if len(value) > limit:
                raise ValueError(f"{name} exceeds release bound")
            if any(type(item) is not dict for item in value):
                raise TypeError(f"{name} rows must be exact dicts")

        def bounded_strings(name: str, limit: int) -> tuple[str, ...]:
            value = data[name]
            if type(value) is not list:
                raise TypeError(f"{name} must be an exact list")
            if len(value) > limit:
                raise ValueError(f"{name} exceeds release bound")
            if any(type(item) is not str or not item for item in value):
                raise TypeError(f"{name} must contain non-empty strings")
            return tuple(value)

        context_refs = bounded_strings(
            "context_refs", config.max_orientation_alternatives
        )
        source_unit_refs = bounded_strings(
            "source_unit_refs", config.max_input_tokens
        )
        raw_spans = data["source_unit_spans"]
        if type(raw_spans) is not list:
            raise TypeError("source_unit_spans must be a list of triples")
        if len(raw_spans) > config.max_input_tokens:
            raise ValueError("source_unit_spans exceeds release bound")
        if any(type(row) is not list or len(row) != 3 for row in raw_spans):
            raise TypeError("source_unit_spans must be a list of triples")
        spans = tuple(tuple(row) for row in raw_spans)
        if type(data["revision_pin"]) is not dict:
            raise TypeError("revision_pin must be an exact dict")

        decoded_rows = {
            name: tuple(owner.from_dict(item) for item in data[name])
            for name, owner, _limit in row_specs
        }
        rebuilt = cls.create(
            orientation_ref=data["orientation_ref"],
            evidence_packet_ref=data["evidence_packet_ref"],
            form_lattice_ref=data["form_lattice_ref"],
            grounding_ref=data["grounding_ref"],
            designation_slots=decoded_rows["designation_slots"],
            contribution_slots=decoded_rows["contribution_slots"],
            mode_slots=decoded_rows["mode_slots"],
            application_frames=decoded_rows["application_frames"],
            reference_slots=decoded_rows["reference_slots"],
            scope_slots=decoded_rows["scope_slots"],
            expression_link_slots=decoded_rows["expression_link_slots"],
            variable_slots=decoded_rows["variable_slots"],
            transition_slots=decoded_rows["transition_slots"],
            residual_evidence=decoded_rows["residual_evidence"],
            context_refs=context_refs,
            source_unit_refs=source_unit_refs,
            source_unit_spans=spans,  # type: ignore[arg-type]
            revision_pin=RevisionPin.from_dict(data["revision_pin"]),
        )
        if data["context_ref"] != rebuilt.context_ref:
            raise ValueError("ProposalContext ref mismatch")
        if rebuilt.as_dict() != data:
            raise ValueError("non-canonical ProposalContext encoding")
        return rebuilt

class ProposalContextBuilder:
    """Build one bounded Proposal Context from already-owned cycle artifacts.

    The builder deliberately consumes an existing ``FormLattice``,
    ``GroundingResult`` and contribution tuple.  It never invokes a form
    resolver or grounder, so the current-cycle source cannot be tokenised a
    second time during proposal construction.
    """

    _CONTRIBUTIONS_PER_PROFILE = 2

    def __init__(
        self,
        authority: Any,
        affordance_index: Any,
        config: RuntimeConfig,
    ) -> None:
        self._authority = authority
        self._affordance_index = affordance_index
        self._config = config

    def build(
        self,
        *,
        orientation: Orientation,
        evidence: EvidencePacket,
        form_lattice: FormLattice,
        grounding_result: GroundingResult,
        contributions: tuple[SemanticContribution, ...],
    ) -> ProposalContext:
        unit_ref_set = _validate_builder_inputs(
            orientation,
            evidence,
            form_lattice,
            grounding_result,
            contributions,
            self._authority,
            self._affordance_index,
            self._config,
        )
        unit_by_ref = {row.unit_ref: row for row in form_lattice.units}
        source_spans = tuple(
            (row.unit_ref, row.source_start, row.source_end)
            for row in form_lattice.units
        )
        designation_slots = self._designation_slots(
            grounding_result,
            unit_by_ref,
            unit_ref_set,
        )
        selected_targets = frozenset(row.target_ref for row in designation_slots)
        semantic_contributions = self._contribution_slots(
            contributions,
            selected_targets,
            unit_by_ref,
            unit_ref_set,
            designation_slots,
        )
        form_contributions, form_references = self._form_evidence_slots(
            orientation,
            form_lattice,
        )
        contribution_slots = _bounded_unique_contributions(
            (*semantic_contributions, *form_contributions),
            self._config,
        )
        predicate_targets = frozenset(
            row.target_ref
            for row in contribution_slots
            if row.kind == "predicate" and row.target_ref is not None
        )

        profiles_by_target: dict[str, tuple[AffordanceProfile, ...]] = {}
        for designation in designation_slots:
            if designation.target_ref in profiles_by_target:
                continue
            raw_profiles = self._affordance_index.for_target(designation.target_ref)
            if not isinstance(raw_profiles, tuple):
                raise TypeError("affordance lookup must return a tuple")
            profiles = raw_profiles[: self._config.max_affordances_per_target]
            if any(
                not isinstance(profile, AffordanceProfile)
                or profile.target_ref != designation.target_ref
                for profile in profiles
            ):
                raise ValueError("affordance lookup returned an invalid profile")
            profiles_by_target[designation.target_ref] = profiles

        application_frames = self._application_frames(
            designation_slots,
            profiles_by_target,
            predicate_targets,
        )
        mode_slots = (_mode_slot(orientation, form_lattice),)
        scope_slots = _scope_slots(form_lattice, self._config)
        expression_link_slots = _expression_link_slots(
            form_lattice,
            self._config,
        )
        transition_slots = self._transition_slots(
            orientation.mode,
            application_frames,
        )
        designation_references = self._designation_references(
            designation_slots,
            profiles_by_target,
            contribution_slots,
        )
        reference_slots = _bounded_unique_slots(
            (*designation_references, *form_references),
            self._config.max_orientation_alternatives,
        )
        variable_slots = _variable_slots(
            form_lattice,
            contribution_slots,
            application_frames,
            self._config,
        )
        consumed = {
            source_ref
            for contribution in contribution_slots
            for source_ref in contribution.source_unit_refs
        }
        residual_evidence = _residual_evidence(form_lattice, consumed)

        return ProposalContext.create(
            orientation_ref=orientation.orientation_ref,
            evidence_packet_ref=evidence.packet_ref,
            form_lattice_ref=form_lattice.lattice_ref,
            grounding_ref=grounding_result.grounding_ref,
            designation_slots=designation_slots,
            contribution_slots=contribution_slots,
            mode_slots=mode_slots,
            application_frames=application_frames,
            reference_slots=reference_slots,
            scope_slots=scope_slots,
            expression_link_slots=expression_link_slots,
            variable_slots=variable_slots,
            transition_slots=transition_slots,
            residual_evidence=residual_evidence,
            context_refs=_orientation_context_refs(orientation, self._config),
            source_unit_refs=tuple(row.unit_ref for row in form_lattice.units),
            source_unit_spans=source_spans,
            revision_pin=orientation.revision_pin,
            config=self._config,
        )

    def _designation_slots(
        self,
        grounding_result: GroundingResult,
        unit_by_ref: Mapping[str, Any],
        unit_ref_set: frozenset[str],
    ) -> tuple[DesignationSlot, ...]:
        candidates: list[DesignationSlot] = []
        for candidate in grounding_result.designations:
            unknown = set(candidate.unit_refs) - unit_ref_set
            if unknown:
                raise ValueError(
                    f"designation contains unknown source unit: {sorted(unknown)}"
                )
            atom = self._authority.atoms.get(candidate.target_ref)
            if not isinstance(atom, AtomRecord):
                raise ValueError(
                    f"designation target is absent from authority: {candidate.target_ref}"
                )
            provenance = (
                candidate.provenance_refs
                or grounding_result.provenance_refs
                or (candidate.designation_fact_ref,)
            )
            candidates.append(
                DesignationSlot.create(
                    source_unit_refs=candidate.unit_refs,
                    target_ref=candidate.target_ref,
                    target_kind=atom.kind,
                    score_q=_score_q(candidate.score),
                    designation_fact_ref=candidate.designation_fact_ref,
                    provenance_refs=provenance,
                )
            )
        candidates.sort(
            key=lambda row: (
                -row.score_q,
                row.target_ref,
                row.designation_fact_ref,
                row.source_unit_refs,
            )
        )
        selected: list[DesignationSlot] = []
        span_counts: dict[tuple[int, int], int] = {}
        seen: set[str] = set()
        for row in candidates:
            if row.slot_ref in seen:
                continue
            geometry = tuple(
                (
                    unit_by_ref[ref].source_start,
                    unit_by_ref[ref].source_end,
                )
                for ref in row.source_unit_refs
            )
            span = (
                min(item[0] for item in geometry),
                max(item[1] for item in geometry),
            )
            if span_counts.get(span, 0) >= self._config.max_designations_per_span:
                continue
            if len(selected) >= self._config.max_orientation_alternatives:
                break
            span_counts[span] = span_counts.get(span, 0) + 1
            seen.add(row.slot_ref)
            selected.append(row)
        return tuple(selected)

    def _contribution_slots(
        self,
        contributions: tuple[SemanticContribution, ...],
        selected_targets: frozenset[str],
        unit_by_ref: Mapping[str, Any],
        unit_ref_set: frozenset[str],
        designations: tuple[DesignationSlot, ...],
    ) -> tuple[ContributionSlot, ...]:
        provenance_by_target: dict[str, tuple[str, ...]] = {}
        for designation in designations:
            provenance_by_target.setdefault(designation.target_ref, ())
            provenance_by_target[designation.target_ref] += (designation.slot_ref,)
        per_target: dict[str, int] = {}
        selected: list[ContributionSlot] = []
        seen_refs: set[str] = set()
        maximum = (
            self._config.max_affordances_per_target * self._CONTRIBUTIONS_PER_PROFILE
        )
        for contribution in contributions:
            if contribution.contribution_ref in seen_refs:
                continue
            unknown = set(contribution.source_unit_refs) - unit_ref_set
            if unknown:
                raise ValueError(
                    f"contribution contains unknown source unit: {sorted(unknown)}"
                )
            target_kind: str | None = None
            if contribution.target_ref is not None:
                if contribution.target_ref not in selected_targets:
                    continue
                atom = self._authority.atoms.get(contribution.target_ref)
                if not isinstance(atom, AtomRecord):
                    raise ValueError("contribution target is absent from authority")
                target_kind = atom.kind
                count = per_target.get(contribution.target_ref, 0)
                if count >= maximum:
                    continue
                per_target[contribution.target_ref] = count + 1
            literal_value = None
            if contribution.kind == "literal":
                literal_value = next(
                    (
                        value
                        for key, value in contribution.constraints
                        if key in {"literal", "literal_value"}
                    ),
                    None,
                )
                if literal_value is None:
                    raise ValueError(
                        "literal contribution requires a literal constraint"
                    )
            selected.append(
                ContributionSlot.create(
                    contribution_ref=contribution.contribution_ref,
                    kind=contribution.kind,
                    source_unit_refs=contribution.source_unit_refs,
                    target_ref=contribution.target_ref,
                    target_kind=target_kind,
                    input_ports=contribution.input_ports,
                    output_ports=contribution.output_ports,
                    constraints=contribution.constraints,
                    provenance_refs=provenance_by_target.get(
                        contribution.target_ref or "",
                        (),
                    ),
                    literal_value=literal_value,
                )
            )
            seen_refs.add(contribution.contribution_ref)
        return tuple(selected)

    def _form_evidence_slots(
        self,
        orientation: Orientation,
        form_lattice: FormLattice,
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ReferenceSlot, ...]]:
        contributions: list[ContributionSlot] = []
        references: list[ReferenceSlot] = []
        feature_kinds = {
            "binder": "binder",
            "query": "open_variable",
            "polarity": "scope",
            "modality": "scope",
            "tense_aspect": "scope",
            "connector": "connector",
            "discourse": "discourse",
            "correction": "discourse",
            "determiner": "qualifier",
            "linker": "qualifier",
        }
        ports = {
            "binder": (("role:subject", "role:predicate"), ("role:application",)),
            "open_variable": ((), ("role:variable",)),
            "scope": (("role:scope_target",), ("role:scope",)),
            "connector": (("role:left", "role:right"), ("role:link",)),
            "discourse": ((), ("role:discourse",)),
            "qualifier": (("role:qualified",), ("role:qualifier",)),
            "reference": ((), ("role:reference",)),
        }
        for unit in form_lattice.units:
            for category, value in unit.features:
                if category == "participant":
                    target = _participant_feature_target(
                        value,
                        orientation,
                        self._authority.atoms,
                    )
                    if target is None:
                        continue
                    atom = self._authority.atoms.get(target)
                    if not isinstance(atom, AtomRecord):
                        continue
                    compatible_roles = _reference_roles(atom.kind)
                    reference = ReferenceSlot.create(
                        target_ref=target,
                        target_kind=atom.kind,
                        source_unit_refs=(unit.unit_ref,),
                        resolution_kind="participant_deixis",
                        compatible_roles=compatible_roles,
                        score_q=1_000_000,
                        provenance_refs=(unit.unit_ref,),
                    )
                    references.append(reference)
                    input_ports, output_ports = ports["reference"]
                    contributions.append(
                        ContributionSlot.create(
                            contribution_ref=stable_ref(
                                "form_contribution",
                                (unit.unit_ref, category, value, target),
                            ),
                            kind="reference",
                            source_unit_refs=(unit.unit_ref,),
                            target_ref=target,
                            target_kind=atom.kind,
                            input_ports=input_ports,
                            output_ports=output_ports,
                            constraints=((category, value),),
                            provenance_refs=(unit.unit_ref,),
                        )
                    )
                    continue
                contribution_kind = feature_kinds.get(category)
                if contribution_kind is None:
                    continue
                input_ports, output_ports = ports[contribution_kind]
                contributions.append(
                    ContributionSlot.create(
                        contribution_ref=stable_ref(
                            "form_contribution",
                            (unit.unit_ref, category, value),
                        ),
                        kind=contribution_kind,
                        source_unit_refs=(unit.unit_ref,),
                        target_ref=None,
                        target_kind=None,
                        input_ports=input_ports,
                        output_ports=output_ports,
                        constraints=((category, value),),
                        provenance_refs=(unit.unit_ref,),
                    )
                )
        return tuple(contributions), tuple(references)

    def _designation_references(
        self,
        designations: tuple[DesignationSlot, ...],
        profiles_by_target: Mapping[str, tuple[AffordanceProfile, ...]],
        contributions: tuple[ContributionSlot, ...],
    ) -> tuple[ReferenceSlot, ...]:
        references: list[ReferenceSlot] = []
        for designation in designations:
            if designation.target_kind not in {"entity", "participant"}:
                continue
            if not any(
                row.target_ref == designation.target_ref
                and row.kind in {"anchor", "reference"}
                and row.source_unit_refs == designation.source_unit_refs
                for row in contributions
            ):
                continue
            roles = tuple(
                dict.fromkeys(
                    role
                    for profile in profiles_by_target.get(
                        designation.target_ref,
                        (),
                    )
                    for role in profile.role_candidates
                    if role.startswith("role:")
                )
            ) or _reference_roles(designation.target_kind)
            references.append(
                ReferenceSlot.create(
                    target_ref=designation.target_ref,
                    target_kind=designation.target_kind,
                    source_unit_refs=designation.source_unit_refs,
                    resolution_kind="designation",
                    compatible_roles=roles,
                    score_q=designation.score_q,
                    provenance_refs=(designation.slot_ref,),
                )
            )
        return tuple(references)

    def _application_frames(
        self,
        designations: tuple[DesignationSlot, ...],
        profiles_by_target: Mapping[str, tuple[AffordanceProfile, ...]],
        predicate_targets: frozenset[str],
    ) -> tuple[ApplicationFrameSlot, ...]:
        frames: list[ApplicationFrameSlot] = []
        per_target: dict[str, int] = {}
        event_signature_by_target: dict[str, EventSignature | None] = {}
        for designation in designations:
            target = designation.target_ref
            if target not in predicate_targets:
                continue
            operator_ref = _operator_for_kind(designation.target_kind)
            if operator_ref is None:
                continue
            for profile in profiles_by_target.get(target, ()):
                if "predicate" not in profile.contribution_kinds:
                    continue
                if per_target.get(target, 0) >= self._config.max_affordances_per_target:
                    break
                structural_role = (
                    profile.output_ports[0]
                    if profile.output_ports
                    else "role:predicate"
                )
                proposition_roles: tuple[str, ...] = ()
                if designation.target_kind == "event_type":
                    if target not in event_signature_by_target:
                        event_signature_by_target[target] = (
                            self._authority.by_event_signature(target)
                        )
                    signature = event_signature_by_target[target]
                    if not isinstance(signature, EventSignature):
                        raise ValueError(
                            "event predicate target lacks a reviewed signature"
                        )
                    required_roles = tuple(
                        role.role for role in signature.roles if role.required
                    )
                    optional_roles = tuple(
                        role.role for role in signature.roles if not role.required
                    )
                    proposition_roles = tuple(
                        role.role for role in signature.roles if role.proposition_valued
                    )
                else:
                    reviewed_roles = tuple(
                        self._authority.operator_roles.get(operator_ref, ())
                    )
                    legal_fillers = tuple(
                        role for role in reviewed_roles if role != structural_role
                    )
                    if any(role not in legal_fillers for role in profile.input_ports):
                        raise ValueError(
                            "affordance input port is absent from operator roles"
                        )
                    required_roles = tuple(
                        role for role in profile.input_ports if role != structural_role
                    )
                    optional_roles = tuple(
                        role
                        for role in profile.role_candidates
                        if role in legal_fillers and role not in required_roles
                    )
                derived = ()
                if designation.target_kind == "state_dimension":
                    derived = (("role:dimension", target),)
                frame = ApplicationFrameSlot.create(
                    designation_slot_ref=designation.slot_ref,
                    predicate_target_ref=target,
                    predicate_kind=designation.target_kind,
                    operator_ref=operator_ref,
                    structural_role_ref=structural_role,
                    required_roles=required_roles,
                    optional_roles=optional_roles,
                    proposition_roles=proposition_roles,
                    source_unit_refs=designation.source_unit_refs,
                    derived_role_targets=derived,
                    affordance_frame_ref=profile.frame_ref,
                    provenance_refs=tuple(
                        dict.fromkeys(
                            (
                                designation.slot_ref,
                                *designation.provenance_refs,
                                *((profile.frame_ref,) if profile.frame_ref else ()),
                            )
                        )
                    ),
                )
                if all(row.slot_ref != frame.slot_ref for row in frames):
                    frames.append(frame)
                    per_target[target] = per_target.get(target, 0) + 1
        return tuple(frames)

    def _transition_slots(
        self,
        mode: SemanticMode,
        frames: tuple[ApplicationFrameSlot, ...],
    ) -> tuple[TransitionSlot, ...]:
        if mode not in {SemanticMode.REQUEST, SemanticMode.SIMULATE}:
            return ()
        transitions: list[TransitionSlot] = []
        record_by_target: dict[str, Mapping[str, Any] | None] = {}
        signature_by_event: dict[str, EventSignature | None] = {}
        for frame in frames:
            if frame.operator_ref != "op:state":
                continue
            target = frame.predicate_target_ref
            if target not in record_by_target:
                record_by_target[target] = self._authority.by_transition(target)
            transition = record_by_target[target]
            if transition is None:
                continue
            event_type = transition.get("event_type_ref") or transition.get(
                "event_type"
            )
            if not isinstance(event_type, str) or not event_type:
                raise ValueError("reviewed transition lacks an event type")
            if event_type not in signature_by_event:
                signature_by_event[event_type] = self._authority.by_event_signature(
                    event_type
                )
            signature = signature_by_event[event_type]
            if not isinstance(signature, EventSignature):
                raise ValueError("transition event lacks a reviewed signature")
            required_roles = tuple(
                role.role for role in signature.roles if role.required
            )
            transitions.append(
                TransitionSlot.create(
                    application_frame_ref=frame.slot_ref,
                    event_type_ref=signature.event_type,
                    compatible_modes=("REQUEST", "SIMULATE"),
                    required_roles=required_roles,
                    required_capabilities=signature.required_capabilities,
                    required_permissions=signature.required_permissions,
                    adapter_ref=signature.adapter_ref,
                    source_unit_refs=frame.source_unit_refs,
                )
            )
        return tuple(transitions)


def _bounded_unique_contributions(
    rows: tuple[ContributionSlot, ...],
    config: RuntimeConfig,
) -> tuple[ContributionSlot, ...]:
    selected: list[ContributionSlot] = []
    seen: set[str] = set()
    per_target: dict[str, int] = {}
    target_limit = config.max_affordances_per_target * 2
    global_limit = config.max_input_tokens * (target_limit + 1)
    for row in rows:
        if row.slot_ref in seen:
            continue
        if row.target_ref is not None:
            count = per_target.get(row.target_ref, 0)
            if count >= target_limit:
                continue
            per_target[row.target_ref] = count + 1
        selected.append(row)
        seen.add(row.slot_ref)
        if len(selected) >= global_limit:
            break
    return tuple(selected)


def _bounded_unique_slots(
    rows: tuple[Any, ...],
    maximum: int,
) -> tuple[Any, ...]:
    selected: list[Any] = []
    seen: set[str] = set()
    for row in rows:
        if row.slot_ref in seen:
            continue
        selected.append(row)
        seen.add(row.slot_ref)
        if len(selected) >= maximum:
            break
    return tuple(selected)


def _participant_feature_target(
    value: str,
    orientation: Orientation,
    atoms: Mapping[str, AtomRecord],
) -> str | None:
    candidate: str | None = None
    if value in {"reference_user", "possessive_user"}:
        candidate = orientation.participant_frame
    elif value in {"reference_system", "possessive_system"}:
        if "participant:system" in orientation.participants:
            candidate = "participant:system"
    elif value in {"reference_other", "possessive_other"}:
        others = tuple(
            ref
            for ref in orientation.participants
            if ref not in {orientation.participant_frame, "participant:system"}
        )
        if len(others) == 1:
            candidate = others[0]
    elif value in {"proximal", "distal"}:
        candidates = tuple(
            ref
            for ref in orientation.focus_refs
            if isinstance(atoms.get(ref), AtomRecord)
            and atoms[ref].kind in {"entity", "participant", "concept"}
        )
        if len(candidates) == 1:
            candidate = candidates[0]
    atom = atoms.get(candidate or "")
    if not isinstance(atom, AtomRecord) or atom.kind != "participant":
        if value not in {"proximal", "distal"}:
            return None
        if not isinstance(atom, AtomRecord):
            return None
    return candidate


def _reference_roles(target_kind: str) -> tuple[str, ...]:
    if target_kind == "participant":
        return (
            "role:actor",
            "role:participant",
            "role:subject",
            "role:target",
        )
    return ("role:subject", "role:object", "role:target")


def _variable_slots(
    form_lattice: FormLattice,
    contributions: tuple[ContributionSlot, ...],
    frames: tuple[ApplicationFrameSlot, ...],
    config: RuntimeConfig,
) -> tuple[VariableSlot, ...]:
    variable_sources = tuple(
        dict.fromkeys(
            source_ref
            for row in contributions
            if row.kind == "open_variable"
            for source_ref in row.source_unit_refs
        )
    )
    if not variable_sources:
        return ()
    construction_by_source: dict[str, str] = {}
    for hypothesis in form_lattice.hypotheses:
        if hypothesis.construction != "query":
            continue
        for source_ref in hypothesis.unit_refs:
            construction_by_source[source_ref] = hypothesis.hypothesis_ref
    role_kinds = {
        "role:actor": ("participant", "entity"),
        "role:participant": ("participant",),
        "role:subject": ("entity", "participant", "concept"),
        "role:object": ("entity", "participant", "concept", "literal"),
        "role:target": ("entity", "participant", "concept"),
        "role:value": ("state_value",),
        "role:dimension": ("state_dimension",),
        "role:instance": ("entity", "participant", "concept"),
        "role:class": ("concept",),
        "role:surface": ("literal",),
        "role:type": ("concept", "event_type"),
    }
    slots: list[VariableSlot] = []
    for source_ref in variable_sources:
        for frame in frames:
            for role_ref in (*frame.required_roles, *frame.optional_roles):
                required_kinds = role_kinds.get(role_ref)
                if required_kinds is None:
                    continue
                slots.append(
                    VariableSlot.create(
                        application_frame_ref=frame.slot_ref,
                        role_ref=role_ref,
                        required_kinds=required_kinds,
                        source_unit_refs=(source_ref,),
                        construction_ref=construction_by_source.get(source_ref),
                    )
                )
                if len(slots) >= config.max_orientation_alternatives:
                    return tuple(slots)
    return tuple(slots)


def _validate_builder_inputs(
    orientation: Orientation,
    evidence: EvidencePacket,
    form_lattice: FormLattice,
    grounding_result: GroundingResult,
    contributions: tuple[SemanticContribution, ...],
    authority: Any,
    affordance_index: Any,
    config: RuntimeConfig,
) -> frozenset[str]:
    if type(orientation) is not Orientation:
        raise TypeError("orientation must be Orientation")
    if not isinstance(evidence, EvidencePacket):
        raise TypeError("evidence must be EvidencePacket")
    if not isinstance(form_lattice, FormLattice):
        raise TypeError("form_lattice must be FormLattice")
    if not isinstance(grounding_result, GroundingResult):
        raise TypeError("grounding_result must be GroundingResult")
    if not isinstance(contributions, tuple):
        raise TypeError("contributions must be a tuple of SemanticContribution")
    if not isinstance(orientation.mode, SemanticMode):
        raise TypeError("orientation mode must be SemanticMode")

    if evidence.packet_ref != form_lattice.evidence_packet_ref:
        raise ValueError("evidence packet lineage disagrees with form lattice")
    if evidence.packet_ref != grounding_result.evidence_packet_ref:
        raise ValueError("evidence packet lineage disagrees with grounding")
    if form_lattice.lattice_ref != grounding_result.form_lattice_ref:
        raise ValueError("form lattice lineage disagrees with grounding")
    if grounding_result.revision_pin != orientation.revision_pin:
        raise ValueError(
            "grounding revision pin disagrees with orientation revision pin"
        )
    if evidence.form_pack_hash != form_lattice.form_pack_hash:
        raise ValueError("evidence and form lattice form pack hash disagree")

    pinned_generation = orientation.revision_pin.authority_generation
    if authority.generation != pinned_generation:
        raise ValueError(
            "builder authority generation disagrees with orientation revision pin"
        )
    if affordance_index.authority_generation != pinned_generation:
        raise ValueError(
            "affordance index generation disagrees with orientation revision pin"
        )
    if orientation.scanned_atom_count != 0:
        raise ValueError("orientation must not contain an authority scan")

    designation_limit = config.max_input_tokens * config.max_designations_per_span
    contribution_limit = config.max_input_tokens * (
        config.max_affordances_per_target * 2 + 1
    )

    def bounded_tuple(
        value: object,
        *,
        owner: type[Any],
        limit: int,
        label: str,
    ) -> tuple[Any, ...]:
        if not isinstance(value, tuple):
            raise TypeError(f"{label} must be a tuple of {owner.__name__}")
        if len(value) > limit:
            raise ValueError(f"{label} bound violated")
        if any(not isinstance(row, owner) for row in value):
            raise TypeError(f"{label} must be a tuple of {owner.__name__}")
        return value

    bounded_tuple(
        grounding_result.designations,
        owner=DesignationCandidate,
        limit=designation_limit,
        label="grounding designations",
    )
    bounded_tuple(
        grounding_result.unresolved,
        owner=ReferenceRequirement,
        limit=config.max_input_tokens,
        label="grounding unresolved",
    )
    bounded_tuple(
        grounding_result.grounded_items,
        owner=GroundedItem,
        limit=config.max_input_tokens,
        label="grounded items",
    )
    bounded_tuple(
        contributions,
        owner=SemanticContribution,
        limit=contribution_limit,
        label="contributions",
    )

    if evidence.source_text != form_lattice.source_text:
        raise ValueError("evidence and form lattice source text disagree")
    if orientation.source_text != evidence.source_text:
        raise ValueError("orientation and evidence source text disagree")
    if not isinstance(evidence.items, tuple):
        raise TypeError("evidence items must be a tuple")
    evidence_refs = tuple(row.source_ref for row in evidence.items)
    if any(not isinstance(ref, str) or not ref for ref in evidence_refs):
        raise TypeError("evidence item source_ref must be a non-empty string")
    if len(evidence_refs) != len(set(evidence_refs)):
        raise ValueError("evidence item source refs must be unique")
    if not isinstance(form_lattice.units, tuple) or not form_lattice.units:
        raise ValueError("form lattice requires source units")
    if len(form_lattice.units) > config.max_input_tokens:
        raise ValueError("form lattice source unit bound violated")
    unit_refs = tuple(row.unit_ref for row in form_lattice.units)
    if len(unit_refs) != len(set(unit_refs)):
        raise ValueError("form lattice source unit refs must be unique")
    cursor = 0
    for unit in form_lattice.units:
        if (
            not isinstance(unit.source_start, int)
            or isinstance(unit.source_start, bool)
            or not isinstance(unit.source_end, int)
            or isinstance(unit.source_end, bool)
        ):
            raise ValueError("form lattice geometry coordinates are not exact")
        if unit.source_end <= unit.source_start:
            raise ValueError("form lattice geometry requires positive-width units")
        if unit.source_start != cursor:
            raise ValueError("form lattice geometry must be contiguous and monotonic")
        if (
            unit.source_end > len(form_lattice.source_text)
            or form_lattice.source_text[unit.source_start : unit.source_end]
            != unit.source_text
        ):
            raise ValueError("form lattice geometry is not exact")
        cursor = unit.source_end
    if cursor != len(form_lattice.source_text):
        raise ValueError("form lattice geometry does not cover exact source text")
    if not isinstance(form_lattice.hypotheses, tuple):
        raise TypeError("form lattice hypotheses must be a tuple")
    if len(form_lattice.hypotheses) > config.max_orientation_alternatives:
        raise ValueError("form hypothesis bound violated")
    hypothesis_refs = tuple(row.hypothesis_ref for row in form_lattice.hypotheses)
    if len(hypothesis_refs) != len(set(hypothesis_refs)):
        raise ValueError("form hypothesis refs must be unique")
    unit_ref_set = frozenset(unit_refs)
    for hypothesis in form_lattice.hypotheses:
        if not set(hypothesis.unit_refs) <= unit_ref_set:
            raise ValueError("form hypothesis contains unknown source unit")
    for requirement in grounding_result.unresolved:
        if requirement.unit_ref not in unit_ref_set:
            raise ValueError("grounding requirement contains unknown source unit")
    for item in grounding_result.grounded_items:
        if not set(item.unit_refs) <= unit_ref_set:
            raise ValueError("grounded item contains unknown source unit")
    if grounding_result.created_refs:
        raise ValueError("grounding must not manufacture semantic refs")
    return unit_ref_set


def _score_q(score: float) -> int:
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise TypeError("designation score must be numeric")
    if not isfinite(score) or score < 0 or score > 1:
        raise ValueError("designation score must be finite and within [0, 1]")
    try:
        exact = Decimal(str(score)) * Decimal(1_000_000)
    except InvalidOperation as exc:
        raise ValueError("designation score is not exact") from exc
    return int(exact.to_integral_value(rounding=ROUND_HALF_EVEN))


def _operator_for_kind(target_kind: str) -> str | None:
    return {
        "label_type": "op:designation",
        "concept": "op:type",
        "relation_type": "op:relation",
        "state_dimension": "op:state",
        "state_value": "op:state",
        "value": "op:state",
        "event_type": "op:event",
    }.get(target_kind)


def _structural_role_for_kind(target_kind: str) -> str | None:
    return {
        "label_type": "role:label_type",
        "concept": "role:class",
        "relation_type": "role:relation",
        "state_dimension": "role:dimension",
        "state_value": "role:value",
        "value": "role:value",
        "event_type": "role:event",
    }.get(target_kind)


def _derived_roles_for_kind(
    target_kind: str, target_ref: str
) -> tuple[tuple[str, str], ...]:
    if target_kind == "state_dimension":
        return (("role:dimension", target_ref),)
    return ()


def _mode_slot(
    orientation: Orientation,
    form_lattice: FormLattice,
) -> ModeSlot:
    construction_ref = None
    source_refs: tuple[str, ...] = ()
    for hypothesis in form_lattice.hypotheses:
        construction = (hypothesis.construction or "").upper()
        if construction == orientation.mode.value:
            construction_ref = hypothesis.hypothesis_ref
            source_refs = hypothesis.unit_refs
            break
    requested_effect = {
        SemanticMode.OBSERVE: "admission",
        SemanticMode.QUERY: "query",
        SemanticMode.REQUEST: "effect",
        SemanticMode.SIMULATE: "simulation",
    }[orientation.mode]
    return ModeSlot.create(
        mode=orientation.mode.value,
        source_unit_refs=source_refs,
        construction_ref=construction_ref,
        requested_effect=requested_effect,
    )


def _scope_slots(
    form_lattice: FormLattice,
    config: RuntimeConfig,
) -> tuple[ScopeSlot, ...]:
    mapping = {
        "polarity": "scope:polarity",
        "modality": "scope:modality",
        "tense": "scope:tense",
        "aspect": "scope:aspect",
        "tense_aspect": "scope:aspect",
        "attribution": "scope:attribution",
    }
    slots: list[ScopeSlot] = []
    for unit in form_lattice.units:
        for feature, value in unit.features:
            operator = mapping.get(feature)
            if operator is None:
                continue
            value_ref = value if value.startswith("value:") else f"value:{value}"
            slot = ScopeSlot.create(
                operator_type=operator,
                value_ref=value_ref,
                source_unit_refs=(unit.unit_ref,),
                construction_ref=None,
            )
            if all(row.slot_ref != slot.slot_ref for row in slots):
                slots.append(slot)
            if len(slots) >= config.max_orientation_alternatives:
                return tuple(slots)
    return tuple(slots)


def _expression_link_slots(
    form_lattice: FormLattice,
    config: RuntimeConfig,
) -> tuple[ExpressionLinkSlot, ...]:
    mapping = {
        "coordination": ("link:coordination", True),
        "conjunction": ("link:conjunction", True),
        "disjunction": ("link:disjunction", True),
        "conditional": ("link:condition", False),
        "condition": ("link:condition", False),
        "causal": ("link:cause", False),
        "cause": ("link:cause", False),
        "contrast": ("link:contrast", False),
        "sequence": ("link:sequence", False),
    }
    slots: list[ExpressionLinkSlot] = []
    for hypothesis in form_lattice.hypotheses:
        if hypothesis.construction not in mapping:
            continue
        link_type, commutative = mapping[hypothesis.construction]
        slots.append(
            ExpressionLinkSlot.create(
                link_type=link_type,
                commutative=commutative,
                min_arity=2,
                max_arity=2,
                source_unit_refs=hypothesis.unit_refs,
                construction_ref=hypothesis.hypothesis_ref,
            )
        )
        if len(slots) >= config.max_orientation_alternatives:
            break
    return tuple(slots)


def _residual_evidence(
    form_lattice: FormLattice,
    consumed: set[str],
) -> tuple[ResidualEvidence, ...]:
    residuals: list[ResidualEvidence] = []
    critical_kinds = {
        "participant": "reference",
        "binder": "binder",
        "query": "open_variable",
        "polarity": "scope",
        "modality": "scope",
        "tense_aspect": "scope",
        "connector": "connector",
        "determiner": "qualifier",
        "linker": "qualifier",
        "correction": "discourse",
        "discourse": "discourse",
    }
    for unit in form_lattice.units:
        if unit.unit_ref in consumed:
            continue
        contribution_kind = next(
            (
                critical_kinds[feature]
                for feature, _ in unit.features
                if feature in critical_kinds
            ),
            None,
        )
        orthographic = not any(character.isalnum() for character in unit.source_text)
        explicitly_noncritical_discourse = any(
            feature == "discourse" and value == "discourse_particle"
            for feature, value in unit.features
        )
        noncritical = orthographic or explicitly_noncritical_discourse
        if contribution_kind is None:
            contribution_kind = "discourse" if noncritical else "anchor"
        residuals.append(
            ResidualEvidence.create(
                source_unit_ref=unit.unit_ref,
                contribution_kind=contribution_kind,
                critical=not noncritical,
                reason=(
                    "reviewed noncritical orthographic or discourse evidence"
                    if noncritical
                    else "unconsumed critical semantic contribution evidence"
                ),
            )
        )
    return tuple(residuals)


def _orientation_context_refs(
    orientation: Orientation,
    config: RuntimeConfig,
) -> tuple[str, ...]:
    candidates = (
        orientation.session_ref,
        orientation.turn_ref,
        orientation.active_turn_ref,
        orientation.participant_frame,
        orientation.temporal_frame,
        *orientation.participants,
        *orientation.focus_refs,
        *orientation.obligation_refs,
        *orientation.event_refs,
    )
    selected: list[str] = []
    for ref in candidates:
        if isinstance(ref, str) and ref and ref not in selected:
            selected.append(ref)
        if len(selected) >= config.max_orientation_alternatives:
            break
    if not selected:
        raise ValueError("orientation provides no current-cycle context refs")
    return tuple(selected)


def _context_material(context: Any) -> dict[str, Any]:
    return {
        "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
        "orientation_ref": context.orientation_ref,
        "evidence_packet_ref": context.evidence_packet_ref,
        "form_lattice_ref": context.form_lattice_ref,
        "grounding_ref": context.grounding_ref,
        "designation_slots": [row.as_dict() for row in context.designation_slots],
        "contribution_slots": [row.as_dict() for row in context.contribution_slots],
        "mode_slots": [row.as_dict() for row in context.mode_slots],
        "application_frames": [row.as_dict() for row in context.application_frames],
        "reference_slots": [row.as_dict() for row in context.reference_slots],
        "scope_slots": [row.as_dict() for row in context.scope_slots],
        "expression_link_slots": [
            row.as_dict() for row in context.expression_link_slots
        ],
        "variable_slots": [row.as_dict() for row in context.variable_slots],
        "transition_slots": [row.as_dict() for row in context.transition_slots],
        "residual_evidence": [row.as_dict() for row in context.residual_evidence],
        "context_refs": list(context.context_refs),
        "source_unit_refs": list(context.source_unit_refs),
        "source_unit_spans": [list(row) for row in context.source_unit_spans],
        "revision_pin": context.revision_pin.as_dict(),
    }


def _validate_context(context: Any, config: RuntimeConfig) -> None:
    _require_strings(context.context_refs, "context_refs", nonempty=True)
    sources = _require_strings(
        context.source_unit_refs, "source_unit_refs", nonempty=True
    )
    if len(sources) > config.max_input_tokens:
        raise ValueError("source unit bound violated")
    if not isinstance(context.source_unit_spans, tuple):
        raise TypeError("source_unit_spans must be a tuple")
    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for row in context.source_unit_spans:
        if not isinstance(row, tuple) or len(row) != 3:
            raise TypeError("source_unit_spans must contain triples")
        ref, start, end = row
        _require_string(ref, "source span ref")
        _require_int(start, "source span start", minimum=0)
        _require_int(end, "source span end", minimum=0)
        if end <= start:
            raise ValueError("source span must have positive width")
        if start != cursor:
            raise ValueError("source spans must be contiguous and monotonic")
        spans.append((ref, start, end))
        cursor = end
    if tuple(row[0] for row in spans) != sources:
        raise ValueError("source spans must exactly match source_unit_refs order")

    limits = (
        (
            "designation",
            context.designation_slots,
            config.max_orientation_alternatives,
            DesignationSlot,
        ),
        (
            "contribution",
            context.contribution_slots,
            config.max_input_tokens * (config.max_affordances_per_target * 2 + 1),
            ContributionSlot,
        ),
        ("mode", context.mode_slots, config.max_orientation_alternatives, ModeSlot),
        (
            "application frame",
            context.application_frames,
            config.max_orientation_alternatives,
            ApplicationFrameSlot,
        ),
        (
            "reference",
            context.reference_slots,
            config.max_orientation_alternatives,
            ReferenceSlot,
        ),
        ("scope", context.scope_slots, config.max_orientation_alternatives, ScopeSlot),
        (
            "expression link",
            context.expression_link_slots,
            config.max_orientation_alternatives,
            ExpressionLinkSlot,
        ),
        (
            "variable",
            context.variable_slots,
            config.max_orientation_alternatives,
            VariableSlot,
        ),
        (
            "transition",
            context.transition_slots,
            config.max_orientation_alternatives,
            TransitionSlot,
        ),
        (
            "residual",
            context.residual_evidence,
            config.max_input_tokens,
            ResidualEvidence,
        ),
    )
    if len(context.context_refs) > config.max_orientation_alternatives:
        raise ValueError("context ref bound violated")
    all_refs: list[str] = []
    for label, rows, maximum, owner in limits:
        if not isinstance(rows, tuple):
            raise TypeError(f"{label} slots must be a tuple")
        if len(rows) > maximum:
            raise ValueError(f"{label} slot bound violated")
        if any(not isinstance(row, owner) for row in rows):
            raise TypeError(f"{label} slots contain invalid records")
        refs = tuple(
            row.residual_ref if isinstance(row, ResidualEvidence) else row.slot_ref
            for row in rows
        )
        if len(refs) != len(set(refs)):
            raise ValueError(f"duplicate {label} slot")
        all_refs.extend(refs)
    if not context.mode_slots:
        raise ValueError("proposal context requires at least one mode slot")
    if len(all_refs) != len(set(all_refs)):
        raise ValueError("proposal context slot refs must be globally unique")

    source_set = set(sources)
    for rows in (
        context.designation_slots,
        context.contribution_slots,
        context.mode_slots,
        context.application_frames,
        context.reference_slots,
        context.scope_slots,
        context.expression_link_slots,
        context.variable_slots,
        context.transition_slots,
    ):
        for row in rows:
            if not set(row.source_unit_refs) <= source_set:
                raise ValueError("slot contains unknown source unit")
    residual_sources = tuple(row.source_unit_ref for row in context.residual_evidence)
    if len(residual_sources) != len(set(residual_sources)):
        raise ValueError("duplicate residual source unit")
    for row in context.residual_evidence:
        if row.source_unit_ref not in source_set:
            raise ValueError("residual contains unknown source unit")

    span_by_ref = {ref: (start, end) for ref, start, end in spans}
    designation_span_counts: dict[tuple[int, int], int] = {}
    for designation in context.designation_slots:
        selected = tuple(span_by_ref[ref] for ref in designation.source_unit_refs)
        exact_span = (
            min(item[0] for item in selected),
            max(item[1] for item in selected),
        )
        designation_span_counts[exact_span] = (
            designation_span_counts.get(exact_span, 0) + 1
        )
        if designation_span_counts[exact_span] > config.max_designations_per_span:
            raise ValueError("designation per exact source span bound violated")

    contribution_target_counts: dict[str, int] = {}
    contributed_sources: set[str] = set()
    for contribution in context.contribution_slots:
        contributed_sources.update(contribution.source_unit_refs)
        if contribution.target_ref is None:
            continue
        count = contribution_target_counts.get(contribution.target_ref, 0) + 1
        contribution_target_counts[contribution.target_ref] = count
        if count > config.max_affordances_per_target * 2:
            raise ValueError("contribution per target bound violated")
    residual_source_set = set(residual_sources)
    if contributed_sources & residual_source_set:
        raise ValueError("residual source cannot also have a contribution")
    if contributed_sources | residual_source_set != source_set:
        raise ValueError(
            "proposal context source partition must cover every source unit"
        )

    designation_by_ref = {row.slot_ref: row for row in context.designation_slots}
    frame_by_ref = {row.slot_ref: row for row in context.application_frames}
    predicates_by_target: dict[str, list[ContributionSlot]] = {}
    for contribution in context.contribution_slots:
        if contribution.kind == "predicate" and contribution.target_ref is not None:
            predicates_by_target.setdefault(contribution.target_ref, []).append(
                contribution
            )
    frame_target_counts: dict[str, int] = {}
    for frame in context.application_frames:
        designation = designation_by_ref.get(frame.designation_slot_ref)
        if designation is None:
            raise ValueError("application frame contains unknown designation slot")
        if (
            frame.predicate_target_ref != designation.target_ref
            or frame.predicate_kind != designation.target_kind
        ):
            raise ValueError("application frame predicate disagrees with designation")
        expected_operator = _operator_for_kind(frame.predicate_kind)
        if expected_operator is None or frame.operator_ref != expected_operator:
            raise ValueError("application frame violates exact operator lowering")
        expected_structural_role = _structural_role_for_kind(frame.predicate_kind)
        if frame.structural_role_ref != expected_structural_role:
            raise ValueError("application frame has an invalid structural role")
        if frame.structural_role_ref in {
            *frame.required_roles,
            *frame.optional_roles,
        }:
            raise ValueError(
                "application frame structural role cannot be a filler role"
            )
        expected_derived_roles = _derived_roles_for_kind(
            frame.predicate_kind, frame.predicate_target_ref
        )
        if frame.derived_role_targets != expected_derived_roles:
            raise ValueError("application frame has invalid derived role targets")
        if frame.predicate_kind != "event_type" and frame.proposition_roles:
            raise ValueError(
                "application frame proposition roles require an event predicate"
            )
        if frame.designation_slot_ref not in frame.provenance_refs:
            raise ValueError("application frame provenance omits its designation slot")
        frame_input_roles = set(frame.required_roles) | set(frame.optional_roles)
        compatible_contribution = any(
            contribution.target_kind == frame.predicate_kind
            and contribution.source_unit_refs == frame.source_unit_refs
            and bool(contribution.output_ports)
            and contribution.output_ports[0] == frame.structural_role_ref
            and set(contribution.input_ports) == frame_input_roles
            for contribution in predicates_by_target.get(frame.predicate_target_ref, ())
        )
        if not compatible_contribution:
            raise ValueError(
                "application frame roles are not proven by predicate contribution "
                "input roles and structural output"
            )
        count = frame_target_counts.get(frame.predicate_target_ref, 0) + 1
        frame_target_counts[frame.predicate_target_ref] = count
        if count > config.max_affordances_per_target:
            raise ValueError("application frame per target bound violated")
    if any(
        row.application_frame_ref not in frame_by_ref for row in context.variable_slots
    ):
        raise ValueError("variable contains unknown application frame")
    for transition in context.transition_slots:
        frame = frame_by_ref.get(transition.application_frame_ref)
        if frame is None:
            raise ValueError("transition contains unknown application frame")
        if frame.operator_ref != "op:state":
            raise ValueError("transition requires an op:state application frame")


__all__ = [
    "PROPOSAL_CONTEXT_ABI_VERSION",
    "DesignationSlot",
    "ContributionSlot",
    "ModeSlot",
    "ApplicationFrameSlot",
    "ReferenceSlot",
    "ScopeSlot",
    "ExpressionLinkSlot",
    "VariableSlot",
    "TransitionSlot",
    "ResidualEvidence",
    "ProposalContext",
    "ProposalContextBuilder",
]
