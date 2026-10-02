"""Proposal Context ABI 3: bounded, current-cycle semantic proposal slots.

ORIENT constructs one immutable context and passes that exact value through
PROPOSE and VERIFY.  The context contains only grounded pointers and reviewed
structural slots.  It never contains a resolved application or semantic graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from itertools import combinations
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
from .role_schemas import (ReviewedRoleSchemaIndex, QueryProjectionBinding, QueryProjectionMatch,
                          CommunicativeRoleMatch, relation_projection_matches, relation_declarative_matches, role_match_evidence)

PROPOSAL_CONTEXT_ABI_VERSION = 3

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


def _require_exact_string(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise TypeError(f"{name} must be an exact non-empty str")
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
        raise ValueError(f"{label} fields mismatch: wrong field count")
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


def _strict_context_wire(value: object) -> None:
    """Bounded exact JSON preflight; detached wire cannot contain aliases."""
    seen: set[int] = set()
    def visit(item, depth):
        if item is None or type(item) in {str, bool, int, float}:
            if type(item) is float and not isfinite(item):
                raise ValueError("context wire floats must be finite")
            return
        if type(item) not in {dict, list}:
            raise TypeError("context wire requires exact JSON types")
        if len(item) > 576 or depth > 16:
            raise ValueError("context wire container exceeds bound")
        if id(item) in seen:
            raise ValueError("context wire contains cycles or mutable aliases")
        seen.add(id(item))
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise TypeError("context wire keys require exact str")
                visit(child, depth + 1)
        else:
            for child in item:
                visit(child, depth + 1)
    visit(value, 0)


@dataclass(frozen=True)
class QueryProjectionSlot(_ContentAddressedSlot):
    """Private nonpersistent request evidence; identity is not activation authority."""
    slot_ref: str
    requested_content: str
    target_designation_slot_ref: str
    index_ref: str
    schema_ref: str
    match_ref: str
    bindings: tuple[QueryProjectionBinding, ...]
    source_unit_refs: tuple[str, ...]
    source_unit_spans: tuple[tuple[str, int, int], ...]
    orthographic_source_unit_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    _NAMESPACE = "query_projection_slot"

    def __post_init__(self):
        for name in ("slot_ref", "requested_content", "target_designation_slot_ref", "index_ref", "schema_ref", "match_ref"):
            _require_exact_string(getattr(self, name), name)
        if self.requested_content not in {"description", "definition"}:
            raise ValueError("invalid query projection requested content")
        if type(self.bindings) is not tuple or len(self.bindings) not in {3, 4}:
            raise ValueError("query projection requires closed ordered ports")
        if any(type(binding) is not QueryProjectionBinding for binding in self.bindings):
            raise ValueError("query projection requires exact ordered binding records")
        ports = tuple(b.port for b in self.bindings)
        if ports not in {("request", "binder", "target"), ("request", "binder", "determiner", "target")}:
            raise ValueError("query projection requires exact ordered binding records")
        owned = []
        for binding in self.bindings:
            _require_exact_string(binding.port, "port")
            _require_exact_string(binding.contribution_slot_ref, "contribution_slot_ref")
            if type(binding.source_unit_refs) is not tuple or not 1 <= len(binding.source_unit_refs) <= 64:
                raise ValueError("query projection port source bound violated")
            for ref in binding.source_unit_refs:
                _require_exact_string(ref, "port source ref")
            owned.extend(binding.source_unit_refs)
        if len(owned) != len(set(owned)):
            raise ValueError("query projection port sources must have exactly one owner")
        for name in ("source_unit_refs", "orthographic_source_unit_refs", "provenance_refs"):
            value = getattr(self, name)
            if type(value) is not tuple or len(value) > 64 or len(set(value)) != len(value):
                raise ValueError("query projection source/provenance bound violated")
            for ref in value:
                _require_exact_string(ref, name)
        if not self.source_unit_refs or type(self.source_unit_spans) is not tuple or len(self.source_unit_spans) != len(self.source_unit_refs):
            raise ValueError("query projection clause geometry is incomplete")
        previous = None
        for row in self.source_unit_spans:
            if (type(row) is not tuple or len(row) != 3 or type(row[0]) is not str
                or type(row[1]) is not int or type(row[2]) is not int
                or row[1] < 0 or row[2] <= row[1] or previous is not None and row[1] != previous):
                raise ValueError("query projection clause geometry is malformed")
            previous = row[2]
        if tuple(row[0] for row in self.source_unit_spans) != self.source_unit_refs:
            raise ValueError("query projection clause/source correspondence differs")
        if (set(owned) & set(self.orthographic_source_unit_refs)
            or set(owned) | set(self.orthographic_source_unit_refs) != set(self.source_unit_refs)):
            raise ValueError("query projection clause port partition differs")
        if self.provenance_refs != tuple(dict.fromkeys((self.index_ref, self.schema_ref, self.match_ref,
            self.target_designation_slot_ref, *(b.contribution_slot_ref for b in self.bindings)))):
            raise ValueError("query projection provenance differs from its exact owners")
        self._verify_ref()

    def as_dict(self):
        return {"slot_ref": self.slot_ref, "requested_content": self.requested_content,
            "target_designation_slot_ref": self.target_designation_slot_ref,
            "index_ref": self.index_ref, "schema_ref": self.schema_ref, "match_ref": self.match_ref,
            "bindings": [{"port": b.port, "contribution_slot_ref": b.contribution_slot_ref,
                          "source_unit_refs": list(b.source_unit_refs)} for b in self.bindings],
            "source_unit_refs": list(self.source_unit_refs),
            "source_unit_spans": [list(row) for row in self.source_unit_spans],
            "orthographic_source_unit_refs": list(self.orthographic_source_unit_refs),
            "provenance_refs": list(self.provenance_refs)}

    def _material(self):
        material = self.as_dict()
        material.pop("slot_ref")
        return {"abi_version": PROPOSAL_CONTEXT_ABI_VERSION, **material}

    @classmethod
    def create(cls, **values):
        if cls is not QueryProjectionSlot:
            raise TypeError("query projection slot requires exact factory")
        provisional = object.__new__(cls)
        for name, value in values.items():
            object.__setattr__(provisional, name, value)
        object.__setattr__(provisional, "slot_ref", "unhashed")
        return cls(stable_ref(cls._NAMESPACE, provisional._material()), **values)

    @classmethod
    def from_dict(cls, data):
        _strict_context_wire(data)
        _strict_mapping(data, frozenset(f.name for f in fields(cls)), "QueryProjectionSlot")
        if type(data["bindings"]) is not list or len(data["bindings"]) not in {3, 4}:
            raise ValueError("query projection requires bounded wire ports")
        bindings = []
        for binding in data["bindings"]:
            _strict_mapping(binding, frozenset({"port", "contribution_slot_ref", "source_unit_refs"}), "query projection port")
            bindings.append(QueryProjectionBinding(binding["port"], binding["contribution_slot_ref"],
                _wire_string_tuple(binding["source_unit_refs"], "port source refs")))
        raw_spans = data["source_unit_spans"]
        if type(raw_spans) is not list or len(raw_spans) > 64 or any(type(row) is not list or len(row) != 3 for row in raw_spans):
            raise ValueError("query projection wire clause geometry is malformed")
        values = {name: data[name] for name in ("requested_content", "target_designation_slot_ref", "index_ref", "schema_ref", "match_ref")}
        values.update(bindings=tuple(bindings), source_unit_spans=tuple(tuple(row) for row in raw_spans))
        for name in ("source_unit_refs", "orthographic_source_unit_refs", "provenance_refs"):
            values[name] = _wire_string_tuple(data[name], name)
        rebuilt = cls.create(**values)
        if rebuilt.as_dict() != data:
            raise ValueError("non-canonical QueryProjectionSlot encoding")
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
class UnresolvedDesignationFrame(_ContentAddressedSlot):
    slot_ref: str
    label_type_ref: str
    literal_contribution_slot_ref: str
    query_binder_slot_ref: str
    source_unit_refs: tuple[str, ...]
    construction_ref: str
    provenance_refs: tuple[str, ...]

    _NAMESPACE = "unresolved_designation_frame"
    _TUPLE_FIELDS = frozenset({"source_unit_refs", "provenance_refs"})

    # Nonserialized common application structure. These are not grounding or
    # designation evidence: the literal's target remains an unbound variable.
    operator_ref = property(lambda self: "op:designation")
    predicate_target_ref = property(lambda self: self.label_type_ref)
    predicate_kind = property(lambda self: "label_type")
    structural_role_ref = property(lambda self: "role:label_type")
    required_roles = property(lambda self: ("role:surface", "role:target"))
    optional_roles = property(lambda self: ())
    proposition_roles = property(lambda self: ())
    derived_role_targets = property(lambda self: (("role:label_type", self.label_type_ref),))

    def __post_init__(self) -> None:
        for name in (
            "slot_ref",
            "label_type_ref",
            "literal_contribution_slot_ref",
            "query_binder_slot_ref",
            "construction_ref",
        ):
            _require_exact_string(getattr(self, name), name)
        source_unit_refs = _require_strings(
            self.source_unit_refs, "source_unit_refs", nonempty=True
        )
        provenance_refs = _require_strings(
            self.provenance_refs, "provenance_refs", nonempty=True
        )
        config = RuntimeConfig.release()
        if len(source_unit_refs) > config.max_input_tokens:
            raise ValueError("unresolved designation source unit bound violated")
        if len(provenance_refs) > config.max_orientation_alternatives:
            raise ValueError("unresolved designation provenance bound violated")
        self._verify_ref()

    @classmethod
    def create(
        cls,
        *,
        label_type_ref: str,
        literal_contribution_slot_ref: str,
        query_binder_slot_ref: str,
        source_unit_refs: tuple[str, ...],
        construction_ref: str,
        provenance_refs: tuple[str, ...],
    ) -> "UnresolvedDesignationFrame":
        if cls is not UnresolvedDesignationFrame:
            raise TypeError(
                "UnresolvedDesignationFrame factories require exact owner type"
            )
        values = {
            "label_type_ref": label_type_ref,
            "literal_contribution_slot_ref": literal_contribution_slot_ref,
            "query_binder_slot_ref": query_binder_slot_ref,
            "source_unit_refs": source_unit_refs,
            "construction_ref": construction_ref,
            "provenance_refs": provenance_refs,
        }
        material = {
            "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
            **{key: _wire(value) for key, value in values.items()},
        }
        return cls(stable_ref(cls._NAMESPACE, material), **values)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "UnresolvedDesignationFrame":
        if cls is not UnresolvedDesignationFrame:
            raise TypeError(
                "UnresolvedDesignationFrame factories require exact owner type"
            )
        return super().from_dict(data)


ApplicationFrame = ApplicationFrameSlot | UnresolvedDesignationFrame


def _application_frame_as_dict(frame: ApplicationFrame) -> dict[str, Any]:
    if type(frame) is ApplicationFrameSlot:
        return {"frame_type": "grounded", **frame.as_dict()}
    if type(frame) is UnresolvedDesignationFrame:
        return {"frame_type": "unresolved_designation", **frame.as_dict()}
    raise TypeError("application frame has invalid owner type")


def _application_frame_from_dict(data: Mapping[str, Any]) -> ApplicationFrame:
    if type(data) is not dict:
        raise TypeError("application frame row must be an exact dict")
    if "frame_type" not in data:
        raise ValueError("application frame is missing frame_type")
    frame_type = data["frame_type"]
    if type(frame_type) is not str:
        raise TypeError("application frame_type must be an exact str")
    payload = {key: value for key, value in data.items() if key != "frame_type"}
    if frame_type == "grounded":
        return ApplicationFrameSlot.from_dict(payload)
    if frame_type == "unresolved_designation":
        return UnresolvedDesignationFrame.from_dict(payload)
    raise ValueError(f"unknown application frame_type: {frame_type}")


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
    application_frames: tuple[ApplicationFrame, ...]
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
    query_projection_slots: tuple[QueryProjectionSlot, ...] = ()
    abi_version: int = PROPOSAL_CONTEXT_ABI_VERSION
    _query_projection_by_ref: Mapping[str, int] = field(init=False, repr=False, compare=False, hash=False)
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
    _unresolved_frame_by_ref: Mapping[str, int] = field(
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
    _variables_by_frame_role: Mapping[tuple[str, str], tuple[int, ...]] = field(
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
        _require_exact_string(self.context_ref, "context_ref")
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
        application_frames: tuple[ApplicationFrame, ...],
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
        query_projection_slots: tuple[QueryProjectionSlot, ...] = (),
    ) -> "ProposalContext":
        if cls is not ProposalContext:
            raise TypeError("ProposalContext factories require exact ProposalContext")
        values = {
            "orientation_ref": orientation_ref,
            "evidence_packet_ref": evidence_packet_ref,
            "form_lattice_ref": form_lattice_ref,
            "grounding_ref": grounding_ref,
            "designation_slots": designation_slots,
            "query_projection_slots": query_projection_slots,
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
    def _from_checked(context_ref: str, values: Mapping[str, Any]) -> "ProposalContext":
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
        object.__setattr__(self, "_query_projection_by_ref", index(self.query_projection_slots))
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
            if type(row) is not ApplicationFrameSlot:
                continue
            grouped.setdefault(row.designation_slot_ref, []).append(position)
        object.__setattr__(
            self,
            "_frames_by_designation",
            MappingProxyType({key: tuple(value) for key, value in grouped.items()}),
        )
        object.__setattr__(
            self,
            "_unresolved_frame_by_ref",
            MappingProxyType(
                {
                    row.slot_ref: position
                    for position, row in enumerate(self.application_frames)
                    if type(row) is UnresolvedDesignationFrame
                }
            ),
        )
        object.__setattr__(self, "_reference_by_ref", index(self.reference_slots))
        object.__setattr__(self, "_scope_by_ref", index(self.scope_slots))
        object.__setattr__(self, "_link_by_ref", index(self.expression_link_slots))
        object.__setattr__(self, "_variable_by_ref", index(self.variable_slots))
        variables_by_frame_role: dict[tuple[str, str], list[int]] = {}
        for position, variable in enumerate(self.variable_slots):
            key = (variable.application_frame_ref, variable.role_ref)
            variables_by_frame_role.setdefault(key, []).append(position)
        object.__setattr__(
            self,
            "_variables_by_frame_role",
            MappingProxyType(
                {key: tuple(value) for key, value in variables_by_frame_role.items()}
            ),
        )
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

    def query_projection(self, slot_ref: str) -> QueryProjectionSlot | None:
        return self._indexed_row(self.query_projection_slots, self._query_projection_by_ref, slot_ref)

    def frame(self, slot_ref: str) -> ApplicationFrame | None:
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
            if type(row) is not ApplicationFrameSlot:
                raise ValueError("ProposalContext derived index is incoherent")
            if row.designation_slot_ref != slot_ref:
                raise ValueError("ProposalContext derived index is incoherent")
            rows.append(row)
        return tuple(rows)

    @property
    def unresolved_designation_frames(
        self,
    ) -> tuple[UnresolvedDesignationFrame, ...]:
        return tuple(
            row
            for row in self.application_frames
            if type(row) is UnresolvedDesignationFrame
        )

    def unresolved_designation_frame(
        self, slot_ref: str
    ) -> UnresolvedDesignationFrame | None:
        row = self._indexed_row(
            self.application_frames,
            self._unresolved_frame_by_ref,
            slot_ref,
        )
        if row is not None and type(row) is not UnresolvedDesignationFrame:
            raise ValueError("ProposalContext derived index is incoherent")
        return row

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

    def variables_for_frame_role(
        self, frame_ref: str, role_ref: str
    ) -> tuple[VariableSlot, ...]:
        rows: list[VariableSlot] = []
        for position in self._variables_by_frame_role.get((frame_ref, role_ref), ()):
            if (
                type(position) is not int
                or position < 0
                or position >= len(self.variable_slots)
            ):
                raise ValueError("ProposalContext derived index is incoherent")
            row = self.variable_slots[position]
            if row.application_frame_ref != frame_ref or row.role_ref != role_ref:
                raise ValueError("ProposalContext derived index is incoherent")
            rows.append(row)
        return tuple(rows)

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
            "query_projection_slots": [row.as_dict() for row in self.query_projection_slots],
            "contribution_slots": [row.as_dict() for row in self.contribution_slots],
            "mode_slots": [row.as_dict() for row in self.mode_slots],
            "application_frames": [
                _application_frame_as_dict(row) for row in self.application_frames
            ],
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
                "query_projection_slots",
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
            raise ValueError("ProposalContext fields mismatch: wrong field count")
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
            ("query_projection_slots", QueryProjectionSlot, config.max_orientation_alternatives),
            ("contribution_slots", ContributionSlot, contribution_limit),
            ("mode_slots", ModeSlot, config.max_orientation_alternatives),
            ("reference_slots", ReferenceSlot, config.max_orientation_alternatives),
            ("scope_slots", ScopeSlot, config.max_orientation_alternatives),
            (
                "expression_link_slots",
                ExpressionLinkSlot,
                config.max_orientation_alternatives,
            ),
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
        raw_application_frames = data["application_frames"]
        if type(raw_application_frames) is not list:
            raise TypeError("application_frames must be an exact list")
        if len(raw_application_frames) > config.max_orientation_alternatives:
            raise ValueError("application_frames exceeds release bound")
        if any(type(item) is not dict for item in raw_application_frames):
            raise TypeError("application_frames rows must be exact dicts")

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
        source_unit_refs = bounded_strings("source_unit_refs", config.max_input_tokens)
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

        _strict_context_wire(data)

        decoded_rows = {
            name: tuple(owner.from_dict(item) for item in data[name])
            for name, owner, _limit in row_specs
        }
        application_frames = tuple(
            _application_frame_from_dict(item) for item in raw_application_frames
        )
        rebuilt = cls.create(
            orientation_ref=data["orientation_ref"],
            evidence_packet_ref=data["evidence_packet_ref"],
            form_lattice_ref=data["form_lattice_ref"],
            grounding_ref=data["grounding_ref"],
            designation_slots=decoded_rows["designation_slots"],
            query_projection_slots=decoded_rows["query_projection_slots"],
            contribution_slots=decoded_rows["contribution_slots"],
            mode_slots=decoded_rows["mode_slots"],
            application_frames=application_frames,
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


@dataclass(frozen=True)
class _DefinitionLabelSpan:
    """Transient form geometry, not a designation or a selected meaning."""

    source_refs: tuple[str, ...]
    marker_ref: str
    support_refs: tuple[str, ...]
    naming_source_ref: str | None
    target_end: int


@dataclass(frozen=True)
class _ReportedClause:
    """One typed report predicate and its exact clause/content geometry."""

    parent_frame_ref: str
    construction_ref: str
    clause_start: int
    report_start: int
    report_end: int
    content_end: int
    child_frame_refs: tuple[str, ...]


def _reported_clauses_from_lattice(
    frames: tuple[ApplicationFrameSlot, ...],
    form_lattice: FormLattice,
    config: RuntimeConfig,
) -> tuple[_ReportedClause, ...]:
    """Reconstruct bounded report regions from typed form evidence and spans."""
    unit_by_ref = {row.unit_ref: row for row in form_lattice.units}
    sentence_boundaries = tuple(
        row
        for row in form_lattice.units
        if ("orthography", "sentence_boundary") in row.features
    )
    rows: list[_ReportedClause] = []
    for hypothesis in form_lattice.hypotheses:
        if hypothesis.construction != "discourse_report":
            continue
        report_units = tuple(
            unit_by_ref[ref] for ref in hypothesis.unit_refs if ref in unit_by_ref
        )
        if not report_units:
            continue
        report_start = min(row.source_start for row in report_units)
        report_end = max(row.source_end for row in report_units)
        clause_start = max(
            (
                row.source_end
                for row in sentence_boundaries
                if row.source_end <= report_start
            ),
            default=0,
        )
        content_end = min(
            (
                row.source_start
                for row in sentence_boundaries
                if row.source_start >= report_end
            ),
            default=len(form_lattice.source_text),
        )
        parents = tuple(
            frame
            for frame in frames
            if "role:content" in frame.proposition_roles
            and "role:actor" in frame.required_roles
            and (span := _source_span_for_units(frame.source_unit_refs, unit_by_ref))
            is not None
            and report_start <= span[0]
            and span[1] <= report_end
        )
        for parent in parents:
            children = tuple(
                frame.slot_ref
                for frame in frames
                if frame.slot_ref != parent.slot_ref
                and (span := _source_span_for_units(frame.source_unit_refs, unit_by_ref))
                is not None
                and report_end <= span[0]
                and span[1] <= content_end
            )
            rows.append(
                _ReportedClause(
                    parent_frame_ref=parent.slot_ref,
                    construction_ref=hypothesis.hypothesis_ref,
                    clause_start=clause_start,
                    report_start=report_start,
                    report_end=report_end,
                    content_end=content_end,
                    child_frame_refs=children,
                )
            )
        if len(rows) >= config.max_orientation_alternatives:
            break
    return tuple(rows)


def _source_span_for_units(
    source_refs: tuple[str, ...], unit_by_ref: Mapping[str, Any]
) -> tuple[int, int] | None:
    units = tuple(unit_by_ref.get(ref) for ref in source_refs)
    if not units or any(row is None for row in units):
        return None
    return (
        min(row.source_start for row in units),
        max(row.source_end for row in units),
    )


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
        *,
        form_pack: Mapping[str, Any] | None = None,
        role_schema_index: ReviewedRoleSchemaIndex | None = None,
    ) -> None:
        self._authority = authority
        self._affordance_index = affordance_index
        self._config = config
        self.role_schema_index = role_schema_index or (
            ReviewedRoleSchemaIndex.from_pack(form_pack, authority, config)
            if form_pack is not None else None
        )
        if self.role_schema_index is not None:
            self.role_schema_index.validate_activation(authority, form_pack)
        self._designation_target_kinds = tuple(sorted({row.kind for row in authority.atoms.values() if type(row) is AtomRecord and row.reviewed}))
        self._language = "en"
        self._scope_values: Mapping[str, Mapping[str, str]] = {}
        self._link_schemas: Mapping[str, Mapping[str, Any]] = {}
        self._application_role_orders: Mapping[str, Mapping[str, Any]] = {}
        if form_pack is not None:
            language = form_pack.get("language", "en")
            if isinstance(language, str) and language:
                self._language = language
            sv = form_pack.get("scope_values", {})
            if isinstance(sv, dict):
                self._scope_values = {
                    k: dict(v) for k, v in sv.items()
                    if isinstance(v, dict)
                }
            ls = form_pack.get("link_schemas", {})
            if isinstance(ls, dict):
                self._link_schemas = {
                    k: dict(v) for k, v in ls.items()
                    if isinstance(v, dict)
                }
            role_orders = form_pack.get("application_role_orders", {})
            if isinstance(role_orders, dict):
                self._application_role_orders = {
                    key: dict(value)
                    for key, value in role_orders.items()
                    if isinstance(key, str) and isinstance(value, dict)
                }

    def build(
        self,
        *,
        orientation: Orientation,
        evidence: EvidencePacket,
        form_lattice: FormLattice,
        grounding_result: GroundingResult,
        contributions: tuple[SemanticContribution, ...],
        designation_batch: Any = None,
    ) -> ProposalContext:
        if designation_batch is not None:
            if designation_batch.reader.authority is not self._authority:
                raise ValueError("designation batch owner differs from context authority")
            if designation_batch.pin != orientation.revision_pin:
                raise ValueError("designation batch pin differs from context pin")
            designation_batch._check()
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
        if orientation.mode is SemanticMode.QUERY:
            lexical_contributions, lexical_frames, lexical_variables = _explicit_lexical_query_evidence(form_lattice, self._authority, self._designation_target_kinds)
            if lexical_frames:
                # The complete reviewed construction mentions the literal;
                # its constituent designations are evidence, not predicates.
                forms, _ = self._form_evidence_slots(orientation, form_lattice, {})
                slots = _bounded_unique_contributions((*forms, *lexical_contributions), self._config)
                consumed = {ref for row in slots if not _is_orthographic_evidence(row) for ref in row.source_unit_refs}
                return ProposalContext.create(
                    orientation_ref=orientation.orientation_ref, evidence_packet_ref=evidence.packet_ref,
                    form_lattice_ref=form_lattice.lattice_ref, grounding_ref=grounding_result.grounding_ref,
                    designation_slots=designation_slots, contribution_slots=slots,
                    mode_slots=(_mode_slot(orientation, form_lattice),), application_frames=lexical_frames,
                    reference_slots=(), scope_slots=(), expression_link_slots=(), variable_slots=lexical_variables,
                    transition_slots=(), residual_evidence=_residual_evidence(form_lattice, consumed),
                    context_refs=_orientation_context_refs(orientation, self._config),
                    source_unit_refs=tuple(row.unit_ref for row in form_lattice.units),
                    source_unit_spans=source_spans, revision_pin=orientation.revision_pin, config=self._config)
        nominal_source_refs = {
            designation.slot_ref: _expanded_nominal_source_refs(
                designation,
                form_lattice,
                unit_by_ref,
            )
            for designation in designation_slots
        }
        reviewed_role_bindings = _reviewed_application_role_bindings(
            designation_slots,
            form_lattice,
            unit_by_ref,
            self._application_role_orders,
            self._config,
        )
        participant_role_bindings = _reviewed_participant_form_role_bindings(
            orientation,
            designation_slots,
            form_lattice,
            unit_by_ref,
            self._application_role_orders,
            self._authority.atoms,
            self._config,
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
            participant_role_bindings,
        )
        capability_query_mode = self._capability_query_mode_evidence(
            orientation,
            designation_slots,
            form_lattice,
        )
        contribution_slots = _bounded_unique_contributions(
            (*semantic_contributions, *form_contributions, *capability_query_mode),
            self._config,
        )
        all_role_matches = self.role_schema_index.matches(
            designation_slots, contribution_slots, source_spans
        ) if self.role_schema_index is not None else ()
        role_matches = relation_projection_matches(self.role_schema_index, all_role_matches) if self.role_schema_index is not None else ()
        declarative_matches = relation_declarative_matches(self.role_schema_index, all_role_matches) if self.role_schema_index is not None else ()
        communication_matches = tuple(m for m in all_role_matches if type(m) is CommunicativeRoleMatch
                                      and orientation.mode is SemanticMode.OBSERVE)
        reviewed_role_bindings = dict(reviewed_role_bindings)
        for match in role_matches:
            reviewed_role_bindings[match.referent_slot_ref] = (match.referent_role,)
        mixed_designations: dict[str, list[str]] = {}
        mixed_participants: dict[str, list[str]] = {}
        for match in (*declarative_matches, *communication_matches):
            for binding in match.bindings:
                if binding.role not in {"role:subject", "role:object", "role:actor", "role:addressee"}:
                    continue
                if binding.designation_slot_ref is not None:
                    mixed_designations.setdefault(binding.designation_slot_ref, []).append(binding.role)
                else:
                    mixed_participants.setdefault(binding.source_unit_refs[0], []).append(binding.role)
        reviewed_role_bindings.update({ref: tuple(dict.fromkeys(roles)) for ref, roles in mixed_designations.items()})
        if mixed_participants:
            participant_role_bindings = dict(participant_role_bindings)
            participant_role_bindings.update({ref: tuple(dict.fromkeys(roles)) for ref, roles in mixed_participants.items()})
            form_contributions, form_references = self._form_evidence_slots(orientation, form_lattice, participant_role_bindings)
            contribution_slots = _bounded_unique_contributions(
                (*semantic_contributions, *form_contributions, *capability_query_mode), self._config)
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

        application_frames, event_signatures = self._application_frames(
            designation_slots,
            profiles_by_target,
            predicate_targets,
        )
        application_frames, contribution_slots = _nominal_predication_evidence(
            application_frames, contribution_slots, form_lattice,
            subject_person_query=orientation.mode is SemanticMode.QUERY,
        )
        definition_spans = self.definition_label_spans(
            tuple(frame.source_unit_refs for frame in application_frames
                if frame.predicate_kind == "event_type" and {"role:surface", "role:target"} <= set(frame.required_roles)
                ), form_lattice,
        )
        mentioned_sources = {ref for span in definition_spans
            if ("discourse", "definition_marker") in unit_by_ref[span.marker_ref].features
            for ref in span.source_refs}
        application_frames = tuple(frame for frame in application_frames
            if not set(frame.source_unit_refs) <= mentioned_sources)
        learning_surface_contributions = self._learning_surface_evidence(
            application_frames,
            form_lattice,
            unit_by_ref,
            definition_spans,
        )
        if learning_surface_contributions:
            contribution_slots = _bounded_unique_contributions(
                (*contribution_slots, *learning_surface_contributions),
                self._config,
            )
        state_value_contributions, state_value_frames = (
            self._state_value_application_evidence(
                designation_slots,
                contribution_slots,
                form_lattice,
                unit_by_ref,
                reviewed_role_bindings,
            )
        )
        if state_value_contributions:
            contribution_slots = _bounded_unique_contributions(
                (*contribution_slots, *state_value_contributions),
                self._config,
            )
            application_frames = _bounded_unique_slots(
                (*application_frames, *state_value_frames),
                self._config.max_orientation_alternatives,
            )
        transition_contributions, transition_frames = (
            self._transition_value_application_evidence(
            designation_slots,
            application_frames,
            reviewed_role_bindings,
        )
        )
        if transition_frames:
            contribution_slots = _bounded_unique_contributions(
                (*contribution_slots, *transition_contributions),
                self._config,
            )
            application_frames = _bounded_unique_slots(
                (*application_frames, *transition_frames),
                self._config.max_orientation_alternatives,
            )
        teaching_contributions, teaching_frames = (
            self._prospective_designation_evidence(
                designation_slots,
                form_lattice,
                unit_by_ref,
                definition_spans,
            )
        )
        if teaching_contributions:
            contribution_slots = _bounded_unique_contributions(
                (*contribution_slots, *teaching_contributions),
                self._config,
            )
            application_frames = _bounded_unique_slots(
                (*application_frames, *teaching_frames),
                self._config.max_orientation_alternatives,
            )
        designation_contributions = self._designation_application_contributions(
            designation_slots,
            form_lattice,
            unit_by_ref,
            nominal_source_refs,
            designation_batch,
        )
        if designation_contributions:
            contribution_slots = _bounded_unique_contributions(
                (*contribution_slots, *designation_contributions),
                self._config,
            )
            application_frames = self._with_designation_fallback_frames(
                application_frames,
                designation_slots,
                designation_contributions,
            )
        # A target's affordances remain available outside a naming literal;
        # inside it, its spelling is mentioned rather than applied.
        application_frames = tuple(frame for frame in application_frames
            if not set(frame.source_unit_refs) <= mentioned_sources)
        mode_slots = (
            _mode_slot(
                orientation,
                form_lattice,
                capability_query=any(
                    row.target_kind == "capability" for row in designation_slots
                ),
            ),
        )
        scope_slots = _scope_slots(
            form_lattice,
            self._config,
            self._scope_values,
            suppress_capability_query=(
                orientation.mode is SemanticMode.QUERY
                and any(row.target_kind == "capability" for row in designation_slots)
            ),
        )
        expression_link_slots = _expression_link_slots(
            form_lattice,
            self._config,
            self._link_schemas,
        )
        transition_slots = self._transition_slots(
            orientation.mode,
            application_frames,
        )
        # Predicate source ownership is unchanged: the witness names the exact
        # reviewed mixed match without consuming the query or referent twice.
        witnessed_frames = []
        for frame in application_frames:
            matches = tuple(m for m in role_matches if m.predicate_slot_ref == frame.designation_slot_ref
                            and frame.operator_ref == "op:relation")
            if matches:
                _, provenance = role_match_evidence(matches)
                values = {f.name: getattr(frame, f.name) for f in fields(frame) if f.name != "slot_ref"}
                values["provenance_refs"] = (*frame.provenance_refs, *provenance)
                frame = ApplicationFrameSlot.create(**values)
            communications = tuple(m for m in communication_matches
                if m.predicate_slot_ref == frame.designation_slot_ref
                and m.target_ref == frame.predicate_target_ref and m.frame_ref == frame.affordance_frame_ref)
            if communications:
                values = {f.name: getattr(frame, f.name) for f in fields(frame) if f.name != "slot_ref"}
                values["provenance_refs"] = tuple(dict.fromkeys((*frame.provenance_refs,
                    *(ref for match in communications for ref in match.provenance))))
                frame = ApplicationFrameSlot.create(**values)
            witnessed_frames.append(frame)
        application_frames = tuple(witnessed_frames)
        witnessed_contributions = []
        for contribution in contribution_slots:
            matches = tuple(m for m in role_matches if contribution.kind == "predicate"
                            and contribution.target_ref == next(d.target_ref for d in designation_slots if d.slot_ref == m.predicate_slot_ref)
                            and contribution.source_unit_refs == next(d.source_unit_refs for d in designation_slots if d.slot_ref == m.predicate_slot_ref))
            if matches:
                witness, provenance = role_match_evidence(matches)
                values = {f.name: getattr(contribution, f.name) for f in fields(contribution) if f.name != "slot_ref"}
                values["constraints"] = (*contribution.constraints, *witness)
                values["provenance_refs"] = (*contribution.provenance_refs, *provenance)
                contribution = ContributionSlot.create(**values)
            witnessed_contributions.append(contribution)
        contribution_slots = tuple(witnessed_contributions)
        reference_contributions, designation_references = (
            self._designation_reference_evidence(
                designation_slots,
                application_frames,
                event_signatures,
                contribution_slots,
                nominal_source_refs,
                reviewed_role_bindings,
                form_lattice,
            )
        )
        designation_references = self._clause_local_reference_slots(
            designation_references, application_frames, form_lattice
        )
        form_references = self._clause_local_reference_slots(
            form_references, application_frames, form_lattice
        )
        coordinated_references = self._coordinated_reference_slots(
            designation_references,
            expression_link_slots,
        )
        reported_references = self._reported_speaker_coreferences(
            (*designation_references, *form_references),
            application_frames,
            event_signatures,
            form_lattice,
        )
        contribution_slots = _bounded_unique_contributions(
            (*reference_contributions, *contribution_slots),
            self._config,
        )
        situated_references = self._situated_participant_references(
            orientation,
            application_frames,
            event_signatures,
            (*designation_references, *form_references),
            form_lattice,
        )
        reference_slots = _bounded_unique_slots(
            (
                *designation_references,
                *coordinated_references,
                *reported_references,
                *form_references,
                *situated_references,
            ),
            self._config.max_orientation_alternatives,
        )
        variable_slots = _variable_slots(
            form_lattice,
            contribution_slots,
            application_frames,
            self._config,
            role_matches=role_matches,
        )
        # Preserve the existing one-residual representation when an unresolved
        # primitive reference has no competing contribution on its source.
        # An overlapping designation instead retains the typed requirement so
        # independent construction rematching can still see the observation.
        unresolved_references = frozenset(row.slot_ref for row in contribution_slots
            if row.kind == "reference" and row.target_ref is None and row.constraints
            and row.constraints[0][0] == "participant")
        designation_owners = frozenset((row.target_ref, row.source_unit_refs) for row in designation_slots)
        designated_sources = frozenset(ref for row in contribution_slots
            if row.slot_ref not in unresolved_references
            and (row.target_ref, row.source_unit_refs) in designation_owners
            for ref in row.source_unit_refs)
        contribution_slots = tuple(row for row in contribution_slots
            if row.slot_ref not in unresolved_references
            or any(ref in designated_sources for ref in row.source_unit_refs))
        consumed = {
            source_ref
            for contribution in contribution_slots
            if not _is_orthographic_evidence(contribution)
            for source_ref in contribution.source_unit_refs
        }
        residual_evidence = _residual_evidence(form_lattice, consumed)

        context = ProposalContext.create(
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
        # Publish only actual activated matches after all ordinary form owners
        # have constructed the exact immutable evidence envelope.
        projections = licensed_query_projection_slots(self.role_schema_index, context)
        if not projections:
            return context
        values = {row.name: getattr(context, row.name) for row in fields(context)
            if row.init and row.name not in {"context_ref", "abi_version"}}
        values["query_projection_slots"] = projections
        return ProposalContext.create(**values, config=self._config)

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
            if any(("orthography", "quotation_boundary") in unit_by_ref[ref].features
                   for ref in candidate.unit_refs):
                # A designation proves identity, never quotation ownership.
                # Retain other source-local alternatives without licensing an
                # unsupported boundary inside this particular occurrence.
                continue
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

    def _designation_application_contributions(
        self,
        designations: tuple[DesignationSlot, ...],
        form_lattice: FormLattice,
        unit_by_ref: Mapping[str, Any],
        nominal_source_refs: Mapping[str, tuple[str, ...]],
        designation_batch: Any = None,
    ) -> tuple[ContributionSlot, ...]:
        """Expose one explicit designation fact as a complete kernel relation.

        The designation target and exact reviewed source span are already
        authenticated by grounding.  This adds no lexical inference: it only
        provides the structural predicate proof and the literal surface role
        needed to lower that existing fact to ``op:designation``.
        """
        rows: list[ContributionSlot] = []
        index = getattr(self._authority, "designations", None)
        canonical_lookup = getattr(index, "canonical_surface_for_target", None)
        if not callable(canonical_lookup):
            return ()
        label_type = self._authority.atoms.get("label:lexical")
        if (
            not isinstance(label_type, AtomRecord)
            or label_type.kind != "label_type"
            or not label_type.reviewed
        ):
            raise ValueError(
                "designation application requires reviewed label:lexical authority"
            )
        label_type_ref = label_type.ref
        source_text = form_lattice.source_text
        source_start = len(source_text) - len(source_text.lstrip())
        source_end = len(source_text.rstrip())
        for designation in designations:
            application_source_refs = nominal_source_refs.get(
                designation.slot_ref,
                designation.source_unit_refs,
            )
            spans = tuple(
                (
                    unit_by_ref[source_ref].source_start,
                    unit_by_ref[source_ref].source_end,
                )
                for source_ref in application_source_refs
            )
            start = min(row[0] for row in spans)
            end = max(row[1] for row in spans)
            if start != source_start or end != source_end:
                continue
            designation_spans = tuple(
                (
                    unit_by_ref[source_ref].source_start,
                    unit_by_ref[source_ref].source_end,
                )
                for source_ref in designation.source_unit_refs
            )
            designation_start = min(row[0] for row in designation_spans)
            designation_end = max(row[1] for row in designation_spans)
            observed_surface = form_lattice.source_text[
                designation_start:designation_end
            ].strip()
            if not observed_surface:
                raise ValueError("designation source span has no surface value")
            if designation_batch is None:
                surface = canonical_lookup(observed_surface, designation.target_ref, self._language)
            else:
                candidates = designation_batch.canonical_surface_for_target(
                    designation.target_ref, self._language, observed_surface,
                    maximum=self._config.max_orientation_alternatives,
                )
                matches = tuple(row for row in candidates
                    if row.designation.designation_fact_ref == designation.designation_fact_ref)
                surface = matches[0].designation.surface if matches else None
            if surface is None:
                continue
            provenance = tuple(
                dict.fromkeys(
                    (
                        designation.slot_ref,
                        designation.designation_fact_ref,
                        *designation.provenance_refs,
                    )
                )
            )
            rows.append(
                ContributionSlot.create(
                    contribution_ref=stable_ref(
                        "designation_application_predicate",
                        {
                            "designation_slot_ref": designation.slot_ref,
                            "label_type_ref": label_type_ref,
                            "target_ref": designation.target_ref,
                            "target_kind": designation.target_kind,
                        },
                    ),
                    kind="predicate",
                    source_unit_refs=application_source_refs,
                    target_ref=label_type_ref,
                    target_kind="label_type",
                    input_ports=("role:surface",),
                    output_ports=("role:label_type",),
                    constraints=(
                        ("designation_fact_ref", designation.designation_fact_ref),
                        ("operator_ref", "op:designation"),
                    ),
                    provenance_refs=provenance,
                )
            )
            rows.append(
                ContributionSlot.create(
                    contribution_ref=stable_ref(
                        "designation_surface_literal",
                        {
                            "designation_slot_ref": designation.slot_ref,
                            "surface": surface,
                            "source_unit_refs": list(application_source_refs),
                        },
                    ),
                    kind="literal",
                    source_unit_refs=application_source_refs,
                    target_ref=None,
                    target_kind=None,
                    input_ports=(),
                    output_ports=("role:surface",),
                    constraints=(
                        ("literal", surface),
                        ("literal_kind", "string"),
                    ),
                    provenance_refs=provenance,
                    literal_value=surface,
                )
            )
        return tuple(rows)

    @staticmethod
    def definition_label_spans(
        naming_sources: tuple[tuple[str, ...], ...],
        form_lattice: FormLattice,
    ) -> tuple[_DefinitionLabelSpan, ...]:
        """Collect contiguous labels at local, reviewed definition boundaries.

        Known open-class words can be part of a literal. Structural evidence
        cannot be skipped to concatenate words across clauses or quotation.
        A naming frame owns only the label immediately following its evidence,
        optionally through one reviewed content linker.
        """
        units = tuple(unit for unit in form_lattice.units if not unit.source_text.isspace())
        positions = {unit.unit_ref: index for index, unit in enumerate(units)}
        naming_sources = tuple(tuple(ref for ref in source if ref in positions) for source in naming_sources)
        spans = []
        for index, marker in enumerate(units):
            if not ({("discourse", "definition_marker"), ("binder", "copula")} & set(marker.features)):
                continue
            cursor = index - 1
            while cursor >= 0:
                unit = units[cursor]
                if unit.features or not any(c.isalnum() for c in unit.source_text):
                    break
                cursor -= 1
            label_units = units[cursor + 1:index]
            if not label_units:
                continue
            if cursor >= 0 and {("orthography", "punctuation"),
                                ("orthography", "quotation_boundary")} & set(units[cursor].features):
                # Generic punctuation does not prove whether this starts a
                # quotation. Do not reinterpret an unclosed quote as a label.
                continue
            target_end = next(
                (unit.source_start for unit in units[index + 1:] if unit.features),
                len(form_lattice.source_text),
            )
            label_refs = tuple(unit.unit_ref for unit in label_units)
            prefixes = tuple(dict.fromkeys(source for source in naming_sources
                if len(source) < len(label_refs) and label_refs[:len(source)] == source))
            if prefixes:
                # Only a predicate at the construction's left edge owns the
                # directive. Later event words remain inside the exact literal.
                for prefix in prefixes:
                    spans.append(_DefinitionLabelSpan(label_refs[len(prefix):], marker.unit_ref,
                        (marker.unit_ref,), prefix[-1], target_end))
            else:
                owner = None
                support = (marker.unit_ref,)
                if cursor > 0 and ("linker", "content_linker") in units[cursor].features:
                    owner_source = next((source for source in naming_sources if source and source[-1] == units[cursor - 1].unit_ref), None)
                    if owner_source is not None:
                        before_owner = positions[owner_source[0]] - 1
                        if before_owner >= 0 and {("orthography", "punctuation"),
                                                 ("orthography", "quotation_boundary")} & set(units[before_owner].features):
                            continue
                        owner = owner_source[-1]
                        support = (units[cursor].unit_ref, *support)
                spans.append(_DefinitionLabelSpan(label_refs, marker.unit_ref, support, owner, target_end))
        return tuple(spans)

    def _prospective_designation_evidence(
        self,
        designations: tuple[DesignationSlot, ...],
        form_lattice: FormLattice,
        unit_by_ref: Mapping[str, Any],
        definition_spans: tuple[_DefinitionLabelSpan, ...],
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ApplicationFrameSlot, ...]]:
        """Lower a form-proved teaching claim without prelinking its new label.

        The language pack proves the definition boundary, while the designation
        index proves only the target on the other side.  The prospective span
        remains a literal; it never receives an invented semantic identity.
        """
        if not definition_spans:
            return (), ()
        designated_sources = {
            source_ref
            for designation in designations
            for source_ref in designation.source_unit_refs
        }
        rows: list[ContributionSlot] = []
        frames: list[ApplicationFrameSlot] = []
        local_targets = (
            (designation, span)
            for span in definition_spans
            for designation in designations
            if all(
                unit_by_ref[span.marker_ref].source_end <= unit_by_ref[ref].source_start
                and unit_by_ref[ref].source_end <= span.target_end
                for ref in designation.source_unit_refs
            )
            # Copular predication is not evidence that a known subject is a
            # lexical label. Preserve the unknown-label hypothesis only.
            if ("binder", "copula") not in unit_by_ref[span.marker_ref].features
            or not any(ref in designated_sources for ref in span.source_refs)
        )
        for designation, span in local_targets:
            surface_refs = span.source_refs
            start = min(unit_by_ref[ref].source_start for ref in surface_refs)
            end = max(unit_by_ref[ref].source_end for ref in surface_refs)
            surface = form_lattice.source_text[start:end].strip()
            if not surface:
                continue
            label_type = self._authority.atoms.get("label:lexical")
            if (
                not isinstance(label_type, AtomRecord)
                or label_type.kind != "label_type"
                or not label_type.reviewed
            ):
                raise ValueError(
                    "prospective designation requires reviewed label:lexical authority"
                )
            label_type_ref = label_type.ref
            support_refs = (span.marker_ref,)
            application_source_refs = tuple(
                dict.fromkeys(
                    (*surface_refs, *support_refs, *designation.source_unit_refs)
                )
            )
            teaching_ref = stable_ref(
                "prospective_designation_teaching_evidence",
                {
                    "designation_slot_ref": designation.slot_ref,
                    "surface_refs": list(surface_refs),
                    "marker_refs": list(support_refs),
                    "target_ref": designation.target_ref,
                },
            )
            provenance = tuple(
                dict.fromkeys(
                    (
                        designation.slot_ref,
                        designation.designation_fact_ref,
                        *designation.provenance_refs,
                        *support_refs,
                        teaching_ref,
                    )
                )
            )
            rows.extend(
                (
                    ContributionSlot.create(
                        contribution_ref=stable_ref(
                            "prospective_designation_predicate",
                            {
                                "teaching_ref": teaching_ref,
                                "label_type_ref": label_type_ref,
                                "target_ref": designation.target_ref,
                            },
                        ),
                        kind="predicate",
                        source_unit_refs=application_source_refs,
                        target_ref=label_type_ref,
                        target_kind="label_type",
                        input_ports=("role:surface",),
                        output_ports=("role:label_type",),
                        constraints=(
                            ("designation_fact_ref", designation.designation_fact_ref),
                            ("operator_ref", "op:designation"),
                            ("prospective_designation", "teaching_claim"),
                            ("teaching_evidence_ref", teaching_ref),
                        ),
                        provenance_refs=provenance,
                    ),
                    ContributionSlot.create(
                        contribution_ref=stable_ref(
                            "prospective_designation_surface_literal",
                            {
                                "teaching_ref": teaching_ref,
                                "surface": surface,
                            },
                        ),
                        kind="literal",
                        source_unit_refs=application_source_refs,
                        target_ref=None,
                        target_kind=None,
                        input_ports=(),
                        output_ports=("role:surface",),
                        constraints=(
                            ("literal", surface),
                            ("literal_kind", "string"),
                            ("prospective_designation", "teaching_claim"),
                            ("prospective_designation_target", designation.target_ref),
                            ("teaching_evidence_ref", teaching_ref),
                        ),
                        provenance_refs=provenance,
                        literal_value=surface,
                    ),
                )
            )
            frames.append(
                ApplicationFrameSlot.create(
                    designation_slot_ref=designation.slot_ref,
                    predicate_target_ref=label_type_ref,
                    predicate_kind="label_type",
                    operator_ref="op:designation",
                    structural_role_ref="role:label_type",
                    required_roles=("role:surface",),
                    optional_roles=(),
                    proposition_roles=(),
                    source_unit_refs=application_source_refs,
                    derived_role_targets=(
                        ("role:label_type", label_type_ref),
                        ("role:target", designation.target_ref),
                    ),
                    affordance_frame_ref=None,
                    provenance_refs=provenance,
                )
            )
            if len(frames) >= self._config.max_orientation_alternatives:
                break
        return tuple(rows), tuple(frames)

    def _with_designation_fallback_frames(
        self,
        frames: tuple[ApplicationFrameSlot, ...],
        designations: tuple[DesignationSlot, ...],
        contributions: tuple[ContributionSlot, ...],
    ) -> tuple[ApplicationFrameSlot, ...]:
        """Append bounded designation frames for authenticated full surfaces."""
        rows = list(frames)
        for designation in designations:
            if len(rows) >= self._config.max_orientation_alternatives:
                break
            predicate = next(
                (
                    row
                    for row in contributions
                    if row.kind == "predicate"
                    and row.target_kind == "label_type"
                    and row.input_ports == ("role:surface",)
                    and row.output_ports == ("role:label_type",)
                    and (
                        "designation_fact_ref",
                        designation.designation_fact_ref,
                    )
                    in row.constraints
                ),
                None,
            )
            if predicate is None:
                continue
            frame = ApplicationFrameSlot.create(
                designation_slot_ref=designation.slot_ref,
                predicate_target_ref=predicate.target_ref,
                predicate_kind="label_type",
                operator_ref="op:designation",
                structural_role_ref="role:label_type",
                required_roles=("role:surface",),
                optional_roles=(),
                proposition_roles=(),
                source_unit_refs=predicate.source_unit_refs,
                derived_role_targets=(
                    ("role:label_type", predicate.target_ref),
                    ("role:target", designation.target_ref),
                ),
                affordance_frame_ref=None,
                provenance_refs=tuple(
                    dict.fromkeys(
                        (
                            designation.slot_ref,
                            designation.designation_fact_ref,
                            *designation.provenance_refs,
                        )
                    )
                ),
            )
            if all(existing.slot_ref != frame.slot_ref for existing in rows):
                rows.append(frame)
        return tuple(rows)

    def _state_value_application_evidence(
        self,
        designations: tuple[DesignationSlot, ...],
        contributions: tuple[ContributionSlot, ...],
        form_lattice: FormLattice,
        unit_by_ref: Mapping[str, Any],
        reviewed_role_bindings: Mapping[str, tuple[str, ...]],
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ApplicationFrameSlot, ...]]:
        """Lower a reviewed state value/dimension link into one state graph."""
        predicate_rows: list[ContributionSlot] = []
        frames: list[ApplicationFrameSlot] = []
        binder_refs = tuple(
            unit.unit_ref
            for unit in form_lattice.units
            if any(category == "binder" for category, _ in unit.features)
        )
        coordination_refs = tuple(
            unit.unit_ref
            for unit in form_lattice.units
            if any(category == "connector" for category, _ in unit.features)
        )
        if not binder_refs:
            return (), ()
        def local_binder_refs(source_unit_refs: tuple[str, ...]) -> tuple[str, ...]:
            value_units = tuple(unit_by_ref[ref] for ref in source_unit_refs)
            value_start = min(unit.source_start for unit in value_units)
            value_end = max(unit.source_end for unit in value_units)
            scored = []
            for ref in binder_refs:
                unit = unit_by_ref[ref]
                if unit.source_end <= value_start:
                    distance = value_start - unit.source_end
                elif value_end <= unit.source_start:
                    distance = unit.source_start - value_end
                else:
                    distance = 0
                scored.append((distance, unit.source_start, unit.source_end, ref))
            if not scored:
                return ()
            best_distance = min(distance for distance, *_rest in scored)
            return tuple(ref for distance, _start, _end, ref in scored if distance == best_distance)

        for designation in designations:
            if (
                designation.target_kind != "state_value"
                or "role:value"
                not in reviewed_role_bindings.get(designation.slot_ref, ())
            ):
                continue
            dimension_ref = self._authority.value_dimensions.get(
                designation.target_ref
            )
            dimension = self._authority.atoms.get(dimension_ref)
            if not isinstance(dimension, AtomRecord) or dimension.kind != "state_dimension":
                continue
            source_refs = tuple(
                unit.unit_ref
                for unit in sorted(
                    (
                        unit_by_ref[ref]
                        for ref in {
                            *designation.source_unit_refs,
                            *local_binder_refs(designation.source_unit_refs),
                        }
                    ),
                    key=lambda unit: (
                        unit.source_start,
                        unit.source_end,
                        unit.unit_ref,
                    ),
                )
            )
            provenance = tuple(
                dict.fromkeys(
                    (
                        designation.slot_ref,
                        designation.designation_fact_ref,
                        dimension_ref,
                        *designation.provenance_refs,
                        *(
                            row.slot_ref
                            for row in contributions
                            if row.kind == "predicate"
                            and row.target_ref == designation.target_ref
                            and row.source_unit_refs
                            == designation.source_unit_refs
                        ),
                    )
                )
            )
            predicate = ContributionSlot.create(
                contribution_ref=stable_ref(
                    "state_value_dimension_predicate",
                    {
                        "designation_slot_ref": designation.slot_ref,
                        "value_ref": designation.target_ref,
                        "dimension_ref": dimension_ref,
                        "source_unit_refs": list(source_refs),
                    },
                ),
                kind="predicate",
                source_unit_refs=source_refs,
                target_ref=dimension_ref,
                target_kind="state_dimension",
                input_ports=("role:subject",),
                output_ports=("role:dimension",),
                constraints=(
                    ("state_value_ref", designation.target_ref),
                    ("value_dimension_ref", dimension_ref),
                ),
                provenance_refs=provenance,
            )
            frame = ApplicationFrameSlot.create(
                designation_slot_ref=designation.slot_ref,
                predicate_target_ref=dimension_ref,
                predicate_kind="state_dimension",
                operator_ref="op:state",
                structural_role_ref="role:dimension",
                required_roles=("role:subject",),
                optional_roles=(),
                proposition_roles=(),
                source_unit_refs=source_refs,
                derived_role_targets=(
                    ("role:dimension", dimension_ref),
                    ("role:value", designation.target_ref),
                ),
                affordance_frame_ref=None,
                provenance_refs=provenance,
            )
            predicate_rows.append(predicate)
            frames.append(frame)
            if coordination_refs:
                coordinated_provenance = tuple(
                    dict.fromkeys((*provenance, *binder_refs, *coordination_refs))
                )
                coordinated_predicate = ContributionSlot.create(
                    contribution_ref=stable_ref(
                        "coordinated_state_value_dimension_predicate",
                        {
                            "designation_slot_ref": designation.slot_ref,
                            "value_ref": designation.target_ref,
                            "dimension_ref": dimension_ref,
                            "coordination_refs": list(coordination_refs),
                        },
                    ),
                    kind="predicate",
                    source_unit_refs=designation.source_unit_refs,
                    target_ref=dimension_ref,
                    target_kind="state_dimension",
                    input_ports=("role:subject",),
                    output_ports=("role:dimension",),
                    constraints=(
                        ("state_value_ref", designation.target_ref),
                        ("value_dimension_ref", dimension_ref),
                        ("binder_inheritance", "coordinated"),
                    ),
                    provenance_refs=coordinated_provenance,
                )
                coordinated_frame = ApplicationFrameSlot.create(
                    designation_slot_ref=designation.slot_ref,
                    predicate_target_ref=dimension_ref,
                    predicate_kind="state_dimension",
                    operator_ref="op:state",
                    structural_role_ref="role:dimension",
                    required_roles=("role:subject",),
                    optional_roles=(),
                    proposition_roles=(),
                    source_unit_refs=designation.source_unit_refs,
                    derived_role_targets=(
                        ("role:dimension", dimension_ref),
                        ("role:value", designation.target_ref),
                    ),
                    affordance_frame_ref=None,
                    provenance_refs=coordinated_provenance,
                )
                predicate_rows.append(coordinated_predicate)
                frames.append(coordinated_frame)
        return tuple(predicate_rows), tuple(frames)

    def _learning_surface_evidence(
        self,
        frames: tuple[ApplicationFrameSlot, ...],
        form_lattice: FormLattice,
        unit_by_ref: Mapping[str, Any],
        definition_spans: tuple[_DefinitionLabelSpan, ...],
    ) -> tuple[ContributionSlot, ...]:
        """Expose bounded label literals only inside a reviewed naming frame."""
        naming_frames = tuple(
            frame
            for frame in frames
            if frame.predicate_kind == "event_type"
            and {"role:surface", "role:target"} <= set(frame.required_roles)
        )
        if not naming_frames:
            return ()
        # A grounded word alone is not evidence of a naming literal. The old
        # markerless cross-product fabricated surface/target roles globally.
        literal_sources = (
            (span.source_refs, span.support_refs, tuple(frame for frame in naming_frames
                if span.naming_source_ref in frame.source_unit_refs))
            for span in definition_spans
            if ("discourse", "definition_marker") in unit_by_ref[span.marker_ref].features
        )
        rows: list[ContributionSlot] = []
        for source_refs, support_refs, local_frames in literal_sources:
            units = tuple(unit_by_ref[ref] for ref in source_refs)
            start = min(unit.source_start for unit in units)
            end = max(unit.source_end for unit in units)
            literal = form_lattice.source_text[start:end].strip()
            if not literal:
                continue
            contribution_source_refs = tuple(dict.fromkeys((*source_refs, *support_refs)))
            for frame in local_frames:
                provenance = tuple(
                    dict.fromkeys(
                        (frame.slot_ref, *frame.provenance_refs, *support_refs)
                    )
                )
                rows.append(
                    ContributionSlot.create(
                        contribution_ref=stable_ref(
                            "reviewed_naming_surface_literal",
                            {
                                "frame_slot_ref": frame.slot_ref,
                                "source_unit_refs": list(contribution_source_refs),
                                "literal": literal,
                            },
                        ),
                        kind="literal",
                        source_unit_refs=contribution_source_refs,
                        target_ref=None,
                        target_kind=None,
                        input_ports=(),
                        output_ports=("role:surface",),
                        constraints=(
                            ("literal", literal),
                            ("literal_kind", "string"),
                            ("naming_frame_ref", frame.slot_ref),
                        ),
                        provenance_refs=provenance,
                        literal_value=literal,
                    )
                )
                if len(rows) >= self._config.max_orientation_alternatives:
                    return tuple(rows)
        return tuple(rows)

    def _transition_value_application_evidence(
        self,
        designations: tuple[DesignationSlot, ...],
        frames: tuple[ApplicationFrameSlot, ...],
        reviewed_role_bindings: Mapping[str, tuple[str, ...]],
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ApplicationFrameSlot, ...]]:
        """Bind a reviewed state value and its dimension inside an effect frame."""
        contributions: list[ContributionSlot] = []
        rows: list[ApplicationFrameSlot] = []
        values = tuple(
            row
            for row in designations
            if row.target_kind == "state_value"
            and "role:value" in reviewed_role_bindings.get(row.slot_ref, ())
        )
        if not values:
            return (), ()
        for frame in frames:
            signature = self._authority.by_event_signature(
                frame.predicate_target_ref
            )
            if (
                frame.operator_ref != "op:event"
                or signature is None
                or signature.adapter_ref is None
                or not {"role:dimension", "role:value"}
                <= set(frame.required_roles)
            ):
                continue
            for designation in values:
                dimension_ref = self._authority.value_dimensions.get(
                    designation.target_ref
                )
                if dimension_ref is None:
                    continue
                provenance = tuple(
                    dict.fromkeys(
                        (
                            frame.slot_ref,
                            *frame.provenance_refs,
                            designation.designation_fact_ref,
                            dimension_ref,
                        )
                    )
                )
                source_unit_refs = tuple(
                    dict.fromkeys(
                        (*frame.source_unit_refs, *designation.source_unit_refs)
                    )
                )
                required_roles = tuple(
                    role
                    for role in frame.required_roles
                    if role not in {"role:dimension", "role:value"}
                )
                contributions.append(
                    ContributionSlot.create(
                        contribution_ref=stable_ref(
                            "transition_value_event_predicate",
                            {
                                "frame_slot_ref": frame.slot_ref,
                                "designation_slot_ref": designation.slot_ref,
                                "dimension_ref": dimension_ref,
                            },
                        ),
                        kind="predicate",
                        source_unit_refs=source_unit_refs,
                        target_ref=frame.predicate_target_ref,
                        target_kind=frame.predicate_kind,
                        input_ports=required_roles,
                        output_ports=(frame.structural_role_ref,),
                        constraints=(
                            ("effect_frame_ref", frame.slot_ref),
                            ("state_value_ref", designation.target_ref),
                            ("value_dimension_ref", dimension_ref),
                        ),
                        provenance_refs=provenance,
                    )
                )
                rows.append(
                    ApplicationFrameSlot.create(
                        designation_slot_ref=frame.designation_slot_ref,
                        predicate_target_ref=frame.predicate_target_ref,
                        predicate_kind=frame.predicate_kind,
                        operator_ref=frame.operator_ref,
                        structural_role_ref=frame.structural_role_ref,
                        required_roles=required_roles,
                        optional_roles=frame.optional_roles,
                        proposition_roles=frame.proposition_roles,
                        source_unit_refs=source_unit_refs,
                        derived_role_targets=(
                            ("role:dimension", dimension_ref),
                            ("role:value", designation.target_ref),
                        ),
                        affordance_frame_ref=frame.affordance_frame_ref,
                        provenance_refs=provenance,
                    )
                )
                if len(rows) >= self._config.max_orientation_alternatives:
                    return tuple(contributions), tuple(rows)
        return tuple(contributions), tuple(rows)

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
        per_occurrence: dict[tuple[str, tuple[str, ...]], int] = {}
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
            if any(("orthography", "quotation_boundary") in unit_by_ref[ref].features
                   for ref in contribution.source_unit_refs):
                continue
            target_kind: str | None = None
            if contribution.target_ref is not None:
                if contribution.target_ref not in selected_targets:
                    continue
                atom = self._authority.atoms.get(contribution.target_ref)
                if not isinstance(atom, AtomRecord):
                    raise ValueError("contribution target is absent from authority")
                target_kind = atom.kind
                occurrence = (contribution.target_ref, contribution.source_unit_refs)
                count = per_occurrence.get(occurrence, 0)
                if count >= maximum:
                    continue
                per_occurrence[occurrence] = count + 1
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
        participant_role_bindings: Mapping[str, tuple[str, ...]],
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ReferenceSlot, ...]]:
        contributions: list[ContributionSlot] = []
        references: list[ReferenceSlot] = []
        for unit in form_lattice.units:
            for category, value in unit.features:
                contribution_kind, constraints = _primitive_form_signature(category, value, unit.features)
                if contribution_kind is None:
                    continue
                if category == "orthography":
                    contributions.append(ContributionSlot.create(
                        contribution_ref=_primitive_form_ref(unit.unit_ref, category, value),
                        kind="discourse", source_unit_refs=(unit.unit_ref,),
                        target_ref=None, target_kind=None, input_ports=(), output_ports=(),
                        constraints=constraints, provenance_refs=(unit.unit_ref,),
                    ))
                    continue
                if category == "participant":
                    target = _participant_feature_target(
                        value,
                        orientation,
                        self._authority.atoms,
                    )
                    if target is None:
                        # A failed deictic resolution is still observed,
                        # argument-critical form evidence, not an absent form.
                        # Retain the primitive requirement without inventing a
                        # referent or a ReferenceSlot that could bind a role.
                        contributions.append(ContributionSlot.create(
                            contribution_ref=_primitive_form_ref(unit.unit_ref, category, value),
                            kind=contribution_kind, source_unit_refs=(unit.unit_ref,),
                            target_ref=None, target_kind=None, input_ports=(),
                            output_ports=_primitive_form_ports("reference")[1], constraints=constraints,
                            provenance_refs=(unit.unit_ref,),
                        ))
                        continue
                    atom = self._authority.atoms.get(target)
                    if not isinstance(atom, AtomRecord):
                        continue
                    compatible_roles = participant_role_bindings.get(
                        unit.unit_ref, _reference_roles(atom.kind)
                    )
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
                    input_ports, output_ports = _primitive_form_ports("reference")
                    contributions.append(
                        ContributionSlot.create(
                            contribution_ref=_primitive_form_ref(unit.unit_ref, category, value, target),
                            kind="reference",
                            source_unit_refs=(unit.unit_ref,),
                            target_ref=target,
                            target_kind=atom.kind,
                            input_ports=input_ports,
                            output_ports=compatible_roles,
                            constraints=constraints,
                            provenance_refs=(unit.unit_ref,),
                        )
                    )
                    continue
                input_ports, output_ports = _primitive_form_ports(contribution_kind, category)
                contributions.append(
                    ContributionSlot.create(
                        contribution_ref=_primitive_form_ref(unit.unit_ref, category, value),
                        kind=contribution_kind,
                        source_unit_refs=(unit.unit_ref,),
                        target_ref=None,
                        target_kind=None,
                        input_ports=input_ports,
                        output_ports=output_ports,
                        constraints=constraints,
                        provenance_refs=(unit.unit_ref,),
                    )
                )
        return tuple(contributions), tuple(references)

    @staticmethod
    def _capability_query_mode_evidence(
        orientation: Orientation,
        designations: tuple[DesignationSlot, ...],
        form_lattice: FormLattice,
    ) -> tuple[ContributionSlot, ...]:
        if orientation.mode is not SemanticMode.QUERY or not any(
            row.target_kind == "capability" for row in designations
        ):
            return ()
        source_refs = tuple(
            unit.unit_ref
            for unit in form_lattice.units
            if any(
                category == "query"
                or (category == "modality" and value == "capability")
                for category, value in unit.features
            )
        )
        if not source_refs:
            return ()
        return (
            ContributionSlot.create(
                contribution_ref=stable_ref(
                    "capability_query_mode_evidence", source_refs
                ),
                kind="discourse",
                source_unit_refs=source_refs,
                target_ref=None,
                target_kind=None,
                input_ports=(),
                output_ports=("role:discourse",),
                constraints=(("semantic_mode_evidence", "capability_query"),),
                provenance_refs=source_refs,
            ),
        )

    def _designation_reference_evidence(
        self,
        designations: tuple[DesignationSlot, ...],
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
        existing_contributions: tuple[ContributionSlot, ...],
        nominal_source_refs: Mapping[str, tuple[str, ...]],
        reviewed_role_bindings: Mapping[str, tuple[str, ...]],
        form_lattice: FormLattice,
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ReferenceSlot, ...]]:
        contributions: list[ContributionSlot] = []
        references: list[ReferenceSlot] = []
        reported_clauses = _reported_clauses_from_lattice(
            frames, form_lattice, self._config
        )
        unit_by_ref = {row.unit_ref: row for row in form_lattice.units}
        for designation in designations:
            if designation.target_kind not in {
                "concept",
                "entity",
                "event_type",
                "participant",
                "relation_type",
                "state_dimension",
                "state_value",
            }:
                continue
            source_unit_refs = nominal_source_refs.get(
                designation.slot_ref,
                designation.source_unit_refs,
            )
            frame_choices: tuple[tuple[str | None, tuple[str, ...]], ...]
            designation_span = _source_span_for_units(source_unit_refs, unit_by_ref)
            containing_reports = tuple(
                row
                for row in reported_clauses
                if designation_span is not None
                and row.clause_start <= designation_span[0]
                and designation_span[1] <= row.content_end
            )
            if containing_reports:
                scoped: list[tuple[str | None, tuple[str, ...]]] = []
                for frame in frames:
                    allowed = False
                    for report in containing_reports:
                        if frame.slot_ref == report.parent_frame_ref:
                            allowed = (
                                designation_span is not None
                                and report.clause_start <= designation_span[0]
                                and designation_span[1] <= report.report_start
                            )
                        elif frame.slot_ref in report.child_frame_refs:
                            allowed = (
                                designation_span is not None
                                and report.report_end <= designation_span[0]
                                and designation_span[1] <= report.content_end
                            )
                        if allowed:
                            break
                    if not allowed:
                        continue
                    roles = self._compatible_reference_roles(
                        designation, (frame,), event_signatures
                    )
                    reviewed_roles = reviewed_role_bindings.get(designation.slot_ref)
                    if reviewed_roles is not None:
                        roles = tuple(role for role in roles if role in reviewed_roles)
                    if roles:
                        scoped.append((frame.slot_ref, roles))
                frame_choices = tuple(scoped)
            else:
                roles = self._compatible_reference_roles(
                    designation, frames, event_signatures
                )
                reviewed_roles = reviewed_role_bindings.get(designation.slot_ref)
                if reviewed_roles is not None:
                    roles = tuple(role for role in roles if role in reviewed_roles)
                frame_choices = ((None, roles),) if roles else ()
            if not frame_choices:
                continue
            roles = tuple(
                dict.fromkeys(
                    role for _frame_ref, choice_roles in frame_choices for role in choice_roles
                )
            )
            existing_roles = tuple(
                dict.fromkeys(
                    role
                    for row in existing_contributions
                    if row.kind == "reference"
                    and row.target_ref == designation.target_ref
                    and row.source_unit_refs == source_unit_refs
                    for role in row.output_ports
                )
            )
            if set(roles) <= set(existing_roles):
                contribution = next(
                    row
                    for row in existing_contributions
                    if row.kind == "reference"
                    and row.target_ref == designation.target_ref
                    and row.source_unit_refs == source_unit_refs
                )
            else:
                contribution = ContributionSlot.create(
                    contribution_ref=stable_ref(
                        "designation_reference_contribution",
                        {
                            "designation_slot_ref": designation.slot_ref,
                            "target_ref": designation.target_ref,
                            "target_kind": designation.target_kind,
                            "source_unit_refs": list(source_unit_refs),
                            "compatible_roles": list(roles),
                        },
                    ),
                    kind="reference",
                    source_unit_refs=source_unit_refs,
                    target_ref=designation.target_ref,
                    target_kind=designation.target_kind,
                    input_ports=(),
                    output_ports=roles,
                    constraints=(("resolution_kind", "designation"),),
                    provenance_refs=tuple(
                        dict.fromkeys(
                            (
                                designation.slot_ref,
                                designation.designation_fact_ref,
                                *designation.provenance_refs,
                            )
                        )
                    ),
                )
            contributions.append(contribution)
            for frame_ref, choice_roles in frame_choices:
                references.append(
                    ReferenceSlot.create(
                        target_ref=designation.target_ref,
                        target_kind=designation.target_kind,
                        source_unit_refs=source_unit_refs,
                        resolution_kind="designation",
                        compatible_roles=choice_roles,
                        score_q=designation.score_q,
                        provenance_refs=(
                            designation.slot_ref,
                            contribution.slot_ref,
                            *((frame_ref,) if frame_ref is not None else ()),
                        ),
                    )
                )
        return tuple(contributions), tuple(references)

    def _compatible_reference_roles(
        self,
        designation: DesignationSlot,
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
    ) -> tuple[str, ...]:
        generic = _reference_roles(designation.target_kind)
        compatible: list[str] = []
        for frame in frames:
            if (
                frame.designation_slot_ref == designation.slot_ref
                or set(frame.source_unit_refs) & set(designation.source_unit_refs)
            ):
                continue
            legal_roles = (*frame.required_roles, *frame.optional_roles)
            if frame.predicate_kind == "event_type":
                signature = event_signatures.get(frame.predicate_target_ref)
                if not isinstance(signature, EventSignature):
                    continue
                specs = {row.role: row for row in signature.roles}
                for role in legal_roles:
                    spec = specs.get(role)
                    if spec is None or spec.proposition_valued:
                        continue
                    if not spec.filler_kinds or designation.target_kind in spec.filler_kinds:
                        compatible.append(role)
                continue
            compatible.extend(role for role in legal_roles if role in generic)
        fallback = generic if designation.target_kind in {"entity", "participant"} else ()
        return tuple(dict.fromkeys((*compatible, *fallback)))

    def _clause_local_reference_slots(
        self,
        references: tuple[ReferenceSlot, ...],
        frames: tuple[ApplicationFrameSlot, ...],
        form_lattice: FormLattice,
    ) -> tuple[ReferenceSlot, ...]:
        """Scope every source-bound reference to compatible frames in its clause."""
        sentence_boundaries = tuple(
            row
            for row in form_lattice.units
            if ("orthography", "sentence_boundary") in row.features
        )
        unit_by_ref = {row.unit_ref: row for row in form_lattice.units}
        reports = _reported_clauses_from_lattice(
            frames, form_lattice, self._config
        )
        rows: list[ReferenceSlot] = []
        for reference in references:
            span = _source_span_for_units(reference.source_unit_refs, unit_by_ref)
            if span is None:
                rows.append(reference)
                continue
            if not frames:
                # Preserve grounded reference evidence even when this clause has
                # no application frame.  With no frame it cannot be rebound
                # across a clause, and the residual path still needs the exact
                # source-owned reference for diagnosis.
                rows.append(reference)
                continue
            clause_start = max(
                (
                    row.source_end
                    for row in sentence_boundaries
                    if row.source_end <= span[0]
                ),
                default=0,
            )
            clause_end = min(
                (
                    row.source_start
                    for row in sentence_boundaries
                    if row.source_start >= span[1]
                ),
                default=len(form_lattice.source_text),
            )
            frame_refs = frozenset(frame.slot_ref for frame in frames)
            pre_scoped = frozenset(
                ref for ref in reference.provenance_refs if ref in frame_refs
            )
            for frame in frames:
                if pre_scoped and frame.slot_ref not in pre_scoped:
                    continue
                frame_span = _source_span_for_units(frame.source_unit_refs, unit_by_ref)
                if (
                    frame_span is None
                    or not clause_start <= frame_span[0]
                    or frame_span[1] > clause_end
                ):
                    continue
                report = next(
                    (
                        row
                        for row in reports
                        if row.clause_start == clause_start
                        and row.content_end == clause_end
                        and (
                            frame.slot_ref == row.parent_frame_ref
                            or frame.slot_ref in row.child_frame_refs
                        )
                    ),
                    None,
                )
                if report is not None:
                    if frame.slot_ref == report.parent_frame_ref:
                        if span[1] > report.report_start:
                            continue
                    elif span[0] < report.report_end:
                        continue
                roles = tuple(
                    role for role in reference.compatible_roles
                    if role in set(frame.required_roles) | set(frame.optional_roles)
                )
                if not roles:
                    continue
                rows.append(
                    ReferenceSlot.create(
                        target_ref=reference.target_ref,
                        target_kind=reference.target_kind,
                        source_unit_refs=reference.source_unit_refs,
                        resolution_kind=reference.resolution_kind,
                        compatible_roles=roles,
                        score_q=reference.score_q,
                        provenance_refs=tuple(
                            dict.fromkeys(
                                (*reference.provenance_refs, frame.slot_ref)
                            )
                        ),
                    )
                )
                if len(rows) >= self._config.max_orientation_alternatives:
                    return tuple(rows)
        return tuple(rows)

    def _situated_participant_references(
        self,
        orientation: Orientation,
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
        explicit_references: tuple[ReferenceSlot, ...],
        form_lattice: FormLattice,
    ) -> tuple[ReferenceSlot, ...]:
        participant_refs = tuple(
            ref
            for ref in orientation.participants
            if isinstance(self._authority.atoms.get(ref), AtomRecord)
            and self._authority.atoms[ref].kind == "participant"
        )
        if not participant_refs:
            return ()
        speaker = (
            orientation.participant_frame
            if orientation.participant_frame in participant_refs
            else participant_refs[0]
        )
        others = tuple(ref for ref in participant_refs if ref != speaker)
        actor_roles = frozenset(
            {"role:actor", "role:subject", "role:speaker", "role:source", "role:participant"}
        )
        addressed_roles = frozenset(
            {"role:addressee", "role:target", "role:object", "role:recipient", "role:beneficiary"}
        )
        embedded_frame_refs = frozenset(
            frame_ref
            for row in _reported_clauses_from_lattice(
                frames, form_lattice, self._config
            )
            for frame_ref in row.child_frame_refs
        )
        rows: list[ReferenceSlot] = []
        for frame in frames:
            if (
                frame.predicate_kind != "event_type"
                or frame.slot_ref in embedded_frame_refs
            ):
                continue
            signature = event_signatures.get(frame.predicate_target_ref)
            if not isinstance(signature, EventSignature):
                continue
            specs = {row.role: row for row in signature.roles}
            situated_roles = tuple(
                dict.fromkeys(
                    (
                        *frame.required_roles,
                        *(
                            role
                            for role in frame.optional_roles
                            if role in actor_roles or role in addressed_roles
                        ),
                    )
                )
            )
            for role in situated_roles:
                spec = specs.get(role)
                if (
                    spec is None
                    or spec.proposition_valued
                    or (spec.filler_kinds and "participant" not in spec.filler_kinds)
                    or any(
                        role in ref.compatible_roles
                        and (
                            not tuple(
                                item for item in ref.provenance_refs
                                if item.startswith("application_frame_slot:")
                            )
                            or frame.slot_ref in ref.provenance_refs
                        )
                        for ref in explicit_references
                    )
                ):
                    continue
                target = (
                    (
                        others[0]
                        if orientation.mode is SemanticMode.REQUEST and others
                        else speaker
                    )
                    if role in actor_roles
                    else (others[0] if role in addressed_roles and others else None)
                )
                if target is None:
                    continue
                rows.append(
                    ReferenceSlot.create(
                        target_ref=target,
                        target_kind="participant",
                        source_unit_refs=(),
                        resolution_kind="situated_participant",
                        compatible_roles=(role,),
                        score_q=1_000_000,
                        provenance_refs=(orientation.orientation_ref, frame.slot_ref),
                    )
                )
        return tuple(rows)

    def _coordinated_reference_slots(
        self,
        explicit_references: tuple[ReferenceSlot, ...],
        link_slots: tuple[ExpressionLinkSlot, ...],
    ) -> tuple[ReferenceSlot, ...]:
        """Expose bounded source-free co-reference for coordinated predicates."""
        coordinating_refs = tuple(
            row.slot_ref
            for row in link_slots
            if row.commutative and row.min_arity >= 2
        )
        if not coordinating_refs:
            return ()
        rows: list[ReferenceSlot] = []
        for reference in explicit_references:
            if not reference.source_unit_refs:
                continue
            roles = tuple(
                role
                for role in reference.compatible_roles
                if role in {"role:subject", "role:object"}
            )
            if not roles:
                continue
            rows.append(
                ReferenceSlot.create(
                    target_ref=reference.target_ref,
                    target_kind=reference.target_kind,
                    source_unit_refs=(),
                    resolution_kind="coordinated_coreference",
                    compatible_roles=roles,
                    score_q=reference.score_q,
                    provenance_refs=(reference.slot_ref, *coordinating_refs),
                )
            )
            if len(rows) >= self._config.max_orientation_alternatives:
                break
        return tuple(rows)

    def _reported_speaker_coreferences(
        self,
        explicit_references: tuple[ReferenceSlot, ...],
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
        form_lattice: FormLattice,
    ) -> tuple[ReferenceSlot, ...]:
        """Reuse a local reporting actor only in a reviewed speech-act child."""
        frame_by_ref = {row.slot_ref: row for row in frames}
        rows: list[ReferenceSlot] = []
        for report in _reported_clauses_from_lattice(
            frames, form_lattice, self._config
        ):
            parent = frame_by_ref[report.parent_frame_ref]
            parent_actors = tuple(
                reference
                for reference in explicit_references
                if "role:actor" in reference.compatible_roles
                and report.parent_frame_ref in reference.provenance_refs
            )
            if len(parent_actors) != 1:
                continue
            parent_actor = parent_actors[0]
            for child_ref in report.child_frame_refs:
                child = frame_by_ref[child_ref]
                signature = event_signatures.get(child.predicate_target_ref)
                control = self._authority.reported_role_inheritance_control(
                    parent.predicate_target_ref,
                    "role:content",
                    child.predicate_target_ref,
                    "role:actor",
                )
                if (
                    child.predicate_kind != "event_type"
                    or "role:actor" not in child.required_roles
                    or not isinstance(signature, EventSignature)
                    or control is None
                    or any(
                        "role:actor" in reference.compatible_roles
                        and child_ref in reference.provenance_refs
                        for reference in explicit_references
                    )
                ):
                    continue
                rows.append(
                    ReferenceSlot.create(
                        target_ref=parent_actor.target_ref,
                        target_kind=parent_actor.target_kind,
                        source_unit_refs=(),
                        resolution_kind="reported_speaker_coreference",
                        compatible_roles=("role:actor",),
                        score_q=parent_actor.score_q,
                        provenance_refs=(
                            parent_actor.slot_ref,
                            report.parent_frame_ref,
                            child_ref,
                            control.control_ref,
                        ),
                    )
                )
                if len(rows) >= self._config.max_orientation_alternatives:
                    return tuple(rows)
        return tuple(rows)

    def _application_frames(
        self,
        designations: tuple[DesignationSlot, ...],
        profiles_by_target: Mapping[str, tuple[AffordanceProfile, ...]],
        predicate_targets: frozenset[str],
    ) -> tuple[tuple[ApplicationFrameSlot, ...], Mapping[str, EventSignature]]:
        frames: list[ApplicationFrameSlot] = []
        per_occurrence: dict[str, int] = {}
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
                if per_occurrence.get(designation.slot_ref, 0) >= self._config.max_affordances_per_target:
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
                derived = _derived_roles_for_kind(
                    designation.target_kind,
                    target,
                )
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
                    per_occurrence[designation.slot_ref] = per_occurrence.get(designation.slot_ref, 0) + 1
        return (
            tuple(frames),
            MappingProxyType(
                {
                    target: signature
                    for target, signature in event_signature_by_target.items()
                    if isinstance(signature, EventSignature)
                }
            ),
        )

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
    per_occurrence: dict[tuple[str, tuple[str, ...]], int] = {}
    target_limit = config.max_affordances_per_target * 2
    global_limit = config.max_input_tokens * (target_limit + 1)
    for row in rows:
        if row.slot_ref in seen:
            continue
        if row.target_ref is not None:
            occurrence = (row.target_ref, row.source_unit_refs)
            count = per_occurrence.get(occurrence, 0)
            if count >= target_limit:
                continue
            per_occurrence[occurrence] = count + 1
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


_PRIMITIVE_FORM_PORTS = MappingProxyType({
    "binder": (("role:subject", "role:predicate"), ("role:application",)),
    "open_variable": ((), ("role:variable",)),
    "scope": (("role:scope_target",), ("role:scope",)),
    "connector": (("role:left", "role:right"), ("role:link",)),
    "discourse": ((), ("role:discourse",)),
    "qualifier": (("role:qualified",), ("role:qualifier",)),
    "reference": ((), ("role:reference",)),
})


def _primitive_form_ports(kind, category=None):
    """The form owner's exact port contract, shared with activated rematching."""
    return ((), ()) if category == "orthography" else _PRIMITIVE_FORM_PORTS[kind]


def _primitive_form_signature(category, value, features=()):
    """Single form-contribution owner for primitive kinds and metadata.

    Construction indexes reuse this signature; target-bearing deixis remains
    resolved by the existing orientation/reference owner, not a second map.
    """
    kinds = {
        "orthography": "discourse", "participant": "reference",
        "binder": "binder", "query": "open_variable", "polarity": "scope",
        "modality": "scope", "tense_aspect": "scope", "connector": "connector",
        "discourse": "discourse", "correction": "discourse", "determiner": "qualifier",
        "linker": "qualifier",
    }
    kind = kinds.get(category)
    if category == "discourse" and value == "discourse_particle":
        kind = None
    elif category == "query" and value == "query_auxiliary":
        kind = "binder"
    metadata = () if category in {"orthography", "participant"} else tuple(
        pair for pair in features if pair[0] in {"interrogative", "construction_role"})
    return kind, ((category, value), *metadata)


def _primitive_form_ref(source_ref, category, value, target_ref=None):
    material = (source_ref, category, value)
    if target_ref is not None:
        material = (*material, target_ref)
    return stable_ref("form_contribution", material)


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
            "role:object",
            "role:target",
            "role:instance",
        )
    if target_kind in {"entity", "concept"}:
        return ("role:subject", "role:object", "role:target", "role:instance")
    return ("role:subject", "role:object", "role:target")


def _explicit_lexical_query_evidence(lattice, authority, target_kinds):
    """One reviewed unquoted construction; no target lookup licenses its form."""
    units = tuple(row for row in lattice.units if ("orthography", "whitespace") not in row.features)
    if units and ("discourse", "question") in units[-1].features:
        units = units[:-1]
    if len(units) < 4 or ("interrogative", "content") not in units[0].features:
        return (), (), ()
    if (("construction_role", "lexical_query_auxiliary") not in units[1].features
        or ("query", "query_auxiliary") not in units[1].features
        or ("construction_role", "lexical_query_terminal") not in units[-1].features
        or any(row.features for row in units[2:-1])):
        return (), (), ()
    label = authority.atoms.get("label:lexical")
    if type(label) is not AtomRecord or not label.reviewed or label.kind != "label_type":
        return (), (), ()
    literal_units = tuple(row for row in lattice.units if units[2].source_start <= row.source_start and row.source_end <= units[-2].source_end)
    literal_refs = tuple(row.unit_ref for row in literal_units)
    binder_refs = (units[1].unit_ref, units[-1].unit_ref)
    construction = stable_ref("lexical_query_construction", (lattice.lattice_ref, units[0].unit_ref, binder_refs, literal_refs))
    binder = ContributionSlot.create(
        contribution_ref=stable_ref("lexical_query_binder", construction), kind="binder",
        source_unit_refs=binder_refs, target_ref=None, target_kind=None,
        input_ports=(), output_ports=("role:variable",),
        constraints=(("binder", "explicit_lexical_target_query"),),
        provenance_refs=(construction, lattice.lattice_ref))
    literal = ContributionSlot.create(
        contribution_ref=stable_ref("lexical_query_literal", construction), kind="literal",
        source_unit_refs=literal_refs, target_ref=None, target_kind=None,
        input_ports=(), output_ports=("role:surface",), constraints=(("literal_kind", "string"),),
        literal_value=lattice.source_text[units[2].source_start:units[-2].source_end],
        provenance_refs=(construction, lattice.lattice_ref))
    frame = UnresolvedDesignationFrame.create(label_type_ref=label.ref,
        literal_contribution_slot_ref=literal.slot_ref, query_binder_slot_ref=binder.slot_ref,
        source_unit_refs=literal_refs, construction_ref=construction,
        provenance_refs=(construction, lattice.lattice_ref, label.ref, authority.content_hash))
    # This activation-derived domain records admitted target kinds, not an
    # ontology restriction on the canonical (unrestricted) BoundVariable.
    variable = VariableSlot.create(application_frame_ref=frame.slot_ref, role_ref="role:target",
        required_kinds=target_kinds,
        source_unit_refs=(units[0].unit_ref, *binder_refs), construction_ref=construction)
    return (binder, literal), (frame,), (variable,)


def _variable_slots(
    form_lattice: FormLattice,
    contributions: tuple[ContributionSlot, ...],
    frames: tuple[ApplicationFrameSlot, ...],
    config: RuntimeConfig,
    *,
    role_matches: tuple[Any, ...] = (),
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
    binder_sources = tuple(
        dict.fromkeys(
            source_ref
            for row in contributions
            if row.kind == "binder"
            for source_ref in row.source_unit_refs
        )
    )
    for source_ref in variable_sources:
        for frame in frames:
            if frame.operator_ref == "op:relation":
                matches = tuple(m for m in role_matches if m.predicate_slot_ref == frame.designation_slot_ref
                                and m.query_source_ref == source_ref)
                for match in matches:
                    slots.append(VariableSlot.create(application_frame_ref=frame.slot_ref,
                        role_ref=match.query_role, required_kinds=role_kinds[match.query_role],
                        source_unit_refs=(source_ref,), construction_ref=match.match_ref))
                    if len(slots) > config.max_orientation_alternatives:
                        raise BudgetExhausted("relation_query_variables", config.max_orientation_alternatives)
                # Actual surface relation queries have no all-role fallback.
                continue
            if (
                frame.affordance_frame_ref is None
                and source_ref in frame.provenance_refs
            ):
                continue
            for role_ref in (*frame.required_roles, *frame.optional_roles):
                required_kinds = role_kinds.get(role_ref)
                if required_kinds is None:
                    continue
                slots.append(
                    VariableSlot.create(
                        application_frame_ref=frame.slot_ref,
                        role_ref=role_ref,
                        required_kinds=required_kinds,
                        source_unit_refs=(
                            tuple(dict.fromkeys((source_ref, *binder_sources)))
                            if frame.predicate_kind == "label_type"
                            and role_ref == "role:surface"
                            else (source_ref,)
                        ),
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
        "capability": "op:relation",
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
        "capability": "role:relation",
    }.get(target_kind)


def _derived_roles_for_kind(
    target_kind: str, target_ref: str
) -> tuple[tuple[str, str], ...]:
    if target_kind == "label_type":
        return (("role:label_type", target_ref),)
    if target_kind == "state_dimension":
        return (("role:dimension", target_ref),)
    if target_kind == "concept":
        return (("role:class", target_ref),)
    return ()


def _is_designation_application_frame(
    frame: ApplicationFrameSlot,
    designation: DesignationSlot,
) -> bool:
    """Recognize the one structural lowering owned by a designation fact."""
    return (
        frame.operator_ref == "op:designation"
        and frame.predicate_kind == "label_type"
        and frame.structural_role_ref == "role:label_type"
        and frame.required_roles == ("role:surface",)
        and frame.optional_roles == ()
        and frame.proposition_roles == ()
        and set(designation.source_unit_refs) <= set(frame.source_unit_refs)
        and frame.derived_role_targets
        == (
            ("role:label_type", frame.predicate_target_ref),
            ("role:target", designation.target_ref),
        )
        and frame.affordance_frame_ref is None
        and designation.designation_fact_ref in frame.provenance_refs
    )


def _is_state_value_application_frame(
    frame: ApplicationFrameSlot,
    designation: DesignationSlot,
) -> bool:
    dimension_ref = frame.predicate_target_ref
    return (
        designation.target_kind == "state_value"
        and frame.predicate_kind == "state_dimension"
        and frame.operator_ref == "op:state"
        and frame.structural_role_ref == "role:dimension"
        and frame.required_roles == ("role:subject",)
        and frame.optional_roles == ()
        and frame.proposition_roles == ()
        and set(designation.source_unit_refs) <= set(frame.source_unit_refs)
        and frame.derived_role_targets
        == (
            ("role:dimension", dimension_ref),
            ("role:value", designation.target_ref),
        )
        and frame.affordance_frame_ref is None
        and designation.designation_fact_ref in frame.provenance_refs
    )


def _is_transition_value_application_frame(
    frame: ApplicationFrameSlot,
    designation: DesignationSlot,
    designations: tuple[DesignationSlot, ...],
) -> bool:
    derived = dict(frame.derived_role_targets)
    value_ref = derived.get("role:value")
    dimension_ref = derived.get("role:dimension")
    value_designations = tuple(
        row
        for row in designations
        if row.target_kind == "state_value" and row.target_ref == value_ref
    )
    return (
        designation.target_kind == "event_type"
        and frame.predicate_target_ref == designation.target_ref
        and frame.predicate_kind == designation.target_kind
        and frame.operator_ref == "op:event"
        and value_ref is not None
        and dimension_ref is not None
        and {role for role, _target in frame.derived_role_targets}
        == {"role:dimension", "role:value"}
        and any(
            set(row.source_unit_refs) <= set(frame.source_unit_refs)
            and row.designation_fact_ref in frame.provenance_refs
            for row in value_designations
        )
    )


def _mode_slot(
    orientation: Orientation,
    form_lattice: FormLattice,
    *,
    capability_query: bool = False,
) -> ModeSlot:
    construction_ref = None
    source_refs: tuple[str, ...] = ()
    for hypothesis in form_lattice.hypotheses:
        construction = (hypothesis.construction or "").upper()
        if construction == orientation.mode.value:
            construction_ref = hypothesis.hypothesis_ref
            source_refs = hypothesis.unit_refs
            break
    if orientation.mode is SemanticMode.QUERY:
        question_refs = tuple(
            unit.unit_ref
            for unit in form_lattice.units
            if any(
                category == "discourse" and value == "question"
                for category, value in unit.features
            )
        )
        capability_refs = tuple(
            unit.unit_ref
            for unit in form_lattice.units
            if any(
                (category == "modality" and value == "capability")
                or (capability_query and category == "query")
                for category, value in unit.features
            )
        )
        if question_refs:
            source_refs = tuple(dict.fromkeys((*capability_refs, *question_refs)))
        elif not source_refs:
            source_refs = capability_refs
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
    scope_values: Mapping[str, Mapping[str, str]] | None = None,
    *,
    suppress_capability_query: bool = False,
) -> tuple[ScopeSlot, ...]:
    """Derive reviewed scope slots from form evidence.

    Per R2 plan section 2.1: no ``value:`` ref is created by string
    prefixing. Every scope slot binds a reviewed value ref from the
    language pack's ``scope_values`` mapping.
    """
    feature_to_operator = {
        "polarity": "scope:polarity",
        "modality": "scope:modality",
        "tense": "scope:tense",
        "aspect": "scope:aspect",
        "tense_aspect": "scope:aspect",
        "attribution": "scope:attribution",
    }
    # Fallback mapping for backward compatibility when no reviewed
    # scope_values mapping is supplied (e.g. R1 tests without form_pack).
    # This maps feature values to reviewed scope_value refs directly.
    fallback_values: Mapping[str, Mapping[str, str]] = {
        "polarity": {"negation": "scope_value:polarity:negative"},
        "modality": {
            "capability": "scope_value:modality:capability",
            "permission": "scope_value:modality:permission",
            "possibility": "scope_value:modality:possibility",
            "obligation": "scope_value:modality:obligation",
            "conditional": "scope_value:modality:conditional",
            "future": "scope_value:modality:future",
        },
        "tense": {
            "future": "scope_value:tense:future",
            "perfect": "scope_value:tense:perfect",
            "pluperfect": "scope_value:tense:pluperfect",
            "temporal_qualifier": "scope_value:tense:temporal_qualifier",
        },
        "aspect": {
            "future": "scope_value:aspect:future",
            "perfect": "scope_value:aspect:perfect",
            "pluperfect": "scope_value:aspect:pluperfect",
            "temporal_qualifier": "scope_value:aspect:temporal_qualifier",
        },
        "attribution": {
            "report": "scope_value:attribution:report",
            "definition_marker": "scope_value:attribution:definition",
        },
    }
    values_map = scope_values if scope_values else fallback_values
    slots: list[ScopeSlot] = []
    for unit in form_lattice.units:
        for feature, value in unit.features:
            if (
                suppress_capability_query
                and feature == "modality"
                and value == "capability"
            ):
                continue
            operator = feature_to_operator.get(feature)
            if operator is None:
                continue
            # Look up the reviewed scope value ref from the mapping.
            # The feature category maps to the scope_values key, and the
            # feature value maps to the reviewed value ref.
            category_key = feature
            if feature == "tense_aspect":
                category_key = "aspect"
            value_map = values_map.get(category_key, {})
            value_ref = value_map.get(value)
            if value_ref is None:
                # Unknown scope evidence remains typed unresolved/critical.
                # Do not manufacture a ref by string prefixing.
                continue
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
    link_schemas: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[ExpressionLinkSlot, ...]:
    """Derive expression link slots from reviewed link schemas.

    Per R2 plan section 2.2: support the existing expression link registry
    with reviewed min/max arity and commutativity. Do not infer
    commutativity from wording at runtime; use the reviewed link schema.
    """
    # Fallback mapping for backward compatibility when no reviewed
    # link_schemas mapping is supplied (e.g. R1 tests without form_pack).
    fallback_schemas: Mapping[str, Mapping[str, Any]] = {
        "coordination": {"link_type": "link:coordination", "commutative": True, "min_arity": 2, "max_arity": 2},
        "conjunction": {"link_type": "link:conjunction", "commutative": True, "min_arity": 2, "max_arity": 2},
        "disjunction": {"link_type": "link:disjunction", "commutative": True, "min_arity": 2, "max_arity": 2},
        "conditional": {"link_type": "link:condition", "commutative": False, "min_arity": 2, "max_arity": 2},
        "condition": {"link_type": "link:condition", "commutative": False, "min_arity": 2, "max_arity": 2},
        "causal": {"link_type": "link:cause", "commutative": False, "min_arity": 2, "max_arity": 2},
        "cause": {"link_type": "link:cause", "commutative": False, "min_arity": 2, "max_arity": 2},
        "contrast": {"link_type": "link:contrast", "commutative": False, "min_arity": 2, "max_arity": 2},
        "purpose": {"link_type": "link:purpose", "commutative": False, "min_arity": 2, "max_arity": 2},
        "sequence": {"link_type": "link:sequence", "commutative": False, "min_arity": 2, "max_arity": 2},
    }
    schemas = link_schemas if link_schemas else fallback_schemas
    slots: list[ExpressionLinkSlot] = []
    for hypothesis in form_lattice.hypotheses:
        if hypothesis.construction not in schemas:
            continue
        schema = schemas[hypothesis.construction]
        link_type = schema.get("link_type", "")
        commutative = bool(schema.get("commutative", False))
        min_arity = int(schema.get("min_arity", 2))
        max_arity = int(schema.get("max_arity", 2))
        slots.append(
            ExpressionLinkSlot.create(
                link_type=link_type,
                commutative=commutative,
                min_arity=min_arity,
                max_arity=max_arity,
                source_unit_refs=hypothesis.unit_refs,
                construction_ref=hypothesis.hypothesis_ref,
            )
        )
        if len(slots) >= config.max_orientation_alternatives:
            break
    return tuple(slots)


def _is_orthographic_evidence(row: ContributionSlot) -> bool:
    return (
        row.kind == "discourse" and row.target_ref is None
        and row.target_kind is None and not row.input_ports and not row.output_ports
        and len(row.source_unit_refs) == 1
        and row.provenance_refs == row.source_unit_refs
        and row.constraints in {
            (("orthography", "whitespace"),),
            (("orthography", "punctuation"),),
            (("orthography", "sentence_boundary"),),
            (("orthography", "quotation_boundary"),),
        }
        and row.contribution_ref == stable_ref(
            "form_contribution", (row.source_unit_refs[0], *row.constraints[0])
        )
    )


def _nominal_predication_evidence(frames, contributions, lattice, *, subject_person_query=False):
    """Extend nominal predicates with one local copula and optional determiner.

    Whitespace and polarity are traversed, never consumed by the predicate.
    Queries require adjacent typed subject-person evidence before the copula.
    Query-variable creation remains separate from this source extension.
    """
    units = lattice.units
    positions = {unit.unit_ref: index for index, unit in enumerate(units)}
    replacements = {}
    result = []
    for frame in frames:
        if frame.operator_ref != "op:type" or frame.predicate_kind != "concept":
            result.append(frame)
            continue
        cursor = min(positions[ref] for ref in frame.source_unit_refs) - 1
        extension = []
        determiner = False
        polarity = False
        while cursor >= 0:
            unit = units[cursor]
            if ("orthography", "whitespace") in unit.features:
                cursor -= 1
                continue
            if not determiner and not polarity and any(key == "determiner" for key, _ in unit.features):
                extension.append(unit.unit_ref)
                determiner = True
            elif not polarity and any(key == "polarity" for key, _ in unit.features):
                polarity = True
            elif ("binder", "copula") in unit.features:
                extension.append(unit.unit_ref)
                break
            else:
                extension = []
                break
            cursor -= 1
        if not extension or cursor < 0:
            result.append(frame)
            continue
        if subject_person_query:
            subject_cursor = cursor - 1
            while subject_cursor >= 0 and ("orthography", "whitespace") in units[subject_cursor].features:
                subject_cursor -= 1
            if subject_cursor < 0 or not {
                ("query", "query"), ("interrogative", "person"),
            } <= set(units[subject_cursor].features):
                result.append(frame)
                continue
        source_refs = tuple(sorted((*frame.source_unit_refs, *extension), key=positions.__getitem__))
        values = {row.name: getattr(frame, row.name) for row in fields(frame) if row.init and row.name != "slot_ref"}
        result.append(ApplicationFrameSlot.create(**{**values, "source_unit_refs": source_refs}))
        for contribution in contributions:
            if (contribution.kind == "predicate"
                and contribution.target_ref == frame.predicate_target_ref
                and contribution.source_unit_refs == frame.source_unit_refs):
                values = {row.name: getattr(contribution, row.name) for row in fields(contribution) if row.init and row.name != "slot_ref"}
                replacements[contribution.slot_ref] = ContributionSlot.create(**{
                    **values, "source_unit_refs": source_refs,
                    "contribution_ref": stable_ref("nominal_predication_contribution", (contribution.contribution_ref, source_refs)),
                })
    return tuple(result), tuple(replacements.get(row.slot_ref, row) for row in contributions)


def _nominal_predication_source_is_exact(frame, designation, context) -> bool:
    """Validate only local source extension, never waive arbitrary extra units."""
    original = set(designation.source_unit_refs)
    actual = set(frame.source_unit_refs)
    if actual == original:
        return True
    if not original < actual:
        return False
    positions = {ref: index for index, ref in enumerate(context.source_unit_refs)}
    rows_by_source = {}
    for row in context.contribution_slots:
        if len(row.source_unit_refs) == 1:
            rows_by_source.setdefault(row.source_unit_refs[0], []).append(row)
    cursor = min(positions[ref] for ref in original) - 1
    expected = set(original)
    determiner = polarity = False
    while cursor >= 0:
        ref = context.source_unit_refs[cursor]
        rows = rows_by_source.get(ref, ())
        if any(_is_orthographic_evidence(row) and row.constraints == (("orthography", "whitespace"),) for row in rows):
            if len(rows) != 1:
                return False
        elif not determiner and not polarity and any(row.kind == "qualifier" and any(key == "determiner" for key, _ in row.constraints) for row in rows):
            expected.add(ref)
            determiner = True
        elif not polarity and any(row.kind == "scope" and any(key == "polarity" for key, _ in row.constraints) for row in rows):
            polarity = True
        elif any(row.kind == "binder" and ("binder", "copula") in row.constraints for row in rows):
            expected.add(ref)
            if any(mode.mode == "QUERY" for mode in context.mode_slots):
                subject_cursor = cursor - 1
                while subject_cursor >= 0:
                    subject_ref = context.source_unit_refs[subject_cursor]
                    subject_rows = rows_by_source.get(subject_ref, ())
                    if len(subject_rows) == 1 and _is_orthographic_evidence(subject_rows[0]) and subject_rows[0].constraints == (("orthography", "whitespace"),):
                        subject_cursor -= 1
                        continue
                    break
                if subject_cursor < 0 or not any(
                    row.kind == "open_variable"
                    and row.constraints == (("query", "query"), ("interrogative", "person"))
                    and row.provenance_refs == (subject_ref,)
                    and row.contribution_ref == stable_ref("form_contribution", (subject_ref, "query", "query"))
                    for row in subject_rows
                ):
                    return False
            return actual == expected and tuple(sorted(actual, key=positions.__getitem__)) == frame.source_unit_refs
        else:
            return False
        cursor -= 1
    return False


def naming_binding_choice_index(context: ProposalContext) -> Mapping[tuple[str, str], frozenset[str]]:
    """Index frame-owned naming ports once; no lexical or world-store scan.

    The compiler enforces these pointer constraints and VERIFY separately
    reconstructs locality from form evidence. This is not a new gate.
    """
    naming_frames = {frame.slot_ref for frame in context.application_frames
        if frame.predicate_kind == "event_type" and {"role:surface", "role:target"} <= set(frame.required_roles)}
    teaching_predicates = tuple(row for row in context.contribution_slots
        if row.kind == "predicate" and any(key == "teaching_evidence_ref" for key, _ in row.constraints))
    if not naming_frames and not teaching_predicates:
        return MappingProxyType({})
    features: dict[str, set[tuple[str, str]]] = {}
    for row in context.contribution_slots:
        if len(row.source_unit_refs) != 1 or len(row.constraints) != 1:
            continue
        ref = row.source_unit_refs[0]
        key, value = row.constraints[0]
        if row.provenance_refs == (ref,) and row.contribution_ref == stable_ref("form_contribution", (ref, key, value)):
            features.setdefault(ref, set()).add((key, value))
    boundaries = tuple(start for ref, start, _ in context.source_unit_spans
        if features.get(ref, set()) - {("orthography", "whitespace")})
    result = {}
    for frame in context.application_frames:
        naming = frame.slot_ref in naming_frames
        teaching_refs = {value for row in teaching_predicates
            if row.source_unit_refs == frame.source_unit_refs
            and row.target_ref == frame.predicate_target_ref
            for key, value in row.constraints if key == "teaching_evidence_ref"}
        if not naming and not teaching_refs:
            continue
        literals = tuple(row for row in context.contribution_slots if row.kind == "literal"
            and (dict(row.constraints).get("naming_frame_ref") == frame.slot_ref if naming else
                dict(row.constraints).get("teaching_evidence_ref") in teaching_refs
                and row.source_unit_refs == frame.source_unit_refs))
        result[frame.slot_ref, "role:surface"] = frozenset(row.slot_ref for row in literals)
        if not naming:
            continue
        intervals = []
        for literal in literals:
            markers = tuple(ref for ref in literal.source_unit_refs
                if ("discourse", "definition_marker") in features.get(ref, ()))
            if len(markers) != 1:
                continue
            marker_end = context.source_span(markers)[1]
            end = min((start for start in boundaries if start >= marker_end), default=max(end for _, _, end in context.source_unit_spans))
            intervals.append((marker_end, end))
        result[frame.slot_ref, "role:target"] = frozenset(row.slot_ref
            for row in (*context.contribution_slots, *context.reference_slots)
            if (span := context.source_span(row.source_unit_refs)) is not None
            and any(start <= span[0] and span[1] <= end for start, end in intervals))
    return MappingProxyType(result)


def nominal_predication_choice_index(
    context: ProposalContext,
) -> tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str]]]:
    """Index local nominal ports once for a bounded PROPOSE invocation.

    These are legal choices over ORIENT-owned slots, not a verification receipt.
    VERIFY independently reconstructs the full role and scope source proof.
    Non-nominal frames and their scope choices are not constrained here.
    """
    whitespace = frozenset(
        row.source_unit_refs[0] for row in context.contribution_slots
        if _is_orthographic_evidence(row)
        and row.constraints == (("orthography", "whitespace"),)
    )
    binders = frozenset(
        row.source_unit_refs[0] for row in context.contribution_slots
        if row.kind == "binder" and len(row.source_unit_refs) == 1
        and ("binder", "copula") in row.constraints
    )
    bindings: dict[str, frozenset[str]] = {}
    scopes: dict[str, set[str]] = {}
    for frame in context.application_frames:
        if type(frame) is not ApplicationFrameSlot or frame.operator_ref != "op:type":
            continue
        bindings[frame.slot_ref] = frozenset()
        designation = context.designation(frame.designation_slot_ref)
        if designation is None or not _nominal_predication_source_is_exact(frame, designation, context):
            continue
        local_binders = (set(frame.source_unit_refs) - set(designation.source_unit_refs)) & binders
        if len(local_binders) != 1:
            continue
        binder_span = context.source_span(tuple(local_binders))
        nominal_span = context.source_span(designation.source_unit_refs)
        if binder_span is None or nominal_span is None:
            continue
        allowed = set()
        for slot in (*context.reference_slots, *context.contribution_slots):
            if slot.target_kind not in {"entity", "participant", "concept"}:
                continue
            span = context.source_span(slot.source_unit_refs)
            if span is None or span[1] > binder_span[0]:
                continue
            if any(ref not in whitespace for ref, start, end in context.source_unit_spans
                   if span[1] <= start and end <= binder_span[0]):
                continue
            allowed.add(slot.slot_ref)
        bindings[frame.slot_ref] = frozenset(allowed)
        for scope in context.scope_slots:
            if scope.operator_type != "scope:polarity":
                continue
            span = context.source_span(scope.source_unit_refs)
            if span is not None and binder_span[1] <= span[0] and span[1] <= nominal_span[0]:
                scopes.setdefault(scope.slot_ref, set()).add(frame.slot_ref)
    return MappingProxyType(bindings), MappingProxyType({key: frozenset(value) for key, value in scopes.items()})


def _expanded_nominal_source_refs(
    designation: DesignationSlot,
    form_lattice: FormLattice,
    unit_by_ref: Mapping[str, Any],
) -> tuple[str, ...]:
    """Attach one adjacent reviewed determiner to an exact designation span.

    The designation remains owned by the exact authority lookup.  This helper
    only extends its source geometry with closed-class form evidence when the
    determiner is immediately adjacent modulo orthographic whitespace.
    """
    designation_units = tuple(
        unit_by_ref[source_ref] for source_ref in designation.source_unit_refs
    )
    start = min(unit.source_start for unit in designation_units)
    candidates = tuple(
        unit
        for unit in form_lattice.units
        if unit.source_end <= start
        and any(category == "determiner" for category, _ in unit.features)
        and not form_lattice.source_text[unit.source_end:start].strip()
    )
    if not candidates:
        return designation.source_unit_refs
    determiner = max(candidates, key=lambda unit: unit.source_end)
    refs = {determiner.unit_ref, *designation.source_unit_refs}
    return tuple(
        unit.unit_ref
        for unit in sorted(
            (unit_by_ref[ref] for ref in refs),
            key=lambda unit: (unit.source_start, unit.source_end, unit.unit_ref),
        )
    )


def _reviewed_participant_form_role_bindings(
    orientation: Orientation,
    designations: tuple[DesignationSlot, ...],
    form_lattice: FormLattice,
    unit_by_ref: Mapping[str, Any],
    schemas: Mapping[str, Mapping[str, Any]],
    atoms: Mapping[str, Any],
    config: RuntimeConfig,
) -> Mapping[str, tuple[str, ...]]:
    """Constrain participant deixis only through a reviewed typed role order."""
    if len(schemas) > config.max_orientation_alternatives:
        raise ValueError("application role-order schema bound exceeded")
    rows: list[tuple[int, str, tuple[str, ...], str | None]] = []
    for designation in designations:
        rows.append(
            (
                min(
                    unit_by_ref[ref].source_start
                    for ref in designation.source_unit_refs
                ),
                designation.target_kind,
                designation.source_unit_refs,
                None,
            )
        )
    for unit in form_lattice.units:
        for category, value in unit.features:
            if category != "participant":
                continue
            target = _participant_feature_target(value, orientation, atoms)
            atom = atoms.get(target) if target is not None else None
            if isinstance(atom, AtomRecord):
                rows.append(
                    (
                        unit.source_start,
                        atom.kind,
                        (unit.unit_ref,),
                        unit.unit_ref,
                    )
                )
    ordered = tuple(sorted(rows, key=lambda row: (row[0], row[2], row[3] or "")))
    available_features = {
        category for unit in form_lattice.units for category, _ in unit.features
    }
    bindings: dict[str, list[str]] = {}
    for schema_ref, schema in sorted(schemas.items()):
        if "evidence_order" in schema:
            continue
        raw_kinds = schema.get("target_kinds")
        raw_roles = schema.get("roles")
        raw_required = schema.get("required_features", [])
        if (
            type(raw_kinds) is not list
            or type(raw_roles) is not list
            or type(raw_required) is not list
            or len(raw_kinds) != len(raw_roles)
            or not raw_kinds
        ):
            raise ValueError(
                f"application role-order schema is invalid: {schema_ref}"
            )
        if not set(raw_required) <= available_features:
            continue
        matches = 0
        for selected in combinations(ordered, len(raw_kinds)):
            if matches >= config.max_orientation_alternatives:
                raise ValueError("application role-order match bound exceeded")
            if tuple(row[1] for row in selected) != tuple(raw_kinds):
                continue
            if len({ref for row in selected for ref in row[2]}) < len(selected):
                continue
            for row, role_ref in zip(selected, raw_roles, strict=True):
                if row[3] is not None:
                    bindings.setdefault(row[3], []).append(role_ref)
            matches += 1
    return MappingProxyType(
        {
            source_ref: tuple(dict.fromkeys(role_refs))
            for source_ref, role_refs in bindings.items()
        }
    )


def _reviewed_application_role_bindings(
    designations: tuple[DesignationSlot, ...],
    form_lattice: FormLattice,
    unit_by_ref: Mapping[str, Any],
    schemas: Mapping[str, Mapping[str, Any]],
    config: RuntimeConfig,
) -> Mapping[str, tuple[str, ...]]:
    """Project the retained reviewed named-designation order.

    Feature-taking schemas require their complete activated match. A purely
    referential order also retains its independently reviewed typed projection
    for surrounding scope/embedding evidence; this does not consume or erase
    that evidence. Complete mixed-reference matches take precedence in build.
    """
    if len(schemas) > config.max_orientation_alternatives:
        raise ValueError("application role-order schema bound exceeded")
    ordered = tuple(
        sorted(
            designations,
            key=lambda row: (
                min(unit_by_ref[ref].source_start for ref in row.source_unit_refs),
                max(unit_by_ref[ref].source_end for ref in row.source_unit_refs),
                row.slot_ref,
            ),
        )
    )
    available_features = {
        category
        for unit in form_lattice.units
        for category, _ in unit.features
    }
    bindings: dict[str, list[str]] = {}
    for schema_ref, schema in sorted(schemas.items()):
        if "construction" in schema:
            # This closed construction is owned by the activated matcher only.
            continue
        if "evidence_order" in schema and any(
            selector.get("kind") not in {"designation", "referent"}
            for selector in schema["evidence_order"]
        ):
            continue
        raw_kinds = schema.get("target_kinds")
        raw_roles = schema.get("roles")
        raw_required = schema.get("required_features", [])
        if (
            type(raw_kinds) is not list
            or type(raw_roles) is not list
            or type(raw_required) is not list
            or len(raw_kinds) != len(raw_roles)
            or not raw_kinds
            or any(type(value) is not str or not value for value in raw_kinds)
            or any(type(value) is not str or not value for value in raw_roles)
            or any(type(value) is not str or not value for value in raw_required)
        ):
            raise ValueError(
                f"application role-order schema is invalid: {schema_ref}"
            )
        if not set(raw_required) <= available_features:
            continue
        matches = 0
        for selected in combinations(ordered, len(raw_kinds)):
            if matches >= config.max_orientation_alternatives:
                raise ValueError("application role-order match bound exceeded")
            if tuple(row.target_kind for row in selected) != tuple(raw_kinds):
                continue
            if len(
                {
                    source_ref
                    for designation in selected
                    for source_ref in designation.source_unit_refs
                }
            ) < len(selected):
                continue
            for designation, role_ref in zip(selected, raw_roles, strict=True):
                bindings.setdefault(designation.slot_ref, []).append(role_ref)
            matches += 1
    return MappingProxyType(
        {
            slot_ref: tuple(dict.fromkeys(role_refs))
            for slot_ref, role_refs in bindings.items()
        }
    )


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
        quotation_boundary = ("orthography", "quotation_boundary") in unit.features
        if unit.unit_ref in consumed and not quotation_boundary:
            continue
        contribution_kind = next(
            (
                critical_kinds[feature]
                for feature, _ in unit.features
                if feature in critical_kinds
            ),
            None,
        )
        if ("query", "query_auxiliary") in unit.features:
            contribution_kind = "binder"
        if quotation_boundary:
            contribution_kind = "discourse"
        orthographic = not any(character.isalnum() for character in unit.source_text)
        explicitly_noncritical_discourse = any(
            feature == "discourse" and value == "discourse_particle"
            for feature, value in unit.features
        )
        noncritical = not quotation_boundary and (orthographic or explicitly_noncritical_discourse)
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
                    else "unresolved reviewed quotation boundary evidence"
                    if quotation_boundary
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


def licensed_query_projection_slots(index: ReviewedRoleSchemaIndex, context: ProposalContext) -> tuple[QueryProjectionSlot, ...]:
    """Slot derivation from the one activated immutable matcher.

    These structural records do not replace the independent compiler/coverage
    rematch required before public interpretation or semantic admission.
    """
    if type(index) is not ReviewedRoleSchemaIndex or type(context) is not ProposalContext:
        raise TypeError("licensed projection slots require exact activated index/context")
    if not index.identity_is_current or index.authority_generation != context.revision_pin.authority_generation:
        raise ValueError("query projection index has stale activation/authority")
    matches = index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
    return tuple(QueryProjectionSlot.create(
        requested_content=match.requested_content,
        target_designation_slot_ref=match.target_designation_slot_ref,
        index_ref=match.index_ref, schema_ref=match.schema_ref, match_ref=match.match_ref,
        bindings=match.bindings,
        source_unit_refs=tuple(row[0] for row in match.source_unit_spans),
        source_unit_spans=match.source_unit_spans,
        orthographic_source_unit_refs=match.orthographic_source_unit_refs,
        provenance_refs=tuple(dict.fromkeys((match.index_ref, match.schema_ref, match.match_ref,
            match.target_designation_slot_ref, *(b.contribution_slot_ref for b in match.bindings)))),
    ) for match in matches if type(match) is QueryProjectionMatch)


def _context_material(context: Any) -> dict[str, Any]:
    return {
        "abi_version": PROPOSAL_CONTEXT_ABI_VERSION,
        "orientation_ref": context.orientation_ref,
        "evidence_packet_ref": context.evidence_packet_ref,
        "form_lattice_ref": context.form_lattice_ref,
        "grounding_ref": context.grounding_ref,
        "designation_slots": [row.as_dict() for row in context.designation_slots],
        "query_projection_slots": [row.as_dict() for row in context.query_projection_slots],
        "contribution_slots": [row.as_dict() for row in context.contribution_slots],
        "mode_slots": [row.as_dict() for row in context.mode_slots],
        "application_frames": [
            _application_frame_as_dict(row) for row in context.application_frames
        ],
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
    if type(context.query_projection_slots) is not tuple:
        raise TypeError("query projection slots must be an exact tuple")
    for name in (
        "orientation_ref",
        "evidence_packet_ref",
        "form_lattice_ref",
        "grounding_ref",
    ):
        _require_exact_string(getattr(context, name), name)
    revision_pin = context.revision_pin
    if type(revision_pin) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    try:
        canonical_pin = RevisionPin.from_dict(RevisionPin.as_dict(revision_pin))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("revision_pin must be canonical RevisionPin") from exc
    if canonical_pin != revision_pin:
        raise ValueError("revision_pin must be canonical RevisionPin")

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
        ("query projection", context.query_projection_slots, config.max_orientation_alternatives, QueryProjectionSlot),
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
            (ApplicationFrameSlot, UnresolvedDesignationFrame),
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
        owners = owner if type(owner) is tuple else (owner,)
        for row in rows:
            if type(row) not in owners:
                raise TypeError(f"{label} slots contain invalid records")
            try:
                type(row).__post_init__(row)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(f"{label} slots contain noncanonical records") from exc
        refs = tuple(
            row.residual_ref if type(row) is ResidualEvidence else row.slot_ref
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
        context.query_projection_slots,
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

    contribution_occurrence_counts: dict[tuple[str, tuple[str, ...]], int] = {}
    contributed_sources: set[str] = set()
    for contribution in context.contribution_slots:
        if _is_orthographic_evidence(contribution):
            continue
        contributed_sources.update(contribution.source_unit_refs)
        if contribution.target_ref is None:
            continue
        occurrence = (contribution.target_ref, contribution.source_unit_refs)
        count = contribution_occurrence_counts.get(occurrence, 0) + 1
        contribution_occurrence_counts[occurrence] = count
        if count > config.max_affordances_per_target * 2:
            raise ValueError("contribution per target occurrence bound violated")
    residual_source_set = set(residual_sources)
    residual_by_source = {row.source_unit_ref: row for row in context.residual_evidence}
    for contribution in context.contribution_slots:
        if (_is_orthographic_evidence(contribution)
            and contribution.constraints == (("orthography", "quotation_boundary"),)):
            residual = residual_by_source.get(contribution.source_unit_refs[0])
            if residual is None or not residual.critical or residual.contribution_kind != "discourse":
                raise ValueError("quotation boundary requires critical discourse residual")
    if contributed_sources & residual_source_set:
        raise ValueError("residual source cannot also have a contribution")
    if contributed_sources | residual_source_set != source_set:
        raise ValueError(
            "proposal context source partition must cover every source unit"
        )

    contribution_by_ref = {row.slot_ref: row for row in context.contribution_slots}
    variables_by_frame: dict[str, list[VariableSlot]] = {}
    for variable in context.variable_slots:
        variables_by_frame.setdefault(variable.application_frame_ref, []).append(
            variable
        )
    open_variable_sources = {
        source_ref
        for contribution in context.contribution_slots
        if contribution.kind == "open_variable"
        for source_ref in contribution.source_unit_refs
    }
    unresolved_hypotheses: set[tuple[str, int, int]] = set()
    for frame in context.application_frames:
        if type(frame) is not UnresolvedDesignationFrame:
            continue
        literal = contribution_by_ref.get(frame.literal_contribution_slot_ref)
        if literal is None:
            raise ValueError(
                "unresolved designation references unknown literal contribution"
            )
        if literal.kind != "literal":
            raise ValueError(
                "unresolved designation literal ref requires literal contribution"
            )
        if literal.source_unit_refs != frame.source_unit_refs:
            raise ValueError(
                "unresolved designation source units must equal literal geometry"
            )
        binder = contribution_by_ref.get(frame.query_binder_slot_ref)
        if binder is None:
            raise ValueError(
                "unresolved designation references unknown binder contribution"
            )
        if binder.kind != "binder":
            raise ValueError(
                "unresolved designation binder ref requires binder contribution"
            )
        selected_spans = tuple(span_by_ref[ref] for ref in frame.source_unit_refs)
        hypothesis = (
            frame.construction_ref,
            min(item[0] for item in selected_spans),
            max(item[1] for item in selected_spans),
        )
        if hypothesis in unresolved_hypotheses:
            raise ValueError(
                "duplicate unresolved designation construction/span hypothesis"
            )
        unresolved_hypotheses.add(hypothesis)
        owned_variables = variables_by_frame.get(frame.slot_ref, ())
        if len(owned_variables) != 1 or owned_variables[0].role_ref != "role:target":
            raise ValueError(
                "unresolved designation requires exactly one owned role:target variable"
            )
        variable = owned_variables[0]
        if variable.construction_ref != frame.construction_ref:
            raise ValueError("unresolved designation variable construction mismatch")
        if (
            not variable.source_unit_refs
            or not set(variable.source_unit_refs) & open_variable_sources
            or not set(variable.source_unit_refs) <= open_variable_sources | set(binder.source_unit_refs)
        ):
            raise ValueError(
                "unresolved designation variable requires open_variable source evidence"
            )

    designation_by_ref = {row.slot_ref: row for row in context.designation_slots}
    for projection in context.query_projection_slots:
        target = designation_by_ref.get(projection.target_designation_slot_ref)
        if target is None or target.target_kind not in {"concept", "entity", "participant"}:
            raise ValueError("query projection target designation is absent or incompatible")
        if projection.source_unit_spans != tuple(row for row in spans if row[0] in projection.source_unit_refs):
            raise ValueError("query projection source geometry differs from its context")
        for binding in projection.bindings:
            contribution = contribution_by_ref.get(binding.contribution_slot_ref)
            if contribution is None or contribution.source_unit_refs != binding.source_unit_refs:
                raise ValueError("query projection contribution pointer/source differs")
            if binding.port == "target":
                if (contribution.kind != "anchor" or contribution.target_ref != target.target_ref
                    or contribution.target_kind != target.target_kind or contribution.source_unit_refs != target.source_unit_refs):
                    raise ValueError("query projection target contribution differs from designation")
            else:
                expected = {"request": ("open_variable", (("query", "query"), ("interrogative", "content"))),
                            "binder": ("binder", (("binder", "copula"),)),
                            "determiner": ("qualifier", (("determiner", "determiner"), ("construction_role", "query_target_article")))}[binding.port]
                if contribution.kind != expected[0] or not set(expected[1]) <= set(contribution.constraints) or contribution.target_ref is not None:
                    raise ValueError("query projection primitive port has incompatible contribution")
        for ref in projection.orthographic_source_unit_refs:
            if not any(c.source_unit_refs == (ref,) and _is_orthographic_evidence(c) for c in context.contribution_slots):
                raise ValueError("query projection orthographic evidence is missing")
    frame_by_ref = {row.slot_ref: row for row in context.application_frames}
    predicates_by_target: dict[str, list[ContributionSlot]] = {}
    for contribution in context.contribution_slots:
        if contribution.kind == "predicate" and contribution.target_ref is not None:
            predicates_by_target.setdefault(contribution.target_ref, []).append(
                contribution
            )
    frame_occurrence_counts: dict[str, int] = {}
    for frame in context.application_frames:
        if type(frame) is UnresolvedDesignationFrame:
            continue
        designation = designation_by_ref.get(frame.designation_slot_ref)
        if designation is None:
            raise ValueError("application frame contains unknown designation slot")
        state_value_frame = _is_state_value_application_frame(
            frame,
            designation,
        )
        transition_value_frame = _is_transition_value_application_frame(
            frame,
            designation,
            context.designation_slots,
        )
        designation_frame = _is_designation_application_frame(frame, designation)
        if (
            frame.predicate_target_ref != designation.target_ref
            or frame.predicate_kind != designation.target_kind
        ) and not (state_value_frame or designation_frame):
            raise ValueError("application frame predicate disagrees with designation")
        if designation_frame:
            expected_operator = "op:designation"
            expected_structural_role = "role:label_type"
            expected_derived_roles = (
                ("role:label_type", frame.predicate_target_ref),
                ("role:target", designation.target_ref),
            )
        elif state_value_frame:
            expected_operator = "op:state"
            expected_structural_role = "role:dimension"
            expected_derived_roles = (
                ("role:dimension", frame.predicate_target_ref),
                ("role:value", designation.target_ref),
            )
        elif transition_value_frame:
            expected_operator = "op:event"
            expected_structural_role = _structural_role_for_kind(
                frame.predicate_kind
            )
            expected_derived_roles = frame.derived_role_targets
        else:
            expected_operator = _operator_for_kind(frame.predicate_kind)
            expected_structural_role = _structural_role_for_kind(frame.predicate_kind)
            expected_derived_roles = _derived_roles_for_kind(
                frame.predicate_kind, frame.predicate_target_ref
            )
        if expected_operator is None or frame.operator_ref != expected_operator:
            raise ValueError("application frame violates exact operator lowering")
        if frame.operator_ref == "op:designation":
            if frame.predicate_kind != "label_type":
                raise ValueError(
                    "designation application predicate must have label_type structure"
                )
            available_roles = {
                *frame.required_roles,
                *frame.optional_roles,
                *(role_ref for role_ref, _ in frame.derived_role_targets),
            }
            if available_roles != {
                "role:label_type",
                "role:surface",
                "role:target",
            } or dict(frame.derived_role_targets).get(
                "role:label_type"
            ) != frame.predicate_target_ref:
                raise ValueError(
                    "designation application frame lacks exact canonical roles"
                )
        if frame.structural_role_ref != expected_structural_role:
            raise ValueError("application frame has an invalid structural role")
        if frame.structural_role_ref in {
            *frame.required_roles,
            *frame.optional_roles,
        }:
            raise ValueError(
                "application frame structural role cannot be a filler role"
            )
        if frame.derived_role_targets != expected_derived_roles:
            raise ValueError("application frame has invalid derived role targets")
        if frame.predicate_kind != "event_type" and frame.proposition_roles:
            raise ValueError(
                "application frame proposition roles require an event predicate"
            )
        if frame.designation_slot_ref not in frame.provenance_refs:
            raise ValueError("application frame provenance omits its designation slot")
        if frame.operator_ref == "op:type" and not _nominal_predication_source_is_exact(frame, designation, context):
            raise ValueError("nominal predication has invalid source geometry")
        frame_input_roles = set(frame.required_roles) | set(frame.optional_roles)
        compatible_contribution = any(
            contribution.target_kind == frame.predicate_kind
            and contribution.source_unit_refs == frame.source_unit_refs
            and bool(contribution.output_ports)
            and contribution.output_ports[0] == frame.structural_role_ref
            and set(contribution.input_ports) == frame_input_roles
            and (
                not designation_frame
                or (
                    (
                        "designation_fact_ref",
                        designation.designation_fact_ref,
                    )
                    in contribution.constraints
                    and ("operator_ref", "op:designation")
                    in contribution.constraints
                    and designation.designation_fact_ref
                    in contribution.provenance_refs
                )
            )
            and (
                not state_value_frame
                or (
                    ("state_value_ref", designation.target_ref)
                    in contribution.constraints
                    and (
                        "value_dimension_ref",
                        frame.predicate_target_ref,
                    )
                    in contribution.constraints
                )
            )
            and (
                not transition_value_frame
                or (
                    ("state_value_ref", dict(frame.derived_role_targets)["role:value"])
                    in contribution.constraints
                    and (
                        "value_dimension_ref",
                        dict(frame.derived_role_targets)["role:dimension"],
                    )
                    in contribution.constraints
                )
            )
            for contribution in predicates_by_target.get(frame.predicate_target_ref, ())
        )
        if not compatible_contribution:
            raise ValueError(
                "application frame roles are not proven by predicate contribution "
                "input roles and structural output"
            )
        if state_value_frame:
            binder_sources = {
                source_ref
                for contribution in context.contribution_slots
                if contribution.kind == "binder"
                and any(
                    category == "binder"
                    for category, _ in contribution.constraints
                )
                for source_ref in contribution.source_unit_refs
            }
            if not (
                set(frame.source_unit_refs) - set(designation.source_unit_refs)
            ) <= binder_sources:
                raise ValueError(
                    "state value application source extension lacks binder proof"
                )
        if designation_frame:
            prospective_teaching_frame = any(
                contribution.source_unit_refs == frame.source_unit_refs
                and ("prospective_designation", "teaching_claim")
                in contribution.constraints
                and any(
                    key == "teaching_evidence_ref"
                    and value in frame.provenance_refs
                    for key, value in contribution.constraints
                )
                for contribution in predicates_by_target.get(
                    frame.predicate_target_ref, ()
                )
            )
            qualifier_sources = {
                source_ref
                for contribution in context.contribution_slots
                if contribution.kind == "qualifier"
                and any(
                    category == "determiner"
                    for category, _ in contribution.constraints
                )
                for source_ref in contribution.source_unit_refs
            }
            if not prospective_teaching_frame and not (
                set(frame.source_unit_refs) - set(designation.source_unit_refs)
            ) <= qualifier_sources:
                raise ValueError(
                    "designation application source extension lacks determiner proof"
                )
            if not any(
                contribution.kind == "literal"
                and contribution.source_unit_refs == frame.source_unit_refs
                and contribution.output_ports == ("role:surface",)
                and contribution.literal_value is not None
                and designation.designation_fact_ref
                in contribution.provenance_refs
                for contribution in context.contribution_slots
            ):
                raise ValueError(
                    "designation application lacks an authenticated surface literal"
                )
            continue
        count = frame_occurrence_counts.get(frame.designation_slot_ref, 0) + 1
        frame_occurrence_counts[frame.designation_slot_ref] = count
        if count > config.max_affordances_per_target:
            raise ValueError("application frame per designation occurrence bound violated")
    if any(
        row.application_frame_ref not in frame_by_ref for row in context.variable_slots
    ):
        raise ValueError("variable contains unknown application frame")
    binder_sources = {
        source_ref
        for contribution in context.contribution_slots
        if contribution.kind == "binder"
        for source_ref in contribution.source_unit_refs
    }
    for variable in context.variable_slots:
        frame = frame_by_ref[variable.application_frame_ref]
        allowed_sources = open_variable_sources
        if type(frame) is UnresolvedDesignationFrame:
            allowed_sources = open_variable_sources | set(contribution_by_ref[frame.query_binder_slot_ref].source_unit_refs)
        if (
            type(frame) is ApplicationFrameSlot
            and frame.predicate_kind == "label_type"
            and variable.role_ref == "role:surface"
        ):
            # The reviewed designation surface contract retains its query
            # source plus predication binders; a binder alone is not a query.
            allowed_sources = open_variable_sources | binder_sources
        sources = set(variable.source_unit_refs)
        if not sources & open_variable_sources or not sources <= allowed_sources:
            raise ValueError("variable requires exact open_variable source evidence")
    for transition in context.transition_slots:
        frame = frame_by_ref.get(transition.application_frame_ref)
        if frame is None:
            raise ValueError("transition contains unknown application frame")
        if type(frame) is not ApplicationFrameSlot or frame.operator_ref != "op:state":
            raise ValueError("transition requires an op:state application frame")


__all__ = [
    "PROPOSAL_CONTEXT_ABI_VERSION",
    "DesignationSlot",
    "QueryProjectionSlot",
    "licensed_query_projection_slots",
    "ContributionSlot",
    "ModeSlot",
    "ApplicationFrameSlot",
    "UnresolvedDesignationFrame",
    "ApplicationFrame",
    "ReferenceSlot",
    "ScopeSlot",
    "ExpressionLinkSlot",
    "VariableSlot",
    "TransitionSlot",
    "ResidualEvidence",
    "ProposalContext",
    "ProposalContextBuilder",
]
